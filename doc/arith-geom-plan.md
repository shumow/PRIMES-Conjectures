# Plan: the arithmetic-geometric interpretation track (AG)

*Created 2026-09-01 on branch `arith-geom-interpretation`. Findings that seed
this plan: `doc/arith-geom-findings.md`. This track is theory-first; it reuses
the repo's measurement record (`data/FINDINGS.md`) and component registry
(`doc/registry.md`) but launches no new large computations until AG4 asks for
them. Style follows PLAN.md: numbered work items with concrete deliverables
and go/no-go gates.*

**Why this track exists.** The main line (PLAN.md Tracks A/B/C) ended in a
quantified negative: the twin-smooth / L–P route is blocked at the solver
(G3), for every AKS modulus r (A11). The geometric reading of those results
(findings §3–§4) does three things: (i) turns the strongest empirical
sections of the planned negative-result paper into provable structure,
(ii) exposes one axis the negative results do *not* cover (non-torus group
schemes, i.e. elliptic torsion), and (iii) suggests the first positive
evidence for Popovych's conjecture. Items are ordered by
(value × tractability), not by intellectual excitement.

---

## AG1. Precise Frobenius-lift statement of the conjecture (formalization)

**Goal.** State and prove the dictionary of findings §1–§2 at full precision,
as a section usable by both papers:

- (a) Lemma: for n prime, ψⁿ = (n-power map) on (Z/n)[Z/r]; for n composite,
  the defect of ψⁿ being a Frobenius lift at n, restricted to X−1, *is* the
  AKS congruence. Include the parity/well-definedness caveats (n coprime
  to r; σ_n well defined via exponent mod r).
- (b) Lemma: n² ≡ 1 (mod r) ⟺ σ_n ∈ Gal(Q(ζ_r)/Q(ζ_r)⁺); restate the
  conjecture as: *a Frobenius impostor on the single section X−1 acts
  trivially on the real locus*.
- (c) Short discussion (no theorem): the Λ-ring/F₁ framing (Wilkerson,
  Borger) and pseudofields (L–P 2019) as prior art for "primality =
  certified Frobenius datum". Cited, not re-developed.

**Deliverable.** `doc/arith-geom.tex` §1–2 (new working paper section, LaTeX
conventions of `doc/background.tex`). **Effort:** days. **Risk:** low — this
is exposition-grade; the only care point is stating (a) for composite n
without accidentally assuming ψⁿ multiplicative.

## AG2. Theorem: the torus dimension count behind A11 (the A11 upgrade)

**Goal.** Replace A11's empirical table with a proof. Target statement:

> For every prime r ∤ n and every valid counterexample regime (σ_n of order
> d > 2 in (Z/r)*), the p-dependent (large-prime) part of ρ(p) = ord(X−1) in
> the F_{p^d}-factor of F_p[X]/(X^r−1) is carried by the cyclotomic factors
> Φ_e(p), e | d, and the counterexample congruences force smoothness /
> divisibility control on a set of levels of total dimension Σ φ(e) ≥ 2,
> with equality iff the level set is {1, 2}. Since φ(e) = 1 ⟺ e ∈ {1, 2},
> the double (Carmichael + Lucas–Carmichael, twin-smooth) condition is the
> unique minimum, for every r.

Steps: (i) re-derive the control of ord(X−1) by p^d−1 and its cyclotomic
splitting for general r (this subsumes part of the old B1 item — for r=5 it
is Váňa's ρ(p) | 10(p²−1)); (ii) isolate exactly which levels must be smooth
for the L–P-style construction to close (the "harvest burden" of A11);
(iii) the φ(e) dimension count. Validate every intermediate claim against
the A11 numbers in `data/FINDINGS.md` and `code/a11_general_r.py` (the
empirical table becomes the theorem's regression test).

**Deliverable.** `doc/arith-geom.tex` §3 + a patch note for
`doc/negative-result-plan.md` pointing the paper's A11 section at the
theorem. **Gate AG-G1:** the proof closes with no unproved bridge lemma left
— if a gap survives (most likely in step (ii), the exact-power/validity
analysis for general r), record it as a stated conjecture verified
empirically by A11 and mark the section conditional. **Effort:** 1–2 weeks.
**Risk:** medium — step (ii) is the same territory old-B1 found nontrivial.

## AG3. The impersonation hierarchy (definitions + literature anchoring)

**Goal.** Define "Korselt at depth d" / Frobenius impersonation on
Res_{F_{p^d}/F_p} G_m cleanly (n ≡ p on the torus factors T_e, e | d), and
anchor it in the existing literature on Carmichael generalizations
(Lucas–Carmichael, Williams numbers, rigid Carmichael variants, Korselt
sets). Two purposes: (a) the negative-result paper gets a standard-sounding
vocabulary and a related-work section that situates the L–P condition as
"depth-2 impersonation"; (b) check for prior art — if someone has already
studied depth-2 Korselt numbers structurally, their results import directly.

**Deliverable.** `doc/arith-geom.tex` §4 + additions to the README literature
survey. **Effort:** days (mostly search + writing). **Risk:** low.

## AG4. Elliptic Agrawal: formulate, then decide (the uncovered axis)

**Goal.** The one place the geometric view might re-open a constructive
route. Three stages, each gated:

- (a) **Formulate.** Write the elliptic analogue precisely: fix E/(Z/n) and a
  torsion scale r; the test congruence is the E-analogue of
  (X−1)ⁿ ≡ Xⁿ−1 (division-polynomial / elliptic-period form, following
  Couveignes–Lercier and the Gurevich–Kunyavskii framework); state what the
  conclusion clause (the analogue of n² ≡ 1 mod r) should be. Nontrivial:
  "the" Frobenius on E mod a composite n is not a single scalar — part of
  the formulation task is deciding what impersonation even means per prime
  divisor (n ≡ a_p-related congruences mod #E(F_p)-type quantities).
- (b) **Counterexample heuristic.** Run the L–P density argument in the
  elliptic setting: the impersonation condition becomes divisibility
  involving #E(F_p) = p+1−a_p — *one* condition per prime, but with curve
  freedom (choose E after seeing the pool, or per-candidate). Estimate
  whether the analogue of the double condition splits into two rigid events
  (→ same wall as N1) or stays one soft event (→ a genuinely new
  constructive route with different economics).
- (c) **Only if (b) is favorable:** port the A1-style yield measurement to
  the elliptic harvest (pool primes p with smooth #E(F_p) for a chosen CM
  family — note this is smooth-cardinality prime hunting, adjacent to ECPP
  and to anomalous-curve constructions) and re-run the solver-side density
  analysis (registry S7 methodology) on the resulting group.

**Gate AG-G2 (after (b)):** proceed to (c) only if the heuristic shows a
single-rare-event structure with identity-density prospects materially
better than H7's ρ ≈ 0.004; otherwise write (a)+(b) up as an extension of
the negative result ("the obstruction persists on the elliptic axis" — also
publishable). **Effort:** (a) ~1 week, (b) 1–2 weeks, (c) only past the
gate. **Risk:** high on (b)'s outcome, low on its executability — either
answer is a usable result.

## AG5. A heuristic *for* Popovych (cheap spin-off)

**Goal.** Findings §6: make precise — in the same style as L–P's heuristic
count *against* Agrawal — why the counterexample machinery cannot control
the pair {ζ−1, ζ+2}. Sketch: impersonation fixes n on the subgroup generated
by the reduction of ζ−1; forcing the (X+2)-congruence adds an independent
order-divisibility system for ζ+2, i.e. a third rare event per pool prime;
combine with the measured N1 collapse (two events already give ~empty
pools) into a quantified statement "no L–P-family construction reaches
Popovych". Distinguish carefully: this is evidence that *this mechanism*
fails, not a proof supporting the conjecture.

**Deliverable.** `doc/arith-geom.tex` §5, candidate for a standalone short
note (would be the first published evidence in either direction on Popovych
beyond search ranges — see README §4). Old-B4 is subsumed by this item.
**Effort:** ~1 week. **Risk:** low-medium (the heuristic must be honest
about independence assumptions).

## AG6. Function-field sanity check (optional, timeboxed)

**Goal.** One-page appendix: in F_q[t] (Carlitz-module Fermat), the analogue
of "one section detects Frobenius" is provable because Weil bounds control
the relevant character sums — locating exactly which ingredient is missing
over Z. Value: sharpens what a proof of Agrawal would need; also a good
introduction paragraph for AG1. Timebox to 2 days; drop if it balloons.

---

## Sequencing and gates

```
AG1 (formalize) ──► AG2 (A11 theorem) ──► fold into negative-result paper
      │                    │ AG-G1: proof closes, else conditional
      ├──► AG3 (hierarchy + lit) ── parallel, feeds related-work
      ├──► AG5 (Popovych heuristic) ── parallel after AG1
      └──► AG4a (elliptic formulation) ──► AG4b (heuristic) ──► AG-G2
                                                │ favorable        │ not
                                                ▼                  ▼
                                       AG4c (measure, new     extend negative
                                       constructive track)    result to the
                                                              elliptic axis
```

Priority order: **AG2 > AG5 > AG1 > AG3 > AG4 > AG6.** AG1 is listed after
AG2/AG5 only because its content is exposition that will be written anyway
as those sections' preliminaries; start AG2 first, let AG1 accrete.

## Deliverables summary

- `doc/arith-geom.tex` (+ compiled PDF): the working document for this
  track, sections per item above. LaTeX conventions of `doc/background.tex`.
- Patch notes into `doc/negative-result-plan.md` (AG2, AG3, AG4-negative
  outcome) — the negative-result paper is written from a separate branch;
  coordinate via notes, do not edit its plan's numbered sections directly.
- Possible standalone short note from AG5.
- New registry entries only if AG4c opens (elliptic harvester/solver ids).

## Risk register

1. **AG2 step (ii) gap** (exact validity analysis for general r): fall back
   to conditional statement + A11 empirical support; the paper survives.
2. **AG4 formulation ambiguity** (what "Frobenius impersonation" means for
   E mod composite n): timebox (a); if no canonical formulation emerges,
   record the obstruction itself — that the elliptic analogue lacks a
   well-posed counterexample mechanism — which is still an answer.
3. **Scope creep toward F₁/Λ-ring theory** (AG1c, AG6): both are capped at
   citation/appendix level; this track's output is number theory, not
   foundations.
4. **Prior art** (AG3): depth-2 Korselt structures may exist under another
   name; a hit is a feature (import results), not a risk to novelty of the
   quantified solver obstruction.
