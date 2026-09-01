# Option-b findings — direction 6: algebraic / pseudo-Boolean CDCL (Davis–Putnam-style search)

*2026-09-01. Executes `doc/b6-cdcl-plan.md` (P1–P3b) for direction 6 of
`doc/option-b-problem.md`. Code: `code/b_cdcl_instances.py` (instances +
encodings + P2 gate), `code/b_cdcl_falsify.py` (P3 grid),
`code/b_dp_prune_depth.py` (P3b). Raw results:
`data/generated/b6_cdcl_grid.jsonl`, `data/generated/b6_prune_depth.json`.
Branch note: work is on the session branch `claude/nice-dijkstra-pukzrv`
(harness-assigned name), not a branch literally named `option-b-solver`.*

## Summary verdict

**PENDING — grid in flight; this section is finalized at the end of the run.**

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

## P3: off-the-shelf CP-SAT falsification grid

**[TO BE FILLED FROM `b6_cdcl_grid.jsonl` WHEN THE RUN COMPLETES —
D ∈ {6,8,10,12,15,20,30,50} × ρ ∈ {0.004, 0.5} × regimes
{ratio10, a10 (N=20k)} × 2 seeds, cap 120 s.]**

Interim signal (foreground probes, recorded before the grid): at ρ = 0.004
with realistic moduli, CP-SAT fails at D = 6–12 (N = 36); at ρ = 0.5 it
solves D ≤ 12 in ≤ 2.4 s. The density-driven separation that A10 measured
for Wagner-4 reappears at micro scale in a CDCL engine.

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
