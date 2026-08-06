# Literature Survey: Agrawal's Conjecture and Popovych's Conjecture

*Compiled 2026-08-05. Status of both conjectures: **open**. Agrawal's is believed false
(Lenstra–Pomerance heuristic); Popovych's has no known evidence in either direction beyond
computation.*

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
- **OEIS [A329223](https://oeis.org/A329223)**: numbers both Carmichael and
  Lucas–Carmichael (would-be Agrawal counterexamples). No terms known; empty against
  Pinch's Carmichael tables (complete to 10¹⁸, later to 10²¹ —
  [Pinch, "The Carmichael numbers up to 10^18"](https://arxiv.org/pdf/math/0604376)).
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
