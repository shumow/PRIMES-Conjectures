#!/usr/bin/env python3
"""AG4: the elliptic (CM) Agrawal analogue -- cell structure and the floor.

Curve: E : y^2 = x^3 - x (j = 1728, CM by Z[i]; automorphism [i](x,y) =
(-x, iy), so x([i]S) = -x(S) exactly). For an ordinary prime p = 1 (mod 4)
and an odd torsion scale r (p, r coprime, p != 2, r), the p-power Frobenius
acts on each prime-above-r eigenline of E[r] by a scalar lambda in (Z/r)^*,
and for an eigenline point T:

    x(T)^{p^e} = x([lambda^e] T)        (exact; Frobenius on coordinates).

The collapse identities are exact too:  lambda^e = +-1  gives
x(T)^{p^e} = x(T), and  lambda^e = +-i (the order-4 elements of the cyclic
group (Z/r)^*, i.e. the images of the CM units)  gives
x(T)^{p^e} = -x(T).  Hence with

    k' := min { e >= 1 : lambda^e in U },   U := <i> = mu_4-image,

the order of t = x(T) divides 2(p^{k'} - 1), i.e. is supported on the
cyclotomic levels e | k' -- burden = k' = [<lambda> : <lambda> n U] by
minimality.  Validity of a counterexample cell (the exception clause must
contain U, since U-cells are the AGP-constructible 'rigid' analogue)
means lambda not in U, so k' >= 2: THE SAME FLOOR AS THE TORUS WORLD.

Checks (doc/arith-geom.tex sec. 7):

  E1. Division polynomial psi_r sanity: degree (r^2-1)/2; factor degrees
      multiply back mod each sample p.
  E2. Frobenius closure per irreducible factor h: t^{p^k} = t (k = deg h).
  E3. Cell classification: for each factor, k' = min e with
      t^{p^e} = +-t; exceptional cells (k' = 1) occur only with k <= 2;
      measured level support of ord(t) equals {e : e | k'} for large
      primes (generic sharpness; exceptions tallied).
  E4. THE FLOOR: over valid cells (k' >= 2), min k' = 2 at r = 17
      (deg-4 factors with t^{p^2} = -t; Phi_4(p) absent from ord(t)) and
      min k' = 3 at r = 13 -- matching the index formula.
  E5. Index-formula burden table: burden_ell(r) = min{ m/gcd(m,4) :
      m | r-1, m/gcd(m,4) >= 2 } vs the torus burden of AG2 -- the
      elliptic axis never beats the torus axis; both floors are 2.

Deterministic; writes data/generated/ag4_elliptic_check.json.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sympy
from sympy import primerange, factorint, Poly, symbols, ZZ
from ag2_torus_check import (divisors, phi_val, factor_resolved, burden,
                             A11_TABLE)

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                        "data", "generated", "ag4_elliptic_check.json")

X, Y = symbols("x y")
A_COEF, B_COEF = -1, 0            # E: y^2 = x^3 - x
F_X = X**3 + A_COEF * X + B_COEF

# ---------- division polynomials over Z: psi_m = g_m(x) * y^eps_m ----------
# eps_m = 0 for odd m, 1 for even m. All y^2 are folded into F(x), and
# division by 2y is: multiply by y (1/y = y/F) and divide the x-part by 2F.

def _fold(gs_eps):
    """Product of (g, eps) pairs -> canonical (g, eps) with y^2 -> F."""
    g = sympy.Integer(1)
    etot = 0
    for gg, ee in gs_eps:
        g *= gg
        etot += ee
    g = sympy.expand(g * F_X**(etot // 2))
    return g, etot % 2

def _exact_div(num, den):
    q, rem = sympy.div(sympy.expand(num), sympy.expand(den), X)
    assert rem == 0, "inexact division in psi recursion"
    return sympy.expand(q)

def division_polys(rmax):
    """g_m(x) with psi_m = g_m * y^(eps_m); returns dict m -> g_m."""
    g = {0: sympy.Integer(0), 1: sympy.Integer(1), 2: sympy.Integer(2),
         3: sympy.expand(3*X**4 + 6*A_COEF*X**2 + 12*B_COEF*X - A_COEF**2),
         4: sympy.expand(4*(X**6 + 5*A_COEF*X**4 + 20*B_COEF*X**3
                            - 5*A_COEF**2*X**2 - 4*A_COEF*B_COEF*X
                            - 8*B_COEF**2 - A_COEF**3))}
    eps = lambda m: (m + 1) % 2
    for m in range(5, rmax + 1):
        if m % 2 == 1:
            k = (m - 1) // 2
            ga, ea = _fold([(g[k+2], eps(k+2)), (g[k], eps(k)),
                            (g[k], eps(k)), (g[k], eps(k))])
            gb, eb = _fold([(g[k-1], eps(k-1)), (g[k+1], eps(k+1)),
                            (g[k+1], eps(k+1)), (g[k+1], eps(k+1))])
            assert ea == eb == 0
            g[m] = sympy.expand(ga - gb)
        else:
            k = m // 2
            gc, ec = _fold([(g[k+2], eps(k+2)),
                            (g[k-1], eps(k-1)), (g[k-1], eps(k-1))])
            gd, ed = _fold([(g[k-2], eps(k-2)),
                            (g[k+1], eps(k+1)), (g[k+1], eps(k+1))])
            assert ec == ed
            inner = sympy.expand(gc - gd)        # times y^ec
            gt, et = _fold([(g[k], eps(k)), (inner, ec)])
            assert et == 0                        # always lands even
            g[m] = _exact_div(gt, 2 * F_X)        # psi_2k = g * y
    return g

# ---------- F_{p^k} arithmetic mod an irreducible h ----------

def monic_mod(coeffs, p):
    inv = pow(coeffs[-1], -1, p)
    return [c * inv % p for c in coeffs]

def pmulmod(a, b, h, p):
    k = len(h) - 1
    c = [0] * (len(a) + len(b) - 1)
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                c[i + j] = (c[i + j] + ai * bj) % p
    for i in range(len(c) - 1, k - 1, -1):
        ci = c[i]
        if ci:
            c[i] = 0
            for j in range(k):
                c[i - k + j] = (c[i - k + j] - ci * h[j]) % p
    c = c[:k]
    c += [0] * (k - len(c))
    return c

def ppowmod(a, e, h, p):
    r = [1] + [0] * (len(h) - 2)
    b = list(a)
    while e:
        if e & 1:
            r = pmulmod(r, b, h, p)
        b = pmulmod(b, b, h, p)
        e >>= 1
    return r

def exact_order_field(t, bound_fac, h, p):
    M = 1
    for q, m in bound_fac.items():
        M *= q**m
    one = [1] + [0] * (len(h) - 2)
    assert ppowmod(t, M, h, p) == one
    o = M
    for q in bound_fac:
        while o % q == 0 and ppowmod(t, o // q, h, p) == one:
            o //= q
    return o

# ---------- per-(r, p) analysis ----------

def analyze(g_r, r, p, kmax=8):
    gp = Poly(g_r, X, modulus=p)
    fl = gp.factor_list()[1]
    degs = sorted(Poly(f, X).degree() for f, _ in fl)
    cells = []
    for f, _ in fl:
        fp = Poly(f, X, modulus=p)
        k = fp.degree()
        if k > kmax:
            continue
        h = monic_mod([int(c) % p for c in reversed(fp.all_coeffs())], p)
        if k == 1:
            # F_p cell: x-value in F_p
            cells.append({"k": 1, "kprime": 1, "twist": "+"})
            continue
        t = [0, 1] + [0] * (k - 2)
        one = [1] + [0] * (k - 1)
        neg_t = [(-c) % p for c in t]
        # E2: Frobenius closure
        assert ppowmod(t, p**k, h, p) == t, "E2 fail"
        kprime, sign = None, None
        for e in range(1, k + 1):
            te = ppowmod(t, p**e, h, p)
            if te == t:
                kprime, sign = e, "+"
                break
            if te == neg_t:
                kprime, sign = e, "-"
                break
        if kprime is None:
            cells.append({"k": k, "kprime": None, "twist": "mixed"})
            continue
        # exact order of t, bounded by 2(p^{k'} - 1) if twisted else p^{k'}-1
        bound_fac, resolved = factor_resolved(2)
        for e in divisors(kprime):
            fe, ok = factor_resolved(phi_val(e, p))
            resolved = resolved and ok
            for q, m in fe.items():
                bound_fac[q] = bound_fac.get(q, 0) + m
        cell = {"k": k, "kprime": kprime, "twist": sign,
                "bound_resolved": resolved}
        if resolved:
            o = exact_order_field(t, bound_fac, h, p)
            cell["ord"] = o
            # E3 sharpness: large primes of levels e | k' divide ord(t);
            # levels e with e not dividing k' are absent automatically,
            # since ord | 2(p^{k'}-1) and gcd(Phi_e(p), p^{k'}-1) is small.
            small = 2 * r * k
            present = []
            for e in divisors(kprime):
                for q in factor_resolved(phi_val(e, p))[0]:
                    if q > small:
                        present.append(o % q == 0)
            cell["sharp_present"] = [sum(present), len(present)]
        cells.append(cell)
    return degs, cells

def burden_ell(r):
    best = None
    for m in divisors(r - 1):
        b = m // __import__("math").gcd(m, 4)
        if b >= 2 and (best is None or b < best):
            best = b
    return best

def main():
    report = {"cases": [], "burden_table": []}
    psi = division_polys(17)
    for r in (13, 17):
        g = psi[r]
        assert Poly(g, X).degree() == (r*r - 1) // 2, "E1 degree"
    print("E1 psi_r degrees ok: deg psi_13 = 84, deg psi_17 = 144")

    n_cells = 0
    n_exc_k_ok = 0
    n_exc = 0
    floor_seen = {13: [], 17: []}
    sharp_tot = [0, 0]
    for r in (13, 17):
        primes = [p for p in primerange(5, 600)
                  if p % 4 == 1 and p != r][:10]
        for p in primes:
            degs, cells = analyze(psi[r], r, p)
            assert sum(degs) == (r*r - 1) // 2, "E1 factor degrees"
            for c in cells:
                c.update({"r": r, "p": p})
                report["cases"].append(c)
                n_cells += 1
                if c["kprime"] == 1:
                    n_exc += 1
                    n_exc_k_ok += c["k"] <= 2
                elif c["kprime"] is not None:
                    floor_seen[r].append(c["kprime"])
                if "sharp_present" in c:
                    sharp_tot[0] += c["sharp_present"][0]
                    sharp_tot[1] += c["sharp_present"][1]
            kp = sorted(set(c["kprime"] for c in cells
                            if c["kprime"] and c["kprime"] > 1))
            print(f"r={r} p={p:4d}: factor degrees {sorted(set(degs))}, "
                  f"valid cells k' in {kp}")

    print(f"\nE3 exceptional (k'=1, lambda in mu_4) cells: {n_exc}, "
          f"all with k <= 2: {n_exc_k_ok}/{n_exc}")
    print(f"E3 sharpness (large primes of levels e | k' divide ord): "
          f"{sharp_tot[0]}/{sharp_tot[1]}")
    f13 = min(floor_seen[13]) if floor_seen[13] else None
    f17 = min(floor_seen[17]) if floor_seen[17] else None
    print(f"E4 measured valid-cell floor: r=13 -> {f13} (predicted 3), "
          f"r=17 -> {f17} (predicted 2)")
    assert f13 == 3 and f17 == 2

    print("\nE5 burden tables (elliptic j=1728 vs torus/AG2):")
    for r in sorted(A11_TABLE):
        be = burden_ell(r)
        bt = burden(r)[0]
        report["burden_table"].append({"r": r, "elliptic": be, "torus": bt})
        print(f"  r={r:3d}: elliptic {be if be else 'degenerate'}   "
              f"torus {bt}")
    assert min(b["elliptic"] for b in report["burden_table"]
               if b["elliptic"]) == 2

    report["summary"] = {"cells": n_cells, "exceptional": n_exc,
                         "sharp": sharp_tot,
                         "floor": {"r13": f13, "r17": f17}}
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"\nwrote {OUT_JSON}")

if __name__ == "__main__":
    main()
