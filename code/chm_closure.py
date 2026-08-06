#!/usr/bin/env python3
"""CHM (Conrey-Holmstrom-McLaughlin) closure experiment.

The CHM iteration: given twin smooth pairs (r, r+1) and (s, s+1) with r < s,
let d = s - r, a = r(s+1), b = s(r+1) = a + d. If d | a then
(a/d, a/d + 1) is a new pair of consecutive integers whose entries divide
products of smooth numbers -- both B-smooth -- i.e., a new twin.
Iterating to (approximate) closure from a seed set approximates the full
(Stormer-finite) set of twin B-smooths, with no size cap X.

We use a bounded-pair-window variant for speed and iterate until no new
twins are found. Then we apply the dictionary filters (m = 1 mod 40,
2m+1 prime) and compare against the X-bounded harvest.

Usage: python3 chm_closure.py [B] [seedX] [window]
"""
import sys, math
from phase1a_calibration import primes_upto, smooth_upto, is_prime, odd_prime_factors

def main():
    B = int(sys.argv[1]) if len(sys.argv) > 1 else 113
    seedX = int(sys.argv[2]) if len(sys.argv) > 2 else 10**7
    W = int(sys.argv[3]) if len(sys.argv) > 3 else 4000  # pair window (by index)
    ps = primes_upto(B)
    sm = smooth_upto(ps, seedX)
    seeds = {sm[i] for i in range(len(sm) - 1) if sm[i + 1] == sm[i] + 1}
    print(f"B={B}: seed twins (m <= {seedX:.0e}): {len(seeds)}")

    twins = set(seeds)
    frontier = sorted(twins)
    rounds = 0
    while frontier:
        rounds += 1
        all_sorted = sorted(twins)
        idx = {m: i for i, m in enumerate(all_sorted)}
        new = set()
        for r in frontier:
            i = idx[r]
            lo, hi = max(0, i - W), min(len(all_sorted), i + W + 1)
            for j in range(lo, hi):
                s = all_sorted[j]
                if s == r:
                    continue
                rr, ss = (r, s) if r < s else (s, r)
                d = ss - rr
                a = rr * (ss + 1)
                if a % d == 0:
                    m = a // d
                    if m not in twins and m not in new:
                        new.add(m)
        twins |= new
        print(f"  round {rounds}: +{len(new)} new twins (total {len(twins)})")
        frontier = sorted(new)
        if rounds >= 12:
            print("  (round cap reached)")
            break

    mx = max(twins)
    print(f"closure: {len(twins)} twins; largest has {mx.bit_length()} bits")

    slice40 = [m for m in sorted(twins) if m % 40 == 1]
    pool = [m for m in slice40 if is_prime(2 * m + 1)]
    print(f"after m = 1 (mod 40): {len(slice40)}; after 2m+1 prime: {len(pool)}")

    # size histogram of pool
    from collections import Counter
    hist = Counter(m.bit_length() // 10 for m in pool)
    print("pool size histogram (bits//10):",
          dict(sorted(hist.items())))

    # demand ceiling for the whole universe at this B (exponents from pool usage)
    used = {}
    for m in pool:
        for q, e in odd_prime_factors(m, ps).items():
            used[q] = max(used.get(q, 0), e)
        for q, e in odd_prime_factors((m + 1) // 2, ps).items():
            used[q] = max(used.get(q, 0), e)
    demand = sum(e * math.log2(q) for q, e in used.items()) + 3
    print(f"pool {len(pool)} vs full-universe demand ~{demand:.0f} bits; "
          f"ratio {len(pool)/demand:.3f}")

if __name__ == "__main__":
    main()
