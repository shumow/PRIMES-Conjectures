"""Producer-version diagnostics on saved reports, without running experiments."""
from contextlib import ExitStack, contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch
import copy
import gzip
import hashlib
import io
import json
import tempfile
import unittest

import a4_solver
import bf_solver as baseline
import bf_solver_information_sets as information
import bf_solver_preprocessing as preprocessing

MODULES = (baseline, preprocessing, information)
ARTIFACTS = (
    ("bf_solver.json.gz", "67b7dd568c925432546d8f43373cab4a8e638abe79fa3802873202243dd5b9a5"),
    ("bf_solver_preprocessing.json.gz",
     "d100e499dfa7c6b3ae5b2cac7ff67e00ed46dea08e6078693cf0671fdfbb2e1a"),
    ("bf_solver_information_sets.json.gz",
     "d62ac9ba58789262180a71589eb0c3ae9e7e42c0272e1e1a8f2dfbb5d8c149e7"),
)


@contextmanager
def no_producers():
    with ExitStack() as stack:
        for module, names in (
                (baseline, ("solve", "_work_cpsat", "backend_version", "carry_rows",
                            "run_limited", "run_pilot")),
                (preprocessing, ("solve_filtered", "_work_filtered", "_basis_columns",
                                 "certify_split_index_two", "run_round")),
                (information, ("solve", "_work", "affine_masks", "run_pilot")),
                (a4_solver, ("gf2_solve",))):
            for name in names:
                stack.enter_context(patch.object(
                    module, name, side_effect=AssertionError("producer must not run: " + name)))
        yield


def current_sources(module):
    return baseline._sources() if module is baseline else module.sources()


class SourceVersionDiagnostics(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = {}
        for module, (filename, expected_hash) in zip(MODULES, ARTIFACTS):
            raw = baseline.DEFAULT_INPUT.with_name(filename).read_bytes()
            if hashlib.sha256(raw).hexdigest() != expected_hash:
                raise AssertionError("archived report changed: " + filename)
            cls.reports[module.SCHEMA] = json.loads(gzip.decompress(raw))
        with no_producers():
            cls.baseline_context = baseline._context(baseline.DEFAULT_INPUT, baseline.CONTROL_INPUT)
            with patch.object(baseline, "_context", return_value=cls.baseline_context):
                cls.preprocessing_context = preprocessing._load_inputs(
                    "unused", baseline.DEFAULT_INPUT.with_name("bf_harvest.json.gz"))
                cls.information_context = information._load_context()

    @contextmanager
    def checker_context(self):
        with no_producers(), ExitStack() as stack:
            for module, name, context in (
                    (baseline, "_context", self.baseline_context),
                    (preprocessing, "_load_inputs", self.preprocessing_context),
                    (information, "_load_context", self.information_context)):
                stack.enter_context(patch.object(module, name, return_value=context))
            yield

    def verify(self, module, report):
        with self.checker_context():
            if module is preprocessing:
                return module.verify_report(report, "unused", None)
            return module.verify_report(report)

    def cli(self, module, report):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "fixture.json.gz"
            path.write_bytes(gzip.compress(json.dumps(report).encode("utf-8"), mtime=0))
            output = io.StringIO()
            with self.checker_context(), \
                    patch("sys.argv", [module.__name__, "--verify", str(path)]), \
                    redirect_stdout(output):
                module.main()
            return json.loads(output.getvalue())

    def test_archived_reports_expose_frozen_producer_in_library_and_cli(self):
        for module in MODULES:
            with self.subTest(schema=module.SCHEMA):
                summary = self.verify(module, self.reports[module.SCHEMA])
                self.assertEqual(summary["source_version"], "frozen-2026-10-study")
                self.assertEqual(self.cli(module, self.reports[module.SCHEMA]), summary)

    def test_current_manifest_fixtures_expose_current_with_archived_controls(self):
        for module in MODULES:
            with self.subTest(schema=module.SCHEMA):
                report = copy.deepcopy(self.reports[module.SCHEMA])
                report["source_sha256"] = current_sources(module)
                summary = self.verify(module, report)
                self.assertEqual(summary["source_version"], "current")
                self.assertEqual(self.cli(module, report), summary)
                previous = dict(self.verify(module, self.reports[module.SCHEMA]))
                previous.pop("source_version")
                self.assertEqual({key: value for key, value in summary.items()
                                  if key != "source_version"}, previous)

    def test_source_label_never_bypasses_provenance_or_mathematical_checks(self):
        for module in MODULES:
            for version in ("frozen", "current"):
                report = copy.deepcopy(self.reports[module.SCHEMA])
                if version == "current":
                    report["source_sha256"] = current_sources(module)
                mutations = (
                    lambda r: r["source_sha256"].update({"bf_solver.py": "0" * 64}),
                    lambda r: r["source_sha256"].pop("fs_controls.py"),
                    lambda r: r["source_sha256"].update({"unexpected.py": "0" * 64}),
                    lambda r: r["protocol"].update(max_calls=999),
                    lambda r: r["inputs"].update(
                        {next(iter(r["inputs"])): "incorrect input provenance"}),
                    lambda r: r["cases"][0]["result"].update(indices=[0, 0, 0]),
                    lambda r: r.update(counterexamples=1),
                )
                for index, mutate in enumerate(mutations):
                    with self.subTest(schema=module.SCHEMA, version=version, mutation=index):
                        changed = copy.deepcopy(report)
                        mutate(changed)
                        with self.assertRaises(ValueError):
                            self.verify(module, changed)

    def test_diagnostics_do_not_mutate_saved_reports_or_input_metadata(self):
        for module in MODULES:
            report = copy.deepcopy(self.reports[module.SCHEMA])
            before = copy.deepcopy(report)
            self.verify(module, report)
            self.cli(module, report)
            self.assertEqual(report, before)
            self.assertNotIn("source_version", report)
            self.assertNotIn("source_version", report["inputs"])
        for filename, expected_hash in ARTIFACTS:
            self.assertEqual(hashlib.sha256(
                baseline.DEFAULT_INPUT.with_name(filename).read_bytes()).hexdigest(), expected_hash)


if __name__ == "__main__":
    unittest.main()
