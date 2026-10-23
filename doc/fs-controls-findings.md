# Track A findings: solver calibration on actual-prime controls

**Track:** A (solver controls) per `doc/harvest-solver-feasibility-plan.md`
**Branch:** `research/feasibility-solver-controls`
**Starting commit:** `4128b62` (planning commit; pilot implementation `6494f89`)
**Code commit:** `a9d5b99` (driver + tests); dataset committed with this report
**Interpreter:** Python 3.11.17 (stdlib only; no new dependencies)
**Input artifact:** `data/generated/real_pool_pilot.json.gz`,
sha256 `008cf08ce3f0d3a2…` (full value in `fs_controls.json.gz`)
**Deliverables:** `code/fs_controls.py`, `code/test_fs_controls_correctness.py`
(7/7 pass), `data/generated/fs_controls.json.gz` (59 experiments, full
provenance), this report.

## Protocol

The frozen pilot was loaded and **fully re-verified** with the independent
verifier before any experiment (`verify_saved_report`: 3 instances, 583 prime
certificates, 6 obstructions, 489 distinct primes; 11.3 s). Controls of
support k ∈ {3, 5, 9, 17} were planted from the pilot's own vectors on five
scopes — small-complete (N=6), medium-sample (N=94), and the 18-, 44-prefix
and full (N=483) medium-complete pools, parent LCMs unchanged — three seeds
each. Witnesses live only in the experiment records; solver RNG streams are
seeded from a separate label. Every returned subset was re-verified in the
original multiplicative residues with odd cardinality ≥ 3. The real pilot
targets were kept unchanged and run under identical budgets.

Budgets (declared before the run, per plan §8; **never increased**): 60 s
enforced wall per solver call; fixed-k MITM work cap 2×10⁸ enumerations ×
components, table cap 2²¹; a4 kernel 20,000 states; a6 local 15 s; a6
full-pool MITM scope ≤ 18; oracle scope ≤ 18 (native caps).

## Calibration table (3 seeds per cell; statuses identical across seeds unless noted)

| Scope (N) | nullity | k=3 | k=5 | k=9 | k=17 |
|---|---|---|---|---|---|
| small-complete (6) | 0 | all 4 solvers + oracle solve | fixed-k5, a4, a6, mitm, oracle solve | — | — |
| medium-sample (94) | 0 | fixed-k3 (0.1–0.5 s), a4, a6 solve | fixed-k5 (12–15 s), a4, a6 solve | a4, a6 solve; fixed-k9 capped | a4, a6 solve; fixed-k17 capped |
| complete prefix (18) | 0 | all + oracle solve | all + oracle solve | all + oracle (fixed-k9 3–5 s) | all + oracle (fixed-k17 28–45 s) |
| complete prefix (44) | 0 | fixed-k3, a4, a6 solve | fixed-k5 (1–2 s), a4, a6 solve | a4, a6 solve; fixed-k9 capped | a4, a6 solve; fixed-k17 capped |
| **complete (483)** | **90** | **fixed-k3 25–45 s; a4 3/3 (0.08–15 s); a6 2/3** | **none** (a4 timeout 60 s; a6 inconclusive 15 s; fixed-k5 capped) | **none** (same statuses) | **none** (same statuses) |

Where a solver solved, the recovered subset was in every case the exact
planted witness (`planted_witness_recovered_exactly` true in all 36 solved
planted cells on nullity-0 scopes and in all solved N=483 k=3 cells).

**Reading the table correctly (plan item 5).** Every scope except the full
483-pool has binary nullity 0: the mod-2 system *uniquely determines* the
subset, so a4/a6 "solve" instantly via GF(2) elimination alone. Those 30/30
successes are the predicted easy consistency checks — they validate
correctness, not residual-search power. The only genuinely hard regime in
the frozen pilot is N=483 (rank 393, nullity 90, 2⁹⁰ affine family):

- **Support 3 is reliably solved there**: the bounded fixed-k MITM always
  (25–45 s, exact and complete for its cardinality), a4 kernel search 3/3
  (two seeds via the particular GF(2) solution directly, one via 15 s of
  kernel enumeration), a6 local 2/3 (one seed missed within 15 s).
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
| sample (94) | certified | a4/a6: proved_no_solution; fixed-k3: exact-k negative (1.5 s) |
| prefix (18) | certified | all + oracle: proved_no_solution |
| prefix (44) | certified | a4/a6: proved_no_solution; fixed-k3 exact-k negative |
| **complete (483)** | **none; unresolved** | a4 timeout; a6 inconclusive; **fixed-k3: completed exact search — no subset of exactly 3 of the 483 pool primes hits the real full-pool target (52.4 s)** |

The boxed item is the one new scoped *exact* result on the real target:
a completed enumeration of all C(483, 2)·483-style size-3 combinations
(hash-keyed, every match exactly rechecked). It says nothing about other
cardinalities or other pools.

## Conclusions and one recommendation

1. The corrected baseline solvers are **correct** (oracle agreement on all
   ≤18-column scopes; every solution independently verified; no planted
   contradiction) and **well-calibrated at support 3** on the real 483-pool
   instance.
2. The reliable-recovery regime under conservative budgets is:
   nullity-0 pools at any tested support (trivially, via GF(2) uniqueness),
   and the nullity-90 pool at support 3 only. **The boundary is between
   support 3 and 5 at N = 483.** The binding gap is residual search in the
   2⁹⁰ kernel family — a4's raw Gray enumeration and a6's annealing both
   fail it at support ≥ 5 within 60 s.
3. **Recommendation** (one, per the handback checklist): before any larger
   search or budget escalation, invest in a kernel-coordinate solver for
   supports 5–17 — e.g. meet-in-the-middle over the 90-dimensional kernel
   space itself (split kernel basis, hash partial residuals), which is the
   direct generalization of what already works at k=3 and fits the existing
   budgets. Uncertainty: the 60 s walls are conservative; it is possible
   (untested, and not attempted per the stop rule) that modest budget
   increases alone would lift a4 at k=5. Stop condition honored: no budget
   was increased, and no claim is made that the real 483 target is
   infeasible.

## Handback checklist

- Branch `research/feasibility-solver-controls`; start `4128b62`; code
  commit `a9d5b99`; this commit adds the dataset and report.
- Files changed: only the four Track-A-owned files. No baseline file,
  dataset, README, registry or paper was modified.
- Tests: `python code/test_fs_controls_correctness.py` → 7/7 pass.
- Reproduce: `python code/fs_controls.py --output <path>` (pilot path and
  budgets recorded in the output; seeds 101/202/303; witness/solver RNG
  labels in `fs_controls.json.gz`).
- Provenance: source SHA256 of the six baseline files plus `fs_controls.py`,
  input artifact SHA256, interpreter version, budgets, and per-experiment
  seeds/targets/outcomes/timings are all in the dataset.
- Witnesses: every planted control verified at planting; every reported
  solution re-verified independently (`verify_group_solution`); no
  counterexample claims (0, as expected).
- Shared-interface note for the coordinator (no action required): this
  track self-capped `mitm_frontier` at 18 columns for time, although the
  baseline permits N ≤ 44; and `a6_oddsolver.solve`'s annealing reports
  only φ/best/moves on failure — a per-component residual histogram would
  help future calibration. Neither blocked progress.
- Outcome classes used: solution (verified) / proved_no_solution (with
  certificate or completed oracle scope) / proved_no_solution_exact_cardinality
  (completed exact-k scope) / resource_limit (declared caps) /
  inconclusive_budget / timeout_enforced. Timeouts and caps are inconclusive.
