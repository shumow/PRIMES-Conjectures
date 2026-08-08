#!/usr/bin/env python3
"""A5 harvest/solver co-design study.

The A4 bottleneck: ~84% of the solver group's bits are odd-prime components,
from the odd factors of (q-1) over the factor-base primes q in Q- and Q+, with
odd primes l up to ~6269. Co-design idea: restrict the factor base to primes q
whose (q-1) odd part is t0-smooth, capping the max odd prime at t0 and shrinking
the odd-part to a small prime support -> potentially solver-tractable. Cost: a
density hit on the factor base -> lower harvest yield.

This script CHARACTERIZES the tradeoff (cheap; no sampling): as t0 varies,
report factor-base retention, group odd-part stats (max odd prime, #distinct
odd primes, odd bits, 2-part bits), and the combinatorial yield proxy
(C(t_minus, j), the dominant yield factor). Decides whether co-design can
close before we invest in full yield sampling.
"""
import math, sys
from phase1a_calibration import primes_upto

def prime_power_factors(n):
    f = {}
    d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1; n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f

def odd_smooth_ok(q, t0):
    """True if every odd prime factor of q-1 is <= t0."""
    n = q - 1
    while n % 2 == 0:
        n //= 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            if d > t0:
                return False
            while n % d == 0:
                n //= d
        d += 2
    return n == 1 or n <= t0

def group_stats(factorbase):
    odd_primes = {}
    two_bits = 0
    odd_bits = 0.0
    for q in factorbase:
        for l, a in prime_power_factors(q - 1).items():
            if l == 2:
                two_bits += a
            else:
                odd_primes[l] = odd_primes.get(l, 0) + a
                odd_bits += a * math.log2(l)
    return dict(max_odd=max(odd_primes) if odd_primes else 0,
                n_distinct_odd=len(odd_primes),
                odd_bits=odd_bits, two_bits=two_bits)

def main():
    B = int(sys.argv[1]) if len(sys.argv) > 1 else 1259
    Bp = int(sys.argv[2]) if len(sys.argv) > 2 else 12590
    j = 4
    ps = primes_upto(Bp)
    Qminus_all = [q for q in ps if B < q <= Bp]
    Qplus_all = [q for q in ps if 2 < q <= B and q != 5]
    t_all = len(Qminus_all)

    print(f"Frozen band B={B} B'={Bp}: |Q-|={t_all}, |Q+|={len(Qplus_all)}")
    print(f"{'t0':>6}{'|Q-|':>7}{'retain':>7}{'maxodd':>8}{'#odd':>6}"
          f"{'oddbits':>9}{'2bits':>7}{'log2C(t,4)':>11}{'yield vs full':>14}")
    full_logC = None
    for t0 in [20, 30, 50, 100, 200, 500, 1000, 10**9]:
        Qm = [q for q in Qminus_all if odd_smooth_ok(q, t0)]
        Qp = [q for q in Qplus_all if odd_smooth_ok(q, t0)]
        if len(Qm) < j:
            print(f"{t0:>6}{len(Qm):>7}  (too few)")
            continue
        gs = group_stats(Qm + Qp)
        t = len(Qm)
        logC = (math.lgamma(t + 1) - math.lgamma(j + 1)
                - math.lgamma(t - j + 1)) / math.log(2)
        if full_logC is None and t0 >= 10**9:
            full_logC = logC
        label = "inf" if t0 >= 10**9 else str(t0)
        yield_ratio = ""
        print(f"{label:>6}{t:>7}{100*t/t_all:>6.0f}%{gs['max_odd']:>8}"
              f"{gs['n_distinct_odd']:>6}{gs['odd_bits']:>9.0f}"
              f"{gs['two_bits']:>7}{logC:>11.1f}{'':>14}")
    # yield vs full at each t0 (relative C(t,4)), recomputed for clarity
    print("\nYield proxy = C(t_constrained,4)/C(t_full,4) (dominant harvest "
          "factor; side-smoothness rate change not included here):")
    Qm_full = Qminus_all
    logC_full = (math.lgamma(len(Qm_full)+1) - math.lgamma(j+1)
                 - math.lgamma(len(Qm_full)-j+1)) / math.log(2)
    for t0 in [20, 30, 50, 100, 200, 500, 1000]:
        Qm = [q for q in Qminus_all if odd_smooth_ok(q, t0)]
        if len(Qm) < j:
            continue
        logC = (math.lgamma(len(Qm)+1) - math.lgamma(j+1)
                - math.lgamma(len(Qm)-j+1)) / math.log(2)
        print(f"  t0={t0:>5}: C-ratio = 2^{logC-logC_full:.1f} "
              f"= {2**(logC-logC_full):.2e}")

if __name__ == "__main__":
    main()
