#!/usr/bin/env python3
"""AG2: numerical verification of the torus dimension-count theorem.

Verifies, for sample primes p and AKS moduli r (deliverable of plan item AG2,
doc/arith-geom-plan.md; math in doc/arith-geom.tex sec. 3):

  V1. Frobenius matching: (X-1)^{p^k} = X^{p^k} - 1 in F_p[X]/(X^r-1).
  V2. Inversion collapse (Lemma B): for d = ord_r(p) even,
        (X-1)^{p^{d/2}-1} = -X^{-1}  (mod p, Phi_r(X)),
      hence rho_r(p) | 2r(p^{d/2}-1) = 2r * prod_{e | d/2} Phi_e(p).
  V3. Exact order rho_r(p) of X-1 in (F_p[X]/Phi_r)^*, and its level
      attribution: which cyclotomic levels e carry the large-prime part.
  V4. Sharpness: for large primes l | Phi_e(p) (e | d', l coprime to 2rd),
      l divides rho_r(p) with frequency ~ 1 - 1/l (exceptions tallied).
  V5. No further collapse below d' (odd d: rho does not retreat to lower
      levels; even d: the top level e = d/2 genuinely appears).
  V6. Burden table: burden(r) = min_{d | r-1, d >= 3} (d/2 if even else d)
      reproduces the A11 measured table (data/FINDINGS.md sec. A11).

All arithmetic is done in the cyclic ring F_p[X]/(X^r-1); congruence mod
Phi_r(X) is tested via "all coefficients of the difference are equal"
(f = g mod Phi_r  iff  f - g is a scalar multiple of 1 + X + ... + X^{r-1}).

Deterministic; writes data/generated/ag2_torus_check.json.
"""

import json
import os
from sympy import primerange, factorint, isprime
from sympy.polys.specialpolys import cyclotomic_poly

OUT_JSON = os.path.join(os.path.dirname(__file__), os.pardir,
                        "data", "generated", "ag2_torus_check.json")

# ---------- cyclic-ring arithmetic in F_p[X]/(X^r - 1) ----------

def polmul(a, b, p, r):
    c = [0] * r
    for i, ai in enumerate(a):
        if ai:
            for j, bj in enumerate(b):
                if bj:
                    k = i + j
                    if k >= r:
                        k -= r
                    c[k] = (c[k] + ai * bj) % p
    return c

def polpow(g, e, p, r):
    result = [1] + [0] * (r - 1)
    base = list(g)
    while e:
        if e & 1:
            result = polmul(result, base, p, r)
        base = polmul(base, base, p, r)
        e >>= 1
    return result

def eq_mod_phi(f, g, p, r):
    """f = g (mod p, Phi_r) for degree-<r representatives mod X^r - 1."""
    d0 = (f[0] - g[0]) % p
    return all((f[i] - g[i]) % p == d0 for i in range(1, r))

def one_mod_phi(f, p, r):
    return eq_mod_phi(f, [1] + [0] * (r - 1), p, r)

# ---------- number-theoretic helpers ----------

def ord_mod(a, m):
    a %= m
    assert a != 0
    o, x = 1, a
    while x != 1:
        x = x * a % m
        o += 1
    return o

def phi_val(e, p):
    return int(cyclotomic_poly(e, p))

def divisors(n):
    return sorted(d for d in range(1, n + 1) if n % d == 0)

def factor_resolved(v):
    """Factor v; return (dict prime->mult, fully_resolved: bool)."""
    if v == 1:
        return {}, True
    if v < 10**24:
        return {int(q): int(m) for q, m in factorint(v).items()}, True
    fac = factorint(v, limit=10**6)
    out, resolved = {}, True
    for q, m in fac.items():
        q = int(q)
        if isprime(q):
            out[q] = out.get(q, 0) + int(m)
        elif q < 10**24:
            for q2, m2 in factorint(q).items():
                out[int(q2)] = out.get(int(q2), 0) + int(m2) * int(m)
        else:
            resolved = False
    return out, resolved

def exact_order(g, bound_fac, p, r):
    """Exact order of g in (F_p[X]/Phi_r)^*, given factored multiple of it."""
    M = 1
    for q, m in bound_fac.items():
        M *= q**m
    assert one_mod_phi(polpow(g, M, p, r), p, r), "bound is not a multiple of ord"
    o = M
    for q in bound_fac:
        while o % q == 0 and one_mod_phi(polpow(g, o // q, p, r), p, r):
            o //= q
    return o

# ---------- the checks ----------

def check_case(r, d, p_count, p_max):
    """Run V1-V5 for sample primes p with ord_r(p) = d."""
    dprime = d // 2 if d % 2 == 0 else d
    levels = divisors(dprime)
    rows = []
    primes = []
    for p in primerange(3, p_max):
        if p == r:
            continue
        if ord_mod(p, r) == d:
            primes.append(p)
        if len(primes) >= p_count:
            break
    for p in primes:
        xm1 = [(-1) % p, 1] + [0] * (r - 2)     # X - 1
        row = {"r": r, "p": p, "d": d, "dprime": dprime}

        # V1: Frobenius matching at k = 1
        lhs = polpow(xm1, p, p, r)
        rhs = [(-1) % p] + [0] * (r - 1)
        rhs[p % r] = (rhs[p % r] + 1) % p        # X^{p mod r} - 1
        row["frobenius_ok"] = eq_mod_phi(lhs, rhs, p, r)

        # V2: inversion collapse identity (even d only)
        if d % 2 == 0:
            e2 = p**(d // 2)
            lhs = polpow(xm1, e2, p, r)
            neg_xinv = [0] * r
            neg_xinv[r - 1] = (-1) % p           # -X^{-1} = -X^{r-1}
            coll = polmul(neg_xinv, xm1, p, r)   # -X^{-1}(X-1)
            row["collapse_identity_ok"] = eq_mod_phi(lhs, coll, p, r)
            bound = 2 * r * (p**(d // 2) - 1)
            row["divides_2r_bound_ok"] = one_mod_phi(
                polpow(xm1, bound, p, r), p, r)

        # factored order bound from the level decomposition
        bound_fac, resolved = factor_resolved(2 * r)
        for e in levels:
            fe, ok = factor_resolved(phi_val(e, p))
            resolved = resolved and ok
            for q, m in fe.items():
                bound_fac[q] = bound_fac.get(q, 0) + m
        row["bound_resolved"] = resolved
        if not resolved:
            rows.append(row)
            continue

        # V3: exact order and level attribution
        rho = exact_order(xm1, bound_fac, p, r)
        row["rho"] = rho

        # V4: sharpness for large primes per level
        small = 2 * r * d
        sharp = []
        for e in levels:
            for q in factor_resolved(phi_val(e, p))[0]:
                if q > small:
                    sharp.append({"level": e, "ell": q,
                                  "divides_rho": rho % q == 0})
        row["sharpness"] = sharp

        # V5: no collapse below d' -- rho must NOT divide the sub-bound
        # obtained by removing the top level d' (unless top is trivial).
        if dprime > 1:
            sub = 2 * r
            for e in levels:
                if e != dprime:
                    sub *= phi_val(e, p)
            row["top_level_needed"] = not one_mod_phi(
                polpow(xm1, sub, p, r), p, r)
        rows.append(row)
    return rows

# A11 measured table (data/FINDINGS.md, 2026-08-24): r -> (best d, degree)
A11_TABLE = {5: (4, 2), 7: (3, 3), 11: (5, 5), 13: (4, 2), 17: (4, 2),
             19: (3, 3), 23: (11, 11), 29: (4, 2), 31: (3, 3), 37: (4, 2),
             41: (4, 2)}

def burden(r):
    """min over valid d of the dimension count; returns (burden, argmin d)."""
    best = None
    for d in divisors(r - 1):
        if d < 3:
            continue                     # ord_r(n) > 2 forces d_p >= 3
        b = d // 2 if d % 2 == 0 else d
        if best is None or b < best[0] or (b == best[0] and d < best[1]):
            best = (b, d)
    return best

def main():
    report = {"cases": [], "burden_table": [], "summary": {}}

    cases = [(5, 4, 12, 5000), (13, 4, 10, 4000), (41, 4, 6, 3000),
             (7, 3, 10, 3000), (7, 6, 8, 2000), (19, 3, 8, 2000),
             (11, 5, 8, 1200), (23, 11, 5, 130)]
    n_id = n_id_ok = n_top = n_top_ok = 0
    sharp_all = []
    for (r, d, k, pmax) in cases:
        rows = check_case(r, d, k, pmax)
        report["cases"].extend(rows)
        for row in rows:
            assert row["frobenius_ok"], f"V1 FAIL r={r} p={row['p']}"
            if "collapse_identity_ok" in row:
                n_id += 1
                n_id_ok += row["collapse_identity_ok"] and \
                    row["divides_2r_bound_ok"]
                assert row["collapse_identity_ok"], \
                    f"V2 FAIL r={r} p={row['p']}"
                assert row["divides_2r_bound_ok"], \
                    f"V2b FAIL r={r} p={row['p']}"
            if "top_level_needed" in row:
                n_top += 1
                n_top_ok += row["top_level_needed"]
            sharp_all.extend(row.get("sharpness", []))
        got = sum(1 for row in rows if "rho" in row)
        print(f"r={r:3d} d={d:2d}: {len(rows)} primes sampled, "
              f"{got} exact orders computed")

    n_sharp = len(sharp_all)
    n_div = sum(1 for s in sharp_all if s["divides_rho"])
    exceptions = [s for s in sharp_all if not s["divides_rho"]]
    exp_misses = sum(1.0 / s["ell"] for s in sharp_all)

    print(f"\nV2 inversion-collapse identity: {n_id_ok}/{n_id} pass")
    print(f"V4 sharpness: {n_div}/{n_sharp} large primes divide rho "
          f"({n_sharp - n_div} exceptions; ~{exp_misses:.2f} expected "
          f"from the 1/ell model)")
    for s in exceptions:
        print(f"   exception: level {s['level']}, ell = {s['ell']}")
    print(f"V5 top level needed: {n_top_ok}/{n_top}"
          f" ({n_top - n_top_ok} collapses; small-probability events)")

    print("\nV6 burden table vs A11 (data/FINDINGS.md):")
    all_match = True
    for r, (d_a11, deg_a11) in sorted(A11_TABLE.items()):
        b, d_star = burden(r)
        match = (b == deg_a11) and (d_star == d_a11)
        all_match = all_match and match
        report["burden_table"].append(
            {"r": r, "burden": b, "argmin_d": d_star,
             "a11_degree": deg_a11, "a11_d": d_a11, "match": match})
        print(f"  r={r:3d}: burden={b} at d={d_star}  "
              f"(A11: degree {deg_a11} at d {d_a11})  "
              f"{'OK' if match else 'MISMATCH'}")
    assert all_match, "V6 FAIL: burden formula does not reproduce A11"

    report["summary"] = {
        "v2_identity": [n_id_ok, n_id],
        "v4_sharpness": [n_div, n_sharp],
        "v4_expected_misses": exp_misses,
        "v5_top_needed": [n_top_ok, n_top],
        "v6_all_match": all_match,
    }
    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(report, fh, indent=1)
    print(f"\nwrote {OUT_JSON}")

if __name__ == "__main__":
    main()
