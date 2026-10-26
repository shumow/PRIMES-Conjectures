"""Small independent oracles for support-blind, bounded information-set search."""
from dataclasses import asdict, replace
from itertools import product
from pathlib import Path
from unittest.mock import patch
from contextlib import redirect_stderr, redirect_stdout
import copy
import gzip
import io
import json
import random
import tempfile
import time
import unittest

import a4_solver
import bf_solver as base
import bf_solver_information_sets as info
from real_pool_verify import RealInstance, UnitBlock, instance_from_json


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


class PilotRunnerAndChecker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = json.loads(gzip.decompress(base.DEFAULT_INPUT.read_bytes()))
        run = next(entry for entry in raw["runs"] if entry["name"] == "medium-complete-family")
        records = instance_from_json(run["instance"]).records[:17]
        # Stub only the validated-loader boundary with a small C2 projection.
        # Real prime products keep independent residue checking active.
        cls.instance = RealInstance(records, (), 2, 12, (UnitBlock("plus", 3, 1, 2, (0,)),),
                                    (2, 2), ((1, 1),) * len(records), (1, 1))
        cls.controls = tuple(base._control(cls.instance, spec) for spec in info.case_specs())
        cls.inputs = {"fixture": "validated small projection, not the full study"}
        cls.context = (cls.instance, cls.controls, cls.inputs)

    def _run(self, outcomes=None):
        pending = iter(outcomes) if outcomes is not None else None

        def simulated(problem):
            self.assertIsNone(problem.exact_size)
            if pending is not None:
                return next(pending)
            # Any three rows solve this projection, including targets planted
            # at support 17. The runner must not enforce the hidden support.
            return info.Result("solution", (0, 1, 2), permutations=1, states=4,
                               candidates=1, wall_seconds=0.01, peak_rss_bytes=1024,
                               memory_measurement="unit fixture")

        with patch.object(info, "_frozen_head", return_value="a" * 40), \
                patch.object(info, "_load_context", return_value=self.context), \
                patch.object(info, "solve", side_effect=simulated) as solver, \
                redirect_stdout(io.StringIO()):
            report = info.run_pilot("unused")
        return report, solver.call_count

    def _verify(self, report):
        with patch.object(info, "_load_context", return_value=self.context):
            return info.verify_report(report)

    def test_declared_protocol_hash_has_not_changed(self):
        self.assertEqual(info.protocol_hash(),
                         "a2ba7c982dc1ea5294a18169cc8a382f41d079163f881ab3fb27cb91f65765b7")

    def test_runner_and_checker_complete_all_eighteen_support_blind_cases(self):
        report, calls = self._run()
        self.assertEqual(calls, 18)
        summary = self._verify(json.loads(json.dumps(report)))
        self.assertEqual(summary["calls"], 18)
        self.assertEqual(summary["solutions"], 18)
        self.assertEqual(summary["not_run"], 0)
        self.assertEqual(summary["errors"], 0)
        self.assertTrue(all(summary[f"support{k}_gate"] for k in (3, 5, 9, 17)))
        self.assertTrue(all(entry["returned_cardinality"] == 3 for entry in report["cases"]))
        self.assertTrue(any(not entry["planted_witness_recovered"] for entry in report["cases"]))

    def test_checker_never_invokes_search_or_affine_producers(self):
        report, _ = self._run()
        with patch.object(info, "_load_context", return_value=self.context), \
                patch.object(info, "solve", side_effect=AssertionError("no solver")), \
                patch.object(info, "_work", side_effect=AssertionError("no worker")), \
                patch.object(info, "affine_masks", side_effect=AssertionError("no enumeration")), \
                patch.object(a4_solver, "gf2_solve", side_effect=AssertionError("no elimination")):
            self.assertEqual(info.verify_report(report)["solutions"], 18)

    def test_failed_phase_gates_skip_later_phases_without_extra_calls(self):
        successful = info.Result("solution", (0, 1, 2), permutations=1, states=4,
                                 candidates=1, wall_seconds=0.01)
        limited = info.Result("inconclusive", reason="fixture state cap", states=4, permutations=1)
        report, calls = self._run([successful] * 3 + [limited] + [successful] * 5)
        summary = self._verify(report)
        self.assertEqual(calls, 9)
        self.assertEqual((summary["solutions"], summary["not_run"]), (8, 9))
        self.assertTrue(summary["support3_gate"])
        self.assertFalse(summary["support5_gate"])
        self.assertFalse(summary["support9_gate"])
        self.assertFalse(summary["support17_gate"])

    def test_errors_abort_once_and_preserve_all_unrun_records(self):
        for status, label in info.ABORT_STATUSES.items():
            report, calls = self._run([info.Result(status, reason="explicit fixture error")])
            summary = self._verify(report)
            self.assertEqual(calls, 1)
            self.assertEqual(summary["errors"], 1)
            self.assertEqual(summary["not_run"], 17)
            self.assertEqual(summary["run_status"], label)
            self.assertTrue(all(entry["not_run_reason"] == label for entry in report["cases"][1:]))

    def test_provenance_scope_gate_and_candidate_tampering_is_rejected(self):
        original, _ = self._run()
        mutations = [
            lambda r: r["protocol"].update(max_calls=19),
            lambda r: r["source_sha256"].__setitem__("bf_solver_information_sets.py", "0" * 64),
            lambda r: r["inputs"].update(fixture="changed"),
            lambda r: r["scope"].update(records=483),
            lambda r: r["cases"].pop(),
            lambda r: r["cases"][0]["case"]["spec"].update(exact=True),
            lambda r: r["cases"][0]["case"]["target_hex"].__setitem__(0, "0x0"),
            lambda r: r["cases"][0]["result"].update(indices=[0, 0, 0]),
            lambda r: r["cases"][0]["result"].update(wall_seconds=60.0),
            lambda r: r["cases"][0]["result"].update(peak_rss_bytes=513 * 1024**2),
            lambda r: r["cases"][0].update(returned_cardinality=3.0),
            lambda r: r["cases"][0].update(planted_witness_recovered=
                                          not r["cases"][0]["planted_witness_recovered"]),
            lambda r: r["cases"][0].update(result=None, not_run_reason="skip"),
            lambda r: r.update(run_status="aborted_worker_error"),
            lambda r: r.update(implementation_commit="not-a-commit"),
            lambda r: r["cases"][0]["result"].update(states=1_000_001),
            lambda r: r["cases"][0]["result"].update(permutations=9),
        ]
        for mutate in mutations:
            report = copy.deepcopy(original)
            mutate(report)
            with self.assertRaises(ValueError):
                self._verify(report)

    def test_malformed_result_types_and_counters_are_rejected(self):
        raw = asdict(info.Result("solution", (0, 1, 2), permutations=1, states=4, candidates=1))
        for key, value in (("indices", [True, 1, 2]), ("states", True),
                           ("states", -1), ("candidates", 5),
                           ("wall_seconds", float("nan")), ("peak_rss_bytes", -1),
                           ("reason", None), ("status", "proved_no_solution"),
                           ("search_seconds", 10.0)):
            with self.assertRaises(ValueError):
                info._read_result({**raw, key: value})

    def test_missing_rss_is_reported_without_inventing_a_measurement(self):
        result = info.Result("solution", (0, 1, 2), permutations=1, states=4,
                             candidates=1, wall_seconds=0.01)
        report, _ = self._run([result] * 18)
        self.assertEqual(self._verify(report)["solutions_without_rss"], 18)

    def test_committed_source_guard_precedes_evaluation(self):
        with patch.object(info, "_frozen_head", side_effect=ValueError("commit source first")), \
                patch.object(info, "solve", side_effect=AssertionError("must not evaluate")):
            with self.assertRaisesRegex(ValueError, "commit source"):
                info.run_pilot("unused")
        with patch.object(info.previous, "_implementation_head", return_value="a" * 40), \
                patch.object(info.subprocess, "check_output", return_value=b"uncommitted source"):
            with self.assertRaisesRegex(ValueError, "commit"):
                info._frozen_head("unused")

    def test_commit_or_source_changes_are_not_published_as_a_frozen_run(self):
        candidate = info.Result("solution", (0, 1, 2), permutations=1, states=4,
                                candidates=1, wall_seconds=0.01)
        with patch.object(info, "_frozen_head", side_effect=["a" * 40, "b" * 40]), \
                patch.object(info, "_load_context", return_value=self.context), \
                patch.object(info, "solve", return_value=candidate), \
                redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "changed"):
            info.run_pilot("unused")
        current = info.sources()
        changed = {**current, "bf_solver_information_sets.py": "0" * 64}
        with patch.object(info, "_frozen_head", return_value="a" * 40), \
                patch.object(info, "sources", side_effect=[current, changed]), \
                patch.object(info, "_load_context", return_value=self.context), \
                patch.object(info, "solve", return_value=candidate), \
                redirect_stdout(io.StringIO()), self.assertRaisesRegex(ValueError, "changed"):
            info.run_pilot("unused")

    def test_context_preserves_support_blindness_and_shares_original_vectors(self):
        prior = json.loads(gzip.decompress(base.DEFAULT_INPUT.with_name(
            "bf_solver_preprocessing.json.gz").read_bytes()))["inputs"]
        inputs = {key: prior[key] for key in ("pilot_sha256", "controls_sha256")}
        with patch.object(base, "_context", return_value=(self.instance, self.controls, inputs)):
            instance, controls, _ = info._load_context()
        self.assertEqual(len(controls), 18)
        self.assertTrue(all(control.problem.exact_size is None for control in controls))
        self.assertTrue(all(control.problem.vectors is instance.vectors for control in controls))

    def test_output_preflight_rejects_frozen_or_existing_files_without_calls(self):
        for name in ("bf_solver.json.gz", "bf_solver_preprocessing.json.gz", "fs_harvest.json.gz",
                     "bf_solver_information_sets.py"):
            with self.assertRaises(ValueError):
                info.validate_output(Path(name))
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bf_solver_information_sets.json.gz"
            path.write_text("preserve", encoding="utf-8")
            with patch("sys.argv", ["info", "--run-pilot", "--output", str(path)]), \
                    patch.object(info, "run_pilot", side_effect=AssertionError("no run")) as runner, \
                    redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                info.main()
            self.assertEqual(runner.call_count, 0)
            self.assertEqual(path.read_text(encoding="utf-8"), "preserve")

    def test_output_is_exclusively_reserved_before_computation(self):
        report, _ = self._run()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bf_solver_information_sets.json.gz"

            def reserved(git):
                self.assertTrue(path.exists())
                with self.assertRaises(FileExistsError):
                    path.open("xb")
                return report

            with patch("sys.argv", ["info", "--run-pilot", "--output", str(path)]), \
                    patch.object(info, "_frozen_head", return_value="a" * 40), \
                    patch.object(info, "run_pilot", side_effect=reserved), \
                    patch.object(info, "_load_context", return_value=self.context), \
                    redirect_stdout(io.StringIO()):
                info.main()
            saved = json.loads(gzip.decompress(path.read_bytes()))
            self.assertEqual(self._verify(saved)["solutions"], 18)

    def test_a_concurrent_output_is_not_overwritten_or_evaluated(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bf_solver_information_sets.json.gz"

            def competing(git):
                path.write_bytes(b"another run")
                return "a" * 40

            with patch("sys.argv", ["info", "--run-pilot", "--output", str(path)]), \
                    patch.object(info, "_frozen_head", side_effect=competing), \
                    patch.object(info, "run_pilot", side_effect=AssertionError("no run")) as runner, \
                    self.assertRaises(FileExistsError):
                info.main()
            self.assertEqual(runner.call_count, 0)
            self.assertEqual(path.read_bytes(), b"another run")

    def test_default_cli_refuses_to_start_a_pilot(self):
        with patch("sys.argv", ["info"]), \
                patch.object(info, "run_pilot", side_effect=AssertionError("no run")), \
                redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            info.main()

    def test_protocol_cli_neither_loads_inputs_nor_runs_searches(self):
        output = io.StringIO()
        with patch("sys.argv", ["info", "--protocol"]), \
                patch.object(info, "_load_context", side_effect=AssertionError("no inputs")), \
                patch.object(info, "run_pilot", side_effect=AssertionError("no run")), \
                redirect_stdout(output):
            info.main()
        declared = json.loads(output.getvalue())
        self.assertEqual(declared["sha256"], info.DECLARED_PROTOCOL_SHA256)
        self.assertEqual(len(declared["protocol"]["cases"]), 18)

    def test_verify_cli_round_trip_needs_neither_git_nor_producers(self):
        report, _ = self._run()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "saved.json.gz"
            path.write_bytes(gzip.compress(json.dumps(report).encode("utf-8"), mtime=0))
            output = io.StringIO()
            with patch("sys.argv", ["info", "--verify", str(path)]), \
                    patch.object(info, "_load_context", return_value=self.context), \
                    patch.object(info, "_frozen_head", side_effect=AssertionError("no git")), \
                    patch.object(info, "run_pilot", side_effect=AssertionError("no run")), \
                    patch.object(info, "solve", side_effect=AssertionError("no search")), \
                    patch.object(info, "affine_masks", side_effect=AssertionError("no masks")), \
                    patch.object(a4_solver, "gf2_solve", side_effect=AssertionError("no elimination")), \
                    redirect_stdout(output):
                info.main()
            self.assertEqual(json.loads(output.getvalue())["solutions"], 18)

    def test_conflicting_modes_and_replace_flag_start_no_pilot(self):
        for arguments in (["--run-pilot", "--verify", "unused.json"], ["--run-pilot", "--replace"]):
            with patch("sys.argv", ["info"] + arguments), \
                    patch.object(info, "run_pilot", side_effect=AssertionError("no run")), \
                    redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                info.main()

    def test_error_report_is_saved_but_cli_exits_unsuccessfully(self):
        report, _ = self._run([info.Result("worker_error", reason="fixture failure")])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "bf_solver_information_sets.json.gz"
            with patch("sys.argv", ["info", "--run-pilot", "--output", str(path)]), \
                    patch.object(info, "_frozen_head", return_value="a" * 40), \
                    patch.object(info, "run_pilot", return_value=report), \
                    patch.object(info, "_load_context", return_value=self.context), \
                    redirect_stdout(io.StringIO()), self.assertRaises(SystemExit) as caught:
                info.main()
            self.assertEqual(caught.exception.code, 1)
            self.assertEqual(self._verify(json.loads(gzip.decompress(path.read_bytes())))["errors"], 1)


if __name__ == "__main__":
    unittest.main()
