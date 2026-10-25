# S3 findings: complete c2 family — scan executed under approved budget

**Work item:** S3, `PLAN.md` current §5 · **Branch:** `research/boolean-c2-complete`
(start `0c9f03f`; proposal `81c577d`; run `1639075`; this report follows) ·
**Date:** 2026-10-25 · **Python:** 3.11.17 · **Approval:** user approval of
`doc/bf-harvest-proposal.md` recorded in session before execution.

**Artifacts:** `data/generated/bf_harvest.json.gz` (schema `bf-harvest/v1`,
5.0 MB, full provenance) · `data/generated/bf_harvest_membership.json`
(side report, schema `bf-harvest-membership/v1`) · code and tests from the
proposal commit plus the post-scan stages (combined suite: **131 pass**).
Reproduce: `python -B code/bf_harvest.py --approved --replace` (approval
required); independent re-check:
`python -B code/bf_harvest.py --verify data/generated/bf_harvest.json.gz`.

## 1. Scan outcome (complete, no binding limit)

- **Coverage:** 39,529,340 / 39,529,340 combinations, 40 contiguous shards,
  manifest sums exactly; `stop_reason = family_exhausted`;
  `complete_family_scan = true`. Zero duplicates (complete enumeration draws
  each combination once), zero certificate exhaustion, zero uint64
  rejections; 2,471,005 mod-40 survivors, 20,603 smooth, 1,250 power-cap
  rejections, 2,234 probable primes — **all 2,234 certified** (full-factor
  Lucas, witnesses within bases 2–65) and admitted.
- **Pool cap 4,096 never bound** (2,234 accepted).

## 2. The completed-family instance (exact, independently re-verified)

| Quantity | Value |
|---|---|
| Certified primes / retained units | **2,234 / 2,234** (no nonunit exclusions) |
| Components / blocks (distinct prime powers) | 2,126 / 719 |
| Exact group bits (Λ₋ 6,991-bit, Λ₊ 880-bit) | **7,864.98** |
| **N / group bits** | **0.2840** |
| Binary rank / rows · nullity | 719 / 720 · **1,515** · consistent |
| Coordinate / GF(ℓ) obstructions | **none** — passes all implemented necessary checks |
| Identity fractions (literal / forced / bit-weighted) | 0.1899 / 0.0071 / 0.0917 |
| **Minimum Boolean cardinality (exact integers)** | product of the 190 largest pool primes first exceeds Λ₋ ⇒ any solution has **≥ 191 factors** (odd) |

Independent re-verification (`--verify`): every prime certificate, every
vector encoding and every recorded structure metric re-derived from first
principles against the saved report; coverage manifest re-summed. All pass.

## 3. Measured costs vs. the approved proposal

| Stage | Proposal estimate | Measured |
|---|---|---|
| Enumeration + certificates | 2–5 min | **46.7 s** |
| Group construction | 2–5 min | **10.5 s** |
| Structure + necessary checks | 10–40 min | **~63 s** (within the 120.7 s end-to-end) |
| End-to-end wall | 20–60 min (2 h stop) | **120.7 s** |
| Peak process RSS | 300–700 MiB (2 GiB allowance) | **518.3 MiB** (measured, `ru_maxrss` of the child) |
| Artifact | 5–15 MB (50 MB ceiling) | **5.0 MB** |

No limit was raised or approached; the conservative structure-stage estimate
was the main overshoot (odd-ℓ eliminations were cheaper than the linear-in-N
worst case).

## 4. Comparisons (completed family kept separate from the old sampled pool)

- **vs. the anchor (both complete scans, exact accounting):** N/bits
  **0.2840 vs 0.1222** — the completed wider-minus design beats the pilot's
  own cell by 2.3×, reversing the first-wave *truncated* ordering exactly as
  the bit-saturation extrapolation predicted.
- **vs. the old sampled c2 (same design, 12.6% coverage):** the sampled pool
  (N = 253) had a certified GF(2) obstruction and observed ratio 0.0440;
  the completed family (N = 2,234 > 720 binary rows) is consistent with
  nullity 1,515 and no obstruction anywhere. The first-wave obstruction is
  now *demonstrated* to have been a truncation phenomenon for this design —
  consistent with the (heuristic, non-theorem) nullity pattern from the
  first wave.
- **Extrapolation scorecard (predictions were on record before the run):**
  distinct supply predicted ≈ 2,070 [1,840–2,340] → **actual 2,234** (inside
  the interval); ratio predicted ≈ 0.25 → actual 0.2840.

## 5. Track B membership stage — inconclusive at the declared limits

`--membership` ran first-wave B's exact checker on the full 2,126 × 2,234
instance under declared `Limits` (290 s solver budget inside a 300 s
`fs_controls.run_limited` watchdog; 20M cells; 1.5 GiB workspace estimate;
4,096-bit scalars). **Outcome: `inconclusive` — watchdog timeout.** Per the
house vocabulary this is a resource stop, not evidence in either direction;
the limits were not raised (doing so needs separate authorization). The
side report records the declared limits, input hash and outcome.

## 6. Gate decision and status (plan §5)

- The new target **passes all implemented necessary checks**, so per the
  gate there is no obstruction to analyze — and equally **no solver budget
  is spent by this work item**: Boolean feasibility of this target is
  **open** and belongs to S1. "Passes necessary checks" is not subgroup
  membership (unresolved here) and not Boolean feasibility.
- **N/bits = 0.284 is not a supply milestone** (the heuristic milestone in
  the first-wave report was ratio > 1); it is, however, the best exactly
  accounted pool so far, and the first with no certified obstruction beyond
  the original 483 anchor.
- The ≥ 191-factor bound sharpens the search picture the same way the
  483-pool's ≥ 93 did: any Boolean solution here is a ≥ 191-subset of
  2,234 — far from small-support calibration territory.
- **No further family expansion follows from this outcome** (plan §5).

## 7. One recommendation, with uncertainty and stop conditions

Hand the instance to the coordinator for two bounded follow-ups, each
needing its own authorization: (i) a longer-budget Track B membership run
on this instance (the 483-pool resolved within 60 s; this one needs more
than 300 s — scale unknown, so propose wall 1,800 s with the same
declared-Limits discipline, outcome inconclusive-on-limit); (ii) S1
calibration may use this pool's small prefixes like the pilot's. Uncertainty:
membership could still return `nonmember` with a character certificate —
passing prime-field quotient checks does not preclude a mixed prime-power
obstruction (first-wave B's own fixture demonstrates exactly that). S3
itself stops here.

## 8. Handback checklist (plan §7)

- **Branch/commits:** `research/boolean-c2-complete`: `81c577d` (proposal +
  gated implementation), `1639075` (approved run + post-scan stages), this
  report's commit. Pushed (worker branch only; no PR opened).
- **Owned files only:** `code/bf_harvest.py`,
  `code/test_bf_harvest_correctness.py`, `doc/bf-harvest-proposal.md`,
  `doc/bf-harvest-findings.md`, `data/generated/bf_harvest.json.gz`,
  `data/generated/bf_harvest_membership.json`. No shared or frozen file
  touched.
- **Tests:** combined suite 131 pass (`python -B -m unittest discover -s
  code -p "*correctness.py"`); includes the pilot-equivalence lock, cap and
  coverage regressions, and bounded post-scan stage tests.
- **Budgets:** all declared in the proposal and above; none raised; the only
  binding limit (membership watchdog) is reported as inconclusive.
- **Outcome classification:** complete exact scan of the declared scope;
  independently verified certificates/encodings/metrics; necessary checks
  pass (not membership, not Boolean feasibility); membership inconclusive
  (resource stop); no counterexample claim of any kind.
