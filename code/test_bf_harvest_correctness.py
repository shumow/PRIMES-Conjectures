"""Correctness tests for S3 bf_harvest (bounded; small family only).

Run: python -B -m unittest discover -s code -p "*correctness.py" -v
"""
from itertools import combinations
from pathlib import Path
import math
import unittest
import unittest.mock

import bf_harvest
from real_pool_pilot import HarvestConfig, harvest as pilot_harvest

SMALL = HarvestConfig("bf-test-small-complete", 113, 565, 3, 100000, 128,
                      False, 20261022)


class Unranking(unittest.TestCase):
    def test_matches_itertools_order(self):
        for n, k in ((7, 3), (10, 4), (5, 1), (6, 6)):
            items = list(range(100, 100 + n))
            expected = list(combinations(items, k))
            for index, combo in enumerate(expected):
                self.assertEqual(bf_harvest.combination_unrank(index, items, k),
                                 combo)

    def test_rejects_out_of_range(self):
        with self.assertRaises(ValueError):
            bf_harvest.combination_unrank(math.comb(7, 3), list(range(7)), 3)
        with self.assertRaises(ValueError):
            bf_harvest.combination_unrank(-1, list(range(7)), 3)

    def test_iterator_covers_ranges_exactly(self):
        items = list(range(9))
        full = list(combinations(items, 3))
        for start, stop in ((0, len(full)), (5, 17), (83, 84), (0, 1)):
            got = list(bf_harvest.iterate_combinations(items, 3, start, stop))
            self.assertEqual(got, full[start:stop])


class ShardRanges(unittest.TestCase):
    def test_partition_exact(self):
        for total, shards in ((10, 3), (39529340, 40), (5, 9), (1, 1)):
            ranges = bf_harvest.shard_ranges(total, shards)
            self.assertEqual(ranges[0][0], 0)
            self.assertEqual(ranges[-1][1], total)
            for (a, b), (c, d) in zip(ranges, ranges[1:]):
                self.assertEqual(b, c)
                self.assertLess(a, b)

    def test_rejects_invalid(self):
        with self.assertRaises(ValueError):
            bf_harvest.shard_ranges(0, 4)


class PilotEquivalence(unittest.TestCase):
    """The sharded complete scan must reproduce the pilot harvest exactly."""

    @classmethod
    def setUpClass(cls):
        cls.pilot_records, cls.pilot_info = pilot_harvest(SMALL)
        cls.scan_records, cls.scan_info = bf_harvest.complete_scan(SMALL, shards=7)

    def test_identical_records_including_certificates(self):
        self.assertEqual(len(self.scan_records), 6)
        self.assertEqual(self.scan_records, self.pilot_records)

    def test_identical_counters(self):
        self.assertEqual(self.scan_info["counts"], self.pilot_info["counts"])
        self.assertTrue(self.scan_info["complete_family_scan"])
        self.assertEqual(self.scan_info["stop_reason"], "family_exhausted")

    def test_manifest_covers_family(self):
        manifest = self.scan_info["coverage_manifest"]
        family = self.scan_info["candidate_family_size"]
        self.assertEqual(sum(entry["draws"] for entry in manifest), family)
        self.assertEqual(manifest[0]["range"][0], 0)
        self.assertEqual(manifest[-1]["range"][1], family)
        self.assertEqual(self.scan_info["workers"], 1)


class PoolCapBehavior(unittest.TestCase):
    def test_binding_cap_records_partial_scope(self):
        capped = HarvestConfig("bf-test-small-capped", 113, 565, 3, 100000, 2,
                               False, 20261022)
        records, info = bf_harvest.complete_scan(capped, shards=7)
        self.assertEqual(len(records), 2)
        self.assertEqual(info["stop_reason"], "pool_cap")
        self.assertFalse(info["complete_family_scan"])
        self.assertLess(info["covered_global_indices"],
                        info["candidate_family_size"])
        self.assertEqual(info["coverage_manifest"][-1]["status"], "pool_cap")

    def test_global_cap_is_not_per_shard(self):
        capped = HarvestConfig("bf-test-small-capped2", 113, 565, 3, 100000, 3,
                               False, 20261022)
        records, info = bf_harvest.complete_scan(capped, shards=50)
        self.assertEqual(len(records), 3)  # 3 total, not 3 per shard


class ConfigurationContract(unittest.TestCase):
    def test_c2_configuration_matches_plan(self):
        config = bf_harvest.C2_COMPLETE
        self.assertEqual((config.plus_bound, config.minus_bound, config.factors),
                         (547, 5470, 3))
        self.assertEqual(config.pool_cap, 4096)
        self.assertEqual(config.prime_power_cap, 8192)
        self.assertFalse(config.sampled)
        self.assertEqual(config.candidate_cap, 39529340)

    def test_rejects_sampled_or_undersized_cap(self):
        with self.assertRaises(ValueError):
            bf_harvest.complete_scan(HarvestConfig("x", 113, 565, 3, 100000, 128,
                                                   True, 1), shards=2)
        with self.assertRaises(ValueError):
            bf_harvest.complete_scan(HarvestConfig("x", 113, 565, 3, 100, 128,
                                                   False, 1), shards=2)

    def test_cli_refuses_without_approval(self):
        with unittest.mock.patch("sys.argv", ["bf_harvest.py"]):
            with self.assertRaises(SystemExit) as caught:
                bf_harvest.main()
        self.assertNotEqual(caught.exception.code, 0)


class SavedReportStages(unittest.TestCase):
    """Bounded end-to-end check of the post-scan stages on the small family."""

    @classmethod
    def setUpClass(cls):
        import gzip
        import json
        import tempfile
        report = bf_harvest.run_s3(SMALL, shards=3)
        cls.tmp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.tmp.name) / "bf_small.json.gz"
        cls.path.write_bytes(gzip.compress(
            (json.dumps(report) + "\n").encode("utf-8"), mtime=0))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_verify_saved_rederives_everything(self):
        summary = bf_harvest.verify_saved(self.path)
        self.assertEqual(summary["records_verified"], 6)
        self.assertTrue(summary["complete_family_scan"])
        bound = summary["minimum_cardinality"]
        self.assertIsNotNone(bound.get("odd_minimum_factors"))
        self.assertEqual(bound["odd_minimum_factors"] % 2, 1)
        self.assertGreaterEqual(bound["odd_minimum_factors"], 3)

    def test_membership_stage_bounded_and_independently_verified(self):
        stage = bf_harvest.run_membership_stage(self.path, wall_seconds=55.0)
        self.assertIn(stage["status"],
                      ("member", "nonmember", "unresolved", "inconclusive"))
        if stage["watchdog"] == "ok":
            self.assertTrue(stage["independently_verified"])
        self.assertEqual(stage["declared_limits"]["seconds"],
                         bf_harvest.MEMBERSHIP_LIMITS["seconds"])


if __name__ == "__main__":
    unittest.main()
