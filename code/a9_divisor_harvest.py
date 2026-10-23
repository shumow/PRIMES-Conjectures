#!/usr/bin/env python3
"""N1: finite squarefree-divisor harvest and side-support counts.

This script fixes disjoint factor bases T- and T+, enumerates squarefree
divisors m of prod(T-), and keeps
pool primes p = 2m+1 with:
    m = 1 (mod 40)                    [r=5 dictionary]
    2m+1 prime
    (m+1)/2 squarefree over T+        [Lucas side: p+1 | Lambda+]
The reported support fraction counts prime factors on BOTH sides. Minus-side
support gives p=1; plus-side support gives p=-1, not identity in the full unit
group. The latter is identity only after odd-order projection. This statistic
is not literal identity density across the cyclic prime-power components.
Finite trials do not prove general unharvestability.
"""
import math, sys
from itertools import combinations
from phase1a_calibration import primes_upto, is_prime

def factor_set_over(n, allowed):
    """Return set of prime factors of n if all are in `allowed` and n is
    squarefree over them; else None."""
    fs = set()
    for q in allowed:
        if n % q == 0:
            fs.add(q); n //= q
            if n % q == 0:
                return None            # not squarefree
        if n == 1:
            break
    return fs if n == 1 else None

def enum_products(primes, maxbits):
    """Yield (m, subset) for squarefree products m of `primes` with m <= 2^maxbits.
    DFS to keep it bounded."""
    primes = sorted(primes)
    def rec(i, cur, chosen):
        yield cur, chosen
        for j in range(i, len(primes)):
            nv = cur * primes[j]
            if nv.bit_length() > maxbits:
                break
            yield from rec(j + 1, nv, chosen + [primes[j]])
    yield from rec(0, 1, [])

def harvest(Tminus, Tplus, maxbits):
    pool = []
    scanned = 0
    for m, subset in enum_products(Tminus, maxbits):
        scanned += 1
        if m % 40 != 1 or m == 1:
            continue
        half = (m + 1) // 2
        fp = factor_set_over(half, Tplus)
        if fp is None:
            continue
        if not is_prime(2 * m + 1):
            continue
        omega_support = len(subset) + len(fp)
        pool.append((m, len(subset), len(fp), omega_support))
    return pool, scanned

def main():
    ps = primes_upto(2000)
    print("N1: finite divisor harvest and side-support fraction (not identity density)")
    print(f"{'T- bnd':>7}{'T+ rng':>12}{'|T-|':>5}{'|T+|':>5}{'maxbit':>7}"
          f"{'scan':>9}{'pool':>6}{'meanSupF':>9}{'maxSupF':>8}{'maxSup':>7}")
    configs = [
        (90, (97, 220), 48),
        (90, (97, 220), 60),
        (150, (160, 400), 56),
        (150, (160, 400), 68),
        (300, (310, 900), 64),
        (60, (67, 160), 56),
    ]
    for (tmb, (plo, phi), mb) in configs:
        Tminus = [q for q in ps if 3 <= q <= tmb and q != 5]
        Tplus = [q for q in ps if plo <= q <= phi]
        pool, scanned = harvest(Tminus, Tplus, mb)
        D = len(Tminus) + len(Tplus)
        if pool:
            dens = [o / D for *_, o in pool]
            md = sum(dens) / len(dens)
            print(f"{tmb:>7}{f'{plo}-{phi}':>12}{len(Tminus):>5}{len(Tplus):>5}"
                  f"{mb:>7}{scanned:>9}{len(pool):>6}{md:>9.3f}"
                  f"{max(dens):>8.3f}{max(o for *_,o in pool):>7}")
        else:
            print(f"{tmb:>7}{f'{plo}-{phi}':>12}{len(Tminus):>5}{len(Tplus):>5}"
                  f"{mb:>7}{scanned:>9}{0:>6}{'--':>9}{'--':>8}{'--':>7}")

if __name__ == "__main__":
    main()
