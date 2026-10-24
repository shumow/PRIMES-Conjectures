"""Track A (feasibility: solver controls): calibration on known-feasible controls.

Plants seeded odd-size controls (supports 3, 5, 9, 17) from the frozen
actual-prime pilot's own vectors, then measures which bounded solvers recover
them: a correctly bounded fixed-cardinality meet-in-the-middle baseline, the
corrected A4 kernel search, the A6 local search, the A6 full-pool MITM, and
the independent residue oracle on small scopes. The real pilot targets are
kept unchanged and run under the same budgets for contrast.

Every solver call runs in a spawned worker process under a portable enforced
wall clock (terminated at the deadline) -- one worker at a time, a watchdog,
not parallelism -- so timeout enforcement behaves identically on POSIX and
Windows. Worker exceptions are classified as worker_error, never silently
swallowed. Reported seconds include child-process startup.

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
import multiprocessing
import platform
import queue as queue_module
import random
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
    "wall_seconds_per_solver_call": 60.0,       # enforced by process watchdog
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


def _worker_entry(fn, payload, out_queue):
    """Child-process entry: run fn(payload), report success or a classified error."""
    try:
        out_queue.put(("ok", fn(payload)))
    except Exception as exc:                      # classified, never silent
        out_queue.put(("worker_error", f"{type(exc).__name__}: {exc}"))


def run_limited(fn, payload, seconds):
    """Portable enforced wall clock: run a module-level callable in a spawned
    worker process and terminate it at the deadline. One worker at a time (a
    watchdog, not parallelism). Returns (kind, value, elapsed) with kind in
    {"ok", "timeout", "worker_error"}; elapsed includes child startup.
    """
    ctx = multiprocessing.get_context("spawn")
    out_queue = ctx.Queue()
    process = ctx.Process(target=_worker_entry, args=(fn, payload, out_queue),
                          daemon=True)
    start = time.monotonic()
    process.start()
    process.join(seconds)
    if process.is_alive():
        process.terminate()
        process.join(5)
        if process.is_alive():
            process.kill()
            process.join()
        return "timeout", None, time.monotonic() - start
    elapsed = time.monotonic() - start
    try:
        kind, value = out_queue.get(timeout=5)
    except queue_module.Empty:
        kind, value = "worker_error", f"no result returned (exit code {process.exitcode})"
    out_queue.close()
    return kind, value, elapsed


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


def classify(instance: RealInstance, kind: str, indices: Optional[Sequence[int]],
             message: str, target: Sequence[int], residues: tuple[int, int],
             size: int, has_obstruction: bool) -> dict[str, object]:
    out: dict[str, object] = {"message": message}
    if kind == "timeout":
        out["status"] = "timeout_enforced"
        out["message"] = "enforced wall clock"
        return out
    if kind == "worker_error":
        out["status"] = "worker_error"
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


# ---- module-level solver workers (picklable for the spawn watchdog) ----

def _work_fixed_k(payload):
    orders, rows, target, k, work_cap, table_cap = payload
    indices, message, counts = fixed_k_mitm(orders, rows, target, k,
                                            work_cap=work_cap, table_cap=table_cap)
    return indices, message, {"counts": counts}


def _work_a4(payload):
    rows, orders, target, size, seed, budget, min_size = payload
    bits, message = a4_solver.full_solve(rows, orders, target, size,
                                         random.Random(seed), budget=budget,
                                         min_size=min_size)
    indices = [i for i in range(size) if bits >> i & 1] if bits is not None else None
    return indices, message, {}


def _work_a6_local(payload):
    rows, orders, target, size, seed, seconds, min_size = payload
    comps = [(next(iter(a4_solver.prime_power_factors(order))), order)
             for order in orders]
    bits, message = a6_oddsolver.solve(comps, orders, rows, target, size,
                                       random.Random(seed), seconds,
                                       min_size=min_size)
    indices = [i for i in range(size) if bits >> i & 1] if bits is not None else None
    return indices, message, {}


def _work_a6_mitm(payload):
    rows, orders, target, size, seconds, min_size = payload
    bits, message = a6_oddsolver.mitm_frontier(orders, rows, target, size,
                                               seconds, min_size=min_size)
    indices = [i for i in range(size) if bits >> i & 1] if bits is not None else None
    return indices, message, {}


def _work_oracle(payload):
    instance, size, residues = payload
    outcome = residue_oracle(instance, size, residues)
    return outcome.get("indices"), outcome["status"], {}


def run_solvers(instance: RealInstance, size: int, target: Sequence[int],
                residues: tuple[int, int], support: Optional[int],
                solver_seed: str, has_obstruction: bool) -> dict[str, object]:
    rows = instance.vectors[:size]
    orders = instance.orders
    wall = BUDGETS["wall_seconds_per_solver_call"]
    results: dict[str, object] = {}

    def record(name: str, fn, payload,
               extra: Optional[dict[str, object]] = None) -> dict[str, object]:
        kind, value, elapsed = run_limited(fn, payload, wall)
        if kind == "ok":
            indices, message, more = value
        else:
            indices, message, more = None, value if kind == "worker_error" else "", {}
        entry = classify(instance, kind, indices, str(message), target, residues,
                         size, has_obstruction)
        entry["seconds"] = round(elapsed, 3)
        for source in (more, extra or {}):
            entry.update(source)
        results[name] = entry
        return entry

    for k in sorted({3, support} - {None}):
        entry = record(f"fixed_k_mitm_k{k}", _work_fixed_k,
                       (orders, rows, target, k, BUDGETS["fixed_k_mitm_work_cap"],
                        BUDGETS["fixed_k_mitm_table_cap"]),
                       {"exact_cardinality": k,
                        "scope": "size-k subsets of this pool only"})
        if entry["status"] == "proved_no_solution":
            entry["status"] = "proved_no_solution_exact_cardinality"

    record("a4_kernel", _work_a4,
           (rows, orders, target, size, f"{solver_seed}/a4",
            BUDGETS["a4_kernel_states"], BUDGETS["minimum_size"]),
           {"budget_states": BUDGETS["a4_kernel_states"]})

    record("a6_local", _work_a6_local,
           (rows, orders, target, size, f"{solver_seed}/a6",
            BUDGETS["a6_local_seconds"], BUDGETS["minimum_size"]),
           {"time_budget_seconds": BUDGETS["a6_local_seconds"]})

    if size <= BUDGETS["a6_mitm_scope_cap"]:
        record("a6_mitm", _work_a6_mitm,
               (rows, orders, target, size, BUDGETS["a6_mitm_seconds"],
                BUDGETS["minimum_size"]))
    else:
        results["a6_mitm"] = {"status": "resource_limit",
                              "message": "declared scope cap", "seconds": 0.0}

    if size <= BUDGETS["oracle_scope_cap"]:
        entry = record("independent_residue_oracle", _work_oracle,
                       (instance, size, residues))
        if entry["status"] == "inconclusive_budget" and entry["message"] in (
                "proved_no_solution",):
            entry["status"] = "proved_no_solution"
        entry["role"] = "independent oracle; searches any odd cardinality >= 3"
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
        "schema": "fs-controls/v1.1",
        "schema_changes": "v1.1: portable multiprocessing watchdog (all platforms), worker_error status, timings include child startup; fields otherwise as v1",
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
        "watchdog": "spawned worker process per solver call, terminated at the "
                    "deadline; sequential (one worker at a time)",
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
