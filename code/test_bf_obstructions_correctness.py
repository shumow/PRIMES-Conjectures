"""Correctness tests for S2 bf_obstructions (bounded; tiny oracles plus the saved report).

Run: python -B -m unittest discover -s code -p "*correctness.py" -v
"""
from itertools import combinations
from pathlib import Path
from unittest.mock import patch
import gzip
import json
import math
import random
import unittest

import bf_obstructions as bf
from real_pool_verify import PrimeRecord, instance_from_json

HERE = Path(__file__).resolve().parent
PILOT = HERE.parent / "data" / "generated" / "real_pool_pilot.json.gz"
REPORT = HERE.parent / "data" / "generated" / "bf_obstructions.json.gz"


def _pilot_run(name: str):
    data = json.loads(gzip.decompress(PILOT.read_bytes()))
    return next(run for run in data["runs"] if run["name"] == name)


def _small_primes(limit: int):
    return [q for q in range(3, limit) if all(q % d for d in range(2, int(q**0.5) + 1))]


class ArithmeticShadow(unittest.TestCase):
    def test_quadratic_nonresidue_matches_brute_force(self):
        for ell in _small_primes(60):
            squares = {x * x % ell for x in range(1, ell)}
            for p in range(1, 3 * ell):
                if p % ell:
                    self.assertEqual(bf.quadratic_nonresidue(p, ell), 0 if p % ell in squares else 1)
        with self.assertRaises(ValueError):
            bf.quadratic_nonresidue(7, 8)
        with self.assertRaises(ValueError):
            bf.quadratic_nonresidue(14, 7)

    def test_target_bits(self):
        self.assertEqual(bf.shadow_target_bit("minus", 7), 0)
        self.assertEqual(bf.shadow_target_bit("plus", 7), 1)
        self.assertEqual(bf.shadow_target_bit("plus", 13), 0)
        self.assertEqual(bf.shadow_target_bit("parity", 2), 1)
        with self.assertRaises(ValueError):
            bf.shadow_target_bit("other", 3)

    def test_shadow_and_forced_relation_on_pilot_instance(self):
        instance = instance_from_json(_pilot_run("small-complete-family")["instance"])
        shadow = bf.legendre_shadow_check(instance)
        self.assertEqual(shadow["status"], "verified")
        self.assertEqual(shadow["two_primary_coordinates"], len(bf.two_primary_coordinates(instance)))
        self.assertEqual(shadow["vector_entries_checked"],
                         shadow["two_primary_coordinates"] * len(instance.records))
        forced = bf.forced_three_relation(instance)
        self.assertEqual(forced["status"], "verified")
        self.assertEqual(instance.orders[forced["plus_three_coordinate"]], 2)
        # The declared shadow system coincides with the instance's own 2-primary blocks.
        labels, rows, bits = bf.shadow_system(instance.records)
        own = {(side, ell) for _, side, ell in bf.two_primary_coordinates(instance)} | {bf.PARITY}
        self.assertEqual(set(labels), own)
        for (side, ell), row, bit in zip(labels, rows, bits):
            if (side, ell) == bf.PARITY:
                continue
            j = next(j for j, s, q in bf.two_primary_coordinates(instance) if (s, q) == (side, ell))
            self.assertEqual(row, sum((v[j] % 2) << i for i, v in enumerate(instance.vectors)))
            self.assertEqual(bit, instance.target[j] % 2)

    def test_shadow_check_rejects_a_flipped_coordinate(self):
        instance = instance_from_json(_pilot_run("small-complete-family")["instance"])
        j = bf.two_primary_coordinates(instance)[0][0]
        vectors = [list(v) for v in instance.vectors]
        vectors[0][j] = (vectors[0][j] + 1) % instance.orders[j]
        broken = instance.__class__(instance.records, instance.excluded_nonunits, instance.lambda_minus,
                                    instance.lambda_plus, instance.blocks, instance.orders,
                                    tuple(tuple(v) for v in vectors), instance.target)
        with self.assertRaises(ValueError):
            bf.legendre_shadow_check(broken)

    def test_forced_relation_rejects_a_prime_that_is_one_mod_three(self):
        instance = instance_from_json(_pilot_run("small-complete-family")["instance"])
        bad = PrimeRecord(7, ((2, 1), (3, 1)), ((2, 3),), 3)
        broken = instance.__class__((bad,) + instance.records, instance.excluded_nonunits,
                                    instance.lambda_minus, instance.lambda_plus, instance.blocks,
                                    instance.orders, instance.vectors, instance.target)
        with self.assertRaises(ValueError):
            bf.forced_three_relation(broken)


class Gf2Machinery(unittest.TestCase):
    def _brute(self, rows, bits, variables):
        return [x for x in range(1 << variables)
                if all(bin(row & x).count("1") % 2 == bit for row, bit in zip(rows, bits))]

    def test_kernel_and_solution_against_brute_force(self):
        rng = random.Random(11)
        for _ in range(400):
            variables = rng.randint(1, 7)
            count = rng.randint(1, 8)
            rows = [rng.randrange(1 << variables) for _ in range(count)]
            bits = [rng.randrange(2) for _ in range(count)]
            kernel, rank = bf.gf2_left_kernel(rows)
            self.assertEqual(rank + len(kernel), count)
            for combo in kernel:
                acc = 0
                for k in range(count):
                    if combo >> k & 1:
                        acc ^= rows[k]
                self.assertEqual(acc, 0)
            solutions = self._brute(rows, bits, variables)
            found = bf.gf2_particular_solution(rows, bits, variables)
            self.assertEqual(found is not None, bool(solutions))
            if found is not None:
                self.assertIn(found, solutions)
            labels = [("minus", q) for q in _small_primes(200)[:count - 1]] + [bf.PARITY]
            analysis = bf.shadow_analysis(labels, rows, bits, variables)
            self.assertEqual(analysis["status"], "consistent" if solutions else "obstructed")
            self.assertEqual(bf.check_shadow_certificate(labels, rows, bits, variables,
                                                         analysis["certificate"]), analysis["status"])

    def test_certificate_checker_rejects_bad_certificates(self):
        labels = [("minus", 7), ("minus", 11), bf.PARITY]
        rows, bits = [0b01, 0b01, 0b11], [0, 1, 1]
        with self.assertRaises(ValueError):
            bf.check_shadow_certificate(labels, rows, bits, 2, {"kind": "gf2_solution_indices", "indices": [0]})
        self.assertEqual(bf.check_shadow_certificate(
            labels, rows, bits, 2, {"kind": "legendre_character", "labels": [["minus", 7], ["minus", 11]]}),
            "obstructed")
        with self.assertRaises(ValueError):
            bf.check_shadow_certificate(labels, rows, bits, 2,
                                        {"kind": "legendre_character", "labels": [["minus", 7], ["parity", 2]]})


class MinimumWeight(unittest.TestCase):
    def test_against_exhaustive_search(self):
        rng = random.Random(5)
        for _ in range(300):
            variables = rng.randint(1, 5)
            count = rng.randint(1, 7)
            rows = [rng.randrange(1 << variables) for _ in range(count)]
            bits = [rng.randrange(2) for _ in range(count)]
            expected = None
            for weight in range(1, 5):
                for combo in combinations(range(count), weight):
                    acc = 0
                    for k in combo:
                        acc ^= rows[k]
                    if acc == 0 and sum(bits[k] for k in combo) % 2:
                        expected = weight
                        break
                if expected:
                    break
            result = bf.minimum_weight_separating(rows, bits, 4)
            self.assertEqual(result["weight"], expected)
            if expected:
                acc = 0
                for k in result["indices"]:
                    acc ^= rows[k]
                self.assertEqual(acc, 0)
                self.assertEqual(sum(bits[k] for k in result["indices"]) % 2, 1)
            else:
                self.assertEqual(result["status"], "completed_scope")


class IndexCertificates(unittest.TestCase):
    def _random_case(self, rng):
        ell = rng.choice([2, 2, 2, 3, 5])
        while True:
            orders = [ell**rng.randint(1, 3) for _ in range(rng.randint(1, 4))]
            if math.prod(orders) <= 2048:      # keep the breadth-first oracle small
                break
        vectors = [[rng.randrange(o) for o in orders] for _ in range(rng.randint(0, 4))]
        target = [rng.randrange(o) for o in orders]
        return ell, orders, vectors, target

    def test_exact_index_and_membership_against_brute_force(self):
        rng = random.Random(7)
        checked = 0
        for _ in range(300):
            ell, orders, vectors, target = self._random_case(rng)
            subgroup = bf.brute_force_subgroup(orders, vectors)
            certificate = bf.primary_index_certificate(orders, vectors, ell)
            result = bf.verify_primary_index_certificate(orders, vectors, target, certificate)
            self.assertEqual(result["index"], math.prod(orders) // len(subgroup))
            self.assertEqual(result["subgroup_order"], len(subgroup))
            self.assertEqual(result["target_member"], tuple(target) in subgroup)
            checked += 1
        self.assertEqual(checked, 300)

    def test_mixed_group_only_uses_the_requested_primary_part(self):
        orders = [4, 3, 2, 9]
        vectors = [[1, 1, 1, 3], [2, 0, 0, 0]]
        certificate = bf.primary_index_certificate(orders, vectors, 2)
        self.assertEqual(certificate["coordinates"], [0, 2])
        result = bf.verify_primary_index_certificate(orders, vectors, [0, 0, 0, 0], certificate)
        self.assertEqual(result["index"], 2)       # <(1,1),(2,0)> in Z/4 x Z/2 has order 4
        odd = bf.primary_index_certificate(orders, vectors, 3)
        # <(1,3)> in Z/3 x Z/9 has order 3, so the 3-primary index is 27 / 3.
        self.assertEqual(bf.verify_primary_index_certificate(orders, vectors, [0, 0, 0, 0], odd)["index"], 9)

    def test_verifier_rejects_falsified_certificates(self):
        orders, vectors, target = [4, 4], [[1, 1]], [0, 2]
        certificate = bf.primary_index_certificate(orders, vectors, 2)
        good = bf.verify_primary_index_certificate(orders, vectors, target, certificate)
        self.assertEqual(good["index"], 4)
        self.assertFalse(good["target_member"])
        falsified = json.loads(json.dumps(certificate))
        falsified["witnesses"][0]["coefficients"][0] = (falsified["witnesses"][0]["coefficients"][0] + 1) % 4
        with self.assertRaises(ValueError):
            bf.verify_primary_index_certificate(orders, vectors, target, falsified)
        dropped = json.loads(json.dumps(certificate))
        dropped["characters"] = dropped["characters"][1:]
        with self.assertRaises(ValueError):
            bf.verify_primary_index_certificate(orders, vectors, target, dropped)
        bad_char = json.loads(json.dumps(certificate))
        bad_char["characters"][0]["coefficients"] = [1, 0]
        with self.assertRaises(ValueError):
            bf.verify_primary_index_certificate(orders, vectors, target, bad_char)
        wrong_prime = json.loads(json.dumps(certificate))
        wrong_prime["prime"] = 3
        with self.assertRaises(ValueError):
            bf.verify_primary_index_certificate(orders, vectors, target, wrong_prime)

    def test_verifier_needs_triangular_pivots(self):
        orders, vectors = [2, 2], [[1, 0], [0, 1]]
        certificate = bf.primary_index_certificate(orders, vectors, 2)
        self.assertEqual(bf.verify_primary_index_certificate(orders, vectors, [1, 1], certificate)["index"], 1)
        swapped = json.loads(json.dumps(certificate))
        swapped["witnesses"].reverse()
        with self.assertRaises(ValueError):
            bf.verify_primary_index_certificate(orders, vectors, [1, 1], swapped)


class FamiliesAndCharacters(unittest.TestCase):
    def test_family_membership_on_pilot_records(self):
        run = _pilot_run("small-complete-family")
        instance = instance_from_json(run["instance"])
        config = run["harvest"]["config"]
        self.assertTrue(all(bf.in_declared_family(r, config) for r in instance.records))
        tighter = dict(config, minus_bound=config["plus_bound"] + 2)
        self.assertFalse(any(bf.in_declared_family(r, tighter) for r in instance.records))
        wider_j = dict(config, factors=config["factors"] + 1)
        self.assertFalse(any(bf.in_declared_family(r, wider_j) for r in instance.records))

    def test_character_labels_and_description(self):
        instance = instance_from_json(_pilot_run("small-complete-family")["instance"])
        j3 = bf.forced_three_relation(instance)["plus_three_coordinate"]
        parity = len(instance.orders) - 1
        labels = bf.character_labels(instance, 2, [[j3, 1]])
        self.assertEqual(labels, [("plus", 3)])
        self.assertEqual([bf.evaluate_character(labels, r.p) for r in instance.records],
                         [1] * len(instance.records))
        description = bf.describe_character(labels + [("minus", 7), ("plus", 13)])
        self.assertEqual(description["sign_carrying_plus_primes"], [3])
        self.assertEqual(description["target_value"], 1)
        canonical = description["canonical_modulo_forced_relation"]
        self.assertEqual(canonical["labels"], [["minus", 7], ["parity", 2], ["plus", 13]])
        self.assertFalse(canonical["minus_only_plus_parity"])
        only_minus = bf.describe_character([("plus", 3), ("minus", 7)])["canonical_modulo_forced_relation"]
        self.assertTrue(only_minus["minus_only_plus_parity"])
        with self.assertRaises(ValueError):
            bf.character_labels(instance, 4, [[j3, 1]])
        with self.assertRaises(ValueError):
            bf.character_labels(instance, 2, [[parity, 1], [parity, 1]])
        odd_coordinate = next(j for j, o in enumerate(instance.orders) if o % 2)
        with self.assertRaises(ValueError):
            bf.character_labels(instance, 2, [[odd_coordinate, 1]])


class DeclaredBudgets(unittest.TestCase):
    def test_budgets_are_bounded_and_declared(self):
        self.assertLessEqual(bf.BUDGETS["wall_seconds_per_probe"], 60.0)
        self.assertLessEqual(bf.BUDGETS["min_weight_cap"], 4)
        self.assertEqual(bf.BUDGETS["worker_processes"], 1)
        self.assertFalse(bf.BUDGETS["new_harvesting"])
        self.assertEqual(len(bf.PROBES), 8)
        self.assertEqual(bf.CELLS[0], bf.ANCHOR)
        for name in bf.TRANSFERS:
            self.assertIn(name, bf.CELLS)
        for _, cell, sources in bf.UNIONS:
            self.assertIn(cell, bf.CELLS)
            for source in sources:
                self.assertIn(source, bf.CELLS)


class SavedReport(unittest.TestCase):
    def test_saved_report_verifies_without_running_the_algorithms(self):
        self.assertTrue(REPORT.exists(), "S2 report missing")
        report = json.loads(gzip.decompress(REPORT.read_bytes()))
        with patch.object(bf, "howell_form", side_effect=AssertionError("must not run")), \
                patch.object(bf, "snf_kernel", side_effect=AssertionError("must not run")), \
                patch.object(bf, "gf2_left_kernel", side_effect=AssertionError("must not run")), \
                patch.object(bf, "primary_index_certificate", side_effect=AssertionError("must not run")), \
                patch.object(bf, "analyze", side_effect=AssertionError("must not run")):
            summary = bf.verify_report(report)
        self.assertEqual(summary["cells"], 5)
        self.assertEqual(summary["characters_rechecked"], 4)
        self.assertGreaterEqual(summary["index_certificates"], 1)
        full = report["anchor_full_index"]
        self.assertEqual(full["status"], "verified")
        self.assertEqual(full["total_index"], 2)
        self.assertTrue(full["real_target_member"])
        anchor = report["cells"][0]
        self.assertTrue(anchor["shadow"]["value"]["kernel_is_exactly_forced_relation"])
        self.assertIsNone(anchor["recorded_character"])
        for entry in report["cells"][1:]:
            self.assertEqual(entry["shadow"]["value"]["status"], "obstructed")
            self.assertTrue(entry["shadow"]["value"]["forced_relation_in_kernel"])

    def test_verifier_rejects_a_tampered_annotation(self):
        self.assertTrue(REPORT.exists(), "S2 report missing")
        report = json.loads(gzip.decompress(REPORT.read_bytes()))
        report["anchor_full_index"]["total_index"] = 4
        with self.assertRaises(ValueError):
            bf.verify_report(report)
        report = json.loads(gzip.decompress(REPORT.read_bytes()))
        report["cells"][1]["recorded_character"]["description"]["weight"] += 1
        with self.assertRaises(ValueError):
            bf.verify_report(report)


if __name__ == "__main__":
    unittest.main()
