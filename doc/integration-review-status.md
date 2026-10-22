# Integration review status

**Prepared:** 2026-10-22
**Branch:** `integration/main-arith-geom-review`
**Purpose:** combine the constructive/experimental track (`main`) and the
arithmetic-geometric track (`arith-geom-interpretation`) into one branch so a
single reviewer can assess both. **This merge is an integration and
review-preparation step only. It is not a correctness review and certifies
nothing.** A clean Git merge is not scientific validation.

## 1. Captured inputs and result

All SHAs were captured after `git fetch origin` on the preparation date and
used explicitly for the merge, so a later fetch cannot silently change the
inputs.

| Ref | Commit |
|---|---|
| `origin/main` tip (first parent) | `37cc491a82e8622808340b371037bfb5e2b35834` |
| `origin/arith-geom-interpretation` tip (second parent) | `9a5bd56400e4be9b0aba09c871b799b2cdfdaee2` |
| Common merge base | `cb7633f20f22f7d340d09437990eae83d3d787a5` |
| Pure merge commit | `98be6455cd5953b59654553f920269f1f278e3f9` |
| Review-readiness commit | *(this document; recorded in the handback)* |

Divergence at these tips: `main` had **1** unique commit (A12, adaptive
cultivation); the geometric branch had **19** (AG2–AG5b scripts/outputs,
writeups, memo, Popovych note, and documentation).

### Deviation from the handoff's pinned tips

The handoff pinned the geometric tip at
`7c6ef97edda75a9f0d88aff707acc6fac0469e57`. On fetch, the live tip had advanced
by one commit to `9a5bd56` ("Clarify the c = 0 exclusion everywhere; memo
section now 'five results'"). Per the handoff's "fetch first / do not reset to
the reviewed commits" instruction, the **current** tip `9a5bd56` was used. That
commit is an exposition-only clarification (the `c = 0` exclusion wording) and
touches only geometric-track documents added by this branch
(`doc/arith-geom-findings.md`, `doc/arith-geom-memo.tex`/`.pdf`,
`doc/arith-geom.tex`/`.pdf`, `doc/popovych-note.tex`/`.pdf`). It changes no
main-track file and does not alter the conflict picture. `main` and the merge
base were unchanged from the handoff.

## 2. The two tracks and retained artifacts

**Constructive / experimental track (`main`).** Literature survey, the working
paper and background document, and the A-series experiments (harvest/solver,
Wagner density, and the A12 adaptive-cultivation experiment). Retained:

- `code/a12_adaptive_cultivation.py`
- `data/FINDINGS.md`
- `doc/option-b-problem.md`, `doc/registry.md`
- Shared historical sources: `doc/working-paper.tex`/`.pdf`,
  `doc/background.tex`/`.pdf`, and the solver prototypes
  `code/a4_solver.py`, `code/a6_oddsolver.py`, `code/a10_wagner_density.py`.

**Arithmetic-geometric track (`arith-geom-interpretation`).** A Frobenius-lift /
torus reading of the conjecture, with deterministic verification scripts and
committed outputs, writeups, a research memo, and a standalone Popovych note.
Retained:

- `code/ag2_torus_check.py`, `code/ag3_hierarchy_check.py`,
  `code/ag4_elliptic_check.py`, `code/ag5_popovych_check.py`,
  `code/ag5b_constant_check.py`
- `data/generated/ag{2,3,4,5,5b}_*.json` (five files)
- `doc/arith-geom-findings.md`, `doc/arith-geom-plan.md`
- `doc/arith-geom.tex` + `.pdf`, `doc/arith-geom-memo.tex` + `.pdf`,
  `doc/popovych-note.tex` + `.pdf`

All retained files were verified **byte-identical** to their respective source
tips (see section 5). No research files, outputs, or papers were deleted,
renamed, or reformatted.

**Both tracks require an independent correctness review.** Nothing here has
been re-derived, re-run, or certified.

## 3. Third-branch boundary (`negative-result-writeup`)

The geometric memo (`doc/arith-geom-memo.tex`) refers to a finished negative-
result paper (v1.1, ~12 pp) living on the separate branch
`negative-result-writeup`. That paper is **not** supplied by this merge and was
**not** imported, cherry-picked, or duplicated. The reference is accurate: the
paper does not exist on `main` or `arith-geom-interpretation`.

- `negative-result-writeup` head at preparation time:
  `6b54f078694901d4fad70062ee8348f3ee3053ec`
  ("Paper: c = 0 exclusion clarified in the constant-c sentence (sec. 5.3)",
  2026-10-22). This is a historical observation, not a reviewed input.
- `doc/negative-result-plan.md` (the execution plan for that separate branch)
  predates the main/geometric split and is present on both merged tracks; it is
  a plan, not the paper.

Do not merge or import that branch without separate user authorization.

## 4. Known review queue (preserved, not repaired)

These observations come from the **preceding review at the handoff's pinned
tips**. They are preserved here so the next reviewer can start cold. They are
**not** instructions that were acted on during integration, and none of the
underlying research was changed. Each should be re-confirmed independently; if a
newer upstream commit already addresses one, record that evidence and its
commit rather than repeating a fix.

Classification used below: **Reproduced defect** (a specific failing case),
**Unsupported inference** (a conclusion stronger than the evidence), **Review
needed** (a broader claim the preceding review did not establish).

### R1. Shared written reduction: incompatible moduli — *reproduced inconsistency*
`doc/working-paper.tex` (subset-product moduli, Prop. 3.1); same in
`doc/background.tex`. The text defines `Lambda_minus = 2*lcm(p-1)` and
`Lambda_plus = 4*lcm(p+1)`. For pool primes `p = 3 mod 80`, both moduli are
divisible by 4, so `n = 1 mod Lambda_minus` and `n = -1 mod Lambda_plus` are
incompatible mod 4; the claim that their gcd is 2 is wrong as written. Likely
intended: `lcm(p-1)` and `lcm(p+1)` (or factors 2/4 applied to the odd parts).
Establish the intended definitions and check their implementation surfaces.

### R2. Main solver: incorrect GF(2) solution construction — *reproduced defect*
`gf2_solve` in `code/a4_solver.py`; corresponding elimination in
`code/a6_oddsolver.py` must also be audited. Minimal cases:
```
gf2_solve([3, 2, 3], [1, 1, 1], 2)  -> bitmask 3; eqs give [0,1,0] != [1,1,1]; correct is 2.
gf2_solve([3, 6], [0, 0], 3)        -> kernel includes 6; eqs at 6 give [1,0] != [0,0]; correct nonzero kernel vector is 7.
```
Missing proper back-substitution affects both the particular solution and the
claimed kernel. Audit every consumer before trusting solver-frontier
measurements.

### R3. Main solver: bit slices are not independent 2-adic constraints — *reproduced defect (independent of R2)*
The "Hensel bit-slices" in `code/a6_oddsolver.py`. An isolated call:
```
comps = [(2, 4)]; orders = [4]; pool = [[1],[1],[0]]; target = [2]
solve(comps, orders, pool, target, 3, random.Random(1), 0.1)  -> (None, "2-part inconsistent")
```
But selecting all three columns is a valid odd-cardinality solution
(`1+1+0 = 2 mod 4`; verifier accepted bitmask 7). The bit-slice equations omit
carries; solving the projection onto `G/2G` over GF(2) is not solving the full
2-primary problem. Review claims about the "solved 2-part" and dependents.

### R4. Main density metric and algorithmic conclusions — *reproduced parameter mismatch + unsupported generalizations*
In `code/a10_wagner_density.py`, `make_pool` produces a zero coordinate with
probability `rho + (1-rho)/ell` (= 0.336 at `rho=0.004, ell=3`, not 0.004;
sample ~0.3365). In `code/a12_adaptive_cultivation.py` the nonzero branch
samples only nonzero values, so its literal zero probability is `rho`. Decide
whether the intended metric is literal identity frequency or a forced-zero
mixture weight; do not compare them as the same parameter. Also revisit
conclusions in `data/FINDINGS.md`, `doc/registry.md`, `doc/option-b-problem.md`:
a fixed four-element birthday search does not exclude general subset-product
algorithms or the full AGHS method; one greedy adaptive strategy does not
exclude all adaptive construction; finite squarefree-divisor harvest trials do
not prove unharvestability; greedy coloring does not upper-bound the optimal
coloring; `2**N >> |G|` guarantees collisions, not reachability of a specified
(odd-cardinality) target. Preserve the measured observations; do not carry
"closed," "proves," or "existence is free" as verified.

### R5. Geometric dictionary: fixed-r primality equivalence — *definite counterexample to the stated equivalence (not to Agrawal)*
`doc/arith-geom.tex` (Frobenius-lift dictionary) and the memo. The claimed
equivalence between primality and the full lift condition in the fixed
truncated algebra fails for `n = 399001 = 31*61*211`, `r = 5`: each factor is
1 mod 5, each `p-1 | n-1`, `n = 1 mod 5`; the truncated algebra splits into
copies of the residue fields, and every element satisfies `f(X)^n = f(X^n)`
though `n` is composite. This is inside Agrawal's exception clause — it
challenges the exposition's stronger "iff," not the conjecture. Preserve the
distinction from the valid untruncated polynomial characterization.

### R6. Generic sharpness and the burden bounds — *incorrect group-theoretic equivalence + further proof review*
`doc/arith-geom.tex` (generic-sharpness proposition/proof). Being an `ell`-th
power is not equivalent to having trivial `ell`-part in the order when the group
order contains `ell**2` (e.g. a cube in a cyclic group of order 9 can have order
3). Handle valuations and component dependencies explicitly; the document's
lower bound on `ell` does not itself exclude repeated prime factors. Keep
separate: proved identities/support bounds; hypotheses about generic attainment
and exceptional primes; smoothness/supply heuristics; empirical behavior; any
claimed computational lower bound. Small exception-free samples are sanity
checks, not proofs of the asymptotics.

### R7. Global stabilizers vs. exceptional finite-field reductions — *reproduced counterexample to universal wording*
`doc/arith-geom.tex` (the `X + 2` no-collapse lemma). The characteristic-zero
non-unit argument does not rule out every special reduction. At `r = 13`,
`p = 5`, `e = 2`: `5**2 != 1 mod 13`, yet `(X+2)**24` lies in `mu_26` in
`F_5[X]/Phi_13(X)`; `p = 5` is not excluded by the stated condition involving
`3*(2**13 + 1)`. (This small exception is already recorded by the project.)
Distinguish absence of a universal algebraic collapse identity from absence of
all finite-field accidents.

### R8. Broader extensions and literature checks — *review needed (do not label disproved)*
Audit the CM-elliptic formulation, stabilizer-index generality, exception
clauses, the claimed transfer of the harvest/solver obstruction, and the
function-field appendix's "both heuristics become theorems by Weil" (statements
and parameter regimes). Two reference corrections are already identifiable:

- OEIS A329223 is a nonempty sequence of base-2 pseudoprimes with residue and
  prime-factor conditions, **not** an empty list of simultaneous Carmichael /
  Lucas-Carmichael numbers. (See also `README.md` §2, which describes A329223
  as "numbers both Carmichael and Lucas–Carmichael … no terms known" — this
  characterization needs the same check.)
- arXiv:1710.08674 is Lance Gurney's thesis, *Elliptic curves with complex
  multiplication and Lambda-structures*, **not** the joint Borger–Gurney item
  described in the bibliography.

Verify precise theorem statements and novelty claims against primary sources.

## 5. What was checked mechanically (and what was not)

Checked during this integration:

- Preflight: clean worktree, correct `origin`, no merge/rebase in progress.
- Captured all SHAs, merge base, and divergence after `git fetch origin`.
- Exactly one merge conflict, in `.gitignore` only, resolved as the **union**
  of both additions (`data/generated/a12_run.log` from main, `__pycache__/`
  from the geometric branch) plus all pre-existing common rules. No branch's
  copy was taken wholesale.
- Both captured tips are ancestors of the merge commit; first parent = main
  tip, second parent = geometric tip.
- `main..merge` touches only `.gitignore`, `README.md`, and geometric-track
  additions; `ag..merge` touches only `.gitignore` and the main-track files
  (`data/FINDINGS.md`, `doc/option-b-problem.md`, `doc/registry.md`) plus the
  added `code/a12_adaptive_cultivation.py`. No deleted or renamed research
  files.
- Every retained file listed in section 2 is byte-identical to its source tip
  (`git diff --quiet` against the captured tip).
- No conflict markers (`git diff --check`, cached and worktree).

**Not** done (out of scope for this preparation task): no mathematical
arguments were checked or fixed; no solver was repaired; no PDF was rebuilt; no
script was run or re-run; no output JSON was regenerated; no formatting or
line-ending normalization. The R1–R8 queue above was **not** acted on.

### Data-access gaps

Some large-corpus measurements in the constructive track depend on private data
not committed to the repository. Those experiments were **not** reproduced here,
and nothing about them was independently verified. Do not upload private data or
substitute invented measurements; record precisely which reproductions require
the private corpus.

## 6. Historical labels are preserved, not certified

Historical "all pass," "closed," "proved," "existence is free," and "ready to
circulate" labels in the retained documents are preserved **as written** for
provenance. They are **not** independently validated by this merge. An original
result can be historically important even when later found incorrect; any
correction should be a separate, explicit commit, not a silent rewrite of the
record.

## 7. Starting order for the next correctness review

1. Establish the intended construction and modulus normalization from the
   Lenstra–Pomerance source and the shared working paper (resolves R1).
2. Reproduce R2–R3 with tiny, independently checked cases before interpreting
   any negative solver benchmark.
3. Audit the harvested-vector structure, density definitions, targets, and
   validation harnesses (R4). Separate synthetic experiments from real pools.
4. Reassess the original experimental conclusions with correct algorithms and
   clearly stated finite-resource limits. Rerun expensive work only when the
   corrected small-scale evidence warrants it.
5. Review the arithmetic-geometric proofs statement by statement (R5–R8),
   classifying unconditional results, conditional results, heuristics, and
   unsupported extensions.
6. Reconcile documentation and results only in explicit follow-up commits,
   preserving the provenance of superseded outputs.

### Useful entry points

- `doc/working-paper.tex`, `doc/background.tex`
- `data/FINDINGS.md` (read chronologically through A12)
- `doc/registry.md`, `doc/option-b-problem.md`
- `code/a4_solver.py`, `code/a6_oddsolver.py`,
  `code/a10_wagner_density.py`, `code/a12_adaptive_cultivation.py`
- `doc/arith-geom.tex`, `doc/popovych-note.tex`, `doc/arith-geom-findings.md`
- The AG scripts and their committed JSON outputs

### Primary-source starting links

- Lenstra–Pomerance remarks: <https://aimath.org/WWN/primesinp/articles/html/50a/>
- Popovych's 2009 note: <https://eprint.iacr.org/2009/008>
- AGHS subset-product paper: <https://arxiv.org/html/1203.6664v2>
- Howe's higher-order Carmichael paper: <https://arxiv.org/abs/math/9812089>
- OEIS A329223 definition: <https://oeis.org/A329223/internal>
- Gurney thesis: <https://arxiv.org/abs/1710.08674>

---

*This branch is the starting point for the review, not its conclusion.*
