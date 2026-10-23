# Track C findings: harvest-design comparison on actual certified pools

**Branch:** `research/feasibility-harvest-designs` · **Starting commit:**
`4128b62` (planning commit; main baseline `0fea665`) · **Driver commit:**
`8e6a8de` · **Date:** 2026-10-23 · **Python:** 3.11.17 (suite also passes the
repo's 3.9+ contract; see tests) · **Plan:** `harvest-solver-feasibility-plan.md` §7.

**Artifacts:** `code/fs_harvest.py`, `code/test_fs_harvest_correctness.py`
(11 tests; full repo suite 76 pass), `data/generated/fs_harvest.json.gz`
(SHA256 `cc2f39edc1583979eb5f…`; includes full instances, source SHA256s, the
frozen pilot dataset's SHA256 `008cf08ce3f0d3a2…`, seeds, budgets, timings).
Reproduce from the repository root:

```text
python -B -m unittest discover -s code -p "*correctness.py" -v
python -B code/fs_harvest.py --output <new path>
```

## 0. Scope and budgets

Four new cells plus a reproducibility anchor, inside plan §8 budgets
(≤ 5,000,000 draws/cell, pool cap 1,024, one process). Rationale for every
cell was declared in the driver **before** any run was interpreted. No solver
benchmarks were run (Track A owns those); no baseline file or dataset was
modified. All counts below are certified primes (probable-prime prefilter,
then independently checked full-factor Lucas certificates); every retained
vector's encoding was verified, and the serialized anchor/new instances
re-verify independently (`instance_from_json` + `verify_encoding` +
`verify_metrics`) in the test suite's small-family fixture path.

## 1. Anchor: the pilot reproduces exactly

`fs-anchor-rerun-medium-complete` (547/2735, j=3, seed 20261022, complete
4,366,296-draw scan) reproduced the frozen pilot's medium-complete family on
all compared fields: **483 accepted / 1,132 components / 3,951.73 group bits /
ratio 0.1222 / no obstruction** — `anchor_comparison.status = "reproduced"`,
six of six fields matching. Comparisons below are therefore against a
reconfirmed baseline, not a stale number.

## 2. The comparison table (measured, exact assembled groups)

| Cell | Design | Scan | Draws / family | N certified | Group bits | **N / bits** | Binary rank / rows | Nullity | Real-target necessary checks |
|---|---|---|---|---:|---:|---:|---|---:|---|
| anchor | 547/2735, j=3 | complete | 4.37M = family | 483 | 3,951.7 | **0.1222** | 393 / 394 | 90 | pass (unresolved) |
| c1 | 547/2735, **j=4** | sampled 1.6% | 5M / 322.0M | 13 | 843.9 | 0.0154 | 13 / 96 | 0 | **GF(2) obstruction** |
| c2 | 547/**5470**, j=3 | sampled 12.6% | 5M / 39.5M | 253 | 5,746.2 | 0.0440 | 253 / 541 | 0 | **GF(2) obstruction** |
| c3 | **1259**/2735, j=3 | **complete** | 1.20M = family | 225 | 3,649.4 | 0.0617 | 225 / 366 | 0 | **GF(2) obstruction** |
| c4 | **1259/6295**, j=3 | sampled 13.1% | 5M / 38.2M | 430 | 8,153.9 | 0.0527 | 430 / 740 | 0 | **GF(2) obstruction** |

Supporting measurements (all in the dataset): per-draw acceptance
1.106e-4 (anchor), 2.60e-6 [Wilson 95%: 1.52–4.45e-6] (c1), 5.06e-5
[4.47–5.72e-5] (c2), 1.878e-4 (c3, exact), 8.60e-5 [7.82–9.45e-5] (c4);
duplicates 0/0/9/0/24; mean literal identity fraction 0.19–0.26 across all
cells (forced fraction 0.007–0.076); every cell stopped at `family_exhausted`
or `candidate_cap`, never at the pool cap.

## 3. What is cleanly established vs. what is sampled

**Clean (complete scan vs. complete scan): the anchor beats c3.** Raising the
plus bound to 1259 *does* raise per-candidate acceptance (1.878e-4 vs
1.106e-4 — the historical "plus side is density-critical" effect is real and
now exactly measured), but it shrinks the three-factor family 3.6× and adds
~726 plus-side bits, so the exact ratio drops 0.1222 → 0.0617. At these
scales, widening the plus base is a net loss under exact accounting.

**Sampled cells are truncation-biased and not directly comparable to complete
cells.** For c1/c2/c4, both the numerator (distinct primes found) and the
denominator (bits of the group assembled from *found* primes only) are
truncated by the draw cap, and they do not truncate proportionally. Their
table ratios are *observed-pool* ratios, valid for the pools as harvested,
not estimates of the full-family design ratio.

**The nullity-0 pattern (new, and the sharpest observation of this run).**
Every cell except the anchor has binary rank = N (each pool vector
independent mod 2) and a *certified* GF(2) obstruction against the real
target. The anchor — the only pool whose size exceeds its binary row count
(483 > 394) — is the only one whose binary system is even consistent. The
mechanism: an undersupplied pool uses more distinct prime powers (binary
rows ≈ distinct used prime powers + parity) than it has elements, so the
real target generically falls outside the mod-2 column space. Measured
blocks (distinct prime powers) vs N: anchor 393/483; c1 95/13; c2 540/253;
c3 365/225; c4 739/430. **A harvest design is only viable once its pool size
clears the number of distinct prime powers it touches — i.e., prime *reuse*,
not raw hit count, is the quantity to maximize.** This gives Track C a crisp,
cheap screening diagnostic (N vs. blocks) that predicts necessary-check
failure before any group assembly.

## 4. Extrapolations (assumption-laden — labeled, not asserted)

Under the binomial model (with-replacement draws over the candidate family;
population hits ≈ per-draw rate × family size; distinct ≈ population here
since population draws are distinct combinations), completed scans would be
expected to yield roughly: c1 ≈ 840 primes [490–1,430]; c2 ≈ 2,000
[1,770–2,260]; c4 ≈ 3,290 [2,990–3,610] — against denominators that
**saturate**: a design's group bits are bounded by the bits of its full
factor bases (c2's minus side, fully used, is ~7.3k bits; it is already at
4.9k with 12.6% coverage). If those extrapolations held, full-scan ratios
would land near ~0.24 (c2) and ~0.33 (c4) — *better than the anchor*,
reversing the truncated table's ordering, with c4's full family also likely
clearing the nullity threshold (N ≈ 3,290 vs ≤ ~820 possible blocks). These
are **not measurements**: they assume the per-draw rate is uniform across
the family (lexicographic position effects untested), ignore the pool cap
(1,024 would bind first, capping both N and reuse gains), and say nothing
about target feasibility. Zero weight should be placed on them beyond
motivating the next bounded measurement.

## 5. Recommendation (one, with uncertainty and stop conditions)

**Authorize one second-wave cell: a complete scan of the c2 design
(547/5470, j=3, ~39.5M draws ≈ 8× the current per-cell cap, pool cap raised
to 4,096 or explicitly accepted as binding).** It is the cheapest cell that
directly tests the two live hypotheses this run surfaced — that ratios
improve as families are scanned to completion (bit saturation), and that
clearing the N > blocks threshold removes the binary obstruction — with
exact accounting end-to-end and an estimated cost of minutes of harvest plus
tens of minutes of instance build (the current 39.5M-family cells harvested
at ~0.4–0.5M draws/s). Uncertainty: moderate — the binomial extrapolation
(§4) could fail at the family's edges, and even a ratio ~0.25 with a
consistent binary system leaves the pool far from a demonstrated-solvable
regime; this would be a supply-structure datum, not a feasibility result.
Stop conditions honored now: no cap was raised and no cell added beyond the
declared four without authorization; this run ends here.

If the coordinator prefers zero new compute: the standing deliverable is
that **within plan budgets, no nearby design beats the pilot's own cell, the
undersupply diagnosis of PR #3 is robust across the j and allocation axes,
and undersupplied pools carry certified obstructions as a rule (nullity-0
mechanism), not as bad luck.**

## 6. Handback checklist (plan §10)

- **Branch/commits:** `research/feasibility-harvest-designs`; start
  `4128b622` (plan commit; recorded main baseline `0fea665f`); code
  `8e6a8de`; this document and the dataset follow it.
- **Files added (C-owned only):** `code/fs_harvest.py`,
  `code/test_fs_harvest_correctness.py`, `data/generated/fs_harvest.json.gz`,
  `doc/fs-harvest-findings.md`. No shared file touched; frozen pilot dataset
  read-only (SHA256 recorded).
- **Tests:** 11 Track C tests + full repo suite (76) pass; interpreter
  3.11.17; standard library only.
- **Inputs/seeds:** harvest seeds 20261022 (anchor) / 20261023 (cells);
  structure-sampling seed = harvest seed; all budgets in the dataset's
  per-cell `harvest.config`; real target `(1 mod Λ₋, −1 mod Λ₊)` per cell's
  own assembled LCMs, odd cardinality ≥ 3 (pilot conventions, unchanged).
- **Results classification:** anchor = reproduced baseline, real target
  passes necessary checks, unresolved; c1–c4 = certified GF(2) obstructions
  (exact witnesses stored and `verify_obstruction`-checked); sampled-cell
  ratios = observed-pool statistics; §4 = labeled extrapolations;
  no exact search or feasibility claim anywhere.
- **Shared bugs for the coordinator:** none found; baseline interfaces were
  sufficient as-is.
- **Pushed:** yes (branch only; no PR opened, none authorized).
