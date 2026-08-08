#!/usr/bin/env python3
"""A6 small-prime odd-part solver + G3 re-attempt.

Co-design (A5) shrank the solver group's odd-prime support to ~24 primes <= 97.
This tests whether that regime is actually solvable: subset-sum
    find x in {0,1}^N, sum_p x_p v_p = t in G = (2-part) x (odd part),
with the odd part supported on small primes, pool N >> dim, |S| odd.

Solver:
  * 2-part: exact GF(2) linear algebra (scales to any dimension) -> a huge
    affine family of 0/1 vectors all satisfying the mod-2^k constraints via
    bit-sliced Hensel rows.
  * odd part: guided local search / annealing WITHIN the GF(2) solution family
    (moves = XOR sparse GF(2)-kernel vectors, preserving the 2-part) to zero
    the odd residual.

G3 harness: faithful co-designed synthetic instances (small primes only) with
a PLANTED solution, at increasing odd dimension; report the success frontier.

RESULT (2026-08-08): G3 NOT passed. The 2-part solves by GF(2) at full scale.
The odd part is the obstruction, and it is DIMENSION not prime size:
  * annealing within the GF(2) family stalls at >=19 odd components (dense
    kernel moves are too disruptive);
  * exact meet-in-the-middle (mitm_frontier) solves small instances annealing
    cannot but is exponential in N, capping ~N=40 / ~15 odd components / ~40
    odd bits.
Both are 2-3 orders of magnitude below the co-designed spec (~thousands of odd
components, ~24k odd bits). Co-design capped the max odd prime (6269->97) but
not the odd dimension. The proven tool for subset-product = 1 in (Z/L)* at this
scale is the Loeh-Niebuhr / AGP CONSTRUCTIVE Carmichael algorithm (they build
Carmichael numbers with millions of prime factors); adapting it to our double
(Carmichael + Lucas-Carmichael) condition is the real next build.
"""
import math, random, sys, time
from phase1a_calibration import primes_upto

# ---- GF(2) solve returning particular solution + sparse-ish kernel ----

def gf2_solve(rows, rhs, ncols):
    piv = {}; reduced = []
    for mask, b in zip(rows, rhs):
        m, bb = mask, b
        for pc in list(piv):
            if (m >> pc) & 1:
                pm, pb = piv[pc]; m ^= pm; bb ^= pb
        if m == 0:
            if bb:
                return None
            continue
        pc = (m & -m).bit_length() - 1
        piv[pc] = (m, bb); reduced.append(pc)
    x0 = 0
    for pc in reduced:
        m, bb = piv[pc]
        if bb:
            x0 |= (1 << pc)
    pivcols = set(piv)
    kernel = []
    for fc in range(ncols):
        if fc in pivcols:
            continue
        kv = 1 << fc
        for pc in reduced:
            m, _ = piv[pc]
            if (m >> fc) & 1:
                kv |= (1 << pc)
        kernel.append(kv)
    return x0, kernel, sorted(pivcols)

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
    D = len(orders)
    two_idx = [j for j in range(D) if comps[j][0] == 2]
    odd_idx = [j for j in range(D) if comps[j][0] != 2]
    # ---- 2-part: GF(2) on lowest bit of each 2-component + higher bits via
    # bit-sliced rows; plus parity row ----
    rows, rhs = [], []
    for j in two_idx:
        a = orders[j].bit_length() - 1        # 2^a
        for bit in range(a):                  # Hensel bit-slices
            mask = 0
            for i in range(N):
                if (pool[i][j] >> bit) & 1:
                    mask |= (1 << i)
            rows.append(mask); rhs.append((t[j] >> bit) & 1)
    rows.append((1 << N) - 1); rhs.append(1)   # parity |S| odd
    sol = gf2_solve(rows, rhs, N)
    if sol is None:
        return None, "2-part inconsistent"
    x0, kernel, _ = sol
    if not odd_idx:
        return x0, "ok (2-part only)"

    # ---- odd part: local search within the GF(2) solution family ----
    def odd_resid(xbits):
        acc = [0] * len(odd_idx)
        xi, i = xbits, 0
        while xi:
            if xi & 1:
                for k, j in enumerate(odd_idx):
                    acc[k] = (acc[k] + pool[i][j]) % orders[j]
            xi >>= 1; i += 1
        return [(t[odd_idx[k]] - acc[k]) % orders[odd_idx[k]]
                for k in range(len(odd_idx))]
    def phi(res):
        return sum(1 for r in res if r != 0)
    x = x0
    res = odd_resid(x)
    cur = phi(res)
    t0 = time.time()
    K = kernel
    temp = max(2.0, cur / 4)
    best = cur
    while cur > 0 and time.time() - t0 < time_budget:
        kv = K[rng.randrange(len(K))]
        # incremental: XOR kv flips bits; recompute odd residual delta
        nx = x ^ kv
        nres = odd_resid(nx)     # recompute (dense kv -> full recompute)
        nc = phi(nres)
        if nc <= cur or rng.random() < math.exp(-(nc - cur) / temp):
            x, res, cur = nx, nres, nc
            best = min(best, cur)
        temp *= 0.9999
        if temp < 0.05:
            temp = max(1.0, cur / 4)   # reheat
    if cur == 0:
        return x, "ok"
    return None, f"odd unsolved (phi={cur}/{len(odd_idx)}, best={best})"

def mitm_frontier(orders, pool, t, N, time_budget=15):
    """Exact meet-in-the-middle over the whole pool (feasible only for small N).
    Establishes the EXACT-method frontier: solves small instances annealing
    cannot, but is exponential in N so caps ~N=40 regardless of prime size.
    Returns (solution_bits, msg)."""
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
    t0 = time.time()
    left = {}
    for combo in subsets(range(half)):
        acc = [0] * D
        for i in combo:
            for j in range(D):
                acc[j] = (acc[j] + pool[i][j]) % orders[j]
        left.setdefault(tuple(acc), combo)
    for combo in subsets(range(half, N)):
        if time.time() - t0 > time_budget:
            return None, "timeout"
        acc = [0] * D
        for i in combo:
            for j in range(D):
                acc[j] = (acc[j] + pool[i][j]) % orders[j]
        need = tuple((t[j] - acc[j]) % orders[j] for j in range(D))
        if need in left:
            xb = 0
            for i in set(left[need]) | set(combo):
                xb |= (1 << i)
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
    print("G3 re-attempt: small-prime odd-part solver (t0=97), planted "
          "faithful instances")
    print(f"{'#fbprimes':>10}{'D comps':>9}{'odd comps':>10}{'odd bits':>9}"
          f"{'N':>7}{'result':>28}{'verif':>7}{'sec':>7}")
    for nfp in [8, 16, 30, 60, 120]:
        comps, orders, pool, t, S = make_codesigned(nfp, 97, N=max(200, 20*nfp),
                                                    planted_k=max(11, nfp//2),
                                                    rng=rng, ps=ps)
        N = len(pool)
        odd = [j for j in range(len(orders)) if comps[j][0] != 2]
        oddbits = sum(math.log2(orders[j]) for j in odd)
        t0 = time.time()
        x, msg = solve(comps, orders, pool, t, N, rng, time_budget=20)
        dt = time.time() - t0
        ok = x is not None and verify(x, orders, pool, t)
        print(f"{nfp:>10}{len(orders):>9}{len(odd):>10}{oddbits:>9.0f}{N:>7}"
              f"{msg:>28}{str(ok):>7}{dt:>7.1f}")

if __name__ == "__main__":
    main()
