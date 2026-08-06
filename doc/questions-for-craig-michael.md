# Questions for Craig & Michael

Context: we're repurposing the twin-smooth machinery to hunt a counterexample
to Agrawal's conjecture (see doc/working-paper.pdf). Pool primes are exactly
prime-sum twin smooths with m ≡ 1 (mod 40); we then need a *global* partition
of the odd prime factor base into a "minus side" (dividing p−1's) and "plus
side" (dividing p+1's) across the whole pool — a constraint the isogeny
applications never see.

1. **Dataset:** Is the CHM B=547 run (the ~82M twin pairs from the ASIACRYPT
   2023 paper) archived somewhere, or is regenerating with the public code the
   right path? Rough compute cost to regenerate, and to push to B ≈ 1000–2000?

2. **Completeness at the small end:** For our purposes the small twins matter
   most (fewest prime factors → cheapest to keep in a partitioned pool). Does
   the constant-range CHM variant preserve completeness at the *bottom* of the
   size distribution (we can sacrifice the large-twin tail)?

3. **Congruence targeting:** Did anyone ever run CHM / PTE / XGCD with a
   congruence condition on m (we need m ≡ 1 mod 40)? Any structural way to
   bake it in, or is post-filtering (≈1/90 survival, measured) the only way?

4. **Prior art on the double condition:** In all the SQIsign/B-SIDH parameter
   hunting, did anyone study twins whose prime factors *partition* by side, or
   connect twin smooths to Carmichael/Lucas–Carmichael constructions? (Our
   go/no-go hinges on this partition; we'd love to know if it was considered
   and discarded.)

5. **Supply curve:** The counts 113 → 547 suggest N(B) ~ B^2.5–3. Do they have
   the count-vs-B table from their runs (and the size distributions)? The MSvW
   largest-twin estimator gives the tail; we need the bulk.

6. **Pell/interval navigation:** Buzek et al. can target twins in intervals.
   Could the same navigation target congruence classes (m ≡ 1 mod 40) directly?

7. **Personnel:** Is Bruno Sterner (or anyone) still actively computing twin
   smooths? Any interest in a collaboration where the target is a 20-year-old
   conjecture in primality testing rather than isogeny parameters?
