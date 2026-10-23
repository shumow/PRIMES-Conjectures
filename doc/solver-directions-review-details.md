# Solver-directions review: claim-by-claim details, derivations, and provenance

*2026-08-24. Companion to `doc/solver-directions-review.md` (the assessments)
and `doc/solver-review-overview.md` (the narrative). This document exists so
that no claim in the review has to be taken on faith: every statement is
classified by provenance, every derivation is shown, and every number that
came from a source I could not fully read is flagged with what a full read
must confirm.*

## Provenance tiers used throughout

- **[A]** Measured in this repo; the number appears in a dated section of
  `data/FINDINGS.md` (single source of truth).
- **[B]** Established literature; the statement is standard and checkable in
  the cited source.
- **[C]** My derivation from [A]/[B] inputs. The arithmetic is written out
  here; if an assumption is heuristic, it is named.
- **[D]** ⚠ Taken from an abstract, review, talk slide, or search snippet —
  **not** from the paper's full text. The environment's egress proxy blocked
  PDF retrieval from arxiv.org, eprint.iacr.org, journal sites, and university
  hosts (verified failures logged in §12). Each [D] item lists what to verify.

---

## 1. The problem instance (all [A])

From FINDINGS A2 (frozen spec), A4, A5, N1, A10:

| Quantity | Value | FINDINGS section |
|---|---|---|
| Pool size N | ~2.5×10⁵ | A2 (frozen spec projection) |
| Demand (bits of \|G\|) | ~18,117 (frozen spec); 18–24k across specs | A2, A4, A5 |
| Components D | ~4,586 (B=1259 spec); 10³–10⁴ range | A4 table |
| 2-part share | ~16% of bits; GF(2)-solvable at full scale | A4 |
| Odd primes ℓ in G (co-designed) | 24 distinct, all ≤ 97 | A5 |
| Identity-density ρ of pool vectors | ≈ 0.003–0.008 | N1 |
| Wagner-4 reach law | r_max ≈ O(log N)/(1−ρ); ρ ≳ 0.98 needed for 10³ comps | A10 |
| Exact/heuristic solver frontier | ~15 odd components / ~40 odd bits | A6 |

Derived constants used repeatedly below [C]:
- log₂N = log₂(2.5×10⁵) = **17.93**
- (log₂N)² ≈ **321**  (log₂N)³ ≈ **5,765**
- Knapsack-style density (variables per constraint-bit): N / 18,117 ≈ **13.8**

---

## 2. The NPP / symmetric-binary-perceptron hardness mapping

### 2.1 What the cited results say

- **Number Partitioning Problem (NPP):** given a₁…a_N i.i.d. Gaussian (or
  random n-bit integers), find x ∈ {±1}^N minimizing |Σxᵢaᵢ|. Statistical
  optimum Θ(√N·2^−N); best known polynomial algorithm is Karmarkar–Karp
  differencing, reaching 2^−Θ(log²N). Both facts are classical [B]
  (Karmarkar–Karp 1982; Boettcher–Mertens statistical mechanics literature).
- **Gamarnik–Kızıldağ**, *Algorithmic obstructions in the random number
  partitioning problem*, Ann. Appl. Prob. 33 (2023); arXiv:2103.01369 [B for
  the headline, D for fine print]: NPP exhibits the **Overlap Gap Property
  (OGP)** in the regime between 2^−Θ(log²N) and the statistical optimum; OGP
  is a proven obstruction for *stable* algorithm classes (gradient descent,
  approximate message passing, Langevin/annealing dynamics run for bounded
  time). ⚠ Verify: the exact algorithm classes covered, and the exact
  discrepancy range where OGP is established.
- **Vafa–Vaikuntanathan**, *Symmetric Perceptrons, Number Partitioning and
  Lattices*, STOC 2025; arXiv:2501.16517, ePrint 2025/130 [D]: any
  polynomial-time algorithm achieving discrepancy 2^−Ω(log³N) for NPP would
  give a polynomial-time algorithm for worst-case approximate SVP to within
  subexponential factors (a standard lattice assumption says this is hard);
  KK is therefore nearly optimal, and the analogous tightness holds for the
  symmetric binary perceptron (SBP) against the Bansal–Spencer bound,
  resolving a conjecture of Gamarnik–Kızıldağ–Perkins–Xu. ⚠ Verify: the exact
  exponent in "log³", the precise lattice assumption (approximation factor,
  subexponential time), and whether the hardness covers *search* at our
  parameter shape or decision variants.
- **SBP structure** (Abbe–Li–Sly; Perkins–Xu; Gamarnik–Kızıldağ–Perkins–Xu,
  arXiv:2203.15667) [B/D]: at all constraint densities, almost all SBP
  solutions are isolated "frozen" singletons; polynomial algorithms
  (Kim–Roche, Bansal–Spencer) nevertheless exist at low densities and find
  atypical, clustered solutions. Relevance: explains *mechanistically* why
  annealing on a frozen landscape (our A6/S3) fails, and why solution
  abundance ("existence is free," option-b brief §1) does not imply
  findability.

### 2.2 The arithmetic that places our instance [C]

Treat each odd prime-power component of G as a constraint "the ±/0-1
combination of N numbers lands in a prescribed residue class mod ℓ^a." Jointly
these force the subset-sum image into a set of relative size 2^−18,117 of the
ambient group — an exact multi-modular analogue of demanding NPP discrepancy
2^−18,117·(scale). Compare:

- what polynomial algorithms achieve in the Gaussian model: ~log²N ≈ **321
  bits** of discrepancy;
- where lattice-conditional hardness begins (VV25): ~log³N ≈ **5,765 bits**;
- what we need: **~18,117 bits** — 3.1× past the hardness threshold, 56× past
  the algorithmic bound.

Interpretation: even granting an algorithm at the *edge of the conditionally
impossible* (log³), we would still be an order of magnitude short. Our A10
measurement (Wagner-4 reaches ~20–24 of thousands of components at ρ=0.004,
growing only logarithmically in N) is the in-repo, multi-modular face of the
same phenomenon: KK differencing *is* the repeated 2-list birthday, and its
log²N reach is the h→log N limit of the k-tree bound.

### 2.3 Why this is an analogy, not a theorem about our instance [C]

Five modeling gaps, none of which is obviously in our favor, but all of which
must be stated:

1. **Real vs. modular.** NPP/SBP results are for Gaussian reals. Our
   constraints are exact residues mod small prime powers. (Modular versions
   are usually *not easier* — there is no "small but nonzero" slack — but the
   theorems do not literally apply.)
2. **Single vs. many constraints.** NPP is one constraint; SBP is m = αN
   dense constraints, which is closer to us (our α ≈ D/N ≈ 0.02–0.04 in
   component count). The VV hardness covers both ends. Still, mixed moduli
   with a product-group CRT structure is its own setting.
3. **Distribution.** Their instances are i.i.d. Gaussian; our vectors are
   discrete logarithms of primes — deterministic, structured objects that
   merely *look* equidistributed. Average-case hardness over one distribution
   says nothing formal about another. This is the same reason the door to
   option-b "direction 1" (exploit dlog structure) stays ajar — though §7
   reports the survey found no handle.
4. **{±1} vs. {0,1} + parity.** Immaterial: the affine map x ↦ (x+1)/2
   converts one to the other, shifting the target; the parity constraint is
   one extra GF(2) row (already handled by S2). [C, exact]
5. **Optimization vs. search-to-target.** NPP hardness is about minimizing;
   we need an exact hit. Exact-hit is the harder direction at the same bit
   depth, so the analogy errs conservative here.

**What would make it a theorem:** a reduction from SBP (Gaussian, m
constraints) to multi-modular 0/1 subset-sum with dense dlog-style vectors —
plausible as a research task (discretize Gaussians mod ℓ's), and would be a
real contribution of the negative-result paper if carried out; flagged as
optional future work, not assumed.

---

## 3. The list-algorithm ("bit-consumption") argument [C, consistent with A10 [A]]

Every k-list/birthday-class algorithm (Wagner's k-tree; Minder–Sinclair
small-list regime; Dinur's framework; KK differencing) advances by merging two
lists of size 2^s and keeping pairs that agree on ~s bits — each level
"consumes" ~s ≈ log₂(list size) bits of the target at the cost of one halving
of the tree. With pool N, list sizes are ≤ N and the number of levels is
h ≤ log₂N, so total consumable bits ≲ log₂N · log₂N ≈ **321 bits** (KK's
log²N again) without exponential list growth. To consume 18,117 bits in
h ≤ 17 levels needs lists of 2^(18117/18) ≈ 2^1,000 — beyond any resource.
This is why refinements that improve constants or memory (Minder–Sinclair,
Nikolić–Sasaki, Dinur 2018, structured-list GBA) cannot change the verdict:
they optimize within the same consumption budget. A10's measured law,
(1−ρ)·r_max ≈ 20 ≈ log₂N, is this argument observed experimentally (identity
coordinates are "pre-consumed," hence the 1/(1−ρ) factor).

---

## 4. Zero-sum theory (Davenport constants) — the compounding computation [C/B/D]

**Inputs [B]:** For an elementary abelian p-group (Z/p)^r, Olson:
D((Z/p)^r) = r(p−1)+1; any sequence of length ≥ D has a nonempty zero-sum
subsequence. **Imran–Ivanyos** (arXiv:2304.08376, QIP 2024) [D]: a
deterministic polynomial-time algorithm *finding* zero-sum subsequences over
F_p^r for constant p, given sequences of polynomial length. ⚠ Verify: the
exact length requirement ((rp)^d for which d?) and whether it extends to
Z/p^a components.

**The obstruction is cross-Sylow simultaneity, not per-Sylow finding [C].**
Our odd group is ⊕_ℓ Syl_ℓ over 24 primes ℓ ≤ 97. A zero-sum for G must be
zero in every Sylow simultaneously. The natural recursion — find many
disjoint zero-sum subsequences mod Syl_ℓ₁, treat their sums (now identity on
Syl_ℓ₁) as super-elements, recurse — pays multiplicatively:

- rank(Syl₃) ~ 10³ (roughly half the factor-base primes q have 3 | q−1;
  the frozen-spec group has thousands of components [A, A4]).
- Shortest zero-sum subsequences mod (Z/3)^r in a random pool of N = 2.5×10⁵:
  need C(N,k) ≳ 3^r, i.e. k(log₂N − log₂k) ≳ 1.585·r; with r = 10³ this
  gives k ≈ 150. So at most N/k ≈ 1,600 *disjoint* level-1 super-elements.
- Level 2 needs a zero-sum mod Syl₅ (rank ~500 ⇒ D = 4·500+1 = 2,001, or
  shortest-length ≈ 10³ by the same count) **from a pool of 1,600** — already
  at the edge, with 22 primes still to go, and the super-elements are *sums
  of ~150 vectors*, hence even denser than the originals.

Conclusion: the recursion dies at level 2–3 of 24. This reproduces the A10
compounding from pure additive combinatorics, independent of any specific
algorithm — which is why it is in the review as corroboration, not as a
direction. A *sub-multiplicative cross-Sylow zero-sum theorem* is the named
form a surprise would take; none was found.

---

## 5. Coding-theory framing: R-SDP [B/C]

Restricted Syndrome Decoding (R-SDP): given a parity-check matrix over F_q and
a syndrome, find an error vector with entries in a restricted set E ⊂ F_q.
With E = {0,1} this is exactly our per-modulus system; jointly over mixed
moduli it is a CRT product of R-SDP instances sharing one binary solution.
Facts [B]: R-SDP is NP-complete; it underlies the NIST-candidate signature
CROSS; solvers are ISD/BJMM/BKW adaptations, exponential in code redundancy
(security analyses: CiC 1(3):33 2024; a BKW-style solver paper, 2025 ⚠[D] for
its exact exponents). Our redundancy is ~18k mixed-modulus digits ⇒ ISD-class
exponents of order thousands of bits [C]. Value: hardness pedigree +
vocabulary; no algorithmic path. Related NP-hardness for subset-product
itself: arXiv:2002.07095 [D at statement level].

---

## 6. Lattice methods [C/B]

- **Low-density attacks** (Lagarias–Odlyzko; Coster et al.) require knapsack
  density n/log₂(max weight) < 0.9408 [B]. Ours is ≈ 13.8 (§1) — the opposite,
  "many solutions" regime where SVP-oracle reductions break down [B].
- **The remaining measurement** (option-b brief, direction 2): eliminate
  exactly over GF(2) and each GF(ℓ), count the residual pivot ("hard-core")
  dimension; BKZ is imaginable only if core ≲ 200–500. Prediction from A4's
  decomposition [A]: the odd part alone has thousands of components, each
  requiring a pivot, so the core should come out ≫ 500 ⇒ dead. This is a
  ~1-day scripting task against `a8_omega_solver.make_structured` instances;
  it is in the recommendations because a *measured* kill is worth more than
  my prediction in the paper's completeness table.
- **Direction of evidence**: VV25 (§2) makes lattice reduction the *reason*
  the regime is hard, which is structurally the wrong place to look for the
  cure [C, judgment].

---

## 7. Algebraic-structure directions that were checked and found empty [C]

1. **Index-calculus-style manufactured relations.** Relations among pool
   vectors correspond to congruences ∏p ≡ ∏p′ (mod Λ) between products of
   distinct ~50-bit primes with Λ ~ 2^18000. Any such congruence with both
   sides < Λ is an integer equality, impossible by unique factorization
   (products of *distinct* primes). Nontrivial congruences require products
   above Λ, i.e. subsets of ≥ ~360 primes — finding those *is* the original
   problem. No shortcut. [C, exact]
2. **Subset-dependent demand accounting.** The fixed-Λ formulation
   (Prop 3.1) is sufficient, not necessary: only components activated by the
   chosen primes constrain. Quantified: restrict to t′ of the t medium
   primes; pool scales as N·(t′/t)^j (j = 4), demand as ~12.3·t′ bits [A,
   PLAN §Track A economics]. Solving pool ≥ demand for the frozen spec
   (N = 2.5×10⁵, t ≈ 10³): (t′)³ ≳ 4.8×10⁷ ⇒ t′ ≳ 360 ⇒ demand still
   ≈ 4,400 bits + the full plus side ≈ thousands of components. The regime
   does not change; the accounting is a real but ~2× effect, already
   anticipated by A2's "only-count-used-primes" knob. [C]
3. **Coset/subvariety structure of dlog vectors** (option-b direction 1's
   speculative core): no literature found connecting dlog images of primes to
   subset-product algorithms; the only structure results found are
   hardness-side (NP-completeness of intersecting subproducts with subgroups
   in Cartesian powers, arXiv:2101.06157 [D]). Remains open in principle,
   with nothing to build on.

---

## 8. The Chen–Greene analysis — the load-bearing new input

This section separates *documented facts* from *my inferences* with care,
because the review's main recommendation (A12) rests on it.

### 8.1 Documented facts [B/D]

- Chen, Zhuo and Greene, John, *Some comments on Baillie-PSW pseudoprimes*,
  Fibonacci Quarterly 41.4 (2003), 334–344. Full text not retrievable in this
  environment (⚠ [D] for everything below not independently corroborated).
- Corroborated by **three independent secondary sources** (Shallue–Webster,
  *Fast tabulation of challenge pseudoprimes*, ANTS-XIII / arXiv:1806.08697;
  the ANTS talk slides; a further survey snippet): Chen–Greene constructed a
  set S of **1,248 primes** such that among the ~2^1248 products of distinct
  primes of S, an expected **~740** are counterexamples to the **PSW** test
  (the weaker $620 challenge variant: base-2 Fermat + *Fibonacci* test with
  n ≡ ±2 mod 5 — not the full Baillie-PSW with strong Lucas/Selfridge
  parameters).
- The construction follows Pomerance's 1984 heuristic blueprint (*Are there
  counterexamples to the Baillie-PSW test?*): choose two highly composite
  numbers M, N with gcd(M,N) = 2 and collect primes whose relevant orders
  divide them — for the Fermat side a condition tied to ord_p(2) | M, for the
  Lucas/Fibonacci side a condition tied to the rank of apparition α(p) | N.
  A subset T ⊆ S whose product n satisfies n ≡ 1 (mod M) and the matching
  ±1-type condition (mod N) is then a counterexample. ⚠ [D] — the *exact*
  conditions, the sizes/factorizations of M and N, and how the 1,248 primes
  were enumerated must be confirmed from the paper.
- Shallue–Webster explicitly classify this construction as leading to "a
  computationally infeasible subset product problem" [B, their published
  assessment], and their own contribution goes the opposite way (exhaustive
  tabulation: no challenge pseudoprime ≤ 2^80 with 2 or 3 prime factors).
- No BPSW counterexample exists below 2^64 (Feitsma–Galway complete base-2
  Fermat-psp list, checked against the Lucas side) [B]; prizes: $620 (PSW),
  $2,000 (Baillie–Fiori–Wagstaff strengthened test, Math. Comp. 90 (2021))
  [B].

### 8.2 Inference 1: their demand was ~1,240 bits and their pool/demand ≈ 1 [C]

Model: subset products equidistribute in the ambient constraint group
(exactly the heuristic Pomerance's blueprint uses). Then

  E[#solutions] ≈ 2^|S| / |constraint group|  ⇒
  log₂|group| ≈ |S| − log₂(E) ≈ 1248 − log₂(740) ≈ 1248 − 9.5 ≈ **1,238.5**.

So demand ≈ 1,238 bits against a pool of 1,248: ratio ≈ 1.008 — an
*existence-threshold* design, ~2⁹·⁵ solutions in a 2^1248 haystack. Known
solvers need pool ≫ bits (AGHS operated at pool/bits ≫ 10; Wagner needs
2^(bits/levels)-sized lists). Assumptions that could shift this by a few bits,
none materially: the group is a unit group not a full cyclic group; parity
and mod-5 side conditions; non-uniformity of dlog images. [C]

### 8.3 Inference 2: what this does and does not say about N1 [C]

N1 [A] tested the strict double-divisibility harvest (p−1 | Λ₋, p+1 | Λ₊,
plus twin-smooth side-coprimality and mod-40 congruence) with factor bases
|T₋|+|T₊| ≤ 68 and found pools of 0–2. Chen–Greene's 1,248 shows the
*ord-divisibility analogue* of that pool is far from empty at ~1,240-bit
modulus scale. Two honest gaps between those statements:

1. **Condition strength.** ord_p(2) | M does *not* imply p−1 | M (the index
   (p−1)/ord_p(2) can carry primes outside M). Our L–P conditions (c),(d)
   as stated in working-paper Thm 2.1 are the strict p∓1 divisibilities. So
   1,248 is an *upper-bound-shaped* encouragement, not a transferred count.
   Quantitative expectation [C, heuristic]: the index is 1 or small with
   constant probability (folklore: index 1 with density ~0.37, Hooley-type
   under GRH), so strict-divisibility pools should be within a small constant
   factor of ord-divisibility pools *for the same (M,N) design* — but this is
   precisely what A12 must measure, not assume.
2. **A possible weakening on our side (new observation, needs B1).** Váňa's
   ρ(p) | 10(p²−1) [A, Phase 0 T3] suggests the *necessary* per-prime control
   is an order-type quantity ρ(p), not the full p²−1: if the construction can
   be re-derived (Track B1 territory) with ρ(p)-divisibility replacing strict
   p∓1-divisibility in conditions (c),(d), our eligibility condition weakens
   exactly toward the Chen–Greene form, enlarging the harvestable pool. ⚠
   This is a conjecture about our own machinery — it must be settled by the
   B1 re-derivation before A12 banks on it; A12 should count both variants.

### 8.4 Inference 3: density at scale [C, heuristic]

In the strict-divisibility divisor paradigm at large scale, a pool prime is
p = 2a+1 with a | M/2 and (a+1) | N/2-type conditions; p is identity exactly
on the components covered by p−1 (minus side) and p+1 (plus side). For M
squarefree with k prime factors, divisors concentrate at k/2 factors
(binomial), so a typical pool prime covers ~half the minus-side components
and (by the same argument) ~half the plus side: identity-density ρ ~ 0.5 in
component measure — the same order as AGHS's own pools (ρ ≈ 0.3–0.5 [A,
FINDINGS N1 comparison]). Contrast with N1's small-scale H8 attempts, where
pool primes were forced small (few components covered). Caveat: the *useful*
pool may be biased toward smaller divisors (primality of 2a+1 is likelier to
be testable/frequent at smaller sizes only mildly); A12 measures the actual
density histogram.

### 8.5 The A12 experiment, specified [proposal]

**Question.** For the double condition (both strict and ρ(p)-weakened
variants, with the full Agrawal filters: p ≡ 3 (mod 80), mod-5 class,
side-coprimality, k ≡ 1,3 (mod 4) reachable), what is the achievable frontier
(pool size vs. demand bits vs. density) as a function of the design of
(M, N) = (Λ₋, Λ₊), and does any design reach pool ≥ 2.5 × demand-bits at
ρ ≳ 0.3?

**Method.** No production harvest; divisor-coincidence accounting:
1. Choose candidate designs: M = 2^a·∏ small primes (highly composite,
   80 | M), N = ∏ different small primes, gcd(M,N) = 2, sweeping total bits
   from N1's ~300 up through Chen–Greene's ~1,240 and beyond (~5,000).
2. Enumerate divisors a | M/2 (meet-in-the-middle over the factor split if
   d(M) is large; cap enumeration ~10⁹–10¹¹ — C implementation, same skill
   set as `chm_closure.c`).
3. For each a: check the congruence filters cheaply, then (a+1) | N-side
   condition, then BPSW-test p = 2a+1. Record pool count, each p's covered
   components (→ density histogram), and demand = bits of the components
   actually activated.
4. Output the frontier curves; compare against the G2-style gate
   (pool/demand ≥ 2.5) and the AGHS density band.

**Cost.** Divisor enumeration dominates; ~10⁹ divisor-tests ≈ hours in C
single-threaded per design; primality tests only on survivors of the cheap
filters. Entirely within existing compute habits.

**Interpretations.**
- *Frontier over-provisions at some scale:* N1's verdict was scale-limited;
  proceed to R5 (full AGHS ω-solver build — a8 never reproduced it [A]) on
  A12-designed pools; G3 re-attempt. Note the end product would have
  ~10⁵⁺-bit prime factors and an enormous n — consistent with the L–P
  "counterexamples are astronomically large" heuristic; verification of
  T(−1,n,5) remains polynomial-time.
- *Frontier stalls at ratio ~1 (Chen–Greene-like) at all computable scales:*
  N1 upgrades from "empty at toy scale" to a measured scaling law
  ("pool/demand → ~1 from below as Λ grows; over-provisioning unreachable"),
  and the negative paper gains: (i) the law, (ii) the identification of
  Chen–Greene's 20-year impasse as the same wall, (iii) the complexity
  framing of §2. This is the more likely outcome.

### 8.6 Why ~20–30% (the subjective prior, decomposed)

P(reopen) ≈ P(frontier over-provisions at computable scale) ×
P(solver then works). For the first factor (~0.35): *for* — exponential
divisor growth vs. linear demand growth; Chen–Greene reached ratio ≈ 1 already
in 2003 with hand-tuned design and no optimization for over-provisioning;
the ρ(p) weakening (§8.3.2) is a potential multiplier. *Against* — coincidence
density per divisor falls as divisors spread over exponentially more sizes;
the Agrawal congruence filters cost a further ~10–40× per prime (mod-80 cell
[A, Lemma 4.1]); and twenty years of BPSW-hunters had incentives to find an
over-provisioned design and did not (though: their goal was one counterexample,
not solver-friendliness, and AGHS-style solvers postdate Chen–Greene — the
combination "over-provision + ω-reduction" appears genuinely untried [C]).
For the second factor (~0.5): AGHS demonstrably solved the single-condition
version at scale in exactly this density regime [B]; the double condition CRTs
into one product group with target (1, −1) — no structural obstacle known,
but the full algorithm remains unimplemented here (a8 stub solves only
r ≤ 20, ρ ≥ 0.9 [A]) and non-uniformity exploitation may interact badly with
the two-sided pool. Multiplying: ≈ 0.17; rounded range 15–30%. These are
priors for prioritization, not results.

---

## 9. The infinitude-proof landscape (per-row citation status)

| Result | Condition per prime | Status of my reading |
|---|---|---|
| Alford–Granville–Pomerance 1994, Carmichael infinitude | p−1 \| n−1 | [B] classical |
| Wright 2018, Lucas–Carmichael infinitude | p+1 \| n+1 | [D] ⚠ attributed by multiple secondary sources; exact venue to confirm (his BLMS elliptic-Carmichael paper is a companion, possibly the same technique) |
| Zheng 2022, arXiv:2207.08641, (−1,1)-Carmichael | p+1 \| n−1 | [D] title+abstract |
| Wright 2013, Carmichael in APs; Wright 2018 elliptic | one-sided variants | [B/D] |
| Larsen–Wright, arXiv:2510.16632 (Oct 2025), Carmichael with exactly R factors for all large R | p−1 \| n−1 | [D] abstract |
| Grantham 2010 (J. Number Theory) / arXiv:1903.06825, Perrin/Frobenius pseudoprime infinitude | see below | [D] ⚠ |
| Carmichael ∧ Lucas–Carmichael simultaneously (our need) | p∓1 \| n∓1 both | open; OEIS A329223 has no terms; no existence proof or construction found in any source consulted |

**The Grantham caveat, precisely.** Secondary descriptions say his
construction covers composites with (Δ|p) = 1 for all p | n — i.e., primes
where the quadratic/cubic structure *splits*, which is the case where the
Frobenius condition degenerates to p−1-side divisibility. If that reading is
right, his result is another one-sided instance and the pattern "every proved
case is one-sided" is intact. If a full read shows he genuinely controls a
two-sided (inert-prime, p+1-type together with p−1-type) condition, his
mechanism (AGP framework + Hecke L-function zero-density input) would be the
single most important thing to import into this project, and the review's
§3.2 assessment must be revised upward. This is the highest-priority ⚠ in the
document.

---

## 10. Hegde–Devaraj 2021 [D]

*Heuristics for the Construction of Counterexamples to the Agrawal
Conjecture*, Springer PROMS 344, pp. 537–543. Accessible: abstract only. It
generalizes the Lenstra–Pomerance method to **two additional classes** of
candidate counterexamples with analytic count estimates. Unknown: whether
either class relaxes the two-sided divisibility (A11's intrinsic-degree
argument [A] suggests not, but A11 analyzed the T(−1,n,r) family as we
formulated it — their classes must be checked against their own definitions).
Action: obtain via library/ILL before the paper's related-work section is
frozen. P(changes the solver regime): ~10% [C, prior].

---

## 11. Directions assessed and closed — one-line reasons (details in review §2)

| Direction | Why closed | Tier |
|---|---|---|
| Dense subset-sum (Galil–Margalit, Bringmann–Wellnitz) | single-modulus additive-combinatorics engine; no rank-10³ analogue; joint DP is \|G\| ≈ 2^18000 | [B/C] |
| Modular subset-sum (Axiotis et al.) | per-component already trivial; same joint blowup | [B/C] |
| k-list refinements | §3 consumption budget; A10 measured it | [A/C] |
| Zero-sum recursion | §4 compounding computation | [C] |
| Lattices | density 13.8 ≫ 0.94; core-dimension predicted ≫ 500 (measure anyway) | [B/C] |
| SAT/ILP/pseudo-Boolean | no native mod-ℓ propagation; 2.5×10⁵ vars × 10³⁺ modular constraints beyond any solver frontier; subset-sum is CDCL-adversarial | [C, judgment] |
| Quantum | best subset-sum ~2^0.22N with N = 2.5×10⁵; abelian HSP does not encode 0/1-restricted subset-product | [B/C] |
| Manufactured algebraic relations | unique factorization, §7.1 | [C, exact] |

## 12. Access log (what could not be verified and why)

WebFetch attempts blocked by the environment's egress proxy
(`EGRESS_BLOCKED`): arxiv.org (×3, incl. 1903.06825, 2510.16632),
eprint.iacr.org (2025/130), dl.acm.org, mathstat.dal.ca and fq.math.ca
(Chen–Greene PDF), d.umn.edu (Greene's page), cerias.purdue.edu (BFW21).
WebSearch (a separate service) worked; all [D] items derive from search-result
snippets and secondary papers found through it. Before the negative-result
paper cites any [D] item, the full text must be obtained (all are
standard-library accessible; none is obscure). The in-repo numbers ([A]) and
the arithmetic ([C]) are checkable now without any external access.
