#!/usr/bin/env python3
"""A4 subset-product solver — prototype + G3 synthetic scaling study.

The counterexample condition (n = prod_{p in S} p with n = 1 mod Lambda-,
n = -1 mod Lambda+, |S| odd) linearizes by discrete logs into a subset-sum in
the finite abelian group G = (Z/Lambda-)* x (Z/Lambda+)*:

    find x in {0,1}^N with  sum_p x_p * v_p = t  in G,  sum_p x_p = 1 (mod 2).

G decomposes (CRT + Pohlig-Hellman, all component orders smooth) into cyclic
prime-power components Z/l^a. This is subset-sum in an abelian group with
pool N >> dim. Many solutions are expected under a uniform-subset-sum model;
the size inequality alone does not prove that the target is reachable.

STRUCTURAL DECOMPOSITION (the key to a scalable solver):
  * The projection of every constraint mod 2 is GF(2)-LINEAR in x (since
    x in {0,1} = GF(2)). So the entire 2-torsion image G/2G is solved exactly
    by GF(2) Gaussian elimination.
  * The residual includes odd-prime components AND higher 2-power constraints.
    Carries prevent treating the latter as independent GF(2) bit slices.

This file implements the GF(2) core (scales to full frozen-spec dimension),
checks small planted synthetic instances using bounded kernel enumeration, and
sizes the group at the frozen spec. These are group-structure models, not
discrete-log vectors harvested from actual primes.
"""
import math, random, sys, time
from phase1a_calibration import primes_upto

# ---------------- GF(2) linear algebra over bitset rows ----------------

def gf2_solve(rows, rhs, ncols):
    """Solve A x = b over GF(2). rows: list of int bitmasks (bit c set = A[r,c]=1);
    rhs: list of 0/1. Returns (x0 bitmask, list of kernel-basis bitmasks) or
    None if inconsistent. x0 is a particular solution; kernel basis spans the
    nullspace (each an int bitmask over columns)."""
    if ncols < 0 or len(rows) != len(rhs):
        raise ValueError("invalid GF(2) dimensions")
    pivots = {}
    for mask, b in zip(rows, rhs):
        if mask < 0 or mask >> ncols or b not in (0, 1):
            raise ValueError("GF(2) rows must fit ncols and rhs must be binary")
        m, bb = mask, b
        while m:
            pc = (m & -m).bit_length() - 1
            if pc not in pivots:
                pivots[pc] = (m, bb)
                break
            pm, pb = pivots[pc]
            m ^= pm; bb ^= pb
        else:
            if bb:
                return None                  # 0 = 1 inconsistent
    descending = sorted(pivots, reverse=True)
    x0 = 0
    for pc in descending:
        m, bb = pivots[pc]
        if bb ^ (bin(m & x0).count("1") % 2):
            x0 |= (1 << pc)
    kernel = []
    for fc in range(ncols):
        if fc in pivots:
            continue
        kv = 1 << fc
        for pc in descending:
            m, _ = pivots[pc]
            if bin(m & kv).count("1") % 2:
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
    """Bounded exact enumeration of a sampled GF(2)-kernel subspace.

    Historical MITM entry point: overlapping XOR moves are not additive in the
    residual group. Gray-code updates account for every bit flip. None means
    this subspace or budget was exhausted, not that the target is infeasible.
    """
    if budget < 1:
        raise ValueError("kernel search budget must be positive")
    if not odd_idx:
        return x0
    K = kernel[:]
    rng.shuffle(K)
    use = K[:26]
    acc = [sum(pool[i][j] for i in range(N) if x0 >> i & 1) % orders[j]
           for j in odd_idx]
    target = [t[j] % orders[j] for j in odd_idx]
    x, previous = x0, 0
    if acc == target:
        return x
    for step in range(1, min(1 << len(use), budget)):
        gray = step ^ (step >> 1)
        kv = use[(gray ^ previous).bit_length() - 1]
        flips = kv
        while flips:
            bit = flips & -flips
            i = bit.bit_length() - 1
            sign = -1 if x & bit else 1
            for k, j in enumerate(odd_idx):
                acc[k] = (acc[k] + sign * pool[i][j]) % orders[j]
            flips ^= bit
        x ^= kv
        previous = gray
        if acc == target:
            return x
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
        return None, "residual search unclosed"
    assert verify(xb, pool, orders, t), "kernel search returned an invalid solution"
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
    print("== small PLANTED synthetic group instances (not harvested vectors) ==")
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
    print("\n== group size and GF(2) projection at frozen-spec scale ==")
    print(f"{'B':>6}{'B_prime':>9}{'comps':>7}{'dim bits':>9}{'2part bits':>11}"
          f"{'mod2 bits':>10}{'resid bits':>11}{'maxodd_l':>9}{'gf2 sec':>8}")
    ps = primes_upto(20000)
    for (B, Bp) in [(547, 5470), (1259, 12590), (1259, 18885)]:
        Qm = [q for q in ps if B < q <= Bp]
        Qp = [q for q in ps if 2 < q <= B and q != 5]
        comps = components(Qm, Qp)
        orders = [c[4] for c in comps]
        dim = sum(math.log2(o) for o in orders)
        two_bits = sum(math.log2(o) for c, o in zip(comps, orders) if c[2] == 2)
        mod2_bits = sum(1 for c in comps if c[2] == 2)
        residual_bits = dim - mod2_bits
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
        assert r is not None, "planted instance has an inconsistent projection"
        x0, _ = r
        assert bin(x0).count("1") % 2 == 1
        assert all(sum(pool[i][j] for i in range(N) if x0 >> i & 1) % 2
                   == t[j] % 2 for j, o in enumerate(orders) if o % 2 == 0)
        print(f"{B:>6}{Bp:>9}{len(comps):>7}{dim:>9.0f}{two_bits:>11.0f}"
              f"{mod2_bits:>10}{residual_bits:>11.0f}{max_odd:>9}{dt:>8.1f}")

def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 7)
    study_correctness(rng)
    study_mod2_scale(rng)

if __name__ == "__main__":
    main()
