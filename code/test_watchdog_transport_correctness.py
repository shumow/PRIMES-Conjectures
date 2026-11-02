"""Synthetic watchdog regressions; no solver or full-pool experiment."""
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from unittest.mock import patch
import json
import multiprocessing
import os
import pickle
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import warnings

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fs_controls


class _Tag(Enum):
    VALUE = "value"


@dataclass
class _Record:
    value: int
    tag: _Tag


def _echo(payload):
    return payload


def _raise(payload):
    raise ValueError(payload)


def _unpickleable(payload):
    return lambda: payload


def _crash(payload):
    os._exit(payload)


def _sleep(payload):
    time.sleep(payload)
    return "late"


def _raw_worker(fn, payload, result_path):
    Path(result_path).write_bytes(payload)


def _missing_worker(fn, payload, result_path):
    return


def _publish_then_linger(fn, payload, result_path):
    fs_controls._write_worker_result(Path(result_path), "ok", "premature")
    time.sleep(30)


def _unwritable_result_worker(fn, payload, result_path):
    Path(result_path).mkdir()
    fs_controls._worker_entry(fn, payload, result_path)


def _return_large(payload):
    size, marker = payload
    parent = multiprocessing.parent_process()
    if parent is not None:
        def exit_with_parent():
            parent.join()
            os._exit(98)
        threading.Thread(target=exit_with_parent, daemon=True).start()
    value = b"\xa5" * size
    Path(marker).write_text(str(os.getpid()), encoding="ascii")
    return value


def _large_scenario(folder):
    marker = folder / "callback-completed"
    size = 4 * 1024**2
    kind, value, elapsed = fs_controls.run_limited(
        _return_large, (size, str(marker)), 30.0)
    summary = {"kind": kind, "callback_completed": marker.exists(),
               "exact_type": type(value) is bytes,
               "exact_value": type(value) is bytes and value == b"\xa5" * size,
               "length": len(value) if type(value) is bytes else None,
               "elapsed": elapsed}
    (folder / "summary.json").write_text(json.dumps(summary), encoding="utf-8")


class LargeResultTransport(unittest.TestCase):
    def test_completed_large_return_is_delivered_not_timed_out(self):
        with tempfile.TemporaryDirectory(prefix="watchdog-regression-") as directory:
            folder = Path(directory)
            result = subprocess.run(
                [sys.executable, "-B", str(Path(__file__).resolve()),
                 "--large-scenario", str(folder)],
                capture_output=True, text=True, timeout=60,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
        self.assertTrue(summary["callback_completed"], summary)
        self.assertEqual(summary["kind"], "ok", summary)
        self.assertTrue(summary["exact_type"], summary)
        self.assertTrue(summary["exact_value"], summary)
        self.assertEqual(summary["length"], 4 * 1024**2)
        self.assertLess(summary["elapsed"], 30.0)


class WatchdogLifecycle(unittest.TestCase):
    def tracked_call(self, fn, payload, seconds=30.0):
        context = multiprocessing.get_context("spawn")
        real_temporary = tempfile.TemporaryDirectory
        processes, folders = [], []

        def make_process(*args, **kwargs):
            process = context.Process(*args, **kwargs)
            processes.append(process)
            return process

        def make_folder(*args, **kwargs):
            folder = real_temporary(*args, **kwargs)
            folders.append(Path(folder.name))
            return folder

        tracked = SimpleNamespace(Process=make_process)
        try:
            with patch.object(fs_controls, "multiprocessing",
                              SimpleNamespace(get_context=lambda method: tracked)), \
                    patch.object(fs_controls.tempfile, "TemporaryDirectory", side_effect=make_folder):
                return fs_controls.run_limited(fn, payload, seconds)
        finally:
            for process in processes:
                with self.assertRaises(ValueError):
                    process.is_alive()
            for folder in folders:
                self.assertFalse(folder.exists(), folder)

    def test_small_none_and_certificate_shaped_values(self):
        for payload in (None, "small", (1, -2, 2**4000),
                        {"certificate": [_Record(2**3000, _Tag.VALUE), [None, -1]]}):
            with self.subTest(payload_type=type(payload)):
                kind, value, elapsed = self.tracked_call(_echo, payload)
                self.assertEqual(kind, "ok", value)
                self.assertEqual(type(value), type(payload))
                self.assertEqual(value, payload)
                self.assertGreaterEqual(elapsed, 0)
                self.assertLess(elapsed, 30)

    def test_worker_exception_and_large_error_message(self):
        for message in ("boom", "large-error:" + "x" * 1024**2):
            kind, value, _ = self.tracked_call(_raise, message)
            self.assertEqual(kind, "worker_error")
            self.assertEqual(value, "ValueError: " + message)

    def test_unpickleable_result_is_delivery_error_not_timeout(self):
        kind, value, _ = self.tracked_call(_unpickleable, None)
        self.assertEqual(kind, "worker_error")
        self.assertIn("result delivery failed:", value)

    def test_crash_and_missing_result_are_explicit_errors(self):
        kind, value, _ = self.tracked_call(_crash, 7)
        self.assertEqual(kind, "worker_error")
        self.assertIn("code 7", value)
        with patch.object(fs_controls, "_worker_entry", _missing_worker):
            kind, value, _ = self.tracked_call(_echo, None)
        self.assertEqual(kind, "worker_error")
        self.assertIn("no result returned", value)

    def test_corrupt_malformed_and_trailing_result_bytes(self):
        for payload in (b"", b"not pickle", pickle.dumps(("unexpected", 1)),
                        pickle.dumps(("worker_error", 5)), pickle.dumps(("ok", 1)) + b"extra"):
            with self.subTest(payload=payload):
                with patch.object(fs_controls, "_worker_entry", _raw_worker):
                    kind, value, _ = self.tracked_call(_echo, payload)
                self.assertEqual(kind, "worker_error")
                self.assertIn("watchdog delivery failed:", value)

    def test_timeout_and_published_but_unfinished_worker(self):
        kind, value, _ = self.tracked_call(_sleep, 30, seconds=1.0)
        self.assertEqual((kind, value), ("timeout", None))
        with patch.object(fs_controls, "_worker_entry", _publish_then_linger):
            kind, value, _ = self.tracked_call(_echo, None, seconds=1.0)
        self.assertEqual((kind, value), ("timeout", None))
        self.assertEqual(self.tracked_call(_echo, "after timeout")[0:2],
                         ("ok", "after timeout"))

    def test_zero_and_invalid_budgets_start_no_worker(self):
        with patch.object(fs_controls.multiprocessing, "get_context",
                          side_effect=AssertionError("no worker")):
            self.assertEqual(fs_controls.run_limited(_echo, None, 0)[:2], ("timeout", None))
            for invalid in (-1, float("nan"), float("inf"), 10**5000, True, "1", None):
                with self.assertRaises(ValueError):
                    fs_controls.run_limited(_echo, None, invalid)

    def test_parent_read_finishing_after_deadline_is_not_success(self):
        real_clock, real_load = time.monotonic, pickle.load
        offset = 0.0

        def delayed_load(stream):
            nonlocal offset
            value = real_load(stream)
            offset = 31.0
            return value

        with patch.object(fs_controls, "time",
                          SimpleNamespace(monotonic=lambda: real_clock() + offset)), \
                patch.object(fs_controls.pickle, "load", side_effect=delayed_load):
            kind, value, elapsed = self.tracked_call(_echo, "late decode")
        self.assertEqual((kind, value), ("timeout", None))
        self.assertGreaterEqual(elapsed, 31)

    def test_startup_error_is_classified_and_cleaned(self):
        with patch.object(multiprocessing.context.SpawnProcess, "start",
                          side_effect=OSError("cannot start")):
            kind, value, _ = self.tracked_call(_echo, None)
        self.assertEqual(kind, "worker_error")
        self.assertIn("cannot start", value)

    def test_interruption_reaps_worker_and_propagates(self):
        original_join = multiprocessing.context.SpawnProcess.join
        interrupted = False

        def interrupt_once(process, timeout=None):
            nonlocal interrupted
            if not interrupted:
                interrupted = True
                raise KeyboardInterrupt
            return original_join(process, timeout)

        with patch.object(multiprocessing.context.SpawnProcess, "join", interrupt_once), \
                self.assertRaises(KeyboardInterrupt):
            self.tracked_call(_sleep, 30)

    def test_cleanup_error_is_visible_not_success(self):
        real_cleanup = tempfile.TemporaryDirectory.cleanup

        def failed_cleanup(folder):
            real_cleanup(folder)
            raise OSError("cleanup denied")

        with patch.object(tempfile.TemporaryDirectory, "cleanup", failed_cleanup):
            kind, value, _ = fs_controls.run_limited(_echo, "completed", 30.0)
        self.assertEqual(kind, "worker_error")
        self.assertIn("cleanup denied", value)

    def test_file_setup_read_and_worker_write_errors_are_not_timeouts(self):
        with patch.object(fs_controls.tempfile, "TemporaryDirectory",
                          side_effect=OSError("cannot create handoff")):
            kind, value, _ = fs_controls.run_limited(_echo, None, 30)
        self.assertEqual(kind, "worker_error")
        self.assertIn("cannot create handoff", value)
        with patch.object(fs_controls.pickle, "load", side_effect=OSError("cannot read handoff")):
            kind, value, _ = self.tracked_call(_echo, None)
        self.assertEqual(kind, "worker_error")
        self.assertIn("cannot read handoff", value)
        with patch.object(fs_controls, "_worker_entry", _unwritable_result_worker):
            kind, value, _ = self.tracked_call(_echo, None)
        self.assertEqual(kind, "worker_error")
        self.assertIn("code 1", value)

    def test_cleanup_warning_does_not_replace_interruption(self):
        original_join = multiprocessing.context.SpawnProcess.join
        real_cleanup = tempfile.TemporaryDirectory.cleanup
        interrupted = False

        def interrupt_once(process, timeout=None):
            nonlocal interrupted
            if not interrupted:
                interrupted = True
                raise KeyboardInterrupt
            return original_join(process, timeout)

        def failed_cleanup(folder):
            real_cleanup(folder)
            raise OSError("cleanup after interrupt")

        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("error", RuntimeWarning)
            with patch.object(multiprocessing.context.SpawnProcess, "join", interrupt_once), \
                    patch.object(tempfile.TemporaryDirectory, "cleanup", failed_cleanup), \
                    self.assertRaises(KeyboardInterrupt):
                self.tracked_call(_sleep, 30)
        self.assertTrue(any("cleanup after interrupt" in str(item.message) for item in caught))

    def test_kill_fallback_is_bounded_and_failure_is_explicit(self):
        class FakeProcess:
            pid = 123
            exitcode = None

            def __init__(self, stuck):
                self.stuck, self.alive, self.closed, self.killed = stuck, True, False, False
                self.waits = []

            def start(self):
                pass

            def join(self, seconds):
                self.waits.append(seconds)

            def is_alive(self):
                return self.alive

            def terminate(self):
                pass

            def kill(self):
                self.killed = True
                self.alive = self.stuck

            def close(self):
                self.closed = True

        for stuck in (False, True):
            process = FakeProcess(stuck)
            with patch.object(fs_controls, "multiprocessing", SimpleNamespace(
                    get_context=lambda method: SimpleNamespace(Process=lambda **kwargs: process))):
                kind, value, _ = fs_controls.run_limited(_echo, None, 30)
            self.assertTrue(process.killed)
            self.assertTrue(all(wait is not None and 0 <= wait <= 30 for wait in process.waits))
            self.assertEqual(process.closed, not stuck)
            if stuck:
                self.assertEqual(kind, "worker_error")
                self.assertIn("could not reap owned worker", value)
            else:
                self.assertEqual((kind, value), ("timeout", None))


if __name__ == "__main__":
    if sys.argv[1:2] == ["--large-scenario"]:
        _large_scenario(Path(sys.argv[2]))
    else:
        unittest.main()
