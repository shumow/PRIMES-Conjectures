#!/usr/bin/env python3
"""A5 co-designed yield: measure the REAL harvest ratio when BOTH factor bases
are constrained to odd-smooth-shifted primes (odd part of q-1 <= t0), which
caps the solver group's max odd prime at t0. Decides whether co-design keeps
ratio above the G2 gate while making the solver tractable.
"""
import math, random, sys
from phase1a_calibration import primes_upto, is_prime

def odd_smooth_ok(q, t0):
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

def ppf(n):
    f = {}; d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1; n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f

def run(B, Bp, j, t0, N, rng):
    ps = primes_upto(Bp)
    Qminus = [q for q in ps if B < q <= Bp and odd_smooth_ok(q, t0)]
    Qplus = [q for q in ps if 2 < q <= B and q != 5 and odd_smooth_ok(q, t0)]
    Qplus_set = set(Qplus)
    t = len(Qminus)
    if t < j:
        return None
    hits = 0
    used_minus = set()
    used_plus_primes = {}
    for _ in range(N):
        qs = rng.sample(Qminus, j)
        m = 1
        for q in qs:
            m *= q
        if m % 40 != 1:
            continue
        v = (m + 1) // 2
        # (m+1)/2 must be smooth over the CONSTRAINED Q+ (odd-smooth primes)
        for q in Qplus:
            while v % q == 0:
                v //= q
            if v == 1:
                break
        if v != 1:
            continue
        if not is_prime(2 * m + 1):
            continue
        hits += 1
        used_minus.update(qs)
    rate = hits / N
    logC = (math.lgamma(t + 1) - math.lgamma(j + 1)
            - math.lgamma(t - j + 1)) / math.log(2)
    proj_pool = 2 ** logC * rate
    # group / demand & odd stats over BOTH constrained factor bases
    odd_primes = {}; two_bits = 0; odd_bits = 0.0
    for q in Qminus + Qplus:
        for l, a in ppf(q - 1).items():
            if l == 2:
                two_bits += a
            else:
                odd_primes[l] = odd_primes.get(l, 0) + a
                odd_bits += a * math.log2(l)
    demand = two_bits + odd_bits
    return dict(B=B, Bp=Bp, j=j, t0=t0, tQm=t, tQp=len(Qplus), hits=hits,
                rate=rate, proj_pool=proj_pool, demand=round(demand),
                odd_bits=round(odd_bits), two_bits=two_bits,
                max_odd=max(odd_primes) if odd_primes else 0,
                n_distinct_odd=len(odd_primes),
                ratio=round(proj_pool / demand, 2))

def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 12_000_000
    rng = random.Random(0x5D)
    cells = [
        (1259, 40060, 4, 50),
        (1259, 40060, 4, 100),
        (1259, 40060, 4, 200),
        (2003, 60090, 4, 100),
        (631, 40060, 4, 50),
    ]
    print(f"{'B':>6}{'Bp':>7}{'j':>3}{'t0':>5}{'tQ-':>6}{'tQ+':>5}"
          f"{'hits':>6}{'ratio':>8}{'pool':>10}{'demand':>8}{'maxodd':>7}"
          f"{'#odd':>6}")
    out = []
    for (B, Bp, j, t0) in cells:
        r = run(B, Bp, j, t0, N, rng)
        if r is None:
            continue
        out.append(r)
        print(f"{r['B']:>6}{r['Bp']:>7}{r['j']:>3}{r['t0']:>5}{r['tQm']:>6}"
              f"{r['tQp']:>5}{r['hits']:>6}{r['ratio']:>8.1f}"
              f"{r['proj_pool']:>10.2g}{r['demand']:>8}{r['max_odd']:>7}"
              f"{r['n_distinct_odd']:>6}")
    import json, os
    GEN = os.path.join(os.path.dirname(__file__), "..", "data", "generated")
    with open(os.path.join(GEN, "a5_codesign_yield.json"), "w") as f:
        json.dump(out, f, indent=1)

if __name__ == "__main__":
    main()
