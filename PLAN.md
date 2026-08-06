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
- [ ] Decide whether to also target general r (the ord_r(p) = 2 cases, where only
      p² − 1 needs controlling) — potential free win if some r gives thinner
      conditions than r = 5. Defer unless r = 5 pool statistics look bad.
- [ ] Due diligence: has anyone run this at scale? Check for unpublished attempts
      (ask Pomerance / Granville; search BOINC archives beyond Primaboinca).

### Phase 1 — Pool harvesting + go/no-go statistics
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
