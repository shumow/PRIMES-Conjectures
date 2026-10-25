"""S1 information-set prototype: bounded odd-subset recovery without a support hint."""
from dataclasses import asdict, dataclass, replace
from itertools import combinations
from typing import Optional
import math
import random
import time

import a4_solver
import bf_solver as baseline
import bf_solver_preprocessing as previous


@dataclass(frozen=True)
class Limits:
    seconds: float = 60.0
    memory_mib: int = 512
    permutations: int = 8
    free_weight: int = 3
    states: int = 1_000_000
    selection_cap: int = 17
    candidates: int = 10_000
    solver_seed: int = 1729

    def __post_init__(self) -> None:
        baseline.Limits(self.seconds, self.memory_mib)
        for name in ("permutations", "free_weight", "states", "selection_cap",
                     "candidates", "solver_seed"):
            if not baseline._integer(getattr(self, name)):
                raise ValueError("information-set limits must be integers")
        if not 1 <= self.permutations <= 8 or not 0 <= self.free_weight <= 3 \
                or not 1 <= self.states <= 1_000_000 or not 3 <= self.selection_cap <= 17 \
                or not 1 <= self.candidates <= 10_000 or not 0 <= self.solver_seed < 2**31:
            raise ValueError("information-set limits exceed the declared round envelope")


@dataclass(frozen=True)
class Result:
    status: str
    indices: tuple[int, ...] = ()
    reason: str = ""
    permutations: int = 0
    states: int = 0
    candidates: int = 0
    projection_seconds: float = 0.0
    elimination_seconds: float = 0.0
    search_seconds: float = 0.0
    wall_seconds: float = 0.0
    verification_seconds: float = 0.0
    peak_rss_bytes: Optional[int] = None
    memory_measurement: str = "not returned by worker"


def affine_masks(particular: int, kernel: list[int], max_weight: int):
    """Exact XOR of selection masks, not an additive residual approximation."""
    for weight in range(min(len(kernel), max_weight) + 1):
        for chosen in combinations(kernel, weight):
            mask = particular
            for vector in chosen:
                mask ^= vector
            yield mask


def _work(payload: tuple[baseline.Problem, Limits, float]) -> Result:
    problem, limits, deadline = payload
    started = time.monotonic()
    columns, target = previous.binary_syndromes(problem)
    rows = [sum(((column >> j) & 1) << i for i, column in enumerate(columns))
            for j in range(target.bit_length())]
    rhs = [(target >> j) & 1 for j in range(len(rows))]
    projection_seconds = time.monotonic() - started
    elimination_seconds = 0.0
    count = states = candidates = 0
    checked_masks: set[int] = set()
    rng = random.Random(limits.solver_seed)
    search_started = time.monotonic()

    def finish(status: str, indices: tuple[int, ...] = (), reason: str = "") -> Result:
        peak, method = baseline._peak_rss()
        return Result(status, indices, reason, count, states, candidates,
                      projection_seconds, elimination_seconds,
                      max(0.0, time.monotonic() - search_started - elimination_seconds),
                      peak_rss_bytes=peak, memory_measurement=method)

    for iteration in range(limits.permutations):
        if time.monotonic() >= deadline:
            return finish("timeout_enforced", reason="information-set deadline")
        permutation = list(range(len(columns)))
        if iteration:
            rng.shuffle(permutation)
        elimination_started = time.monotonic()
        permuted = [sum(((row >> original) & 1) << new
                        for new, original in enumerate(permutation)) for row in rows]
        solution = a4_solver.gf2_solve(permuted, rhs, len(columns))
        elimination_seconds += time.monotonic() - elimination_started
        count += 1
        if solution is None:
            return finish("projection_inconsistent",
                          reason="binary diagnostic only; no independent character emitted")
        particular, kernel = solution
        for mask in affine_masks(particular, kernel, limits.free_weight):
            if states >= limits.states:
                return finish("inconclusive", reason="declared affine-state cap")
            if states % 256 == 0 and time.monotonic() >= deadline:
                return finish("timeout_enforced", reason="affine enumeration deadline")
            states += 1
            size = bin(mask).count("1")
            if size < problem.min_size or size > limits.selection_cap or size % 2 == 0:
                continue
            indices = tuple(sorted(permutation[i] for i in previous._indices(mask)))
            original_mask = sum(1 << i for i in indices)
            if original_mask in checked_masks:
                continue
            if candidates >= limits.candidates:
                return finish("resource_limit", reason="full-target candidate-check cap")
            checked_masks.add(original_mask)
            candidates += 1
            if all(sum(problem.vectors[i][j] for i in indices) % order == problem.target[j]
                   for j, order in enumerate(problem.orders)):
                return finish("solution", indices)
    return finish("inconclusive",
                  reason="declared information sets/free weights/selection envelope exhausted")


def solve(problem: baseline.Problem, limits: Limits = Limits()) -> Result:
    """Support-blind interface; failure never means unrestricted nonexistence."""
    if problem.exact_size is not None:
        raise ValueError("information-set worker must not receive an exact-support hint")
    started = time.monotonic()

    def finish(result: Result) -> Result:
        checked = time.monotonic()
        if result.status not in ("solution", "inconclusive", "projection_inconsistent",
                                 "resource_limit", "timeout_enforced", "worker_error"):
            raise ValueError("unknown information-set outcome")
        if result.status == "solution":
            if result.reason:
                raise ValueError("solution cannot carry a failure reason")
            baseline.verify_subset(problem, result.indices)
            if len(result.indices) > limits.selection_cap:
                raise ValueError("candidate exceeds the algorithmic selection envelope")
        elif result.indices or not result.reason:
            raise ValueError("non-solution must have an explicit reason and no subset")
        elapsed = time.monotonic() - started
        if result.status == "solution" and elapsed >= limits.seconds:
            return replace(result, status="timeout_enforced", indices=(), reason="late candidate",
                           wall_seconds=elapsed)
        return replace(result, wall_seconds=elapsed,
                       verification_seconds=time.monotonic() - checked)

    if limits.seconds == 0:
        return finish(Result("timeout_enforced", reason="zero wall budget"))
    if len(problem.orders) * len(problem.vectors) > baseline.MAX_ENTRIES:
        return finish(Result("resource_limit", reason="matrix-entry guard"))
    if problem.min_size > limits.selection_cap:
        return finish(Result("inconclusive", reason="minimum exceeds algorithmic selection cap"))
    remaining = limits.seconds - (time.monotonic() - started)
    if remaining <= 0:
        return finish(Result("timeout_enforced", reason="preflight deadline"))
    kind, value, _ = baseline.run_limited(_work, (problem, limits, started + limits.seconds),
                                         remaining)
    if kind == "timeout":
        return finish(Result("timeout_enforced", reason="external spawn watchdog"))
    if kind == "worker_error":
        return finish(Result("worker_error", reason=str(value)))
    if kind != "ok" or not isinstance(value, Result):
        raise TypeError("invalid information-set worker protocol")
    if value.peak_rss_bytes is not None and value.peak_rss_bytes > limits.memory_mib * 1024**2:
        return finish(replace(value, status="resource_limit", indices=(),
                              reason="observed worker RSS exceeds target"))
    if time.monotonic() - started >= limits.seconds:
        return finish(replace(value, status="timeout_enforced", indices=(),
                              reason="worker returned after deadline"))
    return finish(value)


def case_specs() -> tuple[baseline.CaseSpec, ...]:
    specs = []
    for phase, support, holdout, seeds in (
            (0, 3, False, (101, 202, 303)),
            (1, 5, False, (101, 202, 303)),
            (1, 5, True, (32452843, 49979687, 67867967)),
            (2, 9, False, (101, 202, 303)),
            (3, 17, False, (101, 202, 303)),
            (3, 17, True, (86028121, 104395301, 122949829))):
        for seed in seeds:
            name = f"{'holdout' if holdout else 'dev'}-k{support}-{seed}-odd"
            specs.append(baseline.CaseSpec(name, phase, support, seed, holdout, False))
    return tuple(specs)


def protocol() -> dict[str, object]:
    return {
        "algorithm": "bounded information-set search over exact binary affine masks",
        "limits": asdict(Limits()), "max_calls": 18, "aggregate_call_seconds": 1080,
        "cases": [asdict(spec) for spec in case_specs()],
        "support_input": "None; control support/planting metadata stays in parent",
        "selection_envelope": "odd sizes from minimum through 17; not unrestricted completeness",
        "permutation_schedule": "identity followed by seven independent fixed-seed shuffles",
        "fresh_holdouts": "six new seeds; bf-solver-holdout/20261024/<seed> planting labels",
        "gates": "all prior-phase controls must solve before the next phase",
        "scope": "full frozen 483-prime pilot, original parent LCMs; no real-target calls",
        "memory_scope": "completed-worker measured target, not OS-enforced RSS",
    }


if __name__ == "__main__":
    import argparse
    import hashlib
    import json

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--protocol", action="store_true")
    args = parser.parse_args()
    if not args.protocol:
        parser.error("prototype only; use --protocol, not an unregistered full-pool run")
    declared = protocol()
    digest = hashlib.sha256(json.dumps(declared, sort_keys=True).encode("utf-8")).hexdigest()
    print(json.dumps({"protocol": declared, "sha256": digest}, indent=2))
