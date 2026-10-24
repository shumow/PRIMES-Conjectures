"""Track B: exact generated-subgroup membership with checkable certificates.

This is integer-coefficient membership, not Boolean subset search. Mixed
prime-power equations are embedded in a common ring for each prime, reduced
using minimum-valuation pivots, and recombined by CRT.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
import platform
import sys
import time
from typing import Literal, Optional, Sequence

from real_pool_verify import (
    RealInstance, instance_from_json, source_digest, verify_counterexample,
    verify_encoding, verify_obstruction, verify_saved_report,
)

Status = Literal["member", "nonmember", "unresolved"]
SCHEMA = "fs-reachability/v1"
STARTING_COMMIT = "4128b622e6ebaff530888aa91ad79a624d7a9679"
DEFAULT_INPUT = Path(__file__).resolve().parent.parent / "data" / "generated" / "real_pool_pilot.json.gz"
SCOPE = "integer-coefficient generated-subgroup membership, not Boolean feasibility"


@dataclass(frozen=True)
class Limits:
    seconds: float = 60.0
    work_units: int = 200_000_000
    cells: int = 1_000_000
    workspace_bytes: int = 512 * 1024 * 1024
    scalar_bits: int = 4096

    def __post_init__(self) -> None:
        if not math.isfinite(self.seconds) or self.seconds < 0:
            raise ValueError("seconds must be finite and nonnegative")
        for value in (self.work_units, self.cells, self.workspace_bytes, self.scalar_bits):
            if not isinstance(value, int) or isinstance(value, bool) or value < 0:
                raise ValueError("resource limits must be nonnegative integers")


@dataclass(frozen=True)
class PrimarySummary:
    prime: int
    exponent: int
    rows: int
    pivots: int
    pivot_valuations: tuple[int, ...]


@dataclass(frozen=True)
class MembershipResult:
    status: Status
    coefficients: tuple[int, ...] = ()
    character_modulus: int = 0
    character_terms: tuple[tuple[int, int], ...] = ()
    reason: str = ""
    seconds: float = 0.0
    work_units: int = 0
    peak_cells: int = 0
    workspace_bytes_estimate: int = 0
    completed_primary_systems: tuple[PrimarySummary, ...] = ()


class _LimitReached(Exception):
    pass


class _Guard:
    def __init__(self, limits: Limits):
        self.limits = limits
        self.started = time.monotonic()
        self.work = 0
        self.peak_cells = 0
        self.workspace_estimate = 0

    def consume(self, amount: int = 0) -> None:
        self.work += amount
        if self.work > self.limits.work_units:
            raise _LimitReached("work-unit budget")
        if time.monotonic() - self.started >= self.limits.seconds:
            raise _LimitReached("wall-time budget")

    def reserve(self, cells: int, estimated_bytes: int) -> None:
        self.peak_cells = max(self.peak_cells, cells)
        self.workspace_estimate = max(self.workspace_estimate, estimated_bytes)
        if cells > self.limits.cells:
            raise _LimitReached("matrix/input cell budget")
        if estimated_bytes > self.limits.workspace_bytes:
            raise _LimitReached("workspace representation estimate")
        self.consume()

    def scalar(self, value: int) -> None:
        if value.bit_length() > self.limits.scalar_bits:
            raise _LimitReached("scalar bit-length budget")


def _check_dimensions(orders: Sequence[int], vectors: Sequence[Sequence[int]],
                      target: Sequence[int]) -> None:
    if len(target) != len(orders) or any(len(vector) != len(orders) for vector in vectors):
        raise ValueError("group/vector/target dimensions do not match")
    if any(not isinstance(m, int) or isinstance(m, bool) or m < 2 for m in orders):
        raise ValueError("component orders must be integers at least two")
    if any(not isinstance(v, int) or isinstance(v, bool)
           for vector in vectors for v in vector) or any(
               not isinstance(v, int) or isinstance(v, bool) for v in target):
        raise ValueError("group entries must be integers")


def _prime_power(order: int, guard: _Guard) -> tuple[int, int]:
    guard.scalar(order)
    q = 2
    while q * q <= order and order % q:
        guard.consume(1)
        q = 3 if q == 2 else q + 2
    if q * q > order:
        return order, 1
    exponent, remainder = 0, order
    while remainder % q == 0:
        guard.consume(1)
        remainder //= q
        exponent += 1
    if remainder != 1:
        raise ValueError("each component order must be a prime power")
    return q, exponent


def verify_certificate(orders: Sequence[int], vectors: Sequence[Sequence[int]],
                       target: Sequence[int], result: MembershipResult) -> None:
    """Independent direct proof checks; no elimination or prime decomposition."""
    _check_dimensions(orders, vectors, target)
    if result.status == "member":
        exponent = math.lcm(*orders) if orders else 1
        if (len(result.coefficients) != len(vectors) or result.character_modulus
                or result.character_terms or result.reason):
            raise ValueError("malformed membership certificate")
        if any(not isinstance(c, int) or isinstance(c, bool) or not 0 <= c < exponent
               for c in result.coefficients):
            raise ValueError("coefficients must be canonical integers modulo the group exponent")
        for j, order in enumerate(orders):
            if sum(c * vector[j] for c, vector in zip(result.coefficients, vectors)) % order \
                    != target[j] % order:
                raise ValueError("integer coefficients do not reproduce the target")
    elif result.status == "nonmember":
        if result.coefficients or result.reason:
            raise ValueError("malformed nonmembership certificate")
        if (not isinstance(result.character_modulus, int) or isinstance(result.character_modulus, bool)
                or any(not isinstance(value, int) or isinstance(value, bool)
                       for term in result.character_terms for value in term)):
            raise ValueError("character modulus, indices and coefficients must be integers")
        verify_obstruction(orders, vectors, target, result.character_modulus,
                           result.character_terms)
    elif result.status == "unresolved":
        if (not result.reason or result.coefficients or result.character_modulus
                or result.character_terms):
            raise ValueError("unresolved must carry only an explicit limitation, not a proof")
    else:
        raise ValueError("unknown membership status")


def _row_character(row: int, operations: Sequence[tuple[str, int, int, int]], rows: int,
                   modulus: int, guard: _Guard) -> list[int]:
    coefficients = [0] * rows
    coefficients[row] = 1
    for operation, row, source, multiplier in reversed(operations):
        guard.consume(1)
        if operation == "swap":
            coefficients[row], coefficients[source] = coefficients[source], coefficients[row]
        elif operation == "scale":
            coefficients[row] = coefficients[row] * multiplier % modulus
        elif operation == "subtract":
            coefficients[source] = (coefficients[source] - multiplier * coefficients[row]) % modulus
        else:
            raise ArithmeticError("unknown recorded row operation")
    return coefficients


def _solve_primary(orders: Sequence[int], vectors: Sequence[Sequence[int]],
                   target: Sequence[int], columns: Sequence[int], prime: int,
                   exponent: int, guard: _Guard) -> tuple[
                       Optional[list[int]], int, tuple[tuple[int, int], ...], PrimarySummary]:
    modulus = prime**exponent
    guard.scalar(modulus)
    rows, variables = len(columns), len(vectors)
    cells = len(orders) * variables + rows * (variables + 1)
    # Deliberately conservative container/int/log estimate; this is not RSS.
    integer_bytes = sys.getsizeof(modulus)
    operation_bound = rows * min(rows, variables) + 2 * min(rows, variables)
    estimate = (cells * (integer_bytes + 8) + 128 * operation_bound
                + 128 * (rows + variables + len(orders)))
    guard.reserve(cells, estimate)
    weights = [modulus // orders[j] for j in columns]
    matrix = [[(vector[j] % orders[j]) * weight for vector in vectors]
              for j, weight in zip(columns, weights)]
    rhs = [(target[j] % orders[j]) * weight for j, weight in zip(columns, weights)]
    permutation = list(range(variables))
    operations: list[tuple[str, int, int, int]] = []
    pivot_divisors: list[int] = []
    pivot_valuations: list[int] = []

    def obstruction(row: int, character_modulus: int) -> tuple[
            Optional[list[int]], int, tuple[tuple[int, int], ...], PrimarySummary]:
        coefficients = _row_character(row, operations, rows, modulus, guard)
        terms = tuple((j, coefficient * weight % character_modulus)
                      for j, coefficient, weight in zip(columns, coefficients, weights)
                      if coefficient * weight % character_modulus)
        common = math.gcd(character_modulus, *(coefficient for _, coefficient in terms))
        if common > 1:
            character_modulus //= common
            terms = tuple((j, coefficient // common) for j, coefficient in terms)
        summary = PrimarySummary(prime, exponent, rows, len(pivot_divisors),
                                 tuple(pivot_valuations))
        return None, character_modulus, terms, summary

    k = 0
    while k < min(rows, variables):
        best = modulus
        location: Optional[tuple[int, int]] = None
        for i in range(k, rows):
            guard.consume(variables - k)
            for j in range(k, variables):
                value = matrix[i][j]
                if value:
                    divisor = math.gcd(value, modulus)
                    if divisor < best:
                        best, location = divisor, (i, j)
                        if best == 1:
                            break
            if best == 1:
                break
        if location is None:
            break
        i, j = location
        if i != k:
            matrix[k], matrix[i] = matrix[i], matrix[k]
            rhs[k], rhs[i] = rhs[i], rhs[k]
            operations.append(("swap", k, i, 1))
        if j != k:
            for row in matrix:
                row[k], row[j] = row[j], row[k]
            permutation[k], permutation[j] = permutation[j], permutation[k]
            guard.consume(rows)
        unit_inverse = pow(matrix[k][k] // best, -1, modulus)
        if unit_inverse != 1:
            matrix[k] = [(value * unit_inverse) % modulus for value in matrix[k]]
            rhs[k] = rhs[k] * unit_inverse % modulus
            operations.append(("scale", k, k, unit_inverse))
            guard.consume(variables + 1)
        if rhs[k] % best:
            return obstruction(k, best)
        valuation, power = 0, best
        while power > 1:
            power //= prime
            valuation += 1
        pivot_divisors.append(best)
        pivot_valuations.append(valuation)
        pivot = matrix[k]
        for i in range(k + 1, rows):
            value = matrix[i][k]
            if not value:
                continue
            if value % best:
                raise ArithmeticError("pivot did not have minimum prime valuation")
            multiplier = value // best
            guard.consume(variables - k + 1)
            matrix[i][k + 1:] = [
                (a - multiplier * b) % modulus for a, b in zip(matrix[i][k + 1:], pivot[k + 1:])]
            matrix[i][k] = 0
            rhs[i] = (rhs[i] - multiplier * rhs[k]) % modulus
            operations.append(("subtract", i, k, multiplier))
        k += 1

    for i in range(k, rows):
        guard.consume(variables + 1)
        if any(matrix[i]):
            raise ArithmeticError("nonzero row remained after pivot exhaustion")
        if rhs[i]:
            return obstruction(i, modulus)
    solution = [0] * variables
    for i in range(k - 1, -1, -1):
        guard.consume(variables - i)
        residual = (rhs[i] - sum(value * x for value, x in
                                zip(matrix[i][i + 1:], solution[i + 1:]))) % modulus
        divisor = pivot_divisors[i]
        if residual % divisor:
            raise ArithmeticError("triangular back-substitution lost divisibility")
        solution[i] = residual // divisor
    original = [0] * variables
    for i, value in enumerate(solution):
        original[permutation[i]] = value
    return original, 0, (), PrimarySummary(prime, exponent, rows, k, tuple(pivot_valuations))


def membership(orders: Sequence[int], vectors: Sequence[Sequence[int]],
               target: Sequence[int], *, limits: Limits = Limits()) -> MembershipResult:
    """Decide exact integer membership, or explicitly stop at a resource limit."""
    _check_dimensions(orders, vectors, target)
    guard = _Guard(limits)
    summaries: list[PrimarySummary] = []

    def finish(status: Status, coefficients: tuple[int, ...] = (), modulus: int = 0,
               terms: tuple[tuple[int, int], ...] = (), reason: str = "") -> MembershipResult:
        result = MembershipResult(status, coefficients, modulus, terms, reason,
                                  time.monotonic() - guard.started, guard.work,
                                  guard.peak_cells, guard.workspace_estimate, tuple(summaries))
        verify_certificate(orders, vectors, target, result)
        return result

    try:
        guard.consume()
        guard.reserve(len(orders) * len(vectors),
                      len(orders) * len(vectors) * 64)
        primary: dict[int, tuple[list[int], int]] = {}
        cache: dict[int, tuple[int, int]] = {}
        for j, order in enumerate(orders):
            guard.consume(len(vectors) + 1)
            for vector in vectors:
                guard.scalar(vector[j])
            guard.scalar(target[j])
            if order not in cache:
                cache[order] = _prime_power(order, guard)
            prime, exponent = cache[order]
            if prime not in primary:
                primary[prime] = ([], exponent)
            columns, previous_exponent = primary[prime]
            columns.append(j)
            primary[prime] = (columns, max(previous_exponent, exponent))
        pieces: list[tuple[int, list[int]]] = []
        for prime, (columns, exponent) in sorted(primary.items()):
            solution, modulus, terms, summary = _solve_primary(
                orders, vectors, target, columns, prime, exponent, guard)
            if solution is None:
                return finish("nonmember", modulus=modulus, terms=terms)
            summaries.append(summary)
            pieces.append((prime**exponent, solution))
        total_modulus = math.prod(modulus for modulus, _ in pieces)
        guard.scalar(total_modulus)
        coefficients = [0] * len(vectors)
        for modulus, solution in pieces:
            partial = total_modulus // modulus
            multiplier = partial * pow(partial, -1, modulus)
            for i, value in enumerate(solution):
                coefficients[i] = (coefficients[i] + multiplier * value) % total_modulus
            guard.consume(len(vectors))
        return finish("member", coefficients=tuple(coefficients))
    except _LimitReached as exc:
        return finish("unresolved", reason=str(exc))


@dataclass(frozen=True)
class PilotCase:
    key: str
    cohort: str
    size: int
    target_kind: Literal["real_lp", "planted_control"]
    instance: RealInstance
    target: tuple[int, ...]
    residues: tuple[int, int]
    prior_has_obstruction: bool


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError("expected an object with string keys")
    return value


def _array(value: object) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected an array")
    return list(value)


def _int(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return int(value, 16 if value.startswith("0x") else 10)
    raise ValueError("expected an integer")


def load_cases(path: Path) -> tuple[str, list[PilotCase]]:
    payload = path.read_bytes()
    data = _object(json.loads(gzip.decompress(payload) if path.suffix == ".gz" else payload))
    verify_saved_report(data)
    cases: list[PilotCase] = []
    for value in _array(data["runs"]):
        run = _object(value)
        if run["status"] != "encoded_and_verified":
            continue
        instance = instance_from_json(run["instance"])
        cohort = run["name"]
        if not isinstance(cohort, str):
            raise ValueError("invalid cohort name")
        for value in _array(run["benchmarks"]):
            case = _object(value)
            size = _int(case["size"])
            if case["target_kind"] == "real_lp":
                kind: Literal["real_lp", "planted_control"] = "real_lp"
            elif case["target_kind"] == "planted_control":
                kind = "planted_control"
            else:
                raise ValueError("unknown target kind")
            target = tuple(_int(v) for v in _array(case["target"]))
            raw_residues = _array(case["residues_hex"])
            if len(raw_residues) != 2:
                raise ValueError("invalid multiplicative target")
            prior = _object(case["necessary_checks"])["has_obstruction"]
            if not isinstance(prior, bool):
                raise ValueError("invalid prior check flag")
            cases.append(PilotCase(f"{cohort}:{size}:{kind}", cohort, size, kind, instance,
                                   target, (_int(raw_residues[0]), _int(raw_residues[1])), prior))
    if len({case.key for case in cases}) != len(cases):
        raise ValueError("duplicate case identifiers")
    return hashlib.sha256(payload).hexdigest(), cases


def verify_instance_certificate(case: PilotCase, result: MembershipResult) -> dict[str, object]:
    """Recheck integer coefficients in the original multiplicative unit groups."""
    instance = case.instance
    verify_encoding(instance)
    verify_certificate(instance.orders, instance.vectors[:case.size], case.target, result)
    if result.status != "member":
        return {"direct_group_check": True, "multiplicative_check": "not applicable"}
    minus = plus = 1
    for record, coefficient in zip(instance.records[:case.size], result.coefficients):
        minus = minus * pow(record.p, coefficient, instance.lambda_minus) % instance.lambda_minus
        plus = plus * pow(record.p, coefficient, instance.lambda_plus) % instance.lambda_plus
    if (minus, plus) != case.residues:
        raise ValueError("integer witness fails original multiplicative target")
    boolean = all(value in (0, 1) for value in result.coefficients)
    eligible = boolean and sum(result.coefficients) >= 3 and sum(result.coefficients) % 2 == 1
    counterexample = None
    if eligible and case.target == instance.target:
        indices = [i for i, value in enumerate(result.coefficients) if value]
        counterexample = hex(verify_counterexample(instance.records, indices))
    return {"direct_group_check": True, "multiplicative_check": True,
            "integer_witness_is_boolean": boolean, "boolean_subset_eligible": bool(eligible),
            "independently_verified_counterexample_hex": counterexample}


def _result_json(result: MembershipResult) -> dict[str, object]:
    value = asdict(result)
    value["coefficients"] = [hex(c) for c in result.coefficients]
    value["character_modulus"] = hex(result.character_modulus)
    value["character_terms"] = [[j, hex(c)] for j, c in result.character_terms]
    return value


def _read_result(value: object) -> MembershipResult:
    raw = _object(value)
    status = raw["status"]
    if status not in ("member", "nonmember", "unresolved"):
        raise ValueError("unknown result status")
    if status == "member":
        kind: Status = "member"
    elif status == "nonmember":
        kind = "nonmember"
    else:
        kind = "unresolved"
    reason = raw["reason"]
    if not isinstance(reason, str):
        raise ValueError("invalid limit reason")
    terms: list[tuple[int, int]] = []
    for item in _array(raw["character_terms"]):
        pair = _array(item)
        if len(pair) != 2:
            raise ValueError("invalid character term")
        terms.append((_int(pair[0]), _int(pair[1])))
    return MembershipResult(kind, tuple(_int(c) for c in _array(raw["coefficients"])),
                            _int(raw["character_modulus"]), tuple(terms), reason)


def analyze(input_path: Path = DEFAULT_INPUT, *, limits: Limits = Limits(),
            case_keys: Optional[Sequence[str]] = None) -> dict[str, object]:
    input_hash, cases = load_cases(input_path)
    if case_keys is not None:
        wanted = set(case_keys)
        if len(wanted) != len(case_keys) or not wanted.issubset({case.key for case in cases}):
            raise ValueError("unknown or repeated case identifier")
        cases = [case for case in cases if case.key in wanted]
    if not cases:
        raise ValueError("no selected cases")
    outputs: list[dict[str, object]] = []
    for case in cases:
        result = membership(case.instance.orders, case.instance.vectors[:case.size],
                            case.target, limits=limits)
        verification = verify_instance_certificate(case, result)
        if case.target_kind == "planted_control" and result.status == "nonmember":
            raise ArithmeticError("nonmembership contradicts verified planted witness")
        outputs.append({
            "key": case.key, "cohort": case.cohort, "size": case.size,
            "target_kind": case.target_kind, "prior_prime_field_obstruction": case.prior_has_obstruction,
            "result": _result_json(result), "verification": verification,
        })
        print(f"{case.key}: {result.status} ({result.seconds:.3f}s, "
              f"{result.work_units} work units)", flush=True)
    return {
        "schema": SCHEMA, "starting_commit": STARTING_COMMIT,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(), "input_sha256": input_hash,
        "source_sha256": {"fs_reachability.py": source_digest(Path(__file__))},
        "source_hash_normalization": "CRLF-to-LF", "limits": asdict(limits),
        "cases": outputs,
        "scope": SCOPE,
        "memory_scope": "matrix/input cell limit and conservative workspace estimate, not an OS RSS cap",
        "timing_scope": "per-case membership computation; input/certificate verification is separate",
    }


def verify_analysis(value: object, input_path: Path = DEFAULT_INPUT) -> dict[str, int]:
    """Verify saved proof content without calling membership or its elimination."""
    report = _object(value)
    if (report["schema"] != SCHEMA or report["source_hash_normalization"] != "CRLF-to-LF"
            or report["starting_commit"] != STARTING_COMMIT or report["scope"] != SCOPE):
        raise ValueError("unknown report schema/provenance normalization")
    if _object(report["source_sha256"]) != {"fs_reachability.py": source_digest(Path(__file__))}:
        raise ValueError("Track B source hash mismatch")
    input_hash, cases = load_cases(input_path)
    if report["input_sha256"] != input_hash:
        raise ValueError("frozen pilot artifact hash mismatch")
    indexed = {case.key: case for case in cases}
    seen: set[str] = set()
    summary = dict(cases=0, member=0, nonmember=0, unresolved=0, counterexamples=0)
    for value in _array(report["cases"]):
        raw = _object(value)
        key = raw["key"]
        if not isinstance(key, str) or key not in indexed or key in seen:
            raise ValueError("unknown or repeated case")
        seen.add(key)
        case = indexed[key]
        if (raw["cohort"] != case.cohort or raw["size"] != case.size
                or raw["target_kind"] != case.target_kind
                or raw["prior_prime_field_obstruction"] is not case.prior_has_obstruction):
            raise ValueError("case scope differs from the frozen input")
        result = _read_result(raw["result"])
        verification = verify_instance_certificate(case, result)
        if raw["verification"] != verification:
            raise ValueError("incorrect independently verified result annotations")
        if case.target_kind == "planted_control" and result.status == "nonmember":
            raise ValueError("negative claim contradicts planted witness")
        summary["cases"] += 1
        summary[result.status] += 1
        if verification.get("independently_verified_counterexample_hex") is not None:
            summary["counterexamples"] += 1
    if not seen:
        raise ValueError("empty analysis")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output", type=Path, default=DEFAULT_INPUT.with_name("fs_reachability.json.gz"))
    parser.add_argument("--verify", type=Path, help="verify a saved Track B report without elimination")
    parser.add_argument("--replace", action="store_true")
    parser.add_argument("--case", action="append", dest="case_keys")
    parser.add_argument("--seconds", type=float, default=60.0)
    parser.add_argument("--max-work", type=int, default=200_000_000)
    parser.add_argument("--max-cells", type=int, default=1_000_000)
    args = parser.parse_args()
    if args.verify:
        payload = args.verify.read_bytes()
        if args.verify.suffix == ".gz":
            payload = gzip.decompress(payload)
        print(json.dumps(verify_analysis(json.loads(payload), args.input), indent=2))
        return
    if args.output.resolve() == args.input.resolve():
        parser.error("output cannot replace the frozen input artifact")
    if args.output.exists() and not args.replace:
        parser.error("output exists; use --replace or another --output")
    report = analyze(args.input, limits=Limits(seconds=args.seconds, work_units=args.max_work,
                                             cells=args.max_cells), case_keys=args.case_keys)
    verify_analysis(report, args.input)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    with args.output.open("wb" if args.replace else "xb") as output:
        output.write(gzip.compress(payload, mtime=0) if args.output.suffix == ".gz" else payload)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
