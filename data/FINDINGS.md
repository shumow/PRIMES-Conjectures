# Phase 0/1a First Results (2026-08-06)

Code: `code/verify_machinery.py`, `code/phase1a_calibration.py`,
`code/chm_closure.py`. All runs deterministic (fixed seeds).

## Machinery validation (Phase 0) — all pass
- T1: T(−1,p,5) holds for all 2,259 primes p < 20,000 (implementation sanity).
- T2: 2,000 random composites n ≡ ±2 (mod 5) all fail T(−1,n,5).
- T3: (X−1)^(10(p²−1)+1) ≡ X−1 (mod p, X⁵−1) for primes p ≡ ±2 (mod 5) —
  confirms Váňa's ρ(p) | 10(p²−1) (working paper Thm 2.1 sketch dependency).
- T4: Lemmas 2.2/2.5/4.1 and Prop 6.1 verified over all residues.

## Calibration runs

| B | source | twins | pool (m≡1 mod 40, 2m+1 prime) | E[rand surv] | opt surv | surv/demand |
|---|---|---|---|---|---|---|
| 113 | X ≤ 1e8 | 18,273 | 59 | 3.8% | 8 (13.6%) | 0.061 |
| 113 | X ≤ 1e10 | 26,908 | 73 | 3.1% | 8 (11.0%) | 0.061 |
| 113 | **CHM closure (complete-ish)** | **33,118** | 78 | 2.9% | 8 (10.3%) | 0.061 |
| 257 | X ≤ 1e9 | 199,118 | 497 | 1.0% | 21 (4.2%) | 0.061 |
| 547 | X ≤ 1e9 | 1,102,529 | 2,715 | 0.6% | 51 (1.9%) | 0.068 |

## Key findings

1. **Congruence slice is ~1/90, not 1/40.** Twins prefer even m and 5 | m;
   update all supply estimates accordingly.
2. **Fixed-B supply saturates in X fast** (B=113: 100× more X → +47% twins;
   CHM closure shows the true total is 33,118 with largest 75 bits). The full
   Størmer set — not an X-bounded harvest — is the real supply. Our CHM
   closure implementation converges (6 rounds) and needs no size cap.
3. **N(B) grows much faster than estimated: α ≈ 5.** N(113) ≈ 3.3e4 (ours,
   complete-ish) vs N(547) = 8.2e7 (Bruno et al.) gives N(B) ~ B^5. The
   pre-coloring supply/demand ratio therefore crosses 1 somewhere around
   B ≈ 200–250 and is projected ~10–30 at B = 547 (pool ~15–30k vs ~1000
   bits) — better than the working paper's B^2.5–3 guess.
4. **The greedy coloring invariant: survivors ≈ 0.06 × survivor-demand-bits,**
   in all five experiments, across B, X, and complete vs truncated sets.
   Mechanism: each kept element consumes ~2 fresh primes × ~7 bits. The
   optimizer beats random by 3.4–4.4× but the ratio is what must reach ≈ 1–2.
   It can only climb when the pool is dense enough that most added elements
   are *fully supported on already-claimed primes* — the regime the projected
   B=547 full pool (15–30k elements over ≤ 100 primes) plausibly enters.
5. **Decisive next experiment:** CHM closure at B = 547 (or obtain the
   Bruno et al. dataset), then re-run the coloring optimizer. Pure-python
   closure is too slow beyond B ≈ 130 (O(N·W) per round over N ≈ 10⁶); needs
   the optimized public implementation or a compiled port. This is question
   #1 in doc/questions-for-craig-michael.md.

## Validation against published data (2026-08-07)

`data/published/` holds a small verified corpus of published record pairs
(collected by a ChatGPT agent from ePrint 2022/1439 and arXiv:2211.04315;
all six rows re-verified arithmetically here: factorizations multiply to n,
n+1 consecutive, smoothness bounds hold).

- **B=100: our CHM closure finds 13,333 of the complete 13,374 pairs
  (99.69%), including the exact published largest** (166055401586083680,
  58 bits). Seeds are exhaustive to 1e7, so all 41 missing pairs are > 1e7:
  the small end is *provably* complete, the deficit is confined to the tail.
- **B=113: our closure maximum equals the published exhaustive record**
  (19316158377073923834000, 75 bits), supporting near-completeness of our
  33,118 count.
- Published complete/near-complete counts now anchor the supply curve:
  N(100) = 13,374; N(200) = 346,192 (original CHM); N(547) = 82,026,426.
  Fitted exponent: alpha = 4.7 (100->200) to 5.4 (200->547) — confirms the
  N(B) ~ B^5 estimate from our own runs.
- No public bulk dataset located (the agent explicitly retracted an
  unverified Zenodo claim) — the ask to Bruno et al. remains the fastest
  path to B=547; our own closure is a credible substitute given a compiled
  implementation. **Next validation anchor: B=200 must reproduce ~346,192**
  (pure python is ~hours there; port the closure to C/Rust first).

## Caveats
- Coloring optimizer is greedy + random restarts; true optimum may be higher
  (annealing/ILP not yet tried). The 0.06 invariant is a *lower bound* on
  what optimization achieves.
