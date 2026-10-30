"""Strict frozen producer-source manifests, not substitutes for live digests."""
from typing import Mapping

FROZEN_BASELINE = "e6b756c20365ea40245aaa6734f9f3044ac791ed"
SOURCE_FILE = "watchdog_source_versions.py"
_FROZEN = {
    "real_pool_pilot.py": "2dc22aeba577ebea02bf955d4f9ab4db7eeb2f80307b887ef4b067c3b33eb467",
    "real_pool_verify.py": "429b06f7dafb50e3134b91f5e22474fb23702e2acde1f7e8dcba99a709e5ccc8",
    "a4_solver.py": "5797a71c8996937381adaa03e77fe5c9062b348d1b1704a338a48f1f7e1406ba",
    "a6_oddsolver.py": "80479e5cc06f30e2e1dde3c536bad5006fac8beaec754c6010fed1ca3f85bd54",
    "a7_lohniebuhr.py": "b5c402983acfb3ed716085931ae943c20d9ef1260c16bd9e0b51227384ed9dcb",
    "phase1a_calibration.py": "b33a0d66ac4941f37bdedeb52a719feb0e13772e22d2ec9e4fb79f316a947113",
    "fs_controls.py": "8a5d440a03ce9a37693288dccdd3213240b77633c5b1d6bfd26dd7707515cf4d",
    "bf_solver.py": "625211269dc6320b1c999045a471a0d257fcc8fb4279a345d848e69c1761451f",
    "bf_solver_preprocessing.py": "868879bcd1993a85aa187986430dce3cff56efe46fd4324c91b711ff09b0d9e6",
    "bf_solver_information_sets.py": "934e295350c979c32874a21e8f5f222ceccb0357c240887db919e759d4c412ef",
}
_COUNTS = {
    "fs-controls/v1.1": 7,
    "bf-solver/v1": 8,
    "bf-solver-preprocessing/v1": 9,
    "bf-solver-information-sets/v1": 10,
}


def verify_source_manifest(schema: str, recorded: object,
                           current: Mapping[str, str]) -> str:
    """Recognize a complete current or frozen producer version for this schema.

    A frozen match does not assert that the current filesystem is unchanged,
    authenticate historical execution, or validate any mathematical claim.
    """
    if schema not in _COUNTS:
        raise ValueError("unsupported source-manifest schema")
    names = tuple(_FROZEN)[:_COUNTS[schema]]
    frozen = {name: _FROZEN[name] for name in names}
    expected_current = set(names)
    if schema != "fs-controls/v1.1":
        expected_current.add(SOURCE_FILE)
    if set(current) != expected_current or any(
            not isinstance(value, str) or len(value) != 64
            or any(c not in "0123456789abcdef" for c in value) for value in current.values()):
        raise ValueError("invalid current source-manifest definition")
    if not isinstance(recorded, dict) or any(
            not isinstance(name, str) or not isinstance(value, str)
            for name, value in recorded.items()):
        raise ValueError("invalid recorded source manifest")
    if recorded == current:
        return "current"
    if recorded == frozen:
        return "frozen-2026-10-study"
    raise ValueError("source manifest is neither the complete current nor frozen producer version")
