"""Correctness tests for Track C fs_harvest (bounded, no large runs).

Run: python -B -m unittest discover -s code -p "*correctness.py" -v
"""
from pathlib import Path
import math
import unittest

import fs_harvest
from real_pool_pilot import CONFIGS as PILOT_CONFIGS, HarvestConfig
from real_pool_verify import instance_from_json, verify_encoding, verify_metrics, verify_prime


class BudgetContract(unittest.TestCase):
    def test_at_most_four_new_cells(self):
        self.assertLessEqual(len(fs_harvest.CELLS), 4)

    def test_cell_budgets(self):
        for config in (fs_harvest.ANCHOR,) + fs_harvest.CELLS:
            self.assertLessEqual(config.candidate_cap, 5_000_000)
            self.assertLessEqual(config.pool_cap, 1024)
            self.assertGreater(config.minus_bound, config.plus_bound)

    def test_every_cell_has_prior_rationale(self):
        for config in (fs_harvest.ANCHOR,) + fs_harvest.CELLS:
            self.assertIn(config.name, fs_harvest.RATIONALE)
            self.assertGreater(len(fs_harvest.RATIONALE[config.name]), 40)

    def test_anchor_is_exact_pilot_rerun(self):
        pilot = next(c for c in PILOT_CONFIGS if c.name == "medium-complete-family")
        for field in ("plus_bound", "minus_bound", "factors", "candidate_cap",
                      "pool_cap", "sampled", "seed", "prime_power_cap"):
            self.assertEqual(getattr(fs_harvest.ANCHOR, field), getattr(pilot, field),
                             field)


class WilsonInterval(unittest.TestCase):
    def test_reference_value(self):
        low, high = fs_harvest.wilson_interval(50, 100)
        self.assertAlmostEqual(low, 0.40383, places=4)
        self.assertAlmostEqual(high, 0.59617, places=4)

    def test_contains_point_estimate_and_bounds(self):
        for successes, trials in ((0, 10), (1, 7), (6, 6), (483, 4366296)):
            low, high = fs_harvest.wilson_interval(successes, trials)
            self.assertLessEqual(0.0, low)
            self.assertLessEqual(high, 1.0)
            self.assertLessEqual(low, successes / trials)
            self.assertLessEqual(successes / trials, high)

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            fs_harvest.wilson_interval(2, 1)
        with self.assertRaises(ValueError):
            fs_harvest.wilson_interval(-1, 5)


class PerDrawStats(unittest.TestCase):
    def test_duplicates_count_as_certified_successes(self):
        """Regression for the PR #4 review: the Bernoulli numerator is
        accepted + duplicates; values pinned to the reviewer's independently
        computed corrected intervals for c2 and c4."""
        c2 = fs_harvest.per_draw_stats(253, 9, 5_000_000, True, "candidate_cap")
        self.assertEqual(c2["certified_draw_successes"], 262)
        self.assertAlmostEqual(c2["certified_hit_wilson95"][0], 4.6427700e-5, places=11)
        self.assertAlmostEqual(c2["certified_hit_wilson95"][1], 5.9140510e-5, places=11)
        c4 = fs_harvest.per_draw_stats(430, 24, 5_000_000, True, "candidate_cap")
        self.assertEqual(c4["certified_draw_successes"], 454)
        self.assertAlmostEqual(c4["certified_hit_wilson95"][0], 8.2823333e-5, places=11)
        self.assertAlmostEqual(c4["certified_hit_wilson95"][1], 9.9544819e-5, places=11)

    def test_distinct_rate_is_separate_and_uninterval(self):
        stats = fs_harvest.per_draw_stats(253, 9, 5_000_000, True, "candidate_cap")
        self.assertAlmostEqual(stats["distinct_discovery_rate"], 253 / 5_000_000)
        self.assertGreater(stats["certified_hit_rate_per_draw"],
                           stats["distinct_discovery_rate"])
        self.assertIn("no binomial interval", stats["distinct_rate_caveat"])

    def test_pool_cap_truncation_voids_the_interval(self):
        stats = fs_harvest.per_draw_stats(100, 5, 123_456, True, "pool_cap")
        self.assertIsNone(stats["certified_hit_wilson95"])
        self.assertIn("pool cap", stats["interval_caveat"])

    def test_complete_scan_has_no_interval(self):
        stats = fs_harvest.per_draw_stats(483, 0, 4_366_296, False, "family_exhausted")
        self.assertNotIn("certified_hit_wilson95", stats)

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(ValueError):
            fs_harvest.per_draw_stats(1, 0, 0, True, "candidate_cap")
        with self.assertRaises(ValueError):
            fs_harvest.per_draw_stats(-1, 0, 10, True, "candidate_cap")


class SmallFamilyEndToEnd(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        config = HarvestConfig("fs-test-small-complete", 113, 565, 3,
                               100000, 128, False, 20261022)
        fs_harvest.RATIONALE[config.name] = (
            "Test fixture: the pilot's complete small family, rerun through "
            "the Track C cell path for end-to-end validation.")
        cls.cell = fs_harvest.run_cell(config)

    def test_reproduces_pilot_small_family(self):
        self.assertEqual(self.cell["status"], "encoded_and_verified")
        summary = self.cell["summary"]
        self.assertEqual(summary["certified_primes"], 6)
        self.assertEqual(summary["components"], 78)
        self.assertAlmostEqual(summary["group_bits"], 231.65, places=1)
        self.assertTrue(summary["has_obstruction"])
        self.assertTrue(summary["complete_family_scan"])

    def test_summary_internal_consistency(self):
        summary = self.cell["summary"]
        self.assertEqual(summary["binary_nullity"],
                         summary["retained_units"] - summary["binary_rank"])
        self.assertAlmostEqual(summary["pool_per_group_bit"],
                               summary["retained_units"] / summary["group_bits"])
        self.assertNotIn("certified_hit_wilson95", summary)  # complete scan
        self.assertEqual(summary["certified_draw_successes"],
                         summary["certified_primes"] + summary["duplicates"])

    def test_independent_reverification_of_serialized_instance(self):
        instance = instance_from_json(self.cell["instance"])
        for record in instance.records:
            verify_prime(record)
        verify_encoding(instance)
        verify_metrics(instance, self.cell["structure"])


class AnchorComparison(unittest.TestCase):
    def test_missing_dataset_is_reported_not_fabricated(self):
        result = fs_harvest.anchor_comparison(
            {"summary": {}}, Path("does-not-exist.json.gz"))
        self.assertEqual(result["status"], "pilot_dataset_missing")


if __name__ == "__main__":
    unittest.main()
