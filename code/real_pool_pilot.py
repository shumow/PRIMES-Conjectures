"""Bounded, reproducible construction and validation of actual L-P pools.

Run: python -B code\\real_pool_pilot.py
Outputs a new dataset only; --replace explicitly permits replacing that output.
"""
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from itertools import combinations, islice
from pathlib import Path
import argparse
import gzip
import json
import math
import platform
import random
import time
from typing import Optional, Sequence, TypedDict

import a4_solver
import a6_oddsolver
from a7_lohniebuhr import gfl_rref
from phase1a_calibration import is_prime, primes_upto
from real_pool_verify import (
    PrimeRecord, RealInstance, UnitBlock, source_digest, subset_residues, verify_counterexample,
    verify_encoding, verify_group_solution, verify_obstruction, verify_prime,
)


@dataclass(frozen=True)
class HarvestConfig:
    name: str
    plus_bound: int
    minus_bound: int
    factors: int
    candidate_cap: int
    pool_cap: int
    sampled: bool
    seed: int
    prime_power_cap: int = 8192


CONFIGS = (
    HarvestConfig("small-complete-family", 113, 565, 3, 100000, 128, False, 20261022),
    HarvestConfig("medium-bounded-sample", 547, 2735, 3, 1000000, 128, True, 20261022),
    HarvestConfig("medium-complete-family", 547, 2735, 3, 5000000, 512, False, 20261022),
)


class SearchResult(TypedDict, total=False):
    status: str
    reason: str
    states: int
    indices: list[int]
    independently_verified_counterexample_hex: str


def lucas_witness(p: int, factors: dict[int, int]) -> Optional[int]:
    for a in range(2, min(p, 66)):
        if pow(a, p - 1, p) == 1 and all(
                math.gcd(pow(a, (p - 1) // q, p) - 1, p) == 1 for q in factors):
            return a
    return None


def harvest(config: HarvestConfig) -> tuple[tuple[PrimeRecord, ...], dict[str, object]]:
    if (config.plus_bound < 3 or config.minus_bound <= config.plus_bound
            or config.factors < 1 or min(config.candidate_cap, config.pool_cap) < 1
            or config.prime_power_cap < 2):
        raise ValueError("invalid harvest configuration")
    primes = primes_upto(config.minus_bound)
    minus = [q for q in primes if q > config.plus_bound]
    plus = [q for q in primes if 2 < q <= config.plus_bound and q != 5]
    if len(minus) < config.factors:
        raise ValueError("minus base is too small")
    family = math.comb(len(minus), config.factors)
    rng = random.Random(config.seed)
    if config.sampled:
        candidates = (tuple(sorted(rng.sample(minus, config.factors)))
                      for _ in range(config.candidate_cap))
    else:
        candidates = islice(combinations(minus, config.factors), config.candidate_cap)
    counts = dict(draws=0, mod40=0, smooth=0, power_cap_rejected=0,
                  probable_primes=0, certificate_exhausted=0, duplicates=0,
                  outside_uint64=0, accepted=0)
    records: dict[int, PrimeRecord] = {}
    stop = "candidate_cap" if config.sampled or family > config.candidate_cap else "family_exhausted"
    start = time.monotonic()
    for factors in candidates:
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
        plus_factors: dict[int, int] = {2: 2}
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
                             tuple(sorted(plus_factors.items())), witness, counts["draws"])
        verify_prime(record)
        records[p] = record
        counts["accepted"] += 1
        if len(records) >= config.pool_cap:
            stop = "pool_cap"
            break
    return tuple(sorted(records.values(), key=lambda record: record.p)), {
        "config": asdict(config), "q_minus": minus, "q_plus": plus,
        "candidate_family_size": family, "counts": counts, "stop_reason": stop,
        "complete_family_scan": not config.sampled and counts["draws"] == family,
        "sampling": "with replacement" if config.sampled else "lexicographic enumeration",
        "primality": "probable-prime prefilter, then independently checked full-factor Lucas certificate",
        "witness_bases": [2, 65], "seconds": time.monotonic() - start,
    }


class DiscreteLog:
    def __init__(self, q: int, exponent: int, max_baby_steps: int = 65536):
        if q < 3 or not is_prime(q) or exponent < 1:
            raise ValueError("discrete-log block requires an odd prime power")
        self.modulus = q**exponent
        self.order = (q - 1) * q**(exponent - 1)
        self.factors = a4_solver.prime_power_factors(q - 1)
        if exponent > 1:
            self.factors[q] = exponent - 1
        self.step = math.isqrt(self.order - 1) + 1
        if self.step > max_baby_steps:
            raise ValueError("discrete-log baby-step budget exceeded")
        g = 2
        while any(pow(g, (q - 1) // ell, q) == 1
                  for ell in a4_solver.prime_power_factors(q - 1)):
            g += 1
        if exponent > 1 and pow(g, q - 1, q * q) == 1:
            g += q
        if pow(g, self.order, self.modulus) != 1 or any(
                pow(g, self.order // ell, self.modulus) == 1 for ell in self.factors):
            raise ArithmeticError("primitive-root construction failed")
        self.generator = g
        self.baby: dict[int, int] = {}
        value = 1
        for j in range(self.step):
            self.baby[value] = j
            value = value * g % self.modulus
        self.giant_inverse = pow(pow(g, self.step, self.modulus), -1, self.modulus)

    def log(self, value: int) -> int:
        if math.gcd(value, self.modulus) != 1:
            raise ValueError("cannot take the logarithm of a nonunit")
        residue = value % self.modulus
        current = residue
        for i in range(self.step + 1):
            j = self.baby.get(current)
            if j is not None:
                exponent = (i * self.step + j) % self.order
                if pow(self.generator, exponent, self.modulus) != residue:
                    raise ArithmeticError("discrete-log reconstruction failed")
                return exponent
            current = current * self.giant_inverse % self.modulus
        raise ArithmeticError("unit logarithm not found")


def build_instance(records: Sequence[PrimeRecord]) -> RealInstance:
    if not records:
        raise ValueError("cannot build an instance from an empty harvest")
    maxima: dict[str, dict[int, int]] = {"minus": {}, "plus": {}}
    for record in records:
        verify_prime(record)
        for side, factors in (("minus", record.minus), ("plus", record.plus)):
            for q, exponent in factors:
                maxima[side][q] = max(maxima[side].get(q, 0), exponent)
    lm, lp = (math.prod(q**e for q, e in maxima[side].items())
              for side in ("minus", "plus"))
    if math.gcd(lm, lp) != 2:
        raise ValueError("harvest does not have disjoint odd side supports")
    retained = tuple(record for record in records if math.gcd(record.p, lm * lp) == 1)
    excluded = tuple(record for record in records if math.gcd(record.p, lm * lp) != 1)
    rows: list[list[int]] = [[] for _ in retained]
    orders: list[int] = []
    target: list[int] = []
    blocks: list[UnitBlock] = []
    for side in ("minus", "plus"):
        for q, exponent in sorted(maxima[side].items()):
            if q == 2:
                continue
            table = DiscreteLog(q, exponent)
            primary_orders = [ell**a for ell, a in sorted(table.factors.items())]
            columns = tuple(range(len(orders), len(orders) + len(primary_orders)))
            orders.extend(primary_orders)
            target_log = 0 if side == "minus" else table.order // 2
            target.extend(target_log % order for order in primary_orders)
            for row, record in zip(rows, retained):
                logarithm = table.log(record.p)
                row.extend(logarithm % order for order in primary_orders)
            blocks.append(UnitBlock(side, q, exponent, table.generator, columns))
    # This C2 replaces the original modulo-4 unit factor; it is not an extra bit.
    orders.append(2)
    target.append(1)
    for row in rows:
        row.append(1)
    instance = RealInstance(retained, excluded, lm, lp, tuple(blocks), tuple(orders),
                            tuple(tuple(row) for row in rows), tuple(target))
    verify_encoding(instance)
    return instance


def necessary_checks(orders: Sequence[int], vectors: Sequence[Sequence[int]],
                     target: Sequence[int]) -> dict[str, object]:
    if len(target) != len(orders) or any(len(vector) != len(orders) for vector in vectors):
        raise ValueError("necessary-check dimensions do not match")
    fields: dict[int, list[int]] = {}
    coordinate_obstructions = []
    for j, order in enumerate(orders):
        factors = a4_solver.prime_power_factors(order)
        if order < 2 or len(factors) != 1:
            raise ValueError("necessary checks require prime-power component orders")
        ell = next(iter(factors))
        fields.setdefault(ell, []).append(j)
        divisor = math.gcd(order, *(vector[j] for vector in vectors))
        if target[j] % divisor:
            terms = [(j, 1)]
            verify_obstruction(orders, vectors, target, divisor, terms)
            coordinate_obstructions.append({"modulus": divisor, "terms": terms})
    results = []
    for ell, columns in sorted(fields.items()):
        matrix = [[vector[j] % ell for vector in vectors] for j in columns]
        rhs = [target[j] % ell for j in columns]
        if ell == 2:
            masks = [sum(value << i for i, value in enumerate(row)) for row in matrix]
            solution = a4_solver.gf2_solve(masks, rhs, len(vectors))
            consistent = solution is not None
            homogeneous = a4_solver.gf2_solve(masks, [0] * len(rhs), len(vectors))
            if homogeneous is None:
                raise ArithmeticError("homogeneous binary system inconsistent")
            rank = len(vectors) - len(homogeneous[1])
        else:
            solution = gfl_rref(matrix, rhs, ell)
            consistent = solution is not None
            homogeneous = gfl_rref(matrix, [0] * len(rhs), ell)
            if homogeneous is None:
                raise ArithmeticError("homogeneous prime-field system inconsistent")
            rank = len(homogeneous[0])
        entry: dict[str, object] = {
            "prime": ell, "rows": len(columns), "rank": rank, "consistent": consistent,
        }
        if not consistent:
            transpose = [[row[i] for row in matrix] for i in range(len(vectors))]
            witness = gfl_rref(transpose + [rhs], [0] * len(vectors) + [1], ell)
            if witness is None:
                raise ArithmeticError("could not certify the linear obstruction")
            coefficients = [0] * len(columns)
            for j, value in zip(witness[0], witness[2]):
                coefficients[j] = value
            terms = [(columns[j], value) for j, value in enumerate(coefficients) if value]
            verify_obstruction(orders, vectors, target, ell, terms)
            entry["obstruction"] = {"modulus": ell, "terms": terms}
        results.append(entry)
    return {
        "coordinate_obstructions": coordinate_obstructions, "prime_field_checks": results,
        "has_obstruction": bool(coordinate_obstructions) or any(
            entry["consistent"] is False for entry in results),
        "scope": "necessary coordinate and prime-field quotient checks; passing is not Boolean or full subgroup reachability",
    }


def measure_structure(instance: RealInstance, seed: int) -> dict[str, object]:
    n, d = len(instance.records), len(instance.orders)
    if not n:
        raise ValueError("cannot measure an empty unit pool")
    forced = [[False] * d for _ in range(n)]
    columns: list[dict[str, object]] = [{} for _ in range(d)]
    for block in instance.blocks:
        for j in block.columns:
            ell = next(iter(a4_solver.prime_power_factors(instance.orders[j])))
            columns[j] = {"side": block.side, "prime": block.prime,
                          "exponent": block.exponent, "primary_prime": ell}
            for i, record in enumerate(instance.records):
                valuation = dict(record.minus if block.side == "minus" else record.plus).get(block.prime, 0)
                forced[i][j] = (valuation > 0 and (block.side == "minus" or ell != 2)
                                and (ell != block.prime or valuation >= block.exponent))
    columns[-1] = {"side": "cardinality/mod4", "prime": 2, "exponent": 2, "primary_prime": 2}
    zeros = [sum(vector[j] == 0 for vector in instance.vectors) for j in range(d)]
    guaranteed = [sum(row[j] for row in forced) for j in range(d)]
    for i, row in enumerate(forced):
        if any(flag and instance.vectors[i][j] != 0 for j, flag in enumerate(row)):
            raise ArithmeticError("a claimed forced identity is nonzero")
    for j, order in enumerate(instance.orders):
        columns[j].update(order=order, zeros=zeros[j], literal_probability=zeros[j] / n,
                          forced_zeros=guaranteed[j], uniform_baseline=1 / order)
    pairs: set[tuple[int, int]] = set()
    rng = random.Random(seed)
    pair_count = min(64, d * (d - 1) // 2)
    while len(pairs) < pair_count:
        pairs.add(tuple(sorted(rng.sample(range(d), 2))))
    correlations = []
    for a, b in sorted(pairs):
        pa, pb = zeros[a] / n, zeros[b] / n
        joint = sum(v[a] == 0 and v[b] == 0 for v in instance.vectors) / n
        denominator = math.sqrt(pa * (1 - pa) * pb * (1 - pb))
        correlations.append({"columns": [a, b], "joint_zero_probability": joint,
                             "product_of_marginals": pa * pb,
                             "phi": (joint - pa * pb) / denominator if denominator else None})
    bits = sum(math.log2(order) for order in instance.orders)
    squarefree_bits = 1 + sum(math.log2(block.prime - 1) for block in instance.blocks)
    return {
        "pool_size": n, "components": d, "group_order_hex": hex(math.prod(instance.orders)),
        "group_bits": bits, "pool_per_group_bit": n / bits,
        "squarefree_q_minus_1_model_bits": squarefree_bits,
        "prime_power_bits_missing_from_that_model": bits - squarefree_bits,
        "mean_literal_identity_fraction": sum(zeros) / (n * d),
        "mean_forced_identity_fraction": sum(guaranteed) / (n * d),
        "bit_weighted_identity_fraction": sum(
            zeros[j] * math.log2(order) for j, order in enumerate(instance.orders)) / (n * bits),
        "distinct_vectors": len(set(instance.vectors)),
        "components_detail": columns, "sampled_zero_correlations": correlations,
        "correlation_sampling": {"seed": seed, "pairs": pair_count,
                                 "note": "descriptive only; constant-column phi is undefined/null"},
        "necessary_target_checks": necessary_checks(instance.orders, instance.vectors, instance.target),
    }


def residue_oracle(instance: RealInstance, size: int, residues: tuple[int, int],
                   state_cap: int = 1 << 18, column_cap: int = 18) -> SearchResult:
    if not 0 <= size <= len(instance.records) or min(state_cap, column_cap) < 1:
        raise ValueError("invalid oracle scope or budget")
    if size < 3:
        return {"status": "proved_no_solution", "reason": "cardinality", "states": 0}
    if size > column_cap:
        return {"status": "resource_limit", "reason": "column_cap", "states": 0}
    lm, lp = instance.lambda_minus, instance.lambda_plus
    primes = [record.p for record in instance.records[:size]]
    inverses = [(pow(p, -1, lm), pow(p, -1, lp)) for p in primes]
    left = right = 1
    previous = count = 0
    limit = min(1 << size, state_cap)
    for step in range(limit):
        gray = step ^ (step >> 1)
        if step:
            flipped = gray ^ previous
            j = flipped.bit_length() - 1
            if gray & flipped:
                left, right = left * primes[j] % lm, right * primes[j] % lp
                count += 1
            else:
                left, right = left * inverses[j][0] % lm, right * inverses[j][1] % lp
                count -= 1
        previous = gray
        if count >= 3 and count % 2 and (left, right) == residues:
            return {"status": "solution", "indices": [j for j in range(size) if gray >> j & 1],
                    "states": step + 1}
    return {"status": "proved_no_solution" if limit == 1 << size else "inconclusive_budget",
            "states": limit}


def selected_subset_oracle(instance: RealInstance, size: int, state_cap: int = 1 << 18,
                           column_cap: int = 18) -> SearchResult:
    """Check original divisibility conditions, not the stronger full-pool target."""
    if not 0 <= size <= len(instance.records) or min(state_cap, column_cap) < 1:
        raise ValueError("invalid selected-subset oracle scope or budget")
    if size < 3:
        return {"status": "proved_no_solution", "reason": "cardinality", "states": 0}
    if size > column_cap:
        return {"status": "resource_limit", "reason": "column_cap", "states": 0}
    states = 0
    for k in range(3, size + 1, 2):
        for indices in combinations(range(size), k):
            if states >= state_cap:
                return {"status": "inconclusive_budget", "states": states}
            states += 1
            n = math.prod(instance.records[i].p for i in indices)
            if all((n - 1) % (instance.records[i].p - 1) == 0
                   and (n + 1) % (instance.records[i].p + 1) == 0 for i in indices):
                verified = verify_counterexample(instance.records, indices)
                return {"status": "solution", "indices": list(indices), "states": states,
                        "independently_verified_counterexample_hex": hex(verified)}
    return {"status": "proved_no_solution", "states": states}


def benchmark(instance: RealInstance, size: int, planted: bool, seed: int) -> dict[str, object]:
    if not 0 < size <= len(instance.records):
        raise ValueError("invalid benchmark pool size")
    rows = instance.vectors[:size]
    if planted and size < 3:
        return {"target_kind": "planted_control", "size": size, "status": "cardinality_infeasible"}
    witness = sorted(random.Random(seed).sample(range(size), 3)) if planted else []
    target = (tuple(sum(rows[i][j] for i in witness) % order
                    for j, order in enumerate(instance.orders)) if planted else instance.target)
    residues = (subset_residues(instance.records, witness, instance.lambda_minus, instance.lambda_plus)
                if planted else (1, instance.lambda_plus - 1))
    planted_counterexample = None
    if planted:
        verify_group_solution(instance, witness, target, residues)
        if target == instance.target:
            planted_counterexample = hex(verify_counterexample(instance.records, witness))
    checks = necessary_checks(instance.orders, rows, target)
    outputs: dict[str, object] = {}
    oracle = residue_oracle(instance, size, residues)
    if oracle["status"] == "solution":
        verify_group_solution(instance, oracle["indices"], target, residues)
        if target == instance.target:
            n = verify_counterexample(instance.records, oracle["indices"])
            oracle["independently_verified_counterexample_hex"] = hex(n)
    outputs["independent_residue_oracle"] = oracle
    for name in ("a4_kernel", "a6_local", "a6_mitm"):
        start = time.monotonic()
        if name == "a4_kernel":
            bits, message = a4_solver.full_solve(
                rows, instance.orders, target, size, random.Random(seed), budget=64, min_size=3)
        elif name == "a6_local":
            comps = [(next(iter(a4_solver.prime_power_factors(order))), order)
                     for order in instance.orders]
            bits, message = a6_oddsolver.solve(
                comps, instance.orders, rows, target, size, random.Random(seed), 2.0,
                min_size=3, move_budget=64)
        elif size <= 18:
            bits, message = a6_oddsolver.mitm_frontier(
                instance.orders, rows, target, size, 5.0, min_size=3)
        else:
            bits, message = None, "pilot column cap"
        output: dict[str, object] = {"message": message, "seconds": time.monotonic() - start}
        if bits is not None:
            indices = [i for i in range(size) if bits >> i & 1]
            verify_group_solution(instance, indices, target, residues)
            output.update(status="solution", indices=indices)
            if target == instance.target:
                n = verify_counterexample(instance.records, indices)
                output["independently_verified_counterexample_hex"] = hex(n)
            if oracle["status"] == "proved_no_solution":
                raise ArithmeticError("solver disagrees with complete independent oracle")
        elif message in ("exhausted", "cardinality infeasible"):
            output["status"] = "proved_no_solution"
        elif message == "mod2 inconsistent":
            if not checks["has_obstruction"]:
                raise ArithmeticError("binary inconsistency has no independent character witness")
            output["status"] = "proved_no_solution"
        else:
            output["status"] = "resource_limit" if "cap" in message else "inconclusive_budget"
        outputs[name] = output
    return {
        "size": size, "pool_scope": "first sorted retained primes, full parent LCMs unchanged",
        "target_kind": "planted_control" if planted else "real_lp",
        "target": list(target), "residues_hex": [hex(value) for value in residues],
        "planted_witness_indices": witness, "target_matches_lp": target == instance.target,
        "planted_witness_counterexample_hex": planted_counterexample,
        "necessary_checks": checks, "solvers": outputs,
        "selected_subset_lp_check": None if planted else selected_subset_oracle(instance, size),
        "budgets": {"minimum_size": 3, "odd": True, "kernel_states": 64,
                    "local_moves": 64, "local_seconds": 2, "mitm_seconds": 5,
                    "exact_column_cap": 18, "oracle_states": 1 << 18, "seed": seed},
    }


def serialize_instance(instance: RealInstance) -> dict[str, object]:
    def record_json(record: PrimeRecord) -> dict[str, object]:
        return {"p": str(record.p), "p_minus_1": dict((str(q), e) for q, e in record.minus),
                "p_plus_1": dict((str(q), e) for q, e in record.plus),
                "lucas_witness": record.witness, "candidate_index": record.candidate_index}

    return {
        "records": [record_json(record) for record in instance.records],
        "excluded_nonunits": [record_json(record) for record in instance.excluded_nonunits],
        "lambda_minus_hex": hex(instance.lambda_minus), "lambda_plus_hex": hex(instance.lambda_plus),
        "blocks": [{**asdict(block), "modulus": block.modulus, "order": block.order}
                   for block in instance.blocks],
        "orders": list(instance.orders), "vectors": [list(vector) for vector in instance.vectors],
        "real_target": list(instance.target), "parity_column": len(instance.orders) - 1,
        "automatic_2adic": {"minus_exponent": 1, "plus_exponent": 2,
                           "p_mod4": 3, "target_parity": 1, "minimum_size": 3,
                           "parity_replaces_mod4": True},
        "scope": "full raw-pool LCMs retained after nonunit filtering; modulo-4 factor replaced by parity",
    }


def run_pilot() -> dict[str, object]:
    runs = []
    for config in CONFIGS:
        records, harvest_info = harvest(config)
        if not records:
            runs.append({"name": config.name, "harvest": harvest_info, "status": "empty_harvest"})
            print(f"{config.name}: empty harvest under the stated caps", flush=True)
            continue
        start = time.monotonic()
        instance = build_instance(records)
        build_seconds = time.monotonic() - start
        structure = measure_structure(instance, config.seed)
        sizes = sorted({min(12, len(instance.records)), len(instance.records)})
        cases = [benchmark(instance, size, planted, config.seed + size)
                 for size in sizes for planted in (False, True)]
        runs.append({"name": config.name, "harvest": harvest_info, "status": "encoded_and_verified",
                     "instance_build_seconds": build_seconds, "instance": serialize_instance(instance),
                     "structure": structure, "benchmarks": cases})
        print(f"{config.name}: {len(records)} certified primes, {len(instance.records)} units, "
              f"{len(instance.orders)} components, {structure['group_bits']} group bits",
              flush=True)
    here = Path(__file__).resolve().parent
    sources = ("real_pool_pilot.py", "real_pool_verify.py", "a4_solver.py", "a6_oddsolver.py",
               "a7_lohniebuhr.py", "phase1a_calibration.py")
    return {
        "schema": "real-pool-pilot/v1", "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "source_hash_normalization": "CRLF-to-LF",
        "python": platform.python_version(), "source_sha256": {
            name: source_digest(here / name) for name in sources},
        "runs": runs,
        "limits": [
            "No claim about all counterexample mechanisms or all possible harvests.",
            "Full-parent LCM targets are stronger than per-selected-subset divisibility.",
            "Passing necessary quotient checks is not sufficient for a Boolean subset.",
            "Planted controls are not actual counterexamples unless independently verified as such.",
            "Sampling, pool and solver caps limit all negative conclusions.",
            "Timings and time-limited search outcomes can vary; seeded harvesting is reproducible.",
        ],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path(__file__).resolve().parent.parent
                        / "data" / "generated" / "real_pool_pilot.json.gz")
    parser.add_argument("--replace", action="store_true", help="explicitly replace this output file")
    args = parser.parse_args()
    if args.output.exists() and not args.replace:
        parser.error("output already exists; use --replace or choose another path")
    report = run_pilot()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    args.output.write_bytes(gzip.compress(payload, mtime=0)
                            if args.output.suffix == ".gz" else payload)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
