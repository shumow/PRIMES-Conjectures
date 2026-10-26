# S1 next step: support-blind information-set search

**Branch:** `research/boolean-solver-calibration`

**Starting combined S1/study commit:** `6c954e9c5da7d8b71ba1d5eaea60522d0775fbf8`

**Current status:** the single explicitly authorized pilot completed with
18/18 independently verified support-blind control recoveries, including all
six fresh holdouts. All four phase gates passed. This is bounded recovery
evidence, not Boolean feasibility of either real fixed-LCM target.

**Published pre-run note and executed implementation:**
`9e5efa8b175e2f4330536141c827790a746156c2`.

**Historical freeze-only status:** runner/checker preparation and protocol freeze only, as explicitly
requested by the user. No full-pool control outcome has been inspected for
this configuration, and no information-set pilot-result artifact exists.

**Reading this record:** the algorithm, declaration, conditional forecast,
runner contract and freeze-validation body below are preserved from the
published pre-execution note. Their future-tense and no-output statements
describe that checkpoint. The new results are appended under
"Authorized single pilot"; those historical statements do not authorize a
repeat or describe the current output state.

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
The date segment is a stable RNG-label identifier, not the date the seeds
were selected; changing it would change the declared cases. No witness is
supplied as a hint or warm start.

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

Round 1 used three full-pool calls and Round 2 used nine. This proposal is
for **up to 18 additional calls**, or at most 30 cumulative S1 calls if every
phase runs. The initial plan's call allowance is not an open-ended permission
for more rounds. Execution still needs an explicit coordinator instruction;
this review and forecast do not authorize it.

## Predicted outcome (conditional; recorded before execution)

A fresh-context review of `c0329d2` reported no mechanical correctness
defects and reproduced the 252-test suite on macOS Python 3.9.6 and 3.13
(three legacy optional-backend tests skipped). Its useful recommendation
was to record expectations before the pilot. The forecast below adopts that
recommendation while distinguishing exact facts from model assumptions.
No actual full-pool information sets or seed-specific witness coverages were
computed for this assessment.

### Exact coverage facts and a conditional model

The audited GF(2) solver uses zero free coordinates for its particular
solution and a systematic kernel basis. The planted witness is among the
states enumerated in a particular information set **exactly when at most
three of its selected indices occupy free coordinates**. This is a statement
about geometric coverage, not successful completion under resource limits.
Containing that witness is sufficient, not necessary, for recovery: another
valid subset may also be accepted.

For a uniformly random planted `k`-subset, independent of any fixed
90-element free set in 483 columns, the intersection size `J` is
hypergeometric. Thus:

```text
P(J <= 3) = sum_j C(90,j) C(393,k-j) / C(483,k), j = 0..min(3,k).
```

This one-set marginal does **not** require that column shuffling makes the
free set uniform. That latter assertion is false for general matrices:
with columns `(1,0), (1,0), (1,0), (0,1)`, the last column must be a pivot.
Across all 24 column permutations the only free sets are the three pairs
from the first three columns, each eight times, not all six two-subsets.
No uniform-free-set property has been established for the actual pilot.

| Planted support | One-set coverage under uniform random planting | All-eight miss under an additional independence model only |
|---:|---:|---:|
| 3 | 1.000000000000 | 0 |
| 5 | 0.995114780240 | 3.244e-19 |
| 9 | 0.933163751949 | 3.982e-10 |
| 17 | 0.606503844379 | 5.748e-4 |

The third column is the illustrative planting-witness miss calculation
`(1-P(J<=3))^8`, **not a verified solver-failure probability for these frozen
cases**. Information sets share the matrix and the same witness, their free
sets can be correlated, and the first order is fixed. Multiplying coverage
probabilities under the same model gives approximately 0.996556 for all 18
cases. Interpreting that as solver success adds resource and candidate-cost
assumptions; it is not an established 99.7% success guarantee.

The actual matrix, planting seeds and permutation seed are fixed. These
probabilities describe hypothetical ensembles, not new independent coin
tosses on each rerun. Repeating the same round does not create independent
evidence.

### Candidate counts and cost expectations

Few full-target candidate checks are plausible under a random-code model,
but are not certified by rank alone. Conditioning that model on the known
odd-parity row, a uniform 90-dimensional kernel inside the 482-dimensional
even-parity space gives the reference estimate

```text
E[other small odd solutions] = (M-1) * (2^90-1)/(2^482-1),
M = sum C(483,k) for odd k = 3..17.
```

This is about `2^-289.18`, but **is not a bound for the structured arithmetic
matrix**. A candidate count above one could reveal legitimate structure or
a poor random-code model; it is not by itself an implementation defect.

The fixed pilot's nullity 90 implies at most 121,576 states per completed
information set, or 972,608 over eight sets. The one-million state cap
therefore cannot bind for a correctly processed instance of this rank.
Time, memory and candidate-check limits are different constraints.

The external review reported an approximately two-second in-process
synthetic benchmark with 909,224 states. That count equals the full eight-set
enumeration at **nullity 88**, not 90. Without its rank and stopping details,
it is not a dimension-matched timing validation of the real pilot.
Synthetic orders and in-process timing also do not establish a 30x margin
for the real vectors, worker startup, full residual checks and OS memory
measurement. We did not rerun that benchmark or any actual control.

### Interpretation fixed before outcomes

Good recovery of most or all small-support controls is a reasonable
expectation, conditional on the geometry and cost assumptions. A pass would
validate implementation, measured costs and **bounded support-blind recovery
capability**, not reliability outside this small batch or scaling toward a
counterexample. Predictability does not make that engineering validation
worthless, but this is not a difficult scaling test for the method.

Diagnostic distinctions:

- A completed first information set contains every planted support-3 witness.
  Failure to recover any valid solution after that enumeration **without a
  binding limit** indicates a defect or changed input. A timeout, memory
  stop or candidate cap is a resource observation, not automatically a
  mathematical contradiction.
- A support-5/9/17 miss may challenge the joint-coverage assumptions, the
  actual information-set geometry or the resource forecast. A tiny
  model-based probability does not prove a software bug.
- `projection_inconsistent` on a verified planted target, an invalid subset
  or a residue mismatch is an invariant failure requiring investigation.
- Do not change cases, budgets or parameters to force a pass after outcomes.
  A genuinely harder challenge belongs to a separately declared next round.

The real full-483 fixed-LCM target requires at least 93 factors, while the
frozen algorithm accepts at most 17. It therefore **cannot return a solution
to that real target in this configuration**, independently of any
probability model. For illustration only, a random 93-subset has expected
free weight 17.329 and one-set coverage about `1.630e-6` at free weight at
most three; enumerating the entire free-weight-17 layer would contain
`C(90,17) = 934,433,788,613,079,150` states. This is not a lower bound on
all algorithms or structured targets. These calculations use the 483-pool
dimensions, not the larger S3 pool. No Boolean-feasibility or general
impossibility conclusion follows.

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

### Manual recovery and invariant failures

There is currently no pilot output or reservation. If a future run is
interrupted:

1. Confirm the owning process has ended and preserve its console output,
   traceback, frozen commit/protocol hashes and the precisely identified
   reservation. Do not delete another process's output or use wildcard cleanup.
2. Distinguish a valid saved error report from an empty or partially written
   reservation. A zero-byte file does **not** prove zero calls occurred:
   output is reserved first and the report is written only after final
   checking. Reconstruct which cases and holdouts were actually evaluated.
3. A residue-verification failure raises an invariant-error traceback rather
   than a verified abort report. Preserve that evidence; do not turn an
   encoding inconsistency into an ordinary budget result. A raw gzip/JSON
   error on an incomplete reservation is not a mathematical conclusion.
4. Archive only the exact reservation and associated logs in a known
   diagnostic location. Any replication needs explicit coordinator approval
   and a recorded scope; source changes require a new freeze. Do not simply
   delete the file and rerun until the gates pass, or treat already observed
   holdouts as untouched data after tuning.

The `c0329d2` commit's no-push statement records its local creation step.
The user subsequently authorized its push. This is chronological provenance,
not a reason to rewrite that historical commit.

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
  The exact payload is `json.dumps(items, sort_keys=True).encode("utf-8")`
  with default separators, no indentation and **no trailing newline**.
  `items` follows `case_specs()` order, each entry being
  `{"case": spec.name, "indices": sorted(random.Random(label).sample(range(483), spec.support))}`.
  The development label is
  `f"fs-controls-witness/medium-complete-family/483/{spec.support}/{spec.seed}"`;
  the holdout label is `f"bf-solver-holdout/20261024/{spec.seed}"`.
  Slashes are literal characters in RNG labels, not filesystem separators.
  The check used only these index definitions, not matrices, targets,
  recovery outcomes or solver calls.
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

## Authorized single pilot

The user explicitly authorized publication of the pre-run note followed by
**one execution** on 2026-10-25. The note at `9e5efa8` was pushed and its
remote SHA verified before the pilot started. The reviewed runtime sources
remained byte-identical to the `c0329d2` freeze and the protocol hash remained
`a2ba7c982dc1ea5294a18169cc8a382f41d079163f881ab3fb27cb91f65765b7`.

The invocation receipt records start **2026-10-26 06:18:39 UTC** and finish
**06:19:24 UTC**. There was exactly one runner invocation, with no tuning,
retry, case replacement, extra call, larger harvest or budget increase.

### Outcomes

All 18 cases returned `solution`. Every subset passed independent checks in
all original component orders and in the original prime-product residues.
Every returned subset also matched its planting witness exactly, although
the support-blind interface and checker do not require that identity.

| Planted support | Batch/seed | Returned size | Call seconds | Information sets | States | Peak RSS MiB |
|---:|---|---:|---:|---:|---:|---:|
| 3 | development 101 | 3 | 0.873 | 1 | 1 | 30.785 |
| 3 | development 202 | 3 | 0.515 | 1 | 1 | 31.066 |
| 3 | development 303 | 3 | 0.481 | 1 | 43 | 30.395 |
| 5 | development 101 | 5 | 0.493 | 1 | 2,827 | 31.195 |
| 5 | development 202 | 5 | 0.484 | 1 | 67 | 31.078 |
| 5 | development 303 | 5 | 0.503 | 1 | 40 | 30.984 |
| 5 | holdout 32452843 | 5 | 0.492 | 1 | 48 | 30.871 |
| 5 | holdout 49979687 | 5 | 0.532 | 1 | 1 | 31.059 |
| 5 | holdout 67867967 | 5 | 0.473 | 1 | 1 | 30.633 |
| 9 | development 101 | 9 | 0.478 | 1 | 2,594 | 31.129 |
| 9 | development 202 | 9 | 0.523 | 1 | 2,152 | 30.895 |
| 9 | development 303 | 9 | 0.727 | 2 | 123,705 | 30.863 |
| 17 | development 101 | 17 | 0.613 | 1 | 83,367 | 31.086 |
| 17 | development 202 | 17 | 0.617 | 1 | 90,954 | 31.113 |
| 17 | development 303 | 17 | 0.496 | 1 | 1,458 | 30.746 |
| 17 | holdout 86028121 | 17 | 0.848 | 2 | 241,372 | 30.957 |
| 17 | holdout 104395301 | 17 | 0.493 | 1 | 39 | 30.652 |
| 17 | holdout 122949829 | 17 | 0.778 | 2 | 176,360 | 30.969 |

All four gates passed: support 3 (3/3), support 5 (6/6), support 9 (3/3),
support 17 (6/6). There were no errors, resource stops, timeouts, missing
RSS observations, unrun cases or counterexample claims.

### Costs and verification

- Call wall times: **0.473-0.873 seconds**, sum **10.418 seconds**.
- Input preparation: **15.548 seconds**, separately recorded.
- Complete invocation: **44.852 seconds**, including startup, preparation
  and final independent report checking; not just solve time.
- Completed-worker peak RSS: **30.395-31.195 MiB**, Windows
  `PeakWorkingSetSize`, not aggregate parent-plus-child memory or an OS cap.
- Fifteen cases solved in the identity information set; three needed the
  second set. None exercised the full eight-set worst case.
- Total states: **725,030** across all calls; maximum **241,372** in one
  call, below the one-million per-call limit.
- Exactly **one full-target candidate check per case**, 18 total.

After execution, two frozen-artifact regressions were added without changing
runtime code. All **39 information-set tests** pass on Python 3.14.5 and
3.9.13 (25.841 and 22.408 seconds). The real input preparation and saved-report
checking succeed with the search, worker, affine enumerator and GF(2)
producer patched to raise. All 18 subsets pass the original component
equations/residue checks, and all phase/provenance/limit annotations pass
on both runtimes. These are
read-only checks, not further pilot calls.

The pre-execution 252-test combined-suite results above remain the frozen
runtime regression evidence.

### Artifact and interpretation

[Saved pilot report](../data/generated/bf_solver_information_sets.json.gz):
schema `bf-solver-information-sets/v1`, **28,964 bytes**, SHA256
`d62ac9ba58789262180a71589eb0c3ae9e7e42c0272e1e1a8f2dfbb5d8c149e7`.
It preserves all case scopes, source/input hashes, returned subsets, observed
costs and outcomes. The exclusive local invocation receipt and execution
log were retained as audit records; neither controls the mathematical proof.
Earlier S1 artifacts and all ten runtime sources remain unchanged.

The all-pass outcome is consistent with the optimistic conditional forecast,
but one small batch does not establish its independence/uniformity assumptions
or calibrate a 99.7% joint-success probability. One checked candidate per
case also does not prove that the binary system has no other small solutions:
search stopped at the first valid full-group subset.

This is a completed engineering milestone: the frozen implementation
recovers these actual-vector controls through planted support 17 **without
an exact-support hint** and within the declared budgets. It is not an
unrestricted odd-subset solver, a scaling theorem, a counterexample, or
evidence that the real 93-/191-factor targets are near.

The S1 full-pool call total is now **30 = 3 + 9 + 18**. This authorization
has been consumed. These holdout outcomes are now observed; future tuning
must not describe them as untouched validation data. Any further trial,
replication, wider support envelope or larger pool requires a separate
declared scope and explicit authorization. The next gate is independent
review of this completed bounded result, not an automatic larger search.
