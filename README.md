# Literature Survey: Agrawal's Conjecture and Popovych's Conjecture

> **Joint correctness audit in progress.** The constructive experiments and the
> arithmetic-geometric analysis have been combined. Initial follow-up work
> corrects the written modulus reduction, A4/A6 solver algebra, and benchmark
> definitions/reporting. The AG sources now distinguish proved identities,
> conditional smoothness and unproved extensions. Small independent regression
> tests pass; historical claims and outputs are preserved;
> neither track is certified. See
> [`doc/integration-review-status.md`](doc/integration-review-status.md)
> for verified corrections, outstanding concerns, provenance, and test commands.
> Original PDFs beside the sources remain historical. Use the separately
> rebuilt [audit PDFs](#current-audit-papers-provisional) below for current statements.

*Compiled 2026-08-05. Status of both conjectures: **open**. Agrawal's is believed false
(Lenstra–Pomerance heuristic); Popovych's has no known evidence in either direction beyond
computation.*

## Running the audit checks

The bounded, standard-library audit suite requires **Python 3.9 or newer**
(it uses `math.lcm`). From the repository root:

```text
python -B -m unittest discover -s code -p "*correctness.py" -v
```

The solver and its independent test oracles do not require Python 3.10's
`int.bit_count()`. This suite does not run production harvests or the
SymPy-dependent AG experiment scripts. The initial audit's 36 tests were run
with Python **3.9.13** and **3.14.5**. The real-pool pilot extends the suite
to **65 passing tests on both runtimes**, adding actual-prime encoding,
minimum-cardinality and independent-verifier checks.

## Real-pool construction and validation pilot

The [pilot report](doc/real-pool-pilot.md) replaces synthetic-vector assumptions
with deterministic actual-prime pools, full prime-power moduli, explicit
target obstructions and bounded solver comparisons. The complete medium
family supplies **483 certified primes**, with a nontrivial binary kernel;
its real target remains unresolved, not disproved.

```powershell
python -B code\real_pool_pilot.py
python -B code\real_pool_verify.py data\generated\real_pool_pilot.json.gz
```

The [compressed dataset](data/generated/real_pool_pilot.json.gz) is committed.
The generator refuses to overwrite it without `--replace`; use a different
`--output` for a comparison run. The standalone verifier checks source hashes,
prime certificates, exact encodings/statistics, obstruction witnesses and
reported outcomes. Planted controls are explicitly separate from real L-P targets.

The [next-phase feasibility plan](doc/harvest-solver-feasibility-plan.md)
defines three parallel agent tracks for solver controls, exact subgroup
reachability and harvest-design comparison, with separate file ownership,
bounded experiments and integration gates.

## Current audit papers (provisional)

These PDFs were compiled from the revised sources with Tectonic **0.17.0**.
They contain the audit notices and qualified statements; a successful build
does not certify the research. Original PDFs in `doc/` are retained unchanged.

| Paper | Rebuilt audit PDF | Current source |
|---|---|---|
| Construction working paper | [PDF](doc/audit-pdfs/working-paper.pdf) | [LaTeX](doc/working-paper.tex) |
| Background and strategy | [PDF](doc/audit-pdfs/background.pdf) | [LaTeX](doc/background.tex) |
| Arithmetic-geometric analysis | [PDF](doc/audit-pdfs/arith-geom.pdf) | [LaTeX](doc/arith-geom.tex) |
| Arithmetic-geometric memo | [PDF](doc/audit-pdfs/arith-geom-memo.pdf) | [LaTeX](doc/arith-geom-memo.tex) |
| Popovych note | [PDF](doc/audit-pdfs/popovych-note.pdf) | [LaTeX](doc/popovych-note.tex) |

To rebuild all five with Tectonic from the repository root in PowerShell,
keeping outputs separate from historical PDFs:

```powershell
New-Item -ItemType Directory -Force doc\audit-pdfs | Out-Null
foreach ($name in @('working-paper', 'background', 'arith-geom', 'arith-geom-memo', 'popovych-note')) {
    tectonic --outdir doc\audit-pdfs "doc\$name.tex"
    if ($LASTEXITCODE -ne 0) { throw "PDF build failed: $name" }
}
```

## The conjectures

**Agrawal's conjecture** (formulated in the 2001 Bhattacharjee–Pandey thesis, popularized in
the AKS paper): if r is a prime not dividing n and

    (X − 1)^n ≡ X^n − 1  (mod n, X^r − 1)

then n is prime or n² ≡ 1 (mod r). If true → deterministic primality in Õ(log³ n).

**Popovych's conjecture** (2008): same conclusion from the two simultaneous conditions

    (X − 1)^n ≡ X^n − 1  and  (X + 2)^n ≡ X^n + 2  (mod n, X^r − 1).

---

## 1. Primary sources

- **M. Agrawal, N. Kayal, N. Saxena, "PRIMES is in P," Annals of Mathematics 160 (2004),
  781–793.** [PDF](https://www.cse.iitk.ac.in/users/manindra/algebra/primality_v6.pdf).
  The conjecture appears in the concluding section. The authors report verification for
  r = 5 up to n < 10¹¹ and for all prime r ≤ 100 up to n < 10¹⁰.
- **R. Bhattacharjee, P. Pandey, "Primality testing," BTech thesis, IIT Kanpur, 2001.**
  Original formulation of the conjecture.
- **N. Kayal, N. Saxena, "Towards a deterministic polynomial-time primality test,"
  Technical report, IIT Kanpur, 2002.** Precursor study of the a = −1 congruence
  T(−1, n, r) and its relation to known probabilistic tests.

## 2. Evidence against Agrawal's conjecture

- **H. W. Lenstra Jr., C. Pomerance, "Remarks on Agrawal's conjecture,"** AIM workshop
  *Future directions in algorithmic number theory*, 2003.
  [aimath.org/WWN/primesinp/articles/html/50a/](https://aimath.org/WWN/primesinp/articles/html/50a/).
  The central negative result. Construction: take n = p₁⋯p_k squarefree with
  (a) k ≡ 1 or 3 (mod 4), (b) each pᵢ ≡ 3 (mod 80), (c) pᵢ − 1 | n − 1,
  (d) pᵢ + 1 | n + 1. Then T(−1, n, 5) holds while n² ≢ 1 (mod 5) — a counterexample
  with r = 5. Heuristic count: at least e^{T²(1−5/m)} counterexamples below e^{T²},
  i.e. density ≫ x^{1−ε} for every ε > 0. Note conditions (c),(d) make n simultaneously
  a **Carmichael and Lucas–Carmichael number** — no such number is known to exist.
- **OEIS [A329223](https://oeis.org/A329223)**: a **nonempty** sequence of
  base-2 Fermat pseudoprimes congruent to 3 or 27 mod 80, with every prime
  factor congruent to 3 mod 80. Its entries are not simultaneous
  Carmichael/Lucas–Carmichael numbers. The entry identifies
  330468624532072027 as its only Carmichael member below 2⁶⁴ and states that
  it is not Lucas–Carmichael. This sequence is not an enumeration of the
  sought counterexamples.
- **A. Hegde, P. Devaraj, "Heuristics for the Construction of Counterexamples to the
  Agrawal Conjecture,"** in *Mathematical Analysis and Computing* (Springer PROMS,
  2021), [chapter](https://link.springer.com/chapter/10.1007/978-981-33-4646-8_42).
  Generalizes the Lenstra–Pomerance method to **two additional classes** of candidate
  counterexamples and gives analytic-number-theory estimates of their counts in large
  intervals. The most recent substantive theoretical work on the conjecture.
- **R. Popovych, "A note on Agrawal conjecture,"** Cryptology ePrint Archive 2009/008,
  [PDF](https://eprint.iacr.org/2009/008.pdf). Proves Lenstra's counterexample
  proposition in a more general setting (strengthening the case that Agrawal's original
  conjecture fails), then proposes the {X−1, X+2} modification, arguing the pair should
  generate a large enough subgroup of (Z/n)[X]/(X^r − 1) units to block the
  counterexample construction.

## 3. Computational verification

| Search | Range | Result |
|---|---|---|
| AKS authors (2002) | r = 5, n < 10¹¹; r ≤ 100, n < 10¹⁰ | no counterexample |
| Váňa (2009), structured search via Pinch's Carmichael tables | n ≤ 10¹⁸ | no candidate even close (see below) |
| **Primaboinca** (BOINC, 2010–2020), both conjectures | 10¹⁰ < n < 10¹⁷ | no counterexample ([project wiki](https://wiki.bc-team.org/index.php?title=Primaboinca/en), [primaboinca.com](https://primaboinca.com/)) |

- **T. Váňa (advisor M. Mačaj), "Agrawal's Conjecture and Carmichael Numbers,"**
  Comenius University Bratislava, student scientific conference, 2009.
  [PDF](http://www.dcs.fmph.uniba.sk/diplomovky/obhajene/getfile.php/diplomovka.pdf?id=228&fid=409&type=application/pdf).
  Underrated source. Contributions: (i) alternative proof of the Lenstra–Pomerance
  theorem including the k ≡ 3 (mod 4) case left as an exercise in the original;
  (ii) shows Carmichael numbers pass the AKS congruence for certain fixed r regardless
  of the base a; (iii) an algorithm computing ρ(p) (the order-like parameter with
  ρ(p) | 10(p²−1)) yielding per-prime CRT congruence systems, so candidate
  counterexamples can be assembled prime-by-prime instead of exhaustively searched;
  (iv) statistics against Pinch's tables to 10¹⁸: among ~10⁶ Carmichael numbers, at
  most 3 prime factors ever satisfy the p ≡ 3 (mod 80) condition and at most 3 satisfy
  p+1 | n+1 — never all factors — supporting the "counterexamples are enormous" view;
  (v) shows T(−1, M_p, 4) holds for every Mersenne number M_p with p > 3 prime, so
  composite Mersenne numbers give AKS pseudoprimes for r = 4 (a non-prime r, so not a
  conjecture counterexample, but structurally interesting); (vi) incidentally uncovered
  a bug in Maple 11's `isprime` via three Carmichael numbers it declared prime
  (43438471758571, 54165858332251, 367826207971951) — fixed in Maple 12.
- Folklore bound (quoted in Maple documentation and Brent's
  [ANU lecture notes](https://maths-people.anu.edu.au/~brent/pd/comp4600_primality.pdf)):
  any counterexample is conjectured to be **hundreds of digits long**, consistent with
  the Lenstra–Pomerance construction requiring many simultaneous divisibility
  conditions.

## 4. Work specific to Popovych's conjecture

- The defining reference is the 2009 ePrint note above; there is **no published
  heuristic against it** and no published proof strategy for it. Its plausibility
  argument rests on {X−1, X+2} generating a large unit subgroup — machinery related to
  Popovych's later unconditional lower bounds for orders of elements like x + c in
  Gauss/Kummer extensions: **R. Popovych, "Elements of high order in finite fields of
  the form F_q[x]/Φ_r(x)," Finite Fields and Their Applications 18(4) (2012), 700–710.**
- Primaboinca tested it alongside Agrawal's over 10¹⁰ < n < 10¹⁷: nothing found.
- Conference talk: [R. Popovych, "On Agrawal conjecture"](http://at.yorku.ca/c/b/f/n/39.htm).

## 4a. Generalized Carmichael structures (the counterexample cells' relatives)

*Added 2026-10-21 by the AG track (branch `arith-geom-interpretation`; see
`doc/arith-geom.tex` §6 for how these map onto "impersonation cells").*

- **H. C. Williams, "On numbers analogous to the Carmichael numbers," Canad.
  Math. Bull. 20 (1977), 133–143.** Asked whether a Carmichael number can
  also satisfy p+1 | n+1 for all p | n; showed such n need ≥ 4 prime
  factors. These are now called **Williams numbers** (Echi's "1-Williams"),
  and the L–P construction seeks such Carmichael+Lucas–Carmichael objects
  with additional local residue conditions. OEIS A329223 instead lists a
  related nonempty base-2 pseudoprime sequence, not this cell.
- **R. J. McIntosh, D. Mitra, "Carmichael numbers with p+1 | n+1," J. Number
  Theory 147 (2015), 81–91.** The modern search floor: **no Williams number
  below 2^64 ≈ 1.8·10^19**; only finitely many exist with any given set of
  all-but-three prime factors; a 4-factor Williams number needs smallest
  prime > 2·10^4. Nonemptiness of the cell is open.
- **T. Wright, "There are infinitely many elliptic Carmichael numbers,"
  Bull. LMS 50 (2018), 791–800 (arXiv:1609.00231).** As a by-product proves
  **infinitude of Lucas–Carmichael numbers** — so both single conditions
  (p−1 | n−1 by AGP 1994, p+1 | n+1 by Wright) hold infinitely often
  separately, while their conjunction (Williams) has no known example.
- **E. W. Howe, "Higher-order Carmichael numbers," Math. Comp. 69 (2000),
  1711–1719.** Defines order-m Carmichael numbers (x ↦ x^n an endomorphism
  of every Z/n-algebra generated by at most m elements **as a Z/n-module**);
  this is not a condition on the number of algebra generators.
  Korselt-type criterion: for each
  p | n and r ≤ m, n ≡ p^i (mod p^r − 1) for some i. Constructed the
  explicit **rigid order-2 example 443372888629441 = 17·31·41·43·89·97·167·
  331** (p²−1 | n−1 for all p; re-verified in code/ag3_hierarchy_check.py);
  heuristic for infinitude at every order. With McIntosh–Mitra this gives
  the striking contrast: **depth-2 impersonation is constructible (rigid,
  one-sided targets) at 4.4·10^14, while the sign-split Williams cell is
  empty to 2^64** — the structural reading of this project's N1/A10 results.
- **O. Eterevsky, M. Vsemirnov, Fibonacci Quart. 42 (2004), 141–148.**
  Order-m Carmichael numbers need ≥ m+2 prime factors; no order-3 example
  is known.
- **J. Grantham, "Frobenius pseudoprimes," Math. Comp. 70 (2001),
  873–891.** The impersonation idea as a primality test against one
  quadratic section.
- **Elliptic analogues** (the AG4 bridge): J. H. Silverman, "Elliptic
  Carmichael numbers and elliptic Korselt criteria," Acta Arith. 155
  (2012), 233–246; A. Ekstrom, C. Pomerance, D. S. Thakur, "Infinitude of
  elliptic Carmichael numbers," J. Aust. Math. Soc. 92 (2012), 45–60
  (conditional); Wright 2018 (unconditional).

## 5. Context: why the conjectures still matter

- **H. W. Lenstra Jr., C. Pomerance, "Primality testing with Gaussian periods,"
  J. Eur. Math. Soc. 21 (2019), 1229–1269** — unconditional Õ(log⁶ n), the current
  state of the art. Only an Agrawal/Popovych-type conjecture would beat it, at Õ(log³ n).
- **L. K. Nemana, V. Ch. Venkaiah, "An Empirical Study towards Refining the AKS
  Primality Testing Algorithm,"** ePrint [2016/362](https://eprint.iacr.org/2016/362) —
  empirical parameter tuning claiming O(log^{4+ε} n) behavior; orthogonal to the
  conjectures but part of the "make AKS practical" literature.

## 6. Bottom line

1. **Agrawal's conjecture: open, believed false.** The only concrete counterexample
   route (Lenstra–Pomerance, extended by Popovych 2009 and Hegde–Devaraj 2021) demands
   numbers that are simultaneously Carmichael and Lucas–Carmichael with extra congruence
   conditions; no such number exists below 10¹⁸, and exhaustive search is clean below
   10¹⁷. All heuristics say counterexamples exist but are astronomically large.
2. **Popovych's conjecture: open, untouched.** No counterexample below 10¹⁷, no
   heuristic against it, no progress toward a proof. It remains the live route to a
   Õ(log³ n) deterministic primality test.
