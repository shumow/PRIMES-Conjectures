# Harvest-and-solver feasibility: plan and parallel agent assignments

**Recorded:** 2026-10-23

**Starting main commit:** `0fea665ffdd36a1c7380078901f424a032bf8b93`

**Planning branch:** `research/harvest-solver-feasibility-plan`

**Purpose:** determine whether the next bottleneck is supply, target
reachability, or algorithms, using verified actual-prime instances.
This document authorizes no production-scale search and makes no claim that
a counterexample exists within any current pool.

## 1. What we have, and why we are not simply scaling the last search

[PR #3](https://github.com/shumow/PRIMES-Conjectures/pull/3) merged the
[actual-prime pilot](real-pool-pilot.md), its
[dataset](../data/generated/real_pool_pilot.json.gz), and an independent
arithmetic verifier. Its implementation commit is
`6494f89641a8dad6367fbaca8116b1bb08c1bc09`.

| Cohort | Certified primes | Group bits | Binary projection | Real fixed target |
|---|---:|---:|---|---|
| Complete small family | 6 | 231.65 | Rank 6; nullity 0 | Certified character obstruction |
| Seeded medium sample | 94 | 2506.60 | Rank 94; nullity 0 | Certified character obstruction |
| Complete medium family | 483 | 3951.73 | Rank 393; nullity 90 | Passes implemented necessary checks; unresolved |

All 65 bounded tests pass on Python 3.9.13 and 3.14.5. Source-hash provenance,
prime certificates, exact encodings, measured statistics, and recorded
outcomes have independent verification. These are the starting facts, not
evidence of a practical counterexample.

The full 483-prime searches failed on both the real target and a known
feasible planted control. That makes their negative search outcomes
inconclusive. Also, 483 Boolean variables against approximately 3,952 group
bits is severely undersupplied under a uniform-subset-sum heuristic.
That heuristic is not a proof about this structured target.

We should use this pool as a diagnostic benchmark, not make exhaustive
resolution of its real target the main goal.

## 2. Four-step execution plan

1. **Calibrate algorithms on known feasible real-vector controls.**
   Distinguish easy small-support recovery from difficult residual search,
   and establish a regime where a solver reliably finds known solutions.
2. **Strengthen target diagnostics.**
   Extend prime-field quotient checks to exact generated-subgroup membership,
   including full prime-power constraints where computationally practical.
3. **Compare better-supplied harvest designs.**
   Measure distinct certified supply, the exact assembled group and target
   obstructions together, rather than extrapolating from hit counts alone.
4. **Integrate the evidence and choose the next investment.**
   Decide between algorithm work, harvest redesign, arithmetic investigation,
   or a separately authorized larger search.

Steps 1-3 can start **in parallel** from the same frozen baseline.
Step 4 depends on their results. Applying the improved diagnostics and solvers
to newly generated pools is a second-wave integration task, not a prerequisite
for the first three agents to make progress.

## 3. Parallel work map

| Track | Owner's objective | Branch | Exclusively owned file prefix |
|---|---|---|---|
| A: solver controls | Establish interpretable algorithm baselines | `research/feasibility-solver-controls` | `fs_controls` |
| B: exact reachability | Prove generated-subgroup membership or obstruction | `research/feasibility-exact-reachability` | `fs_reachability` |
| C: harvest designs | Improve verified supply relative to the exact group | `research/feasibility-harvest-designs` | `fs_harvest` |
| Coordinator | Shared contracts, integration, cross-track validation | `research/harvest-solver-feasibility` | Shared files and integration report |

Start each worker from this planning commit, or from its recorded starting
main commit with this plan supplied separately. Record the exact starting SHA.
Do not start one worker from another worker's unfinished branch.

Use separate clones or Git worktrees. **Never switch branches inside a
checkout another agent is using.** Independent working directories prevent
accidental edits, staging, cache cleanup, or output replacement across agents.

### File ownership

Worker A may add:

- `code/fs_controls.py`
- `code/test_fs_controls_correctness.py`
- `data/generated/fs_controls.json.gz`
- `doc/fs-controls-findings.md`

Worker B may add:

- `code/fs_reachability.py`
- `code/test_fs_reachability_correctness.py`
- `data/generated/fs_reachability.json.gz`
- `doc/fs-reachability-findings.md`

Worker C may add:

- `code/fs_harvest.py`
- `code/test_fs_harvest_correctness.py`
- `data/generated/fs_harvest.json.gz`
- `doc/fs-harvest-findings.md`

Create only files needed for the result; these are ownership boundaries,
not a requirement to manufacture every artifact.

Shared baseline implementations, the existing pilot dataset, README,
registry, review-status document, papers, and PDFs are **read-only for workers**.
If a shared bug or missing interface blocks progress, report the smallest
reproduction to the coordinator. Do not have three agents edit the same core
module or independently introduce incompatible helpers.

The coordinator owns any justified shared changes and reruns affected tests.
No worker merges into main or rewrites another branch.

## 4. Shared scientific and data contract

All tracks must use the same distinctions:

- **Real target:** `(1 mod Lambda_minus, -1 mod Lambda_plus)`, with the exact
  declared LCM scope. Odd cardinality and at least three distinct factors.
- **Planted target:** separately identified target constructed from a known
  subset of real vectors. A planted solution is not a counterexample.
- **Generated-subgroup membership:** permits arbitrary integer coefficients.
  It is necessary, not sufficient, for a Boolean subset solution.
- **Selected-subset divisibility:** weaker than imposing LCMs from the entire
  parent pool. A negative full-pool result must not be generalized to all
  selected-subset constructions.
- **Literal identity frequency:** measured zero coordinates in the exact group.
  Factorization-forced zeros, forced-zero mixture parameters and sign-split
  support counts are separate quantities.
- **Negative search result:** budget exhaustion, timeout, and size/memory limits
  are inconclusive. Nonexistence requires a valid obstruction or a completed
  exact search of the explicitly stated scope.

Use the baseline structures and interfaces where appropriate:

- [PrimeRecord and RealInstance](../code/real_pool_verify.py)
- [HarvestConfig, harvest, build_instance and measure_structure](../code/real_pool_pilot.py)
- [verify_prime, verify_encoding, verify_group_solution and verify_obstruction](../code/real_pool_verify.py)
- [A4 and its explicit minimum-size option](../code/a4_solver.py)
- [A6 local and direct-MITM solvers](../code/a6_oddsolver.py)

Preserve the independence of verification: verification must not call the
algorithm that produced the claimed certificate or trust its success flag.
Every candidate counterexample must pass the existing arithmetic conditions
and an independent direct polynomial-congruence check.

The baseline saved-report verifier intentionally accepts one strict schema
and a fixed source-provenance set. **Do not weaken it or overwrite its dataset
to accommodate new experiments.** Use track-specific reports with their own
provenance and independent checks. A new harvest family outside the original
schema needs an accurately described new format, not a misleading v1 label.

Every experimental result should record:

1. Baseline and implementation commit, normalized source SHA256s, input
   artifact SHA256, interpreter and dependency versions.
2. Exact pool/cohort, ordering, component orders and target, including whether
   the parent moduli were retained or recomputed.
3. Seed, target kind, control support size, algorithm and all budgets.
4. Outcome classification, elapsed time, work counters, observed/estimated
   memory, and whether limits were actually enforced.
5. Witness/certificate and independent verification outcome when applicable.

## 5. Track A: solver calibration

**Question:** which algorithms can solve known feasible subsets of these
actual vectors, in what support-size and resource regimes?

### Work

1. Load and independently verify the frozen pilot. Keep its real target
   unchanged and use its small prefixes for exact-oracle checks.
2. Generate separately labeled seeded controls of support 3, 5, 9 and 17
   where the pool is large enough. Store the witness outside solver inputs;
   a solver must not receive the hidden indices or regenerate them from the
   planting seed.
3. Include at least one small-support baseline, such as a correctly bounded
   three-sum/meet-in-the-middle method. Recovering a three-prime control is
   useful but must not be sold as solving a general large-support problem.
4. Compare the existing corrected A4/A6 methods with that baseline. Add a
   further method only if it fits the budgets and has independent tiny-instance
   tests. No need to implement every algorithmic family.
5. Report success rates over multiple declared seeds, support sizes, binary
   rank/nullity, residual size and resource usage. Unique binary controls
   should be identified as relatively easy consistency checks.

### Acceptance and stop

- Verify every returned subset in the original multiplicative residues,
  with odd size at least three.
- Exhaustive small instances must agree with an independent oracle.
- Deliver a calibration table, including failures on known feasible controls.
- If no method recovers nontrivial controls under the initial budget, report
  that precisely. Do not label the real target impossible or automatically
  increase the budget.

**Ready-to-use assignment:** implement Track A on its isolated branch, touching
only the A-owned files above. Start from the frozen pilot; deliver tested
solver-control comparisons and a short findings report. Stop at the declared
budgets and hand back commit SHAs. Do not edit the baseline solvers or dataset.

## 6. Track B: exact reachability diagnostics

**Question:** does the target lie in the subgroup generated by the pool
vectors, beyond the current coordinate and prime-field quotient checks?

### Work

1. Implement a bounded exact method for mixed prime-power components:
   appropriate integer-lattice normal forms or finite-module methods are
   candidates. Do not treat higher powers as independent field equations.
2. Start with exhaustive small generated subgroups. A useful missed-obstruction
   fixture is:

   ```text
   G = Z/4 x Z/4
   generators = {(1,1)}
   target = (0,2)
   ```

   Coordinate checks and reduction modulo 2 pass, but the target is not in
   the diagonal subgroup. The character `a-b mod4` certifies the obstruction.
3. For a positive membership result, return integer coefficients expressing
   the target in the original group. Independent verification must multiply/
   add those coefficients in the original component orders.
4. For a negative result, return a separating character or another
   independently checkable exact certificate. Existing `verify_obstruction`
   supports finite-modulus character witnesses.
5. Apply to the frozen small, sampled-medium and full-medium real targets,
   plus known feasible controls, within the limits.

### Acceptance and stop

- Tiny exhaustive subgroup oracles must agree with the implementation.
- Do not confuse integer coefficients with a Boolean subset.
- A full 483-prime membership result is desirable, not required: a correct
  bounded implementation and an explicit unresolved/resource-limit result
  are acceptable.
- Normal-form size growth, memory exhaustion or timeout must remain
  inconclusive, not be converted into a mathematical obstruction.

**Ready-to-use assignment:** implement Track B on its isolated branch, touching
only B-owned files. Deliver independent positive/negative certificates,
small-oracle tests, and bounded results on the frozen pilot. Do not alter the
baseline necessary checks or promote membership to Boolean feasibility.

## 7. Track C: harvest-design comparison

**Question:** can we materially improve distinct verified supply relative
to the exact assembled group, without introducing a target obstruction?

### Work

1. Establish the existing three-factor family as a reproducibility anchor.
2. Choose a small declared grid comparing three versus four minus-side
   factors and alternative disjoint factor-base allocations. Explain the
   choices before interpreting results.
3. A controlled prime-power variant is optional. If added, retain exact
   exponents, primality certificates, unit filtering and all group factors.
   Do not claim it fits the original squarefree-family schema.
4. For each cell record candidate family size, sampling distribution,
   distinct counts, duplicates, complete/capped status, verification failures,
   generation cost, exact modulus/group sizes, rank/nullity, literal versus
   forced identities and existing necessary target checks.
5. Compare actual `N / log2(|G|)` and changes in both numerator and denominator.
   Avoid "improvements" obtained by dropping constraints or changing the target
   without saying so.
6. If extrapolating supply from samples, state assumptions and uncertainty.
   A confidence interval for per-draw hit rate is not automatically an
   interval for distinct-prime count, exact group size or target feasibility.
   Zero observed hits must not become an asserted zero population.

### Acceptance and stop

- Every admitted prime must have an independently checked certificate and
  complete side factorizations.
- Verify exact encodings and original residues for every retained vector.
- Classify projections separately from completed harvests.
- Deliver a modest comparison table, not a production harvest. A disappointing
  table is valid evidence; do not silently expand to a large search.
- A ratio above one is a useful heuristic supply milestone, not an existence
  theorem or solver-performance guarantee.

**Ready-to-use assignment:** implement Track C on its isolated branch, touching
only C-owned files. Reuse the verified baseline interfaces where they fit;
produce a few bounded actual-family comparisons and independently checked
new artifacts. No legacy-output replacement or unannounced extrapolation.

## 8. Resource and dependency coordination

Suggested conservative starting limits, to be recorded before any run:

- One worker process per agent; no unbounded nested parallelism.
- At most 60 seconds wall time per individual solver experiment and a
  512 MiB working-memory target. Distinguish measured limits from estimates.
- At most 5,000,000 candidate draws/enumerated combinations per harvest cell,
  with an explicit accepted-pool cap no higher than 1,024.
- Choose at most four new harvest cells initially; test and sample small
  before building their full encoded pools.
- Stop and seek authorization before increasing these limits. On shared
  hardware the coordinator may reduce concurrency or caps.

Prefer the standard-library baseline first. If a normal-form/solver library
is genuinely needed, record the reason, version, environment and license;
do not have multiple workers edit a shared dependency manifest. Coordinate a
minimal isolated dependency change rather than modifying global environments.

The three tracks have independent first-wave outputs:

```text
                frozen pilot + this plan
                   /       |       \
          A: controls  B: membership  C: harvests
                   \       |       /
              coordinator integration
                        |
       cross-test A/B on selected C pools
                        |
             evidence-based next decision
```

A and B do not wait for new harvests. C can start with the existing necessary
checks while B develops stronger ones. After first-wave review, test the new
algorithms and diagnostics on selected new pools without redoing the entire
parameter sweep.

## 9. Coordinator integration and decision gates

The coordinator:

1. Confirms each branch's baseline, diff scope, tests and recorded budgets.
2. Integrates disjoint worker commits without rewriting source history.
3. Verifies shared APIs, Python compatibility, provenance and independent
   witness checking. A clean textual merge is not validation.
4. Runs targeted cross-track checks before the complete regression suite.
5. Updates shared README/status and writes one integrated feasibility summary.
6. Preserves the original pilot dataset, research log, PDFs and earlier outputs.

The next investment follows the evidence:

| Observation | Recommended investment |
|---|---|
| Better supply and no certified obstruction, but poor control recovery | Algorithm development |
| Poor supply relative to exact group size across the bounded designs | Harvest or construction redesign |
| Persistent certified target obstructions | Analyze their arithmetic origin and target/model scope |
| Verified suitable pools and competent control recovery | Propose a separately budgeted larger search |

No single positive metric or failed solver settles either conjecture.

## 10. Worker handback checklist

Each agent returns:

- Branch and exact starting/ending commit SHAs.
- Files changed, tests run, interpreter/dependency versions.
- Input hashes, seeds, target definitions and complete resource limits.
- Results table separating real targets, feasible controls, projections,
  exact obstructions, completed exact searches and inconclusive outcomes.
- Independently checked witnesses and reproduction commands.
- Shared bugs/interfaces requiring coordinator action.
- One concrete recommendation, with uncertainty and stop conditions.

Do not merge into main, overwrite historical artifacts, run production
searches, or claim a counterexample without independent verification.
Record whether the branch was pushed; push or open a PR only when authorized.
