"""S1 support-blind information-set search, frozen pilot runner and direct checker."""
from dataclasses import asdict, dataclass, replace
from datetime import datetime, timezone
from itertools import combinations
from pathlib import Path
from typing import Optional
import argparse
import gzip
import hashlib
import json
import math
import platform
import random
import subprocess
import time

import a4_solver
import bf_solver as baseline
import bf_solver_preprocessing as previous
from real_pool_verify import RealInstance, source_digest, verify_group_solution

SCHEMA = "bf-solver-information-sets/v1"
STARTING_COMMIT = "e0b946daaa10e5d3d9422b2943e1ccba218eaae6"
DECLARED_PROTOCOL_SHA256 = "a2ba7c982dc1ea5294a18169cc8a382f41d079163f881ab3fb27cb91f65765b7"
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUTPUT = baseline.DEFAULT_INPUT.with_name("bf_solver_information_sets.json.gz")
PHASE_COUNTS = (3, 6, 3, 6)
CASE_FIELDS = {"phase", "case", "result", "not_run_reason",
               "residue_verification_seconds", "returned_cardinality",
               "planted_witness_recovered"}
RESULT_STATUSES = {"solution", "inconclusive", "projection_inconsistent",
                   "resource_limit", "timeout_enforced", "worker_error"}
ABORT_STATUSES = {"worker_error": "aborted_worker_error",
                  "projection_inconsistent": "aborted_projection_contradiction"}


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


def _canonical(value: object) -> str:
    return json.dumps(value, sort_keys=True)


def protocol_hash() -> str:
    digest = hashlib.sha256(_canonical(protocol()).encode("utf-8")).hexdigest()
    if digest != DECLARED_PROTOCOL_SHA256:
        raise ValueError("the previously declared protocol changed")
    return digest


def sources() -> dict[str, str]:
    return {**previous.sources(),
            "bf_solver_information_sets.py": source_digest(Path(__file__))}


def _load_context() -> tuple[RealInstance, tuple[baseline.Control, ...], dict[str, str]]:
    instance, prior_controls, prior_inputs = baseline._context(
        baseline.DEFAULT_INPUT, baseline.CONTROL_INPUT)
    round1 = baseline.DEFAULT_INPUT.with_name("bf_solver.json.gz").read_bytes()
    round2 = baseline.DEFAULT_INPUT.with_name("bf_solver_preprocessing.json.gz").read_bytes()
    if hashlib.sha256(round1).hexdigest() != previous.ROUND1_SHA256 \
            or hashlib.sha256(round2).hexdigest() != \
            "d100e499dfa7c6b3ae5b2cac7ff67e00ed46dea08e6078693cf0671fdfbb2e1a":
        raise ValueError("a frozen earlier S1 artifact changed")
    expected = json.loads(gzip.decompress(round2))["inputs"]
    if any(prior_inputs[key] != expected[key] for key in ("pilot_sha256", "controls_sha256")):
        raise ValueError("pilot/control inputs differ from the frozen preceding round")
    development = {(c.spec.support, c.spec.seed): c for c in prior_controls if not c.spec.holdout}
    controls = []
    for spec in case_specs():
        if spec.holdout:
            control = baseline._control(instance, spec)
        else:
            control = replace(development[(spec.support, spec.seed)], spec=spec)
        problem = replace(control.problem, vectors=instance.vectors, exact_size=None)
        controls.append(replace(control, problem=problem))
    return instance, tuple(controls), {
        "pilot_sha256": prior_inputs["pilot_sha256"],
        "controls_sha256": prior_inputs["controls_sha256"],
        "round1_sha256": hashlib.sha256(round1).hexdigest(),
        "round2_sha256": hashlib.sha256(round2).hexdigest(),
    }


def _scope(instance: RealInstance) -> dict[str, object]:
    return {"cohort": "medium-complete-family", "records": len(instance.records),
            "components": len(instance.orders),
            "parent_lcms_hex": [hex(instance.lambda_minus), hex(instance.lambda_plus)],
            "cardinality_mode": "general_odd_minimum_3_no_exact_hint"}


def _frozen_head(git: str) -> str:
    head = previous._implementation_head(git)
    name = "code/bf_solver_information_sets.py"
    committed = subprocess.check_output([git, "-C", str(ROOT), "show", f"{head}:{name}"])
    if committed.replace(b"\r\n", b"\n") != (ROOT / name).read_bytes().replace(b"\r\n", b"\n"):
        raise ValueError("commit the information-set runner and protocol before evaluating controls")
    protocol_hash()
    return head


def _phase_passed(records: list[dict], phase: int) -> bool:
    selected = [record for record in records if record["phase"] == phase]
    return len(selected) == PHASE_COUNTS[phase] and all(
        isinstance(record["result"], dict) and record["result"]["status"] == "solution"
        for record in selected)


def _eligible(records: list[dict], phase: int) -> bool:
    return all(_phase_passed(records, earlier) for earlier in range(phase))


def run_pilot(git: str) -> dict[str, object]:
    """Run only the preregistered batch; all control metadata stays in this parent."""
    head = _frozen_head(git)
    frozen_sources = sources()
    started = time.monotonic()
    instance, controls, inputs = _load_context()
    preparation_seconds = time.monotonic() - started
    records: list[dict] = []
    abort = ""
    for control in controls:
        entry = {
            "phase": control.spec.phase, "case": baseline._case_json(control),
            "result": None, "not_run_reason": "",
            "residue_verification_seconds": None, "returned_cardinality": None,
            "planted_witness_recovered": None,
        }
        if abort:
            entry["not_run_reason"] = abort
        elif not _eligible(records, control.spec.phase):
            entry["not_run_reason"] = "prior-phase control gate did not pass"
        else:
            result = solve(control.problem)
            if result.status == "solution":
                check_started = time.monotonic()
                verify_group_solution(instance, result.indices, control.problem.target,
                                      control.residues)
                entry["residue_verification_seconds"] = time.monotonic() - check_started
                entry["returned_cardinality"] = len(result.indices)
                entry["planted_witness_recovered"] = tuple(sorted(result.indices)) == control.witness
            entry["result"] = asdict(result)
            abort = ABORT_STATUSES.get(result.status, "")
            print(f"{control.spec.name}: {result.status} ({result.wall_seconds:.3f}s, "
                  f"{result.states} states, {result.candidates} candidate checks)"
                  + (f" - {result.reason}" if result.reason else ""), flush=True)
        records.append(entry)
    if _frozen_head(git) != head or sources() != frozen_sources:
        raise ValueError("implementation commit or source changed during the pilot")
    return {
        "schema": SCHEMA, "starting_commit": STARTING_COMMIT,
        "implementation_commit": head,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "platform": platform.platform(),
        "source_hash_normalization": "CRLF-to-LF", "source_sha256": frozen_sources,
        "protocol": protocol(), "protocol_sha256": protocol_hash(), "inputs": inputs,
        "scope": _scope(instance), "preparation_seconds": preparation_seconds,
        "run_status": abort or "completed_protocol", "cases": records,
        "counterexamples": 0,
    }


def _nonnegative_time(value: object) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) \
        and math.isfinite(value) and value >= 0


def _read_result(value: object) -> Result:
    if not isinstance(value, dict) or set(value) != set(Result.__dataclass_fields__):
        raise ValueError("malformed information-set result")
    if value["status"] not in RESULT_STATUSES or not isinstance(value["reason"], str) \
            or not isinstance(value["memory_measurement"], str):
        raise ValueError("invalid information-set outcome")
    indices = value["indices"]
    if not isinstance(indices, (list, tuple)) or any(not baseline._integer(i) for i in indices):
        raise ValueError("invalid saved subset indices")
    limits = Limits()
    for field, cap in (("permutations", limits.permutations), ("states", limits.states),
                       ("candidates", limits.candidates)):
        if not baseline._integer(value[field]) or not 0 <= value[field] <= cap:
            raise ValueError("invalid or out-of-budget search counters")
    if value["candidates"] > value["states"] or (value["states"] and not value["permutations"]):
        raise ValueError("contradictory search counters")
    for field in ("projection_seconds", "elimination_seconds", "search_seconds",
                  "wall_seconds", "verification_seconds"):
        if not _nonnegative_time(value[field]):
            raise ValueError("invalid saved timing")
    if sum(value[key] for key in ("projection_seconds", "elimination_seconds", "search_seconds",
                                 "verification_seconds")) > value["wall_seconds"] + 0.001:
        raise ValueError("component timings exceed the end-to-end call time")
    peak = value["peak_rss_bytes"]
    if peak is not None and (not baseline._integer(peak) or peak < 0):
        raise ValueError("invalid saved RSS measurement")
    return Result(**{**value, "indices": tuple(indices)})


def verify_report(value: object) -> dict[str, object]:
    """Check scope, gates and direct witnesses without calling any search producer."""
    fields = {"schema", "starting_commit", "implementation_commit", "generated_at_utc",
              "python", "platform", "source_hash_normalization", "source_sha256",
              "protocol", "protocol_sha256", "inputs", "scope", "preparation_seconds",
              "run_status", "cases", "counterexamples"}
    if not isinstance(value, dict) or set(value) != fields:
        raise ValueError("unknown information-set report shape")
    if value["schema"] != SCHEMA or value["starting_commit"] != STARTING_COMMIT \
            or _canonical(value["protocol"]) != _canonical(protocol()) \
            or value["protocol_sha256"] != protocol_hash() \
            or value["source_sha256"] != sources() \
            or value["source_hash_normalization"] != "CRLF-to-LF":
        raise ValueError("information-set protocol/source provenance differs")
    head = value["implementation_commit"]
    if not isinstance(head, str) or len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise ValueError("invalid implementation commit")
    if any(not isinstance(value[key], str) or not value[key]
           for key in ("generated_at_utc", "python", "platform")) \
            or not _nonnegative_time(value["preparation_seconds"]):
        raise ValueError("invalid execution metadata")
    instance, controls, inputs = _load_context()
    if value["inputs"] != inputs or value["scope"] != _scope(instance) \
            or type(value["counterexamples"]) is not int or value["counterexamples"] != 0:
        raise ValueError("information-set input/target scope differs")
    if not isinstance(value["cases"], list) or len(value["cases"]) != len(controls):
        raise ValueError("missing or repeated control case")
    checked: list[dict] = []
    abort = ""
    calls = solutions = not_run = errors = without_rss = 0
    for entry, control in zip(value["cases"], controls):
        if not isinstance(entry, dict) or set(entry) != CASE_FIELDS \
                or not baseline._integer(entry["phase"]) or entry["phase"] != control.spec.phase \
                or not isinstance(entry["not_run_reason"], str) \
                or _canonical(entry["case"]) != _canonical(baseline._case_json(control)):
            raise ValueError("control definition, order or cardinality mode differs")
        if control.problem.exact_size is not None:
            raise ValueError("validated control leaked an exact-support hint")
        skipped = abort or ("" if _eligible(checked, control.spec.phase)
                            else "prior-phase control gate did not pass")
        if skipped:
            if entry["result"] is not None or entry["not_run_reason"] != skipped \
                    or any(entry[key] is not None for key in (
                        "returned_cardinality", "planted_witness_recovered",
                        "residue_verification_seconds")):
                raise ValueError("unrun case violates abort or phase gating")
            not_run += 1
        else:
            if entry["not_run_reason"]:
                raise ValueError("eligible case was not run")
            result = _read_result(entry["result"])
            calls += 1
            if result.status == "solution":
                if result.reason or not result.candidates \
                        or result.wall_seconds >= Limits().seconds \
                        or len(result.indices) > Limits().selection_cap \
                        or (result.peak_rss_bytes is not None
                            and result.peak_rss_bytes > Limits().memory_mib * 1024**2):
                    raise ValueError("out-of-envelope result classified as a solution")
                baseline.verify_subset(control.problem, result.indices)
                verify_group_solution(instance, result.indices, control.problem.target,
                                      control.residues)
                if not baseline._integer(entry["returned_cardinality"]) \
                        or entry["returned_cardinality"] != len(result.indices) \
                        or entry["planted_witness_recovered"] is not \
                        (tuple(sorted(result.indices)) == control.witness) \
                        or not _nonnegative_time(entry["residue_verification_seconds"]):
                    raise ValueError("candidate verification annotations differ")
                solutions += 1
                without_rss += result.peak_rss_bytes is None
            else:
                if result.indices or not result.reason or any(entry[key] is not None for key in (
                        "returned_cardinality", "planted_witness_recovered",
                        "residue_verification_seconds")):
                    raise ValueError("non-solution carries a candidate or lacks an explicit reason")
                abort = ABORT_STATUSES.get(result.status, "")
                errors += bool(abort)
        checked.append(entry)
    status = abort or "completed_protocol"
    if value["run_status"] != status:
        raise ValueError("run-status annotation differs from the recorded outcomes")
    return {
        "run_status": status, "calls": calls, "solutions": solutions, "not_run": not_run,
        "errors": errors, "solutions_without_rss": without_rss,
        "support3_gate": _phase_passed(checked, 0), "support5_gate": _phase_passed(checked, 1),
        "support9_gate": _phase_passed(checked, 2), "support17_gate": _phase_passed(checked, 3),
        "counterexamples": 0,
    }


def validate_output(path: Path) -> None:
    if not path.name.startswith("bf_solver_information_sets") \
            or not (path.name.endswith(".json") or path.name.endswith(".json.gz")):
        raise ValueError("use a new bf_solver_information_sets-prefixed JSON report")
    if path.exists():
        raise FileExistsError("output exists; verify it instead of automatically repeating the pilot")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--protocol", action="store_true")
    modes.add_argument("--run-pilot", action="store_true",
                       help="explicitly execute the committed, fixed 18-case protocol")
    modes.add_argument("--verify", type=Path, help="check a saved report without running searches")
    parser.add_argument("--git", default="git")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    if args.protocol:
        print(json.dumps({"protocol": protocol(), "sha256": protocol_hash()}, indent=2))
        return
    if args.verify:
        raw = args.verify.read_bytes()
        report = json.loads(gzip.decompress(raw) if args.verify.suffix == ".gz" else raw)
        summary = verify_report(report)
    else:
        try:
            validate_output(args.output)
        except (ValueError, FileExistsError) as error:
            parser.error(str(error))
        _frozen_head(args.git)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        # Reserve before computation; interruptions remain visible and cannot auto-retry.
        with args.output.open("xb") as output:
            report = run_pilot(args.git)
            summary = verify_report(report)
            payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
            output.write(gzip.compress(payload, mtime=0) if args.output.suffix == ".gz" else payload)
        print(f"Saved {args.output}", flush=True)
    print(json.dumps(summary, indent=2), flush=True)
    if summary["errors"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
