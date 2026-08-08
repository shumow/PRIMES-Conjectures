#!/usr/bin/env python3
"""A4 subset-product solver — prototype + G3 synthetic scaling study.

The counterexample condition (n = prod_{p in S} p with n = 1 mod Lambda-,
n = -1 mod Lambda+, |S| odd) linearizes by discrete logs into a subset-sum in
the finite abelian group G = (Z/Lambda-)* x (Z/Lambda+)*:

    find x in {0,1}^N with  sum_p x_p * v_p = t  in G,  sum_p x_p = 1 (mod 2).

G decomposes (CRT + Pohlig-Hellman, all component orders smooth) into cyclic
prime-power components Z/l^a. This is subset-sum in an abelian group with
pool N >> dim, so solutions are super-dense; the difficulty is finding a 0/1
one (NP-hard in general, tractable here only via structure).

STRUCTURAL DECOMPOSITION (the key to a scalable solver):
  * The projection of every constraint mod 2 is GF(2)-LINEAR in x (since
    x in {0,1} = GF(2)). So the entire 2-torsion image G/2G is solved exactly
    and at full scale by GF(2) Gaussian elimination -- and this is the bulk of
    the demand bits (every q-1 is even, most heavily).
  * The residual (odd-prime components, and higher 2-power bits via Hensel
    lifting) is a smaller subset-sum handled by the GF(2) solution's huge
    kernel + a meet-in-the-middle over the odd part.

This file implements the GF(2) core (scales to full frozen-spec dimension),
verifies end-to-end correctness on small PLANTED faithful instances via a
meet-in-the-middle odd-part closer, and SIZES the odd residual at frozen-spec
scale -- the input that decides how much Wagner/MITM machinery A4-v2 needs.
"""
import math, random, sys, time
from phase1a_calibration import primes_upto

# ---------------- GF(2) linear algebra over bitset rows ----------------

def gf2_solve(rows, rhs, ncols):
    """Solve A x = b over GF(2). rows: list of int bitmasks (bit c set = A[r,c]=1);
    rhs: list of 0/1. Returns (x0 bitmask, list of kernel-basis bitmasks) or
    None if inconsistent. x0 is a particular solution; kernel basis spans the
    nullspace (each an int bitmask over columns)."""
    R = [(rows[i], rhs[i]) for i in range(len(rows))]
    pivot_col_of_row = []
    pivots = {}                              # col -> row index in reduced list
    reduced = []
    for (mask, b) in R:
        m, bb = mask, b
        for (pc, (pm, pb)) in pivots.items():
            if (m >> pc) & 1:
                m ^= pm; bb ^= pb
        if m == 0:
            if bb:
                return None                  # 0 = 1 inconsistent
            continue
        pc = (m & -m).bit_length() - 1       # lowest set bit as pivot
        pivots[pc] = (m, bb)
        reduced.append((pc, m, bb))
    # back-substitute to get a particular solution (free cols = 0)
    x0 = 0
    for (pc, m, bb) in reduced:
        val = bb
        mm = m ^ (1 << pc)
        # free columns are 0 in x0, so contribution from them is 0
        if val:
            x0 |= (1 << pc)
    # kernel basis: one vector per free column
    pivot_cols = set(pivots.keys())
    kernel = []
    for fc in range(ncols):
        if fc in pivot_cols:
            continue
        kv = 1 << fc
        for (pc, m, bb) in reduced:
            if (m >> fc) & 1:
                kv |= (1 << pc)
        kernel.append(kv)
    return x0, kernel

# ---------------- component structure ----------------

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

def components(Qminus, Qplus):
    """Cyclic prime-power components of prod (Z/q)* over Q- and Q+.
    Each (Z/q)* is cyclic of order q-1; split q-1 into prime powers."""
    comps = []
    for side, primes in (("-", Qminus), ("+", Qplus)):
        for q in primes:
            for l, a in prime_power_factors(q - 1).items():
                comps.append((side, q, l, a, l ** a))
    return comps

# ---------------- faithful synthetic instance ----------------

def make_instance(Qminus, Qplus, N, planted_k, rng):
    comps = components(Qminus, Qplus)
    orders = [c[4] for c in comps]
    pool = [[rng.randrange(o) for o in orders] for _ in range(N)]
    if planted_k % 2 == 0:
        planted_k += 1
    S = rng.sample(range(N), planted_k)
    t = [0] * len(orders)
    for i in S:
        for j, o in enumerate(orders):
            t[j] = (t[j] + pool[i][j]) % o
    return comps, orders, pool, t, set(S)

# ---------------- solver ----------------

def solve_mod2(pool, orders, t, N):
    """Solve the mod-2 projection: for every even-order component j,
    sum_p x_p * (v_pj mod 2) = t_j mod 2 over GF(2). Plus parity row.
    Returns (x0, kernel) over GF(2), or None."""
    rows, rhs = [], []
    for j, o in enumerate(orders):
        if o % 2 == 0:
            mask = 0
            for i in range(N):
                if pool[i][j] & 1:
                    mask |= (1 << i)
            rows.append(mask); rhs.append(t[j] & 1)
    # parity |S| odd
    rows.append((1 << N) - 1); rhs.append(1)
    return gf2_solve(rows, rhs, N)

def residual_after(x_bits, pool, orders, t, N):
    """Return list of (j, order, deficit) for components NOT yet satisfied by
    the 0/1 vector x_bits."""
    acc = [0] * len(orders)
    xi = x_bits
    i = 0
    while xi:
        if xi & 1:
            for j, o in enumerate(orders):
                acc[j] = (acc[j] + pool[i][j]) % o
        xi >>= 1; i += 1
    return [(j, orders[j], (t[j] - acc[j]) % orders[j])
            for j in range(len(orders)) if (t[j] - acc[j]) % orders[j] != 0]

def mitm_close(x0, kernel, pool, orders, t, N, odd_idx, rng, budget=200000):
    """Close the odd/high-power residual by XORing GF(2)-kernel basis vectors
    into x0 (each XOR keeps x in {0,1}), searching for a combination that
    zeroes the residual on odd_idx components. Meet-in-the-middle over a random
    subset of kernel vectors. Returns closing x_bits or None."""
    if not odd_idx:
        return x0
    K = kernel[:]
    rng.shuffle(K)
    # each kernel vector's effect on the odd residual coordinates
    def resid_vec(xbits):
        acc = [0] * len(odd_idx)
        xi, i = xbits, 0
        while xi:
            if xi & 1:
                for k, j in enumerate(odd_idx):
                    acc[k] = (acc[k] + pool[i][j]) % orders[j]
            xi >>= 1; i += 1
        return tuple((t[j] - acc[k]) % orders[j] for k, j in enumerate(odd_idx))
    base = resid_vec(x0)
    if all(v == 0 for v in base):
        return x0
    # effect of XORing kernel vector kv: delta on odd coords
    def delta(kv):
        d = [0] * len(odd_idx)
        xi, i = kv, 0
        while xi:
            if xi & 1:
                for k, j in enumerate(odd_idx):
                    d[k] = (d[k] + pool[i][j]) % orders[j]
            xi >>= 1; i += 1
        return d
    # NOTE XOR is not additive on residues (a bit already set flips off).
    # For a clean prototype we restrict to kernel vectors DISJOINT from x0's
    # support so XOR = OR = addition on those coords.
    use = [kv for kv in K if (kv & x0) == 0][:26]
    deltas = [delta(kv) for kv in use]
    half = len(use) // 2
    from itertools import combinations
    # meet in the middle: left combos vs right combos
    left = {}
    L, Rr = use[:half], use[half:]
    Ld, Rd = deltas[:half], deltas[half:]
    tgt = tuple((-b) % orders[odd_idx[k]] for k, b in enumerate(base))
    for r in range(len(L) + 1):
        if r > 6: break
        for combo in combinations(range(len(L)), r):
            acc = [0] * len(odd_idx)
            for c in combo:
                for k in range(len(odd_idx)):
                    acc[k] = (acc[k] + Ld[c][k]) % orders[odd_idx[k]]
            left.setdefault(tuple(acc), combo)
    for r in range(len(Rr) + 1):
        if r > 6: break
        for combo in combinations(range(len(Rr)), r):
            acc = [0] * len(odd_idx)
            for c in combo:
                for k in range(len(odd_idx)):
                    acc[k] = (acc[k] + Rd[c][k]) % orders[odd_idx[k]]
            need = tuple((tgt[k] - acc[k]) % orders[odd_idx[k]]
                         for k in range(len(odd_idx)))
            if need in left:
                xb = x0
                for c in left[need]:
                    xb ^= L[c]
                for c in combo:
                    xb ^= Rr[c]
                return xb
    return None

def full_solve(pool, orders, t, N, rng):
    r = solve_mod2(pool, orders, t, N)
    if r is None:
        return None, "mod2 inconsistent"
    x0, kernel = r
    odd_idx = [j for j, o in enumerate(orders)
               if o % 2 == 1 or o > 2]           # odd primes + higher 2-powers
    xb = mitm_close(x0, kernel, pool, orders, t, N, odd_idx, rng)
    if xb is None:
        return None, "odd residual unclosed"
    return xb, "ok"

def verify(x_bits, pool, orders, t):
    acc = [0] * len(orders)
    xi, i = x_bits, 0
    while xi:
        if xi & 1:
            for j, o in enumerate(orders):
                acc[j] = (acc[j] + pool[i][j]) % o
        xi >>= 1; i += 1
    ok = all(acc[j] == t[j] % orders[j] for j in range(len(orders)))
    parity = bin(x_bits).count("1") % 2
    return ok and parity == 1

# ---------------- G3 study ----------------

def study_correctness(rng):
    print("== end-to-end correctness on small PLANTED faithful instances ==")
    print(f"{'Q- band':>12}{'D':>5}{'dimbits':>8}{'oddbits':>8}{'N':>7}"
          f"{'solved':>8}{'verified':>9}{'sec':>7}")
    for (mb, pb, N, pk) in [((30, 60), (3, 30), 300, 25),
                            ((60, 110), (3, 60), 800, 40),
                            ((110, 200), (3, 110), 2000, 60)]:
        ps = primes_upto(2000)
        Qm = [q for q in ps if mb[0] < q <= mb[1]]
        Qp = [q for q in ps if pb[0] < q <= pb[1] and q != 5]
        comps, orders, pool, t, S = make_instance(Qm, Qp, N, pk, rng)
        dim = sum(math.log2(o) for o in orders)
        oddbits = sum(math.log2(o) for o in orders if o % 2 or o > 2)
        t0 = time.time()
        xb, msg = full_solve(pool, orders, t, N, rng)
        dt = time.time() - t0
        ver = xb is not None and verify(xb, pool, orders, t)
        print(f"{str(mb):>12}{len(comps):>5}{dim:>8.0f}{oddbits:>8.0f}{N:>7}"
              f"{msg:>8}{str(ver):>9}{dt:>7.1f}")

def study_mod2_scale(rng):
    print("\n== 2-part vs odd-part decomposition at frozen-spec scale ==")
    print(f"{'B':>6}{'B_prime':>9}{'comps':>7}{'dim bits':>9}{'2part bits':>11}"
          f"{'odd bits':>9}{'odd%':>6}{'maxodd_l':>9}{'gf2 sec':>8}")
    ps = primes_upto(20000)
    for (B, Bp) in [(547, 5470), (1259, 12590), (1259, 18885)]:
        Qm = [q for q in ps if B < q <= Bp]
        Qp = [q for q in ps if 2 < q <= B and q != 5]
        comps = components(Qm, Qp)
        orders = [c[4] for c in comps]
        dim = sum(math.log2(o) for o in orders)
        two_bits = sum(math.log2(o) for c, o in zip(comps, orders) if c[2] == 2)
        odd_bits = dim - two_bits
        max_odd = max((c[2] for c in comps if c[2] > 2), default=0)
        N = 4 * len(comps)
        pool = [[rng.randrange(o) for o in orders] for _ in range(N)]
        S = rng.sample(range(N), 2 * (N // 8) + 1)
        t = [0] * len(orders)
        for i in S:
            for j, o in enumerate(orders):
                t[j] = (t[j] + pool[i][j]) % o
        t0 = time.time()
        r = solve_mod2(pool, orders, t, N)
        dt = time.time() - t0
        print(f"{B:>6}{Bp:>9}{len(comps):>7}{dim:>9.0f}{two_bits:>11.0f}"
              f"{odd_bits:>9.0f}{100*odd_bits/dim:>5.0f}%{max_odd:>9}{dt:>8.1f}")

def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    study_correctness(rng)
    study_mod2_scale(rng)

if __name__ == "__main__":
    main()
