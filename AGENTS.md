# AGENTS.md — onboarding for agents working in this repository

This file orients an agent picking up work here. Read it before editing.
It reflects `main` as of the PR #6 merge (first-wave harvest-and-solver
feasibility study integrated). It is a map and a set of house rules, not a
research claim.

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
2. **Arithmetic-geometric / theoretical** (`doc/arith-geom.tex`): reframe
   the conjecture as a Frobenius-lift test on `μ_r`, which turned the
   empirical walls into theorems and produced the negative-result paper.

Neither effort claims a counterexample exists in any current pool. Most of
the value to date is **quantified infeasibility** and structure, not a hunt.

## 2. Current state (what is done)

- **Feasibility study, first wave — merged.** Three tracks on `main`:
  - **A (solver controls)** `code/fs_controls.py`, `doc/fs-controls-findings.md`
  - **B (exact reachability)** `code/fs_reachability.py`, `doc/fs-reachability-findings.md`
  - **C (harvest designs)** `code/fs_harvest.py`, `doc/fs-harvest-findings.md`
  - Coordinator plan: `doc/harvest-solver-feasibility-plan.md`
  - Frozen input pilot: `data/generated/real_pool_pilot.json.gz`
    (sha256 `008cf08ce3f0d3a2…`), built by `code/real_pool_pilot.py`,
    checked by `code/real_pool_verify.py`.
- **Arithmetic-geometric track — complete** (`doc/arith-geom.tex` v1.0,
  `doc/arith-geom-findings.md`, `doc/arith-geom-plan.md`,
  `doc/arith-geom-memo.pdf`, `doc/popovych-note.tex`). Verifier scripts
  `code/ag{2,3,4,5,5b}_*.py`.
- **Negative-result paper** (`doc/negative-result.tex` → PDF), plan in
  `doc/negative-result-plan.md`.
- **Component registry** `doc/registry.md` — the H1–H8 harvesters, S1–S7
  solvers, V* validators. Use its ids as vocabulary.

## 3. Load-bearing facts — do not silently re-derive these wrong

- **The real 483-prime target needs ≥ 93 factors.** Exact integers give
  `P₉₁ < Λ₋+1 ≤ P₉₂` (product of largest eligible primes), and odd
  cardinality forces ≥ 93. Small-support control recovery is *calibration*,
  not nearness to the real target.
- **The real 483 target is a subgroup *member*** (Track B, integer witness)
  **but Boolean-unresolved**; the generated subgroup is *proper* (index ≥ 2,
  codim 1 in the GF(2) part). Membership is necessary, never sufficient.
- **The 0.06 mining invariant**: mining any fixed twin corpus keeps ≈ 0.06
  usable elements per demand-bit — dataset mining is dead; partition-first
  harvesting is the supply route.
- **The two-part solver obstruction (N1 + A10)**: high-identity-density
  pools are unharvestable under the double condition, low-density pools are
  unsolvable by the scalable AGHS-class family (`ρ ≳ 0.98` needed vs
  `≈ 0.004` available).
- **The stabilizer-index theorem** (`doc/arith-geom.tex`): any one-section
  Frobenius test on a one-dimensional group has burden
  `[⟨λ⟩ : ⟨λ⟩ ∩ U]`; the twin-smooth double condition is the unique
  minimum for every modulus `r`; Popovych's second section and the
  CM-elliptic analogue are strictly harder. Conditional on one named
  generic-sharpness hypothesis (a theorem in the function-field mirror).

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
   "counterexample". Every structural claim about the conjecture is
   *mechanism-scoped* (Frobenius-matching constructions only).
3. **No production search / no budget escalation without explicit
   authorization.** Declare budgets before a run; never raise them to force
   a result. Bounded by default (the feasibility plan §8 has the caps).
4. **Provenance on every generated artifact.** Record source SHA256s (LF-
   normalized), input artifact SHA256, interpreter version, seeds, budgets,
   and per-case outcomes. Do not overwrite or weaken a frozen dataset or its
   verifier to fit a new experiment — use a new schema/report with its own
   provenance.
5. **Reproducibility.** Deterministic, seeded. Python **standard library
   only** (no new deps without coordinator sign-off). Enforced wall clocks
   use the portable process **watchdog** in `fs_controls.py`
   (`run_limited`), not `signal.SIGALRM` — it must work on Windows too.
6. **Tests are unittest-discoverable:**
   `python -m unittest discover -s code -p "*correctness.py"`.
   Keep new tests `unittest.TestCase`-based so a combined suite can't skip
   them. LaTeX docs compile with `pdflatex` (twice for refs).

## 5. Parallel-work discipline (if several agents run at once)

- One track per branch; **exclusive file-prefix ownership** (`fs_controls*`,
  `fs_reachability*`, `fs_harvest*`, …). Shared baselines
  (`real_pool_*.py`, the a-series solvers, README, registry, papers) are
  **read-only for workers** — report a needed shared change to the
  coordinator instead of editing it in a worker branch.
- Use separate clones or `git worktree`. **Never switch branches inside a
  checkout another agent is using.** Start each worker from a recorded
  baseline SHA, never from another worker's unfinished branch.
- Only the coordinator merges to `main` / opens integration PRs.

## 6. Git / attribution conventions

- Branch names seen here: `research/feasibility-*` (tracks),
  `research/harvest-solver-feasibility` (integration), `arith-geom-*`,
  `negative-result-writeup`, `chore/*`, `docs/*`.
- Commit subject: short imperative; body explains *why* and records
  commits/SHAs, tests run, and provenance for data changes.
- **Attribution trailers:** follow the attribution reminder your session is
  given (it can change). The configured model is `claude-fable-5` but the
  **served model can differ or switch mid-session** — confirm with
  `get_session` (claude-code-remote MCP; report `session_context.model` and
  `external_metadata.last_served_model`) rather than hardcoding a name.
  Never put a model identifier anywhere except chat/commit-trailers.
- Do **not** open a PR or push to a shared branch unless asked; do not merge
  to `main`.

## 7. Candidate next directions (the §9 decision gate is open)

First-wave evidence fires two rows of the plan's decision table. Pick with
the user/coordinator before spending compute:

1. **Algorithm development (the sharpest gap).** A kernel-coordinate /
   bounded-weight MITM solver for **supports 5–17** on the 483 pool.
   Track A recovered support 3 but nothing larger within budget, and the
   target has no certified obstruction. **Must** handle that residuals are
   **not additive under overlapping XOR kernel moves** (the A4-audit
   pitfall; a naive 2⁴⁵ half-split is infeasible). Capability milestone,
   not a near-target search (≥ 93 factors away).
2. **Harvest redesign.** Track C's new designs had *lower* supply/group-bit
   ratios than the anchor. Apply co-design (odd-smooth-shifted factor bases)
   / alternative admissible cells to real-prime harvests; measure against
   the exact assembled group.
3. **Explain the obstructions.** Connect Track B's certified character
   obstructions on the smaller pools to the AG stabilizer / sign-split
   theory — determine whether any harvest can structurally avoid them.
4. **Consolidate.** Write the coordinator's integrated feasibility summary
   and formally record the §9 outcome and what is (not) authorized.

No single metric or failed solver settles either conjecture.

## 8. Fast orientation checklist for a new agent

1. Read `PLAN.md`, then `doc/harvest-solver-feasibility-plan.md` (§4 shared
   contract, §9 decision gate).
2. Skim `doc/registry.md` for the component vocabulary, and the three
   `doc/fs-*-findings.md` for the merged results.
3. For theory, read `doc/arith-geom-findings.md` (dated result log) before
   the full `.tex`.
4. Run `python -m unittest discover -s code -p "*correctness.py"` to confirm
   a green baseline before changing anything.
5. Verify a saved artifact independently, e.g.
   `python code/fs_reachability.py --verify data/generated/fs_reachability.json.gz`.
