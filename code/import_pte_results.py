#!/usr/bin/env python3
"""Import and normalize the PTE sieve results from microsoft/twin-smooth-integers.

Reads data/raw/microsoft-twin-smooth-integers/*.txt (provenance in
PROVENANCE.md there), reconstructs each twin pair m = (p-1)/2, m+1 = (p+1)/2,
factors both sides, verifies the claimed smoothness bound and primality flag,
and derives the Lenstra-Pomerance-relevant fields documented in
data/generated/README.md.

Outputs (all under data/generated/):
  pte_records.jsonl.gz        one JSON object per upstream record (full schema)
  pte_prime_candidates.csv    the records with p prime (pool-candidate view)
  pte_summary.json            per-file and corpus-level statistics

Every record carries source_result_filename + line_number for provenance.
"""
import csv, gzip, json, math, os, random, re, sys
from collections import Counter
from math import gcd
from sympy import isprime


def _iroot(n, k):
    """Largest r with r**k <= n."""
    if n < 2:
        return n
    r = 1 << ((n.bit_length() + k - 1) // k)
    while True:
        nr = ((k - 1) * r + n // r ** (k - 1)) // k
        if nr >= r:
            return r
        r = nr


def _perfect_power(n):
    """Return (w, k) with w**k == n and k maximal >= 2, else None."""
    for k in range(int(math.log2(n)), 1, -1):
        w = _iroot(n, k)
        if w ** k == n:
            return w, k
    return None


def _brent_rho(n, max_iters=400000, attempts=4):
    """Iteration-capped Brent rho; returns a nontrivial factor or None."""
    rng = random.Random(0xC0FFEE ^ n)
    for _ in range(attempts):
        y, c, m = rng.randrange(1, n), rng.randrange(1, n), 128
        g, r, q, it = 1, 1, 1, 0
        while g == 1 and it < max_iters:
            x = y
            for _ in range(r):
                y = (y * y + c) % n
            k = 0
            while k < r and g == 1:
                ys = y
                for _ in range(min(m, r - k)):
                    y = (y * y + c) % n
                    q = q * abs(x - y) % n
                g = gcd(q, n)
                k += m
                it += m
            r *= 2
        if g == n:
            g = 1
            while g == 1:
                ys = (ys * ys + c) % n
                g = gcd(abs(x - ys), n)
        if 1 < g < n:
            return g
    return None


_TRIAL = []
def _trial_primes():
    if not _TRIAL:
        N = 1 << 16
        s = bytearray([1]) * (N + 1)
        for i in range(2, 257):
            if s[i]:
                s[i * i::i] = bytearray(len(s[i * i::i]))
        _TRIAL.extend(i for i in range(2, N + 1) if s[i])
    return _TRIAL


def factorize(n):
    """Trial division to 2^16 + perfect-power + capped Brent rho + BPSW.

    Returns (fac, unfactored): fac maps prime -> exponent; unfactored is a
    list of composite cofactors rho could not split within its cap (these
    occur only for records that are not fully smooth; recorded, not hidden).
    """
    fac, unfactored = {}, []
    for p in _trial_primes():
        if p * p > n:
            break
        while n % p == 0:
            fac[p] = fac.get(p, 0) + 1
            n //= p
    stack = [(n, 1)] if n > 1 else []
    while stack:
        v, mult = stack.pop()
        if v == 1:
            continue
        if isprime(v):
            fac[v] = fac.get(v, 0) + mult
            continue
        pw = _perfect_power(v)
        if pw:
            stack.append((pw[0], mult * pw[1]))
            continue
        d = _brent_rho(v)
        if d is None:
            unfactored.append((v, mult))
            continue
        stack += [(d, mult), (v // d, mult)]
    return fac, unfactored

RAW = os.path.join(os.path.dirname(__file__), "..", "data", "raw",
                   "microsoft-twin-smooth-integers")
GEN = os.path.join(os.path.dirname(__file__), "..", "data", "generated")

FNAME_RE = re.compile(
    r"size-(?P<deg>\d+)(?P<squ>-squ)?_(?P<logB>\d+)_(?P<xlo>\d+)_to_(?P<xhi>\d+)\.txt")
LINE_RE = re.compile(
    r"^(?P<sol>\d+), x=(?P<x>\d+), solution: \[(?P<A>[\d, ]+)\], "
    r"\[(?P<B>[\d, ]+)\], p=(?P<p>\d+), p prime\? (?P<prime>True|False)$")

def factor_side(n, bound):
    """Factor n; return (fac dict, unfactored list, lpf, fully_smooth)."""
    fac, unf = factorize(n)
    lpf = max(fac) if fac else 1
    ok = not unf and lpf <= bound
    return ({str(q): e for q, e in sorted(fac.items())},
            [[str(v), e] for v, e in unf], lpf, ok)

def main():
    os.makedirs(GEN, exist_ok=True)
    records, failures = [], []
    per_file = {}
    for fname in sorted(os.listdir(RAW)):
        m0 = FNAME_RE.match(fname)
        if not m0:
            continue
        deg, squ = int(m0["deg"]), bool(m0["squ"])
        B = 2 ** int(m0["logB"])
        stats = Counter()
        with open(os.path.join(RAW, fname)) as f:
            for lineno, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                if not line[0].isdigit():
                    stats["header_lines"] += 1
                    continue
                mo = LINE_RE.match(line)
                if not mo:
                    failures.append(dict(file=fname, line=lineno,
                                         reason="unparseable line"))
                    continue
                p = int(mo["p"])
                if p % 2 == 0:
                    failures.append(dict(file=fname, line=lineno,
                                         reason="p even"))
                    continue
                m = (p - 1) // 2
                fac_m, unf_m, lpf_m, ok_m = factor_side(m, B)
                fac_m1, unf_m1, lpf_m1, ok_m1 = factor_side(m + 1, B)
                p_prime = isprime(p)
                claimed = mo["prime"] == "True"
                if p_prime != claimed:
                    failures.append(dict(file=fname, line=lineno,
                                         reason=f"primality flag mismatch "
                                                f"(claimed {claimed})"))
                # LP-derived fields (definitions: data/generated/README.md)
                lp_congruence_ok = (m % 40 == 1)
                minus_odd = [int(q) for q in fac_m if int(q) > 2]
                plus_odd = [int(q) for q in fac_m1 if int(q) > 2]
                rec = dict(
                    source="microsoft/twin-smooth-integers@f1b9a52",
                    source_result_filename=fname, line_number=lineno,
                    method=("PTE sieve (squares variant)" if squ
                            else "PTE sieve"),
                    pte_degree=deg, B=B,
                    x=mo["x"], pte_solution_id=int(mo["sol"]),
                    pte_roots_A=[int(t) for t in mo["A"].split(",")],
                    pte_roots_B=[int(t) for t in mo["B"].split(",")],
                    m=str(m), m_plus_1=str(m + 1), p=str(p),
                    bit_length_m=m.bit_length(), bit_length_p=p.bit_length(),
                    factorization_m=fac_m, factorization_m_plus_1=fac_m1,
                    unfactored_cofactors_m=unf_m,
                    unfactored_cofactors_m_plus_1=unf_m1,
                    lpf_m=lpf_m, lpf_m_plus_1=lpf_m1,
                    smooth_ok=bool(ok_m and ok_m1),
                    p_is_prime=bool(p_prime), p_prime_claimed=claimed,
                    LP_congruence_ok=lp_congruence_ok,
                    LP_minus_omega=len(minus_odd),
                    LP_plus_omega=len(plus_odd),
                    LP_minus_lpf=max(minus_odd) if minus_odd else 1,
                    LP_plus_lpf=max(plus_odd) if plus_odd else 1,
                )
                records.append(rec)
                stats["records"] += 1
                stats["p_prime"] += p_prime
                stats["smooth_ok"] += rec["smooth_ok"]
                stats["LP_congruence_ok"] += lp_congruence_ok
                stats["LP_eligible"] += (p_prime and lp_congruence_ok
                                         and rec["smooth_ok"])
        per_file[fname] = dict(stats)
        print(f"{fname}: {dict(stats)}")

    # de-duplicate identical twins found via different (x, solution) routes
    seen, unique = set(), 0
    for r in records:
        if r["m"] not in seen:
            seen.add(r["m"]); unique += 1

    # corpus-level side-compatibility statistics over LP-eligible records
    elig = [r for r in records
            if r["p_is_prime"] and r["LP_congruence_ok"] and r["smooth_ok"]]
    minus_primes, plus_primes = Counter(), Counter()
    for r in elig:
        for q in r["factorization_m"]:
            if int(q) > 2:
                minus_primes[int(q)] += 1
        for q in r["factorization_m_plus_1"]:
            if int(q) > 2:
                plus_primes[int(q)] += 1
    both_sides = sorted(set(minus_primes) & set(plus_primes))

    with gzip.open(os.path.join(GEN, "pte_records.jsonl.gz"), "wt") as f:
        for r in records:
            f.write(json.dumps(r) + "\n")

    prime_rows = [r for r in records if r["p_is_prime"]]
    with open(os.path.join(GEN, "pte_prime_candidates.csv"), "w",
              newline="") as f:
        cols = ["source_result_filename", "line_number", "B", "x",
                "pte_solution_id", "bit_length_p", "p",
                "LP_congruence_ok", "LP_minus_omega", "LP_plus_omega",
                "LP_minus_lpf", "LP_plus_lpf", "smooth_ok"]
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        for r in prime_rows:
            w.writerow(r)

    summary = dict(
        upstream_commit="f1b9a5275098565d5407d2ad869f8a34d49e6f69",
        files=per_file, total_records=len(records),
        unique_twins=unique, duplicates=len(records) - unique,
        p_prime_records=len(prime_rows),
        LP_congruence_ok_records=sum(r["LP_congruence_ok"] for r in records),
        LP_eligible_records=len(elig),
        parse_or_verify_failures=failures,
        side_compatibility=dict(
            eligible_records=len(elig),
            distinct_minus_side_primes=len(minus_primes),
            distinct_plus_side_primes=len(plus_primes),
            primes_demanded_on_both_sides=len(both_sides),
            example_conflicts=both_sides[:20],
        ),
    )
    with open(os.path.join(GEN, "pte_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ("files", "parse_or_verify_failures")},
                     indent=1))
    print(f"failures: {len(failures)}")

if __name__ == "__main__":
    main()
