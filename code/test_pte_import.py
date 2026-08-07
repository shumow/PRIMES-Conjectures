#!/usr/bin/env python3
"""Tests for the generated PTE dataset (data/generated/pte_records.jsonl.gz).

Verifies, for every record:
  V1  m_plus_1 == m + 1 and p == 2m + 1 (consecutiveness / reconstruction);
  V2  the stored factorizations multiply back to m and m+1 exactly;
  V3  every stored factor is prime and <= B  whenever smooth_ok is set
      (and that smooth_ok correctly flags any violation);
  V4  p_is_prime matches an independent Miller-Rabin check (own code, not
      sympy, so the two implementations cross-validate);
  V5  LP fields are consistent with the factorizations:
      LP_congruence_ok == (m % 40 == 1), omegas count distinct odd primes,
      lpf fields match;
  V6  provenance fields present and the source file exists in data/raw.
Exits nonzero on any failure; prints a summary.
"""
import gzip, json, os, sys

HERE = os.path.dirname(__file__)
GEN = os.path.join(HERE, "..", "data", "generated")
RAW = os.path.join(HERE, "..", "data", "raw", "microsoft-twin-smooth-integers")

def is_prime(n):
    if n < 2: return False
    for p in (2,3,5,7,11,13,17,19,23,29,31,37):
        if n % p == 0: return n == p
    d, s = n - 1, 0
    while d % 2 == 0: d //= 2; s += 1
    # deterministic for n < 3.3e24; for larger n this is a strong
    # probable-prime check on 12 fixed + 20 pseudorandom bases
    bases = [2,3,5,7,11,13,17,19,23,29,31,37]
    if n >= 3317044064679887385961981:
        x = 0x9E3779B97F4A7C15 ^ n
        for _ in range(20):
            x = (x * 6364136223846793005 + 1442695040888963407) % (1 << 64)
            bases.append(2 + x % (n - 3))
    for a in bases:
        x = pow(a, d, n)
        if x in (1, n - 1): continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1: break
        else: return False
    return True

def main():
    path = os.path.join(GEN, "pte_records.jsonl.gz")
    fails, n = [], 0
    for line in gzip.open(path, "rt"):
        r = json.loads(line); n += 1
        m, m1, p, B = int(r["m"]), int(r["m_plus_1"]), int(r["p"]), r["B"]
        tag = f'{r["source_result_filename"]}:{r["line_number"]}'
        if m1 != m + 1 or p != 2 * m + 1:
            fails.append((tag, "V1 reconstruction")); continue
        for key, ukey, val in (
                ("factorization_m", "unfactored_cofactors_m", m),
                ("factorization_m_plus_1", "unfactored_cofactors_m_plus_1",
                 m1)):
            prod = 1
            for q, e in r[key].items():
                prod *= int(q) ** e
            for v, e in r[ukey]:
                prod *= int(v) ** e
            if prod != val:
                fails.append((tag, f"V2 {key} product"))
        facs = [int(q) for q in r["factorization_m"]] + \
               [int(q) for q in r["factorization_m_plus_1"]]
        unf = r["unfactored_cofactors_m"] + r["unfactored_cofactors_m_plus_1"]
        all_ok = (not unf and all(is_prime(q) for q in facs)
                  and all(q <= B for q in facs))
        if r["smooth_ok"] != all_ok:
            fails.append((tag, "V3 smooth_ok flag"))
        if r["p_is_prime"] != is_prime(p):
            fails.append((tag, "V4 primality"))
        minus = [int(q) for q in r["factorization_m"] if int(q) > 2]
        plus = [int(q) for q in r["factorization_m_plus_1"] if int(q) > 2]
        if (r["LP_congruence_ok"] != (m % 40 == 1)
                or r["LP_minus_omega"] != len(minus)
                or r["LP_plus_omega"] != len(plus)
                or r["LP_minus_lpf"] != (max(minus) if minus else 1)
                or r["LP_plus_lpf"] != (max(plus) if plus else 1)):
            fails.append((tag, "V5 LP fields"))
        if not os.path.exists(os.path.join(RAW,
                                           r["source_result_filename"])):
            fails.append((tag, "V6 provenance"))
    print(f"{n} records checked, {len(fails)} failures")
    for tag, why in fails[:20]:
        print("  FAIL", tag, why)
    sys.exit(1 if fails else 0)

if __name__ == "__main__":
    main()
