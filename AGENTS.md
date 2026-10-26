# AGENTS.md — onboarding for agents working in this repository

This file orients an agent picking up work here. Read it before editing.
The first-wave study is on `main`; the declared S1/S2/S3 Boolean Feasibility
Study is reviewed and combined on `integration/boolean-feasibility-study`.
The current coordinator gate is its landing on `main`, not another run.
Read the [study summary](README.md#boolean-feasibility-study-reviewed-integration)
and current [PLAN.md](PLAN.md); its archived assignments and budgets are
history, not renewed execution instructions. This file is a map and a set
of house rules, not a research claim.

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

- **Boolean Feasibility Study - reviewed integration.** S1, S2 and S3 are
  combined through [PR #10](https://github.com/shumow/PRIMES-Conjectures/pull/10).
  The [README summary](README.md#boolean-feasibility-study-reviewed-integration)
  links all current findings, including preserved negative results.
  The combined 254-test suite passed on Python 3.9.13 and 3.14.5 with the
  optional native backend and no skips; the baseline remains stdlib-only.
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
  not nearness to the real target. The completed 2,234-prime c2 target needs
  **at least 191 factors**. Neither bound applies to planted control targets.
- **Both real targets are integer subgroup members, but Boolean-unresolved.**
  The anchor and complete c2 subgroups have **exact index two**, certified
  using the [split-C2 saturation argument](doc/bf-solver-preprocessing-findings.md)
  and every primary quotient, not inferred from binary codimension alone.
  Membership is neither a Boolean subset nor a counterexample.
- **The support-blind pilot stops at selected size 17.** It cannot reach the
  real targets above. Its six holdouts are now observed, not fresh data for
  later tuning. The [frozen rounds](doc/bf-solver-information-sets-findings.md)
  consumed 30 S1 full-pool calls; no further trial is authorized by that record.
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

- The reviewed study is assembled on `integration/boolean-feasibility-study`;
  its landing on `main` proceeds through a coordinator PR. Original planning,
  worker branches and exact baselines are retained in the archived study brief
  in `PLAN.md`. Earlier `research/feasibility-*`
  and `research/harvest-solver-feasibility` branches belong to the first wave.
- Commit subject: short imperative; body explains *why* and records
  commits/SHAs, tests run, and provenance for data changes.
- **Attribution trailers:** follow the active environment's attribution
  requirements. Do not hardcode a model identity or require a provider-specific
  session tool in this cross-agent repository.
- Do **not** open a PR, push to a shared branch, or merge to `main` without
  explicit authorization from the user/coordinator.

## 7. Current coordinator gate: land the reviewed study

The declared S1/S2/S3 scopes are complete. Use the current [closeout plan](PLAN.md)
for documentation and the history-preserving PR to `main`; verify live branch
ancestry rather than repeat a landing already performed.

Old assignments, unused gated cases and prior approvals do not authorize a
new run. Further controls, replication, wider support, another harvest or a
real-target search need a separately declared scope and explicit approval.
Preserve the original reports and source hashes; verify saved artifacts
instead of regenerating them.

No single metric or failed solver settles either conjecture.

## 8. Fast orientation checklist for a new agent

1. Read the current section of `PLAN.md`, then the README's
   [reviewed study summary](README.md#boolean-feasibility-study-reviewed-integration).
   The archived study brief, old roadmap and first-wave plan are provenance,
   not competing assignments.
2. Follow the current findings linked there. Use `doc/registry.md` for
   historical component vocabulary and `doc/fs-*-findings.md` for the
   preserved first-wave baseline.
3. For theory, read the correctness audit before dated AG findings, then the
   corrected `.tex` sources or separately rebuilt audit PDFs.
4. For code changes, run the relevant tests. The combined baseline command is
   `python -B -m unittest discover -s code -p "*correctness.py" -v`.
5. Verify saved artifacts independently; do not rerun their pilots. For example:
   ```powershell
   python -B code\bf_solver_information_sets.py --verify data\generated\bf_solver_information_sets.json.gz
   ```
