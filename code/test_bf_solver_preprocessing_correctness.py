"""Independent subgroup/subset oracles for the versioned S1 preprocessing round."""
from dataclasses import replace
from itertools import product
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stdout
import copy
import gzip
import io
import json
import math
import random
import tempfile
import time
import unittest

import bf_solver as original
import bf_solver_preprocessing as pre
from real_pool_verify import RealInstance, UnitBlock, instance_from_json


def subgroup(orders, vectors):
    reached = {tuple(0 for _ in orders)}
    frontier = list(reached)
    while frontier:
        current = frontier.pop()
        for vector in vectors:
            following = tuple((a + b) % m for a, b, m in zip(current, vector, orders))
            if following not in reached:
                reached.add(following)
                frontier.append(following)
    return reached


def subset_oracle(problem):
    answers = []
    for bits in product((0, 1), repeat=len(problem.vectors)):
        if sum(bits) != problem.exact_size:
            continue
        if all(sum(bit * v[j] for bit, v in zip(bits, problem.vectors)) % m == problem.target[j]
               for j, m in enumerate(problem.orders)):
            answers.append(tuple(i for i, bit in enumerate(bits) if bit))
    return answers


class SplitSaturationTests(unittest.TestCase):
    def test_criterion_agrees_with_exhaustive_primary_subgroups(self):
        rng = random.Random(20261025)
        successes = failures = 0
        for orders in ((2, 2), (2, 4, 2), (9, 2, 2), (2, 8, 2, 3), (4, 2, 9, 2)):
            keep, drop = [i for i, m in enumerate(orders) if m == 2]
            for _ in range(40):
                vectors = []
                for _ in range(rng.randrange(8)):
                    v = [rng.randrange(m) for m in orders]
                    v[drop] = v[keep]
                    vectors.append(v)
                target = tuple(rng.randrange(m) for m in orders)
                problem = original.make_problem(orders, vectors, target)
                reached = subgroup(orders, vectors)
                index = math.prod(orders) // len(reached)
                if index != 2:
                    with self.assertRaises(pre.NotCertifiedError):
                        pre.certify_split_index_two(problem, keep, drop)
                    failures += 1
                    continue
                certificate = pre.certify_split_index_two(problem, keep, drop)
                result = pre.verify_split_index_two(problem, certificate)
                self.assertEqual(result["index"], index)
                self.assertEqual(result["target_member"], target in reached)
                successes += 1
        self.assertGreater(successes, 0)
        self.assertGreater(failures, 0)

    def test_binary_codimension_one_is_not_enough_for_order_four(self):
        problem = original.make_problem((4, 4), ((1, 1),), (0, 2))
        self.assertEqual(16 // len(subgroup(problem.orders, problem.vectors)), 4)
        with self.assertRaisesRegex(ValueError, "order exactly two"):
            pre.certify_split_index_two(problem, 0, 1)

    def test_higher_power_deficiency_is_not_certified(self):
        problem = original.make_problem((2, 2, 4), ((1, 1, 2),), (1, 1, 0))
        with self.assertRaises(pre.NotCertifiedError):
            pre.certify_split_index_two(problem, 0, 1)

    def test_target_outside_split_kernel_is_certified_nonmember(self):
        problem = original.make_problem((2, 2, 9), ((1, 1, 1),), (0, 1, 0))
        cert = pre.certify_split_index_two(problem, 0, 1)
        self.assertFalse(pre.verify_split_index_two(problem, cert)["target_member"])

    def test_gate_verifier_does_not_call_certificate_generation(self):
        problem = original.make_problem((2, 2, 4, 9),
                                        ((1, 1, 0, 0), (0, 0, 1, 0), (0, 0, 0, 1)), (1, 1, 2, 8))
        cert = pre.certify_split_index_two(problem, 0, 1)
        with patch.object(pre, "certify_split_index_two", side_effect=AssertionError("no producer")), \
                patch.object(pre, "_basis_columns", side_effect=AssertionError("no producer")):
            self.assertTrue(pre.verify_split_index_two(problem, cert)["target_member"])

    def test_incomplete_swapped_or_false_certificate_is_rejected(self):
        problem = original.make_problem((2, 2, 3, 5),
                                        ((1, 1, 1, 1),), (1, 1, 0, 0))
        cert = pre.certify_split_index_two(problem, 0, 1)
        bad = []
        value = copy.deepcopy(cert)
        value["parts"].pop(0)
        bad.append(value)
        value = copy.deepcopy(cert)
        value["parts"][1] = copy.deepcopy(value["parts"][2])
        bad.append(value)
        value = copy.deepcopy(cert)
        value["parts"][1]["prime"] = 5
        bad.append(value)
        value = copy.deepcopy(cert)
        value["parts"][0]["generator_indices"] = [True]
        bad.append(value)
        value = copy.deepcopy(cert)
        value["parts"][0]["coordinates"] = [1]
        bad.append(value)
        value = copy.deepcopy(cert)
        value["target_member"] = False
        bad.append(value)
        value = copy.deepcopy(cert)
        value["index"] = 4
        bad.append(value)
        value = copy.deepcopy(cert)
        value["parts"][0]["prime"] = 2.0
        bad.append(value)
        for corrupt in bad:
            with self.assertRaises(ValueError):
                pre.verify_split_index_two(problem, corrupt)

    def test_invalid_relation_and_coordinates_are_explicit_errors(self):
        problem = original.make_problem((2, 2), ((0, 1),), (0, 0))
        with self.assertRaises(pre.NotCertifiedError):
            pre.certify_split_index_two(problem, 0, 1)
        for keep, drop in ((0, 0), (-1, 1), (0, 2), (True, 1)):
            with self.assertRaises(ValueError):
                pre.certify_split_index_two(problem, keep, drop)

    def test_rank_probe_deadline(self):
        problem = original.make_problem((2, 2), ((1, 1),), (1, 1))
        with self.assertRaises(TimeoutError):
            pre._basis_columns(problem, [0], 2, time.monotonic() - 1)


class FilterOracleTests(unittest.TestCase):
    def decision(self, problem):
        expected = subset_oracle(problem)
        result = pre._work_filtered((problem, pre.SearchLimits(), time.monotonic() + 10))
        if expected:
            self.assertEqual(result.status, "solution", (problem, result))
            self.assertIn(result.indices, expected)
            original.verify_subset(problem, result.indices)
        else:
            self.assertEqual(result.status, "completed_exact_scope", (problem, result))

    def test_all_four_generator_c4_targets(self):
        for vectors in product(range(4), repeat=4):
            for target in range(4):
                self.decision(original.make_problem((4,), [(v,) for v in vectors],
                                                    (target,), exact_size=3))

    def test_random_small_mixed_groups(self):
        rng = random.Random(20261025)
        for orders in ((), (2,), (4, 8), (3, 9), (2, 3, 4), (6, 8)):
            for _ in range(30):
                vectors = [tuple(rng.randrange(m) for m in orders)
                           for _ in range(rng.randrange(3, 9))]
                target = tuple(rng.randrange(m) for m in orders)
                self.decision(original.make_problem(orders, vectors, target,
                                                    exact_size=rng.choice((3, 5, 7))))

    def test_collision_lists_preserved_until_later_full_target_match(self):
        problem = original.make_problem((3,), ((0,), (0,), (0,), (0,), (1,)),
                                        (1,), exact_size=3)
        result = pre._work_filtered((problem, pre.SearchLimits(), time.monotonic() + 5))
        self.assertEqual(result.status, "solution")
        self.assertGreater(result.candidates, 1)
        original.verify_subset(problem, result.indices)

    def test_binary_match_does_not_discard_higher_power_carries(self):
        problem = original.make_problem((4,), ((1,),) * 3, (1,), exact_size=3)
        self.decision(problem)
        self.assertTrue(pre.binary_syndromes(problem)[0])

    def test_no_repeated_prime_from_overlapping_halves(self):
        problem = original.make_problem((3,), ((1,), (0,), (0,)), (2,), exact_size=3)
        self.decision(problem)

    def test_xor_projection_never_replaces_full_odd_residuals(self):
        for target in ((0, 1), (1, 1)):
            self.decision(original.make_problem((3, 2), ((1, 1), (0, 1), (0, 1)),
                                                target, exact_size=3))

    def test_candidate_guard_is_not_nonexistence(self):
        problem = original.make_problem((3,), ((0,), (0,), (0,), (0,), (1,)),
                                        (1,), exact_size=3)
        result = pre._work_filtered((problem, pre.SearchLimits(max_candidates=1),
                                     time.monotonic() + 5))
        self.assertEqual(result.status, "resource_limit")
        self.assertTrue(subset_oracle(problem))

    def test_expired_worker_deadline(self):
        problem = original.make_problem((4,), ((1,),) * 3, (3,), exact_size=3)
        result = pre._work_filtered((problem, pre.SearchLimits(), time.monotonic() - 1))
        self.assertEqual(result.status, "timeout_enforced")


class FilterRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.problem = original.make_problem((4, 8), ((3, 7),) * 3, (1, 5), exact_size=3)

    def test_caps_and_zero_budget_do_not_launch_worker(self):
        with patch.object(original, "run_limited", side_effect=AssertionError("must not start")):
            self.assertEqual(pre.solve_filtered(self.problem, pre.SearchLimits(seconds=0)).status,
                             "timeout_enforced")
            self.assertEqual(pre.solve_filtered(
                self.problem, pre.SearchLimits(max_left_entries=1)).status, "resource_limit")
            self.assertEqual(pre.solve_filtered(
                self.problem, pre.SearchLimits(max_enumerations=1)).status, "resource_limit")
            with patch.object(original, "MAX_ENTRIES", 1):
                self.assertEqual(pre.solve_filtered(self.problem).status, "resource_limit")

    def test_limits_and_missing_exact_cardinality_are_errors(self):
        for kwargs in ({"seconds": 61}, {"memory_mib": 513},
                       {"max_candidates": True}, {"max_enumerations": 0}):
            with self.assertRaises(ValueError):
                pre.SearchLimits(**kwargs)
        with self.assertRaises(ValueError):
            pre.solve_filtered(replace(self.problem, exact_size=None))

    def test_worker_errors_and_timeouts_preserve_status_and_details(self):
        for kind, value, expected in (("worker_error", "ValueError: bad input", "worker_error"),
                                      ("timeout", None, "timeout_enforced")):
            with patch.object(original, "run_limited", return_value=(kind, value, 0)):
                result = pre.solve_filtered(self.problem)
            self.assertEqual(result.status, expected)
            self.assertTrue(result.reason)
            if kind == "worker_error":
                self.assertIn("ValueError: bad input", result.reason)

    def test_late_and_over_memory_candidates_are_not_successes(self):
        result = pre.SearchResult("solution", (0, 1, 2), peak_rss_bytes=513 * 1024**2)
        with patch.object(original, "run_limited", return_value=("ok", result, 0)):
            self.assertEqual(pre.solve_filtered(self.problem).status, "resource_limit")

        def delayed(*args):
            time.sleep(0.03)
            return "ok", replace(result, peak_rss_bytes=100), 0.03

        with patch.object(original, "run_limited", side_effect=delayed):
            self.assertEqual(pre.solve_filtered(
                self.problem, pre.SearchLimits(seconds=0.01)).status, "timeout_enforced")

    def test_actual_spawn_includes_independent_cardinality_check(self):
        result = pre.solve_filtered(self.problem, pre.SearchLimits(seconds=10))
        self.assertEqual(result.status, "solution", result)
        self.assertEqual(result.indices, (0, 1, 2))
        self.assertLess(result.wall_seconds, 10)
        original.verify_subset(self.problem, result.indices)

    def test_invalid_worker_protocol_or_false_candidate_is_rejected(self):
        for value in ({}, pre.SearchResult("not-a-status", reason="invalid"),
                      pre.SearchResult("solution", (0, 0, 0))):
            with patch.object(original, "run_limited", return_value=("ok", value, 0)), \
                    self.assertRaises((TypeError, ValueError)):
                pre.solve_filtered(self.problem)


class ProtocolAndReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data = json.loads(gzip.decompress(original.DEFAULT_INPUT.read_bytes()))
        raw = next(run for run in data["runs"] if run["name"] == "small-complete-family")
        records = instance_from_json(raw["instance"]).records
        # Stub the validated-input boundary with a genuine C2 projection. Real
        # primes keep the independent residue check active; no encoding is claimed.
        cls.instance = RealInstance(records, (), 2, 12, (UnitBlock("plus", 3, 1, 2, (0,)),),
                                    (2, 2), ((1, 1),) * len(records), (1, 1))
        cls.instances = {"pilot": cls.instance, "s3": cls.instance}
        cls.controls = tuple(original._control(cls.instance, spec) for spec in pre.case_specs())
        cls.inputs = {"fixture": "validated projection boundary"}
        with redirect_stdout(io.StringIO()):
            gates = pre.arithmetic_gates(cls.instances)
        entries = []
        for control in cls.controls:
            k = control.spec.support
            result = pre.SearchResult("solution", tuple(range(k)),
                                      left_entries=math.comb(len(records), k // 2),
                                      right_entries=1, candidates=1, wall_seconds=0.01)
            entries.append({"phase": control.spec.phase, "case": original._case_json(control),
                            "result": pre.asdict(result), "not_run_reason": "",
                            "residue_verification_seconds": 0.01})
        cls.report = {
            "schema": pre.SCHEMA, "baseline_commit": original.BASELINE,
            "implementation_commit": "a" * 40, "protocol": pre.protocol(),
            "protocol_sha256": pre.protocol_hash(), "source_sha256": pre.sources(),
            "source_hash_normalization": "CRLF-to-LF", "inputs": cls.inputs,
            "arithmetic_gates": gates, "cases": entries, "counterexamples": 0,
        }

    def test_protocol_is_nine_exact_calls_with_fixed_unused_holdouts(self):
        specs = pre.case_specs()
        self.assertEqual(len(specs), 9)
        self.assertEqual(sum(spec.phase == 0 for spec in specs), 3)
        self.assertEqual(sum(spec.phase == 1 for spec in specs), 6)
        self.assertTrue(all(spec.exact for spec in specs))
        self.assertEqual({spec.seed for spec in specs if spec.holdout},
                         {104729, 130363, 155921})
        self.assertEqual(pre.protocol()["max_calls"], 9)
        self.assertEqual(pre.protocol()["aggregate_call_seconds"], 540)
        self.assertEqual(pre.protocol()["limits"]["seconds"], 60)
        self.assertEqual(pre.protocol()["limits"]["memory_mib"], 512)

    def test_report_check_does_not_call_search_or_gate_generation(self):
        with patch.object(pre, "_load_inputs", return_value=(
                self.instances, self.controls, self.inputs)), \
                patch.object(pre, "solve_filtered", side_effect=AssertionError("no search")), \
                patch.object(pre, "_work_filtered", side_effect=AssertionError("no search")), \
                patch.object(pre, "_basis_columns", side_effect=AssertionError("no producer")), \
                patch.object(pre, "certify_split_index_two", side_effect=AssertionError("no producer")):
            summary = pre.verify_report(self.report, "unused", None)
        self.assertEqual(summary, {"calls": 9, "solutions": 9, "not_run": 0,
                                   "support3_gate": True, "support5_gate": True,
                                   "arithmetic_instances": 2, "counterexamples": 0})

    def test_report_tampering_and_incomplete_primary_coverage_are_rejected(self):
        altered = []
        value = copy.deepcopy(self.report)
        value["protocol"]["max_calls"] = 10
        altered.append(value)
        value = copy.deepcopy(self.report)
        value["source_sha256"]["bf_solver_preprocessing.py"] = "0" * 64
        altered.append(value)
        value = copy.deepcopy(self.report)
        value["arithmetic_gates"][0]["certificate"]["parts"] = []
        altered.append(value)
        value = copy.deepcopy(self.report)
        value["arithmetic_gates"][0]["certificate"]["index"] = 4
        altered.append(value)
        value = copy.deepcopy(self.report)
        value["cases"].pop()
        altered.append(value)
        value = copy.deepcopy(self.report)
        value["cases"][0]["result"].update(status="timeout_enforced", indices=(), reason="deadline")
        altered.append(value)
        value = copy.deepcopy(self.report)
        value["cases"][0]["result"]["indices"] = [0, 0, 0]
        altered.append(value)
        value = copy.deepcopy(self.report)
        value["cases"][0]["case"]["target_hex"][0] = "0x0"
        altered.append(value)
        value = copy.deepcopy(self.report)
        value["cases"][0]["result"]["wall_seconds"] = 61
        altered.append(value)
        with patch.object(pre, "_load_inputs", return_value=(self.instances, self.controls, self.inputs)):
            for corrupt in altered:
                with self.assertRaises(ValueError):
                    pre.verify_report(corrupt, "unused", None)

    def test_malformed_result_measurements_are_rejected(self):
        raw = pre.asdict(pre.SearchResult("solution", (0, 1, 2)))
        for key, bad in (("indices", [True, 1, 2]), ("status", "proved_global_impossibility"),
                         ("wall_seconds", -1), ("candidates", True),
                         ("peak_rss_bytes", -1), ("projection_seconds", float("nan"))):
            with self.assertRaises(ValueError):
                pre._read_result({**raw, key: bad})

    def test_output_preflight_protects_previous_round_and_existing_results(self):
        for name in ("bf_solver.json.gz", "real_pool_pilot.json.gz", "fs_harvest.json.gz",
                     "bf_solver_preprocessing.py"):
            with self.assertRaises(ValueError):
                pre.validate_output(Path(name), True)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bf_solver_preprocessing.json.gz"
            pre.validate_output(path, False)
            path.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                pre.validate_output(path, False)
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")


if __name__ == "__main__":
    unittest.main()
