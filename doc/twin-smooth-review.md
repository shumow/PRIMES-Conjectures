# The Twin-Smooth Literature and What Transfers to the Agrawal Hunt

*Review of the Costello–Naehrig-et-al. line of work on twin smooth integers
(2020–2025), assessed against the needs of our Lenstra–Pomerance counterexample
construction (see PLAN.md, doc/background.tex). Compiled 2026-08-06.*

## Why this literature is on-point

Our Phase 1 pool is
P = { p : p ≡ 3 (mod 80), (p−1)/2 Q₋-smooth, (p+1)/4 Q₊-smooth }.
Writing p = 2m + 1, membership in P (ignoring the congruence/coloring refinements)
says **m and m+1 are both smooth** — i.e., p comes from a *twin smooth pair with
prime sum*, which is *verbatim* the object the isogeny-crypto community spent
2020–2025 mass-producing for B-SIDH and SQIsign parameter hunts. Even the
prime-sum filter is theirs: SQIsign wants twins (m, m+1) with m + (m+1) = 2m+1
prime. Our extra requirements — m ≡ 1 (mod 40), and the global side-disjointness
("coloring") across the pool — are refinements *on top of their datasets*.

Check on the congruence: m ≡ 1 (mod 40) ⟺ p = 2m+1 ≡ 3 (mod 80), and it implies
m odd (v₂(p−1) = 1), m+1 ≡ 2 (mod 4) (v₂(p+1) = 2), and 5 ∤ m(m+1). So exactly a
1/40 congruence slice of any twin-smooth dataset survives to become pool
candidates, before the primality and coloring filters.

## The corpus

1. **Costello, "B-SIDH: supersingular isogeny Diffie–Hellman using twisted
   torsion" (ASIACRYPT 2020).** Origin of the demand for primes with p²−1 = 
   (p−1)(p+1) smooth; first searches (incl. an XGCD/lattice method over
   smooth-split polynomial pairs).
2. **Costello–Meyer–Naehrig, "Sieving for twin smooth integers with solutions to
   the Prouhet–Tarry–Escott problem" (EUROCRYPT 2021; ePrint 2020/1283).**
   PTE solutions give degree-n polynomial pairs a(x), b(x) = a(x) + C splitting
   into linear factors; a(ℓ)/C, b(ℓ)/C are twins with n forced factors each.
   Results: 240–256-bit primes p with p±1 both 2¹⁵-smooth; 384-bit at 2²²;
   512-bit at 2²⁸.
3. **Bruno, Corte-Real Santos, Costello, Eriksen, Meyer, Naehrig, Sterner,
   "Cryptographic smooth neighbors" (ASIACRYPT 2023; ePrint 2022/1439).**
   Optimized Conrey–Holmström–McLaughlin (CHM) iteration. Headline data:
   **B = 547 yields 82,026,426 twin smooth pairs** (near-complete set; largest
   122 bits); constant-range variant gives 57× speedup keeping 93 of the top 100
   twins. Boosting: evaluate pₙ(x) = 2xⁿ − 1 at twin-smooth x to reach
   cryptographic sizes (n ∈ {2,3,4,6}). **Code is public** (Microsoft repo).
4. **Buzek, Hasan, Liu, Naehrig, Vigil, "Finding twin smooth integers by solving
   Pell equations" (arXiv:2211.04315).** Størmer's theorem: for fixed B the set
   of twin B-smooths is **finite**, computable by solving Pell equations
   x² − 2Dy² = 1 over squarefree B-smooth D. Full sets computed for small B;
   interval-targeted navigation of Pell solutions for larger B.
5. **Sterner, "Towards optimally small smoothness bounds for cryptographic-sized
   smooth twins..." (SAC 2024; ePrint 2023/1576).** PTE-style pairs allowing a
   few quadratic factors; better smoothness bounds at 384/512 bits.
6. **Mulder, Sterner, van Woerden, "Large smooth twins from short lattice
   vectors" (ANTS XVII).** SVP in a Schnorr-style prime-number lattice finds the
   *largest* twin for a given B. Status of completeness: provable for
   **B ≤ 100**, heuristic to **B ≤ 113**; records: 196-bit twin at B = 751,
   213-bit at B = 997. Includes an estimator for the largest B-smooth twin.
7. Background: Conrey–Holmström–McLaughlin, "Smooth neighbors" (Exp. Math.
   2013); Størmer (1897); Lehmer (1964); Corte-Real Santos et al., "Finding
   practical parameters for isogeny-based cryptography" (CiC 2024).

## Applicability matrix

| Their asset | Their goal | Our use | Verdict |
|---|---|---|---|
| CHM algorithm + public code + B=547 dataset (82M pairs) | few huge twins, small B | **raw pool supply**: 1/40 congruence slice × prime-sum filter on *existing data* | **Direct reuse — Phase 1 can start on their data before we write a harvester** |
| Prime-sum twin filters (SQIsign) | p = 2m+1 prime | identical filter | direct reuse |
| Størmer/Pell complete sets (B ≤ 113) | records | **ground truth** to calibrate our density + coloring models exactly | direct reuse (calibration) |
| SVP largest-twin estimator (ANTS) | records | upper envelope of pool size distribution per B | useful analytics |
| PTE sieving | 240–512-bit twins | scaling option if we ever need big pool elements; forced-factor structure may help coloring | keep in reserve |
| Boosting pₙ(x) = 2xⁿ−1 | reach crypto sizes | **structurally side-separating** (see below) but **incompatible with mod-80 as stated** | blocked on a Phase-0 theory question |
| XGCD polynomial pairs | B-SIDH params | same repurposing potential as PTE | reserve |

## Three load-bearing observations

**1. Phase 1 collapses to data analysis.** The CHM B=547 set has ~82M pairs;
filtering m ≡ 1 (mod 40) (÷40) and 2m+1 prime (÷ln p) leaves an estimated
**10⁴–10⁵ raw pool candidates already computed by someone else**. Meanwhile
bits(Λ₋) + bits(Λ₊) over a 100-prime universe (odd primes ≤ 547, exponents
capped by what the pool actually uses) is plausibly a few thousand bits. So the
feasibility inequality |P| ≳ bits(G) is *within an order of magnitude on
existing data*, and everything hinges on the **coloring tax**: each pool element
consumes ω((p−1)/2) + ω((p+1)/4) prime-side assignments from a universe of only
~100 odd primes, and all elements must agree on a single partition Q₋ ⊔ Q₊.
Small pairs (the bulk of CHM output) have few factors each — the tax is
smallest exactly where the supply is thickest. Measuring the maximum consistent
subpool over colorings (greedy/annealing/ILP on the CHM data) is now the *entire*
go/no-go computation, and it requires no new number-theoretic software.

**2. Their boosting polynomials are natively side-separating — if Phase 0
cooperates.** For p = 2x² − 1: (p+1)/2 = x² and (p−1)/2 = (x−1)(x+1), and
gcd(x, x±1) = 1 means the plus-side and minus-side prime supports are
**automatically disjoint within each element** — the very constraint
(side-coprimality lemma) that makes our pool expensive. Better: the two-sided
smoothness condition moves to (x, x²−1) at **half the bit-size**, where Dickman
is far kinder. However, as stated the L–P theorem demands p ≡ 3 (mod 80), and
one checks 2x² − 1 ≡ 3 (mod 16) and x² ≡ 2 (mod 5) are both unsolvable — n = 2
boosting can *never* satisfy L–P's local conditions; n = 3 fails the 2-adic
condition similarly (v₂(p+1) = 1 + 3v₂(x) ≠ 2). **New Phase-0 task, high
value:** re-derive the theorem and map the full set of admissible local
conditions (which residues mod 2^k and mod 5, which v₂ patterns, possibly
uniform over the pool rather than the specific mod-80 cell). Váňa's ρ(p) |
10(p²−1) framework suggests mod-80 is one convenient cell of a larger space. If
any admissible cell is boost-reachable, the search gets dramatically easier.

**3. Størmer finiteness caps the naive design.** For fixed B, twin B-smooths
are finitely many — so for a fixed factor-base budget the supply curve
saturates, and the only levers are B (grows bits(G) ~ linearly in π(B)) and
coloring efficiency. The known complete sets (B ≤ 113) let us compute the
*exact* supply and exact coloring optimum at small scale and extrapolate with
confidence before committing CPU to B in the 500–5000 range.

## What none of their work covers (our novel ground)

- The **global** side-disjointness constraint across a pool (their elements are
  used one at a time; ours must be multiplicatively combined).
- The subset-product / 0/1-linear-algebra stage (Pohlig–Hellman + staged CRT /
  Wagner) — from the Carmichael-construction literature (Löh–Niebuhr), not the
  isogeny literature.
- The mod-80 (or generalized) congruence refinement.

## Concrete next actions (feeds PLAN.md Phase 1)

1. Clone the CHM implementation; regenerate or obtain the B = 547 dataset
   (verify the 82M figure and size distribution).
2. Slice: m ≡ 1 (mod 40), 2m+1 prime (BPSW). Record survivor counts vs size.
3. Compute per-survivor factor signatures; run coloring optimization for the
   max consistent subpool; compare against realized bits(Λ₋) + bits(Λ₊).
   This single number decides go/no-go for the direct (unboosted) route.
4. In parallel (Phase 0): re-derive L–P admissible local conditions; determine
   whether any boost-compatible cell exists.
5. Calibrate the density model against the complete Størmer sets (B ≤ 113).
