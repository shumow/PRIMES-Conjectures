# S1: exact Boolean model and bounded control calibration

**Branch:** `research/boolean-solver-calibration`

**Starting integration commit:** `0c9f03fb1e00dfd85cb9e2b37e15ed1e727c4915`

**Plan:** [current S1 assignment](../PLAN.md#3-s1-exact-boolean-formulation-and-calibrated-solving)

**Status:** implementation and model validation in progress. The protocol
below is fixed before the first full-pool backend call; no calibration
outcome is claimed yet.

## Model and dependency decision

One Boolean variable per distinct retained prime; integer carry variables
enforce each original modular equation:

```text
sum_i (v[i,j] mod m[j]) * x[i] = (target[j] mod m[j]) + m[j] * z[j]
sum_i x[i] = 2*h + 1, h >= 1
```

The model retains the parent LCMs and all prime powers. Exact-k controls add
`sum(x) = k`; general-odd controls do not reveal k to the solver.
Carry bounds follow from the exact coefficient sum. The independent checker
uses the original modular sums and multiplicative residues, not those carries
or the backend's success flag.

The single optional backend is **OR-Tools CP-SAT 9.15.6755**, Apache-2.0,
Python >=3.9. PyPI provides Windows amd64 wheels for both CPython 3.9 and
3.14. It is isolated from the standard-library baseline; see
[requirements-bf-solver.txt](../requirements-bf-solver.txt).
The coordinator approves this narrowly scoped dependency for S1, not a change
to the baseline runtime floor. No global Python environment is modified.

The model has a conservative signed-64-bit activity guard and a one-million
matrix-entry guard. Exceeding them is a resource stop, not infeasibility.
Successful backend results still require independent Boolean/modular checks.
Backend `INFEASIBLE` is reported separately from a checked proof; the only
direct no-solution certificates implemented here are impossible cardinality
and a normalized row target exceeding its entire coefficient sum.

## Frozen initial protocol

All cases use the full **483-prime medium-complete instance**, original
component ordering, and unchanged parent LCMs from
[the frozen pilot](../data/generated/real_pool_pilot.json.gz).
Pilot SHA256:
`008cf08ce3f0d3a2f987bff26d5abd04bf4c41050f949ae0fdc4f4192b6969de`.
Development targets reproduce the first-wave control planting labels; their
source artifact is also hashed.

One configuration: one search worker, solver seed **1729**, **60 seconds**
per call including worker startup/model construction, **512 MiB memory
target**, and no more than **18 full-pool calls**. Memory observations and
any backend advisory limit must not be described as an OS-enforced RSS cap.
No backend parameter tuning, budget increases, witness hints, real-target
search, or harvest is part of this round.

The existing portable spawn watchdog is reused unchanged. The worker receives
an absolute deadline, deducts import/model time from its native solve budget,
and late results cannot count as successful calls. Watchdog termination/reaping
and OS scheduling can make a reported timeout's elapsed time exceed the
deadline; that overhead is recorded rather than hidden. A completed worker
reports OS peak RSS, and a result above the memory target is not counted as a
success. Neither the backend advisory setting nor post-run measurement is an
OS-enforced memory cap; timed-out workers may have no returned RSS measurement.

| Order | Cases | Mode | Gate |
|---|---|---|---|
| 1-3 | Support 3, development seeds 101/202/303 | Exact-k | All three must solve before proceeding |
| 4-6 | Support 5, development seeds 101/202/303 | Exact-k | Combined support-5 gate below |
| 7-9 | Support 5, holdout seeds 104729/130363/155921 | Exact-k | All six support-5 cases must solve |
| 10-12 | Support 9, development seeds 101/202/303 | Exact-k | Only after the support-5 gate |
| 13-15 | Support 17, development seeds 101/202/303 | Exact-k | Only after the support-5 gate |
| 16-18 | The three support-5 holdout targets | General odd, minimum 3 | Only after the support-5 gate; separate task |

Holdout planting labels are `bf-solver-holdout/20261024/<seed>`. Only group
vectors, target, declared cardinality mode, limits and the independent solver
seed reach the worker. Planting labels/indices and actual primes remain in
the parent for verification. The holdout targets are fixed before outcomes
are inspected; no tuning on them is allowed.

Stopped or gated cases remain in the report as explicitly not run. An
infeasible backend status on a verified planted target is a contradiction
requiring investigation, not a mathematical negative result. Exhaustion and
timeouts are inconclusive. Passing the small control gate would not show
that the real fixed-LCM target, which requires at least 93 factors, is near.

## Validation and outcomes

Pending implementation, tiny-oracle validation and the bounded run.
