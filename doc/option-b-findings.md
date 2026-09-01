# Option-b findings — direction 6: algebraic / pseudo-Boolean CDCL (Davis–Putnam-style search)

*2026-09-01. Executes `doc/b6-cdcl-plan.md` (P1–P3b) for direction 6 of
`doc/option-b-problem.md`. Code: `code/b_cdcl_instances.py` (instances +
encodings + P2 gate), `code/b_cdcl_falsify.py` (P3 grid),
`code/b_dp_prune_depth.py` (P3b). Raw results:
`data/generated/b6_cdcl_grid.jsonl`, `data/generated/b6_prune_depth.json`.
Branch note: work is on the session branch `claude/nice-dijkstra-pukzrv`
(harness-assigned name), not a branch literally named `option-b-solver`.*

## Summary verdict

**Direction 6 is dead: gate G-b6-1 (milestone m1 — solve D = 50 at ρ = 0.004)
FAILED, by a wide, mechanistically explained margin.** The best off-the-shelf
algebraic-CDCL engine (CP-SAT) has its ρ = 0.004 frontier at **D = 6
components (~30 demand bits)** — *below* the exact-MITM frontier (~15, A6)
and the Wagner-4 reach (~20, A10). Time-to-solve tracks ~2^(demand bits), so
longer caps buy ~1 component per 30× compute; no cap reaches D = 50 (255
bits), let alone the real D ≈ 10³–10⁴. The P3b measurement explains why and
extends the verdict to the proposed bespoke build: sound Davis–Putnam-style
pruning (including the GF(ℓ) theory-propagator rule such a build would rely
on) first fires when 1–6 variables remain unassigned out of 1,000–20,000 —
the search tree is unpruned until the search is over. Branch-and-prune is now
the third independent algorithm family (after exact search and birthday/list
methods) measured to fail on this instance class, each for the same
density-driven reason. Remaining within-direction residual: a RoundingSat
(native cutting-planes) run, assessed as a completeness item, not a live
hope (see "What remains untried").

## P0/P2: tooling and correctness gate — PASSED

- Environment: OR-tools CP-SAT 9.15.6755, Z3 5.1.0, python-sat 1.9
  (pip-installed this session). RoundingSat not built (see decision log).
- **Gate G-b6-0 (correctness): 20/20.** On easy small-moduli instances
  (`primes_cap=13`, D = 4–8, N ≤ 36, ρ alternating 0.004/0.5), every CP-SAT
  answer verified (residues + odd parity) and the exact MITM oracle
  (`a6_oddsolver.mitm_frontier`) confirmed a residue-solution exists on all
  20. The encodings are correct; everything below is search behavior, not
  encoding artifacts.

## Decision log (deviations from the plan, with reasons)

1. **P2 redefined from "solvers succeed" to "encodings correct".** An early
   probe showed the original gate was unpassable for the *interesting*
   reason: at realistic moduli (primes ≤ 97), CP-SAT and Z3 both time out at
   30 s already at **D = 6, N = 36, ρ = 0.004** — an instance the exact MITM
   oracle solves in **1.7 s**. Solver success on hard cells is P3 *data*;
   gating on it would have conflated hardness with bugs.
2. **Z3 demoted from the P3 grid.** Two encodings tried (native `Sum % ℓ`,
   and slack-equality LIA); both time out even on ρ = 0.5, D = 7, N = 36
   instances that CP-SAT solves in 0.15 s. Z3's simplex+branch LIA engine is
   dominated on dense pseudo-Boolean equalities — recorded, and consistent
   with folklore that PB/CP engines beat SMT-LIA on this shape. Engine
   diversity is instead covered by the (conditional) RoundingSat build.

## P3: off-the-shelf CP-SAT falsification grid — COMPLETE (64 runs)

Grid: D ∈ {6,8,10,12,15,20,30,50} × ρ ∈ {0.004, 0.5} × pool regimes
{ratio10: N ≈ 10× demand bits; a10: N = 20,000} × 2 seeds; cap 120 s,
8 workers; planting `half` (support ≈ N/2, statistically invisible). Every
"solved" is verified (residues + parity). Solved-per-2-seeds:

| D | demand bits | ρ=0.004 ratio10 | ρ=0.004 a10 | ρ=0.5 ratio10 | ρ=0.5 a10 |
|---|---|---|---|---|---|
| 6 | 30.0 | **2/2** (114 s / 18 s; 262k / 70k conf) | **1/2** (31 s) | 2/2 (0.05 s) | 2/2 (~6 s) |
| 8 | 40.4 | 0/2 | 0/2 | 2/2 (0.1 s) | 2/2 (~10 s) |
| 10 | 51.6 | 0/2 | 0/2 | 2/2 (~0.5 s) | 2/2 (~12 s) |
| 12 | 62.0 | 0/2 | 0/2 | 2/2 (5–14 s; 12k–31k conf) | 2/2 (~16 s) |
| 15 | 76.6 | 0/2 | 0/2 | 0/2 | 2/2 (23–51 s) |
| 20 | 100.9 | 0/2 | 0/2 | 0/2 | 0/2 |
| 30 | 152.5 | 0/2 | 0/2 | 0/2 | 0/2 |
| 50 | 254.6 | 0/2 | 0/2 | 0/2 | 0/2 |

Readings:

1. **ρ = 0.004 frontier: D = 6, i.e. ~30 demand bits.** For calibration,
   exact MITM handles ~15 components (A6) and Wagner-4 ~20 (A10): the modern
   branch-and-prune engine is the *weakest* method measured on this problem,
   not the strongest. Milestone m1 (D = 50) is missed by ~44 components /
   ~225 bits.
2. **The scaling is ~2^(demand bits), as predicted by zero pruning.** The
   solved D = 6 cells burn 10⁵–10⁶ conflicts on a 30-bit demand in
   10²–10⁴ ms; each added component adds ~5 bits ≈ 30× time. That is why no
   escalation runs were performed (a deviation from the plan's 1 h cap,
   justified): 1 h caps would move the frontier by roughly *one* component;
   D = 50 needs ~2^225× more than the cap. There is no ambiguity for longer
   caps to resolve.
3. **Density, not size, is the driver.** ρ = 0.5 reaches D ≈ 12–15
   (~62–77 bits) with visibly exponential conflict growth, then dies. The
   ρ separation matches A10's Wagner law at micro scale, in a completely
   different algorithm family.
4. **Pool abundance helps only at the margin.** ratio10 vs a10 changes
   which small-D cells scrape under the cap (more solutions vs more model
   overhead at N = 20k — note the a10 D = 6 seed-0 miss with conf = 1:
   the 120 s cap went almost entirely to presolve at that size), but no
   regime moves the frontier past D ≈ 6–7 at ρ = 0.004.

## P3b: Davis–Putnam prune-fire depth — measured, and it is decisive

Question (the DP question of direction 6): at what depth do *sound*
generalized-DP pruning rules start cutting the search tree? Rules: **R1** —
residual per-prime GF(ℓ) rank feasibility with the 0/1 restriction dropped
(the theory-propagator prune); **R2** — residual parity satisfiability;
**R3** — the (unsound) counting rule, fires when unassigned u < demand bits.
Method: 200 random branches per cell (random order, random 0/1 values), exact
Gaussian elimination once u ≤ n_max + 24, else feasible with probability
≥ 1 − ℓ^−24 (`b_dp_prune_depth.py`).

Result — R1 first-fire distribution, as u* = unassigned variables remaining
at first prune (200 trials per cell, ρ = 0.004):

| D | regime | N | demand bits | n_max/prime | u* median | u* distribution |
|---|---|---|---|---|---|---|
| 20 | ratio10 | 1,008 | 100.9 | 2 | **1** | {1:158, 2:38, 3:3, 4:1} |
| 20 | a10 | 20,000 | 100.9 | 2 | **1** | {1:153, 2:42, 3:5} |
| 50 | ratio10 | 2,546 | 254.6 | 4 | **3** | {3:182, 4:17, 5:1} |
| 50 | a10 | 20,000 | 254.6 | 4 | **3** | {3:184, 4:13, 5:2, 6:1} |

**Reading:** on a random branch, the first sound prune fires when **1–6
variables remain unassigned out of 1,000–20,000** (u* tracks the per-prime
rank n_ℓ, as predicted: a residual linear system over GF(ℓ) cannot be
infeasible while it is underdetermined). R2 fires only at u = 0. Even the
*unsound* counting rule R3 fires only at u ≈ demand bits (101 / 255) — i.e.
the tree is entirely unpruned for its first N − u* levels under any of these
rules. Extrapolation to real scale (D ≈ 4,600 over 24 primes, n_ℓ ~ hundreds,
N ≈ 2.5×10⁵): sound pruning begins in the last ~10³ of 2.5×10⁵ levels —
proportionally the same nothing.

**Conclusion (P3b):** generalized Davis–Putnam pruning — variable
elimination (already closed analytically: induced width ~N at ρ = 0.004),
DPLL-style propagation, and DPLL(T) theory-level pruning with the natural
sound rules — has **measured near-zero leverage** on this instance class.
Solutions are so abundant that almost every partial assignment stays
linearly extendable until the assignment is essentially complete; pruning
power appears exactly where exhaustive search no longer needs it. A bespoke
CDCL + GF(ℓ)-propagator build would inherit these propagators and therefore
this profile; conflict learning could only help via structure the
instance does not appear to have (cf. the A6 annealing null and A10's match
to uniform-random predictions).

## Relation to prior walls

The result is the CDCL/DP face of the same phenomenon measured before:
exact methods cap at ~15 components (A6), Wagner-4 at ~20 (A10), and here
branch-and-prune search loses its pruning until depth ~N. Three independent
algorithm families, one regime, one explanation: at ρ ≈ 0.004 the
constraints are global, dense, and individually loose — nothing local to
propagate, eliminate, or prune on.

## What remains untried within direction 6

- **RoundingSat / native cutting planes** (source build): could conceivably
  outperform CP-SAT's linearization on the PB equalities; nothing in the
  P3b profile suggests it changes the picture (cutting planes still need
  the relaxation to become infeasible, which is the R1 event), so this is
  a completeness item, not a live hope.
- Conflict-driven search with *restarts tuned for abundance* (aiming to
  luck into one of the ~2^(N−demand) solutions) is bounded by the R3 curve:
  a random dive still needs ~demand-bits of lucky residue coincidences,
  i.e. probability ~2^−demand per dive — 2^−255 already at D = 50.
