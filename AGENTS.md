# AGENTS.md — onboarding for agents working in this repository

This file orients an agent picking up work here. Read it before editing.
The first-wave harvest-and-solver feasibility study was integrated in PR #6.
For current assignments and budgets, use the current section of
[PLAN.md](PLAN.md); its preserved historical roadmap is not an execution
instruction. This file is a map and a set of house rules, not a research claim.

---

## 1. What this project is

Two coupled efforts around **Agrawal's conjecture** (if `r` is prime,
`r ∤ n`, and `(X−1)^n ≡ X^n−1 (mod n, X^r−1)`, then `n` is prime or
`n² ≡ 1 (mod r)`) and **Popovych's** two-section strengthening:

1. **Constructive / experimental** (`PLAN.md`): try to *construct* a
   Lenstra–Pomerance (L–P) counterexample — a squarefree `n` whose prime
   factors satisfy `p−1 | n−1` and `p+1 | n+1` (a *Williams number*) plus
   local conditions — as a two-stage pipeline: **harvest** a pool of
   twin-smooth pool primes, then **solve** a two-sided `0/1` subset-product
   in `G = (Z/Λ₋)* × (Z/Λ₊)*`.
2. **Arithmetic-geometric / theoretical** (`doc/arith-geom.tex`): study
   Frobenius-matching constructions and their arithmetic constraints.
   The audited sources distinguish proved identities, conditional comparisons
   and unproved extensions; they do not turn the experimental solver walls
   into general impossibility theorems.

Neither effort establishes a counterexample in any current pool or global
infeasibility. The verified baseline consists of reproducible experiments,
independent certificates and scoped mathematical statements. Consult the
[correctness audit](doc/integration-review-status.md#current-correctness-audit-2026-10-22)
before treating dated findings or historical PDFs as current conclusions.

## 2. Current state (what is done)

- **Feasibility study, first wave — merged.** Three tracks on `main`:
  - **A (solver controls)** `code/fs_controls.py`, `doc/fs-controls-findings.md`
  - **B (exact reachability)** `code/fs_reachability.py`, `doc/fs-reachability-findings.md`
  - **C (harvest designs)** `code/fs_harvest.py`, `doc/fs-harvest-findings.md`
  - Coordinator plan: `doc/harvest-solver-feasibility-plan.md`
  - Frozen input pilot: `data/generated/real_pool_pilot.json.gz`
    (sha256 `008cf08ce3f0d3a2…`), built by `code/real_pool_pilot.py`,
    checked by `code/real_pool_verify.py`.
- **Arithmetic-geometric track — audited, provisional.** Current statements
  are in the corrected `.tex` sources and separately rebuilt
  [audit PDFs](README.md#current-audit-papers-provisional). The dated
  `doc/arith-geom-findings.md` and `doc/arith-geom-plan.md` are historical
  context, not certification of the broader claims they describe.
- **Historical negative-result writing plan**:
  `doc/negative-result-plan.md`. It explicitly says the separate paper branch
  is not part of this checkout; do not assume its proposed paper/PDF is on
  main or its old infeasibility conclusions are validated.
- **Component registry** `doc/registry.md` — the H1–H8 harvesters, S1–S7
  solvers, V* validators. These component IDs are distinct from the new
  study's S1/S2/S3 work-track labels; historical registry statuses need the
  same audit qualifications.

## 3. Load-bearing facts — do not silently re-derive these wrong

- **The real full-483 fixed-LCM target needs ≥ 93 factors.** Exact integers give
  `P₉₁ < Λ₋+1 ≤ P₉₂` (product of largest eligible primes), and odd
  cardinality forces ≥ 93. Small-support control recovery is *calibration*,
  not nearness to the real target.
- **The real 483 target is a subgroup *member*** (Track B, integer witness)
  **but Boolean-unresolved**; the generated subgroup is *proper* (index ≥ 2,
  codim 1 in `G / 2G`). Membership alone does not establish Boolean feasibility;
  the quotient ranks do not determine the exact full subgroup index.
- **Historical density/solver barriers are not universal theorems.**
  The 0.06 corpus measurements and N1/A10 diagnostics do not prove that
  mining or an algorithm family cannot work. Forced-zero mixture weights,
  literal identity frequencies and side-support counts are different
  statistics; in particular, the old `0.004` comparison is not a measured
  literal H7 identity density. See the audit and corrected first-wave reports.
- **The geometric extensions remain qualified** (`doc/arith-geom.tex`).
  The audited stabilizer statement is a cofactor upper bound; its index
  comparison depends on a chosen exception model. General unique-optimum,
  elliptic impossibility and function-field sharpness claims are not proved.

## 4. House rules (these are why the work is trustworthy — keep them)

1. **Verification independence.** A checker must never call the algorithm
   that produced the thing it checks, nor trust its success flag. Pattern:
   `verify_*` functions re-derive from first principles (group equations,
   separating characters, direct polynomial congruence). Tests assert this
   by patching the solver to raise (see
   `test_fs_reachability_correctness.py`). Preserve it.
2. **Scope discipline / honest status vocabulary.** Distinguish, always:
   `solution` (independently verified) · `proved_no_solution` (certificate
   or completed exact scope) · `resource_limit` / `inconclusive_budget` /
   `timeout` (all **inconclusive**, never "impossible"). A planted control
   solved is not a counterexample. A negative over full-pool LCMs does not
   generalize to selected-subset LCMs. "Member" ≠ "Boolean subset" ≠
   "counterexample". State the hypotheses and scope of each structural
   claim; a restriction on a Frobenius-matching construction is not an
   obstruction to every way the polynomial congruence could hold.
3. **No production search / no budget escalation without explicit
   authorization.** Declare budgets before a run; never raise them to force
   a    result. Bounded by default; the current `PLAN.md` governs the new study.
   Recording a larger experiment in a plan is not authorization to run it.
4. **Provenance on every generated artifact.** Record source SHA256s (LF-
   normalized), input artifact SHA256, interpreter version, seeds, budgets,
   and per-case outcomes. Do not overwrite or weaken a frozen dataset or its
   verifier to fit a new experiment — use a new schema/report with its own
   provenance.
5. **Reproducibility.** Deterministic, seeded. The audit/pilot baseline uses
   Python **3.9+ and the standard library**; some separate AG scripts use
   SymPy. No new dependencies without coordinator sign-off, and no silent
   increase of the baseline's Python floor. Enforced wall clocks
   use the portable process **watchdog** in `fs_controls.py`
   (`run_limited`), not `signal.SIGALRM` — it must work on Windows too.
6. **Tests are unittest-discoverable:**
   `python -m unittest discover -s code -p "*correctness.py"`.
   Keep new tests `unittest.TestCase`-based so a combined suite can't skip
   them. Documentation-only edits need no code-suite run unless documentation
   tests apply. For current paper builds, follow the
   [README's Tectonic instructions](README.md#current-audit-papers-provisional)
   and keep rebuilt audit PDFs separate from historical PDFs.

## 5. Parallel-work discipline (if several agents run at once)

- One track per branch; **exclusive file-prefix ownership** from the current
  plan (`bf_solver`, `bf_obstructions`, `bf_harvest` for the new study;
  `fs_*` identifies the completed first wave). Shared baselines
  (`real_pool_*.py`, the a-series solvers, README, registry, papers) are
  **read-only for workers** — report a needed shared change to the
  coordinator instead of editing it in a worker branch.
- Use separate clones or `git worktree`. **Never switch branches inside a
  checkout another agent is using.** Start each worker from a recorded
  baseline SHA, never from another worker's unfinished branch.
- Only the coordinator merges to `main` / opens integration PRs.

## 6. Git / attribution conventions

- The new study integrates on `integration/boolean-feasibility-study`.
  Planning is on `research/boolean-feasibility-plan`; worker branches and
  exact baselines are recorded in `PLAN.md`. Earlier `research/feasibility-*`
  and `research/harvest-solver-feasibility` branches belong to the first wave.
- Commit subject: short imperative; body explains *why* and records
  commits/SHAs, tests run, and provenance for data changes.
- **Attribution trailers:** follow the active environment's attribution
  requirements. Do not hardcode a model identity or require a provider-specific
  session tool in this cross-agent repository.
- Do **not** open a PR, push to a shared branch, or merge to `main` without
  explicit authorization from the user/coordinator.

## 7. Next phase: Boolean Feasibility Study

The combined first-wave summary is in README. The new plan assigns:

1. **S1 — exact Boolean model and calibration**, owned by the large-context
   coordinator. Preserve modular carries, parity and independent verification;
   validate tiny oracles, then support-3 and support-5 controls, including
   held-out seeds. Supports 9/17 are later milestones, not a near-target search.
2. **S2 — arithmetic obstruction analysis**, suitable for an independent
   agent using existing artifacts and bounded probes. Separate family-wide
   proofs from capped-pool patterns; do not assume a geometric explanation
   before establishing one.
3. **S3 — c2 supply proposal**, suitable for a compute-rich cloud agent.
   The proposed complete 39,529,340-combination scan and higher pool cap
   require separate budget approval before execution.

Read the current plan for ownership, dependencies, exact limits and stop
conditions. No implementation or experiment is authorized merely by this map.

No single metric or failed solver settles either conjecture.

## 8. Fast orientation checklist for a new agent

1. Read the current section of `PLAN.md`, then the README's combined
   feasibility summary. The old roadmap and first-wave plan are provenance,
   not competing assignments.
2. Skim `doc/registry.md` for the component vocabulary, and the three
   `doc/fs-*-findings.md` for the merged results.
3. For theory, read the correctness audit before dated AG findings, then the
   corrected `.tex` sources or separately rebuilt audit PDFs.
4. For code changes, run the relevant tests. The combined baseline command is
   `python -B -m unittest discover -s code -p "*correctness.py" -v`.
5. Verify a saved artifact independently, e.g.
   `python -B code/fs_reachability.py --verify data/generated/fs_reachability.json.gz`.
