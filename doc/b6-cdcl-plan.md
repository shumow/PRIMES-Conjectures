# B6 execution plan: algebraic / pseudo-Boolean CDCL on the odd-part subset-sum

*2026-09-01. Executes direction 6 of `doc/option-b-problem.md` (added on main,
commit 7a44624): frame the solver instance as pseudo-Boolean / SMT-over-finite-
fields and falsify fast with off-the-shelf algebraic-CDCL solvers before any
bespoke build. This plan follows the option-b brief's hygiene (new files under
`code/` prefixed `b_*`; results written to `doc/option-b-findings.md`; no
modification of existing code, FINDINGS.md, PLAN.md, or registry.md), with one
deviation: work happens on this session's assigned branch
`claude/nice-dijkstra-pukzrv` rather than a branch literally named
`option-b-solver` — the branch name is harness-assigned and has no content
meaning.*

## 0. What the brief asks, restated as testable questions

The instance: N Boolean variables, D linear congruences mod small odd prime
powers (dense random-like coefficients, identity-density ρ ≈ 0.004), one
parity row, solutions super-abundant (2^N ≫ |G|). The brief's own prognosis is
that this is the CDCL-killer class (propagation fires only when nearly all
variables are fixed; deep trees; the mod-ℓ analogue of random XOR-SAT above
threshold) — but it has never been tried with a solver that has *native linear
reasoning*, so it is unsettled. Questions, in falsification order:

- **Q1.** Does any off-the-shelf solver with native linear/PB reasoning solve
  a faithful reduced instance (D = 50, ρ = 0.004) in reasonable time — i.e.
  beat the measured Wagner-4 reach of ~20 components (FINDINGS A10)?
- **Q2.** If yes: what is the time-vs-D scaling curve — polynomial-ish
  (a real opening, push to m2/m3: D = 200, D = 1000) or exponential with a
  small base (a curiosity that dies by D ≈ 100)?
- **Q3.** Only if Q2 looks favorable: does a bespoke CDCL-with-GF(ℓ)-theory-
  propagators build improve the exponent?

A clean "no" on Q1 is a valid and useful outcome: it converts direction 6 from
"untried" to "tried and dead without a bespoke build," per the brief's
definition of done.

## P0. Tooling — DONE (this session)

Verified available in this environment (recorded so runs are reproducible):

- **OR-tools CP-SAT 9.15.6755** (`pip install ortools`) — primary solver:
  CDCL-style clause learning over integer linear constraints + strong
  presolve; handles the mod-ℓ constraints via slack-variable equalities.
- **Z3 5.1.0** (`pip install z3-solver`) — secondary: SMT with linear integer
  arithmetic and native `%`; different reasoning engine, useful as a check
  that a stall is regime-driven, not solver-specific.
- **python-sat 1.9** — CNF solvers (Cadical etc.) for the optional clausal
  negative control only.
- **Smoke test passed:** both CP-SAT and Z3 solved and *verified* a toy
  instance (N = 30, D = 4, moduli {3,5,7,11}, odd-cardinality row); CP-SAT
  found a support-9 solution, Z3 a support-7 one (scratchpad `smoke.py`;
  encoding pattern below).
- **RoundingSat** (native PB/cutting-planes) is *not* installed — needs a
  source build. Deferred: build it only if CP-SAT/Z3 results at D = 30–50 are
  ambiguous enough that cutting-planes-specific reasoning could tip the
  verdict (decision point after P3).

## P1. Instance + encoding module (`code/b_cdcl_instances.py`)

Build one module that produces solver-ready instances from the brief's own
harness (imports, does not modify, `a8_omega_solver.make_structured` and
`a6_oddsolver.make_codesigned` / `mitm_frontier`):

1. **Instance sources.**
   - `make_structured(r=D, rho, N, planted_k, rng)` — tunable-ρ synthetic,
     odd-prime cyclic components ≤ 97, planted odd-cardinality solution.
     This is the falsification workhorse (matches brief §5).
   - `make_codesigned(...)` — faithful prime-power components from real q−1
     factorizations; used at the confirmation points only.
2. **Sizing policy.** Two pool regimes per D, because "reasonable N" is
   contested territory:
   - *ratio-10*: N ≈ 10 × Σ log₂ℓ_j (matches the real pool/demand ≈ 10;
     e.g. D = 50 ⇒ demand ≈ 260 bits ⇒ N ≈ 2,600);
   - *A10-match*: N = 20,000 (the pool A10's Wagner reach was measured at,
     for apples-to-apples comparison).
3. **Planting policy (honesty about the known pitfall).** A small planted
   support is statistically visible and could flatter search. Default
   `planted_k` ≈ N/2 (odd), which makes the planted subset statistically
   indistinguishable from the abundant organic solutions; additionally run a
   *small-support* variant (planted_k ≈ demand-bits-sized, ~the realistic
   ~1,300-support shape scaled down) to check sensitivity. Report both.
4. **Encodings.**
   - **E1 CP-SAT (primary):** per component j:
     `Σ_i c_ij·x_i == t_j + ℓ_j·s_j`, `s_j ∈ [0, Σ_i c_ij / ℓ_j]`; parity as
     `Σ x_i == 1 + 2·s_par`. (Also try `AddModuloEquality` where available;
     keep whichever presolves better.)
   - **E2 Z3:** 0/1 Ints, `Sum(c·x) % ℓ == t`, parity likewise; tactics:
     default and `qflia`; 0/1 `BitVec` variant if Int stalls in presolve.
   - **E3 CNF negative control (optional, D ≤ 20 only):** adder-tree
     encoding via python-sat, expected to be dominated — included only to
     document that the *clausal* route fails for encoding reasons, separating
     "CNF blowup" from "search hardness."
5. **Verification.** Every SAT answer re-checked by `a8_omega_solver.verify`
   (or the local equivalent) — solver output is never trusted raw. UNSAT/
   UNKNOWN answers on planted instances are, by construction, solver failures
   (the instance is satisfiable) — that is the signal we are measuring.

## P2. Oracle cross-validation (gate before any conclusions)

On 20 seeded instances at D ≤ 12, N ≤ 40: CP-SAT, Z3, and the exact
`mitm_frontier` oracle must all find (possibly different) valid solutions, and
all solutions must verify. **Gate G-b6-0:** 20/20 agreement. This separates
encoding bugs from search hardness before the ladder runs — the same
bug-vs-infeasibility discipline as gate G3 in PLAN.md.

## P3. The falsification ladder (the experiment)

Grid, run by `code/b_cdcl_falsify.py`, results to
`data/generated/b6_cdcl_grid.json`:

| axis | values |
|---|---|
| ρ | 0.004 (the real regime), 0.5 (sanity: easier regime for context) |
| D | 20, 30, 40, 50, 75, 100 |
| N | ratio-10, and 20,000 (A10-match) |
| solver | CP-SAT (8 workers), Z3 (default + qflia) |
| seeds | 3 per cell |
| caps | 1 h wall-clock, 16 GB per run; CP-SAT progress logged |

Reference lines against which every cell is judged:
- **Wagner-4 reach** (FINDINGS A10): ~20 components at ρ = 0.004, N = 20k.
- **Exact-method frontier** (FINDINGS A6): ~15 components.

Also record, per run: conflicts, restarts, best bound / phase progress at
timeout — so a stall is characterized ("propagation never fired" vs "slow
steady progress"), which determines whether P5 has any basis.

**Ordering:** run D = 20 and D = 30 first at both ρ values (fast cells,
immediate sanity + context), then D = 50 at ρ = 0.004 (the decision cell),
then the rest of the curve only as needed to fit the scaling shape.

## P3b. Davis–Putnam-style pruning, made explicit and measured

Direction 6 originated as a question about **Davis–Putnam-like search-space
pruning, generalized beyond clausal SAT**. "Davis–Putnam" names three distinct
algorithmic ideas; this plan must treat each on its own terms rather than
letting "CDCL" stand in for all of them:

1. **DP-1960: variable *elimination*** (resolve a variable away; clauses →
   resolvents). Its non-clausal generalizations are Fourier–Motzkin for
   linear arithmetic, Gaussian elimination for fields, and **bucket
   elimination / adaptive consistency** (Dechter) for general constraint
   networks, whose cost is exponential in the constraint graph's induced
   width (treewidth). **Assessment — closed by density, no experiment
   needed:** our vectors are nonzero on ~99.6% of components (ρ ≈ 0.004), so
   every constraint touches essentially every variable; the constraint
   hypergraph is effectively complete and its induced width is ~N. Bucket
   elimination degenerates to full enumeration; there is no elimination
   ordering to exploit. (Per-prime Gaussian elimination — the field face of
   DP elimination — is already in the plan; it is exactly what leaves the
   0/1 coupling as the residual hard part, FINDINGS A4.)
2. **DPLL-1962: branch + propagate + prune.** This is what P3's engines
   embody: CP-SAT and Z3 are industrial descendants (branching, bounds/
   arc-consistency propagation, conflict learning = learned pruning). The
   *pure-literal rule* has no analogue here (modular equalities have no
   satisfying direction/monotonicity), and LP-relaxation bounding — the
   branch-and-bound face of pruning — is vacuous for modular equalities
   (the slack-variable LP relaxation is feasible almost everywhere). So the
   only pruning with any possible teeth is:
3. **DPLL(T): branch + *theory-level* pruning** — the modern name for
   "Davis–Putnam generalized." For this instance the sound theory-pruning
   rules are:
   - **R1 (per-prime rank feasibility):** after a partial assignment, check
     each residual GF(ℓ) linear system *with the 0/1 restriction dropped*;
     if any is infeasible even as a linear system, prune. Cheap
     (incremental elimination), sound, and exactly the propagator direction
     6 proposes.
   - **R2 (residual 2-part solvability):** the GF(2)+parity system must
     remain solvable over the unassigned variables (S2 machinery, sound).
   - **R3 (counting heuristic, unsound but informative):** prune when the
     expected completion count 2^(#unassigned) / |residual group| falls
     below ~1 (the equidistribution heuristic; Knuth-style tree estimation).

   **The quantitative worry — and the measurement that settles it:** sound
   rules R1/R2 only fire once the residual system becomes *overdetermined*,
   i.e. at assignment depth ≈ N − O(demand); with solutions super-abundant,
   almost every shallow partial assignment is extendable, so the tree is
   effectively unpruned to enormous depth. That is the DP-framed restatement
   of the brief's "propagation fires late" prognosis — currently an
   argument, not a number.

**Experiment (new, `code/b_dp_prune_depth.py`, ~half a day):** a minimal
hand-rolled DPLL over `make_structured` instances (D = 20–50, both ρ, both N
regimes) instrumented to measure the **prune-fire depth profile**: for each
rule R1/R2/R3, at what assignment depth does it first refute a random branch,
and what fraction of branches does it cut at each depth. Deliverables: the
depth profile curves alongside the P3 grid. Interpretation:
- fire-depth ≈ N − O(demand-bits) and negligible shallow cuts → DP-style
  pruning is *measured* dead in this regime (and mechanistically explains
  any CP-SAT/Z3 stall in P3);
- material shallow pruning (would be a surprise — the one plausible source
  is instance structure à la brief direction 1) → feeds directly into the
  P5 bespoke DPLL(GF(ℓ)) propagator design, with R1's increment cost known.

This experiment is worth running even if P3's off-the-shelf runs stall
early, because it answers the *why* at the level direction 6 was actually
posed: not "did solver X time out," but "does generalized DP pruning have
any leverage on this instance class."

## P4. Decision gates

- **G-b6-1 (= milestone m1 of the brief):** some solver solves D = 50 at
  ρ = 0.004 within the caps, verified. 
  - **Pass →** P5.
  - **Fail →** direction 6 is dead without a bespoke build. Write the
    go/no-go into `doc/option-b-findings.md` (create it, per the brief §6):
    the measured stall frontier vs the Wagner reach, the stall
    characterization, the P3b prune-fire depth profiles (the mechanistic
    "why"), both N regimes, both planting policies, and the explicit
    statement that RoundingSat/cutting-planes remains the one untried
    off-the-shelf engine (with the build cost). Recommend whether
    that residual is worth a build (expected: no, unless CP-SAT showed
    partial progress that cutting planes plausibly completes).
- **G-b6-2 (= m2):** D = 200 at ρ = 0.004 within caps, N scaled accordingly.
- **G-b6-3 (= m3):** D = 1000 — per the brief, hitting this reopens the
  entire construction (re-attempt G3 on real co-designed instances via
  `make_codesigned`, then escalate to PLAN.md's A3 question).

## P5. Conditional escalation (only past G-b6-1)

1. Fit the time-vs-D curve at ρ = 0.004; extrapolate to D = 1000. If the
   exponent kills m3, report "solves the toy, not the problem" honestly and
   stop — do not tune toward a foregone conclusion.
2. If scaling is ambiguous: build RoundingSat (source, cmake) and re-run the
   ladder with native PB; try CP-SAT parameter sweeps (linearization level,
   symmetry, no-presolve variants) — bounded to ~one day.
3. Only with a surviving favorable curve: spec the bespoke
   CDCL + GF(ℓ)-elimination-as-theory-propagator prototype (the brief's core
   idea — search handles 0/1, per-prime Gaussian elimination handles the
   algebra, conflict learning bridges). That is a multi-session build and
   gets its own plan; it is *not* started on spec.

## Cost, risks, and honesty notes

- **Cost:** P1+P2 ≈ half a day; P3 ≈ overnight (worst case ~72 solver-hours
  across the grid, embarrassingly parallel across cells); P3b ≈ half a day. All trivially
  cheap next to a production harvest.
- **Prior (stated before running, so the result can be scored against it):**
  the brief's own prognosis, the A6 annealing null, and the A10
  uniform-random match predict a stall at D ≈ 20–40, i.e. G-b6-1 fails —
  I put ~10–15% on m1 passing, most of that mass on CP-SAT's presolve
  finding structure in the *ratio-10* (small-N) cells that does not survive
  to A10-match cells. The experiment is still worth its day: it is the
  cheapest remaining way to either kill direction 6 with a measurement or be
  surprised, and "tried with the right tool class and measured" is what the
  negative paper needs to claim the direction was exhausted.
- **Known confounds controlled for:** planted-support visibility (two
  planting policies); pool-size choice (two N regimes); solver-specificity
  (two engines, different architectures); encoding artifacts (oracle gate
  P2, CNF control E3); toy-scale presolve tricks (scaling curve required,
  single-point success is not a pass).
- **Out of scope here:** the A12 double-condition frontier measurement and
  the R2 hard-core-dimension measurement from
  `doc/solver-directions-review.md` — independent directions, unaffected by
  this plan; B6 neither blocks nor depends on them.
