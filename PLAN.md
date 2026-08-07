# Plan v2: Constructing a Counterexample to Agrawal's Conjecture

*Rewritten 2026-08-07 after Phase 1a calibration. v1 is in git history
(commits 552330e..1925d7e). Supporting documents: doc/working-paper.pdf
(math), data/FINDINGS.md (measurements), doc/twin-smooth-review.md
(literature).*

## What we know now (each item measured or proved, see FINDINGS.md)

1. **The reduction stands.** Pool primes p = 2m+1 with m ≡ 1 (mod 40),
   (m, m+1) twin smooth over disjoint side-sets Q₋ | Q₊; subset with odd
   cardinality and product ≡ (1 mod Λ₋, −1 mod Λ₊) ⇒ counterexample
   (working paper Prop 3.1, machinery unit-tested).
2. **The 0.06 invariant.** For partition-agnostic twin supply (sieve, CHM,
   any completeness level, B = 100–547), the best side-partition keeps
   ≈ 0.06 elements per demand-bit — element-greedy and direct
   partition-space search agree. Feasibility needs ≳ 1–3. **The
   dataset-mining route is dead as the primary hunt.**
3. **Partition-first harvesting sidesteps the invariant.** Fix Q₋, Q₊ first;
   enumerate m over Q₋ only; test (m+1)/2 over Q₊ only. Every hit is
   compatible by construction; the cost moves into per-candidate yield,
   which is a local (Dickman-type) probability, not a global combinatorial
   obstruction.
4. **Supply curves are anchored.** N(B) ~ B^5 (published counts 13,374 /
   346,192 / 82M at B = 100/200/547); our closure reproduces the complete
   sets to 99.7–99.98% with exact largest elements; PTE corpus contributes
   0 pool candidates (residue coverage ~40× poorer than generic twins).
5. **Boost obstruction.** 2xⁿ−1 ≡ 3 (mod 16) is unsolvable for all n ≥ 2:
   the mod-80 cell is unreachable by the boost family (working paper
   Prop 6.1). Whether *other* admissible cells exist is open (Question 6.2).

## Track A — partition-first harvester (main line)

**Design.** Asymmetric split. Q₊ = all odd primes ≤ B except 5 (the tested,
density-critical side). Q₋ = a set of t medium primes in (B, B′] (the
enumerated side — enumeration needs no density, only combinatorial volume).
Disjointness is automatic. Enumerate candidates m = ∏_{q∈Q₋} q^{e_q}
(j = Σe_q factors, j ≈ 3–5) restricted to m ≡ 1 (mod 40) and a size window;
per candidate, trial-divide (m+1)/2 over Q₊ (early-abort), then BPSW on
p = 2m+1.

**Back-of-envelope economics at B = 547, B′ = 5000** (to be replaced by A1
measurements): t = 568 medium primes; j = 3 candidates ≈ 3·10⁷ (more with
j = 4 and exponents); per-candidate success ≈ ρ(u)·(1/ln p) ≈ 10⁻³·⁵ at
m ~ 2³⁰–2⁴⁰ ⇒ pool ~ 10⁴. Demand ≈ 12.3t + θ(B)/ln2 + exponent slack ≈
7000 + 800 + slack bits. Ratio ≈ 1.2 — **marginal, which is exactly why A1
measures before A3 commits compute.** Knobs: t, B, B′, j, exponent caps
(reject q^e > 2¹³ on the plus side), size window, and only-count-used-primes
demand accounting.

- **A1. Yield calibration — DONE 2026-08-07, GATE G1 PASSED.** Measured
  ratios up to 44x (B=2003, B'=20030, j=4); j=4, B'/B=10 is the sweet
  spot; details in data/FINDINGS.md. Original spec follows.
  (prototype, python→C). Enumerate ~10⁶ candidates
  across a grid (B ∈ {547, 1000, 2000}, B′/B ∈ {5, 10, 20}, j ∈ {3,4,5},
  m ∈ 2²⁵…2⁴⁵); measure the true yield curve (the ρ_Q analogue with the
  Q₋-exclusion, mod-40 class, and prime-sum filters folded in) and the
  realized demand-bits growth as pool accumulates. Deliverable: yield
  table + fitted model in FINDINGS.md.
  **Gate G1: some regime shows measured pool/demand ≥ 0.5 at prototype
  scale with a fitted extrapolation ≥ 2.5 at production scale.** (The 0.06
  baseline is the number to beat; partition-first must show ≥ ~10×.)
- **A2. Parameter optimization.** Maximize projected pool/demand over the
  measured curves; choose final (Q₋, Q₊, caps, window). Use the B=200/547
  twin corpora to sanity-check the model where they overlap. Deliverable:
  frozen harvest spec committed to the repo.
  **Gate G2: projected pool ≥ 2.5 × demand bits ≥ 3000 usable elements.**
- **A3. Production harvest.** C implementation (adapt chm_closure.c
  infrastructure; pthreads; ~10⁹–10¹¹ candidates ≈ days of multicore).
  Store elements with full factorizations + deterministic provenance.
- **A4. Subset-product solver.** Pohlig–Hellman DL tables per cyclic
  component (all orders smooth by design); then staged CRT à la
  Löh–Niebuhr — satisfy one prime-power component at a time, maintaining a
  basket of partial solutions, parity (|S| odd) as a Z/2 component; Wagner
  k-list as the fallback for the final hard components; LLL only for a
  terminal low-dimensional correction.
  **Gate G3 (before running on real data): solver succeeds on synthetic
  instances of the same dimensions** (random vectors in the same group,
  planted solution) — separates solver bugs from data infeasibility.
- **A5. Assembly & verification.** Two independent implementations
  (python/sympy and C/GMP or FLINT) re-check: primality of every pᵢ
  (proven, Pocklington/ECPP — the pᵢ are small), conditions (a)–(d),
  direct computation of T(−1, n, 5), n² ≢ 1 (mod 5). Test Popovych's
  (X+2)ⁿ congruence on the find. Write-up either way — a G1/G2 failure
  becomes a quantified-infeasibility section in the working paper.

## Track B — theory (Phase 0, runs parallel to A1–A2)

- **B1. Independent re-derivation of Theorem 2.1** (both k mod 4 cases;
  currently trusted from AIM notes + Váňa). Deliverable: complete proof in
  the working paper appendix. *Everything downstream leans on this.*
- **B2. Admissible local cells (Question 6.2).** Map all (mod 2^k, mod 5)
  patterns — including pool-uniform variants with v₂(p+1) = v > 2 — under
  which the L–P mechanism survives. First test case: p = 2x³−1, x ≡ 2
  (mod 4) ⇒ uniform v₂(p+1) = 4, v₂(p−1) = 1; mod-5 solvable (x ≡ 3).
  **If any boost-reachable cell is admissible ⇒ open Track A′:** harvest at
  x-level (half bit-size, structurally disjoint sides x vs x³−1), which
  should dominate Track A economics — re-plan immediately.
- **B3. General r.** For r with ord_r(p) = 2 the control modulus stays
  p²−1; conditions and residue classes differ by r. Assess whether some
  r ≠ 5 admits denser pools (more congruence classes ⇒ smaller slice
  penalty than 1/16 within mod-40). Low effort, potentially free win.
- **B4. Popovych side-question.** For any pool constructed here, what does
  the (X+2) congruence require? Even partial analysis makes any eventual
  find doubly informative (kills one conjecture or separates two).

## Track C — supporting/supply (opportunistic)

- **C1. Parallel closure runs** (pthreads on chm_closure.c) at B ≈ 250–400:
  denser corpora for validating A1's model out-of-sample, and for
  "partition-vote" analysis (which Q₋ | Q₊ the organic twins prefer — a
  seed for A2's choice).
- **C2. Congruence-targeted PTE sieve.** For a fixed PTE solution, m mod 40
  is a polynomial condition on x: sieving only the right x-classes makes
  every hit land in our congruence class (vs the measured 1/4000). Large
  elements are demand-heavy, so this supplements rather than drives.
- **C3. Costello/Naehrig outcomes.** The B=547 CHM corpus (or higher-B
  runs, or their cluster infrastructure) upgrades C1 and A2 calibration;
  interest from Sterner et al. could parallelize Track A′/A3. Questions
  already prepared in doc/questions-for-craig-michael.md.

## Decision tree

```
A1 yield measured ──► G1 pass ──► A2 ──► G2 pass ──► A3 ──► A4(G3) ──► A5
     │                   │                  │
     │                   │ fail             │ fail
     ▼                   ▼                  ▼
B2 admissible cell?   raise B/B′, retry A1 once with 10× candidates;
     │ yes            else: write up quantified negative for the
     ▼                mod-80 cell; pivot to B2/B3 outcomes
Track A′ (x-level harvest, half size) — re-run A1 economics there
```

## Risk register (updated)

1. **Yield model wrong (A1 kills it).** ρ(u) with the Q₋-exclusion could
   come in ≥ 10× low. Cost of finding out: ~a day of prototype compute.
   Mitigation: B2/B3 open structurally different pools.
2. **Demand-bits creep.** Λ₋ grows 12–13 bits per medium prime used; if
   solutions need most of Q₋, ratio degrades toward the invariant. A2's
   accounting must charge only used primes and cap exponents.
3. **Solver at 8–15k-bit groups.** Löh–Niebuhr worked at comparable scales
   in 1996; Wagner needs pool ≫ dimension — thin margins mean G3 synthetic
   tests come *before* production harvest finishes.
4. **Theorem risk (B1).** Unchanged: everything relies on secondary
   sources until re-derived.
5. **Prior art.** Unchanged; C3 due diligence continues.

## Immediate next actions (this week)

1. A1 prototype harvester (python, ~200 lines, reuse phase1a machinery);
   first yield grid overnight.
2. B1 re-derivation started in the working paper appendix.
3. C1 pthreads patch to chm_closure.c (small change, big corpus payoff).
