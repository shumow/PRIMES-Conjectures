"""Independent subset oracles and adversarial tests for the S1 model."""
from dataclasses import replace
from importlib.util import find_spec
from itertools import product
from pathlib import Path
import copy
import gzip
import json
import random
import tempfile
import time
import unittest
from unittest.mock import patch

import bf_solver as bf


def oracle(problem):
    answers = []
    for bits in product((0, 1), repeat=len(problem.vectors)):
        size = sum(bits)
        if size < problem.min_size or size % 2 != 1:
            continue
        if problem.exact_size is not None and size != problem.exact_size:
            continue
        if all(sum(bit * vector[j] for bit, vector in zip(bits, problem.vectors)) % order
               == problem.target[j] for j, order in enumerate(problem.orders)):
            answers.append(tuple(i for i, bit in enumerate(bits) if bit))
    return answers


class ModelContractTests(unittest.TestCase):
    def test_normalization_retains_all_prime_powers(self):
        problem = bf.make_problem((4, 8), ((-1, 15), (7, -1), (3, 7)), (-3, -3),
                                  exact_size=3)
        self.assertEqual(problem.orders, (4, 8))
        self.assertEqual(problem.vectors, ((3, 7),) * 3)
        rows = list(bf.carry_rows(problem))
        self.assertEqual([(r.target, r.upper) for r in rows], [(1, 2), (5, 2)])
        bf.verify_subset(problem, (0, 1, 2))

    def test_carry_bounds_match_direct_arithmetic(self):
        rng = random.Random(20261024)
        for _ in range(80):
            n, order = rng.randrange(1, 7), rng.randrange(2, 17)
            problem = bf.make_problem((order,), [(rng.randrange(-30, 31),) for _ in range(n)],
                                      (rng.randrange(-30, 31),))
            row = next(bf.carry_rows(problem))
            for bits in product((0, 1), repeat=n):
                total = sum(bit * vector[0] for bit, vector in zip(bits, problem.vectors))
                modular = total % order == problem.target[0]
                carried = any(total == row.target + order * z
                              for z in range(row.upper + 1))
                self.assertEqual(modular, carried)

    def test_invalid_inputs_are_explicit_errors(self):
        for orders, vectors, target in (
                ((1,), ((0,),), (0,)), ((True,), ((0,),), (0,)),
                ((4,), ((1, 2),), (1,)), ((4,), ((True,),), (1,)),
                ((4,), ((1,),), ()), ((4,), ((1,),), (1.5,))):
            with self.assertRaises(ValueError):
                bf.make_problem(orders, vectors, target)
        for kwargs in ({"min_size": 2}, {"min_size": True}, {"exact_size": 4},
                       {"exact_size": True}, {"exact_size": 1}):
            with self.assertRaises(ValueError):
                bf.make_problem((4,), ((1,),) * 5, (3,), **kwargs)

    def test_invalid_limits(self):
        for kwargs in ({"seconds": -1}, {"seconds": 61}, {"seconds": float("nan")},
                       {"seconds": True}, {"memory_mib": 513}, {"memory_mib": 0},
                       {"memory_mib": True}):
            with self.assertRaises(ValueError):
                bf.Limits(**kwargs)

    def test_direct_cardinality_and_zero_row_certificates(self):
        cases = (
            bf.make_problem((4,), (), (0,)),
            bf.make_problem((), ((),) * 4, (), min_size=4),
            bf.make_problem((4,), ((1,),) * 3, (1,), exact_size=5),
            bf.make_problem((4,), ((0,),) * 3, (1,)),
        )
        with patch.object(bf, "backend_version", side_effect=AssertionError("no backend")):
            for problem in cases:
                result = bf.solve(problem)
                self.assertIs(result.status, bf.Outcome.PROVED_NO_SOLUTION)
                bf.verify_result(problem, result)
                self.assertEqual(oracle(problem), [])

    def test_range_guard_is_not_an_impossibility_claim(self):
        problem = bf.make_problem((2**64,), ((2**63,),) * 3, (2**63,))
        with patch.object(bf, "backend_version", side_effect=AssertionError("no backend")):
            result = bf.solve(problem)
        self.assertIs(result.status, bf.Outcome.RESOURCE_LIMIT)
        self.assertIn("64-bit", result.reason)
        self.assertTrue(oracle(problem))

    def test_bad_subset_rejected(self):
        problem = bf.make_problem((4,), ((1,),) * 5, (3,), exact_size=3)
        for bad in ((0, 0, 0), (0, 1, 8), (0, 1), (0, 1, True), (0, 1, 2, 3, 4)):
            with self.assertRaises(ValueError):
                bf.verify_subset(problem, bad)

    def test_verifier_independent_of_model_and_backend(self):
        problem = bf.make_problem((4,), ((1,),) * 3, (3,))
        result = bf.Result(bf.Outcome.SOLUTION, (0, 1, 2))
        with patch.object(bf, "carry_rows", side_effect=AssertionError("no model")), \
                patch.object(bf, "solve", side_effect=AssertionError("no solver")), \
                patch.object(bf, "_work_cpsat", side_effect=AssertionError("no backend")):
            bf.verify_result(problem, result)

    def test_false_proof_and_failure_payload_rejected(self):
        problem = bf.make_problem((4,), ((1,),) * 3, (3,))
        for bad in (bf.Result(bf.Outcome.PROVED_NO_SOLUTION, reason="cardinality"),
                    bf.Result(bf.Outcome.PROVED_NO_SOLUTION, reason="row_target_out_of_range:0"),
                    bf.Result(bf.Outcome.PROVED_NO_SOLUTION, reason="backend said so"),
                    bf.Result(bf.Outcome.TIMEOUT, (0, 1, 2), reason="timeout"),
                    bf.Result(bf.Outcome.SOLUTION, (0, 1, 2), reason="timeout"),
                    bf.Result(bf.Outcome.WORKER_ERROR)):
            with self.assertRaises(ValueError):
                bf.verify_result(problem, bad)


class WatchdogContractTests(unittest.TestCase):
    def setUp(self):
        self.problem = bf.make_problem((4,), ((1,),) * 3, (3,))

    def test_zero_budget_needs_no_backend(self):
        with patch.object(bf, "backend_version", side_effect=AssertionError("no import")):
            result = bf.solve(self.problem, limits=bf.Limits(seconds=0))
        self.assertIs(result.status, bf.Outcome.TIMEOUT)

    def test_missing_or_wrong_backend_is_an_explicit_error(self):
        with patch.object(bf.metadata, "version",
                          side_effect=bf.metadata.PackageNotFoundError("ortools")), \
                self.assertRaises(bf.BackendUnavailableError):
            bf.backend_version()
        with patch.object(bf.metadata, "version", return_value="wrong"), \
                self.assertRaises(bf.BackendUnavailableError):
            bf.backend_version()

    def test_timeout_and_worker_error_remain_explicit(self):
        for message, value, expected in (
                ("timeout", None, bf.Outcome.TIMEOUT),
                ("worker_error", "ArithmeticError: invalid model", bf.Outcome.WORKER_ERROR)):
            with patch.object(bf, "backend_version", return_value=bf.BACKEND_VERSION), \
                    patch.object(bf, "run_limited", return_value=(message, value, 0.0)):
                result = bf.solve(self.problem)
            self.assertIs(result.status, expected)
            self.assertEqual(result.indices, ())
            self.assertTrue(result.reason)

    def test_late_solution_not_accepted(self):
        def late(*args):
            time.sleep(0.04)
            return "ok", bf.Result(bf.Outcome.SOLUTION, (0, 1, 2)), 0.04

        with patch.object(bf, "backend_version", return_value=bf.BACKEND_VERSION), \
                patch.object(bf, "run_limited", side_effect=late):
            result = bf.solve(self.problem, limits=bf.Limits(seconds=0.02))
        self.assertIs(result.status, bf.Outcome.TIMEOUT)
        self.assertEqual(result.indices, ())

    def test_over_memory_target_not_a_success(self):
        value = bf.Result(bf.Outcome.SOLUTION, (0, 1, 2), peak_rss_bytes=513 * 1024**2)
        with patch.object(bf, "backend_version", return_value=bf.BACKEND_VERSION), \
                patch.object(bf, "run_limited", return_value=("ok", value, 0.0)):
            result = bf.solve(self.problem)
        self.assertIs(result.status, bf.Outcome.RESOURCE_LIMIT)
        self.assertEqual(result.indices, ())

    def test_no_witness_or_planting_metadata_reaches_worker(self):
        def worker(fn, payload, seconds):
            problem, limits, deadline, seed = payload
            self.assertIs(fn, bf._work_cpsat)
            self.assertEqual(set(problem.__dataclass_fields__),
                             {"orders", "vectors", "target", "min_size", "exact_size"})
            self.assertEqual(seed, 1729)
            return "ok", bf.Result(bf.Outcome.SOLUTION, (0, 1, 2)), 0.0

        with patch.object(bf, "backend_version", return_value=bf.BACKEND_VERSION), \
                patch.object(bf, "run_limited", side_effect=worker):
            self.assertIs(bf.solve(self.problem).status, bf.Outcome.SOLUTION)

    def test_corrupt_worker_protocol_is_an_error(self):
        with patch.object(bf, "backend_version", return_value=bf.BACKEND_VERSION), \
                patch.object(bf, "run_limited", return_value=("ok", {}, 0.0)), \
                self.assertRaises(TypeError):
            bf.solve(self.problem)


class ProtocolTests(unittest.TestCase):
    def test_case_plan_is_bounded_and_separates_holdouts_and_modes(self):
        specs = bf.case_specs()
        self.assertEqual(len(specs), 18)
        self.assertEqual(len({s.name for s in specs}), 18)
        self.assertEqual([sum(s.phase == phase for s in specs) for phase in range(3)], [3, 6, 9])
        self.assertEqual(sum(not s.exact for s in specs), 3)
        self.assertEqual({s.seed for s in specs if s.holdout}, {104729, 130363, 155921})
        self.assertEqual({s.seed for s in specs if not s.holdout}, {101, 202, 303})
        self.assertEqual(bf.protocol()["limits"], {"seconds": 60.0, "memory_mib": 512})

    def test_gates_require_completed_successful_prior_batches(self):
        records = []
        self.assertTrue(bf._may_run(0, records))
        self.assertFalse(bf._may_run(1, records))
        records.extend({"phase": 0, "result": {"status": "solution"}} for _ in range(3))
        self.assertTrue(bf._may_run(1, records))
        self.assertFalse(bf._may_run(2, records))
        records.extend({"phase": 1, "result": {"status": "solution"}} for _ in range(6))
        self.assertTrue(bf._may_run(2, records))
        records[-1]["result"]["status"] = "timeout_enforced"
        self.assertFalse(bf._may_run(2, records))

    def test_result_round_trip_and_malformed_measurements(self):
        raw = json.loads(json.dumps(bf.asdict(bf.Result(bf.Outcome.SOLUTION, (0, 1, 2)))))
        self.assertEqual(bf._read_result(raw).indices, (0, 1, 2))
        for key, bad in (("indices", [True, 1, 2]), ("indices", [0.0, 1, 2]),
                         ("wall_seconds", -1), ("wall_seconds", True),
                         ("model_seconds", float("nan")), ("peak_rss_bytes", -1),
                         ("status", "global_impossibility")):
            changed = dict(raw, **{key: bad})
            with self.assertRaises(ValueError):
                bf._read_result(changed)

    def test_protocol_tampering_rejected_before_input_verification(self):
        report = {"schema": bf.SCHEMA, "baseline_commit": bf.BASELINE, "protocol": {}}
        with patch.object(bf, "_context", side_effect=AssertionError("must not load")), \
                self.assertRaises(ValueError):
            bf.verify_report(report)

    def test_output_cannot_replace_frozen_input_or_unrelated_artifact(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            pilot, controls = root / "pilot.json.gz", root / "controls.json.gz"
            for path in (pilot, controls, root / "fs_harvest.json.gz", root / "bf_solver.py"):
                with self.assertRaises(ValueError):
                    bf.validate_output(path, pilot, controls, True)
            output = root / "bf_solver.json.gz"
            bf.validate_output(output, pilot, controls, False)
            output.write_text("preserve", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                bf.validate_output(output, pilot, controls, False)
            self.assertEqual(output.read_text(encoding="utf-8"), "preserve")
            bf.validate_output(output, pilot, controls, True)


@unittest.skipUnless(bf.DEFAULT_INPUT.with_name("bf_solver.json.gz").exists(),
                     "frozen S1 pilot artifact not generated")
class FrozenReportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.report = json.loads(gzip.decompress(
            bf.DEFAULT_INPUT.with_name("bf_solver.json.gz").read_bytes()))
        cls.context = bf._context(bf.DEFAULT_INPUT, bf.CONTROL_INPUT)

    def test_saved_report_check_needs_no_solver_or_carry_builder(self):
        with patch.object(bf, "_context", return_value=self.context), \
                patch.object(bf, "solve", side_effect=AssertionError("no solver")), \
                patch.object(bf, "_work_cpsat", side_effect=AssertionError("no backend")), \
                patch.object(bf, "backend_version", side_effect=AssertionError("no dependency")), \
                patch.object(bf, "carry_rows", side_effect=AssertionError("no model")):
            summary = bf.verify_report(self.report)
        self.assertEqual(summary, {"calls": 3, "solutions": 0, "not_run": 15,
                                   "support3_gate": False, "support5_gate": False,
                                   "counterexamples": 0})

    def test_saved_report_tampering_is_rejected(self):
        changed = []
        raw = copy.deepcopy(self.report)
        raw["protocol"]["max_calls"] = 19
        changed.append(raw)
        raw = copy.deepcopy(self.report)
        raw["source_sha256"]["bf_solver.py"] = "0" * 64
        changed.append(raw)
        raw = copy.deepcopy(self.report)
        raw["inputs"]["pilot_sha256"] = "0" * 64
        changed.append(raw)
        raw = copy.deepcopy(self.report)
        raw["cases"][0]["case"]["target_hex"][0] = "0xbad"
        changed.append(raw)
        raw = copy.deepcopy(self.report)
        raw["cases"][0]["result"]["status"] = "backend_reported_infeasible"
        changed.append(raw)
        raw = copy.deepcopy(self.report)
        raw["cases"][3]["result"] = raw["cases"][0]["result"]
        changed.append(raw)
        raw = copy.deepcopy(self.report)
        raw["cases"].pop()
        changed.append(raw)
        raw = copy.deepcopy(self.report)
        raw["cases"][0]["result"].update(status="solution", indices=[0, 0, 0], reason="")
        changed.append(raw)
        with patch.object(bf, "_context", return_value=self.context):
            for corrupt in changed:
                with self.assertRaises(ValueError):
                    bf.verify_report(corrupt)


@unittest.skipUnless(find_spec("ortools") is not None, "optional S1 backend not installed")
class NativeBackendTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        bf.backend_version()
        from ortools.sat.python import cp_model
        # Oracle fixtures time the model, while the spawn test includes cold import.
        if cp_model.CpModel().validate():
            raise AssertionError("optional backend rejects an empty model")

    def decision(self, problem):
        expected = oracle(problem)
        if bf._cardinality_impossible(problem) or any(r.upper < 0 for r in bf.carry_rows(problem)):
            result = bf.solve(problem)
        else:
            result = bf._work_cpsat((problem, bf.Limits(seconds=5), time.monotonic() + 5, 1729))
        if expected:
            self.assertIs(result.status, bf.Outcome.SOLUTION, (problem, result))
            self.assertIn(result.indices, expected)
        else:
            self.assertIn(result.status, (bf.Outcome.BACKEND_INFEASIBLE,
                                          bf.Outcome.PROVED_NO_SOLUTION), (problem, result))
        bf.verify_result(problem, result)

    def test_seeded_small_groups_agree_with_exhaustive_subsets(self):
        rng = random.Random(20261024)
        for orders in ((2,), (4,), (8,), (2, 4), (3, 9), (4, 9), (2, 3, 4), (6, 8)):
            for _ in range(10):
                n = rng.randrange(8)
                vectors = [tuple(rng.randrange(order) for order in orders) for _ in range(n)]
                for _ in range(4):
                    target = tuple(rng.randrange(order) for order in orders)
                    self.decision(bf.make_problem(orders, vectors, target,
                                                 exact_size=rng.choice((None, 3, 5))))

    def test_carries_joint_powers_and_general_cardinality(self):
        for problem in (
                bf.make_problem((4, 8), ((3, 7),) * 3, (1, 5), exact_size=3),
                bf.make_problem((4, 4), ((1, 1),) * 5, (0, 2)),
                bf.make_problem((3, 2), ((1, 1), (0, 1), (0, 1)), (1, 1), exact_size=3),
                bf.make_problem((), ((),) * 5, (), min_size=4),
                bf.make_problem((2**80,), ((0,),) * 3, (0,)),
                bf.make_problem((4,), ((1,),) * 5, (1,), exact_size=3),
                bf.make_problem((4,), ((1,),) * 5, (1,))):
            self.decision(problem)

    def test_spawned_solver_round_trip(self):
        problem = bf.make_problem((4, 8), ((3, 7),) * 3, (1, 5), exact_size=3)
        result = bf.solve(problem, limits=bf.Limits(seconds=10))
        self.assertIs(result.status, bf.Outcome.SOLUTION, result)
        self.assertEqual(result.indices, (0, 1, 2))
        self.assertLess(result.wall_seconds, 10)
        self.assertIsNotNone(result.model_seconds)
        self.assertIsNotNone(result.solve_seconds)
        if result.peak_rss_bytes is not None:
            self.assertLessEqual(result.peak_rss_bytes, 512 * 1024**2)


if __name__ == "__main__":
    unittest.main()
