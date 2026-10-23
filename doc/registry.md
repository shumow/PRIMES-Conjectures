# Component registry: harvesters, solvers, and validators

> **Audit update, 2026-10-22:** S2-S4 have received correctness repairs backed
> by small independent regression oracles. S6/S7 use forced-zero mixture
> weights, S8 uses literal zero probability, and H8 counts side support.
> S8's minimum tracker has been repaired. Historical timings/frontiers are
> not revalidated measurements or proofs of infeasibility. Use
> [current audit status](integration-review-status.md#current-correctness-audit-2026-10-22)
> rather than historical gate decisions to plan new experiments.

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
| **H2 CHM-closure (py)** | `chm_closure.py` | ✅ | heuristic CHM iteration | no size cap; near-complete in historical comparisons, not certified complete; slow past B≈130 |
| **H3 CHM-closure (C)** | `chm_closure.c` | ✅ | same, compiled (`__int128`) | historical B=200 → 346,110: 99.98% of original CHM count, 99.2% of supplied corpus; ~3 min |
| **H4 PTE-import** | `import_pte_results.py` | ✅ | parse microsoft/twin-smooth-integers PTE results | 20,070 records; 0 LP-eligible (residue coverage poor) → calibration-only |
| **H5 corpus-stream** | `b547_pool_analysis.py` | ✅ | stream full TwinSmooths B=547 corpus → pool | needs private data in scratchpad; 73,163-element pool |
| **H6 partition-first** | `a1_yield_prototype.py`, `a2_grid.py` | ✅🔬 | fix Q₋/Q₊ first, enumerate m over Q₋, test (m+1)/2 over Q₊ | sampler-based projected ratio 13.8–44; not a completed production pool |
| **H7 co-designed** | `a5_codesign.py`, `a5_yield.py` | ✅🔬 | H6 + both factor bases odd-smooth-constrained (odd part of q−1 ≤ t0) | q−1-model max odd prime 6269→97; projected ratio ~7.7 at t0=100/B=2003; actual prime-power moduli require checking |
| **H8 divisor-paradigm** | `a9_divisor_harvest.py` | 🟡🔬 | fix disjoint bases; enumerate bounded squarefree divisors | historical N1 trials yielded 0–2 elements; reported fraction is side support, not full-group identity density; not a general impossibility result |

**Harvester selection.** **H6/H7** remain promising sampler-based production
candidates, pending real-pool modeling and a validated solver. For validation corpora
use **H1** (provably complete small end) or **H3** (near-complete fixed-B, fast).
**H5** taps Michael's full B=547 data. **H4** is calibration-only. **H8** is
limited by sparse yields in the tested configurations. Neither N1 nor A10
establishes a universal density threshold or closes the AGHS direction.

---

## Phase S — Solvers (find subset S, product ≡ (1 mod Λ₋, −1 mod Λ₊), |S| odd)

| id | file | status | method | frontier / regime |
|----|------|--------|--------|-------------------|
| **S1 coloring-opt** | `phase1a_calibration.py`, `b547_pool_analysis.py` | 🗄️ | greedy + partition-space local search over side-assignment | historical achieved ratios ~0.06–0.083 are lower bounds on optimization, not upper bounds on feasible colorings |
| **S2 GF(2) projection** | `a4_solver.py` | ✅ | corrected particular solution and kernel for mod-2 constraints + parity | exhaustively checked small affine systems; only G/2G, not the full 2-primary group; old timing unvalidated |
| **S3 anneal residual** | `a6_oddsolver.py` | 🟡 | shared GF(2) projection + local search checking odd components and higher 2-powers with carries | returned solutions checked in the original group; historical frontier requires rerun |
| **S4 exact MITM** | `a6_oddsolver.py` (`mitm_frontier`) | 🟡 | parity-aware meet-in-the-middle over the whole pool | small targets checked against enumeration; exponential; timeouts are inconclusive |
| **S5 per-prime+MITM** | `a7_lohniebuhr.py` | 🟡 | GF(l) reduction pre-pass then MITM core | scaffold; reduction pre-pass is phase-2 |
| **S6 ω-guided prototype** | `a8_omega_solver.py` | 🟡 | simplified strict top-down walk inspired by Löh–Niebuhr / AGHS | not the full AGHS method; forced-zero mixture; odd cardinality is not enforced |
| **S7 four-list birthday** | `a10_wagner_density.py` | ✅🔬 | bounded filtered four-sum diagnostic | historical rho=0.004 means literal P(0)=0.336 for Z/3; first-failure frontier of this implementation, not a general solver bound; outputs have even cardinality |
| **S8 adaptive cultivation** | `a12_adaptive_cultivation.py` | 🟡🔬 | finite-budget greedy filtering with random on-demand moves | literal-zero model; minimum tracker corrected; no number-theoretic pricing oracle or odd-subset certificate; historical floors require rerun |

**Solver selection.** **S2** supplies the validated mod-2 projection, **S4**
is a small-instance oracle including parity, and **S3** is a corrected residual
heuristic. S6-S8 are diagnostics with different models and constraints; no
validated end-to-end production solver is supplied. The full AGHS method and
other algorithms have not been excluded by these experiments.

---

## Validators / analyzers (support any combination)

| id | file | purpose |
|----|------|---------|
| V1 machinery tests | `verify_machinery.py` | unit-tests the r=5 congruence machinery + local lemmas (Prop 6.1 etc.) |
| V2 PTE import tests | `test_pte_import.py` | re-verifies every imported record (reconstruction, factorization, smoothness, primality) |
| V3 yield validation | `a2_validate_and_extend.py` | checks the harvest yield model against the complete B=547 corpus (model is conservative, 0.68×) |
| V4 group decomposition | `a4_solver.py` (`study_mod2_scale`) | full 2-primary size vs actual mod-2 projection and remaining residual bits; synthetic component model |
| V5 general-r degree | `a11_general_r.py` | harvest-burden degree per AKS modulus r (option c): floor is 2 (double condition), intrinsic to all r |
| V6 correctness regression | `test_*correctness.py` | independent small construction/binary/group checks and bounded benchmark model/reporting tests |

---

## Recommended combinations

- **Historically attempted:** H8 → S6. N1's particular finite squarefree
  configurations supplied few elements; this does not exclude other configurations.
- **Promising supply candidate:** H7 (projected ratio ~7.7) → *solver and
  actual-vector model still unvalidated*. A10 does not supply an AGHS threshold.
  A11/AG results require their separate proof audit before drawing universal
  conclusions about moduli or constructions.
- **Validation / calibration:** H1 or H3 (complete-ish corpus) → S1 (coloring)
  reproduces achieved coloring ratios and V3's historical model checks.
- **Regression harness for new solvers:** synthetic instances from
  `a8_omega_solver.make_structured` (tunable identity-density ρ) / 
  `a6_oddsolver.make_codesigned`, run S4 (exact, small) as an oracle against any
  new scalable solver on the same planted instances. Specify forced-zero bias,
  per-component literal identity probability, component orders, target/parity,
  and budgets before comparing results. Do not equate a synthetic parameter
  0.004 to measured H7 density.

## Gate status (see PLAN.md)

G1/G2 are historical supply/projection gates. **G3 has no validated production
pass**; A3 was not launched. Correctness regressions now pass for small solver
and benchmark cases, but the actual harvested group, constraints and resource
requirements remain to be established. A quantified experimental report is
possible; a general infeasibility theorem or closure of every modulus/algorithm
does not follow from the current experiments.
