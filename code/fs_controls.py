"""Track A (feasibility: solver controls): calibration on known-feasible controls.

Plants seeded odd-size controls (supports 3, 5, 9, 17) from the frozen
actual-prime pilot's own vectors, then measures which bounded solvers recover
them: a correctly bounded fixed-cardinality meet-in-the-middle baseline, the
corrected A4 kernel search, the A6 local search, the A6 full-pool MITM, and
the independent residue oracle on small scopes. The real pilot targets are
kept unchanged and run under the same budgets for contrast.

Witness indices are stored only in the experiment records, never passed to a
solver; solver RNG streams are seeded independently of the planting stream.
Timeout/budget outcomes are inconclusive by contract. This module edits no
baseline file and writes only data/generated/fs_controls.json.gz.

Run: python code/fs_controls.py [--output PATH] [--replace]
"""
from itertools import combinations
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import platform
import random
import signal
import subprocess
import time
from typing import Optional, Sequence

import a4_solver
import a6_oddsolver
from real_pool_pilot import necessary_checks, residue_oracle
from real_pool_verify import (
    RealInstance, instance_from_json, source_digest, subset_residues,
    verify_group_solution, verify_saved_report,
)

PLANNING_COMMIT = "4128b62"            # plan recorded on research/harvest-solver-feasibility-plan
PILOT_COMMIT = "6494f89"               # pilot implementation commit (PR #3)
BASELINE_SOURCES = ("real_pool_pilot.py", "real_pool_verify.py", "a4_solver.py",
                    "a6_oddsolver.py", "a7_lohniebuhr.py", "phase1a_calibration.py")

BUDGETS = {
    "wall_seconds_per_solver_call": 60.0,       # enforced with SIGALRM
    "fixed_k_mitm_work_cap": 200_000_000,       # (left+right) enumerations x components
    "fixed_k_mitm_table_cap": 1 << 21,          # stored left combinations
    "a4_kernel_states": 20_000,
    "a6_local_seconds": 15.0,
    "a6_mitm_seconds": 10.0,
    "a6_mitm_scope_cap": 18,
    "oracle_scope_cap": 18,
    "minimum_size": 3,
    "supports": (3, 5, 9, 17),
    "seeds": (101, 202, 303),
}

SCOPES = (("small-complete-family", None),
          ("medium-bounded-sample", None),
          ("medium-complete-family", 18),
          ("medium-complete-family", 44),
          ("medium-complete-family", None))


class _Timeout(Exception):
    pass


def run_limited(seconds: float, fn, *args, **kwargs):
    """Run fn under an enforced wall clock; returns (value, enforced_timeout, elapsed)."""

    def handler(signum, frame):
        raise _Timeout()

    old = signal.signal(signal.SIGALRM, handler)
    signal.setitimer(signal.ITIMER_REAL, seconds)
    start = time.monotonic()
    try:
        value = fn(*args, **kwargs)
        timed_out = False
    except _Timeout:
        value = None
        timed_out = True
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, old)
    return value, timed_out, time.monotonic() - start


def fixed_k_mitm(orders: Sequence[int], pool: Sequence[Sequence[int]],
                 target: Sequence[int], k: int, *, work_cap: int,
                 table_cap: int) -> tuple[Optional[list[int]], str, dict[str, int]]:
    """Exact bounded meet-in-the-middle for subsets of EXACT odd size k >= 3.

    The left table keys are Python hashes of reduced sum tuples; every hash
    match is re-verified by exact componentwise recomputation, so collisions
    cannot produce a wrong answer. 'exhausted' means no size-k subset of this
    pool hits the target; it says nothing about other cardinalities.
    """
    n, d = len(pool), len(orders)
    if k < 3 or k % 2 == 0:
        raise ValueError("controls use odd cardinality at least three")
    counts = {"left": 0, "right": 0, "hash_matches": 0}
    if k > n:
        return None, "cardinality_infeasible", counts
    a = k // 2
    b = k - a
    left_count, right_count = math.comb(n, a), math.comb(n, b)
    if left_count > table_cap or (left_count + right_count) * d > work_cap:
        return None, "resource_limit: declared work cap", counts

    def reduced(combo: Sequence[int]) -> tuple[int, ...]:
        return tuple(sum(pool[i][j] for i in combo) % orders[j] for j in range(d))

    table: dict[int, list[tuple[int, ...]]] = {}
    for combo in combinations(range(n), a):
        counts["left"] += 1
        table.setdefault(hash(reduced(combo)), []).append(combo)
    for combo in combinations(range(n), b):
        counts["right"] += 1
        acc = reduced(combo)
        needed = tuple((target[j] - acc[j]) % orders[j] for j in range(d))
        for candidate in table.get(hash(needed), ()):
            counts["hash_matches"] += 1
            if set(candidate) & set(combo):
                continue
            if reduced(candidate) == needed:
                return sorted(candidate + combo), "ok", counts
    return None, "exhausted", counts


def mod2_rank_nullity(instance: RealInstance, size: int) -> tuple[int, int]:
    """Binary rank/nullity exactly as the pilot's ell=2 check defines them
    (even-order component rows, no parity row; homogeneous system)."""
    rows = instance.vectors[:size]
    masks = []
    for j, order in enumerate(instance.orders):
        if order % 2 == 0:
            masks.append(sum((rows[i][j] & 1) << i for i in range(size)))
    solved = a4_solver.gf2_solve(masks, [0] * len(masks), size)
    if solved is None:
        raise ArithmeticError("homogeneous binary system cannot be inconsistent")
    nullity = len(solved[1])
    return size - nullity, nullity


def classify(instance: RealInstance, indices: Optional[Sequence[int]], message: str,
             target: Sequence[int], residues: tuple[int, int], size: int,
             timed_out: bool, has_obstruction: bool) -> dict[str, object]:
    out: dict[str, object] = {"message": message}
    if timed_out:
        out["status"] = "timeout_enforced"
        return out
    if indices is not None:
        if any(i >= size for i in indices):
            raise ValueError("solver witness outside benchmark scope")
        verify_group_solution(instance, indices, target, residues)
        out.update(status="solution", indices=list(indices),
                   independently_verified=True)
        return out
    if message in ("exhausted", "cardinality_infeasible", "cardinality infeasible"):
        out["status"] = "proved_no_solution"
    elif message == "mod2 inconsistent":
        if not has_obstruction:
            raise ArithmeticError("binary inconsistency lacks an independent certificate")
        out["status"] = "proved_no_solution"
    elif "cap" in message or "too large" in message or "resource" in message:
        out["status"] = "resource_limit"
    else:
        out["status"] = "inconclusive_budget"
    return out


def run_solvers(instance: RealInstance, size: int, target: Sequence[int],
                residues: tuple[int, int], support: Optional[int],
                solver_seed: str, has_obstruction: bool) -> dict[str, object]:
    rows = instance.vectors[:size]
    orders = instance.orders
    wall = BUDGETS["wall_seconds_per_solver_call"]
    results: dict[str, object] = {}

    def record(name: str, value, timed_out: bool, elapsed: float,
               extra: Optional[dict[str, object]] = None) -> None:
        indices, message = (None, "timeout") if timed_out else value
        entry = classify(instance, indices, message, target, residues, size,
                         timed_out, has_obstruction)
        entry["seconds"] = round(elapsed, 3)
        if extra:
            entry.update(extra)
        results[name] = entry

    for k in sorted({3, support} - {None}):
        def mitm_call(k=k):
            indices, message, counts = fixed_k_mitm(
                orders, rows, target, k, work_cap=BUDGETS["fixed_k_mitm_work_cap"],
                table_cap=BUDGETS["fixed_k_mitm_table_cap"])
            return (indices, message), counts

        value, timed_out, elapsed = run_limited(wall, mitm_call)
        pair, counts = value if value is not None else ((None, "timeout"), {})
        record(f"fixed_k_mitm_k{k}", pair, timed_out, elapsed,
               {"exact_cardinality": k, "scope": "size-k subsets of this pool only",
                "counts": counts})
        entry = results[f"fixed_k_mitm_k{k}"]
        if entry["status"] == "proved_no_solution":
            entry["status"] = "proved_no_solution_exact_cardinality"

    def a4_call():
        bits, message = a4_solver.full_solve(
            rows, orders, target, size, random.Random(f"{solver_seed}/a4"),
            budget=BUDGETS["a4_kernel_states"], min_size=BUDGETS["minimum_size"])
        indices = [i for i in range(size) if bits >> i & 1] if bits is not None else None
        return indices, message

    value, timed_out, elapsed = run_limited(wall, a4_call)
    record("a4_kernel", value if value is not None else (None, "timeout"),
           timed_out, elapsed, {"budget_states": BUDGETS["a4_kernel_states"]})

    def a6_call():
        comps = [(next(iter(a4_solver.prime_power_factors(order))), order)
                 for order in orders]
        bits, message = a6_oddsolver.solve(
            comps, orders, rows, target, size, random.Random(f"{solver_seed}/a6"),
            BUDGETS["a6_local_seconds"], min_size=BUDGETS["minimum_size"])
        indices = [i for i in range(size) if bits >> i & 1] if bits is not None else None
        return indices, message

    value, timed_out, elapsed = run_limited(wall, a6_call)
    record("a6_local", value if value is not None else (None, "timeout"),
           timed_out, elapsed, {"time_budget_seconds": BUDGETS["a6_local_seconds"]})

    if size <= BUDGETS["a6_mitm_scope_cap"]:
        def a6_mitm_call():
            bits, message = a6_oddsolver.mitm_frontier(
                orders, rows, target, size, BUDGETS["a6_mitm_seconds"],
                min_size=BUDGETS["minimum_size"])
            indices = [i for i in range(size) if bits >> i & 1] if bits is not None else None
            return indices, message

        value, timed_out, elapsed = run_limited(wall, a6_mitm_call)
        record("a6_mitm", value if value is not None else (None, "timeout"),
               timed_out, elapsed)
    else:
        results["a6_mitm"] = {"status": "resource_limit",
                              "message": "declared scope cap", "seconds": 0.0}

    if size <= BUDGETS["oracle_scope_cap"]:
        def oracle_call():
            outcome = residue_oracle(instance, size, residues)
            return outcome.get("indices"), outcome["status"]

        value, timed_out, elapsed = run_limited(wall, oracle_call)
        indices, status = value if value is not None else (None, "timeout")
        if indices is not None:
            verify_group_solution(instance, indices, target, residues)
        results["independent_residue_oracle"] = {
            "status": "timeout_enforced" if timed_out else status,
            "indices": list(indices) if indices is not None else None,
            "seconds": round(elapsed, 3),
            "role": "independent oracle; searches any odd cardinality >= 3",
        }
    return results


def experiment(instance: RealInstance, cohort: str, size: int,
               support: Optional[int], seed: Optional[int]) -> dict[str, object]:
    rows = instance.vectors[:size]
    planted = support is not None
    if planted:
        witness_rng = random.Random(f"fs-controls-witness/{cohort}/{size}/{support}/{seed}")
        witness = sorted(witness_rng.sample(range(size), support))
        target = tuple(sum(rows[i][j] for i in witness) % order
                       for j, order in enumerate(instance.orders))
        residues = subset_residues(instance.records, witness,
                                   instance.lambda_minus, instance.lambda_plus)
        verify_group_solution(instance, witness, target, residues)
    else:
        witness = None
        target = instance.target
        residues = (1, instance.lambda_plus - 1)
    checks = necessary_checks(instance.orders, rows, target)
    solver_seed = f"fs-controls-solver/{cohort}/{size}/{support}/{seed}"
    solvers = run_solvers(instance, size, target, residues, support, solver_seed,
                          bool(checks["has_obstruction"]))
    if planted:
        for name in ("a6_mitm", "a4_kernel", "a6_local"):
            if solvers.get(name, {}).get("status") == "proved_no_solution":
                raise ArithmeticError(f"{name} negative claim contradicts planted witness")
        oracle = solvers.get("independent_residue_oracle", {})
        if oracle.get("status") == "proved_no_solution":
            raise ArithmeticError("oracle negative claim contradicts planted witness")
    rank, nullity = mod2_rank_nullity(instance, size)
    record: dict[str, object] = {
        "cohort": cohort, "scope_size": size,
        "scope": "first sorted retained primes; full parent LCMs unchanged",
        "target_kind": "planted_control" if planted else "real_lp",
        "support": support, "planting_seed_label": seed,
        "planted_witness_indices": witness,
        "mod2_rank": rank, "mod2_nullity": nullity,
        "group_bits": round(sum(math.log2(order) for order in instance.orders), 2),
        "components": len(instance.orders),
        "has_necessary_obstruction": bool(checks["has_obstruction"]),
        "residues_hex": [hex(value) for value in residues],
        "solvers": solvers,
    }
    if planted:
        recovered = any(entry.get("status") == "solution"
                        for entry in solvers.values())
        exact = any(entry.get("indices") == witness for entry in solvers.values()
                    if isinstance(entry, dict))
        record["any_solver_solved"] = recovered
        record["planted_witness_recovered_exactly"] = exact
    return record


def load_pilot(path: Path) -> tuple[dict[str, RealInstance], dict[str, object], str]:
    payload = path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    data = json.loads(gzip.decompress(payload).decode("utf-8"))
    start = time.monotonic()
    summary = verify_saved_report(data)
    summary["verification_seconds"] = round(time.monotonic() - start, 1)
    instances = {run["name"]: instance_from_json(run["instance"])
                 for run in data["runs"] if run["status"] == "encoded_and_verified"}
    return instances, summary, digest


def git_head() -> Optional[str]:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], capture_output=True,
                              text=True, check=True,
                              cwd=Path(__file__).resolve().parent).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return None


def run_track_a(pilot_path: Path) -> dict[str, object]:
    instances, verification, input_digest = load_pilot(pilot_path)
    experiments = []
    for cohort, scope in SCOPES:
        instance = instances[cohort]
        size = len(instance.records) if scope is None else scope
        if size > len(instance.records):
            continue
        for support in BUDGETS["supports"]:
            if support >= size:
                continue
            for seed in BUDGETS["seeds"]:
                experiments.append(experiment(instance, cohort, size, support, seed))
                last = experiments[-1]
                print(f"{cohort}[:{size}] support={support} seed={seed}: "
                      f"solved={last['any_solver_solved']}", flush=True)
        experiments.append(experiment(instance, cohort, size, None, None))
        print(f"{cohort}[:{size}] real target done", flush=True)
    here = Path(__file__).resolve().parent
    return {
        "schema": "fs-controls/v1",
        "track": "A: solver controls (research/feasibility-solver-controls)",
        "plan_commit": PLANNING_COMMIT, "pilot_commit": PILOT_COMMIT,
        "working_commit": git_head(),
        "python": platform.python_version(),
        "source_hash_normalization": "CRLF-to-LF",
        "source_sha256": {name: source_digest(here / name)
                          for name in BASELINE_SOURCES + ("fs_controls.py",)},
        "input_artifact": {"path": "data/generated/real_pool_pilot.json.gz",
                           "sha256": input_digest},
        "pilot_verification_summary": verification,
        "budgets": {key: list(value) if isinstance(value, tuple) else value
                    for key, value in BUDGETS.items()},
        "witness_isolation": "witnesses live only in experiment records; solver "
                             "RNG streams are seeded from a separate label",
        "experiments": experiments,
        "limits": [
            "Timeouts, declared caps and budget exhaustion are inconclusive.",
            "fixed_k_mitm 'exhausted' covers exactly-size-k subsets of the stated scope only.",
            "Prefix scopes retain full parent LCMs; results do not transfer to re-harvested moduli.",
            "Planted-control success is calibration, not evidence about the real targets.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    root = Path(__file__).resolve().parent.parent
    parser.add_argument("--pilot", type=Path,
                        default=root / "data" / "generated" / "real_pool_pilot.json.gz")
    parser.add_argument("--output", type=Path,
                        default=root / "data" / "generated" / "fs_controls.json.gz")
    parser.add_argument("--replace", action="store_true",
                        help="explicitly replace the output file")
    args = parser.parse_args()
    if args.output.exists() and not args.replace:
        parser.error("output already exists; use --replace or choose another path")
    report = run_track_a(args.pilot)
    payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(gzip.compress(payload, mtime=0))
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
