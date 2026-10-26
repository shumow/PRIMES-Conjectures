# S1 next step: support-blind information-set search

**Branch:** `research/boolean-solver-calibration`

**Starting combined S1/study commit:** `6c954e9c5da7d8b71ba1d5eaea60522d0775fbf8`

**Status:** runner/checker preparation and protocol freeze only, as explicitly
requested by the user. No full-pool control outcome has been inspected for
this configuration, and no information-set pilot-result artifact exists.

S2 and S3's reviewed revisions are now on the study integration branch and
have been merged into S1 without altering either earlier S1 source-hashed
implementation or artifact. This versioned module avoids invalidating those
reports. No new optional backend or dependency is introduced.

## Algorithm and scope

The public worker receives a problem with `exact_size=None`. The support,
planting indices, seed labels and prime records stay in the parent. The
algorithm has its own fixed selection envelope: **odd size at least the
minimum and at most 17**. This is not a claim of complete general solving.

For each of at most eight information sets:

1. Permute the Boolean columns (identity first, then seven fixed-seed
   shuffles independent of the planting streams).
2. Apply the audited GF(2) solver to the parity projection of every original
   even-order component, together with odd cardinality.
3. Enumerate the particular solution XOR combinations of at most three
   free-coordinate kernel basis masks.
4. Use the exact resulting selection mask to enforce the size envelope,
   map back to original prime indices, and check **every original modular
   equation**. Independently check returned subsets and prime residues.

The XOR operations update the selection vector exactly. They do **not**
assume that full-group residuals are additive under overlapping moves.
Higher 2-power carries and odd-primary equations are never dropped from
candidate acceptance.

For the pilot's nullity 90, a full information set has
`1 + 90 + C(90,2) + C(90,3) = 121,576` states. Eight sets have at most
972,608 states. A sparse planted selection may occupy few free coordinates
in one set; that motivates the method, but is not a recovery guarantee.

## Predeclared candidate pilot

One configuration: one worker; 60 seconds per call including startup,
projection, elimination, enumeration and checking; 512 MiB completed-worker
memory target (not an OS cap); eight information sets; free-coordinate
weight at most three; one million states; at most 10,000 full-target
candidate checks; fixed solver seed 1729.

The prototype declares an **18-call maximum**, with gates:

| Phase | Parent-known controls (not worker hints) | Calls |
|---|---|---:|
| 0 | Support 3, development 101/202/303 | 3 |
| 1 | Support 5, development 101/202/303 and fresh holdouts 32452843/49979687/67867967 | 6 |
| 2 | Support 9, development 101/202/303 | 3 |
| 3 | Support 17, development 101/202/303 and fresh holdouts 86028121/104395301/122949829 | 6 |

All cases of each prior phase must solve before a later phase runs.
The six holdout seeds differ from all previously evaluated holdouts.
Development controls reuse frozen first-wave targets; holdouts use the
existing `bf-solver-holdout/20261024/<seed>` namespace with these new seeds.
No witness is supplied as a hint or warm start.

The aggregate solver-call ceiling is 1,080 seconds, not a larger per-call
budget. No real target, larger pool, harvest, parameter sweep or adaptive
retry is authorized by this prototype. Failure is inconclusive outside the
explored affine masks and selection envelope.

The declared protocol SHA256 remains unchanged:
`a2ba7c982dc1ea5294a18169cc8a382f41d079163f881ab3fb27cb91f65765b7`.
The containing freeze commit records the runner, independent checker,
tests and this declaration before any full-pool outcome. A future pilot
requires an explicit execution instruction; the declaration is not a claim
that the pilot has run.

## Runner and independent report contract

The runner has one fixed case list and no runtime target, support, seed or
budget overrides. Each worker receives only the problem with
`exact_size=None`, the fixed limits and its absolute deadline. All control
metadata and prime records remain in the parent. Development cases reproduce
the frozen first-wave controls; the six new holdouts follow the labels above.

The report schema is `bf-solver-information-sets/v1`. It records:

- The frozen implementation commit, unchanged protocol/hash, LF-normalized
  source hashes, interpreter/platform and timestamp.
- Hashes of the frozen pilot, first-wave control dataset and both preceding
  S1 reports. Inputs are checked against those immutable preceding records.
- The exact 483-prime scope, original parent LCMs and every declared case,
  including all cases not run because a gate failed.
- Separate outcome, elapsed/component times, counters, memory observation,
  returned subset size, witness comparison and independent residue-check cost.

Every prior phase must pass completely before a later one can run.
Timeouts/resource stops are inconclusive. A worker error or a projection
diagnosis contradicting a verified planted target aborts all remaining
calls, preserves the explicit error and unrun records, and produces a
nonzero CLI exit rather than a success-shaped fallback.

The independent checker reconstructs the expected input/target definitions,
recomputes gates and abort policy, checks output shapes and limits, and
re-verifies candidate cardinality, every original group equation and the
original prime-product residues. It does **not** invoke the solver, worker,
affine-mask enumerator or GF(2) producer. A valid recovered subset need not
equal the planting witness or have the parent's hidden planting size.

Checks include complete case coverage, exact protocol/source/input sets,
strict numeric types, counter caps, finite/nonnegative timings, component
timing consistency, late/over-target success rejection, and correct
verification annotations. Missing RSS measurements are counted explicitly,
not converted into fabricated memory guarantees. Timings and execution
authenticity are observations, not mathematical certificates.

### Output and execution safeguards

- Running requires `--run-pilot` explicitly and committed matching solver
  sources. The implementation/source snapshot is rechecked after the batch.
- Existing or protected output names fail before computation. Exclusive
  output reservation prevents concurrent runs from clobbering each other.
- There is no `--replace` shortcut or automatic retry/resume. An interruption
  leaves the reservation visible for investigation, not permission to rerun.
- No report is published until direct verification succeeds. Explicit error
  reports can be saved for diagnosis but return a nonzero exit.

All per-call successes must fit the 60-second deadline. The 1,080-second
aggregate is the sum of at most 18 declared call deadlines; OS scheduling,
watchdog teardown and independent input/report checking may add observed
elapsed overhead. Overruns never count as successful calls.

## Prototype validation

- All **18 focused tests** pass on Python 3.14.5 and 3.9.13 (0.977 and
  1.191 seconds).
- The combined **233-test suite** passes on both runtimes, including the
  integrated S2/S3 regressions and the prior optional-backend tests.
- Independent tests compare 300 small binary affine families and 1,184
  small subset decisions with exhaustive enumeration. Additional structured
  fixtures recover different synthetic supports without supplying their
  cardinality to the worker.
- Tests cover exact overlapping XOR masks, retained odd/higher-power
  equations, state/selection/deadline limitations, fresh-holdout separation,
  worker payload isolation, explicit errors and an actual tiny spawned run.
- Every earlier S1 source-hashed implementation and artifact is unchanged.
  No full-483 control, real-target search, membership run or harvest was
  executed while developing this prototype.

## Freeze-only runner/checker validation

- All **37 information-set tests** pass on Python 3.14.5 and 3.9.13
  (2.378 and 2.775 seconds).
- The combined **252-test suite** passes on both runtimes (94.495 and
  124.603 seconds), including the legacy optional-backend tests.
- Runner tests use a small validated-input-boundary projection and simulated
  outcomes. They cover all phases, alternate valid returned cardinalities,
  failed gates, immediate error/contradiction aborts, complete unrun records,
  report round-trips and source/head changes during a run.
- The checker succeeds with search, worker, affine enumeration and GF(2)
  generation patched to raise. Tamper tests reject changed provenance,
  inputs, targets, support-hint modes, missing cases, false verification
  annotations, bad counters/timings, over-budget candidates and false gates.
- CLI regressions verify explicit modes, no default execution, no `--replace`,
  exclusive output reservation, no-clobber races and nonzero error exits.
- The 18 declared planting recipes produce the same index-definition checksum
  on Python 3.14.5 and 3.9.13:
  `f0bc07e8b891d0ecafabcbeccf97cc2be2dfd82ca693672820a5cdd23b637642`.
  This hashes the sorted-key JSON list of case names and sorted sampled
  indices. The check used only seeded index definitions, not matrices,
  targets, recovery outcomes or solver calls.
- Editor-side diagnostics were unavailable in this session; validation used
  the explicit runtimes and independent test oracles above.

**This is not pilot evidence.** No actual 483-prime information-set control
was evaluated, none of the six full-pool holdout outcomes was inspected, and
`data/generated/bf_solver_information_sets.json.gz` remains absent. The user
explicitly requested stopping at the committed freeze checkpoint.

Print the declared candidate protocol without running a study:

```powershell
python -B code\bf_solver_information_sets.py --protocol
python -B -m unittest discover -s code -p "test_bf_solver_information_sets_correctness.py" -v
```

The CLI deliberately refuses a default production invocation. For a report
from a **future separately instructed run**, verification is read-only:

```powershell
python -B code\bf_solver_information_sets.py --verify data\generated\bf_solver_information_sets.json.gz
```

Only after that execution instruction, and with the frozen source checked
out, would the explicit run command be:

```powershell
python -B code\bf_solver_information_sets.py --run-pilot
```

Use `--git` if Git is not on PATH, or a new prefixed `--output` for an
explicitly authorized replication. Neither command was used to evaluate
full-pool controls during this freeze-only task.
