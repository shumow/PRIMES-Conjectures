#!/usr/bin/env python3
"""A11 (option c): does a different AKS modulus r give a friendlier group?

For the T(-1,n,r) construction, a pool prime p with ord_r(p)=d makes X^r-1 split
over F_p into degree-d pieces; the congruence is controlled by the order of
(X-1) in F_{p^d}*, a divisor of p^d-1. Define the EFFECTIVE DEGREE e(r,p) = the
least e with ord(X-1 in F_{p^d}) | p^e - 1. This is the harvest/solver burden:
  e=1  -> control is p-1 alone (SINGLE condition, AGHS-harvestable) -- the prize
  e=2  -> control is (p-1)(p+1) = p^2-1 (DOUBLE condition, exactly r=5's case)
  e>=3 -> needs a cyclotomic factor Phi_e(p) ~ p^{phi(e)} (bigger to make smooth,
          more prime components -> higher dimension) -- strictly worse.

Validity: a counterexample needs n^2 != 1 (mod r), i.e. the common residue g of
the p_i has ord_r(g) = d > 2 (d=1,2 force n = +-1 mod r). So we scan residues g
with ord_r(g) = d > 2 and report the minimal effective degree achievable.

Question answered: can any r beat r=5's effective degree 2 (get a single p-1
condition), which would sidestep the N1/A10 double-condition obstruction?
"""
import sys
from sympy import factorint, isprime, primerange, nextprime

def poly_mulmod(a, b, mod, p):
    """Multiply coeff-lists a,b (low-order first) mod poly `mod` (monic) mod p."""
    res = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                res[i + j] = (res[i + j] + ai * bj) % p
    # reduce mod `mod` (monic, degree D)
    D = len(mod) - 1
    for i in range(len(res) - 1, D - 1, -1):
        c = res[i]
        if c:
            for k in range(D + 1):
                res[i - D + k] = (res[i - D + k] - c * mod[k]) % p
    return [x % p for x in res[:D]] + [0] * max(0, D - len(res))

def poly_powmod(a, e, mod, p):
    result = [1]
    base = a[:]
    while e:
        if e & 1:
            result = poly_mulmod(result, base, mod, p)
        base = poly_mulmod(base, base, mod, p)
        e >>= 1
    return result

def norm_list(a, D):
    a = [x for x in a] + [0] * (D - len(a))
    return tuple(a[:D])

def irreducible_factor_of_cyclotomic(r, p, d):
    """Return a degree-d monic irreducible factor (coeff list) of Phi_r over
    F_p, via building F_{p^d} as F_p[X]/(min poly of a primitive r-th root).
    We get one by factoring X^r - 1 through repeated gcd is heavy; instead use
    sympy factorization over GF(p)."""
    from sympy import Poly, symbols, GF
    X = symbols('X')
    facs = Poly(X**r - 1, X, modulus=p).factor_list()[1]
    for fac, mult in facs:
        if fac.degree() == d and fac.degree() > 0:
            # skip the (X-1) linear factor (degree 1 only if d==1)
            coeffs = fac.all_coeffs()[::-1]   # low-order first
            # ensure it's not X-1 (the trivial root) unless d==1 intended
            if d == 1 and coeffs == [(-1) % p, 1]:
                continue
            return [c % p for c in coeffs]
    return None

def order_of_X_minus_1(r, p, d):
    """Order of (X-1) in F_{p^d}* = F_p[X]/(g), g a deg-d irred factor of Phi_r."""
    g = irreducible_factor_of_cyclotomic(r, p, d)
    if g is None:
        return None
    D = d
    elt = norm_list([(-1) % p, 1], D)     # X - 1
    N = p**d - 1
    fac = factorint(N)
    order = N
    one = norm_list([1], D)
    for q in fac:
        while order % q == 0:
            cand = order // q
            if norm_list(poly_powmod(list(elt), cand, g, p), D) == one:
                order = cand
            else:
                break
    return order

def ord_mult(a, m):
    """multiplicative order of a mod m (m prime)."""
    x = a % m; o = 1
    while x != 1:
        x = (x * a) % m; o += 1
        if o > m:
            return None
    return o

def totient(n):
    from sympy import totient as T
    return int(T(n))

def harvest_levels(order, p, r):
    """The cyclotomic LEVELS carrying the p-dependent (large-prime) part of the
    control. A prime l | order with l > r sits at level e = ord_l(p) (l | Phi_e(p)).
    Primes l <= r are fixed (r itself, and small primes) -> handled by global
    congruences, not by harvesting. Returns set of levels e."""
    levels = set()
    for l in factorint(order):
        if l > r:
            e = ord_mult(p, l)
            if e is not None:
                levels.add(e)
    return levels

def primes_with_order(r, g, count, start=1000):
    """`count` primes p = g (mod r), p >= start (large enough that p^e-1 has
    genuine large factors revealing cyclotomic levels)."""
    out = []
    p = start
    while len(out) < count:
        p = nextprime(p)
        if p != r and p % r == g % r:
            out.append(p)
    return out

def ord_mod(g, r):
    x = g % r; o = 1
    while x != 1:
        x = (x * g) % r; o += 1
        if o > r:
            return None
    return o

def harvest_degree_for(r, g, d, nsamp=3):
    """Union cyclotomic levels of the p-dependent control over nsamp primes,
    and the harvest degree = sum of phi(e) over levels. None if p^d-1 too big."""
    levels = set()
    for p in primes_with_order(r, g, nsamp, start=1000):
        if p**d - 1 > 10**22:
            return None
        order = order_of_X_minus_1(r, p, d)
        if order is None:
            return None
        levels |= harvest_levels(order, p, r)
    if not levels:
        return None
    return sum(totient(e) for e in levels), sorted(levels)

def main():
    rs = [int(x) for x in sys.argv[1:]] or [5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    print("Harvest burden of the T(-1,n,r) construction per r.")
    print("degree = sum phi(e) over cyclotomic levels e of the p-DEPENDENT")
    print("control (large primes>r). r=5 gives {1,2} -> degree 2 (p^2-1, the")
    print("double Carmichael+Lucas condition). Lower is friendlier; degree 1")
    print("(single p-1 condition) would sidestep the double-condition wall.")
    print("Valid counterexample needs d = ord_r(g) > 2.")
    print(f"{'r':>4}{'best d':>7}{'min degree':>11}{'levels':>12}")
    for r in rs:
        best = None
        for g in range(2, r):
            d = ord_mod(g, r)
            if d is None or d <= 2:
                continue
            res = harvest_degree_for(r, g, d)
            if res is None:
                continue
            deg, levels = res
            if best is None or deg < best[0]:
                best = (deg, levels, d)
        if best:
            deg, levels, d = best
            print(f"{r:>4}{d:>7}{deg:>11}{str(levels):>12}")
        else:
            print(f"{r:>4}{'--':>7}{'--':>11}{'(d>2 needs p^d-1 too large)':>12}")

if __name__ == "__main__":
    main()
