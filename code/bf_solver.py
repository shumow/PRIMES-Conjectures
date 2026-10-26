"""S1: exact Boolean modular equations and bounded CP-SAT calibration.

The model/checker import without optional dependencies. Only a spawned solver
worker imports OR-Tools; returned subsets are checked outside that worker.
"""
from dataclasses import asdict, dataclass, replace
from enum import Enum
from importlib import metadata
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import platform
import random
import subprocess
import sys
import time
from typing import Optional, Sequence

from fs_controls import BASELINE_SOURCES, load_pilot, run_limited
from real_pool_verify import (
    RealInstance, source_digest, subset_residues, verify_group_solution,
)

BASELINE = "0c9f03fb1e00dfd85cb9e2b37e15ed1e727c4915"
BACKEND_VERSION = "9.15.6755"
ROOT = Path(__file__).resolve().parent.parent
DEFAULT_INPUT = ROOT / "data" / "generated" / "real_pool_pilot.json.gz"
CONTROL_INPUT = DEFAULT_INPUT.with_name("fs_controls.json.gz")
REQUIREMENTS = ROOT / "requirements-bf-solver.txt"
SCHEMA = "bf-solver/v1"
SAFE_ACTIVITY = (1 << 62) - 1
MAX_ENTRIES = 1_000_000


class Outcome(str, Enum):
    SOLUTION = "solution"
    PROVED_NO_SOLUTION = "proved_no_solution"
    BACKEND_INFEASIBLE = "backend_reported_infeasible"
    INCONCLUSIVE = "inconclusive_budget"
    TIMEOUT = "timeout_enforced"
    RESOURCE_LIMIT = "resource_limit"
    WORKER_ERROR = "worker_error"


@dataclass(frozen=True)
class Problem:
    orders: tuple[int, ...]
    vectors: tuple[tuple[int, ...], ...]
    target: tuple[int, ...]
    min_size: int
    exact_size: Optional[int]


@dataclass(frozen=True)
class Limits:
    seconds: float = 60.0
    memory_mib: int = 512

    def __post_init__(self) -> None:
        if isinstance(self.seconds, bool) or not math.isfinite(self.seconds) \
                or not 0 <= self.seconds <= 60:
            raise ValueError("seconds must be finite and between zero and 60")
        if not _integer(self.memory_mib) or not 1 <= self.memory_mib <= 512:
            raise ValueError("memory target must be an integer from 1 to 512 MiB")


@dataclass(frozen=True)
class CarryRow:
    order: int
    coefficients: tuple[int, ...]
    target: int
    upper: int


@dataclass(frozen=True)
class Result:
    status: Outcome
    indices: tuple[int, ...] = ()
    reason: str = ""
    backend_status: str = ""
    wall_seconds: float = 0.0
    import_seconds: Optional[float] = None
    model_seconds: Optional[float] = None
    solve_seconds: Optional[float] = None
    verification_seconds: Optional[float] = None
    peak_rss_bytes: Optional[int] = None
    memory_measurement: str = "worker measurement unavailable"
    branches: Optional[int] = None
    conflicts: Optional[int] = None


class BackendUnavailableError(RuntimeError):
    pass


def _integer(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool)


def make_problem(orders: Sequence[int], vectors: Sequence[Sequence[int]],
                 target: Sequence[int], *, min_size: int = 3,
                 exact_size: Optional[int] = None) -> Problem:
    if len(target) != len(orders) or any(len(v) != len(orders) for v in vectors):
        raise ValueError("group/vector/target dimensions differ")
    if any(not _integer(m) or m < 2 for m in orders):
        raise ValueError("orders must be integers at least two")
    if any(not _integer(a) for v in vectors for a in v) \
            or any(not _integer(t) for t in target):
        raise ValueError("entries must be integers")
    if not _integer(min_size) or min_size < 3:
        raise ValueError("minimum size must be an integer at least three")
    if exact_size is not None and (not _integer(exact_size)
                                  or exact_size < min_size or exact_size % 2 != 1):
        raise ValueError("exact size must be odd and at least the minimum")
    return Problem(tuple(orders), tuple(tuple(a % m for a, m in zip(v, orders))
                                       for v in vectors),
                   tuple(t % m for t, m in zip(target, orders)), min_size, exact_size)


def carry_rows(problem: Problem):
    for j, order in enumerate(problem.orders):
        coefficients = tuple(v[j] for v in problem.vectors)
        target = problem.target[j]
        # Normalization gives -m < sum(a*x)-t, so an integer carry is >= 0.
        yield CarryRow(order, coefficients, target, (sum(coefficients) - target) // order)


def verify_subset(problem: Problem, indices: Sequence[int]) -> None:
    """Direct modular/cardinality checks, independent of carries and CP-SAT."""
    if any(not _integer(i) or not 0 <= i < len(problem.vectors) for i in indices) \
            or len(set(indices)) != len(indices):
        raise ValueError("subset indices must be distinct integers in range")
    size = len(indices)
    if size < problem.min_size or size % 2 != 1 \
            or (problem.exact_size is not None and size != problem.exact_size):
        raise ValueError("subset violates declared cardinality")
    if any(sum(problem.vectors[i][j] for i in indices) % m != problem.target[j]
           for j, m in enumerate(problem.orders)):
        raise ValueError("subset does not reproduce original modular target")


def _cardinality_impossible(problem: Problem) -> bool:
    minimum_odd = problem.min_size + (problem.min_size % 2 == 0)
    required = minimum_odd if problem.exact_size is None else problem.exact_size
    return required > len(problem.vectors)


def verify_result(problem: Problem, result: Result) -> None:
    if not isinstance(result.status, Outcome):
        raise ValueError("unknown result status")
    if result.status is Outcome.SOLUTION:
        if result.reason:
            raise ValueError("solution cannot carry a failure reason")
        verify_subset(problem, result.indices)
    else:
        if result.indices or not result.reason:
            raise ValueError("non-solution must have an explicit reason and no subset")
        if result.status is Outcome.PROVED_NO_SOLUTION:
            if result.reason == "cardinality":
                minimum = problem.min_size + (problem.min_size % 2 == 0)
                if (minimum if problem.exact_size is None else problem.exact_size) \
                        <= len(problem.vectors):
                    raise ValueError("false cardinality obstruction")
            elif result.reason.startswith("row_target_out_of_range:"):
                j = int(result.reason.split(":")[1])
                if not 0 <= j < len(problem.orders) or problem.target[j] \
                        <= sum(v[j] for v in problem.vectors):
                    raise ValueError("false row-sum obstruction")
            else:
                raise ValueError("unknown direct obstruction")


def backend_version() -> str:
    try:
        version = metadata.version("ortools")
    except metadata.PackageNotFoundError as exc:
        raise BackendUnavailableError(
            "Optional backend absent; install requirements-bf-solver.txt "
            "in an isolated environment") from exc
    if version != BACKEND_VERSION:
        raise BackendUnavailableError(f"Expected ortools {BACKEND_VERSION}, found {version}")
    return version


def _peak_rss() -> tuple[Optional[int], str]:
    if sys.platform == "win32":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD)] + [
                (name, ctypes.c_size_t) for name in (
                    "PeakWorkingSetSize", "WorkingSetSize", "QuotaPeakPagedPoolUsage",
                    "QuotaPagedPoolUsage", "QuotaPeakNonPagedPoolUsage",
                    "QuotaNonPagedPoolUsage", "PagefileUsage", "PeakPagefileUsage")]

        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetCurrentProcess.restype = wintypes.HANDLE
        psapi = ctypes.WinDLL("psapi", use_last_error=True)
        psapi.GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE, ctypes.POINTER(Counters), wintypes.DWORD]
        psapi.GetProcessMemoryInfo.restype = wintypes.BOOL
        counters = Counters()
        counters.cb = ctypes.sizeof(counters)
        if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(),
                                         ctypes.byref(counters), counters.cb):
            raise ctypes.WinError(ctypes.get_last_error())
        return int(counters.PeakWorkingSetSize), "Windows PeakWorkingSetSize"
    if sys.platform.startswith("linux") or sys.platform == "darwin":
        import resource
        scale = 1 if sys.platform == "darwin" else 1024
        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * scale, "getrusage peak RSS"
    return None, "peak RSS not measured on this platform"


def _work_cpsat(payload: tuple[Problem, Limits, float, int]) -> Result:
    problem, limits, deadline, seed = payload
    started = time.monotonic()
    from ortools.sat.python import cp_model
    import_seconds = time.monotonic() - started
    model_started = time.monotonic()
    model = cp_model.CpModel()
    x = [model.new_bool_var(f"x{i}") for i in range(len(problem.vectors))]
    h = model.new_int_var(1, (len(x) - 1) // 2, "odd_half")
    cardinality = sum(x)
    model.add(cardinality == 2 * h + 1)
    model.add(cardinality >= problem.min_size)
    if problem.exact_size is not None:
        model.add(cardinality == problem.exact_size)
    for j, row in enumerate(carry_rows(problem)):
        if time.monotonic() >= deadline:
            return Result(Outcome.INCONCLUSIVE, reason="deadline during model construction",
                          import_seconds=import_seconds,
                          model_seconds=time.monotonic() - model_started)
        if not any(row.coefficients) and row.target == 0:
            continue
        expression = cp_model.LinearExpr.weighted_sum(x, row.coefficients)
        if row.upper == 0:
            model.add(expression == row.target)
        else:
            carry = model.new_int_var(0, row.upper, f"z{j}")
            model.add(expression == row.target + row.order * carry)
    validation = model.validate()
    if validation:
        raise ArithmeticError("CP-SAT rejected the exact model: " + validation)
    model_seconds = time.monotonic() - model_started
    remaining = deadline - time.monotonic()
    if remaining <= 0:
        return Result(Outcome.INCONCLUSIVE, reason="deadline before backend solve",
                      import_seconds=import_seconds, model_seconds=model_seconds)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = remaining
    solver.parameters.max_memory_in_mb = limits.memory_mib
    solver.parameters.num_search_workers = 1
    solver.parameters.random_seed = seed
    solver.parameters.stop_after_first_solution = True
    solve_started = time.monotonic()
    status = solver.solve(model)
    solve_seconds = time.monotonic() - solve_started
    label = solver.status_name(status)
    peak, method = _peak_rss()
    measurements = dict(backend_status=label, import_seconds=import_seconds,
                        model_seconds=model_seconds, solve_seconds=solve_seconds,
                        peak_rss_bytes=peak, memory_measurement=method,
                        branches=solver.num_branches, conflicts=solver.num_conflicts)
    if status in (cp_model.FEASIBLE, cp_model.OPTIMAL):
        return Result(Outcome.SOLUTION,
                      indices=tuple(i for i, variable in enumerate(x) if solver.value(variable)),
                      **measurements)
    if status == cp_model.INFEASIBLE:
        return Result(Outcome.BACKEND_INFEASIBLE, reason="uncertified backend infeasibility",
                      **measurements)
    if status == cp_model.UNKNOWN:
        return Result(Outcome.INCONCLUSIVE, reason="backend UNKNOWN: " + solver.solution_info(),
                      **measurements)
    raise ArithmeticError("Unexpected CP-SAT status: " + label)


def solve(problem: Problem, *, limits: Limits = Limits(), seed: int = 1729) -> Result:
    """One worker, no witness/hints, and no accepted late/over-target solution."""
    if not _integer(seed) or not 0 <= seed < 2**31:
        raise ValueError("solver seed must be a nonnegative signed-32-bit integer")
    started = time.monotonic()

    def finish(result: Result) -> Result:
        verified = time.monotonic()
        verify_result(problem, result)
        elapsed = time.monotonic() - started
        if result.status is Outcome.SOLUTION and elapsed >= limits.seconds:
            return replace(result, status=Outcome.TIMEOUT, indices=(),
                           reason="verification completed after wall deadline",
                           wall_seconds=elapsed,
                           verification_seconds=time.monotonic() - verified)
        return replace(result, wall_seconds=elapsed,
                       verification_seconds=time.monotonic() - verified)

    if limits.seconds == 0:
        return finish(Result(Outcome.TIMEOUT, reason="zero wall-time budget"))
    if _cardinality_impossible(problem):
        return finish(Result(Outcome.PROVED_NO_SOLUTION, reason="cardinality"))
    if len(problem.orders) * len(problem.vectors) > MAX_ENTRIES:
        return finish(Result(Outcome.RESOURCE_LIMIT, reason="matrix-entry guard"))
    for j, row in enumerate(carry_rows(problem)):
        if row.upper < 0:
            return finish(Result(Outcome.PROVED_NO_SOLUTION,
                                 reason=f"row_target_out_of_range:{j}"))
        activity = sum(row.coefficients) + row.target + row.order * row.upper
        if activity > SAFE_ACTIVITY:
            return finish(Result(Outcome.RESOURCE_LIMIT,
                                 reason="conservative signed-64-bit activity guard"))
        if time.monotonic() - started >= limits.seconds:
            return finish(Result(Outcome.TIMEOUT, reason="deadline during model preflight"))
    backend_version()
    remaining = limits.seconds - (time.monotonic() - started)
    if remaining <= 0:
        return finish(Result(Outcome.TIMEOUT, reason="deadline before worker startup"))
    kind, value, _ = run_limited(_work_cpsat, (problem, limits, started + limits.seconds, seed),
                                 remaining)
    if kind == "timeout":
        return finish(Result(Outcome.TIMEOUT, reason="external spawn watchdog deadline"))
    if kind == "worker_error":
        return finish(Result(Outcome.WORKER_ERROR, reason=str(value)))
    if kind != "ok" or not isinstance(value, Result):
        raise TypeError("unexpected solver worker protocol")
    if value.peak_rss_bytes is not None and value.peak_rss_bytes > limits.memory_mib * 1024**2:
        return finish(replace(value, status=Outcome.RESOURCE_LIMIT, indices=(),
                              reason="observed worker peak RSS exceeds memory target"))
    if time.monotonic() - started >= limits.seconds:
        return finish(replace(value, status=Outcome.TIMEOUT, indices=(),
                              reason="worker result arrived after wall deadline"))
    return finish(value)


@dataclass(frozen=True)
class CaseSpec:
    name: str
    phase: int
    support: int
    seed: int
    holdout: bool
    exact: bool


@dataclass(frozen=True)
class Control:
    spec: CaseSpec
    problem: Problem
    witness: tuple[int, ...]
    residues: tuple[int, int]


def case_specs() -> tuple[CaseSpec, ...]:
    cases = []
    for phase, support, holdout, exact in (
            (0, 3, False, True), (1, 5, False, True), (1, 5, True, True),
            (2, 9, False, True), (2, 17, False, True), (2, 5, True, False)):
        for seed in ((104729, 130363, 155921) if holdout else (101, 202, 303)):
            name = f"{'holdout' if holdout else 'dev'}-k{support}-{seed}-{'exact' if exact else 'odd'}"
            cases.append(CaseSpec(name, phase, support, seed, holdout, exact))
    return tuple(cases)


def protocol() -> dict[str, object]:
    return {
        "backend": "ortools-cp-sat", "backend_version": BACKEND_VERSION,
        "limits": asdict(Limits()), "search_workers": 1, "solver_seed": 1729,
        "max_calls": 18, "matrix_entry_guard": MAX_ENTRIES,
        "safe_activity_guard": SAFE_ACTIVITY,
        "cases": [asdict(spec) for spec in case_specs()],
        "scope": "full medium-complete-family, parent LCMs unchanged; planted targets only",
        "gates": "phase 0: all three support-3 solutions; phase 1: all six support-5 solutions",
        "holdout_labels": "bf-solver-holdout/20261024/<seed>",
        "memory_scope": "512 MiB target, backend advisory setting; not an OS RSS cap",
        "wall_scope": "absolute call deadline includes startup/import/build/check; teardown may overrun",
        "negative_scope": "backend infeasibility is not an independently checked proof",
    }


def _protocol_hash() -> str:
    return hashlib.sha256(json.dumps(protocol(), sort_keys=True).encode("utf-8")).hexdigest()


def _sources() -> dict[str, str]:
    names = BASELINE_SOURCES + ("fs_controls.py", "bf_solver.py")
    return {name: source_digest(Path(__file__).with_name(name)) for name in names}


def _control(instance: RealInstance, spec: CaseSpec) -> Control:
    label = (f"bf-solver-holdout/20261024/{spec.seed}" if spec.holdout else
             f"fs-controls-witness/medium-complete-family/483/{spec.support}/{spec.seed}")
    witness = tuple(sorted(random.Random(label).sample(range(len(instance.records)), spec.support)))
    target = tuple(sum(instance.vectors[i][j] for i in witness) % m
                   for j, m in enumerate(instance.orders))
    residues = subset_residues(instance.records, witness,
                               instance.lambda_minus, instance.lambda_plus)
    verify_group_solution(instance, witness, target, residues)
    problem = make_problem(instance.orders, instance.vectors, target,
                           exact_size=spec.support if spec.exact else None)
    return Control(spec, problem, witness, residues)


def _context(pilot_path: Path, controls_path: Path):
    instances, verification, pilot_hash = load_pilot(pilot_path)
    if pilot_hash != "008cf08ce3f0d3a2f987bff26d5abd04bf4c41050f949ae0fdc4f4192b6969de":
        raise ValueError("S1 protocol requires the unchanged frozen pilot")
    instance = instances["medium-complete-family"]
    if len(instance.records) != 483:
        raise ValueError("wrong full-pool scope")
    payload = controls_path.read_bytes()
    previous = json.loads(gzip.decompress(payload))
    if previous["schema"] != "fs-controls/v1.1" \
            or previous["input_artifact"]["sha256"] != pilot_hash:
        raise ValueError("wrong development-control artifact")
    for filename, digest in previous["source_sha256"].items():
        if source_digest(Path(__file__).with_name(filename)) != digest:
            raise ValueError("development-control source mismatch: " + filename)
    controls = tuple(_control(instance, spec) for spec in case_specs())
    for control in controls:
        if control.spec.holdout:
            continue
        match = [e for e in previous["experiments"] if e["cohort"] == "medium-complete-family"
                 and e["scope_size"] == 483 and e["support"] == control.spec.support
                 and e["planting_seed_label"] == control.spec.seed]
        if len(match) != 1 or match[0]["planted_witness_indices"] != list(control.witness) \
                or match[0]["residues_hex"] != [hex(v) for v in control.residues]:
            raise ValueError("development case differs from first-wave target")
    return instance, controls, {
        "pilot_sha256": pilot_hash, "controls_sha256": hashlib.sha256(payload).hexdigest(),
        "pilot_verification": verification,
    }


def _case_json(control: Control) -> dict[str, object]:
    return {"spec": asdict(control.spec), "target_hex": [hex(v) for v in control.problem.target],
            "witness_indices": list(control.witness),
            "residues_hex": [hex(v) for v in control.residues],
            "cardinality_mode": "exact_k" if control.spec.exact else "general_odd_minimum_3"}


def _gate(records: Sequence[dict[str, object]], phase: int, expected: int) -> bool:
    selected = [r for r in records if r["phase"] == phase]
    return len(selected) == expected and all(
        isinstance(r["result"], dict) and r["result"]["status"] == Outcome.SOLUTION
        for r in selected)


def _may_run(phase: int, records: Sequence[dict[str, object]]) -> bool:
    return phase == 0 or (_gate(records, 0, 3) and (phase == 1 or _gate(records, 1, 6)))


def implementation_head(git: str) -> str:
    head = subprocess.check_output([git, "-C", str(ROOT), "rev-parse", "HEAD"],
                                   text=True).strip()
    if len(head) != 40 or any(c not in "0123456789abcdef" for c in head):
        raise ValueError("invalid implementation commit")
    paths = ["code/" + name for name in _sources()] + ["requirements-bf-solver.txt"]
    for path in paths:
        committed = subprocess.check_output([git, "-C", str(ROOT), "show", f"{head}:{path}"])
        if committed.replace(b"\r\n", b"\n") != (ROOT / path).read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("commit the frozen implementation before a pilot: " + path)
    return head


def run_pilot(git: str, pilot_path: Path = DEFAULT_INPUT,
              controls_path: Path = CONTROL_INPUT) -> dict[str, object]:
    backend_version()
    head = implementation_head(git)
    started = time.monotonic()
    instance, controls, inputs = _context(pilot_path, controls_path)
    preparation = time.monotonic() - started
    records: list[dict[str, object]] = []
    for control in controls:
        record: dict[str, object] = {
            "phase": control.spec.phase, "case": _case_json(control),
            "result": None, "not_run_reason": "", "arithmetic_verification_seconds": None,
        }
        if _may_run(control.spec.phase, records):
            result = solve(control.problem)
            if result.status in (Outcome.BACKEND_INFEASIBLE, Outcome.PROVED_NO_SOLUTION):
                raise ArithmeticError(f"{control.spec.name}: negative contradicts a verified control")
            if result.status is Outcome.WORKER_ERROR:
                raise RuntimeError(f"{control.spec.name}: {result.reason}")
            if result.status is Outcome.SOLUTION:
                verify_started = time.monotonic()
                verify_group_solution(instance, result.indices, control.problem.target,
                                      control.residues)
                record["arithmetic_verification_seconds"] = time.monotonic() - verify_started
            record["result"] = asdict(result)
            print(f"{control.spec.name}: {result.status.value} "
                  f"({result.wall_seconds:.3f}s)", flush=True)
        else:
            record["not_run_reason"] = "preregistered prior-phase gate did not pass"
        records.append(record)
    return {
        "schema": SCHEMA, "baseline_commit": BASELINE, "implementation_commit": head,
        "python": platform.python_version(), "platform": platform.platform(),
        "protocol": protocol(), "protocol_sha256": _protocol_hash(),
        "source_sha256": _sources(), "source_hash_normalization": "CRLF-to-LF",
        "requirements_sha256": source_digest(REQUIREMENTS),
        "inputs": inputs, "input_preparation_seconds": preparation,
        "dependencies": {d.metadata["Name"]: d.version for d in metadata.distributions()
                         if d.metadata["Name"]},
        "cases": records, "counterexamples": 0,
    }


def _read_result(raw: object) -> Result:
    if not isinstance(raw, dict) or set(raw) != set(Result.__dataclass_fields__):
        raise ValueError("malformed saved result")
    indices = raw["indices"]
    if not isinstance(indices, (list, tuple)) or any(not _integer(i) for i in indices):
        raise ValueError("invalid saved subset indices")
    if not isinstance(raw["reason"], str) or not isinstance(raw["backend_status"], str) \
            or not isinstance(raw["memory_measurement"], str):
        raise ValueError("invalid saved result annotations")
    for field in ("wall_seconds", "import_seconds", "model_seconds", "solve_seconds",
                  "verification_seconds"):
        value = raw[field]
        if value is None and field != "wall_seconds":
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) \
                or not math.isfinite(value) or value < 0:
            raise ValueError("invalid saved timing")
    for field in ("peak_rss_bytes", "branches", "conflicts"):
        value = raw[field]
        if value is not None and (not _integer(value) or value < 0):
            raise ValueError("invalid saved measurement")
    return Result(status=Outcome(raw["status"]), indices=tuple(indices), reason=raw["reason"],
                  backend_status=raw["backend_status"], wall_seconds=raw["wall_seconds"],
                  import_seconds=raw["import_seconds"], model_seconds=raw["model_seconds"],
                  solve_seconds=raw["solve_seconds"],
                  verification_seconds=raw["verification_seconds"],
                  peak_rss_bytes=raw["peak_rss_bytes"],
                  memory_measurement=raw["memory_measurement"],
                  branches=raw["branches"], conflicts=raw["conflicts"])


def verify_report(value: object, pilot_path: Path = DEFAULT_INPUT,
                  controls_path: Path = CONTROL_INPUT) -> dict[str, object]:
    """Verify saved subsets/protocol without importing or invoking CP-SAT."""
    if not isinstance(value, dict) or value["schema"] != SCHEMA \
            or value["baseline_commit"] != BASELINE:
        raise ValueError("unknown S1 report")
    if value["protocol"] != protocol() or value["protocol_sha256"] != _protocol_hash() \
            or value["source_sha256"] != _sources() \
            or value["requirements_sha256"] != source_digest(REQUIREMENTS) \
            or value["source_hash_normalization"] != "CRLF-to-LF":
        raise ValueError("S1 protocol/source provenance mismatch")
    instance, controls, inputs = _context(pilot_path, controls_path)
    if any(value["inputs"][key] != inputs[key] for key in ("pilot_sha256", "controls_sha256")):
        raise ValueError("S1 input provenance mismatch")
    records = value["cases"]
    if not isinstance(records, list) or len(records) != len(controls) or value["counterexamples"] != 0:
        raise ValueError("incorrect S1 case scope")
    checked: list[dict[str, object]] = []
    calls = solutions = not_run = 0
    for record, control in zip(records, controls):
        if not isinstance(record, dict) or record["case"] != _case_json(control) \
                or record["phase"] != control.spec.phase:
            raise ValueError("S1 target, witness or scope changed")
        if not _may_run(control.spec.phase, checked):
            if record["result"] is not None or record["not_run_reason"] \
                    != "preregistered prior-phase gate did not pass":
                raise ValueError("invalid gated case")
            not_run += 1
        else:
            if record["not_run_reason"]:
                raise ValueError("eligible case was not run")
            result = _read_result(record["result"])
            verify_result(control.problem, result)
            if result.status in (Outcome.PROVED_NO_SOLUTION, Outcome.BACKEND_INFEASIBLE):
                raise ValueError("negative contradicts a verified planted target")
            if result.status is Outcome.SOLUTION:
                if result.wall_seconds >= 60 or (result.peak_rss_bytes is not None
                                                and result.peak_rss_bytes > 512 * 1024**2):
                    raise ValueError("out-of-budget result classified as a success")
                verify_group_solution(instance, result.indices, control.problem.target,
                                      control.residues)
                solutions += 1
            calls += 1
        checked.append(record)
    return {"calls": calls, "solutions": solutions, "not_run": not_run,
            "support3_gate": _gate(checked, 0, 3), "support5_gate": _gate(checked, 1, 6),
            "counterexamples": 0}


def validate_output(path: Path, pilot: Path, controls: Path, replace_existing: bool) -> None:
    protected = {pilot.resolve(), controls.resolve(),
                 DEFAULT_INPUT.with_name("fs_reachability.json.gz").resolve(),
                 DEFAULT_INPUT.with_name("fs_harvest.json.gz").resolve()}
    if path.resolve() in protected or not path.name.startswith("bf_solver") \
            or not (path.name.endswith(".json") or path.name.endswith(".json.gz")):
        raise ValueError("use a new bf_solver-prefixed JSON report, never a frozen input")
    if path.exists() and not replace_existing:
        raise FileExistsError("output exists; use another output or explicit --replace")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--controls", type=Path, default=CONTROL_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_INPUT.with_name("bf_solver.json.gz"))
    parser.add_argument("--git", default="git", help="Git executable for committed-source provenance")
    parser.add_argument("--protocol", action="store_true", help="print fixed protocol; do not solve")
    parser.add_argument("--verify", type=Path, help="check saved subsets without the optional backend")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.protocol:
        print(json.dumps({"protocol": protocol(), "sha256": _protocol_hash()}, indent=2))
        return
    if args.verify:
        payload = args.verify.read_bytes()
        if args.verify.suffix == ".gz":
            payload = gzip.decompress(payload)
        print(json.dumps(verify_report(json.loads(payload), args.pilot, args.controls), indent=2))
        return
    validate_output(args.output, args.pilot, args.controls, args.replace)
    report = run_pilot(args.git, args.pilot, args.controls)
    summary = verify_report(report, args.pilot, args.controls)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    with args.output.open("wb" if args.replace else "xb") as output:
        output.write(gzip.compress(payload, mtime=0) if args.output.suffix == ".gz" else payload)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
