"""Small independent oracles for support-blind, bounded information-set search."""
from dataclasses import replace
from itertools import product
from unittest.mock import patch
import random
import time
import unittest

import a4_solver
import bf_solver as base
import bf_solver_information_sets as info


def oracle(problem, maximum=17):
    answers = []
    for bits in product((0, 1), repeat=len(problem.vectors)):
        size = sum(bits)
        if size < problem.min_size or size > maximum or size % 2 == 0:
            continue
        if all(sum(bit * vector[j] for bit, vector in zip(bits, problem.vectors)) % order
               == problem.target[j] for j, order in enumerate(problem.orders)):
            answers.append(tuple(i for i, bit in enumerate(bits) if bit))
    return answers


class AffineMasks(unittest.TestCase):
    def test_exhaustive_small_binary_affine_families(self):
        rng = random.Random(20261025)
        for _ in range(300):
            n = rng.randrange(1, 6)
            rows = [rng.randrange(1 << n) for _ in range(rng.randrange(6))]
            rhs = [rng.randrange(2) for _ in rows]
            solution = a4_solver.gf2_solve(rows, rhs, n)
            expected = {x for x in range(1 << n)
                        if all(bin(row & x).count("1") % 2 == bit
                               for row, bit in zip(rows, rhs))}
            if solution is None:
                self.assertFalse(expected)
            else:
                particular, kernel = solution
                self.assertEqual(set(info.affine_masks(particular, kernel, len(kernel))), expected)

    def test_overlap_updates_selection_not_additive_residual(self):
        self.assertEqual(set(info.affine_masks(1, [3, 5], 2)), {1, 2, 4, 7})

    def test_weight_cap_does_not_claim_full_kernel_enumeration(self):
        self.assertEqual(set(info.affine_masks(0, [1, 2, 4], 1)), {0, 1, 2, 4})
        self.assertNotIn(7, set(info.affine_masks(0, [1, 2, 4], 1)))


class SmallRecovery(unittest.TestCase):
    def decision(self, problem):
        expected = oracle(problem)
        result = info._work((problem, info.Limits(permutations=1), time.monotonic() + 5))
        if expected:
            self.assertEqual(result.status, "solution", (problem, result))
            self.assertIn(result.indices, expected)
            base.verify_subset(problem, result.indices)
        else:
            self.assertIn(result.status, ("inconclusive", "projection_inconsistent"))
            self.assertEqual(result.indices, ())

    def test_all_four_generator_c4_targets(self):
        # Four Boolean variables have at most three free coordinates once odd
        # parity is included, so a single set exhausts the entire affine family.
        for values in product(range(4), repeat=4):
            for target in range(4):
                self.decision(base.make_problem((4,), [(v,) for v in values], (target,)))

    def test_seeded_mixed_groups_without_cardinality_hints(self):
        rng = random.Random(918273)
        for orders in ((), (3, 9), (4, 8), (2, 3, 4)):
            for _ in range(40):
                vectors = [tuple(rng.randrange(m) for m in orders)
                           for _ in range(rng.randrange(3, 5))]
                target = tuple(rng.randrange(m) for m in orders)
                self.decision(base.make_problem(orders, vectors, target))

    def test_distinct_small_supports_need_no_exact_size(self):
        rng = random.Random(7727)
        for n, support in ((5, 3), (7, 5), (9, 7), (17, 17)):
            orders = (4,) * n + (9,)
            vectors = [tuple(int(i == j) for j in range(n)) + (rng.randrange(9),)
                       for i in range(n)]
            target = tuple(sum(vectors[i][j] for i in range(support)) % order
                           for j, order in enumerate(orders))
            problem = base.make_problem(orders, vectors, target)
            self.assertIsNone(problem.exact_size)
            result = info._work((problem, info.Limits(permutations=1), time.monotonic() + 5))
            self.assertEqual(result.status, "solution")
            self.assertEqual(result.indices, tuple(range(support)))

    def test_full_odd_and_higher_power_constraints_are_retained(self):
        for target in ((1, 1), (0, 1)):
            self.decision(base.make_problem((3, 2), ((1, 1), (0, 1), (0, 1)), target))
        self.decision(base.make_problem((4,), ((1,),) * 3, (1,)))

    def test_state_limit_is_inconclusive_on_known_feasible_target(self):
        problem = base.make_problem((3, 2), ((1, 1), (0, 1), (0, 1)), (1, 1))
        result = info._work((problem, info.Limits(states=1), time.monotonic() + 5))
        self.assertEqual(result.status, "inconclusive")
        self.assertTrue(oracle(problem))

    def test_selection_cap_is_not_a_nonexistence_claim(self):
        n = 5
        vectors = [tuple(int(i == j) for j in range(n)) for i in range(n)]
        problem = base.make_problem((2,) * n, vectors, (1,) * n)
        result = info._work((problem, info.Limits(selection_cap=3), time.monotonic() + 5))
        self.assertEqual(result.status, "inconclusive")
        self.assertTrue(oracle(problem))

    def test_expired_worker_deadline(self):
        problem = base.make_problem((4,), ((1,),) * 3, (3,))
        result = info._work((problem, info.Limits(), time.monotonic() - 1))
        self.assertEqual(result.status, "timeout_enforced")


class RuntimeAndProtocol(unittest.TestCase):
    def setUp(self):
        self.problem = base.make_problem((4, 8), ((3, 7),) * 3, (1, 5))

    def test_exact_support_hint_is_rejected(self):
        with self.assertRaises(ValueError):
            info.solve(replace(self.problem, exact_size=3))

    def test_invalid_limits_are_explicit(self):
        for kwargs in ({"seconds": 61}, {"memory_mib": 513}, {"free_weight": 4},
                       {"states": 0}, {"selection_cap": 18}, {"permutations": 9},
                       {"solver_seed": True}):
            with self.assertRaises(ValueError):
                info.Limits(**kwargs)

    def test_preflight_limits_start_no_worker(self):
        with patch.object(base, "run_limited", side_effect=AssertionError("must not start")):
            self.assertEqual(info.solve(self.problem, info.Limits(seconds=0)).status,
                             "timeout_enforced")
            with patch.object(base, "MAX_ENTRIES", 1):
                self.assertEqual(info.solve(self.problem).status, "resource_limit")
            self.assertEqual(info.solve(replace(self.problem, min_size=19)).status, "inconclusive")

    def test_worker_payload_has_no_support_or_planting_metadata(self):
        def worker(fn, payload, seconds):
            self.assertIs(fn, info._work)
            problem, limits, deadline = payload
            self.assertIsNone(problem.exact_size)
            self.assertEqual(set(problem.__dataclass_fields__),
                             {"orders", "vectors", "target", "min_size", "exact_size"})
            self.assertEqual(limits.selection_cap, 17)
            self.assertEqual(limits.solver_seed, 1729)
            self.assertGreater(deadline, time.monotonic())
            return "ok", info.Result("solution", (0, 1, 2)), 0

        with patch.object(base, "run_limited", side_effect=worker):
            self.assertEqual(info.solve(self.problem).status, "solution")

    def test_errors_timeouts_and_late_candidates_remain_distinct(self):
        for kind, value, expected in (("timeout", None, "timeout_enforced"),
                                      ("worker_error", "ValueError: bad input", "worker_error")):
            with patch.object(base, "run_limited", return_value=(kind, value, 0)):
                result = info.solve(self.problem)
            self.assertEqual(result.status, expected)
            self.assertTrue(result.reason)

        def late(*args):
            time.sleep(0.02)
            return "ok", info.Result("solution", (0, 1, 2)), 0.02

        with patch.object(base, "run_limited", side_effect=late):
            self.assertEqual(info.solve(self.problem, info.Limits(seconds=0.01)).status,
                             "timeout_enforced")

    def test_corrupt_and_over_memory_results_are_rejected(self):
        for bad in ({}, info.Result("unknown", reason="bad"),
                    info.Result("solution", (0, 0, 0))):
            with patch.object(base, "run_limited", return_value=("ok", bad, 0)), \
                    self.assertRaises((TypeError, ValueError)):
                info.solve(self.problem)
        result = info.Result("solution", (0, 1, 2), peak_rss_bytes=513 * 1024**2)
        with patch.object(base, "run_limited", return_value=("ok", result, 0)):
            self.assertEqual(info.solve(self.problem).status, "resource_limit")

    def test_actual_spawn_round_trip(self):
        result = info.solve(self.problem, info.Limits(seconds=10))
        self.assertEqual(result.status, "solution", result)
        self.assertEqual(result.indices, (0, 1, 2))
        self.assertLess(result.wall_seconds, 10)

    def test_protocol_has_fresh_holdouts_and_no_exact_hints(self):
        specs = info.case_specs()
        self.assertEqual(len(specs), 18)
        self.assertEqual([sum(s.phase == p for s in specs) for p in range(4)], [3, 6, 3, 6])
        self.assertTrue(all(not s.exact for s in specs))
        old = {104729, 130363, 155921}
        fresh = {s.seed for s in specs if s.holdout}
        self.assertEqual(len(fresh), 6)
        self.assertFalse(fresh & old)
        self.assertEqual(info.protocol()["limits"]["seconds"], 60)
        self.assertEqual(info.protocol()["limits"]["memory_mib"], 512)


if __name__ == "__main__":
    unittest.main()
