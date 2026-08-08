# A4 solver — G3 phase-1 analysis

*2026-08-07. `code/a4_solver.py`. Status: **G3 NOT yet passed** — and the
reason is the important finding.*

## The problem

n = ∏_{p∈S} p ≡ 1 (mod Λ₋), ≡ −1 (mod Λ₊), |S| odd, linearizes by discrete
logs into subset-sum in G = (Z/Λ₋)* × (Z/Λ₊)*:
find x ∈ {0,1}^N with Σ x_p v_p = t in G, Σ x_p ≡ 1 (mod 2). G decomposes into
cyclic prime-power components Z/ℓ^a (from the prime-power parts of each q−1,
q ∈ Q₋∪Q₊). Pool N ≫ dim, so solutions are super-dense; finding a 0/1 one is
the crux (NP-hard in general; tractable only via structure).

## What the prototype established

**1. The 2-part is GF(2)-linear and solves at full scale.** Every constraint
reduced mod 2 is linear over GF(2) (x∈{0,1}=GF(2)); the GF(2) subset-sum
(+parity row) solves by Gaussian elimination over bitset rows in seconds:

| B | B′ | components | dim bits | 2-part bits | odd bits | odd % | max odd ℓ | GF(2) solve |
|---|---|---|---|---|---|---|---|---|
| 547 | 5470 | 2103 | 7722 | 1412 | 6310 | 82% | 2699 | 1.8s |
| 1259 | 12590 | 4586 | 17973 | 2963 | 15010 | 84% | 6269 | 12s |
| 1259 | 18885 | 6669 | 26957 | 4270 | 22687 | 84% | 9419 | 32s |

**2. The 2-part is only ~16% of the problem.** This overturned the working
assumption (that the 2-torsion was "the bulk"). A random q−1 (q ~ 2^12) has
v₂ ≈ 1–2 but odd part ~2^10, so **~84% of the demand bits live in the
odd-prime components** — and those carry primes ℓ up to ~6000–9000. The
odd-part subset-sum is the real problem, and the prototype's kernel-XOR + MITM
closer fails even at ~60-bit odd scale.

## Consequence: the solver, not supply, is the binding constraint

The phased gates worked exactly as intended — we found this **before** spending
days on the A3 production harvest. G1/G2 proved supply is a solved problem
(ratio 13.8, pool ~2.5e5); G3 shows the ~15k-bit odd-prime subset-sum is where
the difficulty actually is.

## Three paths (not mutually exclusive)

1. **Harvest/solver co-design (couples back to A2).** The odd bits come from
   odd factors of q±1. Preferentially harvest with medium primes q whose q−1
   is 2-power-heavy / odd-smooth (q ≡ 1 mod 2^k, (q−1)/2^k smooth over a tiny
   set) shrinks the odd part toward the GF(2)-tractable regime. Cost: a
   density hit on Q₋ (fewer eligible medium primes → lower harvest yield), so
   A1/A2 economics must be re-run under the constraint. Likely a partial
   mitigation, not a full fix (killing the odd part entirely is very
   restrictive).
2. **A proper odd-part solver.** Options: Wagner k-tree over the odd
   components (classic form needs lists ~2^{oddbits/(h+1)} — too large as-is,
   but block-wise variants over the many small components may fit); or a
   lattice/ILP approach exploiting N ≫ dim (0/1 point in a solution-lattice
   coset — dense, but CVP at N~10^5 is nontrivial); or structured
   integer-linear-algebra with 0/1 rounding driven by the GF(2) kernel (the
   prototype's idea, done properly). This is a substantial build.
3. **General r / different group (Track B3).** A different AKS modulus r
   changes which group controls the construction; some r may yield a
   2-power-heavier or smaller-odd-part group. Cheap to assess, potentially
   reframes the whole solver problem.

## Recommendation

Pursue **(1)+(2) together**: add a "2-power-heavy Q₋" option to the harvester
and measure how far it shrinks the odd part and at what yield cost (feeds A2);
in parallel, prototype the odd-part solver at the reduced odd-dimension that
co-design produces, where Wagner/MITM becomes feasible. Re-attempt G3 with the
co-designed group. Do **not** launch A3 production harvest until G3 passes on
the co-designed spec — the gate exists precisely to prevent harvesting a pool
the solver can't consume.
