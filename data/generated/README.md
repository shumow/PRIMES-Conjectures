# Generated datasets

Produced by `code/import_pte_results.py` from the raw upstream mirror in
`data/raw/microsoft-twin-smooth-integers/` (see PROVENANCE.md there). Tests:
`code/test_pte_import.py`. Nothing in this directory is hand-edited.

## Files

- `pte_records.jsonl.gz` — one JSON object per upstream PTE-sieve record.
- `pte_prime_candidates.csv` — the subset with p = 2m+1 prime (pool-candidate
  view for the Lenstra–Pomerance construction).
- `pte_summary.json` — per-file and corpus statistics, including the failure
  list and the side-compatibility statistics defined below.
- `twins_B200.txt` — output of the compiled CHM closure (`code/chm_closure.c`)
  at B = 200: one twin m per line (validation target: the published original-CHM
  count 346,192).
- `import_run.log`, `chm_B200.log` — run logs.

## Schema of `pte_records.jsonl.gz`

Provenance: `source` (upstream repo @ commit), `source_result_filename`,
`line_number`, `method` ("PTE sieve" / "PTE sieve (squares variant)"),
`pte_degree`, `B` (smoothness bound, = 2^k per filename), `x` (evaluation
point), `pte_solution_id`, `pte_roots_A`, `pte_roots_B` (the PTE solution's
two root multisets).

Reconstructed values: `m`, `m_plus_1`, `p` (= 2m+1; decimal strings),
`bit_length_m`, `bit_length_p`, `factorization_m`, `factorization_m_plus_1`
(maps prime → exponent, computed here, not copied from upstream),
`unfactored_cofactors_m`, `unfactored_cofactors_m_plus_1` (lists of
[composite, multiplicity] that capped Pollard rho could not split — nonempty
only for non-fully-smooth records, and always included in the V2 product
check), `lpf_m`, `lpf_m_plus_1` (largest known prime factors), `smooth_ok`
(both sides verified fully B-smooth), `p_is_prime` (verified here via sympy
BPSW), `p_prime_claimed` (upstream's flag; mismatches are recorded as
failures in the summary).

**Corpus semantics note:** all size-6, size-12, and squares-variant B=2²²
records verify fully twin-smooth; the first squares-variant B=2²³ file
(x near 2⁶⁴) consists of records with large smooth *parts* but 34–42-bit
prime factors and rough cofactors on both sides — B-SIDH-style partial
candidates, faithfully flagged `smooth_ok=false` with their unfactored
cofactors recorded.

**Key finding (2026-08-07): the PTE corpus contains 0 LP-eligible records.**
Only 5 of 20k records land in the m ≡ 1 (mod 40) class at all — a rate
~1/4000, far below the ~1/90 measured for generic twin populations — because
PTE evaluation m = a(x)/C covers residue classes non-uniformly. The
constructive flip side: for a fixed PTE solution, m mod 40 is a polynomial
condition on x, so a congruence-targeted x-sieve could make *every* hit land
in our class. Worth raising with the PTE authors (questions #3/#6 in
doc/questions-for-craig-michael.md).

## Lenstra–Pomerance derived fields (precise definitions)

Context: working-paper.pdf §§2–4. A pool prime for the L–P construction at
r = 5 is p = 2m+1 with (m, m+1) twin smooth, p prime, and m ≡ 1 (mod 40)
(Dictionary Lemma 4.1: this single congruence is equivalent to p ≡ 3 (mod 80)
together with v₂(p−1) = 1, v₂(p+1) = 2, and 5 ∤ (p²−1)).

- `LP_congruence_ok` := (m mod 40 == 1). Exactly the dictionary congruence —
  no other condition is folded in.
- `LP_minus_omega` := #{distinct odd primes q dividing m}. Since p−1 = 2m,
  this is the number of odd primes the record demands on the minus side Q₋.
- `LP_plus_omega` := #{distinct odd primes q dividing m+1}. Since p+1 =
  2(m+1), these are the record's plus-side demands Q₊. (For LP-eligible
  records v₂(p+1) = 2, so the odd part of (p+1)/4 has the same primes.)
- `LP_minus_lpf`, `LP_plus_lpf` := largest odd prime on each side (1 if the
  side is a power of 2). This is the side's effective smoothness bound —
  a record is usable at factor-base bound B' only if both lpf ≤ B'.
- `LP_eligible` (summary-level) := p_is_prime ∧ LP_congruence_ok ∧ smooth_ok.

Interpretation: `LP_minus_omega + LP_plus_omega` is the record's *coloring
cost* — the number of prime-side assignments it consumes under the
side-coprimality lemma (working paper Lemma 2.3). The summary's
`side_compatibility` block reports, over all LP-eligible records, how many
distinct primes are demanded on each side and how many are demanded on *both*
sides by different records (`primes_demanded_on_both_sides`) — each such prime
forces a choice between the records using it, which is the pairwise shadow of
the global partition problem (working paper Question 5.1).

## Important distinction (do not conflate the corpora)

- **This corpus** (PTE): Costello–Meyer–Naehrig, EUROCRYPT 2021 — public code
  and results in `microsoft/twin-smooth-integers`; B = 2^16…2^28; twins of
  60–260 bits; ~20k records; sparse hits from polynomial evaluation.
- **The CHM corpus**: Bruno et al., ASIACRYPT 2023 (ePrint 2022/1439) —
  optimized Conrey–Holmström–McLaughlin; B = 547; 82,026,426 pairs, mostly
  ≤ 122 bits; **no public dump located**. Our compiled closure
  (`code/chm_closure.c`, validated: B=100 → 13,333/13,374 = 99.7% of the
  complete set with exact largest; B=113 max = published exhaustive record)
  is the current substitute.
