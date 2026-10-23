# Actual-prime pool pilot: construction, structure and bounded validation

**Branch:** `research/real-pool-pilot`

**Baseline:** merged main `e1bedc9b210590a58d7a78cc1ece261860c8c597`

**Status:** reproducible bounded pilot, not a counterexample or a general no-go result.

## Main result

The real instances are now built and checked, rather than modeled with
independent synthetic coordinates.

- A complete small family supplies **6** certified primes.
- A seeded medium sample supplies **94** distinct certified primes.
- A complete scan of the same medium family supplies **483** certified primes.
- The first two fixed full-pool targets have independently verified
  quadratic-character obstructions. The complete medium pool **does not**
  have an obstruction in the implemented necessary checks.
- The complete medium pool has binary rank **393** on **483** variables,
  leaving a **90-dimensional** affine kernel. This is not a proof that the
  full Boolean target is reachable.
- Small exact oracles and planted controls validate the encoding and solver
  answers. The bounded searches on the full 483-element pool fail to find
  **both the real target and a known feasible planted target**. Those failures
  are explicitly inconclusive.

**No counterexample was found.** There is no basis here to declare the
Lenstra-Pomerance route closed. The immediate accomplishment is a faithful,
checkable instance and benchmark pipeline.

## Reproduce

Python **3.9+**, standard library only. From the repository root:

```powershell
python -B -m unittest discover -s code -p "*correctness.py" -v
python -B code\real_pool_pilot.py
python -B code\real_pool_verify.py data\generated\real_pool_pilot.json.gz
```

The generator refuses to overwrite an existing output. To reproduce in place,
explicitly add `--replace`; to compare without replacing, use
`--output` with a new path. Both ordinary JSON and `.json.gz` output work.
Harvests, ordering, witnesses, encodings and sampled controls are deterministic
for the recorded configuration, seed and interpreter. Timestamps and timings
are observational, and time-limited heuristic outcomes can vary.

Artifacts:

- [Generator and bounded experiments](../code/real_pool_pilot.py)
- [Independent arithmetic verifier](../code/real_pool_verify.py)
- [Pilot regression tests](../code/test_real_pool_correctness.py)
- [Compressed dataset](../data/generated/real_pool_pilot.json.gz)

The dataset includes full prime records, Lucas witnesses, factorizations,
original LCMs, primitive roots, all vectors and targets, component statistics,
obstruction characters, benchmark witnesses and budgets, and SHA256 hashes
of the implementation sources (CRLF normalized to LF, for Git checkout
portability). The independent verifier rejects stale source
hashes or corrupted records, encodings, statistics, ranks, certificates and
solver claims. It does not import the generator, AG arithmetic helpers, or
the A-series solvers.

## Step 1. Actual bounded harvesting

Fix disjoint bases:

```text
Q_plus  = odd primes <= B, excluding 5
Q_minus = primes in (B, B_prime]
m       = product of three DISTINCT Q_minus primes
p       = 2*m + 1
```

Keep `m = 1 mod 40`, completely `Q_plus`-smooth `(m+1)/2`, and require each
prime power in `p+1` to be at most **8192**. Candidates must fit below
`2**64`. A probable-prime prefilter is followed by an **exact full-factor
Lucas primality certificate**, independently checked with trial-verified
factor primes. No unresolved or probable-only prime is admitted.

For each accepted record the dataset stores complete factorizations of `p-1`
and `p+1`, the certificate witness, and the first accepted candidate index.
The witness search is bounded to bases 2 through 65; certificate exhaustion
is counted explicitly. None occurred in these runs.

| Cohort | B / B_prime | Candidate draws | Distinct certified primes | Complete family scan? |
|---|---|---:|---:|---|
| Small complete | 113 / 565 | 62,196 | 6 | Yes |
| Medium sample | 547 / 2735 | 1,000,000 | 94 | No; seeded with replacement |
| Medium complete | 547 / 2735 | 4,366,296 | 483 | Yes |

Both medium cohorts use seed **20261022** where randomness is involved.
Pool caps are 128 for the first two and 512 for the complete medium scan;
none was reached. A complete scan means complete for this **squarefree,
three-factor, fixed-base, exponent-capped family**, not all eligible primes,
all twin-smooth integers, or all possible constructions.

The medium sample saw 109 probable-prime hits after the smoothness/power
filters, including 15 repetitions, leaving 94 distinct certified records.
The complete medium family had 273,143 congruence survivors, 3,949 smooth
hits, and 192 power-cap rejections before primality filtering. All 483
remaining prime hits received certificates. Prime sizes were 25-27 bits
for the small pool and 29-35 bits for both medium pools.

The recorded harvest times were approximately 0.02, 3.06 and 3.60 seconds,
respectively; exact-instance construction took approximately 0.003, 0.22
and 1.67 seconds. These are observations from one machine, not portable
performance guarantees or production extrapolations.

## Step 2. Exact assembly instances

For each raw pool, compute:

```text
Lambda_minus = lcm(p-1 over the raw pool)
Lambda_plus  = lcm(p+1 over the raw pool)
target       = (1 mod Lambda_minus, -1 mod Lambda_plus)
```

Exclude nonunit pool elements relative to these **original full-pool**
moduli, without silently shrinking the moduli. There were **no nonunit
exclusions in the three actual runs**; a regression fixture verifies the
filter on a pool containing 3 and 83.

For every odd `q**e` dividing a side modulus, the unit group is cyclic of
order `q**(e-1)*(q-1)`. A verified primitive root and bounded baby-step/
giant-step logarithms produce its exact prime-power components. Independent
verification reconstructs every original prime residue and target using CRT
and modular exponentiation. No `q**(e-1)` component is omitted.

For all accepted primes, `v2(p-1)=1`, `v2(p+1)=2`, and `p=3 mod4`.
The minus-side mod-2 unit group is trivial. The plus-side mod-4 unit factor
is represented **once** as the final parity coordinate: each vector is 1,
and the target is 1. It is not counted again as an extra independent bit.
Solvers must additionally require **at least three** selected primes.

| Cohort | Pool size | Cyclic prime-power components | log2(group order) | Bits omitted by a q-1-only model | Pool / group bits |
|---|---:|---:|---:|---:|---:|
| Small complete | 6 | 78 | 231.65 | 19.84 | 0.0259 |
| Medium sample | 94 | 738 | 2506.60 | 53.12 | 0.0375 |
| Medium complete | 483 | 1132 | 3951.73 | 124.25 | 0.1222 |

These are **not** the high-supply production projections of the older
research. Even the complete medium family has fewer variables than group
bits; that comparison is a warning about the uniform-subset-sum heuristic,
not a proof that the particular structured target is unreachable.

The fixed full-pool target is stronger than checking divisibility only for
selected factors. Consequently a negative fixed-target result does not
automatically rule out every original L-P subset of the same raw pool.
The separate selected-subset arithmetic oracle below keeps that distinction.

## Step 3. Measured structure and necessary checks

### Identities are not the same as forced support

Literal identity means a zero in the actual discrete-log component.
Forced identity means the known side factorization guarantees that zero.
Other zeros can occur without being forced by the side support.

On the plus side, `p=-1 mod q**e` is **not identity** in the full unit group;
it projects to identity on odd-order components. Partial prime-power support
does not necessarily force the `q`-primary component to vanish.

| Cohort | Mean literal-zero fraction | Mean forced-zero fraction | Bit-weighted literal-zero fraction |
|---|---:|---:|---:|
| Small complete | 30.56% | 15.38% | 24.77% |
| Medium sample | 20.83% | 2.00% | 11.48% |
| Medium complete | 19.87% | 1.29% | 10.38% |

The artifact includes per-component orders and frequencies, uniform baselines,
and 64 seeded zero-indicator correlation pairs per cohort. These are
descriptive statistics, not an independence claim or significance test;
correlation is recorded as null when a coordinate is constant.
None of these numbers should be equated to the historical synthetic `rho`
parameter or extrapolated to H7 without a matching real harvest.

### Exact obstructions in the smaller pools

Checks include coordinate-generated subgroups and consistency in each
prime-field quotient of the actual group, including the parity/mod-4
coordinate. A failed check carries an annihilating character: it is zero
on **every** pool vector and nonzero on the target. Independent verification
checks this identity, not just the solver's consistency flag.

| Cohort | Binary rows | Binary rank | Binary nullity | Full real target passes implemented checks? |
|---|---:|---:|---:|---|
| Small complete | 33 | 6 | 0 | No; explicit character obstruction |
| Medium sample | 262 | 94 | 0 | No; explicit character obstruction |
| Medium complete | 394 | 393 | 90 | Yes; not sufficient for Boolean reachability |

For example, let `(n/q)` denote the Legendre symbol. In the six-prime
pool, every pool prime has character

```text
chi(n) = (n/131)*(n/163)*(n/167)*(n/199)*(n/3)
```

equal to `+1`. The fixed L-P target requires `+1` at the four minus-side
primes and `-1 mod3` on the plus side, so its character is `-1`.
Multiplying any subset of these pool elements preserves `chi=+1`; hence
that fixed target is impossible. The dataset records a corresponding,
larger explicit character for the 94-prime sample.

The **complete medium pool removes these observed quotient obstructions**.
Its consistent binary projection has `2**90` solutions before the remaining
prime-power constraints and the minimum-cardinality test. Passing these
necessary checks is neither full subgroup membership certification nor
Boolean target reachability.

## Step 4. Oracles, controls and bounded solver comparison

Benchmarks retain the parent pool's full moduli and use either all retained
primes or the first 12 sorted primes (all six in the small case).

- The **real target** is always the fixed L-P target above.
- A **planted control** is the sum/product of three distinct, seeded real
  pool elements. Its residue target and witness are recorded separately.
  None of these planted targets is the real L-P target.
- Any solver return is checked in the original multiplicative residues,
  not just its additive model, with odd cardinality at least three.
- A possible L-P candidate is also checked against both per-factor
  divisibilities, distinct certified primes, the mod-5 exception clause,
  and an independent direct polynomial calculation modulo `(n, X**5-1)`.

Budgets:

| Method | Bound and interpretation |
|---|---|
| Independent residue oracle | All subsets through 18 variables, at most `2**18` states; no logs used |
| A4 kernel search | 64 states in a sampled kernel subspace; failure is inconclusive |
| A6 local search | At most 64 moves and 2 seconds of local search (projection setup separate), original residuals and minimum size checked |
| A6 direct MITM | At most 18 variables and 5 seconds in this pilot; timeout/size cap is inconclusive |
| Selected-subset L-P oracle | At most 18 variables and `2**18` odd subsets; checks original per-selected-factor conditions |

The A4/A6 generic APIs retain their default minimum size of one for existing
callers. The pilot explicitly passes `min_size=3`. MITM now retains the
largest-cardinality witness for a residue/parity key so that a smaller
witness cannot hide a valid one under this lower-size constraint.

### Outcomes

| Instance/target | Independent residue oracle | A4 | A6 local | A6 MITM |
|---|---|---|---|---|
| Small, all 6, real | Exhausted; none | Binary obstruction | Binary obstruction | Exhausted; none |
| Small, all 6, planted | Verified 3-prime solution | Verified solution | Verified solution | Verified solution |
| Medium sample, first 12, real | Exhausted; none | Binary obstruction | Binary obstruction | Exhausted; none |
| Medium sample, first 12, planted | Verified 3-prime solution | Verified solution | Verified solution | Verified solution |
| Medium sample, all 94, real | Size cap | Binary obstruction | Binary obstruction | Size cap |
| Medium sample, all 94, planted | Size cap | Verified solution | Verified solution | Size cap |
| Medium complete, first 12, real | Exhausted; none | Binary obstruction | Binary obstruction | Exhausted; none |
| Medium complete, first 12, planted | Verified 3-prime solution | Verified solution | Verified solution | Verified solution |
| Medium complete, all 483, real | Size cap | Inconclusive budget | Inconclusive budget | Size cap |
| Medium complete, all 483, planted | Size cap | Inconclusive budget | Inconclusive budget | Size cap |

The successful full six-/94-prime controls have unique binary solutions, so
they are useful correctness checks, not evidence of solving a hard residual
problem. The 483-prime planted control is known feasible but was not found
under these tiny search budgets. Its failure is a concrete demonstration of
why the same algorithms' negative outcomes cannot be called impossibility
results.

The independent selected-subset oracle separately checked **26** odd
subsets of size at least three in the six-prime pool, and **2,036** in
each 12-prime prefix. None met the original divisibility conditions.
The 94- and 483-prime selected-subset searches were **not** exhausted.

The saved-report verifier validates prime certificates, source provenance,
block reconstruction, measured statistics and ranks, explicit obstructions,
each reported solution, and small negative claims. It reports **zero**
independently verified counterexamples.

## Validation and boundaries

- The combined suite has **65** bounded tests, including the prior audit
  regressions, minimum-cardinality behavior, exact prime-power logs, unit
  exclusions, independent obstructions, rejection of corrupted datasets,
  and compressed-output/standalone-verifier round trips. All pass on
  **Python 3.9.13 and 3.14.5**; the saved-report verifier also passes on both.
- A separate replay regenerated all three harvests and encodings. Prime
  certificates, factorizations, candidate indices, metadata excluding
  timings, original moduli and all vectors/targets matched exactly.
- The direct polynomial verifier is cross-checked against the earlier
  implementation on small integers; small actual residue searches and
  generic Boolean enumeration independently check solver answers.
- Original findings, data, and both historical and audit PDFs are unchanged.
  All **49** pre-existing protected PDF/data artifacts remain unchanged.
  The pilot dataset is a new artifact; no private corpus is used.

Across the cohorts, 583 record certificates cover 489 distinct primes;
repeated primes across the sampled and complete medium cohorts are not
counted as distinct discoveries.

The immediate next gate is **not** a production harvest or a claim that a
new solver paradigm is mathematically necessary. Compare modest alternative
harvest families on verified pool/group size and target obstructions, then
test whether a better algorithm can recover known feasible real-vector
controls under stated budgets. The complete medium pool is a useful
nontrivial benchmark, but its real target remains unresolved.
