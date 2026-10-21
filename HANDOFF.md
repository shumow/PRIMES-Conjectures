# HANDOFF — negative-result paper (branch `negative-result-writeup`)

Status 2026-10-21: `doc/negative-result.tex` compiles clean to an 11-page
PDF (`doc/negative-result.pdf`), within the plan's 8–12 pp target. All
sections of `doc/negative-result-plan.md` are present; §5 of the plan
("the untested escape") was updated to the current state of knowledge:
A10 has since *closed* that escape (measured Wagner reach law), and the
AG-track results (branch `arith-geom-interpretation`, `doc/arith-geom.tex`
v1.0) are folded in as §5 "The obstruction is structural" (dimension-count
theorem for every r, the Williams/sign-split framing, the Popovych burden
jump, the stabilizer-index closure of the CM-elliptic axis).

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
