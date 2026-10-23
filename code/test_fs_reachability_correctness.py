"""Exact subgroup oracles and adversarial certificate tests for Track B."""
from collections import deque
from contextlib import redirect_stderr, redirect_stdout
from dataclasses import replace
from io import StringIO
from itertools import product
from pathlib import Path
import gzip
import json
import math
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

import fs_reachability as fs
from real_pool_pilot import necessary_checks


def subgroup(orders, vectors):
    zero = tuple(0 for _ in orders)
    reached = {zero}
    queue = deque([zero])
    while queue:
        current = queue.popleft()
        for vector in vectors:
            following = tuple((a + b) % m for a, b, m in zip(current, vector, orders))
            if following not in reached:
                reached.add(following)
                queue.append(following)
    return reached


class ExactMembershipTests(unittest.TestCase):
    def assert_decision(self, orders, vectors, target, expected):
        result = fs.membership(orders, vectors, target)
        self.assertEqual(result.status, "member" if expected else "nonmember",
                         (orders, vectors, target, result))
        fs.verify_certificate(orders, vectors, target, result)
        if result.status == "nonmember":
            self.assertEqual(math.gcd(result.character_modulus,
                                      *(c for _, c in result.character_terms)), 1)
        return result

    def test_missed_prime_power_joint_obstruction(self):
        orders, vectors, target = (4, 4), ((1, 1),), (0, 2)
        self.assertFalse(necessary_checks(orders, vectors, target)["has_obstruction"])
        result = self.assert_decision(orders, vectors, target, False)
        self.assertEqual(result.character_modulus, 4)

    def test_heterogeneous_powers_require_equation_scaling(self):
        orders, vectors = (2, 4), ((1, 1),)
        self.assertEqual(self.assert_decision(orders, vectors, (0, 2), True).coefficients, (2,))
        self.assert_decision(orders, vectors, (1, 0), False)

    def test_divisible_nonunit_pivots(self):
        self.assertEqual(self.assert_decision((8,), ((2,),), (6,), True).coefficients, (3,))
        self.assert_decision((8,), ((4,),), (2,), False)

    def test_shared_integer_coefficients_recombined_across_primes(self):
        result = self.assert_decision((4, 9), ((1, 1),), (2, 5), True)
        self.assertEqual(result.coefficients, (14,))

    def test_later_primary_obstruction_maps_to_original_coordinates(self):
        result = self.assert_decision((4, 9), ((2, 3),), (2, 1), False)
        self.assertEqual(result.character_modulus, 3)
        self.assertEqual(result.character_terms, ((1, 1),))
        self.assertEqual(len(result.completed_primary_systems), 1)

    def test_nonbinary_prime_power_with_mixed_exponents(self):
        self.assert_decision((25, 5), ((5, 1),), (15, 3), True)
        self.assert_decision((25, 5), ((5, 1),), (0, 1), False)

    def test_row_and_variable_permutations(self):
        orders = (8, 9, 4)
        vectors = ((0, 1, 0), (2, 0, 2), (1, 2, 1))
        coefficients = (-3, 8, 5)
        target = tuple(sum(c * v[j] for c, v in zip(coefficients, vectors)) % order
                       for j, order in enumerate(orders))
        self.assert_decision(orders, vectors, target, True)
        self.assert_decision(tuple(reversed(orders)),
                             tuple(tuple(reversed(v)) for v in reversed(vectors)),
                             tuple(reversed(target)), True)

    def test_noncanonical_input_entries(self):
        self.assert_decision((4, 9), ((-3, 10),), (6, -4), True)

    def test_integer_membership_is_not_boolean_feasibility(self):
        result = self.assert_decision((5,), ((1,),), (4,), True)
        self.assertEqual(result.coefficients, (4,))
        self.assertNotIn(4, {0, 1})

    def test_empty_generators_and_trivial_group(self):
        self.assert_decision((4, 9), (), (0, 0), True)
        self.assert_decision((4, 9), (), (0, 3), False)
        self.assertEqual(self.assert_decision((), ((), ()), (), True).coefficients, (0, 0))
        self.assert_decision((), (), (), True)

    def test_zero_and_duplicate_generators(self):
        orders, vectors = (8, 4), ((0, 0), (2, 1), (2, 1))
        reached = subgroup(orders, vectors)
        for target in product(range(8), range(4)):
            self.assert_decision(orders, vectors, target, target in reached)

    def test_all_two_generator_systems_in_c4_squared(self):
        orders = (4, 4)
        elements = list(product(range(4), repeat=2))
        for vectors in product(elements, repeat=2):
            reached = subgroup(orders, vectors)
            for target in elements:
                self.assert_decision(orders, vectors, target, target in reached)

    def test_random_small_mixed_prime_power_groups(self):
        rng = random.Random(20261023)
        for orders in ((2,), (8,), (9,), (2, 4), (4, 8), (3, 9), (4, 9), (2, 3, 4)):
            elements = list(product(*(range(m) for m in orders)))
            for _ in range(12):
                vectors = tuple(rng.choice(elements) for _ in range(rng.randrange(5)))
                reached = subgroup(orders, vectors)
                for target in elements:
                    self.assert_decision(orders, vectors, target, target in reached)

    def test_boolean_two_subgroup_lifting_is_not_bit_slice_elimination(self):
        self.assert_decision((16, 8), ((2, 1), (0, 2)), (6, 5), True)
        self.assert_decision((16, 8), ((2, 1),), (0, 2), False)


class CertificateTests(unittest.TestCase):
    def test_corrupt_positive_witness_rejected(self):
        result = fs.membership((4, 9), ((1, 1),), (2, 5))
        for bad in (replace(result, coefficients=(15,)),
                    replace(result, coefficients=()),
                    replace(result, coefficients=(50,)),
                    replace(result, coefficients=(True,)),
                    replace(result, character_modulus=2)):
            with self.assertRaises(ValueError):
                fs.verify_certificate((4, 9), ((1, 1),), (2, 5), bad)

    def test_corrupt_character_rejected(self):
        result = fs.membership((4, 4), ((1, 1),), (0, 2))
        for bad in (replace(result, character_modulus=3),
                    replace(result, character_terms=((0, 1),)),
                    replace(result, character_terms=((0, 1), (1, 1))),
                    replace(result, character_terms=((2, 1),)),
                    replace(result, character_modulus=4.0),
                    replace(result, character_terms=((0, 3.0), (1, 1))),
                    replace(result, character_terms=((0, 1), (0, 3))),
                    replace(result, coefficients=(0,))):
            with self.assertRaises(ValueError):
                fs.verify_certificate((4, 4), ((1, 1),), (0, 2), bad)

    def test_certificate_verifier_does_not_call_elimination(self):
        positive = fs.membership((4, 9), ((1, 1),), (2, 5))
        negative = fs.membership((4, 4), ((1, 1),), (0, 2))
        with patch.object(fs, "membership", side_effect=AssertionError("must not run")), \
                patch.object(fs, "_solve_primary", side_effect=AssertionError("must not run")):
            fs.verify_certificate((4, 9), ((1, 1),), (2, 5), positive)
            fs.verify_certificate((4, 4), ((1, 1),), (0, 2), negative)


class ResourceTests(unittest.TestCase):
    def test_explicit_resource_limits_are_not_nonmembership(self):
        for limits, reason in (
                (fs.Limits(seconds=0), "wall-time"),
                (fs.Limits(work_units=0), "work-unit"),
                (fs.Limits(cells=0), "cell"),
                (fs.Limits(workspace_bytes=0), "workspace"),
                (fs.Limits(scalar_bits=1), "scalar")):
            result = fs.membership((4, 9), ((1, 1),), (2, 5), limits=limits)
            self.assertEqual(result.status, "unresolved")
            self.assertIn(reason, result.reason)
            fs.verify_certificate((4, 9), ((1, 1),), (2, 5), result)

    def test_unresolved_cannot_smuggle_a_proof(self):
        for result in (fs.MembershipResult("unresolved"),
                       fs.MembershipResult("unresolved", coefficients=(1,), reason="timeout")):
            with self.assertRaises(ValueError):
                fs.verify_certificate((4,), ((1,),), (2,), result)

    def test_crt_resource_stop_does_not_emit_a_partial_witness(self):
        result = fs.membership((4, 9), ((1, 1),), (1, 1),
                               limits=fs.Limits(scalar_bits=4))
        self.assertEqual(result.status, "unresolved")
        self.assertEqual(len(result.completed_primary_systems), 2)
        self.assertEqual(result.coefficients, ())
        fs.verify_certificate((4, 9), ((1, 1),), (1, 1), result)

    def test_invalid_limits_and_dimensions_are_explicit_errors(self):
        for values in ({"seconds": -1}, {"seconds": float("nan")},
                       {"work_units": -1}, {"cells": True}):
            with self.assertRaises(ValueError):
                fs.Limits(**values)
        for orders, vectors, target in (((6,), ((1,),), (1,)),
                                        ((1,), ((0,),), (0,)),
                                        ((4,), ((1, 2),), (1,)),
                                        ((4,), ((True,),), (1,)),
                                        ((4,), ((1,),), ())):
            with self.assertRaises(ValueError):
                fs.membership(orders, vectors, target)


class FrozenPilotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.input_path = Path(cls.temporary.name) / "small-pilot.json.gz"
        data = json.loads(gzip.decompress(fs.DEFAULT_INPUT.read_bytes()))
        data["runs"] = [run for run in data["runs"] if run["name"] == "small-complete-family"]
        cls.input_path.write_bytes(gzip.compress(json.dumps(data).encode("utf-8"), mtime=0))
        cls.input_hash, cls.cases = fs.load_cases(cls.input_path)
        cls.small = [case for case in cls.cases if case.cohort == "small-complete-family"]

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def report(self):
        with redirect_stdout(StringIO()):
            return fs.analyze(self.input_path, case_keys=[case.key for case in self.small])

    def test_small_real_obstruction_and_control_membership(self):
        for case in self.small:
            result = fs.membership(case.instance.orders, case.instance.vectors, case.target)
            self.assertEqual(result.status,
                             "nonmember" if case.target_kind == "real_lp" else "member")
            fs.verify_instance_certificate(case, result)

    def test_report_verifier_does_not_call_algorithm(self):
        report = self.report()
        with patch.object(fs, "membership", side_effect=AssertionError("must not run")), \
                patch.object(fs, "_solve_primary", side_effect=AssertionError("must not run")):
            summary = fs.verify_analysis(json.loads(json.dumps(report)), self.input_path)
        self.assertEqual(summary, {"cases": 2, "member": 1, "nonmember": 1,
                                   "unresolved": 0, "counterexamples": 0})

    def test_report_tampering_is_rejected(self):
        report = self.report()
        for field, value in (("input_sha256", "0" * 64),
                             ("starting_commit", "0" * 40),
                             ("scope", "proved Boolean feasibility"),
                             ("source_sha256", {"fs_reachability.py": "0" * 64})):
            corrupt = json.loads(json.dumps(report))
            corrupt[field] = value
            with self.assertRaises(ValueError):
                fs.verify_analysis(corrupt, self.input_path)
        corrupt = json.loads(json.dumps(report))
        corrupt["cases"][0]["target_kind"] = "planted_control"
        with self.assertRaises(ValueError):
            fs.verify_analysis(corrupt, self.input_path)
        corrupt = json.loads(json.dumps(report))
        positive = next(case for case in corrupt["cases"] if case["target_kind"] == "planted_control")
        coefficient = int(positive["result"]["coefficients"][0], 16)
        positive["result"]["coefficients"][0] = hex(coefficient + 1)
        with self.assertRaises(ValueError):
            fs.verify_analysis(corrupt, self.input_path)

    def test_frozen_input_cannot_be_overwritten_even_with_replace(self):
        original = self.input_path.read_bytes()
        with patch.object(sys, "argv", ["fs", "--input", str(self.input_path),
                                      "--output", str(self.input_path), "--replace"]), \
                redirect_stderr(StringIO()), self.assertRaises(SystemExit):
            fs.main()
        self.assertEqual(self.input_path.read_bytes(), original)

    def test_output_overwrite_guard_and_standalone_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "analysis.json.gz"
            path.write_text("preserve", encoding="utf-8")
            with patch.object(sys, "argv", ["fs", "--input", str(self.input_path),
                                          "--output", str(path)]), \
                    redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                fs.main()
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")
            with patch.object(sys, "argv", ["fs", "--input", str(self.input_path),
                                          "--output", str(path), "--replace",
                                          "--case", self.small[0].key]), \
                    redirect_stdout(StringIO()):
                fs.main()
            self.assertEqual(json.loads(gzip.decompress(path.read_bytes()))["schema"], fs.SCHEMA)
            output = StringIO()
            with patch.object(sys, "argv", ["fs", "--input", str(self.input_path),
                                          "--verify", str(path)]), \
                    patch.object(fs, "membership", side_effect=AssertionError("must not run")), \
                    redirect_stdout(output):
                fs.main()
            self.assertEqual(json.loads(output.getvalue())["nonmember"], 1)


if __name__ == "__main__":
    unittest.main()
