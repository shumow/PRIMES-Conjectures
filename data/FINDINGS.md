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

## Compiled CHM port + B=200 results (2026-08-07)

`code/chm_closure.c` (C, __int128; build: `cc -O2 -o chm_closure chm_closure.c`)
replaces the python closure. Validation anchors, all passed:

| B | ours | published | max pair |
|---|---|---|---|
| 100 | 13,333 | 13,374 complete (99.69%) | exact match |
| 113 | 33,118 | (count unpublished) | exact match w/ exhaustive record |
| 200 | **346,110** | **346,192 original-CHM (99.976%)** | **exact match** (79 bits) |

B=200 runs in ~3 min single-threaded (window 20,000, seeds to 1e7,
9 rounds). B=547 would need parallelism + weeks, or the Bruno et al. corpus.

**B=200 coloring measurement** (near-complete supply, biggest pool yet):
346,110 twins -> 2,833 with m ≡ 1 (mod 40) -> **562 pool** (2m+1 prime).
Mean total omega 9.8 over a 44-prime universe. Random-partition expectation
0.66%; element-greedy optimization: 17 survivors (3.0%), ratio 0.060;
**direct partition-space local search (60 restarts, hill climbing on prime
side-flips): 16 survivors, ratio 0.061.**

**The 0.06 invariant is not an optimizer artifact.** Seven measurements
(five element-greedy across B/X/completeness, one full-set greedy, one
partition-space search) all give survivors/demand-bits = 0.060-0.068 — a
factor ~16-25 below feasibility. Hypothesis: partition-agnostic twin
supply intrinsically pays ~2 fresh primes x ~7.5 bits per kept element.

**Strategic consequence (partition-first harvesting).** The Phase 1b
constructive harvester inverts the problem: fix the partition Q- | Q+ FIRST,
enumerate m as products of Q- primes, keep those with (m+1)/2 being
Q+-smooth and 2m+1 prime. Every harvested element is compatible by
construction — the coloring tax moves into harvest yield, where it is a
per-element Dickman cost rather than a global combinatorial obstruction.
The twin corpora (CHM/PTE) remain essential for calibration and for
choosing WHICH partition to target, but the hunt itself should be
partition-first. This vindicates the original asymmetric-split design in
PLAN.md Phase 1 and doc/background.tex §3.

## A1 yield calibration: GATE G1 PASSED (2026-08-07)

`code/a1_yield_prototype.py`, 20M sampled candidates per cell, 12 cells;
raw curves in `data/generated/a1_yield_grid.json`. Projection = measured
per-candidate hit rate x C(t, j), against demand = full-Q₋ lcm bits +
Q₊ ceiling (1.44B x 1.15 slack):

| B | B′ | j | hit rate | proj. pool H | demand bits | **pool/demand** |
|---|---|---|---|---|---|---|
| 547 | 2735 | 3 | 1.1e-4 | 502 | 4094 | 0.12 |
| 547 | 5470 | 4 | 2.0e-6 | 1.2e4 | 7896 | 1.50 (±16%) |
| 1259 | 6295 | 4 | 4.2e-6 | 2.4e4 | 9273 | 2.57 (±11%) |
| 1259 | 12590 | 4 | 2.4e-6 | 2.9e5 | 18309 | **15.7 (±14%)** |
| 2003 | 10015 | 4 | 5.3e-6 | 1.6e5 | 14811 | **10.7 (±10%)** |
| 2003 | 20030 | 4 | 2.1e-6 | 1.3e6 | 29138 | **44.4 (±16%)** |

(j=3 cells land at 0.12-2.7 — the plan's pessimistic sketch was a j=3
artifact. Full table in the JSON.)

Findings:
1. **Ratio scales ~ t^(j-1) x rate**: combinatorial volume C(t,j) grows
   polynomially in t while Λ₋ grows only linearly — j=4 with B′/B = 10 is
   the discovered sweet spot; j=5 (unmeasured) plausibly better still.
2. Side-smoothness rates given the congruence track plain Dickman — the
   Q₋-exclusion tax on the plus side is mild, as hoped.
3. Production compute for the 15.7x cell: C(t,4) ~ 2^36.8 ~ 1.2e11
   candidates; with the 1/16 mod-40 pre-filter and early-abort trial
   division, ~40-100 CPU-hours in C — a weekend on 8 cores. The 44x cell
   is ~10x that, still feasible.
4. Partition-first beats the 0.06 invariant by a factor of ~200-700 in
   the best cells: **the coloring obstruction is fully bypassed by
   construction, and supply is no longer the binding constraint.**

**A2 refinement targets:** measure j=5 and a finer (B, B′) grid around
(1259-2003, 10x); exponent-capped enumeration; solver-slack modeling;
then freeze the harvest spec.

## Definitive B=547 coloring measurement (2026-08-07)

Source: complete TwinSmooths/twins_data corpus (private, shared by M. Naehrig;
raw data kept OUT of this repo — aggregate stats only). `code/b547_pool_analysis.py`.

- Streamed all **82,026,426** pairs; **642,495** have m ≡ 1 (mod 40);
  **pool = 73,163** with 2m+1 prime (27x the largest pool tested before).
- Mean total omega 14.9 over the odd-prime universe.
- Random-partition expectation 25.6 survivors; **best partition-space local
  search (30 restarts): 82 survivors, demand 984 bits, ratio 0.083.**
- **The 0.06 invariant holds at full scale** (0.060-0.083 across B=100-547,
  pools 78 -> 73,163). Dataset-mining is conclusively dead: measured, not
  extrapolated, on the entire published corpus.
- Contrast with A1 partition-first (15-44) is now airtight: same conjecture,
  filters, and optimizer; the only difference is fixing the partition FIRST.
  ~300-500x separation, demonstrated at scale on both sides.

Completeness audit against the complete corpus (bonus from having exact data):
N(100)=13,374 (our closure 13,333=99.7%), N(113)=33,233 (99.65%),
N(200)=348,840 (our closure 346,110=99.2%; note the original-CHM published
346,192 was itself ~0.8% short of complete). Zero false positives: every twin
our C closure emits is in the corpus. Repo also has B=1300 data to 115 bits +
per-prime histograms -- out-of-sample validation material for the A1/A2 model
in our target region.

## A2: model validated on real data; spec frozen; GATE G2 PASSED (2026-08-07)

**Out-of-sample validation** (`code/a2_validate_and_extend.py`): the A1/A2
sampler vs the complete B=547 corpus (exhaustive to 122 bits), four asymmetric
splits — predicted/real = 0.71, 0.70, 0.41, 1.04 (geo-mean 0.68). The model is
**conservative, never optimistic**; per-candidate physics reproduces real
complete-corpus counts at j=3,4. (Real counts small, 7–13, since asymmetric
bands within B≤547 are narrow; validates physics not absolute scale.)

**Extended grid** (`code/a2_grid.py`, 8M samples/cell, j=4,5,6, B∈[1009,2003],
B′/B∈{10,15,20}). All 9 trustworthy cells (≥8 hits) are j=4; j=5,6 hit-starved
(0–1 hits) — deferred to the C harvester. Reliable j=4 ratios:

| B | B′ | ratio | pool | demand bits | mean bits | rel.err |
|---|---|---|---|---|---|---|
| 1259 | 12590 | 13.8 | 2.5e5 | 18117 | 50 | ±24% |
| 1259 | 18885 | 41.0 | 1.1e6 | 27101 | 51 | ±26% |
| 2003 | 20030 | 45.5 | 1.3e6 | 28768 | 52 | ±24% |
| 2003 | 40060 | 209  | 1.2e7 | 57514 | 54 | ±32% |

Ratio grows with B′ but so does the solver's group modulus — the tradeoff that
sets the frozen spec (doc/harvest-spec.md).

**Frozen spec:** Q₊ = odd primes ≤1259 (≠5); Q₋ = primes in (1259, 12590];
j=4; m ≡ 1 mod 40; exponent cap 2¹³. Ratio 13.8, pool ~2.5e5, demand ~18k
bits, mean 50-bit elements. Production ~10²–10³ core-hours (few days on 8–16
cores), stops at ~10⁴ elements. **G2 PASSED** (gate 2.5); proceed to A3/A4.

## A4 solver, G3 phase-1: the solver is the binding constraint (2026-08-07)

`code/a4_solver.py`; full analysis in doc/a4-solver-analysis.md.
**G3 NOT yet passed** — and finding that now, before the A3 harvest, is the win.

- The condition linearizes to subset-sum in G = (Z/Λ₋)*×(Z/Λ₊)*, a product of
  cyclic prime-power components. Pool N ≫ dim ⇒ solutions dense; a 0/1 one is
  the crux.
- **2-part is GF(2)-linear and solves at full scale** (frozen spec B=1259,
  B′=12590: 4586 components, mod-2 system solved in 12s).
- **But the 2-part is only ~16% of the demand bits.** ~84% (≈15,000 bits at
  the frozen spec) lives in odd-prime components with primes ℓ up to ~6269.
  This overturned the assumption that the 2-torsion was the bulk. The
  prototype's odd-part closer fails even at ~60-bit odd scale.
- **Conclusion:** supply is solved (G1/G2); the ~15k-bit odd-prime subset-sum
  is the real problem. Paths: (1) harvest co-design toward 2-power-heavy q−1
  to shrink the odd part (couples back to A2, at a yield cost); (2) a proper
  odd-part solver (Wagner block-variant / lattice / structured integer LA);
  (3) general r (Track B3) for a friendlier group. Recommendation: (1)+(2)
  together, re-attempt G3 on the co-designed spec, hold A3 until it passes.

## A5 harvest/solver co-design: viable window found (2026-08-07)

`code/a5_codesign.py` (characterization), `code/a5_yield.py` (measured yield);
full picture in doc/a4-solver-analysis.md. Constrain BOTH factor bases to
odd-smooth-shifted primes (odd part of q-1 ≤ t0), capping the solver group's
max odd prime at t0.

**Characterization** (frozen band, cheap): tightening t0 shrinks the odd-prime
support hard — max odd prime 6269→47 and distinct odd primes 336→14 at t0=50 —
but the odd *dimension* (bits) only partly shrinks, since recovering yield
needs many primes (odd bits scale with #primes). So co-design trades prime
SIZE, not dimension.

**Measured co-designed yield** (both bases constrained, 12M samples/cell; low
hit counts, ±40%):

| t0 | B | B′ | ratio | max odd ℓ | #distinct odd |
|---|---|---|---|---|---|
| 50 | 1259 | 40060 | 1.1 | 47 | 14 |
| 100 | 1259 | 40060 | 2.6 | 97 | 24 |
| **100** | **2003** | **60090** | **7.7** | **97** | **24** |
| 200 | 1259 | 40060 | 14.5 | 199 | 45 |
| 50 | 631 | 40060 | 0.0 | 47 | 14 |

**Verdict — co-design works.** A viable window exists: **t0=100, B=2003,
B′=60090, j=4** gives ratio ~7.7 (above the G2 gate 2.5) while shrinking the
solver's odd support from {336 primes ≤6269} to **{24 primes ≤97}** — the
structural change that moves the odd-part subset-sum into the small-prime
regime where per-prime linear algebra + CRT/MITM is applicable. t0=200
(ratio 14.5, 45 primes ≤199) is the safety-margin fallback. Small plus-bound
(B=631) kills yield — constrain Q₊ by smoothness, don't shrink B.

**Next:** (a) confirm the ratio with more samples / the C harvester (current
±40%); (b) build + test the small-prime odd-part solver on the co-designed
group (24 primes ≤97) and re-attempt G3. Co-design achieved its goal: it makes
the solver's odd part small-prime while keeping the harvest above the gate.

## A6 small-prime odd-part solver, G3 re-attempt: NOT passed — dimension is the wall (2026-08-08)

`code/a6_oddsolver.py`. Two solvers tested on faithful co-designed synthetic
instances (small primes ≤97, planted solutions):

- **2-part: GF(2) exact, scales** (from A4: 4586 components solved in 12s).
- **Odd part (heuristic): annealing** within the GF(2) solution family stalls
  at ≥19 odd components (dense kernel XOR moves too disruptive).
- **Odd part (exact): meet-in-the-middle** solves the small instances annealing
  cannot (N=24/D=11 instant; N=40/D=15 in 11s) but is exponential in N, capping
  ~N=40 / ~15 odd components / ~40 odd bits.

Both cap **2–3 orders of magnitude below** the co-designed spec (~thousands of
odd components, ~24k odd bits). **G3 NOT passed.** Diagnosis: co-design capped
the max odd prime (6269→97) but **not the odd dimension**, and dimension is the
obstruction. Capping dimension too would need near-Fermat (2-power-heavy)
primes, which are too sparse for the harvest — a real yield/solver tension.

**The path is concrete, not a dead end.** Subset-product ≡ 1 in (Z/L)* at this
scale is exactly what the Löh–Niebuhr / AGP **constructive** Carmichael
algorithm does (Carmichael numbers with millions of prime factors have been
built this way). It succeeds by exploiting staged construction / structured
prime selection, not by solving a generic dense subset-sum. Our Carmichael
condition (n ≡ 1 mod Λ₋) is directly in its scope; the Lucas–Carmichael twist
(n ≡ −1 mod Λ₊) is the added piece. **Next build: adapt the Löh–Niebuhr
constructive method to the double condition** — the proven tool for this exact
problem, replacing the generic solvers that provably don't scale here.

## A7/A8: the A6 "dimension wall" was a mis-diagnosis — AGHS is the tool (2026-08-08)

Investigating the Löh–Niebuhr adaptation led to Alford–Grantham–Hayman–Shallue,
*Constructing Carmichael numbers through improved subset-product algorithms*
(arXiv:1203.6664), who built a Carmichael number with **10,333,229,505 prime
factors** — subset-product ≡ 1 in (Z/Λ)* including the full odd part.

**Key correction to A6.** They do NOT use exact linear algebra and do NOT
require a small odd part. They use a **subexponential ω-guided reduction**: a
distance-to-identity potential ω(a) = highest CRT component where a ≠ 1, and
build products that zero components top-down. The exact 0/1 constraint (which
makes polynomial elimination impossible) is exactly why the method is
subexponential rather than polynomial — not a wall, a complexity class.
**So the odd-dimension "wall" from A6 is not fundamental**; it was the wrong
solver.

**The real requirement — and the harvest redesign it forces.** ω-reduction
needs pool primes that are ≡ 1 (identity) on MANY components — the AGHS
structure where **p − 1 | Λ** (a fixed highly-composite modulus), so p ≡ 1 mod
every prime power dividing p−1. Our current harvest builds m as a product of j
medium primes, so p = 2m+1 is ≡ 1 on only ~j components — dense group vectors,
the worst case for ω-reduction. **The adaptation therefore has two parts:**
(1) implement the full AGHS ω-solver (two potentials ω/ω̄, birthday step,
non-uniformity exploitation); (2) redesign the harvest to the **divisor
paradigm** — fix highly-composite Λ₋, Λ₊ and harvest twin primes p = 2m+1 with
m | Λ₋/2 and (m+1) | Λ₊/2.

**Status (`code/a7_lohniebuhr.py`, `code/a8_omega_solver.py`).** A first
ω-reducer (strict top-down, one potential) runs and solves the easy regime
(r ≤ 20 components, high identity-density) but not beyond — the full
subexponential AGHS algorithm is a substantial multi-turn build not yet
reproduced. Net: the path is now correctly identified and de-walled; the
remaining work is well-scoped (full ω-solver + divisor-harvest), and both are
concrete.

## N1: divisor-paradigm harvest (H8) is unharvestable under the double condition (2026-08-08)

`code/a9_divisor_harvest.py`. Fixed disjoint factor bases T₋, T₊ (side-
coprimality), enumerated squarefree divisors m of ∏T₋, kept pool primes
p = 2m+1 with m ≡ 1 (mod 40), 2m+1 prime, (m+1)/2 squarefree over T₊.

**Measured yield/density (multiple scales):**

| T₋ bound | T₊ range | \|T₋\|+\|T₊\| | pool | mean density | max density |
|---|---|---|---|---|---|
| 90 | 97–220 | 45 | 1 | 0.178 | 0.178 |
| 120 | 127–300 | 60 | 1 | 0.067 | 0.067 |
| 150 | 160–360 | 68 | 2 | 0.074 | 0.088 |
| 60 | 67–160 | 34 | 0 | — | — |

**The divisor paradigm cannot give a pool that is both non-empty AND
high-density.** Small T₋ (needed for decent density = ω(m)/\|T₋\|) → ~empty;
larger T₋ → density collapses and pool stays ~empty. Root cause: the DOUBLE
condition (both p−1 | Λ₋ and p+1 | Λ₊ for fixed moduli) is the product of two
rare events — far more restrictive than AGHS's single p−1 | Λ.

**The identity-density gap (the crux).** The AGHS ω-solver exploits pool primes
being ≡ 1 on MANY components (high density). Comparison:
- **AGHS pools** (p−1 | highly-composite Λ): density ~0.3–0.5.
- **Our harvestable H7 pools** (p−1 = 2m, m = product of j≈4 medium primes):
  density ≈ j/(#distinct medium primes) ≈ **0.003–0.008** — ~100× lower.
- **Divisor-paradigm H8** (would give AGHS density): **unharvestable** (~empty).

So there is a **structural mismatch**: under the double Carmichael+Lucas
condition we can have a harvestable pool (H7, but ~100× too low density for
ω-reduction) OR AGHS-like density (H8, but ~empty) — not both. The S6 ω-solver
is not straightforwardly applicable.

**Caveats (why this is strong evidence, not absolute proof):** tested
squarefree divisors only (prime-power Λ untested, but analysis says it doesn't
help — high density needs m keeping full powers, still forcing large m);
enormous-scale untested (density trend is against us); and the FULL AGHS
algorithm on low-density H7 pools is untested (my a8 solver is too weak to
settle it). The honest status: the H8→S6 path as conceived is blocked; whether
the real AGHS algorithm tolerates H7's low density is the one open escape.

**Strategic fork (see PLAN.md).** Options: (a) implement the full AGHS solver
and test it directly on low-density H7 pools (the one untested escape);
(b) seek a solver designed for low-density many-prime pools; (c) pursue theory
(B1/B2/B3) / different r for a friendlier group; (d) write up the quantified
infeasibility of the L–P route via this solver family as a negative result
(anticipated from the start as publishable).

## A10 (option a): the low-density escape is CLOSED — quantified density threshold (2026-08-08)

`code/a10_wagner_density.py`. Option (a) asked: does the scalable AGHS-class
birthday solver work on our harvestable but low-density H7 pools? Implemented a
**correct Wagner-4 birthday solver** (4-sum to identity over a small-prime
group) and measured its *reach* — the largest component-count r it can solve —
as a function of identity-density ρ and pool N.

**Measured reach law:** (1−ρ)·r_max ≈ const (pool-limited effective reach), and
r_max grows only ~log(N):

| ρ | N | r_max | (1−ρ)·r_max |
|---|---|---|---|
| **0.004 (H7)** | 20,000 | **20** | 19.9 |
| **0.004 (H7)** | 100,000 | **24** | 23.9 |
| 0.5 | 20,000 | 28 | 14.0 |
| 0.9 | 20,000 | 128 | 12.8 |

**Verdict: the escape fails.** At H7's density (ρ≈0.004) the correct birthday
solver reaches ~20 components; our real groups have **thousands**. Two nails:
1. **Density:** to reach a ~1000-component group needs (1−ρ)·1000 ≲ 20, i.e.
   **ρ ≳ 0.98** (even optimistic high-k Wagner only lowers this to ~0.85–0.95).
   H7 gives ρ≈0.004 — two-plus orders of magnitude short.
2. **Pool:** r_max ~ log(N), so harvesting more is futile — 5× the pool bought
   +4 components; reaching 1000 would need an astronomically large pool. And
   the group grows with the harvest too, so the ratio never improves.

**This settles the strategic fork.** Option (a) — the one untested escape for
the twin-smooth/L–P route via AGHS-class solvers — is now closed with a measured
threshold, not a hand-wave. The AGHS solver needs ρ ≳ 0.98 (the divisor/H8
paradigm), which N1 showed is unharvestable under the double condition. So the
route is blocked at the solver by a **two-part quantified obstruction**:
low-density pools are unsolvable (A10) and high-density pools are unharvestable
(N1). This is the rigorous core for the option-(d) negative-result paper.

**Caveats:** Wagner-4 is the simplest birthday; higher-k Wagner reaches more
components (~linearly in the level count h, but h ≤ log₂N and each level costs
pool), lowering the threshold only to ρ≈0.85–0.95 — still ~100× above H7.
Model uses uniform Z/3 components; real components are mixed small primes, same
qualitative law. What remains genuinely open (not closed by A10): a
fundamentally different solver paradigm (option b), or a different r / construction
(option c).

## Caveats
- Coloring optimizer is greedy + random restarts; true optimum may be higher
  (annealing/ILP not yet tried). The 0.06 invariant is a *lower bound* on
  what optimization achieves.
