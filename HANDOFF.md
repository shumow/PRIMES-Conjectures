# Handoff: negative-result write-up branch

*Branch: `claude/negative-result-writeup-8fantb` (the session-designated name;
the plan's suggested name was `negative-result-writeup`). Executes
`doc/negative-result-plan.md`.*

## Delivered

- `doc/negative-result.tex` + `doc/negative-result.pdf` — 14 pages, compiles
  clean with `pdflatex` (3 passes; texlive-latex-base/-recommended suffice).
  Structure follows the plan §2: intro with explicit non-claims,
  construction + reduction (statements reused from `doc/working-paper.tex`),
  supply-solved (§3), solver obstruction (§4), scope/caveats (§5), reusable
  contributions (§6), data-table appendix A, reproducibility appendix B.
  Registry ids (H1–H8 / S1–S7 / V1–V4) are the pipeline vocabulary.

## Revision after A10 (main merged 2026-08-24)

`main` closed option (a): A10 (`code/a10_wagner_density.py`) measured the
Wagner-4 birthday reach law (1−ρ)·r_max ≈ const, r_max ~ log N, so the
solver class needs ρ ≳ 0.98 vs H7's ≈ 0.004 — the low-density escape is
closed. The paper was revised accordingly (main merged into this branch so
FINDINGS/registry/A10 code are present):

- Abstract, intro (ii), and "what is not claimed" now state the **two-part
  obstruction**: high-density pools unharvestable (N1) AND low-density pools
  unsolvable (A10); the r=5 route is closed for the AGHS/birthday class.
- §4 restructured: 4.5 harvest jaw (N1) → 4.6 solver jaw (A10 reach law,
  new Finding + Table) → 4.7 the identity-density vise.
- §5 retitled "Scope, caveats, and what remains open": the "one open escape"
  item replaced by A10 caveats (Wagner-4 simplest variant; higher-k lowers
  threshold only to ρ≈0.85–0.95; uniform Z/3 component model; full AGHS
  two-potential algorithm not reproduced — closure rests on the birthday
  core's measured law). Remaining open: option (b) different solver
  paradigm, option (c) different r/construction (+ admissible cells Q6.2).
- New Appendix A reach-law table; vise table gained a "solvable?" column;
  Appendix B row for `a10_wagner_density.py`.

## Sourcing notes (per the plan's hard rule 1)

Every number in the paper traces to `data/FINDINGS.md` (or a committed
`data/generated/*.json` it cites). No numbers had to be invented; no TODOs
remain in the text. Deliberate omissions and small deviations:

- **A4 per-cell group-decomposition table** (2103/7722-bit etc. rows) lives
  only in `doc/a4-solver-analysis.md`, not FINDINGS, so it was left out; the
  paper uses only the FINDINGS-quoted values (4586 components, 12 s, ~16%
  2-part, ~84% odd ≈ 15k bits, odd primes to 6269).
- **PTE/H4 figures** ("20,070 records; 0 LP-eligible") appear only in
  `doc/registry.md`/`PLAN.md`, not FINDINGS — omitted; H4 is mentioned only
  as a registry id.
- **a8 stub regime**: the plan says "solves only ρ≥0.9, r≤20"; FINDINGS says
  "r ≤ 20 components, high identity-density". The paper uses the FINDINGS
  wording (ρ≥0.9 is not in FINDINGS).
- **H8 density in the gap table** (≈0.07–0.18 where nonempty) is read off the
  N1 table's mean/max density columns.
- **AGHS authors**: the plan's "Hayman–Shallow" is a typo; cited as Alford–
  Grantham–Hayman–Shallue (Math. Comp. 83 (2014); arXiv:1203.6664), matching
  FINDINGS.

## For the user

- Not pushed to `main`; no PR opened (per plan §1). The live files
  (`code/`, `PLAN.md`, `data/FINDINGS.md`, `doc/registry.md`,
  `doc/working-paper.tex`, `doc/harvest-spec.md`) are only ever brought in
  by merging `main`, never edited here.
- Build artifacts (`doc/negative-result.log`/`.out`) are ignored via a
  two-line append to `.gitignore` (the only file shared with `main` this
  branch touches; the append is additive and should merge cleanly).
