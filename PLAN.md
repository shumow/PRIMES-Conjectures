# Plan: Constructing a Counterexample to Agrawal's Conjecture

**Goal.** Exhibit a composite n and prime r ∤ n with
(X−1)^n ≡ X^n − 1 (mod n, X^r − 1) and n² ≢ 1 (mod r).
We do **not** seek the smallest counterexample. Any counterexample, of any size,
disproves the conjecture; the Lenstra–Pomerance (L–P) heuristic says candidates get
*denser* at large sizes, and their construction is deterministic: if the arithmetic
side conditions hold, the congruence is guaranteed — no verification lottery.

See `doc/background.tex` for the mathematical background at paper level.

## Mathematical foundation

**Theorem (Lenstra–Pomerance, r = 5; as stated in Váňa 2009, Thm 3.1).**
Let n = p₁⋯p_k, distinct primes, with
  (a) k ≡ 1 or 3 (mod 4)  [i.e. k odd],
  (b) pᵢ ≡ 3 (mod 80) for all i,
  (c) pᵢ − 1 | n − 1 for all i  (n is Carmichael),
  (d) pᵢ + 1 | n + 1 for all i  (n is Lucas–Carmichael).
Then (X−1)^n ≡ X^n − 1 (mod n, X⁵ − 1) while n² ≢ 1 (mod 5).
(Check: p ≡ 3 (mod 5) ⇒ n ≡ 3^k ≡ 3 or 2 (mod 5) for k ≡ 1, 3 (mod 4).)

**Key structural lemma (side-coprimality).** If n satisfies (c) and (d), then for all
i, j (including i = j): gcd(pᵢ − 1, pⱼ + 1) | 2.
*Proof:* an odd prime q dividing both divides n − 1 and n + 1, hence 2. ∎
Consequence: the odd prime factors supporting {pᵢ − 1} and {pᵢ + 1} form **disjoint
sets**. This is the real reason simultaneous Carmichael/Lucas–Carmichael numbers are
so elusive, and it dictates the two-sided design below.

**2-adic bookkeeping.** p ≡ 3 (mod 16) ⇒ v₂(p−1) = 1, v₂(p+1) = 2. p ≡ 3 (mod 5) ⇒
5 ∤ (p−1)(p+1). For k odd and all p ≡ 3 (mod 4): n ≡ 3 (mod 4), so the 2-adic parts
of (c), (d) hold automatically. The search lives entirely in odd moduli prime to 5.

**Reduction to subset-product.** Fix disjoint sets of odd primes Q₋, Q₊ (≠ 5) and a
pool
  P = { p ≤ x : p ≡ 3 (mod 80), (p−1)/2 is Q₋-smooth, (p+1)/4 is Q₊-smooth }.
Let Λ₋ = 2·lcm{(p−1) : p ∈ P}, Λ₊ = 4·lcm{(p+1) : p ∈ P}. It suffices to find
S ⊆ P, |S| odd ≥ 3, with n = ∏_{p∈S} p satisfying
  n ≡ 1 (mod Λ₋) and n ≡ −1 (mod Λ₊).
(Strictly stronger than (c),(d) — using the full lcm linearizes the problem.)
Taking discrete logarithms component-wise (Pohlig–Hellman is cheap: all group orders
are Q-smooth), this is a 0/1 subset-sum over ⊕ᵢ Z/mᵢ with an odd-cardinality
constraint. Heuristic solvability: 2^{|P|} ≫ |G| where |G| ≈ φ(Λ₋)φ(Λ₊), i.e.
  |P| ≳ bits(Λ₋) + bits(Λ₊), plus slack for the solver.

## Phases

### Phase 0 — Foundations (correctness before compute)
- [ ] Re-derive the L–P theorem from scratch (both k mod 4 cases; we currently rely
      on secondary sources — the AIM notes and Váňa's thesis. Váňa says the k ≡ 3
      case was "left as an exercise" in the original). Write the proof in
      `doc/background.tex` appendix or a separate note. Any error here poisons
      everything downstream.
- [ ] Unit-test the machinery numerically: for random small n ≡ 2, 3 (mod 5),
      verify T(−1, n, 5) directly against the per-prime criterion
      (n ≡ λ(p) mod ρ(p), ρ(p) | 10(p²−1)) used by Váňa. Test the theorem's
      *congruence conclusion* on synthetic prime tuples satisfying (b)–(d) with (c),(d)
      relaxed to small moduli.
- [ ] **Map the admissible local conditions.** The mod-80 cell is (probably) one
      of several admissible (mod 2^k, mod 5) condition patterns. Re-derive which
      v₂ patterns and residues work — uniform pools with v₂(p+1) > 2 may be fine
      with adjusted conditions. Payoff: if any admissible cell is reachable by the
      isogeny-literature boosting polynomials p = 2xⁿ − 1 (natively
      side-separating, and two-sided smoothness at half bit-size — see
      doc/twin-smooth-review.md §2), the search gets dramatically easier. As
      stated, mod 80 is provably unreachable by n = 2, 3 boosts.
- [ ] Decide whether to also target general r (the ord_r(p) = 2 cases, where only
      p² − 1 needs controlling) — potential free win if some r gives thinner
      conditions than r = 5. Defer unless r = 5 pool statistics look bad.
- [ ] Due diligence: has anyone run this at scale? Check for unpublished attempts
      (ask Pomerance / Granville; search BOINC archives beyond Primaboinca).

### Phase 1 — Pool harvesting + go/no-go statistics
- [ ] **Phase 1a — run on existing data first (see doc/twin-smooth-review.md).**
      Our pool primes p = 2m+1 are exactly twin-smooth pairs (m, m+1) with prime
      sum — the objects the isogeny community mass-produced for B-SIDH/SQIsign.
      Clone the public CHM implementation (Bruno et al., ASIACRYPT 2023); the
      B = 547 run yields ~82M twin pairs. Slice m ≡ 1 (mod 40) (⟺ p ≡ 3 mod 80
      + all 2-adic/mod-5 conditions), filter 2m+1 prime, compute factor
      signatures, and run the coloring optimization for the max consistent
      subpool vs. realized bits(Λ₋)+bits(Λ₊). **This is the go/no-go number and
      needs no new number-theoretic software.** Calibrate density models against
      the complete Størmer sets (B ≤ 113, Pell-equation enumeration).
- [ ] **Harvester design (constructive, not sieved):** enumerate Q₋-smooth odd m,
      set p = 2m + 1; test p ≡ 3 (mod 80), p prime (BPSW; prove later), then
      trial-divide (p+1)/4 over Q₊. This scales to x = 10¹²⁺ without sieving.
- [ ] **Asymmetric side design (first thing to evaluate):** Q₊ = all odd primes
      ≤ B except 5 (the "random side" — (p+1)/4 smoothness is Dickman-governed);
      Q₋ = primes in (B, B′] (the "constructive side" — m built from a controlled
      set of medium primes, disjointness from Q₊ automatic). Tune B, B′, x,
      #medium-primes-per-m.
- [ ] Measure: pool yield per CPU-hour; realized bits(Λ₋) + bits(Λ₊) as a function
      of pool size (exponents capped at what actually appears — expect lcm growth to
      saturate); distribution of ω(p±1).
- [ ] **Go/no-go:** projected |P| ≥ c·(bits Λ₋ + bits Λ₊) for c ≈ 2–3 at achievable
      compute. Ballpark target: group ~ 15–30k bits ⇒ pool ~ 50–100k primes.
      If unreachable for every (B, B′, x) tried, write up the negative result
      (the quantified obstruction is publishable on its own) and pivot to
      general-r / Hegde–Devaraj classes.

### Phase 2 — Solver
- [ ] Pohlig–Hellman tables: discrete logs of every pool prime in each cyclic
      component of (Z/Λ₋)* × (Z/Λ₊)*.
- [ ] 0/1 solver, in escalating order of sophistication:
      (i) staged CRT à la Löh–Niebuhr (satisfy one prime-power component at a
      time, maintaining a large family of partial solutions);
      (ii) Wagner's generalized birthday / k-list algorithm on the component
      lattice (the pool-rich regime is exactly where GBP shines);
      (iii) lattice reduction (BKZ) only for a final low-dimensional correction
      step — it will not scale to the full system.
- [ ] Odd-|S| constraint = one extra Z/2 component. n composite is automatic
      (|S| ≥ 3, distinct primes, squarefree).

### Phase 3 — Verification & write-up
- [ ] Assemble n. Independently verify, with two implementations (e.g. python/sympy
      and C/FLINT): distinctness and primality of all pᵢ (proven, e.g. ECPP or
      Pocklington — the pᵢ are small); conditions (a)–(d); the congruence
      T(−1, n, 5) computed directly; n² ≢ 1 (mod 5).
- [ ] Test Popovych's second congruence (X+2)^n ≡ X^n + 2 on the found n — the
      construction does not guarantee it, so either outcome is informative
      (counterexample to both, or evidence separating the conjectures).
- [ ] Write the paper. A negative result (quantified infeasibility of the L–P
      route at reachable scales) is also worth writing up.

## Heuristic assumptions ledger

What is proven vs. assumed in our feasibility estimates:
1. **Theorems (unconditional):** gcd(p−1, p+1) = 2; the side-coprimality lemma;
   the 2-adic bookkeeping given p ≡ 3 (mod 16); Størmer finiteness of twin
   B-smooths for fixed B.
2. **Exact but unmodeled local corrections:** for prime p and odd prime q,
   P(q | p∓1) = 1/(q−1) each, mutually exclusive (not independent 1/q events).
   Multiplies a computable singular-series constant into density estimates;
   does not change exponents.
3. **Conjectural (standard but unproven):** independence factorization
   P(both sides smooth) ≈ ρ(u₋)ρ(u₊); and even the one-sided density
   #{p ≤ x : p−1 y-smooth} ∼ ρ(u)π(x) is an open conjecture (Erdős–Pomerance
   line; only weaker lower bounds are proven — Friedlander, Baker–Harman).
4. **Empirical anchor:** the twin-smooth datasets (CHM B=547: 82M pairs;
   complete Størmer sets B ≤ 113) let us *measure* rather than assume pool
   densities — the heuristics only steer where we point the search.

## Risks
1. **Side-coloring thins the pool below the linear-algebra threshold.** This is the
   most likely failure mode and precisely why the smallest counterexample is believed
   enormous. Phase 1 quantifies it before we invest in the solver.
2. **Secondary-source error in the theorem statement** (mod-80 condition, k mod 4
   cases). Mitigated by Phase 0 re-derivation.
3. **lcm blow-up:** each pool prime enlarges Λ±; if bits(G) grows linearly with |P|
   the feasibility inequality never closes. Mitigation: cap exponents, restrict m to
   few medium primes, measure saturation early (Phase 1 metric).
4. **Prior art:** the construction has been public since 2003. Due-diligence item in
   Phase 0; worst case we replicate a known negative and say so.

## Tooling
- Prototype: Python + sympy/gmpy2. Production harvester + solver: C or Rust with
  FLINT/GMP. Everything deterministic and seeded; all found pools/solutions
  committed as data with generation parameters.
- Repo layout: `doc/` (notes, paper), `harvest/`, `solve/`, `verify/`, `data/`.

## References
See `doc/background.tex` bibliography and `README.md` (literature survey).
