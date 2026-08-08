# Component registry: harvesters, solvers, and validators

The pipeline is **Harvest → Solve**, with supporting **Validate/Analyze** tools.
Multiple interchangeable implementations exist for each phase; the winning
combination is not yet settled, so this catalogs every component built, its
status, interface, and how they combine. Status legend: ✅ works · 🟡 partial /
regime-limited · 🗄️ superseded but reusable · 🔬 measurement-only.

Full narrative + numbers: `data/FINDINGS.md`. Specs: `doc/harvest-spec.md`.
Method analysis: `doc/a4-solver-analysis.md`, `doc/twin-smooth-review.md`.

---

## Phase H — Harvesters (produce pool primes p = 2m+1, (m,m+1) twin smooth)

| id | file | status | paradigm | notes |
|----|------|--------|----------|-------|
| **H1 native-sieve** | `phase1a_calibration.py` | ✅ | enumerate all B-smooth m ≤ X, keep twins | provably complete ≤ X; small-end complete; caps ~B=130 in python |
| **H2 CHM-closure (py)** | `chm_closure.py` | ✅ | CHM iteration to Størmer closure | no size cap; recovers full fixed-B set; slow past B≈130 |
| **H3 CHM-closure (C)** | `chm_closure.c` | ✅ | same, compiled (`__int128`) | B=200 → 346,110 (99.98% of complete) in ~3 min; validated vs published records |
| **H4 PTE-import** | `import_pte_results.py` | ✅ | parse microsoft/twin-smooth-integers PTE results | 20,070 records; 0 LP-eligible (residue coverage poor) → calibration-only |
| **H5 corpus-stream** | `b547_pool_analysis.py` | ✅ | stream full TwinSmooths B=547 corpus → pool | needs private data in scratchpad; 73,163-element pool |
| **H6 partition-first** | `a1_yield_prototype.py`, `a2_grid.py` | ✅🔬 | fix Q₋/Q₊ first, enumerate m over Q₋, test (m+1)/2 over Q₊ | the **main-line** harvester; measurement mode; ratio 13.8–44 |
| **H7 co-designed** | `a5_codesign.py`, `a5_yield.py` | ✅🔬 | H6 + both factor bases odd-smooth-constrained (odd part of q−1 ≤ t0) | caps solver max-odd-prime (6269→97); ratio ~7.7 at t0=100/B=2003 |
| **H8 divisor-paradigm** | `a9_divisor_harvest.py` | ❌ tested/blocked | fix highly-composite Λ₋,Λ₊; harvest m \| Λ₋/2, (m+1) \| Λ₊/2 | N1 (2026-08-08): ~empty pool (0–2) under the double condition; can't get non-empty AND high-density. Gives AGHS density but unharvestable |

**Harvester selection.** For a real production pool use **H6/H7** (partition-first
— supply is over-provisioned, ratio ≫ gate). For ground-truth/validation corpora
use **H1** (provably complete small end) or **H3** (near-complete fixed-B, fast).
**H5** taps Michael's full B=547 data. **H4** is calibration-only. **H8** is the
next build, needed to feed **S6**.

---

## Phase S — Solvers (find subset S, product ≡ (1 mod Λ₋, −1 mod Λ₊), |S| odd)

| id | file | status | method | frontier / regime |
|----|------|--------|--------|-------------------|
| **S1 coloring-opt** | `phase1a_calibration.py`, `b547_pool_analysis.py` | 🗄️ | greedy + partition-space local search over side-assignment | for the **dataset-mining** route; hits the 0.06 wall — superseded by partition-first harvest, but still the tool if mining a fixed corpus |
| **S2 GF(2) 2-part** | `a4_solver.py` | ✅ | exact GF(2) Gaussian elimination on mod-2 constraints + parity | scales to full dim (4586 comps, 12s); solves ~16% of demand bits (the 2-part) |
| **S3 anneal odd** | `a6_oddsolver.py` | 🟡 | GF(2) 2-part + simulated annealing on odd residual (dense kernel moves) | stalls ≥19 odd components — weak; kept as baseline |
| **S4 exact MITM** | `a6_oddsolver.py` (`mitm_frontier`) | 🟡 | meet-in-the-middle over the whole pool | exact but exponential; caps ~N=40 / ~15 odd comps |
| **S5 per-prime+MITM** | `a7_lohniebuhr.py` | 🟡 | GF(l) reduction pre-pass then MITM core | scaffold; reduction pre-pass is phase-2 |
| **S6 ω-guided (AGHS)** | `a8_omega_solver.py` | 🟡 | subexponential distance-to-identity reduction (Löh–Niebuhr / AGHS) | **the scalable path**; first version solves only r≤20/high-density; full two-potential+birthday algorithm is the multi-turn build. Needs H8-structured pools |

**Solver selection.** **S6** is the intended production solver (AGHS built
Carmichael numbers with 10^10 factors this way) but needs completion **and** an
H8 divisor-paradigm pool. **S2** is a solved, reusable sub-step (the 2-part) for
any solver. **S3/S4** are honest baselines that map the generic-method frontier
(~15 odd comps) — useful for regression-testing S6's improvement. **S1** only
applies to the deprecated mining route.

---

## Validators / analyzers (support any combination)

| id | file | purpose |
|----|------|---------|
| V1 machinery tests | `verify_machinery.py` | unit-tests the r=5 congruence machinery + local lemmas (Prop 6.1 etc.) |
| V2 PTE import tests | `test_pte_import.py` | re-verifies every imported record (reconstruction, factorization, smoothness, primality) |
| V3 yield validation | `a2_validate_and_extend.py` | checks the harvest yield model against the complete B=547 corpus (model is conservative, 0.68×) |
| V4 group decomposition | `a4_solver.py` (`study_mod2_scale`) | 2-part vs odd-part bits, max odd prime, #distinct — sizes any pool for the solver |

---

## Recommended combinations

- **Production target (pending):** H8 (divisor-paradigm) → S6 (ω-guided), with
  V4 sizing the group and V1 verifying the final n. Blocked on completing S6 + H8.
- **Current best measured:** H7 (co-designed, ratio 7.7, max-odd-prime 97) →
  *solver TBD*; S4/S6 cap below its ~24k odd bits, which is why H8→S6 is needed.
- **Validation / calibration:** H1 or H3 (complete-ish corpus) → S1 (coloring)
  reproduces the 0.06 mining wall and V3's model checks. Historical baseline.
- **Regression harness for new solvers:** synthetic instances from
  `a8_omega_solver.make_structured` / `a6_oddsolver.make_codesigned`, run S4
  (exact, small) as an oracle against S6 (scalable) on the same planted instances.

## Gate status (see PLAN.md)

G1 ✅ (supply exists) · G2 ✅ (H6/H7 ratio ≫ gate) · G3 ❌ (no solver yet passes
at full odd dimension — S6+H8 is the route). A3 production harvest held until G3.
