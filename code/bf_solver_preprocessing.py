"""Versioned S1 Round 2: split-C2 arithmetic certificates and exact syndrome filtering."""
from dataclasses import asdict, dataclass, replace
from itertools import combinations
from pathlib import Path
from typing import Optional
import argparse
import gzip
import hashlib
import json
import math
import platform
import subprocess
import time

import bf_solver as baseline
from real_pool_verify import (
    RealInstance, _rank_mod, instance_from_json, source_digest, trial_factors,
    verify_encoding, verify_group_solution,
)

SCHEMA = "bf-solver-preprocessing/v1"
GATE_SCHEMA = "split-c2-index-two/v1"
S3_COMMIT = "fb8dfd186023b8ed518047d7a08c42013e78e4df"
S3_PATH = "data/generated/bf_harvest.json.gz"
S3_SHA256 = "f2670b133827d302a85bc0813348d7f76ce548fd39f27f5f1632b3c51f9322a5"
ROUND1_SHA256 = "67b7dd568c925432546d8f43373cab4a8e638abe79fa3802873202243dd5b9a5"
ROOT = Path(__file__).resolve().parent.parent


class NotCertifiedError(ValueError):
    pass


def _primary_fields(problem: baseline.Problem) -> dict[int, list[int]]:
    fields: dict[int, list[int]] = {}
    for j, order in enumerate(problem.orders):
        factors = trial_factors(order)
        if order < 2 or len(factors) != 1:
            raise ValueError("arithmetic gate requires prime-power component orders")
        fields.setdefault(next(iter(factors)), []).append(j)
    return fields


def _split_fields(problem: baseline.Problem, keep: int, drop: int) -> dict[int, list[int]]:
    if not baseline._integer(keep) or not baseline._integer(drop) or keep == drop \
            or not 0 <= keep < len(problem.orders) or not 0 <= drop < len(problem.orders):
        raise ValueError("split coordinates must be distinct indices in range")
    if problem.orders[keep] != 2 or problem.orders[drop] != 2:
        raise ValueError("both split coordinates must have order exactly two")
    if len(problem.target) != len(problem.orders) or any(
            len(v) != len(problem.orders) for v in problem.vectors):
        raise ValueError("invalid arithmetic-gate dimensions")
    if any(v[keep] % 2 != v[drop] % 2 for v in problem.vectors):
        raise NotCertifiedError("generators do not lie in the proposed split kernel")
    fields = _primary_fields(problem)
    fields[2] = [j for j in fields[2] if j != drop]
    return fields


def _basis_columns(problem: baseline.Problem, coords: list[int], prime: int,
                   deadline: float) -> list[int]:
    selected = []
    if prime == 2:
        binary: dict[int, int] = {}
        for i, vector in enumerate(problem.vectors):
            if time.monotonic() >= deadline:
                raise TimeoutError("arithmetic rank probe deadline")
            value = sum((vector[j] % 2) << k for k, j in enumerate(coords))
            while value:
                pivot = value.bit_length() - 1
                if pivot not in binary:
                    binary[pivot] = value
                    selected.append(i)
                    break
                value ^= binary[pivot]
            if len(selected) == len(coords):
                return selected
    else:
        basis: dict[int, list[int]] = {}
        for i, vector in enumerate(problem.vectors):
            if time.monotonic() >= deadline:
                raise TimeoutError("arithmetic rank probe deadline")
            row = [vector[j] % prime for j in coords]
            for pivot, previous in sorted(basis.items()):
                multiplier = row[pivot]
                if multiplier:
                    row = [(a - multiplier * b) % prime for a, b in zip(row, previous)]
            pivot = next((k for k, value in enumerate(row) if value), None)
            if pivot is not None:
                inverse = pow(row[pivot], -1, prime)
                basis[pivot] = [value * inverse % prime for value in row]
                selected.append(i)
            if len(selected) == len(coords):
                return selected
    return selected


def certify_split_index_two(problem: baseline.Problem, keep: int, drop: int) -> dict[str, object]:
    fields = _split_fields(problem, keep, drop)
    parts = []
    for prime, coords in sorted(fields.items()):
        selected = _basis_columns(problem, coords, prime, time.monotonic() + 60)
        if len(selected) != len(coords):
            raise NotCertifiedError(f"rank deficient for prime {prime}: {len(selected)}/{len(coords)}")
        parts.append({"prime": prime, "coordinates": coords, "generator_indices": selected})
    return {"schema": GATE_SCHEMA, "keep": keep, "drop": drop, "parts": parts,
            "index": 2, "target_member": problem.target[keep] % 2 == problem.target[drop] % 2}


def verify_split_index_two(problem: baseline.Problem, certificate: dict) -> dict[str, object]:
    """Recheck every selected full-rank minor; never call certificate generation."""
    if certificate["schema"] != GATE_SCHEMA or not baseline._integer(certificate["index"]) \
            or certificate["index"] != 2:
        raise ValueError("unknown split-relation certificate")
    fields = _split_fields(problem, certificate["keep"], certificate["drop"])
    parts = certificate["parts"]
    if not isinstance(parts, list) or any(not baseline._integer(part["prime"]) for part in parts) \
            or [part["prime"] for part in parts] != sorted(fields):
        raise ValueError("missing, repeated or mismatched primary part")
    for part in parts:
        prime = part["prime"]
        coords = fields[prime]
        selected = part["generator_indices"]
        if part["coordinates"] != coords or len(selected) != len(coords) \
                or len(set(selected)) != len(selected) or any(
                    not baseline._integer(i) or not 0 <= i < len(problem.vectors) for i in selected):
            raise ValueError("invalid primary minor scope")
        started = time.monotonic()
        if prime == 2:
            pivots: dict[int, int] = {}
            for j in coords:
                value = sum((problem.vectors[i][j] % 2) << k for k, i in enumerate(selected))
                while value:
                    pivot = value & -value
                    if pivot not in pivots:
                        pivots[pivot] = value
                        break
                    value ^= pivots[pivot]
            rank = len(pivots)
        else:
            matrix = [[problem.vectors[i][j] % prime for i in selected] for j in coords]
            rank = _rank_mod(matrix, prime)
        if time.monotonic() - started >= 60:
            raise TimeoutError("arithmetic minor verification deadline")
        if rank != len(coords):
            raise ValueError("selected primary minor is not invertible")
    member = problem.target[certificate["keep"]] % 2 == problem.target[certificate["drop"]] % 2
    if certificate["target_member"] is not member:
        raise ValueError("target-membership annotation differs from the split relation")
    return {"index": 2, "target_member": member, "primary_parts": len(parts),
            "binary_rank_after_drop": len(fields[2])}


@dataclass(frozen=True)
class SearchLimits:
    seconds: float = 60.0
    memory_mib: int = 512
    max_enumerations: int = 20_000_000
    max_left_entries: int = 200_000
    max_candidates: int = 10_000

    def __post_init__(self) -> None:
        baseline.Limits(self.seconds, self.memory_mib)
        for value in (self.max_enumerations, self.max_left_entries, self.max_candidates):
            if not baseline._integer(value) or value < 1:
                raise ValueError("search work limits must be positive integers")


@dataclass(frozen=True)
class SearchResult:
    status: str
    indices: tuple[int, ...] = ()
    reason: str = ""
    left_entries: int = 0
    right_entries: int = 0
    candidates: int = 0
    projection_seconds: float = 0.0
    search_seconds: float = 0.0
    wall_seconds: float = 0.0
    verification_seconds: float = 0.0
    peak_rss_bytes: Optional[int] = None
    memory_measurement: str = "not returned by worker"


def binary_syndromes(problem: baseline.Problem) -> tuple[tuple[int, ...], int]:
    coords = [j for j, order in enumerate(problem.orders) if order % 2 == 0]
    parity = 1 << len(coords)
    columns = tuple(parity | sum((vector[j] % 2) << k for k, j in enumerate(coords))
                    for vector in problem.vectors)
    target = parity | sum((problem.target[j] % 2) << k for k, j in enumerate(coords))
    return columns, target


def _indices(mask: int) -> tuple[int, ...]:
    selected = []
    while mask:
        bit = mask & -mask
        selected.append(bit.bit_length() - 1)
        mask ^= bit
    return tuple(selected)


def _work_filtered(payload: tuple[baseline.Problem, SearchLimits, float]) -> SearchResult:
    problem, limits, deadline = payload
    started = time.monotonic()
    columns, target = binary_syndromes(problem)
    projection_seconds = time.monotonic() - started
    search_started = time.monotonic()
    k = problem.exact_size
    if k is None:
        raise ValueError("filtered search requires a declared exact cardinality")
    left_size, right_size = k // 2, k - k // 2
    table: dict[int, list[int]] = {}
    left_count = right_count = candidates = 0

    def finish(status: str, indices: tuple[int, ...] = (), reason: str = "") -> SearchResult:
        peak, method = baseline._peak_rss()
        return SearchResult(status, indices, reason, left_count, right_count, candidates,
                            projection_seconds, time.monotonic() - search_started,
                            peak_rss_bytes=peak, memory_measurement=method)

    for combo in combinations(range(len(columns)), left_size):
        if left_count % 1024 == 0 and time.monotonic() >= deadline:
            return finish("timeout_enforced", reason="left-table deadline")
        syndrome, mask = 0, 0
        for i in combo:
            syndrome ^= columns[i]
            mask |= 1 << i
        table.setdefault(syndrome, []).append(mask)
        left_count += 1
    for combo in combinations(range(len(columns)), right_size):
        if right_count % 1024 == 0 and time.monotonic() >= deadline:
            return finish("timeout_enforced", reason="right-enumeration deadline")
        syndrome, mask = target, 0
        for i in combo:
            syndrome ^= columns[i]
            mask |= 1 << i
        right_count += 1
        for left_mask in table.get(syndrome, ()):
            if left_mask & mask:
                continue
            if candidates >= limits.max_candidates:
                return finish("resource_limit", reason="full-target candidate-check cap")
            candidates += 1
            indices = _indices(left_mask | mask)
            if all(sum(problem.vectors[i][j] for i in indices) % order == problem.target[j]
                   for j, order in enumerate(problem.orders)):
                return finish("solution", indices)
    return finish("completed_exact_scope", reason="no exact-k subset in the declared pool")


def solve_filtered(problem: baseline.Problem, limits: SearchLimits = SearchLimits()) -> SearchResult:
    if problem.exact_size is None:
        raise ValueError("declare exact_size; general odd recovery is not implemented")
    started = time.monotonic()

    def finish(result: SearchResult) -> SearchResult:
        check_started = time.monotonic()
        if result.status not in ("solution", "completed_exact_scope", "resource_limit",
                                 "timeout_enforced", "worker_error"):
            raise ValueError("unknown filtered-search status")
        if result.status == "solution":
            if result.reason:
                raise ValueError("successful search cannot carry a failure reason")
            baseline.verify_subset(problem, result.indices)
        elif result.indices or not result.reason:
            raise ValueError("non-solution must have a reason and no candidate")
        elapsed = time.monotonic() - started
        if result.status == "solution" and elapsed >= limits.seconds:
            return replace(result, status="timeout_enforced", indices=(),
                           reason="late candidate", wall_seconds=elapsed)
        return replace(result, wall_seconds=elapsed,
                       verification_seconds=time.monotonic() - check_started)

    if limits.seconds == 0:
        return finish(SearchResult("timeout_enforced", reason="zero wall budget"))
    n, k = len(problem.vectors), problem.exact_size
    if k > n:
        return finish(SearchResult("completed_exact_scope", reason="cardinality exceeds pool"))
    left = math.comb(n, k // 2)
    right = math.comb(n, k - k // 2)
    if len(problem.orders) * n > baseline.MAX_ENTRIES:
        return finish(SearchResult("resource_limit", reason="matrix-entry guard"))
    if left > limits.max_left_entries or left + right > limits.max_enumerations:
        return finish(SearchResult("resource_limit", reason="declared enumeration/table cap"))
    remaining = limits.seconds - (time.monotonic() - started)
    if remaining <= 0:
        return finish(SearchResult("timeout_enforced", reason="preflight deadline"))
    kind, value, _ = baseline.run_limited(
        _work_filtered, (problem, limits, started + limits.seconds), remaining)
    if kind == "timeout":
        return finish(SearchResult("timeout_enforced", reason="external spawn watchdog"))
    if kind == "worker_error":
        return finish(SearchResult("worker_error", reason=str(value)))
    if kind != "ok" or not isinstance(value, SearchResult):
        raise TypeError("invalid filtered-worker result")
    if value.peak_rss_bytes is not None and value.peak_rss_bytes > limits.memory_mib * 1024**2:
        return finish(replace(value, status="resource_limit", indices=(),
                              reason="observed worker RSS exceeds target"))
    if time.monotonic() - started >= limits.seconds:
        return finish(replace(value, status="timeout_enforced", indices=(),
                              reason="worker returned after deadline"))
    return finish(value)


def case_specs() -> tuple[baseline.CaseSpec, ...]:
    return tuple(spec for spec in baseline.case_specs() if spec.phase < 2)


def protocol() -> dict[str, object]:
    return {
        "algorithm": "exact-k binary-syndrome filtered meet-in-the-middle",
        "limits": asdict(SearchLimits()), "workers": 1, "max_calls": 9,
        "aggregate_call_seconds": 540, "cases": [asdict(spec) for spec in case_specs()],
        "scope": "full medium-complete-family; parent LCMs unchanged; planted exact-k only",
        "gate": "all three support-3 controls before the six support-5 controls",
        "holdouts": "same unrun Round1 labels, bf-solver-holdout/20261024/<seed>",
        "candidate_check": "all original modular equations plus independent prime residues",
        "wall_scope": "startup, projection, search and subset check; teardown may overrun",
        "memory_scope": "completed-worker peak RSS target; not OS-enforced",
        "round1_artifact_sha256": ROUND1_SHA256,
        "arithmetic_gate": GATE_SCHEMA, "s3_commit": S3_COMMIT, "s3_sha256": S3_SHA256,
    }


def protocol_hash() -> str:
    return hashlib.sha256(json.dumps(protocol(), sort_keys=True).encode("utf-8")).hexdigest()


def sources() -> dict[str, str]:
    return {**baseline._sources(), "bf_solver_preprocessing.py": source_digest(Path(__file__))}


def _load_inputs(git: str, s3_path: Optional[Path]):
    pilot, all_controls, inputs = baseline._context(baseline.DEFAULT_INPUT, baseline.CONTROL_INPUT)
    controls = tuple(control for control in all_controls if control.spec.phase < 2)
    del all_controls
    round1 = baseline.DEFAULT_INPUT.with_name("bf_solver.json.gz").read_bytes()
    if hashlib.sha256(round1).hexdigest() != ROUND1_SHA256:
        raise ValueError("Round1 artifact changed")
    payload = (s3_path.read_bytes() if s3_path is not None else subprocess.check_output(
        [git, "-C", str(ROOT), "show", f"{S3_COMMIT}:{S3_PATH}"]))
    if hashlib.sha256(payload).hexdigest() != S3_SHA256:
        raise ValueError("use the exact reviewed S3 snapshot; no report flags are trusted")
    s3_report = json.loads(gzip.decompress(payload))
    s3 = instance_from_json(s3_report["run"]["instance"])
    verify_encoding(s3)
    return {"pilot": pilot, "s3": s3}, controls, {
        "pilot_sha256": inputs["pilot_sha256"], "controls_sha256": inputs["controls_sha256"],
        "round1_sha256": ROUND1_SHA256, "s3_sha256": S3_SHA256, "s3_commit": S3_COMMIT,
    }


def _group_problem(instance: RealInstance) -> baseline.Problem:
    return baseline.Problem(instance.orders, instance.vectors, instance.target, 3, None)


def _relation(instance: RealInstance) -> tuple[int, int]:
    coords = [j for block in instance.blocks if block.side == "plus" and block.prime == 3
              for j in block.columns if instance.orders[j] == 2]
    if len(coords) != 1 or instance.orders[-1] != 2:
        raise ValueError("instance lacks the named plus-3/parity C2 coordinates")
    return coords[0], len(instance.orders) - 1


def arithmetic_gates(instances: dict[str, RealInstance]) -> list[dict[str, object]]:
    output = []
    for name, instance in instances.items():
        problem = _group_problem(instance)
        keep, drop = _relation(instance)
        started = time.monotonic()
        certificate = certify_split_index_two(problem, keep, drop)
        checked = verify_split_index_two(problem, certificate)
        output.append({"name": name, "records": len(instance.records),
                       "components": len(instance.orders), "certificate": certificate,
                       "summary": checked, "seconds": time.monotonic() - started})
        print(f"arithmetic {name}: index={checked['index']}, "
              f"target_member={checked['target_member']}, "
              f"primary_parts={checked['primary_parts']}", flush=True)
    return output


def _implementation_head(git: str) -> str:
    head = baseline.implementation_head(git)
    name = "code/bf_solver_preprocessing.py"
    payload = subprocess.check_output([git, "-C", str(ROOT), "show", f"{head}:{name}"])
    if payload.replace(b"\r\n", b"\n") != (ROOT / name).read_bytes().replace(b"\r\n", b"\n"):
        raise ValueError("commit the frozen Round2 implementation before running controls")
    return head


def run_round(git: str, s3_path: Optional[Path]) -> dict[str, object]:
    head = _implementation_head(git)
    started = time.monotonic()
    instances, controls, inputs = _load_inputs(git, s3_path)
    gates = arithmetic_gates(instances)
    preparation_seconds = time.monotonic() - started
    records: list[dict[str, object]] = []
    pilot = instances["pilot"]
    for control in controls:
        entry: dict[str, object] = {
            "phase": control.spec.phase, "case": baseline._case_json(control),
            "result": None, "not_run_reason": "", "residue_verification_seconds": None,
        }
        if baseline._may_run(control.spec.phase, records):
            result = solve_filtered(control.problem)
            if result.status == "completed_exact_scope":
                raise ArithmeticError(f"{control.spec.name}: negative contradicts verified control")
            if result.status == "worker_error":
                raise RuntimeError(f"{control.spec.name}: {result.reason}")
            if result.status == "solution":
                check_started = time.monotonic()
                verify_group_solution(pilot, result.indices, control.problem.target, control.residues)
                entry["residue_verification_seconds"] = time.monotonic() - check_started
            entry["result"] = asdict(result)
            print(f"{control.spec.name}: {result.status} ({result.wall_seconds:.3f}s, "
                  f"{result.candidates} full-target checks)", flush=True)
        else:
            entry["not_run_reason"] = "support-3 gate did not pass"
        records.append(entry)
    return {
        "schema": SCHEMA, "baseline_commit": baseline.BASELINE, "implementation_commit": head,
        "python": platform.python_version(), "platform": platform.platform(),
        "source_sha256": sources(), "source_hash_normalization": "CRLF-to-LF",
        "inputs": inputs, "protocol": protocol(), "protocol_sha256": protocol_hash(),
        "preparation_seconds": preparation_seconds, "arithmetic_gates": gates,
        "cases": records, "counterexamples": 0,
    }


def _read_result(raw: object) -> SearchResult:
    if not isinstance(raw, dict) or set(raw) != set(SearchResult.__dataclass_fields__):
        raise ValueError("malformed filtered result")
    if raw["status"] not in ("solution", "completed_exact_scope", "resource_limit",
                             "timeout_enforced", "worker_error") \
            or not isinstance(raw["reason"], str) or not isinstance(raw["memory_measurement"], str):
        raise ValueError("invalid filtered outcome")
    if not isinstance(raw["indices"], (list, tuple)) \
            or any(not baseline._integer(i) for i in raw["indices"]):
        raise ValueError("invalid candidate indices")
    for key in ("left_entries", "right_entries", "candidates"):
        if not baseline._integer(raw[key]) or raw[key] < 0:
            raise ValueError("invalid search counters")
    for key in ("projection_seconds", "search_seconds", "wall_seconds", "verification_seconds"):
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, (float, int)) \
                or not math.isfinite(value) or value < 0:
            raise ValueError("invalid search timing")
    peak = raw["peak_rss_bytes"]
    if peak is not None and (not baseline._integer(peak) or peak < 0):
        raise ValueError("invalid RSS measurement")
    return SearchResult(**{**raw, "indices": tuple(raw["indices"])})


def verify_report(report: dict, git: str, s3_path: Optional[Path]) -> dict[str, object]:
    """Check every gate/candidate directly; no search or gate-generation calls."""
    if report["schema"] != SCHEMA or report["baseline_commit"] != baseline.BASELINE \
            or report["protocol"] != protocol() or report["protocol_sha256"] != protocol_hash() \
            or report["source_sha256"] != sources() \
            or report["source_hash_normalization"] != "CRLF-to-LF":
        raise ValueError("Round2 provenance/protocol differs")
    head = report["implementation_commit"]
    if not isinstance(head, str) or len(head) != 40 \
            or any(c not in "0123456789abcdef" for c in head):
        raise ValueError("invalid implementation commit")
    instances, controls, inputs = _load_inputs(git, s3_path)
    if report["inputs"] != inputs or report["counterexamples"] != 0:
        raise ValueError("Round2 input scope differs")
    gates = report["arithmetic_gates"]
    if [entry["name"] for entry in gates] != list(instances):
        raise ValueError("missing or repeated arithmetic instance")
    for entry in gates:
        instance = instances[entry["name"]]
        if entry["records"] != len(instance.records) or entry["components"] != len(instance.orders):
            raise ValueError("arithmetic scope differs")
        certificate = entry["certificate"]
        if (certificate["keep"], certificate["drop"]) != _relation(instance):
            raise ValueError("certificate uses a different split relation")
        summary = verify_split_index_two(_group_problem(instance), certificate)
        if entry["summary"] != summary:
            raise ValueError("arithmetic summary differs from checked minors")
    if not isinstance(report["cases"], list) or len(report["cases"]) != len(controls):
        raise ValueError("missing or repeated control case")
    checked: list[dict[str, object]] = []
    calls = solutions = not_run = 0
    for entry, control in zip(report["cases"], controls):
        if entry["phase"] != control.spec.phase or entry["case"] != baseline._case_json(control):
            raise ValueError("control target, scope or mode differs")
        if baseline._may_run(control.spec.phase, checked):
            if entry["not_run_reason"]:
                raise ValueError("eligible case was not run")
            result = _read_result(entry["result"])
            if result.status in ("completed_exact_scope", "worker_error"):
                raise ValueError("negative/error on a verified control cannot be a completed run")
            if result.left_entries + result.right_entries > SearchLimits().max_enumerations \
                    or result.left_entries > SearchLimits().max_left_entries \
                    or result.candidates > SearchLimits().max_candidates:
                raise ValueError("out-of-budget counters")
            if result.status == "solution":
                if result.reason or result.wall_seconds >= 60 \
                        or (result.peak_rss_bytes is not None and result.peak_rss_bytes > 512 * 1024**2):
                    raise ValueError("out-of-budget candidate classified as a success")
                baseline.verify_subset(control.problem, result.indices)
                verify_group_solution(instances["pilot"], result.indices, control.problem.target,
                                      control.residues)
                solutions += 1
            elif result.indices or not result.reason:
                raise ValueError("non-solution must carry only an explicit limitation")
            calls += 1
        else:
            if entry["result"] is not None or entry["not_run_reason"] != "support-3 gate did not pass":
                raise ValueError("unrun phase violates its gate")
            not_run += 1
        checked.append(entry)
    return {"calls": calls, "solutions": solutions, "not_run": not_run,
            "support3_gate": baseline._gate(checked, 0, 3),
            "support5_gate": baseline._gate(checked, 1, 6), "arithmetic_instances": len(gates),
            "counterexamples": 0}


def validate_output(path: Path, replace_existing: bool) -> None:
    if not path.name.startswith("bf_solver_preprocessing") \
            or not (path.name.endswith(".json") or path.name.endswith(".json.gz")):
        raise ValueError("use a new bf_solver_preprocessing-prefixed report")
    if path.exists() and not replace_existing:
        raise FileExistsError("output already exists; no repeated pilot is authorized")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--git", default="git")
    parser.add_argument("--s3-report", type=Path, help="exact reviewed S3 snapshot, otherwise read its Git blob")
    parser.add_argument("--output", type=Path,
                        default=baseline.DEFAULT_INPUT.with_name("bf_solver_preprocessing.json.gz"))
    parser.add_argument("--protocol", action="store_true")
    parser.add_argument("--verify", type=Path)
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.protocol:
        print(json.dumps({"protocol": protocol(), "sha256": protocol_hash()}, indent=2))
        return
    if args.verify:
        raw = args.verify.read_bytes()
        report = json.loads(gzip.decompress(raw) if args.verify.suffix == ".gz" else raw)
        print(json.dumps(verify_report(report, args.git, args.s3_report), indent=2))
        return
    validate_output(args.output, args.replace)
    if args.s3_report is not None and args.output.resolve() == args.s3_report.resolve():
        parser.error("output cannot overwrite the reviewed arithmetic input")
    report = run_round(args.git, args.s3_report)
    summary = verify_report(report, args.git, args.s3_report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    with args.output.open("wb" if args.replace else "xb") as output:
        output.write(gzip.compress(payload, mtime=0) if args.output.suffix == ".gz" else payload)
    print(json.dumps(summary, indent=2), flush=True)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
