# Solver-strategy literature review: directions after A10/A11

*2026-08-24. Written from a step-back survey of the literature, after ingesting
FINDINGS.md (through A11), PLAN.md, registry.md, a4-solver-analysis.md, and the
option-b brief. Purpose: identify and honestly assess every direction that could
reopen — or definitively close — the solver stage of the pipeline. This document
recommends; it does not decide. No numbers in FINDINGS.md are re-measured here.*

*Companion documents: `doc/solver-review-overview.md` (2-page narrative of how
the project arrived here and what this review adds) and
`doc/solver-directions-review-details.md` (claim-by-claim provenance tiers,
full derivations, and the verification status of every external source —
read it before trusting any specific number below).*

**Access caveat.** The research environment could search the open web but could
not fetch full PDFs (egress proxy blocks arxiv.org, eprint.iacr.org, journal
sites). Assessments marked ⚠ are based on abstracts, secondary sources, and
search snippets, not a full read; each names what a full read must confirm.

---

## 0. The problem being surveyed (recap, one paragraph)

Find x ∈ {0,1}^N, Σx odd, with Σ xₚvₚ = t in G = ⊕ᵢ Z/mᵢ: D ≈ 10³–10⁴
prime-power components (primes ≤ 97 after co-design), log₂|G| ≈ 18–24k bits,
pool N ≈ 2.5×10⁵ vectors that are *dense* (identity-density ρ ≈ 0.004), pool
only ~10× the bit-dimension. Measured walls: exact methods cap at ~15 odd
components (A6); GF(2) solves only the 2-part (~16% of bits, A4); Wagner-class
birthday methods obey reach r_max ≈ O(log N)/(1−ρ), needing ρ ≳ 0.98 (A10);
high-ρ pools are unharvestable under the double Carmichael+Lucas condition at
the scales tested (N1); no AKS modulus r avoids the double condition (A11).

The survey below splits into **solver-side** directions (attack the instance as
given) and **construction-side** directions (change what instance we generate).
The single most consequential finding is construction-side: §4.1.

---

## 1. Complexity-theoretic framing: the wall is (probably) a real wall

### 1.1 Our problem is a multi-modular Number Partitioning Problem — and NPP now has *proven* conditional hardness

The random Number Partitioning Problem (NPP) — find x ∈ {±1}^N minimizing
|Σ xᵢaᵢ| for random aᵢ — is the closest well-studied model for our regime: a
single dense constraint, exponentially many solutions at the statistical
optimum, and a huge statistical-to-computational gap. Statistically the optimum
is ~2^−N; the best known polynomial algorithm (Karmarkar–Karp differencing)
reaches only 2^−Θ(log²N).

- **Gamarnik–Kızıldağ** (Ann. Appl. Prob. 2023; arXiv:2103.01369) proved NPP
  exhibits the **Overlap Gap Property** in the gap regime — a rigorous barrier
  for stable algorithms (gradient descent, AMP, Langevin dynamics).
- **Vafa–Vaikuntanathan** (STOC 2025; ePrint 2025/130, arXiv:2501.16517) went
  further: **any polynomial-time algorithm achieving discrepancy 2^−Ω(log³N)
  would imply worst-case subexponential-factor SVP approximation** — i.e.,
  Karmarkar–Karp is nearly *optimal* under standard lattice assumptions. The
  same paper proves the analogous tightness (the Bansal–Spencer bound) for the
  symmetric binary perceptron, resolving a conjecture of Gamarnik et al.
- The symmetric binary perceptron literature (Abbe–Li–Sly; Gamarnik–Kızıldağ–
  Perkins–Xu, arXiv:2203.15667) adds the structural insight that typical
  solutions are **totally frozen isolated singletons** — exactly the geometry in
  which local/annealing methods fail, matching our A6 annealing result.

**Mapping to our numbers.** Karmarkar–Karp differencing is the h=∞ limit of the
2-list birthday; our measured Wagner law r_max ~ log N is its expression in the
multi-component setting. Polynomial methods reach ~log²–log³ N bits of
"discrepancy": with N = 2.5×10⁵, log₂²N ≈ 320 bits, log₂³N ≈ 5,800 bits. Our
demand is **~18,000–24,000 bits — beyond even the provably-lattice-hard
threshold** in the Gaussian model.

**Honest caveats.** (i) These results are for Gaussian/real single-constraint
instances; our problem is modular, multi-constraint, and *structured* (vectors
are discrete logs of primes). There is **no literal reduction** either way — the
mapping is an analogy of regimes, not a theorem about our instance. (ii)
Hardness is average-case over their distribution; structure could in principle
evade it (that is option-b direction 1, §3.6). (iii) ⚠ statement details from
abstracts.

**Assessment.** This does not close option (b), but it re-prices it: a solver
for the generic version of our regime would contradict conjectures that the
lattice-cryptography community bets on. Any remaining hope must come from
*instance structure*, never from a better generic algorithm. **Recommended
regardless of outcome: import this framing into the negative-result paper**
(§5, R5) — it converts "our solvers failed" into "the regime is conditionally
hard," which is a much stronger and more publishable statement.

### 1.2 Corroborating hardness pedigrees from coding theory

Our problem is precisely a **Restricted Syndrome Decoding Problem** (R-SDP):
find an error vector with entries restricted to {0,1} ⊂ F_ℓ satisfying a
syndrome equation — here jointly over many small moduli. R-SDP is NP-complete
and is the security foundation of the NIST-candidate signature scheme CROSS
(spec: csrc.nist.gov; security analyses: CiC 1(3):33, 2024; BKW-style solver,
2025). Known solvers are ISD/BJMM/BKW adaptations, all **exponential in the
code redundancy** — here ~18k mixed-modulus digits, i.e. 2^(thousands).
Similarly, "subset product" per se is NP-hard (arXiv:2002.07095), and the
generic-group method (Bisson–Sutherland, *A low-memory algorithm for finding
short product representations in finite groups*, DCC 2012) is O(2^(bits/2)).

**Assessment: closed as a source of algorithms** — but useful vocabulary: it
puts our instance inside a family whose hardness working cryptographers
actively rely on, again strengthening the negative paper.

---

## 2. Solver-side directions from the algorithms literature — assessed

### 2.1 Dense / modular subset-sum algorithms (additive combinatorics) — closed

The celebrated dense-case algorithms (Galil–Margalit; **Bringmann–Wellnitz**,
SODA 2021, arXiv:2010.09096 — near-linear time for dense subset sum, with a
matching SETH lower-bound dichotomy) and the modular subset-sum line (Axiotis
et al., linear sketching) are all **single-modulus / single-target-dimension**:
their additive-combinatorics engine (long arithmetic progressions in subset
sums, Szemerédi–Vu) has no known analogue for rank-10³ groups, and per-component
our problem was never the issue — DP solves any one Z/ℓ in O(Nℓ). The joint
group has |G| ≈ 2^18000, killing every pseudo-polynomial-in-|G| method.
**Likelihood of yielding a solver: negligible.** The dichotomy papers are worth
citing to show the "dense = easy" folklore does not extend to high rank.

### 2.2 Zero-sum theory (Davenport constants, EGZ, Olson) — fails by compounding, but newly quantifiable

Existence theory is rich: any sequence longer than the Davenport constant D(G)
has a zero-sum subsequence; Olson computed D exactly for p-groups. Notably,
**Imran–Ivanyos** (Quantum Inf. Process. 2024; arXiv:2304.08376) give a
**deterministic polynomial-time algorithm** finding zero-sum subsequences over
F_p^n for constant p (developed for hidden-subgroup reductions) ⚠. So *within a
single Sylow subgroup*, finding is not the obstruction — consistent with our
per-component picture.

The wall is **simultaneity across the ~24 odd primes ℓ**. The natural recursion
(find many disjoint zero-sums mod Sylow-ℓ₁, treat their sums as super-elements,
recurse on Sylow-ℓ₂, …) pays a *multiplicative* pool cost: with our co-designed
spec, rank(Syl₃) alone is ~10³, so D(Syl₃) ~ 2×10³, and disjoint zero-sums
number only N/(shortest length ~250) ≈ 10³ — already below D(Syl₅) needed at
the next level. Two levels in, the pool is spent; there are 24 levels. This is
the same compounding as the Wagner law, derived independently.
**Likelihood: negligible as stated.** Residual value: the estimate above is a
clean back-of-envelope for the paper; and if anyone ever proves a
*sub-multiplicative* cross-Sylow zero-sum theorem, that would be the form a
positive answer takes. No such theorem appears to exist.

### 2.3 k-list / generalized-birthday refinements — closed by A10 already

Post-Wagner refinements — Minder–Sinclair (small-list regime), Nikolić–Sasaki,
Dinur's algorithmic framework (ePrint 2018/575), structured-list GBA speedups —
buy constant or small polynomial factors, or trade time/memory. None changes
the governing constraint (list sizes ~2^(bits/(h+1)), h ≤ log₂N) that A10
measured as r_max ≈ O(log N)/(1−ρ). **Likelihood: negligible**; A10's
measurement stands as the empirical form of what this literature predicts.

### 2.4 Lattice methods — one cheap falsification experiment left, expected negative

Classical low-density attacks (LO/CJLOSS) require knapsack density < ~0.94; our
knapsack density is N/log₂|G| ≈ 10–14 — the opposite regime, where lattice
attacks are known to fail and DP is supposed to take over (but can't, §2.1).
The one untested concrete idea (option-b direction 2) remains: eliminate
exactly over GF(2) and each GF(ℓ) and **measure the hard-core dimension**; BKZ
is thinkable only if the core is ≲ 200–500. From A4's decomposition (thousands
of odd components each of which must pivot), the predicted core is ~the odd
dimension, i.e. ≫ 500. Additionally, Vafa–Vaikuntanathan cuts the other way:
lattice algorithms are now the *benchmark whose hardness explains* this regime,
which makes "lattices will save us" structurally unlikely.
**Likelihood: ~5%. Cost: ~a day (it is a measurement, not a build). Verdict:
run it once, for the paper's completeness table, expecting a kill** (§5, R3).

### 2.5 SAT / ILP / pseudo-Boolean solvers — closed on scaling grounds

CDCL with native XOR reasoning handles the GF(2) part (already solved). Mod-ℓ
constraints for odd ℓ have no native propagation in any production solver;
encodings (adders/totalizers per component) at 2.5×10⁵ variables × 10³–10⁴
modular constraints are far beyond the frontier (competition instances top out
orders of magnitude smaller in constraint volume, and subset-sum-like instances
are precisely CDCL's worst case — no structure to learn). ILP relaxations are
vacuous for modular equalities. **Likelihood: negligible** at full scale; at
most a curiosity on a (nonexistent) small hard core.

### 2.6 Quantum — not a live option

Best quantum subset-sum algorithms (Bernstein–Jeffery–Lange–Meurer; Helm–May)
run at ~2^0.22N–2^0.24N — exponential, and N = 2.5×10⁵. The abelian
hidden-subgroup machinery (polytime) does not apply: subset-product with 0/1
exponents is not an HSP instance (the "subgroup" generated by the pool is the
whole group; the 0/1 restriction is what is hard, and it is not a coset
structure). **Likelihood: zero on any relevant horizon.** One-line mention in
the paper suffices.

### 2.7 Exploiting the algebraic structure of the vectors (option-b direction 1) — still the only *theoretical* opening, still without a concrete handle

The vectors are not random: vₚ = (dlog of p mod q^a)_{q}. A survey pass found
no literature that exploits dlog structure to solve subset-products faster —
unsurprisingly, since index-calculus goes the other way (it *finds* relations
among smooth numbers by factoring, which is unavailable here: our pool is
fixed, and congruences mod a 18,000-bit Λ between products of 50-bit primes
essentially never occur except trivially). Two sub-ideas assessed:
- *Manufactured relations:* products of pool primes that coincide as integers —
  impossible (unique factorization).
- *Subset-dependent demand accounting:* the true constraint is only over
  components activated by the chosen subset (the fixed-Λ formulation is a
  sufficient strengthening). Quantified: restricting to t′ of t medium primes
  scales pool as (t′/t)^j but demand only as t′, so pool/demand ~ t′^(j−1) —
  *shrinking* t′ hurts; solutions with |S| ≥ ~250 activate nearly all of Q₋
  anyway. Gain is real but marginal (validates A2's "only-count-used-primes"
  knob); it does not change the regime. **Closed as a solver route.**

**Overall likelihood for §2 as a whole: low single digits.** The honest reading
of the algorithms literature is that A6/A10 measured exactly what theory now
conditionally predicts.

---

## 3. Construction-side directions: what the pseudoprime-construction literature knows

This is where the survey produced genuinely new information.

### 3.1 The Chen–Greene construction: our wall has a 20-year-old twin — and N1's scale was too small to see the interesting regime ⚠

**Chen–Greene** (*Some comments on Baillie-PSW pseudoprimes*, Fibonacci Quart.
41 (2003) 334–344) attacked the PSW challenge (composite passing base-2 Fermat
+ Fibonacci tests — structurally our double condition: a p−1-side and a
p+1-side divisibility per prime, via ord_p(2) and the rank of apparition).
Following Pomerance's 1984 heuristic, they fixed two highly composite numbers
M, N with gcd(M,N) = 2 and harvested primes satisfying both side-conditions
into those fixed moduli. Result (per multiple secondary sources; the paper
itself was not fetchable ⚠): **a pool of 1,248 primes such that among the
~2^1248 subset products an expected ~740 are PSW counterexamples.** They
stopped there: among 2^1248 subsets, *finding* one of ~2^9.5 solutions is a
subset-product instance with ~1,240 bits of demand and pool/demand ratio ≈ 1 —
"computationally infeasible," per Shallue–Webster's later assessment
(*Fast tabulation of challenge pseudoprimes*, ANTS-XIII, arXiv:1806.08697).
The PSW/BPSW prizes ($620; $2,000 for the strengthened test of
Baillie–Fiori–Wagstaff, Math. Comp. 90 (2021)) have stood since; no BPSW
counterexample exists below ~2^64 (Feitsma–Galway base-2 list), and
Shallue–Webster ruled out 2- and 3-factor challenge pseudoprimes to 2^80.

Two consequences, one for each half of our project:

**(a) External corroboration of the wall.** An independent community, with
money on the table, has been stuck for two decades at *exactly* the
double-condition subset-product step. The negative-result paper should say so —
it is the strongest possible "this is not a local failure of our solvers"
evidence, and our A6/A10/N1 measurements are (to my knowledge) the first
*quantification* of that shared wall. High-value, zero-risk addition (§5, R5).

**(b) N1's conclusion is scale-limited — the H8 verdict has an untested regime.**
N1 tested divisor-paradigm harvests with |T₋|+|T₊| ≤ 68 small primes (Λ of a
few hundred bits) and found pools of 0–2. Chen–Greene, at Λ-scale ~1,240 bits
with *highly composite* M and N, harvested **1,248** double-condition primes.
The mechanism: divisor counts grow exponentially in the number of prime factors
of Λ while demand bits grow only linearly, so twin-divisor coincidences
(a | M/2 with the p+1-side condition landing in N) eventually proliferate.
Moreover, in this regime pool primes are comparable in size to Λ itself, so
each p is identity on the components covered by p∓1 — **identity-density
ρ ≈ 0.3–0.5 (heuristic estimate, details §8.4), the AGHS regime**, where the
A10 objection (which killed ρ ≈ 0.004 pools) does not apply. Important
caveat: Chen–Greene's eligibility conditions are *order*-divisibility
(ord_p(2) | M and a rank-of-apparition condition), which is **weaker** than
the strict p∓1-divisibility our L–P conditions (c),(d) require — so their
1,248 is an optimistic bound for us, not a transferred count; conversely,
Váňa's ρ(p) | 10(p²−1) hints our necessary condition may itself weaken to
order-type (a B1 question). Both variants are what A12 must measure (details
§8.3). What Chen–Greene lacked was *over-provisioning*:
with ~2^10 expected solutions among 2^1248 subsets, their pool sat essentially
at the existence threshold (pool ≈ demand bits, ratio ≈ 1), far below what
list-merge or ω-reduction methods need (pool ≫ bits).

**The open quantitative question — and the recommended experiment (A12).**
Nobody appears to have asked: as the scale of (M, N) grows, how does the
achievable frontier (pool size vs. demand bits vs. density) move? Concretely:
design M, N highly composite (with the Agrawal-specific congruence filters
folded in: p ≡ 3 mod 80, mod-5 conditions, side-coprimality); enumerate
divisors a | M/2, test the p+1-side divisibility and primality of p = 2a+1;
count. This is **pure divisor-coincidence accounting plus primality tests — no
new solver needed, no production harvest**: cost is divisor enumeration
(feasible to d(M) ~ 10^9–10^11 in C, exactly the chm_closure.c skill set) on
candidate (M, N) designs. Deliverable: measured pool(Λ)/demand(Λ) curves and
density, i.e. the H8 analogue of the A1 yield grid, at Chen–Greene scale and
beyond. Gate: does any design reach pool ≥ 2.5× demand bits (the G2 threshold)
with ρ ≳ 0.3?

**Honest assessment.** This is the one direction the survey found that could
*reopen* the construction, because it attacks the exact premise (H8 empty) that
closed the route, in a regime the existing measurement never reached, with
favorable exponential-vs-linear scaling on its side and a documented
1,248-prime existence proof at ratio ≈ 1. Against it: pushing ratio from ~1 to
~2.5–10 may cost enormous Λ growth (the coincidence density per divisor falls
as divisors spread over a wider range — the trend is not obviously winning);
the Agrawal congruence filters cost further constant factors per prime; and if
the frontier does over-provision, the resulting counterexample has ~10⁵⁺-bit
prime factors and an astronomically large n (acceptable — L–P predicts enormous
counterexamples, and verification stays polynomial). Subjective probability
that A12 finds an over-provisioned, AGHS-dense regime at computable scale:
**~20–30%**. Conditional on that, probability the full AGHS ω-solver (S6, still
a multi-turn build — unchanged from A7/A8's plan) then solves it: **moderate
(~40–60%)** — it is literally the regime AGHS solved, plus a second side
condition that the ω-potential formalism accommodates (two moduli CRT into
one). Even on failure, A12 converts N1 from "empty at toy scale" to a **scaling
law**, and ties our negative result to the PSW-challenge literature — a strict
upgrade of the paper either way. **This is the top recommendation (R1).**

### 3.2 The infinitude-proof literature: every proved case is one-sided — the double condition is a recognized frontier, with no importable machinery

Survey of what is actually proved about Carmichael-type constructions:

| Result | Condition per prime p | n |
|---|---|---|
| AGP 1994 (Carmichael) | p−1 \| n−1 | infinitude proved |
| Wright 2018 (Lucas–Carmichael) ⚠ | p+1 \| n+1 | infinitude proved |
| Zheng 2022, arXiv:2207.08641 ((−1,1)-Carmichael) | p+1 \| n−1 | infinitude proved |
| Wright 2018 (elliptic Carmichael); Wright 2013 (Carmichael in APs); Larsen–Wright 2025, arXiv:2510.16632 (Carmichael with exactly R factors, all large R) | one-sided variants | proved |
| Grantham 2010 (Perrin/Frobenius pseudoprimes, J. Number Theory; arXiv:1903.06825) | via restriction to (Δ\|p) = 1 (split) primes ⚠ | infinitude proved |
| **Carmichael ∧ Lucas–Carmichael (our need; OEIS A329223)** | **p−1 \| n−1 and p+1 \| n+1** | **open — not one example known** |

The pattern is stark: the AGP sieve framework and all its descendants
(including Larsen–Wright's newest refinement) control exactly **one** linear
condition p−a | n−b per prime; Grantham's Perrin proof — the one result that
superficially involves p²−1 — appears to restrict to split primes precisely so
the condition becomes one-sided ⚠ (a full read must confirm this; if instead he
genuinely handles a two-sided condition, his mechanism would be *the* thing to
import, and this line item escalates sharply). No paper claims even a
conditional existence proof for the simultaneous case. **Assessment: nothing to
import today (likelihood ~5%, pending the Grantham read), but the survey
establishes that our target sits on a known open frontier of analytic number
theory — worth one paragraph of context in the paper.**

### 3.3 Hegde–Devaraj's two additional counterexample classes — unread, must be obtained ⚠

*Heuristics for the Construction of Counterexamples to the Agrawal Conjecture*
(Springer PROMS 344, 2021) generalizes the L–P construction to two further
classes with analytic count estimates. Only the abstract was accessible. A11's
intrinsic-degree argument (harvest degree ≥ 2 for every valid r) suggests any
class within the Agrawal congruence inherits a double condition, but that
argument was derived for the T(−1,n,r) family — whether HD21's classes fall
inside it must be checked against their actual definitions, not assumed.
**Action: obtain the chapter (ILL / library access). Likelihood it changes the
solver regime: low (~10%), but the check is cheap and due diligence for the
paper requires citing them correctly (R4).**

### 3.4 Relaxations of the target — closed

Korselt's criterion forces n squarefree, so exponents stay 0/1; the
subset-dependent-Λ relaxation is marginal (§2.7); and A11 closed the modulus-r
degree of freedom. No further relaxation survives that still yields a valid
Agrawal counterexample under working-paper Prop 3.1.

---

## 4. What this means for the strategic fork

FINDINGS' fork (a)–(d) updates as follows:

- **(a) closed** (A10) — unchanged, now with *conditional-hardness* backing (§1).
- **(b) generic solver: effectively closed** — every family in §2 is negligible
  except one cheap falsification run (hard-core dimension, §2.4). The
  theoretical opening "exploit vector structure" found no handle in the
  literature (§2.7).
- **(c) closed** (A11) — unchanged; §3.2–§3.3 add that the broader
  construction literature has never crossed a double condition either.
- **(d) the negative paper: strengthened substantially** by §1 (OGP +
  lattice-conditional hardness), §1.2 (R-SDP/NP-hard pedigree), and §3.1a/§3.2
  (PSW-challenge twin wall; one-sided-only infinitude landscape).
- **(new, e := A12)** — the Chen–Greene-scale frontier measurement (§3.1b): the
  one live route back to a constructive result, and simultaneously the missing
  scaling law for the paper's N1 section.

## 5. Ranked recommendations

1. **R1 (do first): A12 — double-condition pool frontier at large highly
   composite Λ** (§3.1b). Cheap (divisor enumeration in C + BPSW tests),
   decisive in both directions. Success gate: pool/demand ≥ 2.5 at ρ ≳ 0.3
   under the full Agrawal filters. *P(reopens route) ≈ 20–30%; value on
   failure: high (scaling law for the paper).*
2. **R2: hard-core dimension measurement** (§2.4) — one day, expected kill,
   completes the option-b due-diligence table. *P(positive) ≈ 5%.*
3. **R3: import the hardness framing into the negative-result paper** (§1,
   §1.2, §3.1a, §3.2) — no risk, large credibility gain. Update
   doc/negative-result-plan.md's bibliography accordingly (VV25, GK23,
   R-SDP/CROSS, Chen–Greene 2003, Shallue–Webster 2018, BFW21, Wright 2018,
   Zheng 2022, Larsen–Wright 2025).
4. **R4: obtain and read the three ⚠-critical texts** — Hegde–Devaraj 2021
   (§3.3), Grantham's Perrin proof (§3.2), Chen–Greene 2003 (§3.1) — before the
   paper's related-work section is frozen; each carries a small probability of
   changing a conclusion, and all are currently cited from secondary sources.
5. **R5 (conditional on R1 success): resume the full AGHS ω-solver build**
   (S6/a8, per A7/A8's original two-part plan) targeting the A12-designed
   pools, then re-attempt G3.
6. **Do not invest further in:** dense/modular subset-sum ports, k-list
   refinements, SAT/ILP, quantum, zero-sum recursion, manufactured algebraic
   relations (§2.1–2.3, 2.5–2.7) — each assessed negligible with reasons above.

## 6. Sources

Complexity / algorithms: [Gamarnik–Kızıldağ, NPP OGP](https://arxiv.org/pdf/2103.01369) ·
[Vafa–Vaikuntanathan, STOC 2025](https://eprint.iacr.org/2025/130) ([arXiv](https://arxiv.org/pdf/2501.16517)) ·
[SBP algorithms & barriers](https://arxiv.org/abs/2203.15667) ·
[Discrepancy algorithms for the binary perceptron](https://arxiv.org/pdf/2408.00796) ·
[Bringmann–Wellnitz, dense subset sum](https://arxiv.org/abs/2010.09096) ·
[Imran–Ivanyos, zero-sum subsequences & hidden subgroups](https://arxiv.org/pdf/2304.08376) ·
[Wagner, generalized birthday](https://www.iacr.org/archive/crypto2002/24420288/24420288.pdf) ·
[Minder–Sinclair-type k-tree refinements](https://iacr.org/archive/asiacrypt2015/94520186/94520186.pdf) ·
[Dinur, GBP framework](https://eprint.iacr.org/2018/575.pdf) ·
[CROSS / R-SDP spec](https://csrc.nist.gov/csrc/media/Projects/pqc-dig-sig/documents/round-1/spec-files/CROSS-spec-web.pdf) ·
[R-SDP security analysis](https://cic.iacr.org/p/1/3/33) ·
[Product subset problem, NP-hardness](https://ui.adsabs.harvard.edu/abs/arXiv:2002.07095) ·
[Bisson–Sutherland, short product representations](https://link.springer.com/article/10.1007/s10623-011-9527-8).

Pseudoprime constructions: [Chen–Greene 2003](https://www.fq.math.ca/Scanned/41-4/chen.pdf) ·
[Shallue–Webster, challenge pseudoprimes](https://arxiv.org/pdf/1806.08697) ·
[Baillie–Fiori–Wagstaff 2021](https://homes.cerias.purdue.edu/~ssw/bfw.pdf) ·
[Nicely, BPSW overview](https://faculty.lynchburg.edu/~nicely/misc/bpsw.html) ·
[Open Problem Garden, BPSW](http://www.openproblemgarden.org/op/counterexamples_to_the_baillie_psw_primality_test) ·
[AGHS, subset-product Carmichael](https://arxiv.org/abs/1203.6664) ·
[Grantham, Perrin pseudoprimes](https://arxiv.org/abs/1903.06825) ·
[Wright, Lucas–Carmichael / elliptic Carmichael](https://londmathsoc.onlinelibrary.wiley.com/doi/abs/10.1112/blms.12185) ·
[Zheng, (−1,1)-Carmichael](https://arxiv.org/abs/2207.08641) ·
[Larsen–Wright, specified number of prime factors](https://arxiv.org/abs/2510.16632) ·
[Hegde–Devaraj 2021](https://link.springer.com/chapter/10.1007/978-981-33-4646-8_42) ·
[Agrawal's conjecture background](https://aimath.org/WWN/primesinp/articles/html/50a/).
