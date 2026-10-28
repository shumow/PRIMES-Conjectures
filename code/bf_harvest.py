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
from real_pool_verify import (
    PrimeRecord, instance_from_json, source_digest, verify_encoding,
    verify_metrics, verify_prime,
)

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


def load_report(path: Path) -> dict:
    raw = path.read_bytes()
    payload = gzip.decompress(raw) if path.suffix == ".gz" else raw
    return json.loads(payload)


# Scanner-implementation registry: LF-normalized SHA256 of code/bf_harvest.py
# at each version that has produced a saved report. The scan artifact records
# the hash of the implementation that RAN, which legitimately differs from the
# current source once later stages are added; verification accepts a recorded
# hash only if it is a known implementation version (or the current source).
KNOWN_IMPLEMENTATIONS = {
    "81c577d (proposal + gated scanner; produced the approved 2026-10-25 run)":
        "3b9e5717ffda8d332e9d26df50b9a3fe477ef9b4368df9a0c920d3faf8a4ca1d",
}


def combination_rank(combo: tuple, items: list, k: int) -> int:
    """Lexicographic rank of a k-combination; inverse of combination_unrank."""
    if len(combo) != k or list(combo) != sorted(combo):
        raise ValueError("combination must be sorted and of length k")
    index_of = {value: i for i, value in enumerate(items)}
    n, rank, previous = len(items), 0, -1
    for slot, value in enumerate(combo):
        position = index_of[value]
        for skipped in range(previous + 1, position):
            rank += math.comb(n - skipped - 1, k - slot - 1)
        previous = position
    return rank


def _gf2_rank_consistent(rows: list, rhs: list, ncols: int) -> tuple:
    """Row rank and consistency over GF(2); local bitset elimination,
    independent of the generator's a4_solver.gf2_solve."""
    augmented = [(mask << 1) | (b & 1) for mask, b in zip(rows, rhs)]
    rank = 0
    for col in range(ncols):
        bit = 1 << (col + 1)
        pivot = next((i for i in range(rank, len(augmented))
                      if augmented[i] & bit), None)
        if pivot is None:
            continue
        augmented[rank], augmented[pivot] = augmented[pivot], augmented[rank]
        for i in range(len(augmented)):
            if i != rank and augmented[i] & bit:
                augmented[i] ^= augmented[rank]
        rank += 1
    consistent = all(row != 1 for row in augmented[rank:])
    return rank, consistent


def _gfl_rank_consistent(matrix: list, rhs: list, ell: int) -> tuple:
    """Row rank and consistency over GF(ell); local elimination, independent
    of the generator's a7_lohniebuhr.gfl_rref."""
    rows = [[value % ell for value in row] + [b % ell]
            for row, b in zip(matrix, rhs)]
    rank = 0
    ncols = len(matrix[0]) if matrix else 0
    for col in range(ncols):
        pivot = next((i for i in range(rank, len(rows)) if rows[i][col]), None)
        if pivot is None:
            continue
        rows[rank], rows[pivot] = rows[pivot], rows[rank]
        inverse = pow(rows[rank][col], ell - 2, ell)
        rows[rank] = [(value * inverse) % ell for value in rows[rank]]
        for i in range(len(rows)):
            if i != rank and rows[i][col]:
                factor = rows[i][col]
                rows[i] = [(a - factor * b) % ell
                           for a, b in zip(rows[i], rows[rank])]
        rank += 1
    consistent = all(any(row[:-1]) or row[-1] == 0 for row in rows)
    return rank, consistent


def _verify_provenance(report: dict) -> str:
    if report.get("schema") != "bf-harvest/v1":
        raise ArithmeticError("unknown report schema")
    here = Path(__file__).resolve().parent
    recorded = report["source_sha256"]
    scanner = recorded.get("bf_harvest.py")
    current = source_digest(here / "bf_harvest.py")
    if scanner == current:
        version = "current source"
    else:
        version = next((name for name, digest in KNOWN_IMPLEMENTATIONS.items()
                        if digest == scanner), None)
        if version is None:
            raise ArithmeticError("recorded scanner hash is neither the current "
                                  "source nor a known implementation version")
    for name, digest in recorded.items():
        if name == "bf_harvest.py":
            continue
        if source_digest(here / name) != digest:
            raise ArithmeticError(f"recorded hash for shared source {name} does "
                                  "not match the current file")
    return version


def _verify_family_and_records(run: dict, instance) -> None:
    """Every admitted record must belong to the declared family and sit at the
    candidate index its lexicographic rank implies."""
    config = run["harvest"]["config"]
    if config["sampled"]:
        raise ArithmeticError("bf-harvest reports must come from the "
                              "deterministic complete scanner")
    primes = primes_upto(config["minus_bound"])
    minus = [q for q in primes if q > config["plus_bound"]]
    plus = set(q for q in primes if 2 < q <= config["plus_bound"] and q != 5)
    if run["harvest"]["q_minus"] != minus or set(run["harvest"]["q_plus"]) != plus:
        raise ArithmeticError("recorded factor bases do not match the declared bounds")
    family = math.comb(len(minus), config["factors"])
    if run["harvest"]["candidate_family_size"] != family:
        raise ArithmeticError("recorded family size does not match the declared bases")
    minus_set = set(minus)
    for record in instance.records:
        odd_minus = tuple(q for q, e in record.minus if q != 2)
        exponents = dict(record.minus)
        if (len(odd_minus) != config["factors"] or exponents.get(2) != 1
                or any(exponents[q] != 1 or q not in minus_set for q in odd_minus)):
            raise ArithmeticError(f"record {record.p} is outside the declared minus family")
        m = math.prod(odd_minus)
        if m % 40 != 1 or record.p != 2 * m + 1 or record.p >= 1 << 64:
            raise ArithmeticError(f"record {record.p} violates the admissibility congruences")
        for q, e in record.plus:
            if q == 2:
                if e != 2:
                    raise ArithmeticError(f"record {record.p} has wrong 2-adic plus part")
            elif q not in plus:
                raise ArithmeticError(f"record {record.p} has a plus factor outside the base")
            if q**e > config["prime_power_cap"]:
                raise ArithmeticError(f"record {record.p} violates the prime-power cap")
        rank = combination_rank(odd_minus, minus, config["factors"])
        if rank + 1 != record.candidate_index:
            raise ArithmeticError(
                f"record {record.p}: candidate index {record.candidate_index} "
                f"does not equal lexicographic rank {rank} + 1")
        if rank >= run["harvest"]["covered_global_indices"]:
            raise ArithmeticError(f"record {record.p} lies outside the covered scope")


def _verify_manifest_and_counts(run: dict, records_count: int) -> None:
    harvest = run["harvest"]
    manifest = harvest["coverage_manifest"]
    family = harvest["candidate_family_size"]
    counts = harvest["counts"]
    config = harvest["config"]
    position = 0
    draws_total = 0
    for i, entry in enumerate(manifest):
        start, end = entry["range"]
        if start != position or end <= start or end > family:
            raise ArithmeticError("coverage manifest is not contiguous and "
                                  "nonoverlapping from zero")
        expected = end - start
        last = i == len(manifest) - 1
        if entry["draws"] != expected and not (last and entry["status"] == "pool_cap"
                                               and entry["draws"] < expected):
            raise ArithmeticError("a shard's draw count does not match its range")
        if entry["status"] == "pool_cap" and not last:
            raise ArithmeticError("a pool-cap stop must terminate the manifest")
        draws_total += entry["draws"]
        position = end
    covered = harvest["covered_global_indices"]
    if draws_total != covered or counts["draws"] != covered:
        raise ArithmeticError("coverage manifest does not match covered indices")
    complete = (harvest["stop_reason"] == "family_exhausted" and covered == family
                and position == family)
    if harvest["complete_family_scan"] != complete:
        raise ArithmeticError("complete-family flag contradicts the manifest")
    if harvest["stop_reason"] == "pool_cap" and counts["accepted"] != config["pool_cap"]:
        raise ArithmeticError("pool-cap stop without a full pool")
    if counts["accepted"] != records_count or counts["accepted"] > config["pool_cap"]:
        raise ArithmeticError("accepted count does not match the stored records")
    if not (counts["mod40"] <= counts["draws"]
            and counts["smooth"] <= counts["mod40"]
            and counts["probable_primes"] <= counts["smooth"] - counts["power_cap_rejected"]
            and counts["accepted"] + counts["duplicates"] + counts["certificate_exhausted"]
            <= counts["probable_primes"]):
        raise ArithmeticError("filter counters are not monotone")
    if complete and counts["accepted"] + counts["duplicates"] + \
            counts["certificate_exhausted"] != counts["probable_primes"]:
        raise ArithmeticError("probable primes unaccounted for in a complete scan")


def _verify_necessary_checks(run: dict, instance) -> dict:
    """Recompute the necessary target checks from the vectors with local,
    generator-independent linear algebra, and re-verify stored witnesses."""
    from real_pool_verify import verify_obstruction
    stored = run["structure"]["necessary_target_checks"]
    orders, vectors, target = instance.orders, instance.vectors, instance.target
    n = len(vectors)
    coordinate = []
    for j, order in enumerate(orders):
        divisor = math.gcd(order, *(vector[j] for vector in vectors))
        if target[j] % divisor:
            coordinate.append({"modulus": divisor, "terms": [(j, 1)]})
            verify_obstruction(orders, vectors, target, divisor, [(j, 1)])
    stored_coordinate = stored["coordinate_obstructions"]
    if len(stored_coordinate) != len(coordinate) or any(
            s["modulus"] != c["modulus"]
            or [tuple(t) for t in s["terms"]] != c["terms"]
            for s, c in zip(stored_coordinate, coordinate)):
        raise ArithmeticError("stored coordinate obstructions do not match recomputation")
    fields: dict = {}
    for j, order in enumerate(orders):
        ell = min(q for q in range(2, order + 1) if order % q == 0)
        fields.setdefault(ell, []).append(j)
    any_inconsistent = False
    recomputed = {}
    for ell, columns in sorted(fields.items()):
        rhs = [target[j] % ell for j in columns]
        if ell == 2:
            masks = [sum((vector[j] & 1) << i for i, vector in enumerate(vectors))
                     for j in columns]
            rank, consistent = _gf2_rank_consistent(masks, rhs, n)
        else:
            matrix = [[vector[j] % ell for vector in vectors] for j in columns]
            rank, consistent = _gfl_rank_consistent(matrix, rhs, ell)
        recomputed[ell] = {"rows": len(columns), "rank": rank,
                           "consistent": consistent}
        any_inconsistent = any_inconsistent or not consistent
    stored_fields = {entry["prime"]: entry for entry in stored["prime_field_checks"]}
    if set(stored_fields) != set(recomputed):
        raise ArithmeticError("stored prime-field check set does not match recomputation")
    for ell, mine in recomputed.items():
        theirs = stored_fields[ell]
        if (theirs["rows"], theirs["rank"], theirs["consistent"]) != \
                (mine["rows"], mine["rank"], mine["consistent"]):
            raise ArithmeticError(
                f"stored GF({ell}) rank/consistency does not match recomputation")
        if not mine["consistent"]:
            witness = theirs.get("obstruction")
            if not witness:
                raise ArithmeticError(
                    f"inconsistent GF({ell}) system lacks a stored witness")
            verify_obstruction(orders, vectors, target, witness["modulus"],
                               [tuple(term) for term in witness["terms"]])
    has = bool(coordinate) or any_inconsistent
    if stored["has_obstruction"] != has:
        raise ArithmeticError("stored has_obstruction flag contradicts recomputation")
    # Premises of the coordinator's index-two argument (PR #9 review):
    # order-2 coordinates equal to 1 on every vector and on the target.
    all_ones = [j for j, order in enumerate(orders)
                if order == 2 and target[j] == 1
                and all(vector[j] == 1 for vector in vectors)]
    binary = recomputed.get(2, {"rows": 0, "rank": 0, "consistent": False})
    odd_full = all(value["rank"] == value["rows"] and value["consistent"]
                   for ell, value in recomputed.items() if ell != 2)
    return {
        "has_obstruction": has,
        "all_ones_order2_components": all_ones,
        "index_two_argument_premises": (len(all_ones) >= 2
                                        and binary["rank"] == binary["rows"] - 1
                                        and binary["consistent"] and odd_full),
    }


def minimum_cardinality_bound(instance) -> dict:
    """Exact-integer lower bound on the factor count of any Boolean solution:
    n = product of chosen primes satisfies n = 1 (mod Lambda_minus) and n > 1,
    so n >= Lambda_minus + 1; the product of the k largest pool primes bounds
    any k-subset product, and odd cardinality rounds up."""
    primes = sorted((record.p for record in instance.records), reverse=True)
    product, k = 1, 0
    for p in primes:
        if product > instance.lambda_minus:
            break
        product *= p
        k += 1
    if product <= instance.lambda_minus:
        return {"bound": None, "note": "entire pool product does not exceed Lambda_minus"}
    bound = k if k % 2 else k + 1
    return {"product_exceeds_at": k, "odd_minimum_factors": bound}


def verify_saved(path: Path) -> dict:
    """Independent re-verification of a saved bf-harvest report. Re-derives,
    without trusting any stored flag: schema and versioned source provenance;
    every prime certificate and vector encoding; family membership, caps,
    congruences and the exact lexicographic rank of every record; manifest
    contiguity, coverage, counters and stop-reason/completeness consistency;
    all necessary-check ranks, consistency flags and obstruction witnesses
    (via local linear algebra, not the generator's); the recorded structure
    metrics; and the minimum-cardinality bound."""
    report = load_report(path)
    implementation = _verify_provenance(report)
    run = report["run"]
    instance = instance_from_json(run["instance"])
    for record in instance.records:
        verify_prime(record)
    verify_encoding(instance)
    verify_metrics(instance, run["structure"])
    _verify_family_and_records(run, instance)
    _verify_manifest_and_counts(run, len(instance.records)
                                + len(instance.excluded_nonunits))
    checks = _verify_necessary_checks(run, instance)
    bound = minimum_cardinality_bound(instance)
    summary = {
        "records_verified": len(instance.records),
        "encoding_verified": True,
        "metrics_verified": True,
        "provenance": implementation,
        "family_and_ranks_verified": True,
        "manifest_verified": True,
        "necessary_checks_reverified": True,
        "has_obstruction": checks["has_obstruction"],
        "all_ones_order2_components": checks["all_ones_order2_components"],
        "index_two_argument_premises": checks["index_two_argument_premises"],
        "manifest_draws": run["harvest"]["covered_global_indices"],
        "complete_family_scan": run["harvest"]["complete_family_scan"],
        "minimum_cardinality": bound,
    }
    print(f"verify_saved: {summary}", flush=True)
    return summary


def membership_probe(payload: dict) -> dict:
    """Module-level worker for fs_controls.run_limited (spawn-picklable). Runs
    first-wave B's exact membership checker under declared Limits and writes
    the FULL result to payload['result_path'] — a file-backed handoff, because
    a large result through the shared watchdog's queue can deadlock its join
    (the defect reported on PR #8/#9: a ~440 KB certificate pickle makes even
    an instantaneous worker look like a timeout). Only a tiny summary returns
    through the queue."""
    import fs_reachability
    report = load_report(Path(payload["path"]))
    instance = instance_from_json(report["run"]["instance"])
    limits = fs_reachability.Limits(**payload["limits"])
    result = fs_reachability.membership(list(instance.orders),
                                        [list(v) for v in instance.vectors],
                                        list(instance.target), limits=limits)
    data = {
        "status": result.status,
        "coefficients": list(result.coefficients),
        "character_modulus": result.character_modulus,
        "character_terms": [list(term) for term in result.character_terms],
        "reason": result.reason,
        "seconds": result.seconds,
        "work_units": result.work_units,
        "peak_cells": result.peak_cells,
        "workspace_bytes_estimate": result.workspace_bytes_estimate,
    }
    text = json.dumps(data)
    Path(payload["result_path"]).write_text(text)
    return {"status": result.status, "result_bytes": len(text)}


MEMBERSHIP_LIMITS = dict(seconds=290.0, work_units=4_000_000_000,
                         cells=20_000_000, workspace_bytes=1_610_612_736,
                         scalar_bits=4096)


def run_membership_stage(path: Path, wall_seconds: float = 300.0) -> dict:
    """Approved post-scan stage: Limits-bounded Track B membership under the
    portable watchdog, with a file-backed result handoff; any certificate is
    independently re-verified here with fs_reachability.verify_certificate and
    persisted IN FULL so later verification does not depend on this run."""
    import tempfile

    import fs_controls
    import fs_reachability
    with tempfile.TemporaryDirectory() as tmp:
        result_path = Path(tmp) / "membership_result.json"
        kind, value, elapsed = fs_controls.run_limited(
            membership_probe,
            {"path": str(path), "limits": MEMBERSHIP_LIMITS,
             "result_path": str(result_path)},
            wall_seconds)
        stage = {"watchdog": kind, "wall_seconds": round(elapsed, 2),
                 "declared_limits": {**MEMBERSHIP_LIMITS,
                                     "watchdog_wall": wall_seconds},
                 "result_handoff": "file-backed (shared watchdog queue "
                                   "deadlocks on large results)",
                 "scope": fs_reachability.SCOPE}
        if kind == "timeout":
            stage["status"] = "inconclusive"
            stage["reason"] = "watchdog timeout"
            return stage
        if kind != "ok":
            stage["status"] = "worker_error"
            stage["reason"] = ("worker process failed; an implementation "
                               "error, not a budget stop")
            stage["error_detail"] = str(value)
            return stage
        data = json.loads(result_path.read_text())
    result = fs_reachability.MembershipResult(
        status=data["status"],
        coefficients=tuple(data["coefficients"]),
        character_modulus=data["character_modulus"],
        character_terms=tuple(tuple(term) for term in data["character_terms"]),
        reason=data["reason"], seconds=data["seconds"],
        work_units=data["work_units"], peak_cells=data["peak_cells"],
        workspace_bytes_estimate=data["workspace_bytes_estimate"])
    report = load_report(path)
    instance = instance_from_json(report["run"]["instance"])
    fs_reachability.verify_certificate(list(instance.orders),
                                       [list(v) for v in instance.vectors],
                                       list(instance.target), result)
    stage.update(status=result.status, reason=result.reason,
                 independently_verified=True,
                 solver_seconds=result.seconds, work_units=result.work_units,
                 peak_cells=result.peak_cells,
                 workspace_bytes_estimate=result.workspace_bytes_estimate,
                 certificate={
                     "coefficients": list(result.coefficients),
                     "character_modulus": result.character_modulus or None,
                     "character_terms": [list(t) for t in result.character_terms]},
                 nonzero_coefficients=sum(1 for c in result.coefficients if c))
    return stage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--approved", action="store_true",
                        help="assert that the S3 budget proposal was explicitly "
                             "approved; the scan refuses to run without it")
    parser.add_argument("--shards", type=int, default=DEFAULT_SHARDS)
    parser.add_argument("--verify", type=Path, metavar="REPORT",
                        help="independently re-verify a saved bf-harvest report "
                             "and exit")
    parser.add_argument("--membership", type=Path, metavar="REPORT",
                        help="run the Limits-bounded Track B membership stage "
                             "on a saved report and save a side report")
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent.parent
                        / "data" / "generated" / "bf_harvest.json.gz")
    parser.add_argument("--replace", action="store_true",
                        help="explicitly replace the output file")
    args = parser.parse_args()
    if args.verify:
        verify_saved(args.verify)
        return
    if args.membership:
        side = args.membership.parent / "bf_harvest_membership.json"
        if side.exists() and not args.replace:
            parser.error("membership side report exists; use --replace")
        if not args.membership.exists():
            parser.error("membership input report does not exist")
        stage = run_membership_stage(args.membership)
        here = Path(__file__).resolve().parent
        payload = {
            "schema": "bf-harvest-membership/v1",
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "python": platform.python_version(),
            "input_report": str(args.membership),
            "input_sha256": __import__("hashlib").sha256(
                args.membership.read_bytes()).hexdigest(),
            "source_sha256": {name: source_digest(here / name)
                              for name in ("bf_harvest.py", "fs_reachability.py",
                                           "fs_controls.py")},
            "stage": stage,
        }
        side.write_text(json.dumps(payload, indent=2) + "\n")
        print(f"membership stage: {stage.get('status')} "
              f"({stage.get('reason') or 'no reason'}); saved {side}", flush=True)
        return
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
