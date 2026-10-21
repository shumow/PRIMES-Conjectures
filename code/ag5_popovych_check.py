#!/usr/bin/env python3
"""AG5: numerical verification of the Popovych burden jump.

Companion to code/ag2_torus_check.py (whose helpers are reused). Verifies,
for the second Popovych section X+2 (math in doc/arith-geom.tex sec. 5):

  P1. Frobenius matching holds for X+2 too:
        (X+2)^p = X^p + 2 (mod p, X^r - 1)   [uses 2^p = 2].
  P2. NO inversion collapse: for d = ord_r(p) even,
        (X+2)^{2r(p^{d/2}-1)} != 1 (mod p, Phi_r)
      (the Lemma-3.2 identity fails for X+2; exceptions ~ 1/ell rare).
  P3. Exact order rho'_r(p) of X+2 in (F_p[X]/Phi_r)^* and its level
      support: the TOP level e = d is genuinely present (for even d this
      is the level the X-1 section never sees).
  P4. Sharpness: large primes ell | Phi_e(p) for ALL e | d divide rho'.
  P5. Burden tables: burden_Pop(r) = min{d : d | r-1, d >= 3} (= least
      divisor of r-1 that is >= 3) vs burden_Agr(r) from AG2/A11.
  P6. Global independence data: gcd(r, 2^r + 1) = gcd(r, 3) = 1 for prime
      r != 3, so the ideals (zeta-1) | (r) and (zeta+2) | ((2^r+1)/3) have
      disjoint support (Lemma 5.2's arithmetic input).
  P7. Dickman cost table at the frozen harvest spec (doc/harvest-spec.md):
      the supply tax of the extra quadratic level Phi_4(p) (r=5) or
      Phi_3(p) (d=3 moduli), ~ 2x the bits of p.

Degenerate p excluded from sampling: p = 3 (there -2 = 1, so X+2 = X-1 and
the two sections coincide) and p | 2^r + 1 (X+2 is a zero divisor in some
component). Both are finite sets for fixed r.

Deterministic; writes data/generated/ag5_popovych_check.json.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sympy import primerange
from ag2_torus_check import (polpow, eq_mod_phi, one_mod_phi, ord_mod,
                             phi_val, divisors, factor_resolved, exact_order,
                             A11_TABLE, burden)

OUT_JSON = os.path.join(os.path.dirname(os.path.abspath(__file__)), os.pardir,
                        "data", "generated", "ag5_popovych_check.json")

# ---------- Dickman rho ----------

def dickman_grid(umax=14.0, h=0.001):
    n = int(umax / h) + 1
    rho = [1.0] * n
    for i in range(int(1 / h), n - 1):
        um = i * h + h / 2                 # midpoint
        t = (um - 1.0) / h                 # interpolate rho(um - 1)
        k = int(t)
        r_mid = rho[k] + (t - k) * (rho[k + 1] - rho[k])
        rho[i + 1] = rho[i] - h * r_mid / um
    return rho, h

RHO_GRID, RHO_H = dickman_grid()

def dickman(u):
    if u <= 1:
        return 1.0
    t = u / RHO_H
    k = int(t)
    if k + 1 >= len(RHO_GRID):
        return 0.0
    return RHO_GRID[k] + (t - k) * (RHO_GRID[k + 1] - RHO_GRID[k])

# ---------- the X+2 checks ----------

def check_case_xp2(r, d, p_count, p_max):
    dprime_agr = d // 2 if d % 2 == 0 else d
    levels_all = divisors(d)
    rows = []
    primes = []
    bad = 2**r + 1
    for p in primerange(5, p_max):
        if p == r or bad % p == 0:
            continue
        if ord_mod(p, r) == d:
            primes.append(p)
        if len(primes) >= p_count:
            break
    for p in primes:
        xp2 = [2 % p, 1] + [0] * (r - 2)         # X + 2
        row = {"r": r, "p": p, "d": d}

        # P1: Frobenius matching for X+2
        lhs = polpow(xp2, p, p, r)
        rhs = [2 % p] + [0] * (r - 1)
        rhs[p % r] = (rhs[p % r] + 1) % p        # X^{p mod r} + 2
        row["frobenius_ok"] = eq_mod_phi(lhs, rhs, p, r)

        # P2: the X-1 collapse bound does NOT kill X+2 (even d only)
        if d % 2 == 0:
            bound_agr = 2 * r * (p**(d // 2) - 1)
            row["no_collapse"] = not one_mod_phi(
                polpow(xp2, bound_agr, p, r), p, r)

        # exact order rho' within p^d - 1 = prod_{e|d} Phi_e(p)
        bound_fac, resolved = factor_resolved(2 * r)
        for e in levels_all:
            fe, ok = factor_resolved(phi_val(e, p))
            resolved = resolved and ok
            for q, m in fe.items():
                bound_fac[q] = bound_fac.get(q, 0) + m
        row["bound_resolved"] = resolved
        if not resolved:
            rows.append(row)
            continue
        rho2 = exact_order(xp2, bound_fac, p, r)
        row["rho_prime"] = rho2

        # P3: top level e = d genuinely present in rho'
        sub = 2 * r
        for e in levels_all:
            if e != d:
                sub *= phi_val(e, p)
        row["top_level_needed"] = not one_mod_phi(
            polpow(xp2, sub, p, r), p, r)

        # P4: sharpness over ALL levels e | d
        small = 2 * r * d
        sharp = []
        for e in levels_all:
            for q in factor_resolved(phi_val(e, p))[0]:
                if q > small:
                    sharp.append({"level": e, "ell": q,
                                  "divides_rho_prime": rho2 % q == 0})
        row["sharpness"] = sharp
        row["agr_levels"] = divisors(dprime_agr)
        rows.append(row)
    return rows

def burden_pop(r):
    """min{d : d | r-1, d >= 3} -- full depth for every admissible d."""
    for d in divisors(r - 1):
        if d >= 3:
            return d
    return None

def main():
    report = {"cases": [], "burden_table": [], "independence": [],
              "dickman": {}, "summary": {}}

    # sanity of the Dickman grid against standard values
    for u, ref in [(2, 3.0685e-1), (5, 3.547e-4), (10, 2.77e-11)]:
        v = dickman(u)
        assert abs(v - ref) / ref < 0.02, (u, v, ref)
    print(f"Dickman grid ok: rho(2)={dickman(2):.4e} rho(5)={dickman(5):.4e} "
          f"rho(10)={dickman(10):.4e}")

    cases = [(5, 4, 12, 5000), (13, 4, 10, 4000), (41, 4, 6, 3000),
             (7, 6, 8, 2000), (7, 3, 10, 3000), (11, 5, 6, 1200),
             (23, 11, 4, 130)]
    n_nc = n_nc_ok = n_top = n_top_ok = 0
    sharp_all = []
    for (r, d, k, pmax) in cases:
        rows = check_case_xp2(r, d, k, pmax)
        report["cases"].extend(rows)
        for row in rows:
            assert row["frobenius_ok"], f"P1 FAIL r={r} p={row['p']}"
            if "no_collapse" in row:
                n_nc += 1
                n_nc_ok += row["no_collapse"]
            if "top_level_needed" in row:
                n_top += 1
                n_top_ok += row["top_level_needed"]
            sharp_all.extend(row.get("sharpness", []))
        got = sum(1 for row in rows if "rho_prime" in row)
        print(f"r={r:3d} d={d:2d}: {len(rows)} primes sampled, "
              f"{got} exact orders of X+2 computed")

    n_sharp = len(sharp_all)
    n_div = sum(1 for s in sharp_all if s["divides_rho_prime"])
    exp_misses = sum(1.0 / s["ell"] for s in sharp_all)
    print(f"\nP2 no X-1-style collapse for X+2 (even d): {n_nc_ok}/{n_nc}")
    print(f"P3 top level e=d present in ord(X+2): {n_top_ok}/{n_top}")
    print(f"P4 sharpness over all levels e|d: {n_div}/{n_sharp} "
          f"({n_sharp - n_div} exceptions; ~{exp_misses:.2f} expected)")
    for s in sharp_all:
        if not s["divides_rho_prime"]:
            print(f"   exception: level {s['level']}, ell = {s['ell']}")

    print("\nP5 burden tables (Agrawal from AG2/A11 vs Popovych pair):")
    for r in sorted(A11_TABLE):
        b_agr, d_agr = burden(r)
        b_pop = burden_pop(r)
        report["burden_table"].append(
            {"r": r, "agrawal": b_agr, "popovych": b_pop,
             "delta": b_pop - b_agr})
        print(f"  r={r:3d}: Agrawal {b_agr} (d={d_agr})   "
              f"Popovych {b_pop}   (+{b_pop - b_agr})")
    assert min(burden(r)[0] for r in A11_TABLE) == 2
    assert min(burden_pop(r) for r in A11_TABLE) == 3
    assert burden_pop(5) == 4 and burden(5)[0] == 2

    print("\nP6 independence (disjoint ideal support of zeta-1, zeta+2):")
    for r in sorted(A11_TABLE):
        g = __import__("math").gcd(r, 2**r + 1)
        report["independence"].append({"r": r, "norm2": (2**r + 1) // 3,
                                       "gcd_r": g})
        assert g == 1
    print("  gcd(r, 2^r+1) = 1 for all tested r (supports disjoint).")

    # P7: Dickman cost at the frozen spec (harvest-spec.md): p ~ 51 bits
    import math
    p_bits = 51.0
    extra_bits = 2 * p_bits            # Phi_4(p) = p^2+1 or Phi_3 ~ p^2
    ratio_measured, pool_measured = 13.8, 2.5e5
    print("\nP7 supply tax of the extra quadratic level at the frozen spec")
    print(f"   (p ~ {p_bits:.0f} bits; extra level ~ {extra_bits:.0f} bits):")
    for base, bname in [(1259, "Q+ base B=1259"), (12590, "B'=12590")]:
        u = extra_bits / math.log2(base)
        tax = dickman(u)
        report["dickman"][bname] = {"u": u, "tax": tax,
                                    "ratio_after": ratio_measured * tax,
                                    "pool_after": pool_measured * tax}
        print(f"   {bname:17s}: u = {u:5.2f}, rho(u) = {tax:.2e}  ->  "
              f"ratio {ratio_measured} -> {ratio_measured*tax:.1e}, "
              f"pool {pool_measured:.1e} -> {pool_measured*tax:.1e}")

    report["summary"] = {
        "p2_no_collapse": [n_nc_ok, n_nc],
        "p3_top_needed": [n_top_ok, n_top],
        "p4_sharpness": [n_div, n_sharp],
        "p4_expected_misses": exp_misses,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"\nwrote {OUT_JSON}")

if __name__ == "__main__":
    main()
