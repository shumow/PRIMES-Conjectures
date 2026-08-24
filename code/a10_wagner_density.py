#!/usr/bin/env python3
"""A10 (option a): does the AGHS-class birthday solver work at H7's low density?

The scalable subset-product method (AGHS / Wagner generalized birthday) cancels
group components by finding collisions among combinations of pool elements. Its
feasibility hinges on how many components must actually be cancelled -- and that
is governed by IDENTITY-DENSITY rho: a pool element that is identity (=0) on a
component imposes no constraint there, so only the ~(1-rho) fraction of
components on which elements are non-trivial have to be cancelled.

  AGHS pools:      rho ~ 0.3-0.5 (primes = 1 on many components; p-1 | Lambda)
  Our H7 pools:    rho ~ 0.004   (p-1 = 2m, m a product of ~4 primes)

This measures, with a CORRECT Wagner-4 (four-list, 4-sum-to-identity over a
small-prime group), the largest solvable component-count r as a function of rho
at fixed pool N -- the birthday REACH and its density dependence. It answers
option (a): whether low density (H7) can ever be solved, or whether AGHS-class
methods need the high density the double condition can't supply.

Wagner-4 solves a 4-sum in time/space ~ N when N >~ |Geff|^(1/... ), where the
EFFECTIVE group Geff is the components on which the four chosen elements are not
all identity. We report, per rho, the max r with success over trials.
"""
import math, random, sys, time
from collections import defaultdict

def make_pool(r, rho, N, ell, rng):
    """N elements of (Z/ell)^r; each coord is 0 (identity) w.p. rho else
    uniform nonzero-ish (uniform over Z/ell)."""
    pool = []
    for _ in range(N):
        v = tuple(0 if rng.random() < rho else rng.randrange(ell)
                  for _ in range(r))
        pool.append(v)
    return pool

def wagner4_zero(pool, r, ell, rng, target=None):
    """Find 4 DISTINCT indices a,b,c,d with pool[a]+pool[b]+pool[c]+pool[d] ==
    target (default identity 0) over (Z/ell)^r. Split components into two
    blocks; two half-joins matched on block1, then matched on block2.
    Returns the 4 indices or None."""
    if target is None:
        target = tuple([0] * r)
    N = len(pool)
    idx = list(range(N)); rng.shuffle(idx)
    q = N // 4
    P1, P2, P3, P4 = idx[:q], idx[q:2*q], idx[2*q:3*q], idx[3*q:4*q]
    h = r // 2
    def blk1(v): return v[:h]
    def blk2(v): return v[h:]
    def add(u, v): return tuple((u[k] + v[k]) % ell for k in range(r))
    def sub1(u, v): return tuple((u[k] - v[k]) % ell for k in range(h))
    # L12: a+b with block1 == target|block1
    t1 = target[:h]
    map2 = defaultdict(list)
    for b in P2:
        map2[blk1(pool[b])].append(b)
    L12 = []
    for a in P1:
        need = tuple((t1[k] - pool[a][k]) % ell for k in range(h))
        for b in map2.get(need, ()):
            L12.append((a, b))
            if len(L12) > 6 * N:
                break
        if len(L12) > 6 * N:
            break
    # L34: c+d with block1 == 0
    map4 = defaultdict(list)
    for d in P4:
        map4[blk1(pool[d])].append(d)
    L34 = []
    for c in P3:
        need = tuple((-pool[c][k]) % ell for k in range(h))
        for d in map4.get(need, ()):
            L34.append((c, d))
            if len(L34) > 6 * N:
                break
        if len(L34) > 6 * N:
            break
    # match L12,L34 on block2: (a+b)+(c+d) == target on block2
    t2 = target[h:]
    m34 = defaultdict(list)
    for (c, d) in L34:
        key = blk2(add(pool[c], pool[d]))
        m34[key].append((c, d))
    for (a, b) in L12:
        s = blk2(add(pool[a], pool[b]))
        need = tuple((t2[k] - s[k]) % ell for k in range(len(t2)))
        for (c, d) in m34.get(need, ()):
            if len({a, b, c, d}) == 4:
                return (a, b, c, d)
    return None

def max_solvable_r(rho, N, ell, rng, rcap=200):
    maxr = 0
    for r in range(4, rcap, 2):
        ok = 0
        for tr in range(3):
            pool = make_pool(r, rho, N, ell, rng)
            if wagner4_zero(pool, r, ell, rng) is not None:
                ok += 1
        if ok >= 2:
            maxr = r
        else:
            break
    return maxr

def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 3)
    ell = 3
    N = int(sys.argv[2]) if len(sys.argv) > 2 else 20000
    print(f"Wagner-4 4-sum over (Z/{ell})^r, pool N={N}. Max solvable r "
          f"(component count) vs identity-density rho (3 trials each).")
    print("Reach law: (1-rho)*r_max ~ const (pool-limited effective components).")
    print(f"{'rho':>7}{'r_max':>7}{'(1-rho)*rmax':>14}  interpretation")
    rows = [(0.004, "<- H7 pools (identity on ~0.4% of components)"),
            (0.0,   "   uniform baseline"),
            (0.5,   ""),
            (0.9,   ""),
            (0.98,  "<- threshold to reach ~thousand-component groups"),
            (0.996, "")]
    for rho, note in rows:
        mr = max_solvable_r(rho, N, ell, rng)
        print(f"{rho:>7}{mr:>7}{(1-rho)*mr:>14.1f}  {note}")

    # pool-scaling at fixed low (H7) density: does harvesting more help? (log only)
    print("\nPool scaling at rho=0.004 (H7): r_max vs N -- growth is ~log(N),")
    print("so harvesting more cannot reach thousand-component groups.")
    print(f"{'N':>9}{'r_max':>7}{'log3(N)':>9}")
    for NN in [2000, 20000, 100000]:
        mr = max_solvable_r(0.004, NN, ell, rng)
        print(f"{NN:>9}{mr:>7}{math.log(NN,3):>9.1f}")

if __name__ == "__main__":
    main()
