# Raw upstream data: microsoft/twin-smooth-integers (PTE sieve results)

- **Upstream repository:** https://github.com/microsoft/twin-smooth-integers
- **Upstream commit:** `f1b9a5275098565d5407d2ad869f8a34d49e6f69` (shallow clone,
  retrieved 2026-08-07)
- **Upstream path:** `pte_sieve/results/*.txt` (13 files, ~3.4 MB; the
  `read_results.sage` reader script was not copied — see upstream for it)
- **License:** MIT (Microsoft Corporation) — copy in `UPSTREAM-LICENSE`.
- **Integrity:** `SHA256SUMS` covers all 13 `.txt` files as retrieved.

## What this data is

Search output of the **Prouhet–Tarry–Escott (PTE) sieve** of Costello–Meyer–
Naehrig, *Sieving for twin smooth integers with solutions to the
Prouhet–Tarry–Escott problem* (EUROCRYPT 2021). Each line records a hit
`(solution_id, x, PTE root sets A and B, p, p prime?)` where p = 2m+1 and
(m, m+1) is a twin B-smooth pair produced by evaluating the PTE polynomial
pair at x. File-name convention `size-<deg>[-squ]_<log2 B>_<xlo>_to_<xhi>.txt`
gives the PTE degree, smoothness bound B = 2^(log2 B), and the searched
x-interval.

## What this data is NOT

This is **not** the CHM corpus of Bruno et al., *Cryptographic Smooth
Neighbors* (ASIACRYPT 2023, ePrint 2022/1439). That work used an optimized
Conrey–Holmström–McLaughlin algorithm and reports 82,026,426 twin pairs at
B = 547; **no public dump of that corpus has been located**. The two datasets
come from different algorithms, different smoothness regimes (B = 2^16–2^28
here vs B = 547 there), and different size regimes (60–260-bit twins here vs
mostly ≤ 122-bit there). Do not conflate them.

Normalized/derived records are generated into `data/generated/` by
`code/import_pte_results.py`; every generated record carries
`source_result_filename` tracing back to a file listed in `SHA256SUMS`.
