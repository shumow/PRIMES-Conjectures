# Proposed next phase: binary-affine, carry-aware Boolean lifting

**Status (2026-11-02): proposal only, not authorized for execution.**
No new targets, planting witnesses, free-set coverages or recovery outcomes
have been evaluated for this proposal. Its preparation uses existing findings,
source inspection and exact combinatorial calculations only.

The [reviewed study](../README.md#boolean-feasibility-study-reviewed-integration)
and [watchdog repair](shared-watchdog-repair-plan.md#10-accepted-post-merge-review-follow-ups)
are on main at `b2d5042`. The current documentation and source-version
diagnostic follow-ups do not renew any experimental allowance.
This proposal follows the diagnostic implementation at
`68ee39174823d5fab5103c187c8dbcd9e9751f24`; that code/proposal working branch
still needs its normal review and authorized landing.

## 1. Decision this experiment would inform

**Question:** can explicit binary-affine constraints plus exact modular
refinement recover higher-support, actual-vector controls without giving
the solver their support, and without enumerating a bounded free-weight shell?

Recommend testing this single formulation on the existing **483-prime anchor**.
Do not harvest more primes or start with the 2,234-prime S3 pool.
The [initial CP-SAT failure](bf-solver-findings.md) remains a caution: a correct
carry model is not automatically an effective search algorithm.

The proposed supports are **17, 41 and 93**. Support 17 is a fresh calibration
gate; 41 tests an intermediate regime; 93 reaches the anchor's real-target
minimum-cardinality scale, not its real target. Passing any or all controls
would still not prove Boolean feasibility for the real target or predict
recovery at S3's minimum of 191.

### Why not simply extend the frozen information-set search?

The anchor has 90 free binary coordinates; S3 has 1,515. Enumerating all free
assignments costs `2^90` or `2^1515`. Even sparse enumeration grows quickly:

| Anchor free-weight ceiling | `sum(C(90,j), j=0..w)` states per set |
|---:|---:|
| 3 | 121,576 |
| 10 | 6,512,554,148,192 |
| 17 | 1,205,900,704,396,823,273 |

For a *hypothetical uniform k-subset* and a fixed free-column set of size `f`
in `N` columns, the probability of at most three free positions is exactly
`sum(C(f,j)*C(N-f,k-j), j=0..3) / C(N,k)`, with impossible terms omitted:

| Pool / planted support | Mean free positions | One-set coverage | Eight-set union upper bound |
|---|---:|---:|---:|
| Anchor / 17 | 3.168 | 0.606504 | 1 |
| Anchor / 41 | 7.640 | 0.0328236 | 0.262589 |
| Anchor / 93 | 17.329 | 0.00000162981 | 0.0000130385 |
| S3 / 191 | 129.528 | 8.70019e-96 | 6.96015e-95 |

These are geometric calculations for recovering the planted subset, not
empirical success rates or bounds on finding any alternative valid subset.
They assume uniform hypothetical supports, not uniform free sets, and the
union bound assumes no independence between information sets. They do not
assign probabilities to the already fixed seeds or to the real targets.
The actual frozen selection cap of 17 additionally excludes the real targets
by their product-size bounds. S3's free-weight-three shell alone has
579,545,576 states per set, already beyond the frozen one-million-state budget.

The proposed model removes that artificial sparse-shell restriction. Whether
its exact constraints prune enough to be useful is **an untested hypothesis**,
not a complexity improvement established by these counts.

## 2. One proposed formulation, one existing backend

Reuse audited input encoding, binary projection and independent checkers,
but implement this experiment in a new versioned `bf_solver_lifting` module,
report and tests. Preserve every earlier solver/report/protocol unchanged.
Use only the already approved optional **OR-Tools CP-SAT 9.15.6755** backend.

1. Construct the necessary binary system from every even-order original
   component plus odd cardinality, in original column order.
2. Obtain a systematic particular vector `x0` and kernel basis `B`. Check
   directly that they satisfy the original binary equations, that the free
   block is an identity, and that there are the expected 90 free coordinates.
3. Introduce 90 Boolean free variables `y` and 483 selection variables `x`,
   with exact Boolean equations `x[i] XOR XOR_j(B[i,j]*y[j]) = x0[i]`.
   Keep `sum(x) >= 3` and odd cardinality. **No exact support, warm start,
   cap 17, cap 93 or witness-derived objective is supplied.**
4. Ask the backend for one candidate using the remaining call deadline.
   Recompute that candidate's sums in **all 1,132 original component orders**.
5. If any row fails, add up to eight previously unmodeled violated rows,
   in original row order, as exact carry equations:

   ```text
   sum_i a[j,i]*x[i] = t[j] + m[j]*z[j]
   0 <= z[j] <= floor((sum_i a[j,i] - t[j]) / m[j])
   ```

   Coefficients and targets are normalized modulo the original `m[j]`.
   Check backend integer ranges using the existing conservative guards.
   Retain all prime powers; there are no independent bit-slice substitutes.
6. Repeat within the unchanged per-call budget, at most **64 native solver
   queries and 64 full-component candidate checks**. Add at most 512 carry
   rows. Reaching a cap is inconclusive, not exhaustion of the Boolean space.
7. Only a candidate passing every original group equation can be returned
   as a solution. The parent independently checks distinct indices, odd
   cardinality, group equations and original-prime multiplicative residues.

Each added row is a necessary original constraint, so no genuine full-group
solution is removed by refinement. Overlapping XOR moves affect the exact
selection mask; full-group residuals are never treated as additive in `y`.
A candidate violating an already active row is an implementation contradiction,
not a reason to silently add another constraint or continue.

This is not just the original carry model with a longer timeout: the complete
binary-affine relation is explicit from the start, and remaining rows are
introduced by a fixed violation rule. It still may perform worse than the
bounded information-set method, including at the first calibration gate.

## 3. Fresh controls and pre-run freeze

Use the unchanged [anchor artifact](../data/generated/real_pool_pilot.json.gz),
SHA256 `008cf08ce3f0d3a2f987bff26d5abd04bf4c41050f949ae0fdc4f4192b6969de`,
with its retained prime order and parent LCMs. No S3 solver call is included.

| Stage | Parent-known support | Development seeds | Fresh holdout seeds |
|---:|---:|---|---|
| 0 | 17 | 1701101, 1701102, 1701103 | 1701901, 1701902, 1701903 |
| 1 | 41 | 4101101, 4101102, 4101103 | 4101901, 4101902, 4101903 |
| 2 | 93 | 9301101, 9301102, 9301103 | 9301901, 9301902, 9301903 |

Define `label = "bf-lift-controls/v1/20261102/{support}/{batch}/{seed}"`,
with `batch` exactly `development` or `holdout`, decimal integers without
padding, and the table order above. The parent constructs
`tuple(sorted(random.Random(label).sample(range(483), support)))`.
The namespace date is a stable identifier, not a claim about execution time.
Do not sample these witnesses merely while preparing or reviewing this proposal.

Freeze one implementation/configuration and this complete case list before
**any** full-pool call. Before evaluation, record all target-definition digests,
source/input hashes, protocol hash, backend/interpreter/platform and budgets
in a committed pre-run note. If any new witness/target duplicates another new
case or a prior observed control, stop before the batch and request a declared
revision; do not silently redraw or replace a case after observing outcomes.
The eventual runner must require an explicit execution mode, reserve a new
versioned output exclusively before any call, and verify committed source/head
and protocol hashes before and after the batch. An interrupted or empty output
reservation is not evidence that no calls occurred and does not authorize a retry.

Only vectors, target, `min_size=3`, `exact_size=None`, fixed limits and solver
seed **1729** reach the worker. Support labels, seeds, witnesses, prime records
and residue targets remain in the parent. Backend threads: one; no parameter
sweep, random restart portfolio or target-specific ordering.

For each reached stage, evaluate the three development cases first. All three
must pass before its three holdouts run. All six must pass before the next
stage begins. A development failure leaves its holdouts/later stages explicitly
unrun; finish only the already declared development batch unless an error aborts.
There is no tuning between development and holdout evaluation.

Any valid odd subset of size at least three may count, not only the planting
witness. Report both planted and returned cardinalities after independent
verification; do not leak either back into subsequent calls as search hints.

## 4. Proposed aggregate budget and cost model

| Resource | Fixed proposed limit / accounting |
|---|---|
| Full-pool worker trials | At most 18, one at a time; no retries or real-target call |
| Wall per trial | 60 seconds including startup, projection, imports, model, refinement, handoff and independent candidate acceptance |
| Worker native queries / candidate checks | At most 64 each per trial; at most 1,152 each over all 18 trials |
| Independent checks | One parent acceptance check per returned subset; final checker replays up to 64 rejected/returned candidates per trial plus each accepted subset |
| Exact carry rows | At most eight new rows per rejection, 512 active rows per trial |
| Input preparation | 120 seconds; separately recorded, not hidden in solver timing |
| Final report verification | 120 seconds; read-only, with producers disabled |
| Worker memory | 512 MiB observed peak-RSS target; native advisory setting, not an OS cap |
| Parent memory | 512 MiB observed peak-RSS target; combined parent/worker peak-sum target 1 GiB, not a process-family hard cap |
| Aggregate wall | 1,800 seconds including preparation, verification, startup and cleanup; unused time authorizes no extra call |
| Aggregate CPU | 1,800 processor-seconds, sum of parent and worker CPU; record actual values and stop on reaching the allowance |
| Storage | 64 MiB report ceiling, 128 MiB total new report/scratch allowance; keep all old artifacts read-only |

The anchor has 546,756 original matrix entries and at most 35,370 pivot/free
incidences. Even counting the original matrix plus 512 dense carry rows and
those incidences gives 829,422 entries, below a one-million-entry guard.
One full candidate check uses at most 546,756 coefficient additions; 64 checks
give at most 34,992,384 such additions per trial in the worker. Parent acceptance
and later independent replay are additional checks within the separately
declared call/verification budgets, not hidden in that worker count. These
counts do not estimate native solver runtime or promise that it will complete
64 queries in 60 seconds.

Search runs inside the repaired process watchdog. Native solve time is reduced
to the remaining deadline before each query; parent validation finishing late
cannot count as a solution. Cleanup/OS I/O can overrun a wall deadline and must
be recorded rather than hidden. CPU, storage and observed RSS accounting need
explicit checks; they are not hard quotas merely because this table names limits.
Unavailable memory/CPU measurements cannot be silently counted as budget compliance.
Implement the aggregate accounting and interruption/error path before seeking
execution approval; an unimplemented limit is not a valid frozen protocol.

## 5. Correctness gates before requesting execution approval

- Compare the binary-affine and carry/refinement model against exhaustive
  subset oracles on at least 320 seeded tiny-system decisions, including
  heterogeneous prime powers, overlapping basis moves, parity/cardinality,
  false targets and exact carry bounds. These are unit fixtures, not pilot calls.
- Test that each cut preserves all oracle solutions; reject duplicate/incorrect
  cuts, candidates violating active rows, and discarded higher-power carries.
- Prove with tests that no support/planting metadata or warm start reaches the
  worker. Exercise actual tiny native/Windows spawn and the watchdog lifecycle.
- Test partial budgets, 64-query/candidate caps, late handoff, RSS/CPU/storage
  measurement failures, worker errors, interruption, gating and no-clobber output.
- An independent report checker must reconstruct cases/provenance, recheck every
  returned subset in original equations/residues, and replay recorded rejected
  candidate/cut rows directly. It must not invoke search, elimination or cut
  generation, trust a backend status, or require equality to the planting witness.
- Store native-query counts separately from the at-most-18 worker trials.
  A native `INFEASIBLE` on a verified planted target is a contradiction requiring
  investigation and batch abort, not a negative mathematical result. Likewise
  abort on model/input/projection errors. `UNKNOWN`, limits and timeouts are
  explicitly inconclusive; incomplete later phases stay in the report.
- Run the affected tests on Python 3.9 and a current supported runtime, preserve
  all ten existing artifact hashes, and obtain independent pre-run review.
  Only after the code/protocol is frozen, request separate explicit authorization
  for the one bounded batch.

## 6. Decision after the proposed batch

- **Fails the fresh support-17 gate:** publish the bounded negative engineering
  result; do not spend the support-41/93 allowance or raise limits.
- **Passes 17 but not 41/93:** record the precise frontier and refinement/query
  costs. A longer run or another formulation is a new proposal, not a retry.
- **Passes all 18:** this is support-blind recovery at a higher planted-support
  scale on the anchor, not recovery of its real target or proof of scaling.
  Request a fresh review before proposing S3 controls or any real-target search.

The real fixed-parent-LCM targets remain Boolean-unresolved. Their bounds of
93 and 191 do not imply that a real solution exists at those sizes, and the
planted targets do not inherit those lower bounds. No outcome here changes
the original conjectures or generalizes fixed-LCM findings to selected-subset
LCMs. The previous **30 S1 full-pool calls remain historical**; this document
has not added an executed call.
