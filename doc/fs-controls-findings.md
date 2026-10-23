# Track A findings: solver calibration on actual-prime controls

**Track:** A (solver controls) per `doc/harvest-solver-feasibility-plan.md`
**Branch:** `research/feasibility-solver-controls`
**Starting commit:** `4128b62` (planning commit; pilot implementation `6494f89`)
**Code commits:** `a9d5b99` (initial driver + tests), `39be9a8` (review fixes:
portable watchdog, unittest discovery); dataset v1.1 committed with this report
**Interpreter:** Python 3.11.17 (stdlib only; no new dependencies)
**Input artifact:** `data/generated/real_pool_pilot.json.gz`,
sha256 `008cf08ce3f0d3a2…` (full value in `fs_controls.json.gz`)
**Deliverables:** `code/fs_controls.py`, `code/test_fs_controls_correctness.py`
(9/9 via `python -m unittest discover -s code -p "test_fs_*.py"`),
`data/generated/fs_controls.json.gz` (schema `fs-controls/v1.1`, 59
experiments, full provenance), this report.

**Revision note (PR #5 coordinator review, 2026-10-23).** This version
addresses the review: (1) the POSIX-only SIGALRM wall was replaced by a
portable process watchdog (spawned worker per solver call, terminated at the
deadline; identical on POSIX and Windows; worker exceptions classified as
`worker_error`, never swallowed); (2) tests are unittest-discoverable, with
new regressions for the enforced-timeout and worker-error paths; (3) the
kernel-MITM recommendation below is qualified per the review's overlap/carry
counterexample; (4) the planted-cell counts are corrected (42, not 30/36);
(5) the exact-size-3 real-target result is marked as subsumed by a
product-size bound. The calibration was fully rerun under the watchdog; every
status reproduced the v1 run seed-for-seed (timings shifted by child-process
startup, which the reported seconds now include).

## Protocol

The frozen pilot was loaded and **fully re-verified** with the independent
verifier before any experiment (`verify_saved_report`: 3 instances, 583 prime
certificates, 6 obstructions, 489 distinct primes; ~11 s). Controls of
support k ∈ {3, 5, 9, 17} were planted from the pilot's own vectors on five
scopes — small-complete (N=6), medium-sample (N=94), and the 18-, 44-prefix
and full (N=483) medium-complete pools, parent LCMs unchanged — three seeds
each. Witnesses live only in the experiment records; solver RNG streams are
seeded from a separate label. Every returned subset was re-verified in the
original multiplicative residues with odd cardinality ≥ 3, in the parent
process (verification never runs inside a solver worker). The real pilot
targets were kept unchanged and run under identical budgets.

Budgets (declared before the run, per plan §8; **never increased**): 60 s
enforced wall per solver call via the process watchdog (sequential — one
worker at a time); fixed-k MITM work cap 2×10⁸ enumerations × components,
table cap 2²¹; a4 kernel 20,000 states; a6 local 15 s; a6 full-pool MITM
scope ≤ 18; oracle scope ≤ 18 (native caps). Outcome vocabulary: `solution`
(independently verified) / `proved_no_solution` (certificate or completed
oracle scope) / `proved_no_solution_exact_cardinality` (completed exact-k
scope) / `resource_limit` (declared caps) / `inconclusive_budget` /
`timeout_enforced` / `worker_error`. Timeouts, caps and worker errors are
inconclusive; **zero `worker_error` outcomes occurred**.

## Calibration table (3 seeds per cell; statuses identical across seeds unless noted)

| Scope (N) | nullity | k=3 | k=5 | k=9 | k=17 |
|---|---|---|---|---|---|
| small-complete (6) | 0 | all 4 solvers + oracle solve | fixed-k5, a4, a6, mitm, oracle solve | — | — |
| medium-sample (94) | 0 | fixed-k3, a4, a6 solve | fixed-k5 (~14–18 s), a4, a6 solve | a4, a6 solve; fixed-k9 capped | a4, a6 solve; fixed-k17 capped |
| complete prefix (18) | 0 | all + oracle solve | all + oracle solve | all + oracle (fixed-k9 ~3–6 s) | all + oracle (fixed-k17 ~30–50 s) |
| complete prefix (44) | 0 | fixed-k3, a4, a6 solve | fixed-k5 (~1–2 s), a4, a6 solve | a4, a6 solve; fixed-k9 capped | a4, a6 solve; fixed-k17 capped |
| **complete (483)** | **90** | **fixed-k3 23–44 s; a4 3/3 (0.2–14.5 s); a6 2/3** | **none** (a4 timeout 60 s; a6 inconclusive 15 s; fixed-k5 capped) | **none** (same statuses) | **none** (same statuses) |

Counts (reconciled per review): **42 planted nullity-zero experiments, all 42
solved**; including the full-483 pool, **45 planted cells were solved in
total, and in all 45 the recovered subset was the exact planted witness**.

**Reading the table correctly (plan item 5).** Every scope except the full
483-pool has binary nullity 0: the mod-2 system *uniquely determines* the
subset, so a4/a6 "solve" instantly via GF(2) elimination alone. Those 42/42
successes are the predicted easy consistency checks — they validate
correctness, not residual-search power. The only genuinely hard regime in
the frozen pilot is N=483 (rank 393, nullity 90, 2⁹⁰ affine family):

- **Support 3 is reliably solved there**: the bounded fixed-k MITM always
  (23–44 s, exact and complete for its cardinality), a4 kernel search 3/3
  (two seeds via the particular GF(2) solution directly, one via ~15 s of
  kernel enumeration), a6 local 2/3 (seed 303 missed within 15 s, in both
  the v1 and v1.1 runs).
- **Supports 5, 9, 17 were not recovered by any method within the declared
  budgets** — a4 hit the enforced 60 s wall, a6 exhausted its 15 s budget
  (residual φ > 0), fixed-k exceeded its declared work cap at k ≥ 5 for
  N = 483. Per the plan these are reported as failures on known-feasible
  controls; they are inconclusive about the targets, and budgets were not
  raised.

## Real targets (unchanged, same budgets)

| Scope | necessary obstruction | outcomes |
|---|---|---|
| small (6) | certified | all solvers + oracle: proved_no_solution (consistent with certificate) |
| sample (94) | certified | a4/a6: proved_no_solution; fixed-k3: exact-k negative |
| prefix (18) | certified | all + oracle: proved_no_solution |
| prefix (44) | certified | a4/a6: proved_no_solution; fixed-k3 exact-k negative |
| **complete (483)** | **none; unresolved** | a4 timeout; a6 inconclusive; fixed-k3: completed exact search — no subset of exactly 3 of the 483 pool primes hits the real full-pool target (58.2 s) |

**Scope of the exact-size-3 result (per review).** The completed size-3
search is *subsumed by arithmetic*: since $n \equiv -1 \pmod{\Lambda_+}$ and
$n \equiv 1 \pmod{\Lambda_-}$ force $n \ge \Lambda_- + 1$
($\log_2 \Lambda_- \approx 3094.5$), a greedy largest-primes product bound
already requires **at least 92 selected primes** for the frozen full-483 real
target (the coordinator's accounting gives 93; either way, far above any
small support). The size-3 run therefore has value only as an end-to-end
exercise of the exact pipeline on the real target, not as new information
about it — and small-support control recovery is calibration, not evidence
of approaching that target.

## Conclusions and one recommendation

1. The corrected baseline solvers are **correct** (oracle agreement on all
   ≤18-column scopes; every solution independently verified; no planted
   contradiction; statuses reproduced seed-for-seed across the v1 and v1.1
   runs) and **well-calibrated at support 3** on the real 483-pool instance.
2. The reliable-recovery regime under conservative budgets is:
   nullity-0 pools at any tested support (trivially, via GF(2) uniqueness),
   and the nullity-90 pool at support 3 only. **The boundary is between
   support 3 and 5 at N = 483.** The binding gap is residual search in the
   2⁹⁰ kernel family — a4's bounded kernel enumeration and a6's annealing
   both fail it at support ≥ 5 within 60 s. Note the real target, by the
   size bound above, lives at support ≥ 92: closing the 5–17 control gap is
   a prerequisite capability milestone, not a near-target event.
3. **Recommendation** (one, per the handback checklist; qualified per the
   coordinator review): before any larger search or budget escalation,
   investigate solvers for supports 5–17 that operate in the GF(2) kernel
   family **while respecting that residuals are not additive under
   overlapping XOR kernel moves** — the review's counterexample (orders
   (3,2), vectors [(1,1),(0,1),(0,1)], base mask 1, kernel moves 3 and 5:
   individual residual changes (2,0)+(2,0) ≠ combined (0,0)) is exactly the
   pitfall the original A4 audit repaired, so any meet-in-the-middle over
   kernel coordinates must either restrict to disjoint-support move
   decompositions, recompute exact residuals per candidate (as the
   working fixed-k baseline does), or carry explicit overlap corrections.
   A naive half-split of the 90-dimensional kernel (2⁴⁵ entries per side)
   is **not** feasible under the current budgets; bounded-weight kernel
   combinations with exact Gray-style updates are the plausible starting
   point. This is a research direction with the overlap/carry issue as its
   first obstacle, **not** a design that fits 60 s / 512 MiB as previously
   implied. Uncertainty: the 60 s walls are conservative; it is possible
   (untested, and not attempted per the stop rule) that modest budget
   increases alone would lift a4 at k=5. Stop condition honored: no budget
   was increased, and no claim is made that the real 483 target is
   infeasible.

## Handback checklist

- Branch `research/feasibility-solver-controls`; start `4128b62`; commits
  `a9d5b99` (code) + `b42c95f` (v1 data/report) + `39be9a8` (review fixes)
  + this commit (v1.1 data, corrected report).
- Files changed: only the four Track-A-owned files. No baseline file,
  dataset, README, registry or paper was modified.
- Tests: `python -m unittest discover -s code -p "test_fs_*.py"` → 9/9
  (also runnable directly). Includes timeout-path and worker-error-path
  regressions for the watchdog.
- Reproduce: `python code/fs_controls.py --output <path>` (pilot path and
  budgets recorded in the output; seeds 101/202/303; witness/solver RNG
  labels in `fs_controls.json.gz`). Statuses are deterministic given the
  budgets; a6_local outcomes near its time budget may vary with hardware.
- Provenance: source SHA256 of the six baseline files plus `fs_controls.py`,
  input artifact SHA256, interpreter version, budgets, watchdog description,
  and per-experiment seeds/targets/outcomes/timings are all in the dataset.
- Witnesses: every planted control verified at planting; every reported
  solution re-verified independently (`verify_group_solution`), in the
  parent process; no counterexample claims (0, as expected).
- Shared-interface note for the coordinator (no action required): this
  track self-capped `mitm_frontier` at 18 columns for time, although the
  baseline permits N ≤ 44; and `a6_oddsolver.solve`'s annealing reports
  only φ/best/moves on failure — a per-component residual histogram would
  help future calibration. Neither blocked progress.
- Integration destination (review note): PR #5 targets the planning branch
  so the diff is exactly the Track A work; retargeting to `main` is a
  coordinator decision and merges cleanly either way.
