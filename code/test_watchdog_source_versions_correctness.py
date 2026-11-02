"""Strict provenance compatibility without running archived experiments."""
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import copy
import gzip
import hashlib
import json
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))

import bf_solver as baseline
import bf_solver_information_sets as information
import bf_solver_preprocessing as preprocessing
from real_pool_verify import source_digest
from watchdog_source_versions import SOURCE_FILE, verify_source_manifest

DATA = Path(__file__).resolve().parent.parent / "data" / "generated"
REPORTS = (
    ("fs_controls.json.gz", "fs-controls/v1.1",
     "ad3c7cc4b909b174e8e19b279324d7e9856d3d0b232b913dff458f8fd8aa3b21"),
    ("bf_solver.json.gz", baseline.SCHEMA,
     "67b7dd568c925432546d8f43373cab4a8e638abe79fa3802873202243dd5b9a5"),
    ("bf_solver_preprocessing.json.gz", preprocessing.SCHEMA,
     "d100e499dfa7c6b3ae5b2cac7ff67e00ed46dea08e6078693cf0671fdfbb2e1a"),
    ("bf_solver_information_sets.json.gz", information.SCHEMA,
     "d62ac9ba58789262180a71589eb0c3ae9e7e42c0272e1e1a8f2dfbb5d8c149e7"),
)


def _current(schema):
    if schema == "fs-controls/v1.1":
        return {name: source_digest(Path(baseline.__file__).with_name(name))
                for name in baseline.BASELINE_SOURCES + ("fs_controls.py",)}
    return {baseline.SCHEMA: baseline._sources,
            preprocessing.SCHEMA: preprocessing.sources,
            information.SCHEMA: information.sources}[schema]()


class FrozenSourceVersions(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reports = {}
        for name, schema, digest in REPORTS:
            raw = (DATA / name).read_bytes()
            if hashlib.sha256(raw).hexdigest() != digest:
                raise AssertionError("frozen fixture bytes changed: " + name)
            cls.reports[schema] = json.loads(gzip.decompress(raw))

    def test_complete_frozen_manifests_are_recognized(self):
        for schema, report in self.reports.items():
            with self.subTest(schema=schema):
                self.assertEqual(verify_source_manifest(
                    schema, report["source_sha256"], _current(schema)),
                    "frozen-2026-10-study")

    def test_complete_current_manifests_use_actual_file_digests(self):
        for schema in self.reports:
            with self.subTest(schema=schema):
                current = _current(schema)
                self.assertEqual(verify_source_manifest(schema, current, current), "current")
                for name, digest in current.items():
                    self.assertEqual(digest, source_digest(Path(baseline.__file__).with_name(name)))
                if schema != "fs-controls/v1.1":
                    self.assertIn(SOURCE_FILE, current)

    def test_no_missing_extra_unknown_or_mixed_source_maps(self):
        for schema, report in self.reports.items():
            original = report["source_sha256"]
            corruptions = [None, [], {"fs_controls.py": False}]
            changed = dict(original)
            changed["fs_controls.py"] = "0" * 64
            corruptions.append(changed)
            changed = dict(original)
            changed.pop("fs_controls.py")
            corruptions.append(changed)
            changed = dict(original, unexpected="a" * 64)
            corruptions.append(changed)
            current = _current(schema)
            for name in original:
                if original[name] != current[name]:
                    changed = dict(original)
                    changed[name] = current[name]
                    if changed != current:
                        corruptions.append(changed)
            for changed in corruptions:
                with self.subTest(schema=schema, recorded=changed):
                    with self.assertRaises(ValueError):
                        verify_source_manifest(schema, changed, current)

    def test_schema_binding_and_current_definition_are_strict(self):
        for schema, report in self.reports.items():
            for other_schema in self.reports:
                if schema != other_schema:
                    with self.assertRaises(ValueError):
                        verify_source_manifest(other_schema, report["source_sha256"],
                                               _current(other_schema))
            with self.assertRaises(ValueError):
                verify_source_manifest(schema, report["source_sha256"], {})
        with self.assertRaises(ValueError):
            verify_source_manifest("unknown/v1", {}, {})

    def test_control_input_checks_the_whole_historical_manifest(self):
        original = self.reports["fs-controls/v1.1"]
        for field in ("unknown_hash", "extra_source", "normalization"):
            altered = copy.deepcopy(original)
            if field == "unknown_hash":
                altered["source_sha256"]["fs_controls.py"] = "f" * 64
            elif field == "extra_source":
                altered["source_sha256"]["injected.py"] = "f" * 64
            else:
                altered["source_hash_normalization"] = "unrecognized"
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory) / "controls.json.gz"
                path.write_bytes(gzip.compress(json.dumps(altered).encode()))
                with patch.object(baseline, "load_pilot", return_value=(
                        {"medium-complete-family": SimpleNamespace(records=range(483))},
                        {}, "008cf08ce3f0d3a2f987bff26d5abd04bf4c41050f949ae0fdc4f4192b6969de")), \
                        self.assertRaises(ValueError):
                    baseline._context(baseline.DEFAULT_INPUT, path)


if __name__ == "__main__":
    unittest.main()
