#!/usr/bin/env python3
"""A8 omega-guided subset-product solver (Loeh-Niebuhr / AGHS method).

A4-A6 wrongly treated the odd part as a wall: generic solvers (MITM, annealing)
cap ~15 components. But AGHS (arXiv:1203.6664) built Carmichael numbers with
10^10 prime factors -- subset-product = 1 in (Z/Lambda)* including the odd part
-- via a SUBEXPONENTIAL omega-guided reduction, NOT exact linear algebra:
  omega(a) = highest CRT component index where a != identity.
Build the product by zeroing components top-down, exploiting that pool primes
p with p-1 | Lambda are = 1 (identity) on MANY components (the ones dividing
p-1), so a move touching component i can be chosen trivial on all j > i.

This tests the method and, crucially, the STRUCTURE it needs: pool elements
must be identity on many components (density rho of trivial components). Our
current harvest (m = product of j primes) gives LOW rho (dense vectors); the
AGHS 'p-1 | Lambda' divisor paradigm gives HIGH rho. We measure solver success
vs dimension r for high vs low rho -> validates the path and pinpoints the
harvest redesign.

RESULT (2026-08-08): this SIMPLIFIED omega-reducer (strict top-down, one
potential) only solves the easy regime (r<=20, high rho). The real AGHS
algorithm uses TWO potentials (omega and omega-bar), a birthday-combination
step, and exploits the specific non-uniform distribution of p-1 | Lambda
primes -- a substantial multi-turn implementation not reproduced here. Value:
(a) the framework runs; (b) it makes concrete that the pool needs the AGHS
'p-1 | Lambda' structure (primes = 1 on many components), which our current
product-of-j-primes harvest does NOT give. This OVERTURNS the A6 'dimension
wall': AGHS solve exactly this at 10^10-factor scale, so the solver is not a
fundamental obstruction -- it needs the right algorithm + harvest structure.
"""
import math, random, sys, time
from phase1a_calibration import primes_upto

def subset_sum_mod(values, target, modulus, rng, cap=18):
    """Find a subset of `values` (list of (idx, val)) summing to target mod
    modulus. Small birthday/greedy search; returns list of idxs or None."""
    if not values:
        return None
    # greedy: try singletons, then pairs (birthday), then small random subsets
    for idx, v in values:
        if v % modulus == target % modulus:
            return [idx]
    seen = {}
    for idx, v in values[:400]:
        r = v % modulus
        if (target - r) % modulus in seen:
            return [seen[(target - r) % modulus], idx]
        seen.setdefault(r, idx)
    # random small subsets
    for _ in range(2000):
        k = rng.randint(1, min(cap, len(values)))
        pick = rng.sample(values, k)
        s = sum(v for _, v in pick) % modulus
        if s == target % modulus:
            return [i for i, _ in pick]
    return None

def omega(acc, target, orders, D):
    """Distance-to-target: highest component index where acc != target."""
    for j in range(D - 1, -1, -1):
        if acc[j] != target[j] % orders[j]:
            return j
    return -1

def omega_solve(pool, orders, target, N, rng, time_budget=4):
    """Guided random walk (AGHS-style). Maintain a 0/1 subset (acc = its group
    sum); reduce omega = highest mismatched component by adding/removing single
    pool elements, greedily fixing from the top. An element added to fix the
    top mismatch must be = target there and identity on higher (already-fixed)
    components -- these exist w.p. rho^(#higher). Returns chosen set or None."""
    D = len(orders)
    # index elements by (highest non-identity component) for fast candidate lookup
    from collections import defaultdict
    by_top = defaultdict(list)
    for i in range(N):
        hi = -1
        for j in range(D - 1, -1, -1):
            if pool[i][j] % orders[j] != 0:
                hi = j; break
        by_top[hi].append(i)
    acc = [0] * D
    chosen = set()
    t0 = time.time()
    stuck = 0
    while time.time() - t0 < time_budget:
        c = omega(acc, target, orders, D)
        if c == -1:
            return chosen                      # exact hit
        need = (target[c] - acc[c]) % orders[c]
        # candidates: top == c (identity above c), not yet chosen
        cands = [(i, pool[i][c]) for i in by_top[c] if i not in chosen]
        pick = subset_sum_mod(cands, need, orders[c], rng, cap=8)
        if pick is not None:
            for i in pick:
                chosen.add(i)
                for j in range(D):
                    acc[j] = (acc[j] + pool[i][j]) % orders[j]
            stuck = 0
            continue
        # stuck at component c: no candidate subset. Back off -- remove a
        # random chosen element touching c to perturb, then retry.
        stuck += 1
        touching = [i for i in chosen if pool[i][c] % orders[c] != 0]
        if touching and stuck < 200:
            i = rng.choice(touching)
            chosen.discard(i)
            for j in range(D):
                acc[j] = (acc[j] - pool[i][j]) % orders[j]
        else:
            return None
    return None

def make_structured(r, rho, N, planted_k, rng, primes_cap=97):
    """Synthetic instance with tunable identity-density rho: each element is
    identity (0) on each component independently w.p. rho, else uniform random.
    Components are cyclic of small odd prime order. Planted solution guaranteed
    by construction: build target as the sum of planted elements."""
    ps = [p for p in primes_upto(primes_cap) if p > 2]
    orders = [rng.choice(ps) for _ in range(r)]
    pool = []
    for _ in range(N):
        vec = [0 if rng.random() < rho else rng.randrange(orders[j])
               for j in range(r)]
        pool.append(vec)
    # plant: pick planted_k elements, set target = their sum
    if planted_k % 2 == 0:
        planted_k += 1
    S = rng.sample(range(N), planted_k)
    target = [0] * r
    for i in S:
        for j in range(r):
            target[j] = (target[j] + pool[i][j]) % orders[j]
    return orders, pool, target, set(S)

def verify(chosen, pool, orders, target):
    acc = [0] * len(orders)
    for i in chosen:
        for j in range(len(orders)):
            acc[j] = (acc[j] + pool[i][j]) % orders[j]
    return all(acc[j] == target[j] % orders[j] for j in range(len(orders)))

def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 9)
    print("A8 omega-guided solver: success vs dimension r, at identity-density")
    print("rho (high rho = AGHS 'p-1|Lambda' structure; low rho = our dense harvest)")
    print(f"{'rho':>6}{'r (comps)':>10}{'N':>8}{'solved':>8}{'|S|':>6}{'sec':>7}")
    for rho in [0.9, 0.75, 0.5, 0.2]:
        for r in [20, 50, 100, 300, 1000]:
            N = max(2000, 40 * r)
            orders, pool, target, S = make_structured(r, rho, N,
                                                       planted_k=r // 2 + 3,
                                                       rng=rng)
            t0 = time.time()
            sol = omega_solve(pool, orders, target, N, rng)
            dt = time.time() - t0
            ok = sol is not None and verify(sol, pool, orders, target)
            print(f"{rho:>6}{r:>10}{N:>8}{str(ok):>8}"
                  f"{(len(sol) if sol else 0):>6}{dt:>7.1f}")

if __name__ == "__main__":
    main()
