# HANDOFF — negative-result paper (branch `negative-result-writeup`)

## Update 2026-10-22: external feedback incorporated (v1.1)

The 2026-10-22 feedback memo was applied across both branches:

- **Epistemic framing**: the one conditional ingredient (Artin-type
  generic sharpness) is now *named in the abstracts* of the paper, the AG
  document and the memo, with the 0/196 empirical support and its
  theorem-status in the function-field mirror, and explicitly separated
  from the mechanism scope.
- **§5 restructured theorem-first**: the stabilizer-index theorem now
  leads, with the per-section table (section / U / min burden /
  realizability), and AG2/AG5/AG4 derived as corollaries; the sign-split
  section closes it. Paper is now 12 pp.
- **Technical checks**: (a) the (2^r+1)/3 norm is correct in all sources —
  the reviewer's "(2r+1)/3" was a PDF text-extraction artifact; (b) the
  Dickman tax now names both bases (B = 1259, B' = 12590) wherever stated;
  (c) the AG2 verification states its 67 primes are sampled and
  implemented independently of the A11 scan (A11: p > 1000, one fixed
  class per r; AG2: p from 3 upward, all classes, exact orders by
  polynomial arithmetic); (d) Borger–Gurney no longer carries the elliptic
  only-if — the elementary degree-p-endomorphism argument is inline, with
  B–G cited for CM existence/canonicity; (e) Howe's n failing T(−1,n,5) is
  now in Appendix A with the script/check pointer (H1/H4).
- **Constructive reframings** (feedback §"positive reframings" items 1–2):
  §7 now presents the stabilizer index as a design metric / security
  parameter for AKS-style tests, and states the unconditional
  function-field form ("no Frobenius-matching forgery beats the floor"
  over F_q(T)); §6 states the result *sharpens rather than kills* option
  (b). Items 3–4 (AG3 as a standalone classification note; full
  repackaging to lead the main paper with the metric) are left as
  user-level packaging decisions.
- **Standalone AG5 note written**: `doc/popovych-note.{tex,pdf}` (4 pp, on
  the AG branch, merged here) — self-contained, conditionality in the
  abstract, non-unit lemma, burden theorem + table, Dickman estimate with
  explicit parameters, base-3/char-3 remarks, verification summary.

Not adopted (with reasons): the full repackaging of the main paper around
the design metric (changes the paper's genre from the planned negative
result; the metric is §7-prominent instead) — flag to the user as a
decision.

Status 2026-10-21 (original): `doc/negative-result.tex` compiles clean
(now 12 pp with the restructure), within the plan's 8–12 pp target. All
sections of `doc/negative-result-plan.md` are present; §5 of the plan
("the untested escape") was updated to the current state of knowledge:
A10 has since *closed* that escape (measured Wagner reach law), and the
AG-track results (branch `arith-geom-interpretation`, `doc/arith-geom.tex`
v1.0) are folded in as §5 "The obstruction is structural" (the
stabilizer-index theorem with the dimension-count, Popovych and elliptic
corollaries, and the Williams/sign-split framing).

## Deviations from the plan, with reasons

1. **Branch base.** The plan said to branch off `main`; this branch is
   based on `arith-geom-interpretation` instead, because the paper cites
   and depends on the AG results (arith-geom.tex, the ag*-scripts and
   their JSON outputs, README §4a). Merging `arith-geom-interpretation`
   to main first, then rebasing or merging this branch, is the clean
   integration path.
2. **"Untested escape" → "closed escape."** The plan predates FINDINGS
   §A10/§A11. The paper reports A10 as part of the core result (§4.3)
   rather than as an open caveat, and §6 item 5 lists what actually
   remains open now (option (b) solver; admissible cells / Q6.2;
   Williams existence; unconditional sharpness).
3. **No per-claim TODOs remain in the tex.** Every number was taken from
   `data/FINDINGS.md` or `doc/arith-geom-findings.md`; nothing was
   recomputed or invented.

## Items for the user to verify before any submission

- **Bibliographic page numbers** taken from memory/search rather than the
  publishers' pages: Wright BLMS 50 (2018) 791–800; AGHS Math. Comp. 83
  (2014) 899–915; Echi C. R. Can. 29 (2007) 41–47; Williams Canad. Math.
  Bull. 20 (1977) 133–143. Volumes/years are confirmed; double-check the
  page ranges.
- **Acknowledgment**: the complete B=547 corpus is credited to M. Naehrig
  in §3.1 (data itself is not in the repo, per the agreement noted in
  FINDINGS); confirm he is comfortable with the wording before
  circulating.
- **Authorship/affiliations** are copied from the repo's existing
  convention; adjust as desired.
- The proof of Theorem 2.1 (L–P) is cited to [LPremarks]/[Vana09], per
  the repo's standing caveat that the full independent re-derivation
  (old item B1) was never completed; the paper never relies on more than
  the mechanism-level statements that *were* re-derived and verified
  (arith-geom.tex §§2–3).

## Definition-of-done checklist (from the plan §4)

- [x] `doc/negative-result.tex` compiles clean, 11 pp.
- [x] Every table/number traces to FINDINGS / arith-geom-findings
      (reproducibility map in Appendix B).
- [x] Scope section (§6) present and prominent; "not a disproof" stated
      in the abstract, §1, and §6.
- [x] Committed to branch `negative-result-writeup`; not pushed to main.
- [x] This HANDOFF.md.
