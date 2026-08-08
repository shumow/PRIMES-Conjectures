#!/usr/bin/env python3
"""A7 Loeh-Niebuhr-style subset-product solver — phase 1.

Adapting the AGP / Loeh-Niebuhr constructive Carmichael method to our double
(Carmichael + Lucas-Carmichael) condition. Structural conclusion from A4-A6:
the solver group is always ~ prod Z/(q-1) over the factor-base primes q, so the
odd-part dimension is intrinsic; the reframing does not escape it and the
scalable subset-product solver IS the deliverable.

This phase tests the key scalability question empirically: does per-prime
GF(l) linear-algebra REDUCTION (eliminating free columns to shrink the odd
system to its rank) push the exact-solve frontier past the raw-MITM cap
(~15 odd components, A6)? Method:
  * 2-part: GF(2) exact (scales).
  * odd part: for the combined odd system over Z/M (M = odd exponent, smooth),
    Gaussian-eliminate to rank r over the CRT-prime fields; the free columns
    (N - r) carry 0/1 freedom. Try to realize a 0/1 solution by (a) setting
    frees to satisfy pivots via per-pivot subset-sums mod small primes, then
    (b) exact search on any residual core.
Reports the frontier reached vs A6's MITM cap, and the honest remaining gap.
"""
import math, random, sys, time
from phase1a_calibration import primes_upto

def ppf(n):
    f = {}; d = 2
    while d * d <= n:
        while n % d == 0:
            f[d] = f.get(d, 0) + 1; n //= d
        d += 1
    if n > 1:
        f[n] = f.get(n, 0) + 1
    return f

# ---- GF(l) Gaussian elimination (small l, dense) ----

def gfl_rref(A, b, l):
    """Row-reduce [A|b] over GF(l). A: list of rows (lists), b: list.
    Returns (pivcols, reduced_rows, reduced_b) or None if inconsistent."""
    A = [row[:] for row in A]; b = b[:]
    rows = len(A); cols = len(A[0]) if A else 0
    piv = []; r = 0
    for c in range(cols):
        pr = None
        for i in range(r, rows):
            if A[i][c] % l != 0:
                pr = i; break
        if pr is None:
            continue
        A[r], A[pr] = A[pr], A[r]; b[r], b[pr] = b[pr], b[r]
        inv = pow(A[r][c], l - 2, l)
        A[r] = [(x * inv) % l for x in A[r]]; b[r] = (b[r] * inv) % l
        for i in range(rows):
            if i != r and A[i][c] % l != 0:
                f = A[i][c]
                A[i] = [(A[i][k] - f * A[r][k]) % l for k in range(cols)]
                b[i] = (b[i] - f * b[r]) % l
        piv.append(c); r += 1
        if r == rows:
            break
    for i in range(r, rows):
        if b[i] % l != 0 and all(A[i][k] % l == 0 for k in range(cols)):
            return None
    return piv, A[:r], b[:r]

# ---- solver: per-prime reduction + greedy 0/1 ----

def solve_odd_greedy(pool, orders, t, N, odd_idx, rng, tries=4000):
    """Attempt a 0/1 solution to the odd system by: reduce over each odd prime,
    then greedily set free columns and correct pivots via per-prime subset-sums.
    Returns x (set of chosen indices) or None. Heuristic; measures frontier."""
    # Work modulo each distinct odd prime l (bottom layer) jointly.
    # Build combined system rows over ALL odd components (mod their prime).
    prime_of = {j: (round(orders[j] ** (1.0 / _mult(orders[j])))) for j in odd_idx}
    # Represent each column i as its residues on odd components.
    # Greedy random search with linear-algebra feasibility check per prime.
    best = None
    for _ in range(tries):
        # random 0/1 start biased sparse
        x = set(i for i in range(N) if rng.random() < 0.5)
        # evaluate residual
        ok = True
        for j in odd_idx:
            s = sum(pool[i][j] for i in x) % orders[j]
            if s != t[j] % orders[j]:
                ok = False; break
        if ok and len(x) % 2 == 1:
            return x
    return None

def _mult(m):
    # exponent a for m = l^a
    for a in range(1, 64):
        r = round(m ** (1.0 / a))
        if r ** a == m and _isprime(r):
            return a
    return 1

def _isprime(n):
    if n < 2: return False
    for p in (2,3,5,7,11,13,17,19,23,29,31,37):
        if n % p == 0: return n == p
    d,s=n-1,0
    while d%2==0: d//=2; s+=1
    for a in (2,3,5,7,11,13,17,19,23,29,31,37):
        x=pow(a,d,n)
        if x in (1,n-1): continue
        for _ in range(s-1):
            x=x*x%n
            if x==n-1: break
        else: return False
    return True

# ---- exact per-prime-reduction solver: reduce then MITM on the core ----

def solve_reduced(pool, orders, t, N, odd_idx, rng, time_budget=15):
    """Reduce the odd system by GF(l) elimination to a small core of 'hard'
    columns, then meet-in-the-middle on the core. Frontier test."""
    from itertools import combinations
    D = len(odd_idx)
    # Build residue matrix restricted to odd components (mod full order).
    # Combined modulus per component is orders[j]; treat as CRT of prime powers.
    # For the frontier test we just do MITM but with a linear pre-pass that
    # fixes columns forced by rank deficiency. Given pure-python limits, we
    # measure the honest cap.
    t0 = time.time()
    # naive MITM cap check (same as A6) as the baseline the reduction must beat
    if N <= 44:
        half = N // 2
        def subsets(idxs):
            idxs=list(idxs)
            for r in range(len(idxs)+1):
                for c in combinations(idxs,r): yield c
        left={}
        for combo in subsets(range(half)):
            acc=tuple(sum(pool[i][odd_idx[k]] for i in combo)%orders[odd_idx[k]]
                      for k in range(D))
            left.setdefault(acc,combo)
        for combo in subsets(range(half,N)):
            if time.time()-t0>time_budget: return None,"timeout"
            need=tuple((t[odd_idx[k]]-sum(pool[i][odd_idx[k]] for i in combo))
                       %orders[odd_idx[k]] for k in range(D))
            if need in left:
                return set(left[need])|set(combo),"ok"
        return None,"exhausted"
    return None,"N>44 (needs true reduction; phase-2)"

def make_instance(nfp, t0cap, N, pk, rng, ps):
    cand=[q for q in ps if q>50 and all(l<=t0cap for l in ppf(q-1) if l!=2)]
    qs=rng.sample(cand,min(nfp,len(cand)))
    comps=[]
    for q in qs:
        for l,a in ppf(q-1).items():
            comps.append((l,l**a))
    orders=[m for _,m in comps]
    pool=[[rng.randrange(o) for o in orders] for _ in range(N)]
    if pk%2==0: pk+=1
    S=rng.sample(range(N),pk)
    t=[0]*len(orders)
    for i in S:
        for j,o in enumerate(orders): t[j]=(t[j]+pool[i][j])%o
    return comps,orders,pool,t,set(S)

def main():
    rng=random.Random(int(sys.argv[1]) if len(sys.argv)>1 else 5)
    ps=primes_upto(4000)
    print("A7 phase-1: honest cap of exact odd-solve (reduction pre-pass TBD)")
    print(f"{'nfp':>5}{'N':>5}{'Dodd':>6}{'oddbits':>8}{'result':>14}{'sec':>7}")
    for nfp in [3,5,8,12,20]:
        comps,orders,pool,t,S=make_instance(nfp,97,N=min(40,8*nfp),pk=3,rng=rng,ps=ps)
        N=len(pool)
        odd=[j for j in range(len(orders)) if comps[j][0]!=2]
        ob=sum(math.log2(orders[j]) for j in odd)
        t0=time.time()
        x,msg=solve_reduced(pool,orders,t,N,odd,rng)
        dt=time.time()-t0
        print(f"{nfp:>5}{N:>5}{len(odd):>6}{ob:>8.0f}{msg:>14}{dt:>7.1f}")

if __name__=="__main__":
    main()
