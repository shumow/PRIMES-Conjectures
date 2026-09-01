# Arithmetic-geometric interpretations of Agrawal's conjecture: initial findings

*Recorded 2026-09-01, branch `arith-geom-interpretation`. Status: interpretive /
theoretical — no new computation yet. Companion plan: `doc/arith-geom-plan.md`.
This document reframes the conjecture, the Lenstra–Pomerance counterexample
mechanism, and this repo's negative results (A4–A11, N1; see `data/FINDINGS.md`)
in the language of group schemes, algebraic tori, and Frobenius lifts. Claims
are graded: **[std]** standard/known, **[reform]** a reformulation of something
this repo measured or proved, **[spec]** speculative, needs work.*

---

## 1. The AKS congruence is a Frobenius-lift condition on μ_r

**[std]** The seed of AKS is the polynomial identity: n is prime iff
(X+a)ⁿ ≡ Xⁿ+a (mod n) in (Z/n)[X] for a single a coprime to n. Geometrically:
n is prime iff x ↦ xⁿ is a ring endomorphism of (Z/n)-algebras — iff there is
an "absolute Frobenius at n". AKS truncates this universal statement from the
affine line to the finite group scheme μ_r = Spec Z[X]/(X^r − 1): on
A = (Z/n)[X]/(X^r−1) we have the substitution σ_n : X ↦ Xⁿ, and when n is
prime the freshman's dream + Fermat give f(X)ⁿ ≡ f(Xⁿ) for *every* f — the
n-power map coincides with σ_n on all of A. The AKS congruence checks the
coincidence on the single function f = X−1.

**[std] Λ-ring formalization.** Z[X]/(X^r−1) is the group ring Z[Z/r], a
Λ-ring with Adams operations ψᵏ(X) = Xᵏ. The defining property of a
Λ-structure on a torsion-free ring (Wilkerson's criterion) is that each ψᵖ is
a Frobenius lift: ψᵖ(f) ≡ fᵖ (mod p) for all f. So:

> **n is prime ⟺ ψⁿ is a Frobenius lift at n**, and the AKS congruence is
> that lift condition tested on the single element X−1.

In Borger's program a Λ-structure *is* descent data to F₁, so Agrawal's
conjecture becomes a **quantitative descent statement**: checking the
Frobenius-lift congruence at one well-chosen section of μ_r certifies it
globally, up to the σ_n² = id exception. Lenstra–Pomerance's *pseudofields*
(the Gaussian-periods paper, JEMS 2019) are the operational form of the same
object: finite rings equipped with a certified Frobenius datum.

## 2. The exceptional clause n² ≡ 1 (mod r) is about the real subfield

**[std]** σ_n is the action of n ∈ (Z/r)* ≅ Gal(Q(ζ_r)/Q) on μ_r; n² ≡ 1
(mod r) says σ_n is the identity or complex conjugation, i.e. σ_n lies in
Gal(Q(ζ_r)/Q(ζ_r)⁺). So the conjecture asserts:

> *A composite can pass the test only if its fake Frobenius acts trivially on
> the maximal real subfield Q(ζ_r)⁺.* Composite impostors are confined to the
> decomposition group of the real locus.

## 3. The L–P double condition = Frobenius impersonation on both 1-dim tori

**[reform]** The Lenstra–Pomerance counterexample conditions — p−1 | n−1 and
p+1 | n+1 for every p | n — say exactly:

- xⁿ = x for all x ∈ **G_m(F_p)** = F_p^× (order p−1): n acts as the p-power
  Frobenius on the **split torus**. Alone, this is Korselt's criterion
  (Carmichael numbers).
- tⁿ = t⁻¹ = tᵖ for all t in the **norm-one torus** T(F_p) ⊂ F_{p²}^×
  (order p+1): n acts as Frobenius on the **nonsplit twist** of G_m
  (Lucas–Carmichael numbers).

So an L–P counterexample is a composite n that **impersonates the Frobenius
on both one-dimensional algebraic tori over F_p, simultaneously at every
prime divisor** — "Korselt at depth 2", n ≡ p on F_{p²}^× (up to sign).
Váňa's ρ(p) | 10(p²−1) is the trace of this: p²−1 = (p−1)(p+1) is the product
of the two torus orders.

**[reform] Twin-smoothness is torus-order smoothness.** Requiring (m, m+1)
twin-smooth for p = 2m+1 is requiring both tori over F_p to have smooth
order — the *same* condition the isogeny-crypto community optimizes when
hunting twin smooths for B-SIDH/SQISign parameter primes (a supersingular
curve over F_{p²} has group order (p∓1)², so twin-smooth p ⟺ smooth
supersingular curve groups). Our reliance on the Costello–Naehrig corpora is
not a coincidence of technique; it is the same underlying geometry.

## 4. A11 is the shadow of a dimension count on cyclotomic tori

**[reform — the main upgrade candidate.]** The A11 measurement
(`code/a11_general_r.py`, `data/FINDINGS.md` §A11) found empirically that the
"harvest degree" floor is 2 for every AKS modulus r, achieved exactly at
cyclotomic levels {1, 2}. Torus restatement:

- p^d − 1 = ∏_{e|d} Φ_e(p), and Φ_e(p) is (up to small factors) the order of
  the e-th **cyclotomic torus** T_e over F_p, of dimension φ(e).
- The counterexample congruences require controlling (smoothing / dividing)
  the torus factors at the levels carrying the p-dependent part of ord(X−1).
- **φ(e) = 1 exactly for e ∈ {1, 2}** — the split and nonsplit tori. A valid
  counterexample forces σ_n of order > 2, which forces control at a level set
  of total dimension ≥ 2; the minimum is achieved precisely by {1, 2}, i.e.
  the double (twin-smooth) condition. Larger level sets drag in tori of
  dimension ≥ 2, whose orders Φ_e(p) ~ p^{φ(e)} are the Rubin–Silverberg /
  XTR tori — essentially never smooth.

This gives A11's table a theorem-shaped skeleton: *"the double condition is
intrinsic" ⟺ "the only one-dimensional cyclotomic tori are e = 1, 2."*
It upgrades an empirical section of the negative-result paper
(`doc/negative-result-plan.md`) into a structural claim, and it explains
*why* the burden table looks the way it does (levels {1,3} cost φ(3)=2 extra
dimensions via Φ₃(p) = p²+p+1, level {1,11} costs φ(11)=10, etc.).

**What remains to prove [spec]:** the precise bridge lemma — that the
p-dependent part of ρ(p) = ord(X−1) in the relevant factor of
F_p[X]/(X^r−1) sits in exactly the cyclotomic levels e | d with the
large-prime content of Φ_e(p), for general r (A11 verified this empirically;
B1-style derivation needed). See plan item AG2.

## 5. Group-scheme generalizations (the "different construction" axis)

**[std]** The literature already treats primality tests as constructions over
one-dimensional commutative group schemes:

- Gurevich–Kunyavskii, *Deterministic primality tests based on tori and
  elliptic curves*, Finite Fields Appl. 18 (2012) 222–236 — a uniform
  group-scheme framework recovering Gross's and Denomme–Savin's
  Mersenne/Fermat tests as torus and CM-elliptic special cases.
- Couveignes–Lercier, *Elliptic periods and primality proving*
  (arXiv:0810.2853) — the elliptic analogue of Gaussian periods.
- Cheng, *Primality proving via one round in ECPP and one iteration in AKS*
  (math/0301179) — exploits exactly the freedom of moving from μ_r to
  elliptic torsion.
- Lenstra, *Galois theory and primality testing* (Mahler lecture) — the
  ancestral framing: a primality proof is the construction of Artin-symbol
  data in an auxiliary abelian extension (APR: cyclotomic; ECPP: elliptic).

**[spec] Elliptic Agrawal.** An elliptic analogue (single-point Frobenius
test on E[r] instead of μ_r) would have its counterexample heuristic
controlled by divisibility conditions on #E(F_p) rather than p±1 — *one*
rare event per prime with curve freedom, instead of two rigid ones. Whether
the L–P impersonation mechanism even makes sense there appears unexplored,
and our N1/A10/A11 obstruction is specific to the torus pair, so it would not
automatically transfer. This is the one place the geometric view might
re-open a *constructive* route (see plan item AG4) — or yield a matching
negative result.

## 6. Popovych's pair = reductions of two independent points of G_m

**[std/reform]** {X−1, X+2} evaluates to {ζ−1, ζ+2}: two fixed,
multiplicatively independent points of G_m(Q̄). Popovych's plausibility
argument is that their reductions generate a large subgroup of each residue
ring's unit group — the "orders of reductions of fixed algebraic numbers"
circle (Artin-primitive-root flavor; unconditional lower bounds via
Gauss/Kummer-period techniques, Popovych FFA 2012). Geometric reading of why
no L–P-style heuristic exists against it: the counterexample machinery
controls the order of *one* section's reduction via torus-order divisibility;
forcing simultaneous impersonation on the subgroup generated by two
independent points adds a third independent system of rare congruences on
top of the double condition that N1 already showed is unaffordable. **[spec]**
Making this precise (even heuristically, in the style of L–P's density
count) would be the first published evidence *for* Popovych's conjecture.

## 7. Consequences for this project

1. **The negative result gains a structural spine.** N1 + A10 + A11 currently
   read as three measurements; the torus reading binds them: the construction
   *must* smooth the orders of a dimension-≥2 family of tori (A11 ⟸ φ(e)=1
   iff e ∈ {1,2}), the resulting pool primes are constrained by two
   independent 1-dim torus conditions (twin-smoothness), and the solver-side
   density gap (N1/A10) is a statement about how such doubly-constrained
   primes sit in (Z/Λ₋)* × (Z/Λ₊)* — itself a product of split/nonsplit local
   character data.
2. **A new axis exists that our negative results do not cover:** replace μ_r
   by elliptic torsion (§5). Everything measured in A1–A11 is about the
   G_m/torus world.
3. **A Popovych-positive heuristic (§6) is a cheap, publishable spin-off** of
   machinery we already have (the L–P density count + the N1 measurement).

## AG2 result: the torus dimension-count theorem (2026-09-01)

*Deliverables: `doc/arith-geom.tex` §2–4 (+ compiled PDF),
`code/ag2_torus_check.py`, `data/generated/ag2_torus_check.json`.*

**The theorem is proved, with the conditional part localized exactly where
the plan predicted (gate AG-G1: substantially passed).**

**Unconditional core.**
1. *Frobenius matching* (Lemma 3.1): (X−1)^{p^k} ≡ X^{p^k}−1 (mod p, X^r−1);
   the L–P mechanism n ≡ p^j (mod lcm(r, ρ_r(p))) suffices per component,
   and it forces ord_r(n) | d_p = ord_r(p), so validity (ord_r(n) > 2)
   forces **d_p ≥ 3** for every pool prime.
2. *Inversion collapse* (Lemma 3.2, the key identity): for d even, the
   unique involution of (Z/r)× is −1, so p^{d/2} ≡ −1 (mod r) and
   **(X−1)^{p^{d/2}−1} = −X^{−1}** in F_p[X]/Φ_r; hence
   ρ_r(p) | 2r(p^{d/2}−1) = 2r·∏_{e | d/2} Φ_e(p). For r=5, d=4 this *is*
   Váňa's ρ(p) | 10(p²−1).
3. *Support bound*: with d' := d/2 (d even) or d (d odd),
   ρ_r(p) | 2r·∏_{e|d'} Φ_e(p) — the p-dependent part of ρ_r(p) lives on
   cyclotomic levels e | d'.
4. *Dimension count* (Theorem 3.6): the smoothness burden is the F_p-point
   order of the torus ∏_{e|d'} T_e of dimension Σ_{e|d'} φ(e) = **d'**;
   burden ≥ 2 always (d' = 1 would need d ≤ 2, excluded); burden = 2 ⟺
   d = 4 ⟺ level set {1,2} = the split/nonsplit pair (p−1, p+1 smooth =
   the double condition = twin-smoothness); d = 4 realizable ⟺ 4 | r−1;
   r ≡ 3 (mod 4) ⟹ burden ≥ 3. So
   **burden(r) = min{d/2 if d even else d : d | r−1, d ≥ 3}**, never 1.

**Conditional ingredient (the localized AG-G1 gap).** *Generic sharpness*
(Prop 3.5): that the support bound is attained — large primes ℓ | Φ_e(p),
e | d', actually divide ρ_r(p) — is an Artin-type statement, heuristic
failure probability ~1/ℓ per component. A harvest could in principle target
the collapsed thin set; that set is far thinner than the twin-smooth pool
itself (density ~1/ℓ per avoided prime), so the escape is uneconomical, but
it is not unconditionally excluded. Recorded as such in Remark 3.9.

**Numerical verification** (`code/ag2_torus_check.py`, deterministic, 67
sample primes across (r,d) ∈ {(5,4),(13,4),(41,4),(7,3),(7,6),(19,3),
(11,5),(23,11)}):

| check | statement | result |
|---|---|---|
| V1 | Frobenius matching | 67/67 |
| V2 | collapse identity (X−1)^{p^{d/2}−1} = −X^{−1} | 36/36 (all even-d) |
| V3 | exact ρ_r(p) computed inside the support bound | 67/67 |
| V4 | large primes of levels e \| d' divide ρ_r(p) | 37/37 (0 exceptions; ~0.19 expected under 1/ℓ) |
| V5 | top level e = d' genuinely needed in ρ_r(p) | 67/67 |
| V6 | burden formula vs the A11 measured table | 11/11 moduli match (value AND minimizing d) |

**Consequences.**
- A11 is upgraded from an empirical table to a corollary of a dimension
  count: *the double condition is the unique minimizer; the twin-smooth
  condition is intrinsic to every AKS modulus; no r admits a single
  1-dimensional-torus (p±1-only) route.* The structural reason "every other
  r is worse" is that burden ≥ 3 forces smooth values of Φ_e(p) ~ p^{φ(e)},
  φ(e) ≥ 2 — the same quantities whose non-smoothness underpins
  Rubin–Silverberg torus cryptography.
- The negative-result paper's option-(c) section can now cite a theorem
  (mechanism-scoped, sharpness-generic) instead of a measurement; patch
  note for `doc/negative-result-plan.md` owners: use arith-geom.tex
  §3 (Theorem 3.6, Corollary 3.7) with the two caveats of Remark 2.3
  (mechanism scope) and Remark 3.9 (generic sharpness).

**Scope caveat (unchanged from A11):** everything quantifies the L–P
*mechanism* (Frobenius-matching constructions, Def. 2.2); "accidental"
component solutions outside it are not excluded — same discipline as the
negative-result paper.

## References (verified links)

- Agrawal–Kayal–Saxena, *PRIMES is in P*:
  https://www.cse.iitk.ac.in/users/manindra/algebra/primality_v6.pdf
- Lenstra–Pomerance, *Primality testing with Gaussian periods*, JEMS 21
  (2019): https://ems.press/journals/jems/articles/16019 (preprint:
  https://math.dartmouth.edu/~carlp/aks111216.pdf)
- Lenstra, *Galois theory and primality testing*, Mahler lecture 2003:
  http://magma.maths.usyd.edu.au/~bruin/Workshop/mahler.pdf
- Borger, *Λ-rings and the field with one element*:
  https://maths-people.anu.edu.au/~borger/papers/_all/LambdaRingsAndTheFieldWithOneElement.pdf
- nLab, *Lambda-ring* (Wilkerson criterion, Adams/Frobenius):
  https://ncatlab.org/nlab/show/Lambda-ring
- Gurevich–Kunyavskii, *Deterministic primality tests based on tori and
  elliptic curves*, FFA 18 (2012):
  https://www.sciencedirect.com/science/article/pii/S1071579711000670
  (author list: https://u.math.biu.ac.il/~kunyav/publ.html)
- Couveignes–Lercier, *Elliptic periods and primality proving*:
  https://arxiv.org/pdf/0810.2853
- Cheng, *Primality proving via one round in ECPP and one iteration in AKS*:
  https://arxiv.org/html/math/0301179v1
- Voskresenskii-tradition survey, *Algebraic tori — thirty years after*:
  https://arxiv.org/pdf/0712.4061
- Popovych, *A note on Agrawal conjecture*, ePrint 2009/008:
  https://eprint.iacr.org/2009/008.pdf
