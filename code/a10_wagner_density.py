#!/usr/bin/env python3
"""A10: bounded four-list/four-sum diagnostic on synthetic groups.

The legacy rho parameter is a FORCED-zero mixture weight: otherwise a
coordinate is uniform over Z/ell, including zero. Literal P(0) is
rho + (1-rho)/ell. This differs from A12's literal-zero model.

The search filters pair sums on the first half of the coordinates and caps
intermediate lists. Its first-failure frontier is a finite heuristic statistic,
not a bound on general subset-product algorithms or the full AGHS method.
Four-element outputs also do not satisfy the construction's odd-cardinality
requirement. Historical results remain in data/FINDINGS.md.
"""
import math, random, sys, time
from collections import defaultdict

def identity_probability(rho, ell):
    """Literal P(0) in the forced-zero/uniform mixture, not its bias parameter."""
    if not 0 <= rho <= 1 or ell < 2:
        raise ValueError("rho must be in [0, 1] and the group order at least 2")
    return rho + (1 - rho) / ell

def make_pool(r, rho, N, ell, rng):
    """N elements with forced-zero mixture weight rho; otherwise uniform."""
    identity_probability(rho, ell)
    if r < 0 or N < 0:
        raise ValueError("pool dimensions must be nonnegative")
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
    Returns the 4 indices or None. None is inconclusive: filtering, random
    partitioning and list caps can miss valid four-sums.
    """
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
                assert all(sum(pool[i][k] for i in (a, b, c, d)) % ell
                           == target[k] % ell for k in range(r)), "invalid four-sum"
                return (a, b, c, d)
    return None

def max_solvable_r(rho, N, ell, rng, rcap=200):
    """Historical API: last accepted dimension before the first failed trial set."""
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
    print(f"Four-list 4-sum over (Z/{ell})^r, pool N={N}; forced-zero rho.")
    print("Literal P(0)=rho+(1-rho)/ell. First-failure frontier: 3 trials each,")
    print("accept >=2 successes; stop at first failure; cap r<200.")
    print("This is not a general solver bound or a measurement of H7 vectors.")
    print(f"{'rho':>7}{'literal P(0)':>14}{'frontier':>10}")
    rows = [(0.004, "   historical setting (not literal P(0)=0.004)"),
            (0.0,   "   uniform baseline"),
            (0.5,   ""),
            (0.9,   ""),
            (0.98,  ""),
            (0.996, "")]
    for rho, note in rows:
        mr = max_solvable_r(rho, N, ell, rng)
        print(f"{rho:>7}{identity_probability(rho, ell):>14.3f}{mr:>10}  {note}")

    print("\nPool scaling at forced-zero rho=0.004 (literal P(0)=0.336).")
    print("Finite first-failure frontiers, not an asymptotic impossibility result.")
    print(f"{'N':>9}{'r_max':>7}{'log3(N)':>9}")
    for NN in [2000, 20000, 100000]:
        mr = max_solvable_r(0.004, NN, ell, rng)
        print(f"{NN:>9}{mr:>7}{math.log(NN,3):>9.1f}")

if __name__ == "__main__":
    main()
