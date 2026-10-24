"""Bounded correctness tests for Track A (code/fs_controls.py).

unittest-discoverable:  python -m unittest discover -s code -p "test_fs_*.py"
or directly:            python code/test_fs_controls_correctness.py
All tests are deterministic and complete in well under a minute; they use the
frozen pilot dataset read-only and small synthetic groups.
"""
from itertools import combinations
from pathlib import Path
import gzip
import json
import random
import sys
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fs_controls
from real_pool_verify import instance_from_json, subset_residues, verify_group_solution

PILOT = Path(__file__).resolve().parent.parent / "data" / "generated" / "real_pool_pilot.json.gz"


def _spin_for_test(payload):
    deadline = time.monotonic() + payload
    while time.monotonic() < deadline:
        pass
    return None, "finished", {}


def _raise_for_test(payload):
    raise ValueError(f"intentional test failure: {payload}")


def _small_instance():
    data = json.loads(gzip.decompress(PILOT.read_bytes()).decode("utf-8"))
    run = next(r for r in data["runs"] if r["name"] == "small-complete-family")
    return instance_from_json(run["instance"])


def _brute_force_exact_k(orders, pool, target, k):
    for combo in combinations(range(len(pool)), k):
        if all(sum(pool[i][j] for i in combo) % orders[j] == target[j]
               for j in range(len(orders))):
            return sorted(combo)
    return None


class TrackAControlsTests(unittest.TestCase):

    def test_fixed_k_mitm_agrees_with_exhaustive_oracle(self):
        rng = random.Random(20261023)
        for trial in range(25):
            n = rng.randrange(5, 11)
            d = rng.randrange(2, 6)
            orders = [rng.choice([2, 3, 4, 5, 7, 9]) for _ in range(d)]
            pool = [[rng.randrange(o) for o in orders] for _ in range(n)]
            for k in (3, 5):
                if k > n:
                    continue
                if trial % 2:                   # planted, guaranteed feasible
                    witness = rng.sample(range(n), k)
                    target = [sum(pool[i][j] for i in witness) % orders[j]
                              for j in range(d)]
                else:                           # arbitrary, often infeasible
                    target = [rng.randrange(o) for o in orders]
                found, message, _ = fs_controls.fixed_k_mitm(
                    orders, pool, target, k, work_cap=10**7, table_cap=1 << 16)
                expected = _brute_force_exact_k(orders, pool, target, k)
                self.assertEqual(found is None, expected is None, (message, trial, k))
                if found is not None:
                    self.assertEqual(len(found), k)
                    self.assertEqual(len(set(found)), k)
                    self.assertTrue(all(
                        sum(pool[i][j] for i in found) % orders[j] == target[j]
                        for j in range(d)))

    def test_fixed_k_mitm_rejects_even_or_tiny_cardinality(self):
        with self.assertRaises(ValueError):
            fs_controls.fixed_k_mitm([3], [[1]] * 4, [0], 2, work_cap=100, table_cap=16)
        found, message, _ = fs_controls.fixed_k_mitm(
            [3], [[1]] * 2, [0], 3, work_cap=100, table_cap=16)
        self.assertIsNone(found)
        self.assertEqual(message, "cardinality_infeasible")

    def test_fixed_k_mitm_respects_declared_caps(self):
        orders = [5] * 4
        pool = [[1, 2, 3, 4] for _ in range(30)]
        found, message, counts = fs_controls.fixed_k_mitm(
            orders, pool, [0, 0, 0, 0], 5, work_cap=10, table_cap=1 << 16)
        self.assertIsNone(found)
        self.assertTrue(message.startswith("resource_limit"))
        self.assertEqual(counts, {"left": 0, "right": 0, "hash_matches": 0})

    def test_planted_controls_verify_and_hide_witness(self):
        instance = _small_instance()
        record = fs_controls.experiment(instance, "small-complete-family",
                                        len(instance.records), 3, 101)
        self.assertEqual(record["target_kind"], "planted_control")
        witness = record["planted_witness_indices"]
        self.assertEqual(len(witness), 3)
        self.assertEqual(len(set(witness)), 3)
        rows = instance.vectors
        target = tuple(sum(rows[i][j] for i in witness) % order
                       for j, order in enumerate(instance.orders))
        residues = subset_residues(instance.records, witness,
                                   instance.lambda_minus, instance.lambda_plus)
        verify_group_solution(instance, witness, target, residues)
        for name, entry in record["solvers"].items():
            self.assertNotIn("planted_witness_indices", entry, name)
            self.assertNotIn("planting_seed_label", entry, name)
        repeat = fs_controls.experiment(instance, "small-complete-family",
                                        len(instance.records), 3, 101)
        self.assertEqual(repeat["planted_witness_indices"], witness)
        for entry in record["solvers"].values():
            if entry.get("status") == "solution":
                self.assertIsNotNone(entry.get("indices"))

    def test_solution_statuses_come_from_declared_vocabulary(self):
        instance = _small_instance()
        record = fs_controls.experiment(instance, "small-complete-family",
                                        len(instance.records), None, None)
        allowed = {"solution", "proved_no_solution",
                   "proved_no_solution_exact_cardinality", "resource_limit",
                   "inconclusive_budget", "timeout_enforced", "worker_error"}
        for name, entry in record["solvers"].items():
            self.assertIn(entry["status"], allowed, name)
            self.assertNotEqual(entry["status"], "worker_error", name)
        self.assertTrue(record["has_necessary_obstruction"])

    def test_mod2_rank_matches_pilot_definition(self):
        instance = _small_instance()
        rank, nullity = fs_controls.mod2_rank_nullity(instance, len(instance.records))
        self.assertEqual(rank + nullity, len(instance.records))
        self.assertEqual((rank, nullity), (6, 0))   # pilot: rank 6, nullity 0

    def test_watchdog_enforces_wall_clock(self):
        kind, value, elapsed = fs_controls.run_limited(_spin_for_test, 30, 1.0)
        self.assertEqual(kind, "timeout")
        self.assertIsNone(value)
        self.assertLess(elapsed, 15)

    def test_watchdog_classifies_worker_errors(self):
        kind, value, elapsed = fs_controls.run_limited(_raise_for_test, "boom", 10.0)
        self.assertEqual(kind, "worker_error")
        self.assertIn("ValueError", value)
        self.assertIn("boom", value)

    def test_watchdog_returns_results_and_is_deterministic(self):
        instance = _small_instance()
        payload = (instance.vectors, instance.orders, list(instance.target),
                   len(instance.records), "det-check/a4", 64, 3)
        first = fs_controls.run_limited(fs_controls._work_a4, payload, 30.0)
        second = fs_controls.run_limited(fs_controls._work_a4, payload, 30.0)
        self.assertEqual(first[0], "ok")
        self.assertEqual(first[1][:2], second[1][:2])


if __name__ == "__main__":
    unittest.main(verbosity=2)
