"""Independent small checks for actual harvesting, encoding and solver outcomes."""
from contextlib import redirect_stdout, redirect_stderr
from dataclasses import replace
from io import StringIO
from itertools import combinations, product
from pathlib import Path
import json
import gzip
import math
import random
import sys
import tempfile
import unittest
from unittest.mock import patch

import a6_oddsolver
import real_pool_pilot as pilot
import real_pool_verify as verify
from verify_machinery import T_minus1


def record(p):
    minus, plus = verify.trial_factors(p - 1), verify.trial_factors(p + 1)
    witness = pilot.lucas_witness(p, minus)
    if witness is None:
        raise ValueError("test fixture has no prime certificate")
    result = verify.PrimeRecord(p, tuple(sorted(minus.items())),
                                tuple(sorted(plus.items())), witness)
    verify.verify_prime(result)
    return result


class CertificateTests(unittest.TestCase):
    def test_source_hash_is_portable_across_git_checkout_newlines(self):
        with tempfile.TemporaryDirectory() as directory:
            windows = Path(directory) / "windows.py"
            posix = Path(directory) / "posix.py"
            windows.write_bytes(b"x = 1\r\ny = 2\r\n")
            posix.write_bytes(b"x = 1\ny = 2\n")
            self.assertEqual(verify.source_digest(windows), verify.source_digest(posix))
            posix.write_bytes(b"x = 1\ny = 3\n")
            self.assertNotEqual(verify.source_digest(windows), verify.source_digest(posix))

    def test_full_factor_certificate(self):
        prime = record(163)
        self.assertEqual(dict(prime.minus), {2: 1, 3: 4})
        self.assertEqual(dict(prime.plus), {2: 2, 41: 1})

    def test_composite_rejected(self):
        composite = verify.PrimeRecord(
            243, ((2, 1), (11, 2)), ((2, 2), (61, 1)), 2)
        with self.assertRaises(ValueError):
            verify.verify_prime(composite)

    def test_corrupt_factorization_and_witness_rejected(self):
        prime = record(163)
        for corrupted in (replace(prime, plus=((2, 2), (41, 2))),
                          replace(prime, witness=1),
                          replace(prime, minus=((2, 1), (3, 3), (3, 1)))):
            with self.assertRaises(ValueError):
                verify.verify_prime(corrupted)

    def test_independent_polynomial_implementation(self):
        for n in range(2, 250):
            self.assertEqual(verify.polynomial_congruence(n), T_minus1(n), n)

    def test_invalid_counterexample_claims_rejected(self):
        primes = (record(3), record(163), record(883))
        for indices in ([1], [1, 2], [1, 1, 2], [-1, 1, 2], [0, 1, 2]):
            with self.assertRaises(ValueError):
                verify.verify_counterexample(primes, indices)


class EncodingTests(unittest.TestCase):
    def test_unit_filter_retains_original_full_moduli(self):
        instance = pilot.build_instance((record(3), record(83)))
        self.assertEqual([r.p for r in instance.records], [83])
        self.assertEqual([r.p for r in instance.excluded_nonunits], [3])
        self.assertEqual((instance.lambda_minus, instance.lambda_plus), (82, 84))
        self.assertEqual(math.prod(instance.orders), 960)
        verify.verify_encoding(instance)

    def test_prime_power_components_not_just_q_minus_one(self):
        instance = pilot.build_instance((record(163), record(883)))
        block = next(block for block in instance.blocks
                     if block.side == "minus" and block.prime == 3)
        self.assertEqual(block.exponent, 4)
        self.assertEqual(block.order, 54)
        self.assertEqual({instance.orders[j] for j in block.columns}, {2, 27})
        self.assertEqual(instance.orders[-1], 2)
        self.assertTrue(all(row[-1] == 1 for row in instance.vectors))
        self.assertEqual(math.gcd(instance.lambda_minus, instance.lambda_plus), 2)

    def test_non_disjoint_sides_rejected(self):
        with self.assertRaises(ValueError):
            pilot.build_instance((record(83), record(163)))

    def test_corrupt_logarithm_and_missing_prime_power_rejected(self):
        instance = pilot.build_instance((record(163), record(883)))
        row = list(instance.vectors[0])
        row[0] = (row[0] + 1) % instance.orders[0]
        with self.assertRaises(ValueError):
            verify.verify_encoding(replace(instance, vectors=(tuple(row),) + instance.vectors[1:]))
        with self.assertRaises(ValueError):
            verify.verify_encoding(replace(
                instance, blocks=(replace(instance.blocks[0], exponent=1),) + instance.blocks[1:]))

    def test_discrete_logs_on_every_unit_of_small_prime_powers(self):
        for q, exponent in ((3, 1), (3, 4), (7, 2), (41, 1)):
            table = pilot.DiscreteLog(q, exponent)
            for value in range(1, q**exponent):
                if math.gcd(value, q) == 1:
                    self.assertEqual(pow(table.generator, table.log(value), table.modulus), value)
        with self.assertRaises(ValueError):
            pilot.DiscreteLog(3, 4).log(3)
        with self.assertRaises(ValueError):
            pilot.DiscreteLog(3, 4, max_baby_steps=1)

    def test_plus_side_support_is_not_forced_identity_on_two_part(self):
        instance = pilot.build_instance((record(163), record(883)))
        metrics = pilot.measure_structure(instance, 1)
        columns = metrics["components_detail"]
        selected = [c for c in columns if c["side"] == "plus" and c["primary_prime"] == 2]
        self.assertTrue(selected)
        self.assertTrue(all(c["forced_zeros"] == 0 for c in selected))
        self.assertTrue(any(c["phi"] is None for c in metrics["sampled_zero_correlations"]))


class NecessaryCheckTests(unittest.TestCase):
    def test_joint_obstruction_has_independent_character(self):
        orders, vectors, target = (2, 2), ((1, 1), (1, 1), (1, 1)), (0, 1)
        checks = pilot.necessary_checks(orders, vectors, target)
        self.assertTrue(checks["has_obstruction"])
        witness = checks["prime_field_checks"][0]["obstruction"]
        verify.verify_obstruction(orders, vectors, target, witness["modulus"], witness["terms"])

    def test_odd_prime_character_and_higher_power_coordinate(self):
        for orders, vectors, target in (((3, 3), ((1, 1),), (0, 1)),
                                        ((4,), ((0,),), (2,))):
            checks = pilot.necessary_checks(orders, vectors, target)
            self.assertTrue(checks["has_obstruction"])
            witnesses = checks["coordinate_obstructions"] + [
                entry["obstruction"] for entry in checks["prime_field_checks"]
                if not entry["consistent"]]
            for witness in witnesses:
                verify.verify_obstruction(orders, vectors, target,
                                           witness["modulus"], witness["terms"])

    def test_passing_linear_checks_does_not_prove_boolean_reachability(self):
        vectors = ((1,), (1,), (1,))
        checks = pilot.necessary_checks((5,), vectors, (4,))
        self.assertFalse(checks["has_obstruction"])
        self.assertFalse(any(sum(bits) % 5 == 4 for bits in product((0, 1), repeat=3)))

    def test_invalid_character_and_composite_primary_order_rejected(self):
        with self.assertRaises(ValueError):
            verify.verify_obstruction((4,), ((0,),), (1,), 3, ((0, 1),))
        with self.assertRaises(ValueError):
            pilot.necessary_checks((6,), ((1,),), (1,))


class ActualPoolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records, cls.harvest = pilot.harvest(pilot.CONFIGS[0])
        cls.instance = pilot.build_instance(cls.records)

    def test_complete_small_family_and_prime_certificates(self):
        self.assertEqual(self.harvest["candidate_family_size"], 62196)
        self.assertTrue(self.harvest["complete_family_scan"])
        self.assertEqual(self.harvest["counts"]["draws"], 62196)
        self.assertEqual([r.p for r in self.records],
                         [22920083, 24987203, 38255363, 46729283, 60824483, 106292003])
        for prime in self.records:
            verify.verify_prime(prime)
        again, _ = pilot.harvest(pilot.CONFIGS[0])
        self.assertEqual(self.records, again)

    def test_sampling_and_pool_caps_are_explicit(self):
        _, sample = pilot.harvest(replace(pilot.CONFIGS[0], sampled=True, candidate_cap=25))
        self.assertEqual(sample["counts"]["draws"], 25)
        self.assertFalse(sample["complete_family_scan"])
        one, capped = pilot.harvest(replace(pilot.CONFIGS[0], pool_cap=1))
        self.assertEqual(len(one), 1)
        self.assertEqual(capped["stop_reason"], "pool_cap")
        self.assertFalse(capped["complete_family_scan"])

    def test_oracle_matches_direct_subset_products_for_all_small_targets(self):
        n = len(self.records)
        for bits in range(1 << n):
            selected = [i for i in range(n) if bits >> i & 1]
            residues = verify.subset_residues(
                self.records, selected, self.instance.lambda_minus, self.instance.lambda_plus)
            expected = [indices for k in range(3, n + 1, 2)
                        for indices in combinations(range(n), k)
                        if verify.subset_residues(self.records, indices,
                            self.instance.lambda_minus, self.instance.lambda_plus) == residues]
            outcome = pilot.residue_oracle(self.instance, n, residues)
            self.assertEqual(outcome["status"] == "solution", bool(expected))
        limited = pilot.residue_oracle(self.instance, n, (1, self.instance.lambda_plus - 1),
                                       state_cap=1)
        self.assertEqual(limited["status"], "inconclusive_budget")
        self.assertEqual(pilot.residue_oracle(self.instance, n, (1, 1), column_cap=1)["status"],
                         "resource_limit")

    def test_all_solvers_on_real_and_separated_planted_targets(self):
        for planted in (False, True):
            case = pilot.benchmark(self.instance, len(self.records), planted, 123)
            for result in case["solvers"].values():
                self.assertEqual(result["status"], "solution" if planted else "proved_no_solution")
            self.assertEqual(case["target_kind"], "planted_control" if planted else "real_lp")
            self.assertEqual(case["target_matches_lp"], not planted)

    def test_saved_report_is_independently_verified_and_tampering_rejected(self):
        with patch.object(pilot, "CONFIGS", (pilot.CONFIGS[0],)), redirect_stdout(StringIO()):
            report = json.loads(json.dumps(pilot.run_pilot()))
        summary = verify.verify_saved_report(report)
        self.assertEqual(summary["instances"], 1)
        self.assertEqual(summary["prime_certificates"], 6)
        self.assertEqual(summary["counterexamples"], 0)
        corrupt = json.loads(json.dumps(report))
        corrupt["runs"][0]["instance"]["vectors"][0][0] ^= 1
        with self.assertRaises(ValueError):
            verify.verify_saved_report(corrupt)
        corrupt = json.loads(json.dumps(report))
        corrupt["source_sha256"]["real_pool_pilot.py"] = "0" * 64
        with self.assertRaises(ValueError):
            verify.verify_saved_report(corrupt)
        for section, key, value in (("structure", "mean_literal_identity_fraction", 0.99),
                                    ("harvest", "complete_family_scan", False)):
            corrupt = json.loads(json.dumps(report))
            corrupt["runs"][0][section][key] = value
            with self.assertRaises(ValueError):
                verify.verify_saved_report(corrupt)
        corrupt = json.loads(json.dumps(report))
        corrupt["runs"][0]["structure"]["necessary_target_checks"]["prime_field_checks"][0]["rank"] = 0
        with self.assertRaises(ValueError):
            verify.verify_saved_report(corrupt)

    def test_selected_subset_conditions_are_separate_from_full_pool_target(self):
        result = pilot.selected_subset_oracle(self.instance, len(self.records))
        self.assertEqual(result["status"], "proved_no_solution")
        self.assertEqual(result["states"], math.comb(6, 3) + math.comb(6, 5))
        result = pilot.selected_subset_oracle(self.instance, len(self.records), state_cap=1)
        self.assertEqual(result["status"], "inconclusive_budget")

    def test_output_overwrite_requires_explicit_permission(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "existing.json"
            path.write_text("preserve", encoding="utf-8")
            with patch.object(sys, "argv", ["real_pool_pilot", "--output", str(path)]), \
                    redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                pilot.main()
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")

    def test_compressed_output_and_independent_cli_round_trip(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.json.gz"
            with patch.object(pilot, "CONFIGS", (pilot.CONFIGS[0],)), \
                    patch.object(sys, "argv", ["pilot", "--output", str(path)]), \
                    redirect_stdout(StringIO()):
                pilot.main()
            self.assertEqual(json.loads(gzip.decompress(path.read_bytes()))["schema"],
                             "real-pool-pilot/v1")
            output = StringIO()
            with patch.object(sys, "argv", ["verify", str(path)]), redirect_stdout(output):
                verify.main()
            self.assertEqual(json.loads(output.getvalue())["prime_certificates"], 6)

    def test_empty_harvest_is_an_explicit_outcome(self):
        config = replace(pilot.CONFIGS[0], candidate_cap=1)
        with patch.object(pilot, "CONFIGS", (config,)), redirect_stdout(StringIO()):
            report = pilot.run_pilot()
        self.assertEqual(report["runs"][0]["status"], "empty_harvest")
        self.assertEqual(verify.verify_saved_report(report)["empty_harvests"], 1)

    def test_minimum_size_mitm_matches_small_boolean_oracle(self):
        rng = random.Random(71)
        for n in range(7):
            for _ in range(3):
                rows = [[rng.randrange(4), rng.randrange(3)] for _ in range(n)]
                for target in product(range(4), range(3)):
                    valid = {bits for bits in range(1 << n)
                             if bin(bits).count("1") >= 3 and bin(bits).count("1") % 2
                             and all(sum(rows[i][j] for i in range(n) if bits >> i & 1) % m == t
                                     for j, (m, t) in enumerate(zip((4, 3), target)))}
                    result, _ = a6_oddsolver.mitm_frontier((4, 3), rows, target, n, min_size=3)
                    self.assertEqual(result is not None, bool(valid))
                    if result is not None:
                        self.assertIn(result, valid)


if __name__ == "__main__":
    unittest.main()
