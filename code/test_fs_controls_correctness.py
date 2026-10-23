"""Bounded correctness tests for Track A (code/fs_controls.py).

Run: python code/test_fs_controls_correctness.py
All tests are deterministic and complete in well under a minute; they use the
frozen pilot dataset read-only and small synthetic groups.
"""
from itertools import combinations
from pathlib import Path
import gzip
import json
import math
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))

import fs_controls
from real_pool_verify import instance_from_json, subset_residues, verify_group_solution

PILOT = Path(__file__).resolve().parent.parent / "data" / "generated" / "real_pool_pilot.json.gz"


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


def test_fixed_k_mitm_agrees_with_exhaustive_oracle():
    rng = random.Random(20261023)
    for trial in range(25):
        n = rng.randrange(5, 11)
        d = rng.randrange(2, 6)
        orders = [rng.choice([2, 3, 4, 5, 7, 9]) for _ in range(d)]
        pool = [[rng.randrange(o) for o in orders] for _ in range(n)]
        for k in (3, 5):
            if k > n:
                continue
            if trial % 2:                       # planted, guaranteed feasible
                witness = rng.sample(range(n), k)
                target = [sum(pool[i][j] for i in witness) % orders[j]
                          for j in range(d)]
            else:                               # arbitrary, often infeasible
                target = [rng.randrange(o) for o in orders]
            found, message, _ = fs_controls.fixed_k_mitm(
                orders, pool, target, k, work_cap=10**7, table_cap=1 << 16)
            expected = _brute_force_exact_k(orders, pool, target, k)
            assert (found is None) == (expected is None), (message, trial, k)
            if found is not None:
                assert len(found) == k and len(set(found)) == k
                assert all(sum(pool[i][j] for i in found) % orders[j] == target[j]
                           for j in range(d))


def test_fixed_k_mitm_rejects_even_or_tiny_cardinality():
    try:
        fs_controls.fixed_k_mitm([3], [[1]] * 4, [0], 2, work_cap=100, table_cap=16)
    except ValueError:
        pass
    else:
        raise AssertionError("even cardinality must be rejected")
    found, message, _ = fs_controls.fixed_k_mitm(
        [3], [[1]] * 2, [0], 3, work_cap=100, table_cap=16)
    assert found is None and message == "cardinality_infeasible"


def test_fixed_k_mitm_respects_declared_caps():
    orders = [5] * 4
    pool = [[1, 2, 3, 4] for _ in range(30)]
    found, message, counts = fs_controls.fixed_k_mitm(
        orders, pool, [0, 0, 0, 0], 5, work_cap=10, table_cap=1 << 16)
    assert found is None and message.startswith("resource_limit")
    assert counts == {"left": 0, "right": 0, "hash_matches": 0}


def test_planted_controls_verify_and_hide_witness():
    instance = _small_instance()
    record = fs_controls.experiment(instance, "small-complete-family",
                                    len(instance.records), 3, 101)
    assert record["target_kind"] == "planted_control"
    witness = record["planted_witness_indices"]
    assert len(witness) == 3 == len(set(witness))
    # the witness verifies independently against the original residues
    rows = instance.vectors
    target = tuple(sum(rows[i][j] for i in witness) % order
                   for j, order in enumerate(instance.orders))
    residues = subset_residues(instance.records, witness,
                               instance.lambda_minus, instance.lambda_plus)
    verify_group_solution(instance, witness, target, residues)
    # witness isolation: solver entries never embed the planting data
    for name, entry in record["solvers"].items():
        assert "planted_witness_indices" not in entry, name
        assert "planting_seed_label" not in entry, name
    # determinism of the planting stream
    repeat = fs_controls.experiment(instance, "small-complete-family",
                                    len(instance.records), 3, 101)
    assert repeat["planted_witness_indices"] == witness
    # every reported solution was independently verified
    for entry in record["solvers"].values():
        if entry.get("status") == "solution":
            assert entry.get("indices") is not None


def test_solution_statuses_come_from_declared_vocabulary():
    instance = _small_instance()
    record = fs_controls.experiment(instance, "small-complete-family",
                                    len(instance.records), None, None)
    allowed = {"solution", "proved_no_solution", "proved_no_solution_exact_cardinality",
               "resource_limit", "inconclusive_budget", "timeout_enforced"}
    for name, entry in record["solvers"].items():
        assert entry["status"] in allowed, (name, entry["status"])
    # the small cohort's real target carries a certified obstruction
    assert record["has_necessary_obstruction"] is True


def test_mod2_rank_matches_pilot_definition():
    instance = _small_instance()
    rank, nullity = fs_controls.mod2_rank_nullity(instance, len(instance.records))
    assert rank + nullity == len(instance.records)
    assert (rank, nullity) == (6, 0)            # pilot: rank 6, nullity 0


def test_run_limited_enforces_wall_clock():
    def spin():
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline:
            pass
        return "finished"

    value, timed_out, elapsed = fs_controls.run_limited(0.2, spin)
    assert timed_out and value is None and elapsed < 5


def main() -> None:
    tests = [value for name, value in sorted(globals().items())
             if name.startswith("test_")]
    for test in tests:
        start = time.monotonic()
        test()
        print(f"{test.__name__}: ok ({time.monotonic() - start:.1f}s)")
    print(f"{len(tests)} tests passed")


if __name__ == "__main__":
    main()
