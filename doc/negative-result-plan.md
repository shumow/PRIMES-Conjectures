# Execution plan: the "quantified infeasibility" negative-result paper

**For:** a fresh agent, working in a **separate git branch**, with no access to
the conversation that produced the repo. Everything you need is in the repo;
this document tells you what to build, where every number comes from, and the
scope discipline that keeps the paper honest.

**Deliverable:** a self-contained LaTeX paper,
`doc/negative-result.tex` (+ compiled `.pdf`), an arXiv-style technical note
reporting that the *specific pipeline* for constructing a Lenstra–Pomerance
counterexample to Agrawal's conjecture — twin-smooth harvest → subset-product
solve — is blocked at the solver stage by a **quantified identity-density gap**,
while the supply (harvesting) half is solved. It is **not** a disproof of
Agrawal's conjecture and **not** a proof that no counterexample can ever be
constructed. Scope discipline (below) is the most important part of the job.

---

## 0. First, orient yourself (read these, in order)

1. `README.md` — literature survey of Agrawal's & Popovych's conjectures.
2. `doc/working-paper.tex` — the math: the L–P theorem (Thm 2.1), the proved
   lemmas (mod-5 residues 2.2, **side-coprimality 2.3**, 2-adic 2.5, dictionary
   4.1), the **reduction to subset-product (Prop 3.1)**, boost obstruction
   (Prop 6.1). **Reuse these statements verbatim** — do not re-derive.
3. `doc/background.tex` — the 2-page framing (multicol bib); mirror its LaTeX
   conventions (amsthm, hyperref, the `\Z`,`\F`,`\lcm`,`\ord` macros).
4. `data/FINDINGS.md` — **the single source of truth for every number.** Every
   quantitative claim in the paper must be traceable to a dated section here.
5. `doc/registry.md` — the H1–H8 harvesters / S1–S6 solvers / V1–V4 validators,
   with status. Use the ids as the paper's vocabulary for the pipeline stages.
6. `doc/twin-smooth-review.md` — the isogeny twin-smooth literature (CMN/CHM/
   Pell/MSW) and why the lattice method (2025/1462) doesn't fit.
7. `doc/a4-solver-analysis.md` — the solver decomposition and the AGHS pointer.
8. `PLAN.md` §"A4/A5/A6 STATUS" and the **N1 RESULT** block — the arc summary
   and the strategic fork this paper writes up (option d).

Skim the code files named in `registry.md` only enough to cite them correctly
(`code/a1_yield_prototype.py`, `a2_*`, `a4_solver.py`, `a5_*`, `a6_oddsolver.py`,
`a8_omega_solver.py`, `a9_divisor_harvest.py`, `b547_pool_analysis.py`,
`chm_closure.c`). **Do not modify any code.**

---

## 1. Branch & hygiene

- Create branch `negative-result-writeup` off current `main`. Work only there.
- You **create** `doc/negative-result.tex` and its `.pdf`, and may add a short
  `doc/negative-result-data.md` if you want a numbers-appendix scratchpad. Do
  **not** edit `code/`, `PLAN.md`, `data/FINDINGS.md`, `doc/registry.md`,
  `doc/working-paper.tex`, or `doc/harvest-spec.md` — those are live for the
  parallel "option (a)" work on `main` and must not conflict.
- Commit to the branch; **do not push to main / do not open a PR** unless the
  user says so. End commit messages with the repo's Co-Authored-By trailer.
- Compile with `pdflatex` (available). Ensure it builds clean (2× for refs).

---

## 2. Paper structure (target ~8–12 pages)

**Title (working):** *On the Infeasibility of Constructing Lenstra–Pomerance
Counterexamples to Agrawal's Conjecture via Twin-Smooth Subset Products.*
Authors: Dan Shumow and Claude (Anthropic Fable 5) — match existing docs.

**Abstract.** Agrawal's conjecture; the L–P construction; the idea of
*constructing* rather than searching for a counterexample; the two-stage
pipeline (harvest → subset-product solve); the finding: supply is solved
(validated yield model, ratios ≫ threshold) but the solve stage is blocked by
a quantified identity-density gap between what the scalable subset-product
solver (AGHS) needs and what the double Carmichael+Lucas condition can supply.
State scope: not a disproof of the conjecture; one escape remains untested.

**§1 Introduction.** Conjecture 1 (Agrawal) from working-paper. Why constructing
a counterexample is attractive (abandon minimality; density improves with size;
the construction is deterministic). Contributions: (i) a validated,
over-provisioned *supply* method; (ii) identification and *quantification* of a
solver-stage obstruction; (iii) reusable machinery and diagnostics. One
paragraph, explicit, on what is NOT claimed.

**§2 The construction and its reduction.** Restate (cite working-paper): L–P
Thm 2.1 (r=5, conditions a–d), side-coprimality Lemma 2.3 (the odd supports of
{p−1} and {p+1} are disjoint — the structural crux), the dictionary (Lemma 4.1:
m ≡ 1 mod 40), and **Prop 3.1** (odd-cardinality subset with product ≡
(1 mod Λ₋, −1 mod Λ₊) ⇒ counterexample). This makes the target precise: a 0/1
subset-sum in G = (Z/Λ₋)* × (Z/Λ₊)*.

**§3 Supply is solved (the positive half).** Cover, with numbers from FINDINGS:
- The **0.06 mining invariant**: mining any fixed twin corpus, the best
  side-partition keeps ≈0.06 elements per demand-bit, measured across B=100–547
  and pool sizes 78→73,163 (the complete B=547 corpus, 82,026,426 pairs). Table.
  ⇒ dataset-mining is dead; partition-first is required.
- **Partition-first harvest (H6/H7)** and gates **G1, G2**: ratios 13.8–44
  (A2 grid), frozen spec, and the **model validation** against the complete
  B=547 corpus (predicted/real 0.41–1.04, geo-mean 0.68 — *conservative*).
- **CHM-closure validation** (`chm_closure.c`): 99.2–99.98% of the exact
  complete sets with zero false positives; note the published N(200)=346,192
  was itself 0.8% short of the true 348,840.
Conclusion of §3: supply is abundant and over-provisioned; the binding
constraint is downstream.

**§4 The solver obstruction (the core negative result).**
- Linearization: G decomposes (CRT + Pohlig–Hellman) into cyclic prime-power
  components; finding a 0/1 subset is NP-hard in general, tractable only via
  structure.
- **2-part is easy but small:** GF(2)-linear, solved at full scale (4586
  components, 12s), but only ~16% of demand bits (FINDINGS A4/A6).
- **Odd part is the problem:** ~84% of bits, primes up to 6269. Generic exact
  (MITM) and heuristic (annealing) solvers cap at ~15 odd components / ~40 odd
  bits — 2–3 orders of magnitude below the ~24k-bit need (FINDINGS A6). Table.
- **The scalable method exists — AGHS (arXiv:1203.6664), 10^10-factor
  Carmichael numbers** — a subexponential ω-guided reduction over (Z/Λ)*, no
  small-odd-part requirement. **But it needs pool primes ≡ 1 on many
  components (high identity-density), the "p−1 | Λ" structure.**
- **N1, the density gap (the punchline).** The divisor-paradigm harvest (H8,
  `a9_divisor_harvest.py`) that *would* supply AGHS-density is **unharvestable
  under the double condition**: pool ≈ 0–2 primes across all feasible scales
  (table from FINDINGS N1). Quantified gap:
  - AGHS pools: identity-density ~0.3–0.5.
  - Harvestable H7 pools: ~0.003–0.008 (p−1 = 2m, m a product of ~4 primes) —
    ~100× lower.
  - H8 (AGHS-density): empty.
  ⇒ under the double Carmichael+Lucas condition one can have a harvestable pool
  **or** AGHS-like density, **not both**. The scalable solver is therefore not
  straightforwardly applicable; that is the obstruction.

**§5 Scope, caveats, and the untested escape.** Be scrupulous:
- NOT a disproof of Agrawal's conjecture (which remains open, believed false).
- NOT a proof no counterexample is constructible — only that *this pipeline*
  with *known solver families* is blocked.
- N1 tested squarefree divisors at finite scale (prime-power Λ and enormous
  scale untested, though the density trend and the ω(m)/|T₋| argument point the
  same way).
- **The one open escape:** whether the *full* AGHS ω-solver tolerates H7's low
  density is untested (the repo's `a8_omega_solver.py` is a stub that only
  solves ρ≥0.9, r≤20). State plainly that this is being pursued separately.
- Other unexhausted avenues: a solver purpose-built for low-density many-prime
  pools; a different AKS modulus r; the admissible-cell / boost question
  (working-paper Q6.2, Prop 6.1).

**§6 Reusable contributions & conclusion.** The validated supply machinery and
yield model; the density-gap as a *diagnostic* for Carmichael-type constructive
problems under a double side condition; the honest map of where the wall is.
Restate: the pipeline is blocked at the solver by a quantified density gap, one
escape remains open.

**Appendix A — data tables.** Reproduce, verbatim-from-FINDINGS: the 0.06
invariant table; the A2 ratio grid; the A6 solver-frontier table; the N1
yield/density table; the density-gap comparison. Each with a one-line pointer
to the generating script + FINDINGS section.

**Appendix B — reproducibility.** Map each claim → script in `code/` → the
`data/generated/*.json` it produced (list them; they are committed).

---

## 3. Hard rules for accuracy

1. **Every number comes from `data/FINDINGS.md`** (or a `data/generated/*.json`
   it cites). If a number isn't there, don't state it. Do not recompute or
   invent; if tempted, add a TODO and flag it to the user instead.
2. **Distinguish proved / measured / conjectured** in the prose, always. The
   lemmas (2.3 etc.) are proved; the ratios and the density gap are *measured*;
   the L–P counterexample-density heuristic is *conjectural*; the "blocked"
   conclusion is *empirical + structural argument*, not a theorem.
3. **No overclaiming the scope** — §5 is not optional throat-clearing, it is the
   result's boundary. A reviewer's first question will be "did you prove the
   conjecture has no counterexample?" — the answer, prominent, is no.
4. Cite the same bibliography as `working-paper.tex` (AKS, LPremarks, Vana09,
   AGP, LN, Wagner, CMN21, BCCEMNS23, MSW/2025.1462, Popovych09, HD21, LP2019)
   **plus** AGHS = Alford–Grantham–Hayman–Shallow, arXiv:1203.6664, *Constructing
   Carmichael numbers through improved subset-product algorithms*.

## 4. Definition of done

- `doc/negative-result.tex` compiles clean to a ~8–12pp PDF.
- Every table/number traces to FINDINGS; §5 scope section present and prominent.
- Committed to branch `negative-result-writeup`; not pushed to main.
- A short `HANDOFF.md` note on the branch listing any TODOs / numbers you could
  not source (for the user to resolve), if any.
