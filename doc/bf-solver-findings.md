# S1: exact Boolean model and bounded control calibration

**Branch:** `research/boolean-solver-calibration`

**Starting integration commit:** `0c9f03fb1e00dfd85cb9e2b37e15ed1e727c4915`

**Plan:** [current S1 assignment](../PLAN.md#3-s1-exact-boolean-formulation-and-calibrated-solving)

**Status:** first frozen round complete. The exact model passes small-oracle
checks, but this configuration recovered **0 of 3 support-3 controls**.
The first gate failed, so the other 15 calls were not run. This is a negative
engineering result, not evidence that any of these known-feasible targets
is impossible.

**Frozen implementation/protocol commit:** `136b00ac0b98ad6599f14c223525c4d160692341`.
The protocol below was committed before the first full-pool call. No backend
parameters or solver source were changed in response to the outcomes.

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

### Correctness and compatibility

- The original 116 tests plus 24 initial S1 tests passed as a **140-test
  combined suite** on Python **3.14.5** and **3.9.13** before calibration
  (22.637 and 30.699 seconds, respectively).
- The model was compared with independent exhaustive Boolean enumeration
  on **320 seeded tiny-system decisions per runtime**, plus direct
  carry-bound, heterogeneous-power, parity/cardinality, trivial-group,
  invalid-input and overflow-guard fixtures.
- Spawned-worker tests cover actual native recovery and classified timeout/
  worker-error paths. Late and over-memory-target results cannot count as
  successes. The native backend was tested on both Python versions.
- After saving the artifact, two report regressions were added. All **26 S1
  tests** pass on Python 3.9.13 with the backend. The same focused suite
  passes on the unmodified, standard-library-only Python 3.14.5 installation,
  with the three optional native tests explicitly skipped.
- Saved-report checking passes with the solver, backend/version lookup and
  carry builder patched to raise. Eight tamper cases reject altered
  provenance, targets, skipped-case gating, negative claims and invalid
  candidate payloads. The standalone checker also works without OR-Tools.

The embedded Python 3.9 runtime omits normal script directories from its
isolated import path. Local validation used an explicit-path launcher, not
an edit to the runtime or repository. Initial test-fixture failures from
spawning out of stdin and timing the first cold library import were corrected
in the test setup; the production 60-second budget was not increased.

### First full-pool round

| Development control | Backend status | Recorded outcome | End-to-end call seconds | Worker peak RSS (MiB) |
|---|---|---|---:|---:|
| Support 3, seed 101 | UNKNOWN | `inconclusive_budget` | 57.390 | 152.133 |
| Support 3, seed 202 | UNKNOWN | `timeout_enforced` | 60.354 | 256.559 |
| Support 3, seed 303 | UNKNOWN | `timeout_enforced` | 60.227 | 256.023 |

Input validation and case preparation took **22.560 seconds**, separately
from the timed solver calls. The artifact also records backend-import,
model-build, solve and verification costs separately. RSS is Windows
`PeakWorkingSetSize` of the solver worker, not aggregate parent-plus-child
or whole-machine peak memory. The small timeout overruns are reported
honestly; they are not successful calls granted extra solve budget.

There were exactly **three** full-pool calls, **zero solutions**, and
**15 explicitly gated, unrun cases**. Neither support-5 development nor
holdout recovery was attempted, and neither support-9/17 nor general-odd
recovery was tested. No real-target search, harvest, retry, parameter tuning
or budget escalation occurred.

All three original controls have independently verified planting witnesses.
Their `UNKNOWN`/timeout outcomes therefore diagnose this implementation's
bounded recovery performance, not feasibility. The first-wave methods
already recover these support-3 targets; the present carry formulation
demonstrates **no recovery improvement**. Timings from different machines,
interpreters and methods are not a controlled speed comparison.

### Preserved artifact and reproduction

- [S1 report](../data/generated/bf_solver.json.gz), schema `bf-solver/v1`,
  **26,294 bytes**.
- Artifact SHA256:
  `67b7dd568c925432546d8f43373cab4a8e638abe79fa3802873202243dd5b9a5`.
- Protocol SHA256:
  `12b2353f65ef241860c45998f88510729f702054d848c597e991b56a0e2746be`.
- Eight normalized source hashes, the dependency manifest hash, both frozen
  input hashes, implementation commit, dependency versions, targets,
  witnesses, scope, limits, costs and all unrun cases are recorded.
- The frozen pilot and first-wave artifacts, shared implementations,
  integration branch and main are unchanged.

From the repository root, verification does not rerun the experiment and
does not require the optional dependency:

```powershell
python -B code\bf_solver.py --verify data\generated\bf_solver.json.gz
python -B -m unittest discover -s code -p "test_bf_solver_correctness.py" -v
python -B code\bf_solver.py --protocol
```

For native model tests, create an isolated Python 3.9+ environment and install
the optional manifest; do not modify a global environment:

```powershell
python -m venv C:\path\to\s1-env
C:\path\to\s1-env\Scripts\python.exe -m pip install -r requirements-bf-solver.txt
C:\path\to\s1-env\Scripts\python.exe -B -m unittest discover -s code -p "test_bf_solver_correctness.py" -v
```

Do not rerun calibration merely to verify this report. A new pilot needs a
new declared round and output; the CLI requires committed solver sources,
uses exclusive output creation by default, and protects all frozen inputs.
Report verification checks mathematical witnesses and protocol consistency,
not the authenticity of historical timings or backend execution.

## Recommendation and stop

**Stop this round at the failed support-3 gate.** The model is an exact
correctness baseline, not a competitive recovery algorithm on this pool.
A next round should examine arithmetic/GF(2) preprocessing and how to
preserve the full modular constraints while reducing the backend's work.
Any kernel-coordinate formulation must still handle overlapping XOR moves
exactly; no additive-residual shortcut is justified.

That is a proposal for a newly frozen configuration, not a claim that such
preprocessing will work. Do not increase the budget, switch through multiple
backends, reuse holdouts for tuning, or infer that CP-SAT or Boolean solving
in general is incapable from this one round.

## Post-run integration test maintenance (2026-10-26)

The final combined regression run exposed a timing-sensitive native
round-trip smoke test: its separate ten-second limit included cold Windows
process/backend startup and expired after 10.052 seconds. The unchanged
test passed in isolation. Its three-variable, two-row functional fixture
is not a full-pool control or a ten-second performance benchmark.

The smoke test now uses the adapter's existing default limits (60 seconds,
512 MiB worker memory target) and still checks completion before its
deadline, the exact returned subset, model/solve measurements and observed
RSS. The separate zero-budget, deadline, late-result and timeout tests are
unchanged. This changes only test scheduling tolerance, not the solver's
runtime, production limits or recorded protocol.

All frozen reports, inputs, runtime source hashes and historical outcomes
above remain unchanged. No additional full-pool calibration call, retry or
experiment is part of this maintenance.
