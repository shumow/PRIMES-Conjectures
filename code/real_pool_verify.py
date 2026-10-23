"""Independent arithmetic verification for the real-pool pilot.

This module does not import the harvester, discrete-log builder or A-series
solvers. Prime records carry full-factor Lucas primality certificates.
"""
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
import argparse
import gzip
import hashlib
import json
import math
from typing import Literal, Optional, Sequence

Factors = tuple[tuple[int, int], ...]


@dataclass(frozen=True)
class PrimeRecord:
    p: int
    minus: Factors
    plus: Factors
    witness: int
    candidate_index: int = 0


@dataclass(frozen=True)
class UnitBlock:
    side: Literal["minus", "plus"]
    prime: int
    exponent: int
    generator: int
    columns: tuple[int, ...]

    @property
    def modulus(self) -> int:
        return self.prime**self.exponent

    @property
    def order(self) -> int:
        return (self.prime - 1) * self.prime**(self.exponent - 1)


@dataclass(frozen=True)
class RealInstance:
    records: tuple[PrimeRecord, ...]
    excluded_nonunits: tuple[PrimeRecord, ...]
    lambda_minus: int
    lambda_plus: int
    blocks: tuple[UnitBlock, ...]
    orders: tuple[int, ...]
    vectors: tuple[tuple[int, ...], ...]
    target: tuple[int, ...]


def trial_factors(n: int) -> dict[int, int]:
    if n < 1:
        raise ValueError("factorization input must be positive")
    factors: dict[int, int] = {}
    q = 2
    while q * q <= n:
        while n % q == 0:
            factors[q] = factors.get(q, 0) + 1
            n //= q
        q += 1
    if n > 1:
        factors[n] = factors.get(n, 0) + 1
    return factors


def factor_product(factors: Factors) -> int:
    seen: set[int] = set()
    product = 1
    for q, exponent in factors:
        if q in seen or q < 2 or exponent < 1 or trial_factors(q) != {q: 1}:
            raise ValueError("factorization must contain distinct primes and positive exponents")
        seen.add(q)
        product *= q**exponent
    return product


def verify_prime(record: PrimeRecord) -> None:
    p = record.p
    if p < 3 or p % 80 != 3:
        raise ValueError("pool prime must be 3 modulo 80")
    if factor_product(record.minus) != p - 1 or factor_product(record.plus) != p + 1:
        raise ValueError("factorizations do not reconstruct p-1 and p+1")
    a = record.witness
    if not 1 < a < p or pow(a, p - 1, p) != 1:
        raise ValueError("invalid Lucas primality witness")
    if any(math.gcd(pow(a, (p - 1) // q, p) - 1, p) != 1
           for q, _ in record.minus):
        raise ValueError("Lucas witness does not certify full order")


def crt_exponent(values: Sequence[int], moduli: Sequence[int]) -> int:
    if len(values) != len(moduli) or not moduli:
        raise ValueError("CRT requires matching nonempty vectors")
    total = math.prod(moduli)
    if any(m < 2 for m in moduli) or any(
            math.gcd(m, n) != 1 for i, m in enumerate(moduli) for n in moduli[i + 1:]):
        raise ValueError("CRT component orders must be pairwise coprime")
    return sum(value * (total // modulus) * pow(total // modulus, -1, modulus)
               for value, modulus in zip(values, moduli)) % total


def verify_encoding(instance: RealInstance) -> None:
    all_records = instance.records + instance.excluded_nonunits
    if not all_records or len({record.p for record in all_records}) != len(all_records):
        raise ValueError("instance needs distinct prime records")
    for record in all_records:
        verify_prime(record)
    lm = math.lcm(*(record.p - 1 for record in all_records))
    lp = math.lcm(*(record.p + 1 for record in all_records))
    if (instance.lambda_minus, instance.lambda_plus) != (lm, lp) or math.gcd(lm, lp) != 2:
        raise ValueError("incorrect full-pool LCMs or overlapping odd supports")
    if any(math.gcd(record.p, lm * lp) != 1 for record in instance.records):
        raise ValueError("retained nonunit")
    if any(math.gcd(record.p, lm * lp) == 1 for record in instance.excluded_nonunits):
        raise ValueError("excluded record is a unit")
    dimension = len(instance.orders)
    if not dimension or len(instance.target) != dimension:
        raise ValueError("invalid target dimension")
    if len(instance.vectors) != len(instance.records):
        raise ValueError("record/vector count mismatch")
    for vector in instance.vectors + (instance.target,):
        if len(vector) != dimension or any(not 0 <= v < m
                                           for v, m in zip(vector, instance.orders)):
            raise ValueError("noncanonical group vector")
    if instance.orders[-1] != 2 or instance.target[-1] != 1:
        raise ValueError("last coordinate must encode odd cardinality / modulo 4")
    if any(vector[-1] != 1 for vector in instance.vectors):
        raise ValueError("incorrect modulo-4 prime image")
    expected: dict[tuple[str, int], int] = {}
    for record in all_records:
        for side, factors in (("minus", record.minus), ("plus", record.plus)):
            for q, exponent in factors:
                if q != 2:
                    expected[side, q] = max(expected.get((side, q), 0), exponent)
    actual: dict[tuple[str, int], int] = {}
    covered: list[int] = []
    for block in instance.blocks:
        key = block.side, block.prime
        if key in actual or block.side not in ("minus", "plus") or block.exponent < 1:
            raise ValueError("duplicate or invalid block")
        actual[key] = block.exponent
        if block.prime < 3 or trial_factors(block.prime) != {block.prime: 1}:
            raise ValueError("block base is not an odd prime")
        if not block.columns or any(not 0 <= j < dimension - 1 for j in block.columns):
            raise ValueError("invalid block coordinate indices")
        covered.extend(block.columns)
        orders = tuple(instance.orders[j] for j in block.columns)
        if math.prod(orders) != block.order or any(len(trial_factors(m)) != 1 for m in orders):
            raise ValueError("block omits a prime-power part of phi(q^e)")
        crt_exponent([0] * len(orders), orders)
        modulus, order = block.modulus, block.order
        g = block.generator
        if math.gcd(g, modulus) != 1 or pow(g, order, modulus) != 1 or any(
                pow(g, order // ell, modulus) == 1 for ell in trial_factors(order)):
            raise ValueError("block generator has incorrect order")
        for record, vector in zip(instance.records, instance.vectors):
            exponent = crt_exponent([vector[j] for j in block.columns], orders)
            if pow(g, exponent, modulus) != record.p % modulus:
                raise ValueError("discrete-log vector fails residue reconstruction")
        exponent = crt_exponent([instance.target[j] for j in block.columns], orders)
        target = 1 if block.side == "minus" else modulus - 1
        if pow(g, exponent, modulus) != target:
            raise ValueError("target fails residue reconstruction")
    if actual != expected or sorted(covered) != list(range(dimension - 1)):
        raise ValueError("missing, extra or overlapping prime-power blocks")


def subset_residues(records: Sequence[PrimeRecord], indices: Sequence[int],
                    lm: int, lp: int) -> tuple[int, int]:
    if len(set(indices)) != len(indices) or any(not 0 <= i < len(records) for i in indices):
        raise ValueError("subset indices must be distinct and in range")
    n = math.prod(records[i].p for i in indices)
    return n % lm, n % lp


def verify_group_solution(instance: RealInstance, indices: Sequence[int],
                          target: Sequence[int], residues: tuple[int, int]) -> None:
    if len(indices) < 3 or len(indices) % 2 != 1:
        raise ValueError("solution must select at least three, and an odd number of, primes")
    actual = subset_residues(instance.records, indices, instance.lambda_minus,
                             instance.lambda_plus)
    if actual != residues:
        raise ValueError("solution fails independent multiplicative residues")
    if len(target) != len(instance.orders) or any(
            sum(instance.vectors[i][j] for i in indices) % order != target[j]
            for j, order in enumerate(instance.orders)):
        raise ValueError("solution fails group target")


def verify_obstruction(orders: Sequence[int], vectors: Sequence[Sequence[int]],
                       target: Sequence[int], modulus: int,
                       terms: Sequence[tuple[int, int]]) -> None:
    """Check an annihilating character, independently of the elimination code."""
    if modulus < 2 or not terms or len(target) != len(orders):
        raise ValueError("invalid obstruction")
    if len({j for j, _ in terms}) != len(terms):
        raise ValueError("duplicate obstruction coordinates")
    for j, coefficient in terms:
        if not 0 <= j < len(orders) or not 0 < coefficient < modulus:
            raise ValueError("invalid obstruction term")
        if coefficient * orders[j] % modulus:
            raise ValueError("character is not defined on the component group")
    if any(len(vector) != len(orders) or
           sum(coefficient * vector[j] for j, coefficient in terms) % modulus
           for vector in vectors):
        raise ValueError("character does not annihilate every pool vector")
    if sum(coefficient * target[j] for j, coefficient in terms) % modulus == 0:
        raise ValueError("character does not separate the target")


def polynomial_congruence(n: int, constant: int = -1) -> bool:
    """Independent ordinary convolution, then reduction by X^5-1."""
    if n < 2:
        raise ValueError("congruence modulus/exponent must be at least two")

    def multiply(a: list[int], b: list[int]) -> list[int]:
        product = [0] * 9
        for i in range(5):
            for j in range(5):
                product[i + j] += a[i] * b[j]
        for degree in range(8, 4, -1):
            product[degree - 5] += product[degree]
        return [value % n for value in product[:5]]

    result = [1, 0, 0, 0, 0]
    base = [constant % n, 1, 0, 0, 0]
    exponent = n
    while exponent:
        if exponent & 1:
            result = multiply(result, base)
        base = multiply(base, base)
        exponent //= 2
    target = [constant % n, 0, 0, 0, 0]
    target[n % 5] = (target[n % 5] + 1) % n
    return result == target


def verify_counterexample(records: Sequence[PrimeRecord], indices: Sequence[int]) -> int:
    subset_residues(records, indices, 1, 1)
    if len(indices) < 3 or len(indices) % 2 != 1:
        raise ValueError("counterexample requires odd cardinality at least three")
    selected = [records[i] for i in indices]
    if len({record.p for record in selected}) != len(selected):
        raise ValueError("counterexample must be squarefree")
    for record in selected:
        verify_prime(record)
    n = math.prod(record.p for record in selected)
    if n % 5 == 0 or n * n % 5 == 1:
        raise ValueError("candidate lies outside the required counterexample class")
    if any((n - 1) % (record.p - 1) or (n + 1) % (record.p + 1)
           for record in selected):
        raise ValueError("candidate fails the two divisibility conditions")
    if not polynomial_congruence(n):
        raise ValueError("candidate fails independent direct polynomial verification")
    return n


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise ValueError("expected an object with string keys")
    return value


def _items(value: object) -> list[object]:
    if not isinstance(value, (list, tuple)):
        raise ValueError("expected an array")
    return list(value)


def _integer(value: object) -> int:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str):
        return int(value, 16 if value.startswith("0x") else 10)
    raise ValueError("expected an integer or an exact integer string")


def source_digest(path: Path) -> str:
    """Hash source with LF newlines so Git's Windows checkout filters are harmless."""
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def instance_from_json(value: object) -> RealInstance:
    data = _object(value)

    def record(value: object) -> PrimeRecord:
        raw = _object(value)
        minus = tuple(sorted((_integer(q), _integer(e))
                             for q, e in _object(raw["p_minus_1"]).items()))
        plus = tuple(sorted((_integer(q), _integer(e))
                            for q, e in _object(raw["p_plus_1"]).items()))
        return PrimeRecord(_integer(raw["p"]), minus, plus, _integer(raw["lucas_witness"]),
                           _integer(raw["candidate_index"]))

    blocks = []
    for value in _items(data["blocks"]):
        raw = _object(value)
        if raw["side"] == "minus":
            side: Literal["minus", "plus"] = "minus"
        elif raw["side"] == "plus":
            side = "plus"
        else:
            raise ValueError("invalid side")
        block = UnitBlock(side, _integer(raw["prime"]), _integer(raw["exponent"]),
                          _integer(raw["generator"]),
                          tuple(_integer(j) for j in _items(raw["columns"])))
        if _integer(raw["modulus"]) != block.modulus or _integer(raw["order"]) != block.order:
            raise ValueError("serialized block metadata is inconsistent")
        blocks.append(block)
    instance = RealInstance(
        tuple(record(value) for value in _items(data["records"])),
        tuple(record(value) for value in _items(data["excluded_nonunits"])),
        _integer(data["lambda_minus_hex"]), _integer(data["lambda_plus_hex"]),
        tuple(blocks), tuple(_integer(m) for m in _items(data["orders"])),
        tuple(tuple(_integer(v) for v in _items(row)) for row in _items(data["vectors"])),
        tuple(_integer(v) for v in _items(data["real_target"])),
    )
    if _integer(data["parity_column"]) != len(instance.orders) - 1:
        raise ValueError("incorrect parity-column metadata")
    expected_2adic = {"minus_exponent": 1, "plus_exponent": 2, "p_mod4": 3,
                      "target_parity": 1, "minimum_size": 3, "parity_replaces_mod4": True}
    if _object(data["automatic_2adic"]) != expected_2adic:
        raise ValueError("incorrect automatic 2-adic constraint metadata")
    verify_encoding(instance)
    return instance


def _close_number(value: object, expected: float) -> bool:
    return (isinstance(value, (int, float)) and not isinstance(value, bool)
            and math.isclose(value, expected, rel_tol=1e-12, abs_tol=1e-12))


def verify_metrics(instance: RealInstance, value: object) -> None:
    data = _object(value)
    n, d = len(instance.records), len(instance.orders)
    group_bits = sum(math.log2(order) for order in instance.orders)
    if (data["pool_size"] != n or data["components"] != d
            or _integer(data["group_order_hex"]) != math.prod(instance.orders)
            or data["distinct_vectors"] != len(set(instance.vectors))):
        raise ValueError("incorrect group or pool statistics")
    zero_counts = [sum(vector[j] == 0 for vector in instance.vectors) for j in range(d)]
    columns = [_object(column) for column in _items(data["components_detail"])]
    if len(columns) != d or not n:
        raise ValueError("invalid component statistics")
    forced_counts = [0] * d
    for block in instance.blocks:
        for j in block.columns:
            ell = next(iter(trial_factors(instance.orders[j])))
            expected = {"side": block.side, "prime": block.prime,
                        "exponent": block.exponent, "primary_prime": ell}
            if any(columns[j].get(key) != val for key, val in expected.items()):
                raise ValueError("incorrect component metadata")
            for record, vector in zip(instance.records, instance.vectors):
                sign = 1 if block.side == "minus" else -1
                forced = (record.p % block.prime == sign % block.prime
                          and (block.side == "minus" or ell != 2)
                          and (ell != block.prime
                               or record.p % block.modulus == sign % block.modulus))
                if forced:
                    if vector[j] != 0:
                        raise ValueError("claimed forced identity is not zero")
                    forced_counts[j] += 1
    for j, column in enumerate(columns):
        order = instance.orders[j]
        if (column["order"] != order or column["zeros"] != zero_counts[j]
                or column["forced_zeros"] != forced_counts[j]
                or not _close_number(column["literal_probability"], zero_counts[j] / n)
                or not _close_number(column["uniform_baseline"], 1 / order)):
            raise ValueError("incorrect identity statistics")
    squarefree_bits = 1 + sum(math.log2(block.prime - 1) for block in instance.blocks)
    expected_metrics = {
        "group_bits": group_bits, "pool_per_group_bit": n / group_bits,
        "squarefree_q_minus_1_model_bits": squarefree_bits,
        "prime_power_bits_missing_from_that_model": group_bits - squarefree_bits,
        "mean_literal_identity_fraction": sum(zero_counts) / (n * d),
        "mean_forced_identity_fraction": sum(forced_counts) / (n * d),
        "bit_weighted_identity_fraction": sum(zero_counts[j] * math.log2(order)
                                             for j, order in enumerate(instance.orders))
        / (n * group_bits),
    }
    if any(not _close_number(data[key], expected) for key, expected in expected_metrics.items()):
        raise ValueError("incorrect aggregate structure statistics")
    for value in _items(data["sampled_zero_correlations"]):
        pair = _object(value)
        indices = [_integer(j) for j in _items(pair["columns"])]
        if len(indices) != 2 or len(set(indices)) != 2 or any(not 0 <= j < d for j in indices):
            raise ValueError("invalid correlation pair")
        a, b = indices
        pa, pb = zero_counts[a] / n, zero_counts[b] / n
        joint = sum(v[a] == 0 and v[b] == 0 for v in instance.vectors) / n
        denominator = math.sqrt(pa * (1 - pa) * pb * (1 - pb))
        if (not _close_number(pair["joint_zero_probability"], joint)
                or not _close_number(pair["product_of_marginals"], pa * pb)
                or (not denominator and pair["phi"] is not None)
                or (denominator and not _close_number(pair["phi"], (joint - pa * pb) / denominator))):
            raise ValueError("incorrect correlation statistic")


def verify_harvest_metadata(instance: RealInstance, value: object) -> None:
    data = _object(value)
    config = _object(data["config"])
    b, bp = _integer(config["plus_bound"]), _integer(config["minus_bound"])
    if b < 3 or bp <= b:
        raise ValueError("invalid factor-base bounds")
    minus = [_integer(q) for q in _items(data["q_minus"])]
    plus = [_integer(q) for q in _items(data["q_plus"])]
    if (minus != [q for q in range(b + 1, bp + 1) if trial_factors(q) == {q: 1}]
            or plus != [q for q in range(3, b + 1) if q != 5 and trial_factors(q) == {q: 1}]):
        raise ValueError("incorrect declared factor bases")
    j = _integer(config["factors"])
    counts = _object(data["counts"])
    draws = _integer(counts["draws"])
    family = math.comb(len(minus), j)
    records = instance.records + instance.excluded_nonunits
    if (data["candidate_family_size"] != family or not 0 < draws <= _integer(config["candidate_cap"])
            or counts["accepted"] != len(records) or len(records) > _integer(config["pool_cap"])):
        raise ValueError("invalid harvest counts")
    if config["sampled"] is not True and config["sampled"] is not False:
        raise ValueError("sampling mode must be boolean")
    complete = config["sampled"] is False and draws == family
    if data["complete_family_scan"] is not complete:
        raise ValueError("incorrect family completeness claim")
    for record in records:
        fm, fp = dict(record.minus), dict(record.plus)
        if (not 1 <= record.candidate_index <= draws or fm.get(2) != 1 or fp.get(2) != 2
                or len(fm) - 1 != j or any(q not in minus or e != 1
                                                          for q, e in fm.items() if q != 2)
                or any(q not in plus for q in fp if q != 2)
                or any(q**e > _integer(config["prime_power_cap"]) for q, e in fp.items())
                or record.p >= 1 << 64):
            raise ValueError("record is outside the declared harvest family")


def _rank_mod(matrix: Sequence[Sequence[int]], prime: int) -> int:
    pivots: dict[int, list[int]] = {}
    for row in matrix:
        current = [value % prime for value in row]
        for pc, pivot in sorted(pivots.items()):
            coefficient = current[pc]
            if coefficient:
                current = [(a - coefficient * b) % prime for a, b in zip(current, pivot)]
        pc = next((j for j, value in enumerate(current) if value), None)
        if pc is not None:
            inverse = pow(current[pc], -1, prime)
            pivots[pc] = [value * inverse % prime for value in current]
    return len(pivots)


def verify_saved_report(value: object) -> dict[str, int]:
    data = _object(value)
    if data["schema"] != "real-pool-pilot/v1":
        raise ValueError("unknown pilot schema")
    if data["source_hash_normalization"] != "CRLF-to-LF":
        raise ValueError("unknown source-hash normalization")
    sources = _object(data["source_sha256"])
    expected_sources = {"real_pool_pilot.py", "real_pool_verify.py", "a4_solver.py",
                        "a6_oddsolver.py", "a7_lohniebuhr.py", "phase1a_calibration.py"}
    if set(sources) != expected_sources:
        raise ValueError("missing or unexpected source provenance")
    for name, expected_hash in sources.items():
        actual_hash = source_digest(Path(__file__).with_name(name))
        if actual_hash != expected_hash:
            raise ValueError(f"source hash mismatch: {name}")
    summary = dict(instances=0, prime_certificates=0, solutions=0, obstructions=0,
                   no_solution_claims=0, empty_harvests=0, counterexamples=0)
    counterexamples: set[int] = set()
    distinct_primes: set[int] = set()

    def check_obstructions(raw: object, instance: RealInstance,
                           vectors: Sequence[Sequence[int]], target: Sequence[int]) -> bool:
        checks = _object(raw)
        witnesses = [_object(item) for item in _items(checks["coordinate_obstructions"])]
        fields: dict[int, list[int]] = {}
        for j, order in enumerate(instance.orders):
            ell = next(iter(trial_factors(order)))
            fields.setdefault(ell, []).append(j)
        seen: set[int] = set()
        for value in _items(checks["prime_field_checks"]):
            entry = _object(value)
            ell = _integer(entry["prime"])
            if ell not in fields or ell in seen:
                raise ValueError("missing or repeated prime-field check")
            seen.add(ell)
            matrix = [[vector[j] % ell for vector in vectors] for j in fields[ell]]
            rhs = [target[j] % ell for j in fields[ell]]
            rank = _rank_mod(matrix, ell)
            consistent = _rank_mod([row + [b] for row, b in zip(matrix, rhs)], ell) == rank
            if entry["rows"] != len(fields[ell]) or entry["rank"] != rank \
                    or entry["consistent"] is not consistent:
                raise ValueError("incorrect prime-field rank or consistency")
            if entry["consistent"] is False:
                witnesses.append(_object(entry["obstruction"]))
            elif entry["consistent"] is not True:
                raise ValueError("consistency status must be boolean")
        if seen != set(fields):
            raise ValueError("missing prime-field checks")
        for witness in witnesses:
            terms = []
            for value in _items(witness["terms"]):
                pair = _items(value)
                if len(pair) != 2:
                    raise ValueError("invalid character term")
                terms.append((_integer(pair[0]), _integer(pair[1])))
            verify_obstruction(instance.orders, vectors, target,
                               _integer(witness["modulus"]), terms)
            summary["obstructions"] += 1
        if checks["has_obstruction"] is not bool(witnesses):
            raise ValueError("obstruction summary disagrees with certificates")
        return bool(witnesses)

    runs = _items(data["runs"])
    if not runs:
        raise ValueError("report has no runs")
    for value in runs:
        run = _object(value)
        if run["status"] == "empty_harvest":
            summary["empty_harvests"] += 1
            continue
        if run["status"] != "encoded_and_verified":
            raise ValueError("unknown run status")
        instance = instance_from_json(run["instance"])
        verify_harvest_metadata(instance, run["harvest"])
        summary["instances"] += 1
        summary["prime_certificates"] += len(instance.records) + len(instance.excluded_nonunits)
        distinct_primes.update(record.p for record in instance.records + instance.excluded_nonunits)
        structure = _object(run["structure"])
        verify_metrics(instance, structure)
        check_obstructions(structure["necessary_target_checks"], instance,
                           instance.vectors, instance.target)
        for value in _items(run["benchmarks"]):
            case = _object(value)
            size = _integer(case["size"])
            if not 0 < size <= len(instance.records):
                raise ValueError("invalid benchmark pool scope")
            if case.get("status") == "cardinality_infeasible":
                if size >= 3:
                    raise ValueError("invalid cardinality claim")
                continue
            target = tuple(_integer(v) for v in _items(case["target"]))
            raw_residues = _items(case["residues_hex"])
            if len(raw_residues) != 2:
                raise ValueError("invalid residue target")
            residues = (_integer(raw_residues[0]), _integer(raw_residues[1]))
            planted = case["target_kind"] == "planted_control"
            if planted:
                witness = [_integer(i) for i in _items(case["planted_witness_indices"])]
                if any(i >= size for i in witness):
                    raise ValueError("control witness outside benchmark pool")
                verify_group_solution(instance, witness, target, residues)
            elif case["target_kind"] != "real_lp" or target != instance.target or residues != (
                    1, instance.lambda_plus - 1):
                raise ValueError("real target metadata is inconsistent")
            if case["target_matches_lp"] is not (target == instance.target):
                raise ValueError("incorrect real/control target classification")
            if planted and target == instance.target:
                n = verify_counterexample(instance.records, witness)
                if case.get("planted_witness_counterexample_hex") != hex(n):
                    raise ValueError("real-target control witness was not directly verified")
                counterexamples.add(n)
            elif case.get("planted_witness_counterexample_hex") is not None:
                raise ValueError("spurious planted counterexample claim")
            selected = case.get("selected_subset_lp_check")
            if planted:
                if selected is not None:
                    raise ValueError("planted control cannot substitute for a real L-P search")
            else:
                selected = _object(selected)
                if selected["status"] == "solution":
                    indices = [_integer(i) for i in _items(selected["indices"])]
                    if any(i >= size for i in indices):
                        raise ValueError("selected-subset witness outside benchmark pool")
                    n = verify_counterexample(instance.records, indices)
                    if selected.get("independently_verified_counterexample_hex") != hex(n):
                        raise ValueError("incorrect selected-subset counterexample value")
                    counterexamples.add(n)
                elif selected["status"] == "proved_no_solution":
                    if size > 18:
                        raise ValueError("unbounded selected-subset negative claim")
                    for k in range(3, size + 1, 2):
                        for indices in combinations(range(size), k):
                            n = math.prod(instance.records[i].p for i in indices)
                            if all((n - 1) % (instance.records[i].p - 1) == 0
                                   and (n + 1) % (instance.records[i].p + 1) == 0
                                   for i in indices):
                                raise ValueError("selected-subset negative claim is false")
                elif selected["status"] not in ("resource_limit", "inconclusive_budget"):
                    raise ValueError("unknown selected-subset search status")
            obstruction = check_obstructions(case["necessary_checks"], instance,
                                              instance.vectors[:size], target)
            no_solution: Optional[bool] = None
            for value in _object(case["solvers"]).values():
                result = _object(value)
                status = result["status"]
                if status == "solution":
                    indices = [_integer(i) for i in _items(result["indices"])]
                    if any(i >= size for i in indices):
                        raise ValueError("solver witness outside benchmark pool")
                    verify_group_solution(instance, indices, target, residues)
                    summary["solutions"] += 1
                    if target == instance.target:
                        n = verify_counterexample(instance.records, indices)
                        if result.get("independently_verified_counterexample_hex") != hex(n):
                            raise ValueError("counterexample claim is missing verification data")
                        counterexamples.add(n)
                    elif "independently_verified_counterexample_hex" in result:
                        raise ValueError("a planted target was mislabeled as a counterexample")
                elif status == "proved_no_solution":
                    if planted:
                        raise ValueError("negative claim contradicts planted witness")
                    if size >= 3 and not obstruction:
                        if size > 18:
                            raise ValueError("large negative claim needs a character certificate")
                        if no_solution is None:
                            no_solution = not any(
                                subset_residues(instance.records, indices, instance.lambda_minus,
                                                instance.lambda_plus) == residues
                                for k in range(3, size + 1, 2)
                                for indices in combinations(range(size), k))
                        if not no_solution:
                            raise ValueError("negative claim contradicted by independent enumeration")
                    summary["no_solution_claims"] += 1
                elif status not in ("resource_limit", "inconclusive_budget"):
                    raise ValueError("unknown solver status")
    summary["counterexamples"] = len(counterexamples)
    summary["distinct_primes"] = len(distinct_primes)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    args = parser.parse_args()
    payload = args.report.read_bytes()
    if args.report.suffix == ".gz":
        payload = gzip.decompress(payload)
    summary = verify_saved_report(json.loads(payload.decode("utf-8")))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
