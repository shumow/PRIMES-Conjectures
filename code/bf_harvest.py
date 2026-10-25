"""S3 (Boolean Feasibility Study): complete scan of the c2 family — approval-gated.

Plan: PLAN.md "Current next steps (2026-10-24)" section 5. This module prepares
and, ONLY after explicit budget approval, executes the complete enumeration of
the fs-c2-wider-minus family (plus bound 547, minus bound 5470, three distinct
minus factors, prime-power cap 8192): 39,529,340 combinations, global accepted
pool cap 4,096.

Without --approved, the command line refuses to run the production scan.
Library functions are bounded and are exercised by the correctness tests on
the small 113/565 family only.

Design points required by the plan:
  - deterministic contiguous shard ranges over the lexicographic combination
    index space, with a coverage manifest and aggregate counters;
  - one worker process (sharding is checkpoint granularity, not parallelism),
    so the global pool cap can never become a per-shard allowance;
  - identical admissibility tests to the pilot harvest (locked by a
    record-level equivalence regression on the small complete family);
  - full-factor Lucas certificates only; probable primes are never admitted;
  - if any cap binds, the actual partial scope and stop reason are recorded.

Run (after approval): python -B code/bf_harvest.py --approved
"""
from datetime import datetime, timezone
from dataclasses import asdict
from pathlib import Path
import argparse
import gzip
import json
import math
import platform
import time

from phase1a_calibration import is_prime, primes_upto
from real_pool_pilot import (
    HarvestConfig, build_instance, harvest as pilot_harvest, lucas_witness,
    measure_structure, serialize_instance,
)
from real_pool_verify import PrimeRecord, source_digest, verify_prime

C2_COMPLETE = HarvestConfig("bf-c2-complete-family", 547, 5470, 3,
                            39529340, 4096, False, 20261025)
DEFAULT_SHARDS = 40


def combination_unrank(index: int, items: list, k: int) -> tuple:
    """The index-th k-combination of items in lexicographic order."""
    n = len(items)
    if k < 0 or k > n or not 0 <= index < math.comb(n, k):
        raise ValueError("invalid unrank arguments")
    chosen = []
    position = 0
    for slot in range(k):
        for candidate in range(position, n - (k - slot - 1)):
            block = math.comb(n - candidate - 1, k - slot - 1)
            if index < block:
                chosen.append(items[candidate])
                position = candidate + 1
                break
            index -= block
    return tuple(chosen)


def shard_ranges(total: int, shards: int) -> list:
    """Contiguous [start, stop) ranges that exactly partition range(total)."""
    if total < 1 or shards < 1:
        raise ValueError("invalid shard arguments")
    shards = min(shards, total)
    base, extra = divmod(total, shards)
    ranges, start = [], 0
    for i in range(shards):
        stop = start + base + (1 if i < extra else 0)
        ranges.append((start, stop))
        start = stop
    return ranges


def iterate_combinations(items: list, k: int, start: int, stop: int):
    """Lexicographic combinations for global indices [start, stop)."""
    current = list(combination_unrank(start, items, k))
    index_of = {value: i for i, value in enumerate(items)}
    n = len(items)
    for _ in range(stop - start):
        yield tuple(current)
        # advance to the successor combination in lexicographic order
        positions = [index_of[value] for value in current]
        slot = k - 1
        while slot >= 0 and positions[slot] == n - k + slot:
            slot -= 1
        if slot < 0:
            return
        positions[slot] += 1
        for later in range(slot + 1, k):
            positions[later] = positions[slot] + (later - slot)
        current = [items[position] for position in positions]


def scan_shard(minus_combination_iter, plus: list, config: HarvestConfig,
               records: dict, counts: dict) -> str:
    """Apply the pilot's admissibility pipeline to one shard.

    The filter chain below mirrors real_pool_pilot.harvest step for step
    (mod-40 class, uint64 bound, complete Q+ smoothness of (m+1)/2 with the
    prime-power cap, probable-prime prefilter, duplicate check, exact
    full-factor Lucas certificate, independent verify_prime). Equivalence is
    locked by test_bf_harvest_correctness on the complete small family.
    Returns "ok" or "pool_cap".
    """
    for factors in minus_combination_iter:
        counts["draws"] += 1
        m = math.prod(factors)
        if m % 40 != 1:
            continue
        counts["mod40"] += 1
        p = 2 * m + 1
        if p >= 1 << 64:
            counts["outside_uint64"] += 1
            continue
        value = (m + 1) // 2
        plus_factors = {2: 2}
        for q in plus:
            exponent = 0
            while value % q == 0:
                value //= q
                exponent += 1
            if exponent:
                plus_factors[q] = exponent
            if value == 1:
                break
        if value != 1:
            continue
        counts["smooth"] += 1
        if any(q**e > config.prime_power_cap for q, e in plus_factors.items()):
            counts["power_cap_rejected"] += 1
            continue
        if not is_prime(p):
            continue
        counts["probable_primes"] += 1
        if p in records:
            counts["duplicates"] += 1
            continue
        minus_factors = {2: 1, **{q: 1 for q in factors}}
        witness = lucas_witness(p, minus_factors)
        if witness is None:
            counts["certificate_exhausted"] += 1
            continue
        record = PrimeRecord(p, tuple(sorted(minus_factors.items())),
                             tuple(sorted(plus_factors.items())), witness,
                             counts["draws"])
        verify_prime(record)
        records[p] = record
        counts["accepted"] += 1
        if len(records) >= config.pool_cap:
            return "pool_cap"
    return "ok"


def complete_scan(config: HarvestConfig, shards: int = DEFAULT_SHARDS):
    """Complete deterministic enumeration with a coverage manifest."""
    if config.sampled:
        raise ValueError("complete_scan requires a non-sampled configuration")
    primes = primes_upto(config.minus_bound)
    minus = [q for q in primes if q > config.plus_bound]
    plus = [q for q in primes if 2 < q <= config.plus_bound and q != 5]
    family = math.comb(len(minus), config.factors)
    if config.candidate_cap < family:
        raise ValueError("candidate cap below the family size; this scanner "
                         "is for complete coverage only")
    counts = dict(draws=0, mod40=0, smooth=0, power_cap_rejected=0,
                  probable_primes=0, certificate_exhausted=0, duplicates=0,
                  outside_uint64=0, accepted=0)
    records: dict[int, PrimeRecord] = {}
    manifest = []
    stop = "family_exhausted"
    start_time = time.monotonic()
    for start, end in shard_ranges(family, shards):
        shard_start = time.monotonic()
        draws_before, accepted_before = counts["draws"], counts["accepted"]
        status = scan_shard(iterate_combinations(minus, config.factors, start, end),
                            plus, config, records, counts)
        manifest.append({
            "range": [start, end],
            "draws": counts["draws"] - draws_before,
            "accepted": counts["accepted"] - accepted_before,
            "seconds": round(time.monotonic() - shard_start, 3),
            "status": status,
        })
        if status == "pool_cap":
            stop = "pool_cap"
            break
    covered = counts["draws"]
    info = {
        "config": asdict(config),
        "q_minus": minus, "q_plus": plus,
        "candidate_family_size": family, "counts": counts, "stop_reason": stop,
        "complete_family_scan": stop == "family_exhausted" and covered == family,
        "covered_global_indices": covered,
        "coverage_manifest": manifest,
        "sampling": "deterministic lexicographic enumeration in contiguous shard ranges",
        "primality": ("probable-prime prefilter, then independently checked "
                      "full-factor Lucas certificate"),
        "witness_bases": [2, 65],
        "workers": 1,
        "seconds": time.monotonic() - start_time,
    }
    return tuple(sorted(records.values(), key=lambda record: record.p)), info


def run_s3(config: HarvestConfig, shards: int) -> dict:
    records, info = complete_scan(config, shards)
    report: dict = {"name": config.name, "harvest": info}
    if not records:
        report["status"] = "empty_harvest"
    else:
        build_start = time.monotonic()
        instance = build_instance(records)
        report["instance_build_seconds"] = time.monotonic() - build_start
        structure = measure_structure(instance, config.seed)
        report.update(status="encoded_and_verified",
                      instance=serialize_instance(instance),
                      structure=structure)
        print(f"{config.name}: {len(records)} certified primes, "
              f"{len(instance.records)} units, {len(instance.orders)} components, "
              f"{structure['group_bits']:.2f} group bits, "
              f"N/bits = {structure['pool_per_group_bit']:.4f}, "
              f"obstruction = "
              f"{structure['necessary_target_checks']['has_obstruction']}",
              flush=True)
    here = Path(__file__).resolve().parent
    sources = ("bf_harvest.py", "real_pool_pilot.py", "real_pool_verify.py",
               "a4_solver.py", "a6_oddsolver.py", "a7_lohniebuhr.py",
               "phase1a_calibration.py")
    return {
        "schema": "bf-harvest/v1",
        "work_item": "S3 (complete c2 family), PLAN.md current section 5",
        "approval": "executed only under an explicitly recorded budget approval",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "source_hash_normalization": "CRLF-to-LF",
        "source_sha256": {name: source_digest(here / name) for name in sources},
        "run": report,
        "limits": [
            "Global accepted-pool cap 4,096 across all shards (never per-shard).",
            "One worker process; shards are checkpoints, not parallelism.",
            "If any cap binds, the partial scope and stop reason above are the result scope.",
            "Passing necessary checks is not Boolean or full-subgroup reachability.",
            "No further family expansion follows from any outcome of this run.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved", action="store_true",
                        help="assert that the S3 budget proposal was explicitly "
                             "approved; refuses to run without it")
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARDS)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent.parent
                        / "data" / "generated" / "bf_harvest.json.gz")
    parser.add_argument("--replace", action="store_true",
                        help="explicitly replace this output file")
    args = parser.parse_args()
    if not args.approved:
        parser.error("the S3 complete scan requires explicit budget approval; "
                     "re-run with --approved only after the proposal in "
                     "doc/bf-harvest-proposal.md is approved")
    if args.output.exists() and not args.replace:
        parser.error("output already exists; use --replace or choose another path")
    report = run_s3(C2_COMPLETE, args.shards)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    args.output.write_bytes(gzip.compress(payload, mtime=0)
                            if args.output.suffix == ".gz" else payload)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
