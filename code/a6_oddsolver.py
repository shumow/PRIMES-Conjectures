#!/usr/bin/env python3
"""A6 small-prime odd-part solver + G3 re-attempt.

Co-design (A5) shrank the solver group's odd-prime support to ~24 primes <= 97.
This tests whether that regime is actually solvable: subset-sum
    find x in {0,1}^N, sum_p x_p v_p = t in G = (2-part) x (odd part),
with the odd part supported on small primes, pool N >> dim, |S| odd.

Solver:
  * GF(2) projection: exact linear algebra plus odd-cardinality parity.
  * Residual: guided local search within that affine family, checking BOTH odd
    components and higher 2-powers with carries in the original group.

G3 harness: synthetic groups with co-designed component orders and a planted
solution. Uniform residues do not reproduce harvested prime-vector structure.

The 2026-08-08 frontier observations in data/FINDINGS.md predate the 2026-10-22
elimination, carry and parity corrections. They are preserved historical
observations, not validated limits of the corrected implementation.
"""
import math, random, sys, time
from phase1a_calibration import primes_upto
from a4_solver import gf2_solve as _gf2_solve, solve_mod2

def gf2_solve(rows, rhs, ncols):
    """Compatibility entry point returning x0, kernel and sorted pivot columns."""
    result = _gf2_solve(rows, rhs, ncols)
    if result is None:
        return None
    x0, kernel = result
    # A4 uses lowest-bit pivots; each kernel vector's highest bit is its free column.
    free_columns = {vector.bit_length() - 1 for vector in kernel}
    pivots = [column for column in range(ncols) if column not in free_columns]
    return x0, kernel, pivots

# ---- faithful co-designed instance ----

def ppf(n):
    f = {}; d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1; n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f

def make_codesigned(n_factor_primes, t0, N, planted_k, rng, ps):
    """Faithful instance: pick n_factor_primes primes q (odd part of q-1
    t0-smooth) and build cyclic prime-power components from q-1. Each pool
    element gets uniform-random residues. Plant an odd-size solution."""
    cand = [q for q in ps if q > 50 and all(
        l <= t0 for l in ppf(q - 1) if l != 2)]
    qs = rng.sample(cand, min(n_factor_primes, len(cand)))
    comps = []            # (prime l, modulus l^a)
    for q in qs:
        for l, a in ppf(q - 1).items():
            comps.append((l, l ** a))
    orders = [m for (_, m) in comps]
    D = len(orders)
    pool = [[rng.randrange(o) for o in orders] for _ in range(N)]
    if planted_k % 2 == 0:
        planted_k += 1
    S = rng.sample(range(N), planted_k)
    t = [0] * D
    for i in S:
        for j, o in enumerate(orders):
            t[j] = (t[j] + pool[i][j]) % o
    return comps, orders, pool, t, set(S)

# ---- solver ----

def col_bit(pool, i, j):
    return pool[i][j] & 1

def solve(comps, orders, pool, t, N, rng, time_budget):
    residual_idx = [j for j, o in enumerate(orders) if o % 2 or o > 2]
    sol = solve_mod2(pool, orders, t, N)
    if sol is None:
        return None, "mod2 inconsistent"
    x0, kernel = sol
    def residual(xbits):
        acc = [0] * len(residual_idx)
        xi, i = xbits, 0
        while xi:
            if xi & 1:
                for k, j in enumerate(residual_idx):
                    acc[k] = (acc[k] + pool[i][j]) % orders[j]
            xi >>= 1; i += 1
        return [(t[j] - acc[k]) % orders[j] for k, j in enumerate(residual_idx)]
    def phi(res):
        return sum(1 for r in res if r != 0)
    x = x0
    res = residual(x)
    cur = phi(res)
    if cur and not kernel:
        return None, "unique mod2 solution misses residual"
    t0 = time.monotonic()
    K = kernel
    temp = max(2.0, cur / 4)
    best = cur
    while cur > 0 and time.monotonic() - t0 < time_budget:
        kv = K[rng.randrange(len(K))]
        nx = x ^ kv
        nres = residual(nx)
        nc = phi(nres)
        if nc <= cur or rng.random() < math.exp(-(nc - cur) / temp):
            x, res, cur = nx, nres, nc
            best = min(best, cur)
        temp *= 0.9999
        if temp < 0.05:
            temp = max(1.0, cur / 4)   # reheat
    if cur == 0:
        assert verify(x, orders, pool, t), "local search returned an invalid solution"
        return x, "ok"
    return None, f"residual search unclosed (phi={cur}/{len(residual_idx)}, best={best})"

def mitm_frontier(orders, pool, t, N, time_budget=15):
    """Exact meet-in-the-middle over the whole pool (feasible only for small N).
    Includes odd-cardinality parity. Exhausted means no solution in this pool;
    timeout/resource-limit outcomes are inconclusive. Returns (bits, msg).
    """
    from itertools import combinations
    D = len(orders)
    if N > 44:
        return None, "N too large for direct MITM"
    half = N // 2
    def subsets(idxs):
        idxs = list(idxs)
        for r in range(len(idxs) + 1):
            for c in combinations(idxs, r):
                yield c
    t0 = time.monotonic()
    left = {}
    for combo in subsets(range(half)):
        if time.monotonic() - t0 > time_budget:
            return None, "timeout"
        acc = [0] * D
        for i in combo:
            for j in range(D):
                acc[j] = (acc[j] + pool[i][j]) % orders[j]
        left.setdefault(tuple(acc) + (len(combo) % 2,), combo)
    for combo in subsets(range(half, N)):
        if time.monotonic() - t0 > time_budget:
            return None, "timeout"
        acc = [0] * D
        for i in combo:
            for j in range(D):
                acc[j] = (acc[j] + pool[i][j]) % orders[j]
        need = tuple((t[j] - acc[j]) % orders[j] for j in range(D)) \
            + (1 - len(combo) % 2,)
        if need in left:
            xb = 0
            for i in set(left[need]) | set(combo):
                xb |= (1 << i)
            assert verify(xb, orders, pool, t), "MITM returned an invalid solution"
            return xb, "ok"
    return None, "exhausted"

def verify(xbits, orders, pool, t):
    acc = [0] * len(orders)
    xi, i = xbits, 0
    while xi:
        if xi & 1:
            for j, o in enumerate(orders):
                acc[j] = (acc[j] + pool[i][j]) % o
        xi >>= 1; i += 1
    return all(acc[j] == t[j] % orders[j] for j in range(len(orders))) \
        and bin(xbits).count("1") % 2 == 1

def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 11)
    ps = primes_upto(4000)
    print("G3 re-attempt: residual solver (t0=97), planted synthetic groups")
    print(f"{'#fbprimes':>10}{'D comps':>9}{'res comps':>10}{'res bits':>9}"
          f"{'N':>7}{'result':>28}{'verif':>7}{'sec':>7}")
    for nfp in [8, 16, 30, 60, 120]:
        comps, orders, pool, t, S = make_codesigned(nfp, 97, N=max(200, 20*nfp),
                                                    planted_k=max(11, nfp//2),
                                                    rng=rng, ps=ps)
        N = len(pool)
        residual = [j for j, o in enumerate(orders) if o % 2 or o > 2]
        residual_bits = sum(math.log2(orders[j]) - (orders[j] % 2 == 0)
                            for j in residual)
        t0 = time.time()
        x, msg = solve(comps, orders, pool, t, N, rng, time_budget=20)
        dt = time.time() - t0
        ok = x is not None and verify(x, orders, pool, t)
        print(f"{nfp:>10}{len(orders):>9}{len(residual):>10}{residual_bits:>9.0f}{N:>7}"
              f"{msg:>28}{str(ok):>7}{dt:>7.1f}")

if __name__ == "__main__":
    main()
