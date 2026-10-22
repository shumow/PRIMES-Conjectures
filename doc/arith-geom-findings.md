# Arithmetic-geometric interpretations of Agrawal's conjecture: initial findings

> **Audit update, 2026-10-22:** this chronological record is retained, not
> certified by its historical "complete" labels. The current LaTeX sources
> correct the fixed-ring primality converse, prime-power order criterion,
> and global-versus-reduction claims. Smoothness necessities are explicit
> hypotheses; the elliptic result is an upper bound, and the function-field
> appendix does not prove sharpness or smooth-pool existence. Original JSON
> and PDFs are unchanged. See [current audit status](integration-review-status.md#current-correctness-audit-2026-10-22).

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

## AG5 result: the Popovych burden jump — first quantified evidence (2026-10-21)

*Deliverables: `doc/arith-geom.tex` §5 (+ recompiled PDF),
`code/ag5_popovych_check.py`, `data/generated/ag5_popovych_check.json`.
Subsumes old plan item B4.*

**Headline.** The second Popovych section X+2 **destroys the inversion
collapse** that made the Agrawal attack supply-feasible. The L–P mechanism
against the pair pays burden = d (full depth) at *every* parity of d, so

> **burden_Pop(r) = min{d : d | r−1, d ≥ 3} ≥ 3 for every modulus r** —
> global optimum 3 (iff 3 | r−1) vs Agrawal's 2; at Popovych's own r = 5
> the burden is **4**: p−1, p+1 AND p²+1 simultaneously smooth. The
> twin-smooth (burden-2) regime does not exist for the pair at any r.

**Why (the structural lemmas, Theorem 5.5 in the tex).**
1. *Trivial stabilizer* (Lemma 5.3, unconditional and global): for every
   γ ≠ 1 in (Z/r)×, the ratio (ζ^γ+2)/(ζ+2) is not even a unit of Z[ζ_r]
   (a prime q | (ζ+2) has ζ ≡ −2 of order r mod q; q | (ζ^γ+2) would force
   ζ^{γ−1} ≡ 1, i.e. γ = 1). Contrast X−1: its zero {1} is Galois-stable
   ((ζ−1) is the totally ramified prime above r), which is exactly what
   furnished σ₋₁(ζ−1)/(ζ−1) = −ζ^{−1} ∈ μ_2r — the AG2 collapse. The zero
   −2 of X+2 has trivial stabilizer, so no collapse at any depth.
2. *Global independence* (Lemma 5.2): N(ζ−1) = r, N(ζ+2) = (2^r+1)/3,
   coprime supports (gcd(r, 2^r+1) = gcd(r,3) = 1) — no multiplicative
   identity ties ord(ζ+2) to ord(ζ−1); rank 2 mod torsion.
3. *Level-1 component* (Lemma 5.1): the X=1 component of the second
   congruence is 3^n ≡ 3 (mod n) (base-3 Fermat) — free for Carmichael n
   but, unlike the first section's 0 = 0, already nontrivial at level one.
4. Hence ρ'_r(p) = ord(X+2) generically spans ALL levels e | d including
   the top level Φ_d(p) (dim φ(d)); lcm(ρ, ρ') spans all of p^d−1; burden
   Σ_{e|d} φ(e) = d. Char-3 degeneracy noted: mod p=3 the sections coincide.

**Burden comparison table** (deltas over Agrawal): +2 at r ∈ {5, 17, 29,
41}; +1 at r ∈ {13, 37}; 0 at the r ≡ 3 (mod 4) moduli (where Agrawal was
already ≥ 3 and both share full depth). Minima: 2 (Agrawal, any r ≡ 1 mod
4) vs 3 (Popovych, needs 3 | r−1).

**Cost at measured scale** (Prop 5.6; Dickman grid validated to <2% against
reference values): at the frozen spec (p ≈ 51 bits, measured burden-2 ratio
13.8, pool 2.5e5), the extra ~102-bit quadratic level is a pure Dickman tax
— ρ(9.9) ≈ 3.9e-11 over the Q₊ base, ρ(7.5) ≈ 1.8e-7 even over the generous
B′ base — so ratio → 5e-10 … 2.5e-6 and pool → 1e-5 … 0.05 elements:
**the pair-mechanism harvest is empty at any feasible scale.** Φ₄(p) is
pinned once p is, so the partition-first trick that pays for p∓1 cannot
remove this tax. Solver side: the group gains the level-4 components, so
identity-density drops below H7's 0.004 — the N1/A10 obstruction for the
pair strictly contains Agrawal's.

**Numerical verification** (`code/ag5_popovych_check.py`, 56 sample primes,
same (r,d) grid as AG2):

| check | statement | result |
|---|---|---|
| P1 | Frobenius matching for X+2 | 56/56 |
| P2 | X−1 collapse bound does NOT absorb X+2 (even d) | 35/36 |
| P3 | top level e = d present in ρ'_r(p) | 55/56 |
| P4 | large primes of all levels e \| d divide ρ' | 47/47 (~0.28 misses expected) |
| P5 | burden_Pop vs burden_Agr over the 11 A11 moduli | as stated above |
| P6 | gcd(r, 2^r+1) = 1 (independence) | 11/11 |

The single P2/P3 exception is r=13, p=5, where Φ₄(5) = 26 = 2·13 has no
prime outside 2r at all — the top level is vacuous for that tiny prime, a
small-prime degeneracy predicted by the generic model, not a collapse.

**Interpretation & scope.** First quantified evidence in either direction
on Popovych beyond search ranges (README §4 lists none): every known
counterexample mechanism is strictly more blocked against the pair —
≥ 1 extra torus dimension globally, 2 extra at r = 5 — and the only
supply-feasible regime this project ever measured does not exist for it.
Caveats unchanged: mechanism-scope (Remark 2.3) and generic sharpness
(Remark 3.9), now applied to both sections; this quantifies the failure of
the only known engine, not the truth of the conjecture. Candidate for a
standalone short note per the plan.

## AG3 result: the impersonation hierarchy — definitions, prior art, census (2026-10-21)

*Deliverables: `doc/arith-geom.tex` §6 (+ recompiled PDF, now 12 pp),
`code/ag3_hierarchy_check.py`, `data/generated/ag3_hierarchy_check.json`,
README §4a (literature additions). Gate: low-risk item, complete.*

**Definitions (Def 6.1).** An *impersonation cell* is a level set S with
Frobenius powers (i_e): Φ_e(p) | n − p^{i_e} for e ∈ S, at every p | n ⟺
x^n = x^{p^{i_e}} on the T_e(F_p) points. Normalizations: at level 1 all
powers coincide; at level 2, p^i ≡ (−1)^i (mod p+1), so **only the parity
of i₂ matters, and the parity is a sign** (even ↔ target +1, odd ↔ −1).

**Dictionary (Prop 6.2).** Carmichael = ({1}, 0); Lucas–Carmichael =
({2}, 1); **Williams numbers** (H. C. Williams 1977; Echi's "1-Williams")
= ({1,2}, (0,1)) = uniform depth-2 power 1, n ≡ p (mod (p²−1)/2) — i.e.
exactly the L–P/A329223 objects, which turn out to have an established name
and a 1977 pedigree; Howe's order-m Carmichael numbers = depth r ≤ m with
any powers (his Theorem 1), "rigid" = all powers 0; AG2's theorem = the AKS
mechanism forces level set {e | d'} (minimum = the Williams cell); AG5 =
Popovych forces full depth {e | d}. Grantham's Frobenius pseudoprimes =
same idea against one quadratic section.

**Status of the cells (Thm 6.3, survey; prior-art check of the plan).**
- ({1}, 0): infinite (AGP 1994). 105 below 10⁷ (census matches known count
  — validates the census code).
- ({2}, 1): infinite — **Wright 2018** (by-product of elliptic Carmichael
  infinitude; arXiv:1609.00231). 135 below 10⁷.
- Williams ({1,2}, (0,1)): **open even for nonemptiness**; ≥ 4 prime
  factors (Williams 1977); **none below 2^64** (McIntosh–Mitra, JNT 147
  (2015) 81–91), finiteness with all-but-three factors fixed. The Agrawal
  cell refines this, a fortiori empty.
- Depth-2 any parity (Howe order 2): **NONEMPTY** — Howe's explicit rigid
  example n = 443372888629441 = 17·31·41·43·89·97·167·331, **re-verified
  here** (p²−1 | n−1 for all 8 primes; level-2 matching powers {0,2,4},
  all even = rigid parity; not Williams). Order-m needs ≥ m+2 prime factors
  (Eterevsky–Vsemirnov, Fib. Quart. 42 (2004)); no order-3 known; Howe's
  heuristic predicts infinitude at every order.
- Elliptic rungs (AG4's raw material): Silverman's elliptic Korselt
  criteria (Acta Arith. 155 (2012)); Ekstrom–Pomerance–Thakur conditional
  infinitude (J. Aust. Math. Soc. 92 (2012)); Wright unconditional.

**The structural punchline (Remark 6.4): sign splitting, not depth, is the
wall.** Rigid depth-2 impersonators exist at 4.4·10¹⁴ while the same-level
Williams cell is empty to 2⁶⁴. The rigid cell is one-sided (n ≡ 1 mod
lcm(p²−1): single AGP-style target 1, no coprimality needed between p−1 and
p+1 parts) — the AGP machine built it at modest size. The Williams parities
(0,1) force targets (+1, −1), which conflict on shared prime powers, forcing
the coprime side-split — exactly the side-coprimality whose harvest collapse
is N1 and whose two-sided solver obstruction is A10. The project's negative
results are precisely about the sign-split cells; Howe's example shows the
unsplit cells are reachable. Validity (n ≢ ±1 mod r) pins the AKS
construction to a sign-split cell: a rigid n passes the component equation
only with j = 0, i.e. n ≡ 1 (mod r) — inside the exception clause (Váňa's
observation about Carmichael numbers passing T(−1,n,r)).

**A sharp concrete datum (H4).** Howe's rigid n has n ≡ 1 (mod 5) but
**does not pass T(−1, n, 5)**: rigidity controls the p²−1 part of ρ₅(p)
but not the extra μ_2r-torsion (the factor 2r in the AG2 collapse bound) —
precisely the 2-adic bookkeeping the L–P mod-80 conditions exist to fix.
Even the exception-clause pass needs arranged torsion, not just depth.

**Numerical verification** (`code/ag3_hierarchy_check.py`): H1 Howe example
confirmed (order 2, rigid, not Williams); H2 dictionary on T₂ 60/60 random
(p, n, i); H3 census below 10⁷: 105 / 135 / 0 / 0 (Carmichael /
Lucas–Carmichael / Williams / Howe order-2; smallest 561 / 399 / — / —);
H4 as above.

**Imports for the negative-result paper.** (1) Vocabulary: the target
objects are *Williams numbers in prescribed congruence cells*. (2) Search
floor: McIntosh–Mitra's 2^64 supersedes/complements the Pinch-table
emptiness already cited. (3) Calibration: Howe's construction is the
nearest success of the AGP machine to our cell; the one-sided vs sign-split
contrast is the structural explanation of why it succeeded where H8/N1
collapsed. README §4a now carries the reference block.

## AG4 result: the elliptic axis is closed — the stabilizer-index floor (2026-10-21)

*Deliverables: `doc/arith-geom.tex` §7 (+ recompiled PDF, now 14 pp),
`code/ag4_elliptic_check.py`, `data/generated/ag4_elliptic_check.json`,
status annotation in `doc/arith-geom-plan.md`. **Gate AG-G2: NOT passed;
AG4(c) cancelled** — the write-up extends the negative result instead.*

**Formulation (AG4a).** A canonical elliptic Agrawal congruence exists
only for CM curves: an elliptic curve carries a canonical Frobenius-lift
family (Λ-structure) iff it has CM (Borger–Gurney, arXiv:1710.08674); for
non-CM E there is no analogue of X ↦ Xⁿ, and trying all traces is
exponential. CM form (Def 7.1): E with CM by O_K (units U of order w = 4
at j=1728, 6 at j=0), eigenline kernel polynomial g of E[r], section
f = x; test ∃τ ∈ (Z/r)×: fⁿ ≡ f∘[τ] (mod n, g) — poly(r) candidates;
prime n passes with τ = λ_n (the Frobenius scalar on the eigenline). The
exception clause must be **τ ∈ U**: U-cells are the elliptic analogue of
rigid Carmichael numbers (one-sided, AGP-constructible per §6), exactly as
n² ≡ 1 (mod r) is σ_n ∈ {±1} — **the clause is the stabilizer** (the
§1/§6 principle, now uniform).

**The master theorem (Thm 7.3, stabilizer-index floor).** For a section f
with scalar Frobenius λ in cyclic Γ and unit-stabilizer U (the subgroup
acting on f by root-of-unity cofactors):

> **burden = k' = [⟨λ⟩ : ⟨λ⟩ ∩ U]** (levels e | k'; exact collapse
> identities give the upper bound, generic sharpness the attainment), and
> **validity (λ ∉ U) forces k' ≥ 2.**

One theorem now subsumes everything: (μ_r, X−1): U = {±1} → AG2's d/2-d;
(μ_r, X+2): U = {1} → AG5's full depth; (E_{j=1728}, x): U = μ₄ →
burden m/gcd(m,4); (E_{j=0}, x): U = μ₆-image → m/gcd(m,6). The collapse
identities are exact as before: x([i]S) = −x(S) on y² = x³ − x gives
x(T)^{p^e} = −x(T) when λ^e ≡ ±i.

**Why the elliptic world looked better and isn't.** Cells with λ ≡ ±i
collapse the section order to level 1 (x(T)^{p−1} = ±1: burden 1 — the
thing AG2 proved impossible on every torus route!) — but all order-4
elements of the cyclic (Z/r)× ARE ±i, i.e. these cells lie inside U =
the exception clause, mirroring rigid Carmichaels inside n ≡ ±1 (mod r).
For valid λ the floor returns to 2 (order-8 λ at j=1728: x^{p²} = −x,
ord | 2(p²−1)), and burden-2 cells demand **p−1 and p+1 smooth — the same
twin-smooth condition** — with a ray-class slice (λ_p of order 2w mod r)
replacing the mod-80 cell and unit-twisted mixed targets reproducing the
sign-split structure of §6. So the N1/A10 harvest+solver obstruction
transfers verbatim. Supersingular cells (a_p = 0, φ² = [−p]) collapse via
⟨p⟩ mod r exactly as in the torus case — no separate escape.

**Burden comparison over the A11 moduli (j=1728 vs torus):** elliptic ≥
torus at every r — equal at r ∈ {7, 11, 17, 19, 23, 31, 41}, strictly
worse at {13: 3v2, 29: 7v2, 37: 3v2}, degenerate at r=5 (every λ-order
divides 4: all cells exceptional — the elliptic test can't even be run
non-trivially at Popovych's modulus). Floor 2 attained iff 8 | r−1
(j=1728) or 12 | r−1 (j=0).

**Numerical verification** (`code/ag4_elliptic_check.py`, division
polynomials built from the recursion and checked, E: y² = x³ − x,
r ∈ {13, 17}, 10 ordinary split primes each): E1 ψ_r degrees and factor
degrees all consistent; E2 Frobenius closure all factors; E3 all 45
exceptional (λ ∈ μ₄) cells have k ≤ 2 as predicted, sharpness 112/112;
**E4 measured valid-cell floor: r=13 → 3, r=17 → 2, exactly the index
formula** (r=17 data shows the whole ladder: deg-4 factors with
x^{p²} = −x at burden 2, deg-8 with k'=4 at levels {1,2,4}, deg-16
mixed); E5 elliptic ≥ torus at all 11 moduli.

**Caveats.** Standing ones (mechanism scope, generic sharpness) plus:
the formulation is CM-bound (non-CM not well-posed); eigenline data is
certificate-style for general n (explicit only for special sequences à la
Gurevich–Kunyavskii / elliptic periods); the elliptic no-further-collapse
uses the disjoint-support argument for division values (elliptic-unit
independence), same epistemic status as Lemma 5.3's cyclotomic version
with empirical backing.

**Consequence for the AG track.** All four planned mathematical items
(AG2, AG3, AG5, AG4) are done; the negative result now covers: every AKS
modulus r (A11/AG2), the Popovych pair (AG5), and the CM-elliptic axis
(AG4), unified by the stabilizer-index theorem. Remaining: AG1's
exposition polish (§1 todos) and the optional AG6 function-field appendix;
then the material is ready to fold into the negative-result paper.

## AG5b addendum: the constant 2 is immaterial (2026-10-22)

*Prompted by reviewer/user question; `code/ag5b_constant_check.py`,
`data/generated/ag5b_constant_check.json`; Remark 5.8 in the tex and the
matching remark in `doc/popovych-note.tex`.*

For any integer c ∉ {0, ±1}, the trivial-stabilizer lemma and the full
Popovych burden jump hold verbatim for the pair {X−1, X+c}; c enters only
through the norm Φ_r(−c) = (c^r+1)/(c+1) (finitely many excluded p, with
p | c(c+1)), the excluded modulus r | c+1, and the level-1 component
(base-(c+1) Fermat). **What must be avoided is exactly degeneracy of the zero −c: it must be a
point of G_m avoiding the rational torsion {±1}**, i.e. c ∉ {0, ±1}. The
c = 0 exclusion is vacuous, not subtle (X is a monomial: (X)^n ≡ X^n is an
identity in every ring; the zero sits at the origin, off the torus). Among
nonzero c, the subtle case is c = +1, not just c = −1: the zero of X+1 is −1, inversion-fixed, so the collapse SURVIVES
((ζ+1)^{p^{d/2}} = ζ^{−1}(ζ+1), ord | r(p^{d/2}−1) at even d), and
ζ+1 = (ζ²−1)/(ζ−1) is multiplicatively dependent on the ζ−1 orbit — the
pair {X−1, X+1} adds no rank and no burden. In stabilizer terms:
U(X±1) = {±1}, U(X+c) = {1} otherwise; c = 2 is merely the smallest
valid choice (c = −2 works equally; Mersenne norm 2^r − 1).

Measured (20 primes over (r,d) ∈ {(5,4),(13,4),(7,6),(7,3),(11,5)},
c ∈ {1,2,3,−2,5}): X+1 collapses 22/22 at even d with top level never
needed (and full support at odd d 13/13, where no section collapses);
c ∈ {2,3,−2,5} show no collapse and full top-level presence except the
single already-documented vacuous point (r,p) = (13,5).

**Sharper (2026-10-22, prompted by the follow-up question):** the X+1
variant is *mechanism-equivalent* to Agrawal's conjecture (Prop in the tex
and note): since ζ+1 = (ζ²−1)/(ζ−1) and ρ_r(p) controls all conjugates of
ζ−1, the mechanism congruence n ≡ p^j (mod lcm(r, ρ_r(p))) plus the
Carmichael condition imply T(+1, n, r) outright — every mechanism-built
Agrawal counterexample passes the X+1 test for free. Measured (ag5b check
W): 48/48 synthetic mechanism instances pass T(+1); 0/48 pass T(+2).

## AG track wrap-up: COMPLETE (2026-10-21)

*Final deliverables: `doc/arith-geom.tex` v1.0 (15 pp, compiled; AG1
exposition finished — Prop 1.2 untruncated test, Wilkerson/Borger/pseudofield
citations in place, no TODOs remain; Appendix A = AG6), this findings file,
the annotated plan, four verification scripts (`code/ag{2,3,4,5}_*.py`) with
JSON outputs, and README §4a.*

**AG1 (done).** §1 now states the full dictionary: the untruncated Fermat
identity characterizes primality (AKS Lemma 2.1); Z[Z/r] is a Λ-ring whose
ψ^p are Frobenius lifts (Wilkerson's criterion), so *n prime ⟺ ψ^n is a
Frobenius lift at n*, with the AKS congruence as the one-section test;
Borger's F₁-descent reading and L–P pseudofields cited as the conceptual
and operational forms. The conjecture = a quantitative descent statement;
the exception clause = the real-subfield decomposition group.

**AG6 (done, timeboxed as planned).** Appendix A: the Carlitz-module
mirror over F_q[t]. The mechanism analysis transposes (constant-field
tori, stabilizer-index with U = image of F_q^×); both heuristic
ingredients — generic sharpness and the density counts — become theorems
via Weil's RH for curves (function-field Chebotarev); and the problem
carries no complexity content there since irreducibility testing is
unconditionally deterministic polynomial time. Placement conclusion: the
part of the Agrawal problem resisting the mechanism analysis over Z is
exactly the unconditional-equidistribution (GRH-grade) gap. No claims made
about Carlitz–Carmichael literature (not needed).

**Track outcome summary.**

| item | result | status |
|---|---|---|
| AG2 | torus dimension-count theorem: burden = d' ≥ 2, min at {1,2} (twin-smooth), for every AKS r; A11 upgraded to a corollary | done; gate AG-G1 substantially passed (sharpness localized to Prop 3.5) |
| AG5 | Popovych burden ≥ 3 everywhere, 4 at r=5; first quantified evidence beyond search ranges; standalone-note candidate | done |
| AG3 | impersonation hierarchy; L–P targets = Williams numbers (open, none < 2^64); sign-splitting, not depth, is the wall (Howe contrast) | done |
| AG4 | elliptic axis closed: stabilizer-index theorem (burden = [⟨λ⟩:⟨λ⟩∩U] ≥ 2) subsumes AG2/AG5/CM curves | done; gate AG-G2 NOT passed, AG4(c) cancelled |
| AG1 | Frobenius-lift dictionary, full exposition | done |
| AG6 | function-field mirror appendix | done |

**Unifying result of the track:** the stabilizer-index theorem (Thm 7.3).
Every one-section Frobenius test on a one-dimensional group — μ_r with
X−1 or X+2, CM elliptic curves with x — has burden [⟨λ⟩ : ⟨λ⟩ ∩ U], U the
unit-stabilizer of the section, and every credible exception clause equals
U; validity therefore forces burden ≥ 2, attained exactly at the
twin-smooth (sign-split) cells whose harvest/solver economics this
project's N1/A10 measurements closed.

**Handoffs.**
1. *Negative-result paper* (`doc/negative-result-plan.md`, separate
   branch): fold in §3 (Thm 3.6 + Cor 3.7 for the option-(c) section,
   caveats Rem 2.3/3.9), §6 (related-work vocabulary: Williams numbers,
   the 2^64 floor, the Howe sign-split contrast), §7 (the elliptic
   extension + Thm 7.3 as the structural spine), Appendix A (the
   discussion of what a proof would need).
2. *AG5 standalone note* on Popovych: §5 is self-contained; candidate for
   a short arXiv note after the main paper.
3. *Option (b)* (`doc/option-b-problem.md`) is unaffected: it remains the
   only live constructive direction, now with the added knowledge that
   any solver breakthrough would unblock the torus route only — the
   elliptic and Popovych variants stay strictly harder.

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
