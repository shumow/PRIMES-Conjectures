# Twin Smooth Integers / Smooth Neighbors --- Dataset & Resource Notes

*Last checked: 2026-08-06*

## Important correction

In the preceding conversation I said that I had found a **Zenodo dataset
containing the complete set of 200-smooth twin pairs** and a linked
GitHub implementation. I have **not been able to verify that claim**, so
it should not be treated as established. I am recording the verified
resources below instead.

## Cryptographic Smooth Neighbors

**Paper:** *Cryptographic Smooth Neighbors*\
**Authors:** Giacomo Bruno, Maria Corte-Real Santos, Craig Costello,
Jonathan Komada Eriksen, Michael Meyer, Michael Naehrig, Bruno Sterner\
**Conference:** ASIACRYPT 2023\
**Cryptology ePrint:** 2022/1439\
**ePrint URL:** https://eprint.iacr.org/2022/1439\
**Microsoft Research page:**
https://www.microsoft.com/en-us/research/publication/cryptographic-smooth-neighbors/

### What it does

The paper revisits the Conrey--Holmstrom--McLaughlin (CHM)
smooth-neighbors algorithm for finding consecutive integers

\[ (r,r+1) \]

such that both integers are (B)-smooth. The authors give an optimized
implementation of CHM. The method is not exhaustive in principle, but
the authors report that in practice it obtains a very close
approximation to the complete set while requiring much less computation
than exhaustive approaches.

The work uses these searches both for the pure twin-smooth problem and
for constructing smoother parameters useful in isogeny-based
cryptography, particularly SQISign.

### Data actually present in the paper

The paper contains concrete smooth-neighbor examples and tables of
record-sized solutions/cryptographic parameters. These are therefore
immediately usable as a small, published reference set even if a
separate bulk-data archive cannot be located.

For machine-readable work, the tables in the ePrint version are the
first source I would extract and normalize.

## Earlier Costello--Meyer--Naehrig work

**Paper:** *Sieving for Twin Smooth Integers with Solutions to the
Prouhet--Tarry--Escott Problem*\
**Authors:** Craig Costello, Michael Meyer, Michael Naehrig\
**EUROCRYPT 2021**\
**DOI:** 10.1007/978-3-030-77870-5_10

This gives a different sieving approach based on solutions to the
Prouhet--Tarry--Escott problem. A PTE solution produces two split
polynomials whose values can be used to generate candidate consecutive
smooth integers.

Microsoft Research lists this publication on Michael Naehrig's
publication page:
https://www.microsoft.com/en-us/research/people/mnaehrig/publications/

## Original CHM algorithm

**Paper:** *Smooth Neighbors*\
**Authors:** Brian Conrey, Mark Holmstrom, Tara McLaughlin\
**arXiv:** 1212.5161\
**URL:** https://arxiv.org/abs/1212.5161

This is the original CHM algorithm referred to by the later
cryptographic smooth-neighbor work.

## Related Pell-equation work

**Paper:** *Finding twin smooth integers by solving Pell equations*\
**Authors:** Jan Buzek, Junaid Hasan, Jason Liu, Michael Naehrig,
Anthony Vigil\
**arXiv:** 2211.04315\
**URL:** https://arxiv.org/abs/2211.04315

This explores a different way of searching for twin (B)-smooth integers
by exploiting the Pell-equation structure associated with smooth
neighbors. It reports examples of twin smooth pairs with improved
size/smoothness characteristics.

## Useful explanatory source

Maria Corte-Real Santos wrote an accessible technical overview of
*Cryptographic Smooth Neighbors*:

https://www.mariascrs.com/2022/10/24/twinsmooths.html

It explains the (B)-smooth-neighbor problem, its cryptographic
motivation, and the relationship to the CHM algorithm.

## Next data-recovery targets

The useful next step is to locate or reconstruct small machine-readable
datasets from:

1.  Tables and appendices of **Cryptographic Smooth Neighbors** (ePrint
    2022/1439).
2.  Supplementary material or author repositories associated with that
    paper.
3.  Tables/examples in the **PTE sieving** paper.
4.  Tables/examples in the **Pell-equation** paper.
5.  Any surviving implementation or data files from the original CHM
    work.
6.  Author GitHub pages/repositories and archived versions thereof.

A practical deliverable would be a CSV/JSON/SQLite file with fields such
as:

-   `B`
-   `n`
-   `n_plus_1`
-   factorization of `n`
-   factorization of `n+1`
-   bit length
-   source paper
-   algorithm
-   completeness/status
-   source table/record

That would give a small verified corpus against which a new
implementation or other analysis can be tested.
