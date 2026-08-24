# Handoff: negative-result write-up branch

*Branch: `claude/negative-result-writeup-8fantb` (the session-designated name;
the plan's suggested name was `negative-result-writeup`). Executes
`doc/negative-result-plan.md`.*

## Delivered

- `doc/negative-result.tex` + `doc/negative-result.pdf` — 12 pages, compiles
  clean with `pdflatex` (3 passes; texlive-latex-base/-recommended suffice).
  Structure follows the plan §2 exactly: intro with explicit non-claims,
  construction + reduction (statements reused from `doc/working-paper.tex`),
  supply-solved (§3), solver obstruction + density gap (§4), scope/caveats/
  open escape (§5), reusable contributions (§6), data-table appendix A,
  reproducibility appendix B. Registry ids (H1–H8 / S1–S6 / V1–V4) are the
  pipeline vocabulary.

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

- Not pushed to `main`; no PR opened (per plan §1). Untouched: `code/`,
  `PLAN.md`, `data/FINDINGS.md`, `doc/registry.md`, `doc/working-paper.tex`,
  `doc/harvest-spec.md`.
- §5's "one open escape" (full AGHS solver on low-density H7 pools) is stated
  as being pursued separately — update that sentence if the option-(a) work
  on `main` resolves it before submission.
- Build artifacts (`doc/negative-result.log`/`.out`) are left untracked; add
  them to `.gitignore` on `main` if desired (this branch avoids editing
  `.gitignore` to prevent conflicts).
