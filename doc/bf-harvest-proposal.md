# S3 budget proposal: complete scan of the c2 family (requires approval before execution)

**Work item:** S3, `PLAN.md` "Current next steps (2026-10-24)" §5 ·
**Branch:** `research/boolean-c2-complete` (off
`integration/boolean-feasibility-study`, start `0c9f03f`) ·
**Owned prefix:** `bf_harvest` · **Date:** 2026-10-25 · **Status: PROPOSAL —
nothing beyond the bounded correctness tests has been executed.**

Implementation is ready and tested (`code/bf_harvest.py`,
`code/test_bf_harvest_correctness.py`; combined suite 129 tests pass): the
production command refuses to run without `--approved`, and the test suite
exercises the scanner only on the complete small 113/565 family, where it
reproduces the pilot harvest **record-for-record including certificates and
all counters** (the admissibility-equivalence lock the plan requires).

## 1. Exact configuration (frozen in source as `C2_COMPLETE`)

| Parameter | Value |
|---|---|
| Family | `fs-c2-wider-minus` design: plus bound 547 (odd primes ≠ 5), minus bound 5470, **3 distinct minus factors** |
| Admissibility | identical to the pilot: m ≡ 1 (mod 40); p = 2m+1 < 2⁶⁴; (m+1)/2 completely Q₊-smooth; prime-power cap **8192**; BPSW prefilter then **exact full-factor Lucas certificate** (witness bases 2–65); independent `verify_prime` on every record; probable primes never admitted |
| Coverage | complete lexicographic enumeration of all **39,529,340** combinations |
| Accepted-pool cap | **4,096 global** (a resource ceiling, not a supply prediction) |
| Seed | 20261025 (used only by `measure_structure` correlation sampling; enumeration is deterministic and seed-free) |

## 2. Coverage / shard scheme and worker count

- **One worker process. No parallelism.** The harvest stage is minutes of
  single-thread work (measured basis below), so parallel shards would add
  cap-splitting and coverage risk with no payoff. The global pool cap is
  enforced across shards by construction (single accumulator; a regression
  test proves cap 3 over 50 shards admits 3 total, not 3 per shard).
- **Sharding is checkpoint granularity:** 40 contiguous index ranges
  (~988,234 combinations each) over the lexicographic combination index
  space, produced by exact unranking (tested against `itertools.combinations`
  positions). The saved report carries a **coverage manifest**: per-shard
  range, draws, accepted, seconds, status; the scan is called complete only
  if Σ draws = 39,529,340 and the pool cap never bound. If the cap binds,
  the manifest records the exact covered prefix and `stop_reason =
  pool_cap`, and that partial scope is the entire claim.

## 3. Cost estimates (each with its calibration source; none is a measurement of the new scale)

All calibration numbers are recorded first-wave measurements in
`data/generated/fs_harvest.json.gz` (schema v2) on this baseline, same
machine class, CPython. Estimates marked **E** are extrapolations.

| Stage | Calibration (recorded) | Estimate for this run (E) |
|---|---|---|
| Enumeration + filters + certificates | c2 sampled cell: 5,000,000 draws incl. 262 certificates in ~11 s (~2.2 µs/draw) | 39.53M draws ≈ **2–5 min** |
| Expected distinct supply | corrected binomial from the sampled cell: ≈ 2,070 [95%: 1,840–2,340] | pool cap 4,096 not expected to bind (margin ≥ 1.75×); **if it binds, partial scope is published, not papered over** |
| Group construction (discrete logs) | c4: 430 records × 739 blocks = 317,770 logs in 17 s (~19k logs/s); anchor ~38k/s | ~2,100 × ~740 blocks ≈ 1.6M logs ≈ **2–5 min** |
| Structure + necessary checks | first-wave cells completed in seconds at N ≤ 483; odd-ℓ rref cost grows ~linearly in N (columns) | **10–40 min** (dominant uncertain stage; see wall allowance) |
| Encoding verification + serialization | `verify_encoding` ≈ one small-modulus check per (record, block) ≈ 1.6M ops; first-wave 5-cell dataset serialized to 2.4 MB gz | **≈ 5 min**; artifact ≈ 5–15 MB gz |
| Independent re-verification of the saved report | pilot verifier pattern | **≈ 5–15 min**, separate invocation |

**Totals requested for approval:**

- **Wall time:** estimate 20–60 min end-to-end, single process; request a
  **2-hour hard stop** (enforced by the operator/watchdog pattern; if it
  binds, the run is reported as `resource_limit` with whatever stage it died
  in — never as a result).
- **Memory:** the in-memory instance (~2,100 vectors × ~2,400 components)
  plus JSON serialization is estimated at 300–700 MiB peak — **above the
  plan's default 512 MiB working target**, so this proposal explicitly
  requests a **2 GiB process-memory allowance** for the build/serialize
  stages; measured peak RSS will be reported, distinguishing it from the
  allowance.
- **Storage:** one new artifact `data/generated/bf_harvest.json.gz`
  (schema `bf-harvest/v1`, full provenance: LF-normalized source SHA256s,
  config, manifest, counters, timings), ceiling **50 MB**. No frozen
  artifact is touched; no first-wave report schema is reused or weakened.
- **CPU:** single core; aggregate CPU ≈ wall.

## 4. Post-scan analysis stages (same approval, separately capped)

1. Exact assembled group, distinct supply, rank/nullity, literal vs forced
   identity fractions, and the existing necessary target checks — all via
   the read-only pilot interfaces (`build_instance`, `measure_structure`),
   inside the wall budget above.
2. **Gate (plan §5):** if the new full-pool target has a verified
   obstruction, no solver budget is spent against it; if it passes, Boolean
   feasibility remains open and is *not* pursued by this work item.
3. **Track B membership checker** on the new instance, where budgets permit:
   proposed as a separate invocation of `fs_reachability.membership` with
   declared `Limits` (wall 300 s via the `fs_controls.run_limited` watchdog,
   its own cell/byte reserves), outcome `inconclusive` on any limit. This
   stage touches no B-owned file; if interface friction appears, it is
   reported to the coordinator rather than worked around.
4. Comparison tables keep the completed family separate from the old sampled
   pool; per-draw statistics use the certified-draw numerator (accepted +
   duplicates); distinct supply and group size are reported as measurements,
   never binomial estimates.

## 5. Stop conditions and non-goals

- The pool cap, wall stop, memory allowance and storage ceiling are never
  raised mid-run; any binding limit ends the run with its partial scope
  published.
- **No further family expansion follows from any outcome** (plan §5 gate).
- No production counterexample search; no solver calibration (S1 owns it);
  no obstruction theory (S2 owns it). A ratio above one, if it appears,
  is a heuristic supply milestone only.

## 6. What approval covers (checklist for the approver)

- [ ] Run `python -B code/bf_harvest.py --approved` once, with the frozen
      §1 configuration and §2 scheme, on this branch.
- [ ] 39,529,340-draw complete enumeration (≈ 7.9× the first-wave per-cell
      candidate cap) and global pool cap 4,096 (vs 1,024).
- [ ] 2-hour wall hard stop · 2 GiB memory allowance · ≤ 50 MB new artifact.
- [ ] The §4 post-scan stages, including one `Limits`-bounded membership
      invocation.

Nothing else is authorized by an approval of this document.
