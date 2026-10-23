# Option (b): a low-density high-dimension subset-product solver — research brief

> **Audit revision, 2026-10-22:** this is an exploratory problem, not a proven
> last remaining escape. The proposed production numbers below are historical
> projections, not a completed harvested-vector instance. See
> [current audit status](integration-review-status.md#current-correctness-audit-2026-10-22)
> for corrected constraints, benchmark definitions and the limits of the evidence.

**For:** a research agent working in a **separate git branch**, with no access
to the conversation that produced this repo. This is an **open problem**, not an
execution plan: the solution is unknown and may not exist efficiently. The goal
is to determine whether a solver exists for the regime below, or to characterize
rigorously why not. Even a clean hardness/no-go result is a valuable outcome.

**TL;DR.** The proposed construction requires a **0/1 subset-product to a
specified target with odd cardinality**. The repository has promising supply
projections and unsuccessful finite heuristic experiments, but no validated
end-to-end production solve and no proof excluding all standard algorithms.
First establish the actual group and vector distribution; then investigate
algorithms, including exploitation of their number-theoretic structure.

---

## 0. Orientation (read, in order)

1. `doc/integration-review-status.md` — current corrections and limitations.
   `data/FINDINGS.md` preserves the historical A4, A6, A10, N1 and A11 observations.
2. `doc/working-paper.tex` — Prop 3.1 (the reduction to subset-product) and the
   group definition G = (Z/Λ₋)* × (Z/Λ₊)*.
3. `doc/registry.md` — the solver menu S1–S7 and the **regression harness**
   (bottom) you will use to test any idea.
4. `doc/a4-solver-analysis.md` — the 2-part/odd-part decomposition.
5. Candidate code to reuse: `code/a8_omega_solver.py`
   (`make_structured` — synthetic instances with forced-zero mixture weight ρ),
   `code/a6_oddsolver.py` (`make_codesigned`, `mitm_frontier` — the exact
   small-scale oracle), `code/a10_wagner_density.py` (the Wagner reach measurement).

---

## 1. The target problem and historical parameter proposal

Given:
- a finite abelian group **G = ⊕_{i=1}^{D} Z/mᵢ**, each mᵢ a prime power; after
  co-design (H7) the primes dividing the mᵢ are **small (≤ 97)**, so components
  share small primes and **log₂|G| ≈ 18,000–24,000 bits** over **D ≈ 1,000–5,000
  components**;
- a **pool** of **N ≈ 2.5×10⁵** vectors vₚ ∈ G (one per harvested prime p);
- a **target** t ∈ G.

Find **x ∈ {0,1}ᴺ** with **Σₚ xₚ vₚ = t** in G and **Σₚ xₚ odd** (a parity
constraint = one extra Z/2 coordinate).

Two structural facts that define the regime:
- **Target reachability needs evidence.** `2ᴺ ≫ |G|` guarantees collisions,
  not coverage of the specified target. Abundant target solutions are a
  distributional expectation, or can be planted for a synthetic test.
- **Forced support is not literal identity density.** Prime divisors of
  `p-1` force zero residues on the minus side; other components can be zero by
  coincidence. Plus-side `p+1` support gives `p=-1`, which is identity only
  in odd-order projections. The proposed `0.004` support fraction does not
  establish `99.6%` nonzero coordinates in the actual group.

Before production use, construct the full lcms, exclude nonunit pool elements,
and include prime powers: `phi(qᵉ)=qᵉ⁻¹(q-1)`. The existing squarefree `q-1`
component models alone do not validate all quoted production dimensions.

The quoted proposal has `N ≈ 10 × log₂|G|`; this is not an asymptotic theorem.
The group is fixed for a fixed factor base and exponent caps, although changing
the harvest design can enlarge it.

---

## 2. Implemented methods and their limitations

- **Exact search (MITM / DP):** exponential in D (or in |G|). Caps at ~15
  components / ~40 bits in the historical experiments. Direct MITM instead
  scales exponentially with N; its code cap and timeout are resource limits,
  not bounds on all exact algorithms.
- **GF(2) linear algebra:** solves the projection onto `G/2G` plus parity.
  Higher 2-powers require residual checks with carries, alongside the odd
  components. The old 16% figure counts the full 2-primary group, not the
  number of solved projection bits. Elimination and carry defects have been
  repaired; the old frontier experiments require reassessment.
- **Generic 0/1 rounding of a linear-algebra solution:** the solution set is a
  lattice coset; rounding to {0,1} is CVP in dimension N ≈ 2.5×10⁵ — out of
  reach for LLL/BKZ without massive dimension reduction.
- **Four-list diagnostic / simplified omega walk:** neither implements the
  full AGHS algorithms. A10's parameter 0.004 means literal zero probability
  0.336 in ternary coordinates; A8 has order-dependent literal probabilities.
  Four-sum outputs have even cardinality, and A8 does not enforce parity.
  Finite first-failure frontiers do not prove a universal density threshold.

The gap is between a proposed real construction and the currently implemented,
limited synthetic solvers. It is not a proved boundary for every known solver.

---

## 3. The open question

> Is there an algorithm that finds a 0/1 subset-sum to a target in G = ⊕ Z/mᵢ
> (D ≈ 10³–10⁴ prime-power components, all primes ≤ 97, log₂|G| ≈ 2×10⁴) given
> N ≈ 2.5×10⁵ **dense** vectors (identity-density ρ ≈ 0.004), running in
> feasible time/space (say ≤ a few core-days, ≤ ~64 GB)?

Success on a well-specified synthetic instance is useful progress, not
validation of the real construction. A negative finite-resource result must be
reported with its model, algorithm and budget, not as a general impossibility.

---

## 4. Candidate directions (ranked; assess each, don't assume)

1. **Exploit the specific algebraic structure of vₚ (most novel, least
   explored — the only angle that can beat generic hardness).** The vectors are
   *not* random: vₚ is the CRT-collected discrete log of p = 2m+1 across the
   components (Z/q)* for factor-base primes q. There may be exploitable relations
   — e.g. between p's dlog base structure, the fixed harvest congruence
   (m ≡ 1 mod 40), and the small shared primes — that a bespoke method uses to
   linearize or decompose the search. This is speculative but is where a real
   opening, if any, lives. Concretely: study whether vₚ lies in a predictable
   coset/subvariety, or whether products of a *structured* family of pool primes
   collapse the target algebraically.
2. **Lattice + aggressive dimension reduction (concrete, testable).** Reduce the
   problem before any lattice step: solve the mod-2 projection by GF(2) (S2) and
   eliminate over each small GF(ℓ) to shrink to a "hard core" of pivot columns;
   then run BKZ on the core coset. **Key measurement:** how small is the core?
   From A4/A6 the odd part has ~thousands of components — likely still far above
   BKZ's ~few-hundred-dimension practical limit. Quantify the core dimension; if
   it is ≲ 200, this could work.
3. **Representation-technique / advanced subset-sum (HGJ, BCJ, dissection).**
   Modern subset-sum solvers beat naive MITM (e.g. 2^{0.29N}). For the *modular,
   high-density, product-of-small-primes* variant the exponent may be smaller.
   Assess whether the effective hard-core dimension after reduction is small
   enough for a 2^{c·core} method to be feasible.
4. **Structured sparse linear algebra + iterated GF(2) (index-calculus style).**
   Factoring's linear algebra (block Lanczos/Wiedemann) handles 10⁶-dimensional
   GF(2) systems. Can a 0/1 solution be assembled by iterating GF(2) relations
   across the odd primes (e.g. "make the product a square, then descend")?
   Assess whether the descent terminates without blowing up.
5. **Relaxation of the exact target (reframing).** Does the construction truly
   need product ≡ target on the *full* lcm Λ, or is there slack (allow n with a
   few pᵢ² factors, i.e. drop squarefree; or a weaker per-prime condition)? A
   relaxation that shrinks |G| or raises effective density could move the regime.
   Note: heavy relaxation edges toward changing the construction — keep it
   honest about what still yields a valid Agrawal counterexample (cf.
   working-paper §2, Prop 3.1).
6. **Algebraic / pseudo-Boolean CDCL (DPLL-style search + linear reasoning).**
   The instance is a system of ~D linear congruences (mod small prime powers)
   in N Boolean variables — a pseudo-Boolean / SMT-over-finite-fields problem,
   NOT clausal SAT (a CNF encoding of a mod-ℓ equation destroys the structure).
   The right tools are CDCL with native linear reasoning: SAT-with-Gaussian-
   elimination (CryptoMiniSat, XOR handling — covers the mod-2 projection),
   pseudo-Boolean / cutting-planes solvers (RoundingSat), or SMT (Z3) with
   modular arithmetic; the concrete idea is CDCL branching + conflict learning
   *on top of* per-prime GF(ℓ) Gaussian elimination as theory propagators — the
   search handling the 0/1 constraint that pure algebra cannot. **Prognosis
   (honest):** the odd part is a *dense random-like linear system mod small
   primes* — the class where CDCL degenerates because propagation does not fire
   until nearly all variables are fixed (the mod-ℓ analog of random k-XOR-SAT
   above threshold, solved by Gaussian elimination not by search), and valid
   solutions have large support (~1300 ones) so the tree is deep. Empirically
   our instances already look random-like (annealing found no gradient; the A10
   Wagner reach matched the uniform-random prediction), which is evidence
   *against* this helping. It has NOT been tried with a real algebraic-CDCL
   solver, so it is unsettled, and it is the natural embodiment of "algebra +
   search" (subsumes dirs 2–4). The upside, if any, comes from the same place
   as dir 1 (instance structure the solver's conflict-learning might exploit)
   and from solution abundance (~2^{N−log|G|} solutions — you need only stumble
   on one). **Falsify fast:** feed a *reduced* synthetic instance
   (`make_structured`, D=50, ρ=0.004) to an off-the-shelf solver — RoundingSat
   or CryptoMiniSat(+XOR) or Z3 — and see if it beats the Wagner reach (Wagner
   reported ~20 there, with a different model and constraint set). If a tuned
   solver fails at D=50, record that model and budget rather than excluding the
   whole direction; if it succeeds, scale toward D=1000 (milestone m3).

Directions 3–4 most likely bottom out in the same hardness; 1 and 2 are where to
spend real effort. Report a go/no-go on each with the measured hard-core
dimension.

---

## 5. Test harness & success criteria

- **Synthetic instances:** `a8_omega_solver.make_structured(r, rho, N, ...)`
  uses forced-zero bias, not literal density. For order mᵢ,
  `P(0)=rho+(1-rho)/mᵢ`; record it for each component. `make_codesigned`
  (a6) matches co-designed component orders but uses uniform, not harvested,
  vectors. Include the odd-cardinality target in every solver/oracle comparison.
- **Oracle:** `mitm_frontier` (a6) checks small pools exactly, including parity;
  use only completed searches as existence/nonexistence evidence. Independently
  verify every returned solution in the original group.
- **Milestones:** try D=50, 200 and 1000 with explicit orders, distribution,
  N, parity, seed and time/memory budgets. A synthetic success must then be
  transferred to actual harvested vectors; a failure remains algorithm- and
  budget-specific.
- **Falsify fast:** for the lattice route (dir 2), first just *measure the
  hard-core dimension* after GF(2)+GF(ℓ) reduction on a real-scale synthetic
  instance. If it is ≫ 500, dir 2 is dead without running any BKZ — report and
  move on.

---

## 6. Scope, hygiene, definition of done

- Work on branch `option-b-solver`. Add files under `code/` prefixed `b_*` and a
  writeup `doc/option-b-findings.md`. **Do not modify** existing `code/`,
  `data/FINDINGS.md`, `PLAN.md`, `doc/registry.md`, or the working-paper — those
  are live on `main`. Commit to the branch; do not push to main / open a PR
  unless asked. Use the repo's Co-Authored-By trailer.
- **Done =** a `doc/option-b-findings.md` reporting, per direction: what was
  tried, the measured hard-core dimension / reach, the milestone reached (m1–m3
  or none), and a budget-specific outcome. Plus any solver code that passes
  independent small-instance checks. If nothing crosses m1, list precisely
  the algorithms, models and budgets tested; do not claim all paradigms were
  implemented or ruled out.

## 7. Honest expectation

Low-density, high-dimension 0/1 subset-sum with a merely-linear pool is a regime
where no efficient general algorithm is known, and directions 3–4 likely confirm
that. The realistic hope rests on direction 1 (our vectors are structured, not
random) and on direction 2 turning out to have a small hard core. Treat a
rigorous no-go as a success, not a failure — it completes the negative result.


**Historical A12 experiment:** finite-budget synthetic greedy filtering was
tested, not an unrestricted number-theoretic pricing oracle. The original
reported minimum actually tracked end-of-restart deficits; that defect has
been corrected. Reassessment is warranted. Its failure does not exclude all
adaptive or column-generation methods.
