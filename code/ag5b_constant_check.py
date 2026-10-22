#!/usr/bin/env python3
"""AG5b: does the '2' in Popovych's second section X+2 matter?

Claim (doc/arith-geom.tex Rem. 5.8 / doc/popovych-note.tex): the constant
is immaterial; what matters is that the zero -c of the section X + c
avoids the rational torsion {+-1} of G_m, i.e. c not in {0, +-1}.

  - c = -1 is the first section X - 1 itself (zero at 1).
  - c = +1 (zero at -1, inversion-fixed): the inversion collapse SURVIVES:
      (zeta+1)^{p^{d/2}} = zeta^{-1}+1 = zeta^{-1}(zeta+1), so
      (X+1)^{p^{d/2}-1} = X^{-1} and ord(X+1) | r(p^{d/2}-1) for even d.
    Worse, zeta+1 = (zeta^2-1)/(zeta-1) is multiplicatively DEPENDENT on
    the Galois orbit of zeta-1 (zero rank added): the pair {X-1, X+1}
    gives no burden jump at all.
  - |c| >= 2: trivial stabilizer (the Lemma 5.3 argument runs verbatim:
    a prime q | (zeta+c) has zeta = -c of order r mod q, forcing gamma=1),
    so the full Popovych burden jump holds for ANY such c, with the
    constant entering only through the finitely many excluded p
    (p | c(c+1) and p | Phi_r(-c)), the excluded modulus r | c+1, and the
    level-1 component = base-(c+1) Fermat.

Measured here: for even d, the collapse bound (X+c)^{2r(p^{d/2}-1)} = 1
holds for c = 1 at every sample and generically fails for
c in {2, 3, -2, 5}; exact orders confirm the top level e = d is absent
for c = 1 and present otherwise.

Writes data/generated/ag5b_constant_check.json.
"""
import json, os, random, sys
from math import lcm
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sympy import primerange
from sympy.polys.specialpolys import cyclotomic_poly
from ag2_torus_check import (polpow, one_mod_phi, ord_mod, phi_val,
                             divisors, factor_resolved, exact_order)

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                   "data", "generated", "ag5b_constant_check.json")
CONSTS = [1, 2, 3, -2, 5]
CASES = [(5, 4, 8, 4000), (13, 4, 8, 3000), (7, 6, 6, 1500),
         (7, 3, 8, 2500), (11, 5, 5, 1000)]

def t_congruence(c, n, p, r):
    """(X+c)^n = X^n + c in F_p[X]/(X^r - 1)?"""
    lhs = polpow([c % p, 1] + [0] * (r - 2), n, p, r)
    rhs = [c % p] + [0] * (r - 1)
    rhs[n % r] = (rhs[n % r] + 1) % p
    return lhs == rhs

def mechanism_freeness():
    """W: under the X-1 mechanism congruences n = p (mod lcm(r, rho_r(p)))
    plus Carmichael (p-1 | n-1), T(+1) holds automatically -- the identity
    zeta+1 = (zeta^2-1)/(zeta-1) with rho controlling all conjugates --
    while T(+2) generically fails at even d (half-depth modulus misses
    rho'). So the {X-1, X+1} 'conjecture' is mechanism-equivalent to
    Agrawal's, whereas c = 2 genuinely blocks the engine."""
    rng = random.Random(7)
    res = {1: [0, 0], 2: [0, 0]}
    for (r, d, k, pmax) in [(5, 4, 8, 3000), (13, 4, 8, 2500)]:
        primes = [p for p in primerange(7, pmax)
                  if p != r and ord_mod(p, r) == d][:k]
        for p in primes:
            bf, ok = factor_resolved(2 * r)
            for e in divisors(d // 2):
                fe, o2 = factor_resolved(phi_val(e, p))
                ok = ok and o2
                for q, m in fe.items():
                    bf[q] = bf.get(q, 0) + m
            if not ok:
                continue
            rho = exact_order([(-1) % p, 1] + [0] * (r - 2), bf, p, r)
            M = lcm(r, rho, p - 1)
            for _ in range(3):
                n = p + rng.randrange(1, 10**4) * M
                for c in (1, 2):
                    res[c][0] += t_congruence(c, n, p, r)
                    res[c][1] += 1
    return res

def main():
    rows = []
    stats = {c: {"collapse": [0, 0], "top_even": [0, 0],
                 "top_odd": [0, 0]} for c in CONSTS}
    for r, d, k, pmax in CASES:
        primes = []
        for p in primerange(5, pmax):
            if p != r and ord_mod(p, r) == d:
                primes.append(p)
            if len(primes) >= k:
                break
        for p in primes:
            for c in CONSTS:
                if p == 3 and c in (2, 5):   # sections coincide: p | c+1
                    continue
                if c % p == 0 or (c + 1) % p == 0 or \
                        int(cyclotomic_poly(r, -c)) % p == 0:
                    continue
                xc = [c % p, 1] + [0] * (r - 2)
                row = {"r": r, "p": p, "d": d, "c": c}
                if d % 2 == 0:
                    coll = one_mod_phi(
                        polpow(xc, 2*r*(p**(d//2) - 1), p, r), p, r)
                    row["collapse"] = coll
                    stats[c]["collapse"][0] += coll
                    stats[c]["collapse"][1] += 1
                # exact order within 2r * prod_{e|d} Phi_e(p)
                bf, ok = factor_resolved(2 * r)
                for e in divisors(d):
                    fe, o2 = factor_resolved(phi_val(e, p))
                    ok = ok and o2
                    for q, m in fe.items():
                        bf[q] = bf.get(q, 0) + m
                if ok:
                    o = exact_order(xc, bf, p, r)
                    sub = 2 * r
                    for e in divisors(d):
                        if e != d:
                            sub *= phi_val(e, p)
                    top = not one_mod_phi(polpow(xc, sub, p, r), p, r)
                    row["ord"] = o
                    row["top_needed"] = top
                    key = "top_even" if d % 2 == 0 else "top_odd"
                    stats[c][key][0] += top
                    stats[c][key][1] += 1
                rows.append(row)
    print(f"{'c':>4} | collapse(even d) | top e=d (even d) | top e=d (odd d)")
    for c in CONSTS:
        t = stats[c]
        print(f"{c:>4} | {t['collapse'][0]:3d}/{t['collapse'][1]:<3d}"
              f"          | {t['top_even'][0]:3d}/{t['top_even'][1]:<3d}"
              f"           | {t['top_odd'][0]:3d}/{t['top_odd'][1]}")
    # c = 1: the inversion collapse SURVIVES at even d (like X-1); at odd
    # d there is no collapse for any section, so full support is expected.
    assert stats[1]["collapse"][0] == stats[1]["collapse"][1]
    assert stats[1]["top_even"][0] == 0
    assert stats[1]["top_odd"][0] == stats[1]["top_odd"][1]
    # |c| >= 2: trivial stabilizer -- no collapse, top level present (both
    # parities), up to the ~1/ell generic exceptions.
    for c in (2, 3, -2, 5):
        n_ok, n = stats[c]["collapse"]
        assert n_ok <= n * 0.1, (c, n_ok, n)
        t_ok, t = (stats[c]["top_even"][0] + stats[c]["top_odd"][0],
                   stats[c]["top_even"][1] + stats[c]["top_odd"][1])
        assert t_ok >= t * 0.9, (c, t_ok, t)
    free = mechanism_freeness()
    print(f"\nW mechanism-freeness (n = p mod lcm(r, rho, p-1), even d):")
    print(f"   T(+1) passes {free[1][0]}/{free[1][1]}   "
          f"T(+2) passes {free[2][0]}/{free[2][1]}")
    assert free[1][0] == free[1][1], "T(+1) must be free for the mechanism"
    assert free[2][0] <= free[2][1] * 0.1, "T(+2) must generically fail"

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump({"rows": rows, "stats": stats, "mechanism_freeness": free},
              open(OUT, "w"), indent=1)
    print(f"\nwrote {OUT}")

if __name__ == "__main__":
    main()
