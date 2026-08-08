# Harvest specification

> **UPDATE 2026-08-07 (co-design, supersedes the pure-yield spec below).**
> The A4 solver's group is ~84% odd-prime bits with primes up to ~6269 — the
> real bottleneck. The A5 co-design study (data/FINDINGS.md, doc/
> a4-solver-analysis.md) constrains both factor bases to odd-smooth-shifted
> primes (odd part of q−1 ≤ t0), capping the solver's max odd prime.
>
> **Co-designed spec (recommended target): t0 = 100, Q₊ = odd primes ≤ 2003
> with (q−1) odd-part 100-smooth, Q₋ = primes in (2003, 60090] with (q−1)
> odd-part 100-smooth, j = 4, m ≡ 1 mod 40.** Measured ratio ~7.7 (above the
> G2 gate; ±40% at current sample size), solver odd-support {24 primes ≤ 97}
> vs the uncoded {336 primes ≤ 6269}. Fallback t0 = 200 (ratio ~14.5, 45
> primes ≤ 199). This spec is pending (a) a higher-sample ratio confirmation
> and (b) a G3 pass with the small-prime odd-part solver.
>
> The pure-yield spec below (ignoring the solver) is retained for reference.

---

# Frozen harvest specification (Gate G2) — pure-yield (superseded)

*Frozen 2026-08-07 from A1/A2 calibration. Supersedes the back-of-envelope
sketch in PLAN.md §Track A. All numbers measured; see data/generated/
a2_grid.json, a2_validation.json and data/FINDINGS.md.*

## Model validation (why we trust the projection)

The A1/A2 sampler was checked against the **complete** TwinSmooths B=547
corpus (exhaustive twin population to 122 bits): for four asymmetric splits it
predicted 0.41–1.04× the true pool count (geo-mean 0.68) — i.e. **slightly
conservative**, never optimistic. The per-candidate physics (Dickman side-
smoothness × 1/16 congruence × 1/ln p primality, sides independent) reproduces
real complete-corpus counts at j=3,4. Extrapolation to B ≈ 1300 rests on this
validated model plus C(t,j) combinatorics. Two further sources of conservatism:
the sampler counts only squarefree m (real harvest may use q² on the minus
side), and demand is charged over the full Q₋ band.

## Primary spec

| parameter | value |
|---|---|
| r (AKS modulus) | 5 |
| congruence | m ≡ 1 (mod 40)  ⟺ p = 2m+1 ≡ 3 (mod 80) |
| Q₊ (plus side) | odd primes ≤ **1259**, except 5 (π ≈ 205) |
| Q₋ (minus side) | primes in (**1259, 12590**]  (t ≈ 1130) |
| j (minus-side factors) | 4 (squarefree; q² allowed as a bonus) |
| Q₊ exponent cap | reject q^e > 2¹³ |

**Measured projection (17 hits, ±24%):** pool ≈ 2.5×10⁵ elements of mean 50
bits; demand ≈ 18,100 bits (Λ₋ + Λ₊). **Ratio 13.8 — 5.5× the G2 threshold
of 2.5, ≥10 even at the pessimistic end of the error bar.**

Rationale for this cell over higher-ratio ones: ratio grows with B′ (up to 209
at B′=40060) but so does the solver's group modulus (up to 57k bits). B′=10·B
keeps the A4 subset-product group at ~18k bits — Löh–Niebuhr Carmichael
territory (1996) — while still over-provisioning the pool ~80× beyond the
~3,000 elements a solution needs. Most reliable measurement (most hits) too.

## Fallback / escalation spec

If A4 fails at the primary demand, **B′ = 18885 (=15·B), j=4**: ratio 41,
pool ≈ 1.1×10⁶, demand ≈ 27,100 bits. More margin, harder solver.

## Production compute (A3)

C(1130, 4) ≈ 6.7×10¹⁰ squarefree candidates. With the mod-40 pre-filter
(rejects 39/40 cheaply) and early-abort trial division over Q₊, ≈ 10⁶–10⁷
candidates/core-sec ⇒ order **10²–10³ core-hours** for the full space — a few
days on 8–16 cores. Harvest stops once ~10⁴ pool elements accumulate (≈1% of
the space), so realistically far less. Adapt code/chm_closure.c infrastructure
(C, pthreads); store each element with full factorization + deterministic
seed/provenance.

## Open refinements (do not block A3)

- **j=5** projects far higher ratios but is hit-starved at 8M python samples
  (0–1 hits). Measure properly with the C harvester (hit rate ~10⁻⁷ needs
  ~10⁹ candidates, minutes in C). If it holds, it dominates.
- **Prime-power minus side** (q²): raises yield, unmeasured.
- **General r** (Track B3): a different r may widen the congruence class,
  reducing the 1/40 slice penalty.

## G2 verdict: PASSED

Primary spec projects pool/demand = 13.8 (gate 2.5) and pool = 2.5×10⁵
(gate 3000), on a model validated conservative against complete real data.
Proceed to A3 (production harvester) and A4 (solver, with G3 synthetic tests
first).
