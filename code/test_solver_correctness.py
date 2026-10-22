"""Small independent oracles for the A4/A6 solver correctness audit.

Run with: python -m unittest discover -s code -p test_solver_correctness.py -v
"""
import itertools
import random
import unittest

import a4_solver
import a6_oddsolver


def satisfies_binary(mask, rows, rhs):
    return all((mask & row).bit_count() % 2 == b
               for row, b in zip(rows, rhs))


def satisfies_group(mask, pool, orders, target):
    if mask.bit_count() % 2 != 1:
        return False
    return all(sum(row[j] for i, row in enumerate(pool) if mask >> i & 1) % order
               == target[j] % order for j, order in enumerate(orders))


class BinaryEliminationTests(unittest.TestCase):
    def test_particular_solution_back_substitution(self):
        rows, rhs = [3, 2, 3], [1, 1, 1]
        x0, _ = a4_solver.gf2_solve(rows, rhs, 2)
        self.assertTrue(satisfies_binary(x0, rows, rhs))
        self.assertEqual(x0, 2)

    def test_kernel_back_substitution(self):
        x0, kernel = a4_solver.gf2_solve([3, 6], [0, 0], 3)
        self.assertEqual(x0, 0)
        self.assertEqual(kernel, [7])

    def test_a6_retains_legacy_pivot_column_return(self):
        x0, kernel, pivots = a6_oddsolver.gf2_solve([3, 6], [1, 0], 3)
        self.assertTrue(satisfies_binary(x0, [3, 6], [1, 0]))
        self.assertEqual(kernel, [7])
        self.assertEqual(pivots, [0, 1])

    def test_exhaustive_affine_solution_sets(self):
        for ncols in range(4):
            for nrows in range(4):
                for rows in itertools.product(range(1 << ncols), repeat=nrows):
                    for rhs in itertools.product((0, 1), repeat=nrows):
                        expected = {mask for mask in range(1 << ncols)
                                    if satisfies_binary(mask, rows, rhs)}
                        result = a4_solver.gf2_solve(rows, rhs, ncols)
                        if not expected:
                            self.assertIsNone(result, (rows, rhs))
                            continue
                        self.assertIsNotNone(result, (rows, rhs))
                        x0, kernel = result
                        actual = {x0}
                        for vector in kernel:
                            actual |= {mask ^ vector for mask in actual}
                        self.assertEqual(actual, expected, (rows, rhs))
                        self.assertEqual(len(actual), 1 << len(kernel))


class ResidualSearchTests(unittest.TestCase):
    def test_residual_target_sign(self):
        result = a4_solver.mitm_close(
            1, [6], [[0], [1], [0]], [3], [1], 3, [0], random.Random(1))
        self.assertEqual(result, 7)

    def test_no_false_positive_from_negated_target(self):
        result = a4_solver.mitm_close(
            1, [6], [[0], [2], [0]], [3], [1], 3, [0], random.Random(1))
        self.assertIsNone(result)

    def test_overlapping_kernel_moves_and_base(self):
        result = a4_solver.mitm_close(
            1, [3, 5], [[0], [1], [1]], [3], [2], 3, [0], random.Random(1))
        self.assertEqual(result, 7)

    def test_carries_are_residual_constraints(self):
        pool, orders, target = [[1], [1], [0]], [4], [2]
        result, _ = a6_oddsolver.solve(
            [(2, 4)], orders, pool, target, 3, random.Random(1), 0.1)
        self.assertIsNotNone(result)
        self.assertTrue(satisfies_group(result, pool, orders, target))

    def test_unique_projection_with_unmet_residual(self):
        result, _ = a6_oddsolver.solve(
            [(2, 4)], [4], [[1]], [3], 1, random.Random(1), 0.1)
        self.assertIsNone(result)

    def test_a4_returned_solutions_meet_original_constraints(self):
        rng = random.Random(41)
        orders = [4, 3, 5]
        for ncols in range(1, 9):
            for _ in range(12):
                pool = [[rng.randrange(order) for order in orders]
                        for _ in range(ncols)]
                target = [rng.randrange(order) for order in orders]
                result, _ = a4_solver.full_solve(pool, orders, target, ncols, rng)
                if result is not None:
                    self.assertTrue(satisfies_group(result, pool, orders, target))

    def test_a6_returned_solutions_meet_original_constraints(self):
        rng = random.Random(42)
        orders, comps = [4, 3], [(2, 4), (3, 3)]
        for ncols in range(1, 7):
            for _ in range(8):
                pool = [[rng.randrange(order) for order in orders]
                        for _ in range(ncols)]
                target = [rng.randrange(order) for order in orders]
                result, _ = a6_oddsolver.solve(
                    comps, orders, pool, target, ncols, rng, 0.005)
                if result is not None:
                    self.assertTrue(satisfies_group(result, pool, orders, target))


class MeetInTheMiddleOracleTests(unittest.TestCase):
    def test_odd_solution_not_shadowed_by_empty_subset(self):
        pool, orders, target = [[0], [1]], [3], [0]
        result, _ = a6_oddsolver.mitm_frontier(orders, pool, target, 2)
        self.assertIsNotNone(result)
        self.assertTrue(satisfies_group(result, pool, orders, target))

    def test_even_only_solution_is_rejected(self):
        result, _ = a6_oddsolver.mitm_frontier([3], [[1], [1]], [2], 2)
        self.assertIsNone(result)

    def test_exhaustive_small_group_targets(self):
        rng = random.Random(43)
        orders = [4, 3]
        for ncols in range(7):
            for _ in range(4):
                pool = [[rng.randrange(order) for order in orders]
                        for _ in range(ncols)]
                for target in itertools.product(*(range(order) for order in orders)):
                    expected = {mask for mask in range(1 << ncols)
                                if satisfies_group(mask, pool, orders, target)}
                    result, _ = a6_oddsolver.mitm_frontier(
                        orders, pool, target, ncols)
                    if not expected:
                        self.assertIsNone(result, (pool, target))
                    else:
                        self.assertIn(result, expected, (pool, target))


if __name__ == "__main__":
    unittest.main()
