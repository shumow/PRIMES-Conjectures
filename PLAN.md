# Research plan: Boolean feasibility and harvest structure

## Current engineering gate (2026-10-29)

The reviewed study and coordinator documentation have landed on `main` through
[PR #11](https://github.com/shumow/PRIMES-Conjectures/pull/11) and
[PR #12](https://github.com/shumow/PRIMES-Conjectures/pull/12), at
`e6b756c20365ea40245aaa6734f9f3044ac791ed`. The landing gate is complete.

The next task is the [shared watchdog repair](doc/shared-watchdog-repair-plan.md):
fix the existing large-result delivery path while explicitly preserving frozen
source-manifest verification. That document records the chosen design,
synthetic regressions, provenance migration, validation and review gates.
It is a plan only; implementation and all new experiments remain unstarted.
After the tested repair, the separately bounded next research proposal remains
the next scientific gate. No old execution allowance is renewed.

## Reviewed coordinator closeout snapshot (2026-10-26)

**Status:** the declared Boolean Feasibility Study is complete and reviewed,
with S1/S2/S3 combined on `integration/boolean-feasibility-study`. This closes
the declared study, not the Boolean feasibility question.

**Reviewed study merge:** `fd651caa2fcb0b6e72c2a3e1d7a90210259ce755`
([PR #10](https://github.com/shumow/PRIMES-Conjectures/pull/10)), preserving
the reviewed implementation tree `1796b994908dfc4286eebbdf8c1e9406543b3a66`.
S2 and S3 were already accepted in PRs #8 and #9.

**Main at this closeout snapshot:** `0c9f03fb1e00dfd85cb9e2b37e15ed1e727c4915`;
the study has not yet landed there. The coordinator documentation pass does
not itself push, open a PR or merge to `main`.

The [combined summary](README.md#boolean-feasibility-study-reviewed-integration)
links the established results and limitations. The final 254-test suite
passed on Python 3.9.13 and 3.14.5 with optional CP-SAT 9.15.6755 and no skips.
Independent review accepted the frozen artifacts and interpretation.
This documentation-only closeout changes no implementation, dataset or protocol.

### Immediate gates

1. Finish the coordinator documentation and preserve the original briefs,
   results, certificates, source hashes and failed as well as successful rounds.
2. With publication authorization, land the documentation with the reviewed
   study and open `integration/boolean-feasibility-study` into `main`.
   Check live ancestry first; do not open a duplicate PR or repeat a completed
   landing. Use a reviewed, history-preserving merge rather than overwrite
   another branch. No further experiment is needed for this landing.
3. Before any next-phase worker relies on the shared watchdog, fix
   `fs_controls.run_limited` to drain the result queue before `join` (or hand
   the result off through a file), with a regression test that reproduces the
   deadlock on a result larger than the OS pipe buffer. This is a
   shared-baseline code change outside this documentation closeout and needs
   its own tested commit.
4. After landing, propose the next bounded research phase from the existing
   evidence before executing it. The cap-17 success does not bridge the real
   93-/191-factor requirements, and integer membership does not resolve Boolean
   feasibility. A new configuration needs fresh validation cases, declared
   aggregate budgets and explicit execution approval.

**No remaining execution allowance is created by this closeout.** S1's three
frozen rounds used **30 full-pool calls (3 + 9 + 18)**; the last once-only
authorization is consumed and its holdouts are observed. S3's approved complete
c2 scan is finished, not a standing harvest budget. Unrun gated cases and old
proposals are not permission to resume, replicate, retune or enlarge a run.
Use independent saved-report verification instead of regeneration.

---

## Archived Boolean Feasibility Study brief (2026-10-24)

**Original planning baseline:** `c114e84465495d5e414590393b41eb3dca341821`, the merge of
[PR #6](https://github.com/shumow/PRIMES-Conjectures/pull/6).

**Original planning branch:** `research/boolean-feasibility-plan`.

**Status when written:** planning and work allocation only. Recording this
brief did not authorize the larger c2 harvest or a production search.
The completed rounds and subsequent approvals are recorded in their findings;
the closeout above governs the current state.

The following assignments and original budgets are retained as the study
contract and history, not renewed execution instructions. The original Plan v2
is also preserved below as historical context, not a competing plan.
The earlier [first-wave plan](doc/harvest-solver-feasibility-plan.md) records
the contracts and ownership of the completed A/B/C work. Use **S1/S2/S3**
below for these study assignments; do not confuse them with either older
track-label scheme.

### 1. Verified starting point and objective

The integrated [feasibility baseline](README.md#combined-harvest-and-solver-feasibility-baseline)
has 116 correctness tests passing on Python 3.9.13 and 3.14.5, plus independent
review and saved-artifact verification. Its results are:

- [First-wave A: controls](doc/fs-controls-findings.md): the bounded exact-k
  solver recovers the full 483-prime pool's support-3 controls. No tested
  method recovers its support-5, 9 or 17 controls within the stated budgets.
  Nullity-zero control successes are consistency checks, not evidence of
  residual-search power.
- [First-wave B: membership](doc/fs-reachability-findings.md): the real
  483-prime fixed-LCM target belongs to the generated subgroup, with a
  non-Boolean integer witness. The subgroup is proper, with index at least
  two; the quotient ranks do not establish its exact full prime-power index.
  Membership neither solves nor disproves Boolean feasibility.
- [First-wave C: harvests](doc/fs-harvest-findings.md): the four new measured
  pools have certified binary target obstructions and lower observed
  supply/group-bit ratios than the anchor. Three are capped samples, so this
  does not rank the completed families.
- For the real full-483 fixed-LCM target, exact products of the largest
  eligible primes give `P_91 < Lambda_minus + 1 <= P_92`. Odd cardinality
  therefore requires **at least 93 selected distinct primes**. This bound
  does not apply to the small-support planted targets or invalidate the
  unrestricted integer witness.

**Objective:** establish whether better Boolean solving, better supply, or
an arithmetic redesign is the justified next investment. A small-control
success is a capability milestone, not a near-counterexample result.

The frozen pilot input is [real_pool_pilot.json.gz](data/generated/real_pool_pilot.json.gz),
SHA256 `008cf08ce3f0d3a2f987bff26d5abd04bf4c41050f949ae0fdc4f4192b6969de`.
Use the existing `fs_controls`, `fs_reachability` and `fs_harvest` artifacts
read-only; retain the parent LCMs when reproducing a recorded case.

### 2. Agent allocation and ownership

| Track | Owner profile | Objective | Proposed branch | Owned prefix |
|---|---|---|---|---|
| S1: Boolean model and calibration | This assistant: largest reasoning/context budget | Build one exact Boolean formulation and determine whether it improves interpretable control recovery | `research/boolean-solver-calibration` | `bf_solver` |
| S2: arithmetic obstructions | Independent agent; bounded cloud batches useful | Explain the observed characters and distinguish structural constraints from sampling effects | `research/boolean-obstruction-analysis` | `bf_obstructions` |
| S3: c2 supply experiment | Compute-rich cloud agent | Prepare the budget proposal; run one complete family only after approval | `research/boolean-c2-complete` | `bf_harvest` |

**Why this assistant takes S1:** its difficult part is the coupled reasoning:
correct modular carries, Boolean/parity/cardinality semantics, backend limits,
oracle agreement, non-leaking controls and honest outcome interpretation.
A large working context helps maintain those invariants across the model,
solver, verifier and reports. I also own integration and cross-track review.
More context or financial headroom is not permission for unbounded process
memory or computation.

The cloud agents receive narrow, self-contained objectives. S2 can begin
from existing artifacts independently of S1. S3 can prepare its proposal
immediately, but its larger run remains blocked on approval. Once S1's
interface is frozen, an independent cloud worker can also execute a bounded
holdout-validation batch; that is a follow-up, not a prerequisite for S1.

Each worker starts from the baseline above or the same coordinator-reviewed
planning commit descended from it, and records its exact starting SHA.
Use separate branches and worktrees/clones; never switch another agent's
checkout. Do not start from another worker's unfinished branch.

For each owned prefix `bf_name`, the worker may add only:

- `code/bf_name.py`
- `code/test_bf_name_correctness.py`
- `data/generated/bf_name.json.gz`
- `doc/bf-name-findings.md` (replace underscores by hyphens)

These are ownership boundaries, not requirements to create unnecessary
files. Shared Python modules, all existing datasets/reports, papers, PDFs,
README and this plan are read-only for workers. Report a minimal reproduction
of any shared defect to the coordinator instead of changing shared APIs.
S1 alone coordinates any justified optional-backend dependency manifest.

### 3. S1: exact Boolean formulation and calibrated solving

Use the actual vectors in [RealInstance](code/real_pool_verify.py), not a
synthetic replacement. For every original component, model:

```text
sum_i a[j,i] * x[i] = t[j] + m[j] * z[j]
x[i] in {0,1}; z[j] integer
sum_i x[i] = 2*h + 1; h integer >= 1
```

Normalize `a[j,i]` and `t[j]` modulo the original `m[j]`. Bound the carry
variables from exact coefficient sums, handle impossible zero rows
explicitly, and check the backend's integer ranges before encoding.
Retain all prime powers: no independent bit slices that discard carries,
and no assumption that overlapping XOR kernel moves have additive residuals.

Execution order:

1. Implement one minimal exact Boolean/integer backend adapter and an
   independently checked model contract. Do not begin a many-backend shootout.
   Prefer existing tools; if a new dependency is needed, record its pinned
   version, license, runtime requirements and isolated installation procedure
   before installation. Do not silently raise the baseline's Python 3.9 floor.
2. Compare the model against exhaustive subset oracles on tiny groups and
   small actual-prime scopes, including satisfiable and infeasible cases,
   heterogeneous powers, parity, minimum size and cardinality edge cases.
3. Reproduce support-3 controls, then tackle the full-483 support-5 controls.
   Declare the development cases/seeds before comparing results. Freeze a
   separate three-seed holdout batch before inspecting its outcomes.
4. First substantive gate: recover all three declared development support-5
   controls and all three held-out support-5 controls within unchanged
   per-call budgets. This small batch is not a statistical reliability claim.
   Freeze the implementation before holdout evaluation; do not tune on it.
5. Extend to supports 9 and 17 only if the first gate passes and the declared
   initial batch budget permits it. Otherwise report the support-5 failure
   boundary rather than increasing budgets until a success appears.

Keep two tasks separate: exact-k recovery may impose `sum(x) = k` when the
experiment declares k; general recovery imposes odd size at least three
without revealing k. Do not report exact-k success as general-search success.
Solver inputs must never include the planted witness, planting RNG state,
or a witness-derived warm start. Solver and planting RNG streams are separate.

Independently verify every returned subset in the original group and
multiplicative residues. Retain the existing stricter counterexample verifier,
including the direct polynomial congruence, for any real-target candidate.
The 93-factor bound is specific to the real full-pool target, not to controls.
Do not spend the initial round attacking that real target before calibration.

**Stop:** if the model disagrees with an oracle, fix that before benchmarking.
If recovery does not improve within the fixed batch and budgets, report that
negative engineering result. Neither a correct formulation nor a timeout
settles the Boolean problem.

### 4. S2: explain the arithmetic obstructions

Use the five serialized instances in [fs_harvest.json.gz](data/generated/fs_harvest.json.gz)
and the pilot anchor. Recheck each character directly against original
generators and target before drawing conclusions.

1. Describe the four new pools' binary characters in arithmetic terms:
   which local components, prime-power blocks or congruence patterns they
   depend on, and how the real target violates them.
2. Compare with the anchor's codimension-one binary quotient constraint,
   whose kernel contains the real target. Separate this observation from
   the unknown exact full subgroup index.
3. Distinguish a constraint forced by a declared harvest family from one
   caused by a capped sample. Prove a family-wide claim, give a counterexample,
   or label it an unproved hypothesis; sample agreement is not a proof.
4. Deliver one justified cheap screening rule or one concrete, falsifiable
   harvest-design hypothesis. Tiny exhaustive examples and bounded probes
   are appropriate; another broad harvest grid is not.

Do not resurrect `N > rows`, positive nullity or a supply ratio as a necessary
or sufficient feasibility theorem. If adding primes changes the ambient
LCMs, rebuild and declare that new group/target; do not compare characters
as if the coordinates were unchanged. Fixed-parent-LCM obstructions must not
be generalized to constructions with selected-subset LCMs.

**Stop:** when no structural explanation has been established within the
declared probes, return the verified characters, counterexamples and remaining
hypotheses. Do not substitute a universal rule for an observed pattern.

### 5. S3: complete c2, subject to a separate budget decision

The existing cell is `fs-c2-wider-minus`: plus bound 547, minus bound 5470,
three distinct minus-side factors, prime-power cap 8192. Its family has
**39,529,340 combinations**. The old with-replacement sample used 5,000,000
draws, finding 253 distinct primes and nine duplicate certified draws.

**Proposed experiment, not yet authorized:** enumerate this one family
completely instead of sampling, with a global accepted-pool cap of 4,096
instead of 1,024. This is approximately 7.9 times the old candidate cap.
The 4,096 cap is a resource ceiling, not a prediction of supply.

Before running, submit the exact configuration, deterministic coverage/shard
scheme, worker count, aggregate CPU/wall/storage limits, process-memory
limits, and separate encoding/verification cost estimates for approval.
More cloud compute does not waive those limits. A large retained pool may
make group construction, not harvesting, the expensive stage.

After approval:

- Preserve the original admissibility tests, exact factorization and prime
  certificates. Never count probable primes as admitted records.
- If parallelizing, use disjoint deterministic combination ranges with a
  coverage manifest and aggregate counters. Parallelism must not multiply
  the candidate budget or turn a global cap into an independent per-shard
  allowance. Deduplicate records before group construction.
- Call the scan complete only with full family coverage and no binding pool
  cap. If any limit binds, publish the actual partial scope and stop reason.
- Verify every admitted prime and exact vector encoding, account for nonunit
  exclusions and parent moduli, then measure the exact assembled group,
  distinct supply, rank/nullity and necessary target checks.
- Apply S2's justified screens and, where budgets permit, first-wave B's
  exact membership checker to the new instance. Do not weaken its frozen-input
  report schema; use a new report with honest provenance.
- Compare completed-family results separately from the old sampled pool.
  Correct per-draw statistics use accepted plus duplicates; distinct discovery
  and group size are separate measurements, not binomial estimates.

**Gate:** if the new target has a verified obstruction, do not spend a solver
budget trying to overcome it. If it passes necessary checks, Boolean
feasibility is still open. No further family expansion follows automatically.

### 6. Shared budgets, outcomes and reproducibility

Unless separately approved, retain one worker process per task, at most
60 seconds enforced wall time per solver call or computational probe, and a
512 MiB working-memory target. Distinguish measured RSS, estimates and
OS-enforced limits; do not describe a target as a hard cap.

For the initial S1 pilot, freeze one configuration and a case list of at most
18 non-oracle solver calls. Record an aggregate budget before running;
no unbounded retries or parameter sweeps. S2 likewise declares a finite probe
list and work caps before computation. The much larger S3 harvest and its
encoding/verification jobs need their own approved limits, not an assumption
that all stages fit in a 60-second solver call.

Every report records baseline/implementation SHAs, normalized source hashes,
input hashes, schema, exact pool ordering and LCM scope, target kind,
support/cardinality mode, seeds, backend/version, thread count and all limits.
Record model-build, solve and verification costs separately and include
startup/build costs in end-to-end comparisons.

Use explicit outcomes: independently verified solution; independently checked
obstruction/proof or completed exact search of a declared scope; unverified
backend-reported infeasibility; inconclusive budget/timeout/resource stop;
and explicit worker/input error. Do not promote an uncertified backend status
to a mathematical proof. Never turn an error, limit or incomplete shard into
a negative existence claim.

### 7. Dependencies, handback and integration

```text
merged baseline + this plan
     |                 |                    |
S1 model/controls   S2 characters      S3 budget proposal
     |                 |                    |
     |                 |             explicit approval
     |                 |                    |
     |                 |             complete c2 or
     |                 |             documented limit
     +-----------------+--------------------+
                       |
           coordinator cross-track checks
                       |
             evidence-based next decision
```

S1 and S2 do not wait for a larger harvest. S3's preparation does not wait
for either, but its execution waits for approval. Testing S1 on a new S3 pool
waits for both a calibrated solver and an independently verified instance.

Each worker returns its branch/start/end SHAs, owned files, test commands and
versions, schemas and hashes, declared budgets, outcome table, independently
checked witnesses, unresolved limitations and one recommendation. State
whether the branch was pushed; push or open a PR only when authorized.

The coordinator integrates on `integration/boolean-feasibility-study`,
reviews scope and mathematical claims, cross-tests the relevant surfaces,
then runs the affected suite on Python 3.9 and a current supported runtime.
Do not weaken existing verifiers, overwrite first-wave artifacts, or merge
worker branches directly into main. A new phase lands through a reviewed PR.

**Immediate priority:** S1 model correctness and support-5 calibration, in
parallel with S2 obstruction analysis. S3 supplies a budgeted proposal first.
No result above is permission to start a production counterexample search.

---

## Historical Plan v2: Constructing a Counterexample to Agrawal's Conjecture

The original roadmap below is retained for provenance. Its dated "next"
actions, passed gates and strategic conclusions are historical, not the
current execution plan.

> **Historical plan; audit update 2026-10-22.** The reduction and solver
> implementations have received correctness repairs. Density definitions and
> benchmark reporting have also changed; the old "closed" gates and "proved"
> labels below are not validated conclusions. For current work, use
> [the audit status](doc/integration-review-status.md#current-correctness-audit-2026-10-22)
> and corrected sources rather than the historical PDFs or no-rerun directives.

*Rewritten 2026-08-07 after Phase 1a calibration. v1 is in git history
(commits 552330e..1925d7e). Supporting documents: doc/working-paper.pdf
(math), data/FINDINGS.md (measurements), doc/twin-smooth-review.md
(literature).*

**Component registry** (all harvesters/solvers/validators as reusable,
combinable options, with status and selection guidance): `doc/registry.md`.

### What we know now (each item measured or proved, see FINDINGS.md)

1. **The reduction stands.** Pool primes p = 2m+1 with m ≡ 1 (mod 40),
   (m, m+1) twin smooth over disjoint side-sets Q₋ | Q₊; subset with odd
   cardinality and product ≡ (1 mod Λ₋, −1 mod Λ₊) ⇒ counterexample
   (working paper Prop 3.1, machinery unit-tested).
2. **The 0.06 invariant.** For partition-agnostic twin supply (sieve, CHM,
   any completeness level, B = 100–547), the best side-partition keeps
   ≈ 0.06 elements per demand-bit — element-greedy and direct
   partition-space search agree. Feasibility needs ≳ 1–3. **The
   dataset-mining route is dead as the primary hunt.**
3. **Partition-first harvesting sidesteps the invariant.** Fix Q₋, Q₊ first;
   enumerate m over Q₋ only; test (m+1)/2 over Q₊ only. Every hit is
   compatible by construction; the cost moves into per-candidate yield,
   which is a local (Dickman-type) probability, not a global combinatorial
   obstruction.
4. **Supply curves are anchored.** N(B) ~ B^5 (published counts 13,374 /
   346,192 / 82M at B = 100/200/547); our closure reproduces the complete
   sets to 99.7–99.98% with exact largest elements; PTE corpus contributes
   0 pool candidates (residue coverage ~40× poorer than generic twins).
5. **Boost obstruction.** 2xⁿ−1 ≡ 3 (mod 16) is unsolvable for all n ≥ 2:
   the mod-80 cell is unreachable by the boost family (working paper
   Prop 6.1). Whether *other* admissible cells exist is open (Question 6.2).

### Track A — partition-first harvester (main line)

**Design.** Asymmetric split. Q₊ = all odd primes ≤ B except 5 (the tested,
density-critical side). Q₋ = a set of t medium primes in (B, B′] (the
enumerated side — enumeration needs no density, only combinatorial volume).
Disjointness is automatic. Enumerate candidates m = ∏_{q∈Q₋} q^{e_q}
(j = Σe_q factors, j ≈ 3–5) restricted to m ≡ 1 (mod 40) and a size window;
per candidate, trial-divide (m+1)/2 over Q₊ (early-abort), then BPSW on
p = 2m+1.

**Back-of-envelope economics at B = 547, B′ = 5000** (to be replaced by A1
measurements): t = 568 medium primes; j = 3 candidates ≈ 3·10⁷ (more with
j = 4 and exponents); per-candidate success ≈ ρ(u)·(1/ln p) ≈ 10⁻³·⁵ at
m ~ 2³⁰–2⁴⁰ ⇒ pool ~ 10⁴. Demand ≈ 12.3t + θ(B)/ln2 + exponent slack ≈
7000 + 800 + slack bits. Ratio ≈ 1.2 — **marginal, which is exactly why A1
measures before A3 commits compute.** Knobs: t, B, B′, j, exponent caps
(reject q^e > 2¹³ on the plus side), size window, and only-count-used-primes
demand accounting.

- **A1. Yield calibration — DONE 2026-08-07, GATE G1 PASSED.** Measured
  ratios up to 44x (B=2003, B'=20030, j=4); j=4, B'/B=10 is the sweet
  spot; details in data/FINDINGS.md. Original spec follows.
  (prototype, python→C). Enumerate ~10⁶ candidates
  across a grid (B ∈ {547, 1000, 2000}, B′/B ∈ {5, 10, 20}, j ∈ {3,4,5},
  m ∈ 2²⁵…2⁴⁵); measure the true yield curve (the ρ_Q analogue with the
  Q₋-exclusion, mod-40 class, and prime-sum filters folded in) and the
  realized demand-bits growth as pool accumulates. Deliverable: yield
  table + fitted model in FINDINGS.md.
  **Gate G1: some regime shows measured pool/demand ≥ 0.5 at prototype
  scale with a fitted extrapolation ≥ 2.5 at production scale.** (The 0.06
  baseline is the number to beat; partition-first must show ≥ ~10×.)
- **A2. Parameter optimization — DONE 2026-08-07, GATE G2 PASSED.** Model
  validated conservative (0.68x) against the complete B=547 corpus; frozen
  spec in doc/harvest-spec.md (Q₊ ≤ 1259, Q₋ ⊂ (1259,12590], j=4): ratio
  13.8, pool ~2.5e5, demand ~18k bits. j=5 deferred to the C harvester.
  Original spec follows.
  **Gate G2: projected pool ≥ 2.5 × demand bits ≥ 3000 usable elements.**
- **A4/A5/A6 STATUS 2026-08-08: solver is the binding constraint; A3 ON HOLD.**
  Chain of findings (doc/a4-solver-analysis.md, data/FINDINGS.md):
   - A4/G3: the group's 2-part is GF(2)-linear and solves at full scale, but is
     only ~16% of demand bits; the ~84% odd part (~15k bits, ℓ up to 6269) is
     an unsolved subset-sum.
   - A5 co-design: constraining both factor bases to odd-smooth-shifted primes
     shrinks the odd support to {24 primes ≤97} while keeping harvest ratio
     ~7.7 (above gate). Caps the odd PRIME, not the odd DIMENSION.
   - A6/G3 re-attempt: NOT passed. Generic solvers (annealing, exact MITM) cap
     2-3 orders of magnitude below the ~24k-bit odd dimension. Dimension is the
     wall; capping it needs near-Fermat primes (too sparse) -> yield/solver
     tension.
  **A7/A8 correction (2026-08-08): the A6 'wall' was a mis-diagnosis.** AGHS
  (arXiv:1203.6664) built a Carmichael number with 10^10 prime factors via a
  SUBEXPONENTIAL omega-guided subset-product reduction over (Z/Lambda)*,
  including the full odd part -- no small-odd-part requirement. So the solver
  is not fundamentally blocked. Two-part next build:
   (i) implement the full AGHS omega-solver (two potentials omega/omega-bar,
       birthday step, non-uniformity) -- a first top-down version
       (code/a8_omega_solver.py) solves only the easy regime (r<=20); the full
       algorithm is a multi-turn build;
   (ii) redesign the harvest to the DIVISOR paradigm -- fix highly-composite
       Lambda-, Lambda+ and harvest twin primes p=2m+1 with m | Lambda-/2 and
       (m+1) | Lambda+/2, so primes are = 1 on many components (the structure
       omega-reduction needs). Re-run A1/A2 economics under this paradigm.
  Hold A3 until the omega-solver passes G3 on divisor-harvested pools.
  **N1 RESULT (2026-08-08, code/a9_divisor_harvest.py): H8 is unharvestable
  under the double condition** -- ~empty pool (0-2 primes) at all feasible
  scales; can't get non-empty AND AGHS-like high density. Our harvestable H7
  pools have ~100x lower identity-density (~0.004) than AGHS (~0.5), so the
  omega-solver is not straightforwardly applicable. STRATEGIC FORK:
   (a) implement the FULL AGHS solver and test directly on low-density H7 pools
       (the one untested escape -- my a8 solver is too weak to settle it);
   (b) find a solver for low-density many-prime pools;
   (c) theory B1/B2/B3 or different r for a friendlier group;
   (d) write up the quantified infeasibility of the L-P route via this solver
       family (a negative result anticipated as publishable from the start).
- **A3. Production harvest.** C implementation (adapt chm_closure.c
  infrastructure; pthreads; ~10⁹–10¹¹ candidates ≈ days of multicore).
  Store elements with full factorizations + deterministic provenance.
- **A4. Subset-product solver.** Pohlig–Hellman DL tables per cyclic
  component (all orders smooth by design); then staged CRT à la
  Löh–Niebuhr — satisfy one prime-power component at a time, maintaining a
  basket of partial solutions, parity (|S| odd) as a Z/2 component; Wagner
  k-list as the fallback for the final hard components; LLL only for a
  terminal low-dimensional correction.
  **Gate G3 (before running on real data): solver succeeds on synthetic
  instances of the same dimensions** (random vectors in the same group,
  planted solution) — separates solver bugs from data infeasibility.
- **A5. Assembly & verification.** Two independent implementations
  (python/sympy and C/GMP or FLINT) re-check: primality of every pᵢ
  (proven, Pocklington/ECPP — the pᵢ are small), conditions (a)–(d),
  direct computation of T(−1, n, 5), n² ≢ 1 (mod 5). Test Popovych's
  (X+2)ⁿ congruence on the find. Write-up either way — a G1/G2 failure
  becomes a quantified-infeasibility section in the working paper.

### Track B — theory (Phase 0, runs parallel to A1–A2)

- **B1. Independent re-derivation of Theorem 2.1** (both k mod 4 cases;
  currently trusted from AIM notes + Váňa). Deliverable: complete proof in
  the working paper appendix. *Everything downstream leans on this.*
- **B2. Admissible local cells (Question 6.2).** Map all (mod 2^k, mod 5)
  patterns — including pool-uniform variants with v₂(p+1) = v > 2 — under
  which the L–P mechanism survives. First test case: p = 2x³−1, x ≡ 2
  (mod 4) ⇒ uniform v₂(p+1) = 4, v₂(p−1) = 1; mod-5 solvable (x ≡ 3).
  **If any boost-reachable cell is admissible ⇒ open Track A′:** harvest at
  x-level (half bit-size, structurally disjoint sides x vs x³−1), which
  should dominate Track A economics — re-plan immediately.
- **B3. General r.** For r with ord_r(p) = 2 the control modulus stays
  p²−1; conditions and residue classes differ by r. Assess whether some
  r ≠ 5 admits denser pools (more congruence classes ⇒ smaller slice
  penalty than 1/16 within mod-40). Low effort, potentially free win.
- **B4. Popovych side-question.** For any pool constructed here, what does
  the (X+2) congruence require? Even partial analysis makes any eventual
  find doubly informative (kills one conjecture or separates two).

### Track C — supporting/supply (opportunistic)

- **C1. Parallel closure runs** (pthreads on chm_closure.c) at B ≈ 250–400:
  denser corpora for validating A1's model out-of-sample, and for
  "partition-vote" analysis (which Q₋ | Q₊ the organic twins prefer — a
  seed for A2's choice).
- **C2. Congruence-targeted PTE sieve.** For a fixed PTE solution, m mod 40
  is a polynomial condition on x: sieving only the right x-classes makes
  every hit land in our congruence class (vs the measured 1/4000). Large
  elements are demand-heavy, so this supplements rather than drives.
- **C4. Lattice twin-finder (MSW, ePrint 2025/1462).** SOTA for *largest*
  twin at bound B (Naehrig's pointer, 2026-08-07). Analyzed in
  doc/twin-smooth-review.md: structurally a poor fit for our harvest — the
  partition is a sign-cone, not a sublattice, so imposing it costs 2^{-omega}
  (the same tax partition-first escapes), and the method is extremal not
  population. Retained only as a possible corpus generator for very large pool
  elements; does not change Track A.
- **C3. Costello/Naehrig outcomes.** The B=547 CHM corpus (or higher-B
  runs, or their cluster infrastructure) upgrades C1 and A2 calibration;
  interest from Sterner et al. could parallelize Track A′/A3. Questions
  already prepared in doc/questions-for-craig-michael.md.

### Decision tree

```
A1 yield measured ──► G1 pass ──► A2 ──► G2 pass ──► A3 ──► A4(G3) ──► A5
     │                   │                  │
     │                   │ fail             │ fail
     ▼                   ▼                  ▼
B2 admissible cell?   raise B/B′, retry A1 once with 10× candidates;
     │ yes            else: write up quantified negative for the
     ▼                mod-80 cell; pivot to B2/B3 outcomes
Track A′ (x-level harvest, half size) — re-run A1 economics there
```

### Risk register (updated)

1. **Yield model wrong (A1 kills it).** ρ(u) with the Q₋-exclusion could
   come in ≥ 10× low. Cost of finding out: ~a day of prototype compute.
   Mitigation: B2/B3 open structurally different pools.
2. **Demand-bits creep.** Λ₋ grows 12–13 bits per medium prime used; if
   solutions need most of Q₋, ratio degrades toward the invariant. A2's
   accounting must charge only used primes and cap exponents.
3. **Solver at 8–15k-bit groups.** Löh–Niebuhr worked at comparable scales
   in 1996; Wagner needs pool ≫ dimension — thin margins mean G3 synthetic
   tests come *before* production harvest finishes.
4. **Theorem risk (B1).** Unchanged: everything relies on secondary
   sources until re-derived.
5. **Prior art.** Unchanged; C3 due diligence continues.

### Immediate next actions (this week)

1. A1 prototype harvester (python, ~200 lines, reuse phase1a machinery);
   first yield grid overnight.
2. B1 re-derivation started in the working paper appendix.
3. C1 pthreads patch to chm_closure.c (small change, big corpus payoff).
