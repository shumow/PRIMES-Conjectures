#!/usr/bin/env python3
"""AG3: the Frobenius-impersonation hierarchy -- verification and census.

Companion to doc/arith-geom.tex sec. 6. Checks:

  H1. Howe's explicit higher-order example n = 17*31*41*43*89*97*167*331
      (Math. Comp. 69 (2000); cited as a rigid order-2 Carmichael number):
      verify squarefreeness and, for each p | n and r in {1,2}, find all
      Frobenius powers i with n = p^i (mod p^r - 1). Confirm rigidity
      (i = 0 works at every level, i.e. p^2 - 1 | n - 1) and confirm the
      number is NOT in the Williams/Agrawal cell (needs i = 1 at level 2,
      i.e. n = -1 mod p+1).
  H2. Dictionary spot-check (Prop. 6.2 of the tex): on the nonsplit torus
      T_2(F_p) (norm-one subgroup of F_{p^2}^*, order p+1, elements
      x = y^{p-1}), the point identity x^n = x^{p^i} for all x holds iff
      p + 1 | n - p^i. Verified on random (p, n) pairs, both directions.
  H3. Census of the hierarchy cells in [2, LIMIT] (smallest-prime-factor
      sieve; squarefree composites only):
        - Carmichael          (level 1, i=0:  p-1 | n-1 for all p | n)
        - Lucas-Carmichael    (level 2, i=1:  p+1 | n+1 for all p | n)
        - Williams            (both; the Agrawal/L-P cell's superset)
        - Howe order-2        (for each p, SOME i works at levels 1 and 2)
      Expected: Carmichael and Lucas-Carmichael populate; Williams empty
      (none < 2^64, McIntosh-Mitra 2015); Howe order-2 empty at this scale
      (the known example is ~4.4e14).

Deterministic; writes data/generated/ag3_hierarchy_check.json.
"""

import json
import os
import random
from array import array

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                        "data", "generated", "ag3_hierarchy_check.json")

LIMIT = 10**7

HOWE_FACTORS = [17, 31, 41, 43, 89, 97, 167, 331]

# ---------- H1: Howe's example ----------

def powers_matching(n, p, r, imax=None):
    """All i in [0, ord) with n = p^i (mod p^r - 1)."""
    m = p**r - 1
    if imax is None:
        imax = 2 * r + 2
    out, x = [], 1 % m
    for i in range(imax):
        if n % m == x:
            out.append(i)
        x = x * p % m
    return out

def check_howe():
    n = 1
    for p in HOWE_FACTORS:
        n *= p
    rows = []
    rigid = True
    williams = True
    for p in HOWE_FACTORS:
        i1 = powers_matching(n, p, 1)
        i2 = powers_matching(n, p, 2)
        rows.append({"p": p, "i_level1": i1, "i_level2": i2,
                     "rigid_here": n % (p*p - 1) == 1,
                     "lucas_here": (n + 1) % (p + 1) == 0})
        rigid &= n % (p*p - 1) == 1
        williams &= (n - 1) % (p - 1) == 0 and (n + 1) % (p + 1) == 0
        assert i1 and i2, f"not order-2 at p={p}"
    return {"n": n, "factors": HOWE_FACTORS, "rows": rows,
            "is_order2": True, "is_rigid": rigid, "is_williams": williams,
            "n_mod_5": n % 5}

# ---------- H2: dictionary spot-check on T_2 ----------

def f_p2_mul(a, b, p, t):
    """Multiply a, b in F_{p^2} = F_p[x]/(x^2 - t), elements (c0, c1)."""
    c0 = (a[0]*b[0] + t*a[1]*b[1]) % p
    c1 = (a[0]*b[1] + a[1]*b[0]) % p
    return (c0, c1)

def f_p2_pow(a, e, p, t):
    r, b = (1, 0), a
    while e:
        if e & 1:
            r = f_p2_mul(r, b, p, t)
        b = f_p2_mul(b, b, p, t)
        e >>= 1
    return r

def check_dictionary(trials=60, seed=1):
    rng = random.Random(seed)
    from sympy import isprime, legendre_symbol
    ok = 0
    results = []
    tested = 0
    while tested < trials:
        p = rng.randrange(1000, 100000) | 1
        if not isprime(p):
            continue
        # nonsquare t for F_{p^2}
        t = next(t for t in range(2, p) if legendre_symbol(t, p) == -1)
        i = rng.randrange(0, 2)
        match = rng.random() < 0.5    # build n that matches or not
        if match:
            n = pow(p, i) + rng.randrange(1, 1000) * (p + 1)
        else:
            n = pow(p, i) + rng.randrange(1, 1000) * (p + 1) \
                + rng.randrange(1, p)   # offset off the cell
        cong = (n - pow(p, i)) % (p + 1) == 0
        # test x^n == x^{p^i} for several norm-one points x = y^{p-1}
        holds = True
        for _ in range(8):
            y = (rng.randrange(0, p), rng.randrange(0, p))
            if y == (0, 0):
                y = (1, 1)
            x = f_p2_pow(y, p - 1, p, t)
            if f_p2_pow(x, n, p, t) != f_p2_pow(x, pow(p, i), p, t):
                holds = False
                break
        # direction 1 (congruence -> identity) is a theorem; direction 2
        # (identity -> congruence) can fail only if all sampled x had
        # small order -- count agreement.
        ok += (cong == holds)
        results.append({"p": p, "i": i, "cong": cong, "holds": holds})
        tested += 1
    return {"trials": trials, "agree": ok, "results_sample": results[:5]}

# ---------- H3: the census ----------

def spf_sieve(limit):
    spf = array("I", [0]) * 0
    spf = array("I", range(limit + 1))
    for i in range(2, int(limit**0.5) + 1):
        if spf[i] == i:                      # i prime
            for j in range(i*i, limit + 1, i):
                if spf[j] == j:
                    spf[j] = i
    return spf

def factor_with_spf(n, spf):
    fac = []
    while n > 1:
        p = spf[n]
        e = 0
        while n % p == 0:
            n //= p
            e += 1
        fac.append((p, e))
    return fac

def census(limit):
    spf = spf_sieve(limit)
    counts = {"carmichael": 0, "lucas_carmichael": 0,
              "williams": 0, "howe_order2": 0}
    smallest = {"carmichael": None, "lucas_carmichael": None,
                "williams": None, "howe_order2": None}
    for n in range(3, limit + 1, 2):
        if spf[n] == n:                      # prime
            continue
        fac = factor_with_spf(n, spf)
        if any(e > 1 for _, e in fac) or len(fac) < 2:
            continue                         # not squarefree composite
        ps = [p for p, _ in fac]
        carm = all((n - 1) % (p - 1) == 0 for p in ps)
        lucas = all((n + 1) % (p + 1) == 0 for p in ps)
        if carm:
            counts["carmichael"] += 1
            smallest["carmichael"] = smallest["carmichael"] or n
        if lucas:
            counts["lucas_carmichael"] += 1
            smallest["lucas_carmichael"] = smallest["lucas_carmichael"] or n
        if carm and lucas:
            counts["williams"] += 1
            smallest["williams"] = smallest["williams"] or n
        if carm and all(powers_matching(n, p, 2) for p in ps):
            counts["howe_order2"] += 1
            smallest["howe_order2"] = smallest["howe_order2"] or n
    return counts, smallest

# ---------- H4: does Howe's n pass the AKS congruence at r = 5? ----------

def aks_congruence(n, r):
    """T(-1, n, r): (X-1)^n = X^n - 1 in (Z/n)[X]/(X^r - 1)."""
    def mul(a, b):
        c = [0] * r
        for i, ai in enumerate(a):
            if ai:
                for j, bj in enumerate(b):
                    k = i + j
                    if k >= r:
                        k -= r
                    c[k] = (c[k] + ai * bj) % n
        return c
    g = [(-1) % n, 1] + [0] * (r - 2)
    res, e = [1] + [0] * (r - 1), n
    while e:
        if e & 1:
            res = mul(res, g)
        g = mul(g, g)
        e >>= 1
    rhs = [(-1) % n] + [0] * (r - 1)
    rhs[n % r] = (rhs[n % r] + 1) % n
    return res == rhs

def main():
    report = {}

    howe = check_howe()
    report["howe"] = howe
    print(f"H1 Howe example n = {howe['n']} = "
          + "*".join(map(str, howe["factors"])))
    print(f"   order-2: True   rigid (p^2-1 | n-1 for all p): "
          f"{howe['is_rigid']}   Williams (needs i=1 at level 2): "
          f"{howe['is_williams']}   n mod 5 = {howe['n_mod_5']}")
    for row in howe["rows"]:
        print(f"   p={row['p']:4d}: level-1 powers {row['i_level1']}, "
              f"level-2 powers {row['i_level2']}, "
              f"lucas-cell here: {row['lucas_here']}")

    d = check_dictionary()
    report["dictionary"] = d
    print(f"\nH2 dictionary on T_2: congruence <-> point identity agree "
          f"on {d['agree']}/{d['trials']} random (p, n, i)")
    assert d["agree"] == d["trials"]

    passes = aks_congruence(howe["n"], 5)
    report["howe_aks_r5"] = passes
    print(f"\nH4 Howe's n passes T(-1, n, 5): {passes}"
          f"   (n mod 5 = {howe['n_mod_5']}, so even a pass is inside"
          f" the n^2 = 1 (mod r) exception clause, not a counterexample)")

    counts, smallest = census(LIMIT)
    report["census"] = {"limit": LIMIT, "counts": counts,
                        "smallest": smallest}
    print(f"\nH3 census of squarefree composites below {LIMIT:.0e}:")
    for k in counts:
        print(f"   {k:16s}: {counts[k]:4d}   smallest: {smallest[k]}")
    assert counts["williams"] == 0, "a Williams number below 1e7?!"

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"\nwrote {OUT_JSON}")

if __name__ == "__main__":
    main()
