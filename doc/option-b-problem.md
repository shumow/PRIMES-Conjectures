# Option (b): a low-density high-dimension subset-product solver — research brief

**For:** a research agent working in a **separate git branch**, with no access
to the conversation that produced this repo. This is an **open problem**, not an
execution plan: the solution is unknown and may not exist efficiently. The goal
is to determine whether a solver exists for the regime below, or to characterize
rigorously why not. Even a clean hardness/no-go result is a valuable outcome.

**TL;DR.** The twin-smooth / Lenstra–Pomerance route to an Agrawal-conjecture
counterexample is blocked at exactly one step: solving a **0/1 subset-product =
target in a high-dimensional abelian group of small smooth exponent, in the
low-identity-density (dense-vector) regime, with a pool only ~linearly larger
than log₂|G|.** Every standard method has been tried and quantifiably fails
(details below). Option (b) asks: is there any algorithm — likely one that
exploits the *specific algebraic structure* of our vectors — that solves it?

---

## 0. Orientation (read, in order)

1. `data/FINDINGS.md` — the measurement record; the sections **A4, A6, A10, N1,
   A11** define the walls. Single source of truth for all numbers.
2. `doc/working-paper.tex` — Prop 3.1 (the reduction to subset-product) and the
   group definition G = (Z/Λ₋)* × (Z/Λ₊)*.
3. `doc/registry.md` — the solver menu S1–S7 and the **regression harness**
   (bottom) you will use to test any idea.
4. `doc/a4-solver-analysis.md` — the 2-part/odd-part decomposition.
5. Code you will reuse (do not modify): `code/a8_omega_solver.py`
   (`make_structured` — synthetic instances with tunable density ρ),
   `code/a6_oddsolver.py` (`make_codesigned`, `mitm_frontier` — the exact
   small-scale oracle), `code/a10_wagner_density.py` (the Wagner reach measurement).

---

## 1. The exact problem

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
- **Existence is free.** 2ᴺ ≫ |G| (N ≈ 2.5×10⁵ ≫ log₂|G| ≈ 24k), so solutions
  are super-abundant by pigeonhole. The difficulty is *finding* one.
- **Vectors are dense (low identity-density).** Each vₚ is the discrete-log
  image of p = 2m+1 (m a product of ~4 medium primes); p ≡ 1 (identity, i.e.
  vₚ = 0) on only ~4 of the D components. So **identity-density ρ ≈ 0.004** —
  vₚ is nonzero on ~99.6% of coordinates.

The pool/dimension ratio is **only ~linear**: N ≈ 10 × log₂|G|. We cannot make
it exponentially larger — harvesting more primes grows N and |G| together
(N1/A11), so the ratio stays ~constant.

---

## 2. Why it is hard — the walls already measured (do not re-derive)

- **Exact search (MITM / DP):** exponential in D (or in |G|). Caps at ~15
  components / ~40 bits (`mitm_frontier`, FINDINGS A6/A10). Our D ≈ thousands.
- **GF(2) linear algebra:** solves the 2-torsion part *exactly and at full
  scale*, but that is only **~16% of the bits**; the odd part (~84%) is the
  wall (FINDINGS A4). The obstruction is that x∈{0,1} makes the mod-ℓ (ℓ odd)
  constraints non-linear in the GF(2) solution kernel — the NP-hard core.
- **Generic 0/1 rounding of a linear-algebra solution:** the solution set is a
  lattice coset; rounding to {0,1} is CVP in dimension N ≈ 2.5×10⁵ — out of
  reach for LLL/BKZ without massive dimension reduction.
- **Wagner / AGHS generalized birthday (the scalable subset-product method):**
  measured reach **r_max ≈ O(log N)/(1−ρ)** (FINDINGS A10). At ρ ≈ 0.004 it
  solves ~20 components; it would need **ρ ≳ 0.98** to reach thousand-component
  groups. Raising ρ needs the divisor-paradigm pool (H8), which is
  **unharvestable** under the double condition (N1). And **no modulus r** avoids
  the double condition that forces low ρ (A11).

So: the harvestable pools are low-density, and every known solver needs either
exponential resources or high density. That is the precise gap option (b) must
cross.

---

## 3. The open question

> Is there an algorithm that finds a 0/1 subset-sum to a target in G = ⊕ Z/mᵢ
> (D ≈ 10³–10⁴ prime-power components, all primes ≤ 97, log₂|G| ≈ 2×10⁴) given
> N ≈ 2.5×10⁵ **dense** vectors (identity-density ρ ≈ 0.004), running in
> feasible time/space (say ≤ a few core-days, ≤ ~64 GB)?

A "yes" (with a working implementation that passes the harness at D ≈ 1000,
ρ ≈ 0.004) reopens the entire construction. A rigorous "no / conditional-no"
is the honest close of the last live direction.

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
   problem before any lattice step: solve the 2-part exactly by GF(2) (S2) and
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

Directions 3–4 most likely bottom out in the same hardness; 1 and 2 are where to
spend real effort. Report a go/no-go on each with the measured hard-core
dimension.

---

## 5. Test harness & success criteria

- **Synthetic instances:** `a8_omega_solver.make_structured(r, rho, N, ...)`
  gives a group with tunable density ρ and a planted solution; sweep ρ from
  0.5 down to **0.004** and D up from 20 toward **1000**. `make_codesigned`
  (a6) gives faithful small-prime instances.
- **Oracle:** `mitm_frontier` (a6) solves small instances exactly — use it to
  confirm your solver's answers on D ≤ ~15 before scaling.
- **Milestones:** (m1) beat the Wagner reach — solve ρ=0.004 at D=50 (Wagner
  caps ~20); (m2) D=200 at ρ=0.004; (m3) D=1000 at ρ=0.004. Hitting **m3**
  reopens the construction. Failing m1 after honest effort strongly corroborates
  the wall.
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
  or none), and a clear go/no-go. Plus any solver code that passes the oracle on
  small instances. If nothing crosses m1, state that plainly — it converts the
  option-(d) negative result from "no known solver" to "no solver despite a
  dedicated search across five paradigms."

## 7. Honest expectation

Low-density, high-dimension 0/1 subset-sum with a merely-linear pool is a regime
where no efficient general algorithm is known, and directions 3–4 likely confirm
that. The realistic hope rests on direction 1 (our vectors are structured, not
random) and on direction 2 turning out to have a small hard core. Treat a
rigorous no-go as a success, not a failure — it completes the negative result.
