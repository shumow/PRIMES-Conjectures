"""Bounded checks of density definitions and reported benchmark outputs."""
import contextlib
import io
import random
import unittest
from unittest.mock import patch

import a8_omega_solver
import a9_divisor_harvest
import a10_wagner_density
import a12_adaptive_cultivation


class DensityModelTests(unittest.TestCase):
    def test_a10_preserves_legacy_forced_zero_distribution(self):
        rng = random.Random(50)
        reference = [tuple(0 if rng.random() < 0.004 else rng.randrange(3)
                           for _ in range(20)) for _ in range(100)]
        actual = a10_wagner_density.make_pool(20, 0.004, 100, 3, random.Random(50))
        self.assertEqual(actual, reference)

    def test_a10_literal_identity_frequency(self):
        pool = a10_wagner_density.make_pool(50, 0.004, 1000, 3, random.Random(51))
        frequency = sum(value == 0 for row in pool for value in row) / 50000
        self.assertAlmostEqual(frequency, 0.004 + 0.996 / 3, delta=0.006)

    def test_a8_component_dependent_identity_frequency(self):
        orders, pool, _, _ = a8_omega_solver.make_structured(
            20, 0.004, 2000, 5, random.Random(52))
        expected = sum(0.004 + 0.996 / order for order in orders) / len(orders)
        frequency = sum(value == 0 for row in pool for value in row) / 40000
        self.assertAlmostEqual(frequency, expected, delta=0.006)

    def test_a12_uses_literal_identity_probability(self):
        rng = random.Random(53)
        values = [value for _ in range(500)
                  for value in a12_adaptive_cultivation.fresh_vec(60, 0.004, 3, rng)]
        self.assertAlmostEqual(values.count(0) / len(values), 0.004, delta=0.003)

    def test_a10_output_distinguishes_the_parameter_from_identity_frequency(self):
        output = io.StringIO()
        with patch("sys.argv", ["a10_wagner_density.py", "3", "12"]), \
                patch.object(a10_wagner_density, "max_solvable_r", return_value=0), \
                contextlib.redirect_stdout(output):
            a10_wagner_density.main()
        self.assertIn("forced-zero", output.getvalue())
        self.assertIn("literal", output.getvalue())
        self.assertIn("0.336", output.getvalue())
        self.assertNotIn("so harvesting more cannot", output.getvalue())

    def test_side_support_is_not_full_group_identity(self):
        pool, _ = a9_divisor_harvest.harvest([41], [3, 7], 6)
        self.assertEqual(pool, [(41, 1, 2, 3)])
        p = 2 * pool[0][0] + 1
        self.assertEqual(p % 41, 1)
        self.assertEqual(p % 3, 2)
        self.assertEqual(p % 7, 6)


class CultivationReportingTests(unittest.TestCase):
    def test_minimum_is_preserved_after_a_worse_perturbation(self):
        moves = [(1, 2), (1, 1), (1, 1)]
        with patch.object(a12_adaptive_cultivation, "fresh_vec", side_effect=moves):
            best = a12_adaptive_cultivation.cultivate(
                2, 0.004, 3, random.Random(54), 1, (1, 1), 2, 1)
        self.assertEqual(best, 1)

    def test_zero_step_budget_reports_initial_deficit(self):
        best = a12_adaptive_cultivation.cultivate(
            2, 0.004, 3, random.Random(55), 1, (1, 0), 0, 1)
        self.assertEqual(best, 1)

    def test_empty_restart_budget_is_an_explicit_error(self):
        with self.assertRaises(ValueError):
            a12_adaptive_cultivation.cultivate(
                2, 0.004, 3, random.Random(56), 1, (1, 0), 2, 0)

    def test_target_dimension_mismatch_is_an_explicit_error(self):
        with self.assertRaises(ValueError):
            a12_adaptive_cultivation.cultivate(
                2, 0.004, 3, random.Random(57), 1, (1,), 2, 1)


class FourSumTests(unittest.TestCase):
    def test_distinct_indices_and_original_target_equations(self):
        rng = random.Random(58)
        for dimension in range(1, 6):
            for _ in range(10):
                pool = a10_wagner_density.make_pool(dimension, 0.2, 40, 3, rng)
                target = tuple(rng.randrange(3) for _ in range(dimension))
                result = a10_wagner_density.wagner4_zero(
                    pool, dimension, 3, rng, target)
                if result is not None:
                    self.assertEqual(len(set(result)), 4)
                    self.assertTrue(all(sum(pool[i][j] for i in result) % 3 == target[j]
                                        for j in range(dimension)))

    def test_zero_pool_has_a_four_sum_but_not_an_odd_cardinality_certificate(self):
        result = a10_wagner_density.wagner4_zero(
            [(0, 0)] * 8, 2, 3, random.Random(59))
        self.assertEqual(len(set(result)), 4)
        self.assertEqual(len(result) % 2, 0)


if __name__ == "__main__":
    unittest.main()
