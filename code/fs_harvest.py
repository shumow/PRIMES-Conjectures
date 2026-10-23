"""Track C (harvest-design comparison): bounded actual-prime family comparisons.

Plan: doc/harvest-solver-feasibility-plan.md section 7. Baseline interfaces are
reused read-only from the merged real-pool pilot; this module owns only the
fs_harvest artifacts. Run from the repository root:

    python -B code/fs_harvest.py

Writes data/generated/fs_harvest.json.gz (refuses to overwrite; --replace to
permit). The declared grid and its rationale are fixed below BEFORE any
interpretation of results, per the plan's contract.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import gzip
import json
import math
import platform
import time

from real_pool_pilot import (
    CONFIGS as PILOT_CONFIGS, HarvestConfig, build_instance, harvest,
    measure_structure, serialize_instance,
)
from real_pool_verify import source_digest

# ---------------------------------------------------------------------------
# Declared grid. Budgets follow plan section 8: at most four new cells, at most
# 5,000,000 candidate draws per cell, accepted-pool cap at most 1,024.
# The anchor is a byte-for-byte rerun of the pilot's complete medium family
# (same bounds, factor count, caps and seed; only the name differs) so that
# reproduction can be checked against the frozen dataset without replacing it.
# ---------------------------------------------------------------------------

ANCHOR = HarvestConfig("fs-anchor-rerun-medium-complete", 547, 2735, 3,
                       5000000, 512, False, 20261022)

CELLS = (
    HarvestConfig("fs-c1-four-factors", 547, 2735, 4, 5000000, 1024, True, 20261023),
    HarvestConfig("fs-c2-wider-minus", 547, 5470, 3, 5000000, 1024, True, 20261023),
    HarvestConfig("fs-c3-wider-plus-complete", 1259, 2735, 3, 5000000, 1024, False, 20261023),
    HarvestConfig("fs-c4-both-wider", 1259, 6295, 3, 5000000, 1024, True, 20261023),
)

RATIONALE = {
    ANCHOR.name:
        "Reproducibility anchor: identical configuration to the pilot's "
        "medium-complete-family (547/2735, three factors, seed 20261022); "
        "must reproduce its accepted count and exact group statistics.",
    "fs-c1-four-factors":
        "The j axis at fixed bases: four distinct minus factors multiply the "
        "candidate family (C(298,4) ~ 3.2e8) at the same factor bases, so "
        "any supply gain comes from combinatorial volume alone while the "
        "assembled group can only grow through newly used primes. Sampled "
        "with replacement (family exceeds the draw cap).",
    "fs-c2-wider-minus":
        "Minus-base allocation: doubling the minus bound (B'/B = 10 instead "
        "of 5) multiplies the three-factor family (~9x) but each used medium "
        "prime adds ~log2(q) group bits; measures whether the numerator "
        "(distinct certified primes) or denominator (exact group bits) moves "
        "faster. Sampled with replacement.",
    "fs-c3-wider-plus-complete":
        "Plus-base allocation: raising the plus bound to 1259 improves the "
        "smoothness probability of (m+1)/2 (historically the density-"
        "critical side) at the cost of more plus-side components. The "
        "three-factor family C(194,3) = 1,178,816 fits the draw cap, so this "
        "cell is a complete scan with exact family statistics.",
    "fs-c4-both-wider":
        "Interaction cell: both bases widened at the pilot's B'/B = 5 shape "
        "(1259/6295). Tests whether the C2 and C3 effects compose. Sampled "
        "with replacement.",
}

LIMITS = [
    "At most four new cells, 5,000,000 draws per cell, accepted-pool cap 1,024 (plan section 8).",
    "One worker process; no nested parallelism.",
    "With-replacement sampling: per-draw acceptance intervals do not convert into distinct-prime population counts or group-size predictions.",
    "Zero observed hits in a sampled cell bounds nothing about the population; it is recorded as observed zero only.",
    "Passing necessary quotient checks is not Boolean or full-subgroup reachability.",
    "A pool/group-bit ratio above one would be a heuristic supply milestone, not an existence theorem.",
    "No production search is run by this module; no solver benchmarks are run (Track A owns those).",
]


def wilson_interval(successes: int, trials: int, z: float = 1.959964) -> tuple[float, float]:
    """95% Wilson score interval for a binomial proportion."""
    if trials < 1 or not 0 <= successes <= trials:
        raise ValueError("invalid interval inputs")
    phat = successes / trials
    denominator = 1 + z * z / trials
    center = (phat + z * z / (2 * trials)) / denominator
    half = (z / denominator) * math.sqrt(
        phat * (1 - phat) / trials + z * z / (4 * trials * trials))
    return (max(0.0, center - half), min(1.0, center + half))


def per_draw_stats(accepted: int, duplicates: int, draws: int, sampled: bool,
                   stop_reason: str) -> dict:
    """Per-draw statistics with the correct Bernoulli numerator.

    A with-replacement draw is a certified success when it passes every filter
    and certifies, whether or not the prime was already in the pool — so the
    i.i.d. per-draw numerator is accepted + duplicates. The distinct-discovery
    rate (accepted/draws) is a depleting process, NOT identically distributed,
    and carries no binomial interval. Intervals are only attached when the
    trial count was fixed in advance (the run did not stop at the pool cap).
    """
    if draws < 1 or min(accepted, duplicates) < 0:
        raise ValueError("invalid per-draw statistics inputs")
    certified = accepted + duplicates
    stats: dict = {
        "certified_draw_successes": certified,
        "certified_hit_rate_per_draw": certified / draws,
        "distinct_discovery_rate": accepted / draws,
        "distinct_rate_caveat": ("depleting (non-i.i.d.) process; "
                                 "no binomial interval applies"),
    }
    if sampled:
        if stop_reason == "pool_cap":
            stats["certified_hit_wilson95"] = None
            stats["interval_caveat"] = ("trial count truncated by the pool "
                                        "cap; fixed-n binomial interval "
                                        "does not apply")
        else:
            low, high = wilson_interval(certified, draws)
            stats["certified_hit_wilson95"] = [low, high]
            stats["sampling_caveat"] = (
                "with-replacement per-draw interval for the certified-hit "
                "rate; not an interval for distinct primes, exact group size "
                "or target feasibility")
    return stats


def summarize_cell(config: HarvestConfig, info: dict, instance, structure) -> dict:
    counts = info["counts"]
    checks = structure["necessary_target_checks"]
    binary = next(entry for entry in checks["prime_field_checks"] if entry["prime"] == 2)
    retained = structure["pool_size"]
    summary = {
        "certified_primes": counts["accepted"],
        "retained_units": retained,
        "excluded_nonunits": counts["accepted"] - retained,
        "components": structure["components"],
        "group_bits": structure["group_bits"],
        "pool_per_group_bit": structure["pool_per_group_bit"],
        "lambda_minus_bits": instance.lambda_minus.bit_length(),
        "lambda_plus_bits": instance.lambda_plus.bit_length(),
        "binary_rows": binary["rows"],
        "binary_rank": binary["rank"],
        "binary_nullity": retained - binary["rank"],
        "binary_consistent": binary["consistent"],
        "has_obstruction": checks["has_obstruction"],
        "coordinate_obstructions": len(checks["coordinate_obstructions"]),
        "mean_literal_identity_fraction": structure["mean_literal_identity_fraction"],
        "mean_forced_identity_fraction": structure["mean_forced_identity_fraction"],
        "bit_weighted_identity_fraction": structure["bit_weighted_identity_fraction"],
        "distinct_vectors": structure["distinct_vectors"],
        "duplicates": counts["duplicates"],
        "draws": counts["draws"],
        "candidate_family_size": info["candidate_family_size"],
        "complete_family_scan": info["complete_family_scan"],
        "stop_reason": info["stop_reason"],
    }
    summary.update(per_draw_stats(counts["accepted"], counts["duplicates"],
                                  counts["draws"], config.sampled,
                                  info["stop_reason"]))
    return summary


def run_cell(config: HarvestConfig) -> dict:
    records, info = harvest(config)
    cell: dict = {"name": config.name, "rationale": RATIONALE[config.name],
                  "harvest": info}
    if not records:
        cell["status"] = "empty_harvest"
        print(f"{config.name}: empty harvest under the stated caps", flush=True)
        return cell
    start = time.monotonic()
    instance = build_instance(records)
    structure = measure_structure(instance, config.seed)
    cell.update(status="encoded_and_verified",
                instance_build_seconds=time.monotonic() - start,
                instance=serialize_instance(instance),
                structure=structure,
                summary=summarize_cell(config, info, instance, structure))
    summary = cell["summary"]
    print(f"{config.name}: {summary['certified_primes']} certified primes, "
          f"{summary['retained_units']} units, {summary['components']} components, "
          f"{summary['group_bits']:.2f} group bits, "
          f"N/bits = {summary['pool_per_group_bit']:.4f}, "
          f"obstruction = {summary['has_obstruction']}", flush=True)
    return cell


def anchor_comparison(anchor_cell: dict, pilot_path: Path) -> dict:
    """Compare the anchor rerun against the frozen pilot dataset (read-only)."""
    if not pilot_path.exists():
        return {"status": "pilot_dataset_missing", "path": str(pilot_path)}
    raw = pilot_path.read_bytes()
    payload = gzip.decompress(raw) if pilot_path.suffix == ".gz" else raw
    pilot = json.loads(payload)
    run = next(r for r in pilot["runs"] if r["name"] == "medium-complete-family")
    expected = {
        "accepted": run["harvest"]["counts"]["accepted"],
        "draws": run["harvest"]["counts"]["draws"],
        "group_bits": run["structure"]["group_bits"],
        "components": run["structure"]["components"],
        "pool_per_group_bit": run["structure"]["pool_per_group_bit"],
        "has_obstruction": run["structure"]["necessary_target_checks"]["has_obstruction"],
    }
    got_summary = anchor_cell.get("summary", {})
    got = {
        "accepted": got_summary.get("certified_primes"),
        "draws": got_summary.get("draws"),
        "group_bits": got_summary.get("group_bits"),
        "components": got_summary.get("components"),
        "pool_per_group_bit": got_summary.get("pool_per_group_bit"),
        "has_obstruction": got_summary.get("has_obstruction"),
    }
    matches = {key: (got[key] == expected[key] if isinstance(expected[key], (int, bool))
                     else got[key] is not None
                     and math.isclose(got[key], expected[key], rel_tol=1e-12))
               for key in expected}
    return {"status": "reproduced" if all(matches.values()) else "MISMATCH",
            "pilot_dataset_sha256_gz": __import__("hashlib").sha256(raw).hexdigest(),
            "expected": expected, "observed": got, "matches": matches}


def run_track_c() -> dict:
    here = Path(__file__).resolve().parent
    pilot_path = here.parent / "data" / "generated" / "real_pool_pilot.json.gz"
    cells = []
    anchor_cell = run_cell(ANCHOR)
    anchor_cell["anchor_comparison"] = anchor_comparison(anchor_cell, pilot_path)
    cells.append(anchor_cell)
    for config in CELLS:
        cells.append(run_cell(config))
    sources = ("fs_harvest.py", "real_pool_pilot.py", "real_pool_verify.py",
               "a4_solver.py", "a6_oddsolver.py", "a7_lohniebuhr.py",
               "phase1a_calibration.py")
    return {
        "schema": "fs-harvest/v2",
        "schema_note": ("v2 after PR #4 coordinator review: per-draw "
                        "statistics use the certified-success numerator "
                        "(accepted + duplicates); the distinct-discovery "
                        "rate is reported separately without an interval"),
        "track": "C (harvest-design comparison)",
        "plan": "doc/harvest-solver-feasibility-plan.md section 7",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "source_hash_normalization": "CRLF-to-LF",
        "source_sha256": {name: source_digest(here / name) for name in sources},
        "pilot_configs_for_reference": [c.name for c in PILOT_CONFIGS],
        "cells": cells,
        "limits": LIMITS,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent.parent
                        / "data" / "generated" / "fs_harvest.json.gz")
    parser.add_argument("--replace", action="store_true",
                        help="explicitly replace this output file")
    args = parser.parse_args()
    if args.output.exists() and not args.replace:
        parser.error("output already exists; use --replace or choose another path")
    report = run_track_c()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    args.output.write_bytes(gzip.compress(payload, mtime=0)
                            if args.output.suffix == ".gz" else payload)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
