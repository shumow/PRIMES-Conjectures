# S3 findings: complete c2 family — scan executed under approved budget

**Work item:** S3, `PLAN.md` current §5 · **Branch:** `research/boolean-c2-complete`
(start `0c9f03f`; proposal `81c577d`; run `1639075`; this report follows) ·
**Date:** 2026-10-25 · **Python:** 3.11.17 · **Approval:** user approval of
`doc/bf-harvest-proposal.md` recorded in session before execution.

**Artifacts:** `data/generated/bf_harvest.json.gz` (schema `bf-harvest/v1`,
5.0 MB, full provenance) · `data/generated/bf_harvest_membership.json`
(side report, schema `bf-harvest-membership/v1`) · code and tests from the
proposal commit plus the post-scan stages (combined suite: **140 pass**,
including the PR #9 review regressions).
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

## 5. Track B membership — resolved: the target is a subgroup member

**Revision (2026-10-25, after the coordinator's PR #9 review).** The first
membership attempt reported a watchdog timeout at 300 s. The review identified
a shared watchdog defect (also reported on PR #8): `run_limited`'s parent
joins the worker before draining the result queue, so a *large successful
result* (a full 2,234-coefficient certificate pickles to ~440 KB) deadlocks
the hand-off and is indistinguishable from a timeout. The earlier "needs more
than 300 s" inference was therefore unjustified and is withdrawn.

With the stage reworked to a **file-backed result handoff** (only a tiny
summary crosses the queue; the full result is written to a file) and rerun
under the **same declared limits** (290 s solver inside a 300 s watchdog —
no budget escalation):

- **Status: `member`** — the completed-family real target is an
  integer-coefficient member of the subgroup generated by the pool vectors.
- Wall 96.9 s, solver 87.7 s, 1.17e9 work units, 6.36M peak cells — the
  original attempt had in fact completed within budget and been eaten by the
  queue deadlock, exactly as the review hypothesized.
- The **full certificate (2,234 coefficients, 483 nonzero) is persisted** in
  `data/generated/bf_harvest_membership.json` and was independently
  re-verified here with `fs_reachability.verify_certificate` (direct
  reproduction of the target in the original component orders). Later
  verification does not depend on rerunning anything.
- Worker errors are now classified distinctly (`worker_error` with the error
  detail preserved), never as budget stops.

Membership is **not** Boolean feasibility: integer coefficients may be
arbitrary; the ≥ 191-factor Boolean bound is unchanged.

## 5b. The coordinator's index-two structural argument — premises verified

The PR #9 review contributed a coordinate-specific argument that settles
membership without any solver run, under explicit hypotheses which
`--verify` now checks computationally on the saved instance:

1. **Two order-2 coordinates are 1 on every generator and on the target**
   (verified: components **1854 and 2125** — the plus-3 2-primary coordinate
   and the parity coordinate). Hence the generated subgroup H lies in their
   diagonal kernel K, a split index-2 subgroup of G.
2. **Binary rank = rows − 1 = 719, consistent** (verified by local,
   generator-independent elimination): after merging the duplicate order-2
   row, H surjects onto K/2K, so the finite 2-group quotient K₂/H₂
   satisfies Q = 2Q, forcing H₂ = K₂.
3. **All 176 odd prime fields have full row rank** (verified likewise):
   H_q + qG_q = G_q, so H_q = G_q for every odd q.

Therefore H = K, **[G : H] = 2**, and the real target — which satisfies the
diagonal relation — is a member. This agrees with, and is independently
corroborated by, the backend certificate of §5. As the review emphasizes:
the split relation on the two concrete order-2 coordinates is essential
(binary rank alone does not settle prime-power membership), the argument
produces no Boolean subset, and no larger harvest or solver budget follows.
`verify_saved` reports the premises as `index_two_argument_premises: True`
for this instance and would report their failure on any pool where the
hypotheses do not hold.

## 6. Gate decision and status (plan §5)

- The new target **passes all implemented necessary checks** (now
  independently recomputed by `--verify`, not trusted from stored flags), so
  per the gate there is no obstruction to analyze — and equally **no solver
  budget is spent by this work item**: Boolean feasibility of this target is
  **open** and belongs to S1. "Passes necessary checks" and "integer-
  coefficient subgroup member" (§5, §5b) are each weaker than Boolean
  feasibility.
- **N/bits = 0.284 is not a supply milestone** (the heuristic milestone in
  the first-wave report was ratio > 1); it is, however, the best exactly
  accounted pool so far, and the first with no certified obstruction beyond
  the original 483 anchor.
- The ≥ 191-factor bound sharpens the search picture the same way the
  483-pool's ≥ 93 did: any Boolean solution here is a ≥ 191-subset of
  2,234 — far from small-support calibration territory.
- **No further family expansion follows from this outcome** (plan §5).

## 7. One recommendation, with uncertainty and stop conditions

Membership of this instance is **settled** (§5 certificate + §5b structural
argument, mutually corroborating), so no longer-budget membership run is
needed or recommended. The remaining items: (i) the **shared watchdog
queue defect** in `fs_controls.run_limited` belongs to the coordinator —
PR #8 reports the same issue; this branch works around it in C-owned code
only (file-backed handoff) without touching the shared module; (ii) S1 owns
Boolean feasibility on this instance and may use its small prefixes for
calibration like the pilot's. Uncertainty that remains is exactly the
Boolean question: index-2 membership with a 483-nonzero integer certificate
says nothing about a 0/1 solution, and the ≥ 191-factor bound stands. S3
stops here.

## 8. Handback checklist (plan §7)

- **Branch/commits:** `research/boolean-c2-complete`: `81c577d` (proposal +
  gated implementation), `1639075` (approved run + post-scan stages), this
  report's commit. Pushed (worker branch only; no PR opened).
- **Owned files only:** `code/bf_harvest.py`,
  `code/test_bf_harvest_correctness.py`, `doc/bf-harvest-proposal.md`,
  `doc/bf-harvest-findings.md`, `data/generated/bf_harvest.json.gz`,
  `data/generated/bf_harvest_membership.json`. No shared or frozen file
  touched.
- **Tests:** combined suite 140 pass (`python -B -m unittest discover -s
  code -p "*correctness.py"`); includes the pilot-equivalence lock, cap and
  coverage regressions, and bounded post-scan stage tests.
- **Budgets:** all declared in the proposal and above; none raised; the only
  binding limit (membership watchdog) is reported as inconclusive.
- **Outcome classification:** complete exact scan of the declared scope;
  independently verified certificates/encodings/metrics; necessary checks
  pass (not membership, not Boolean feasibility); membership inconclusive
  (resource stop); no counterexample claim of any kind.
