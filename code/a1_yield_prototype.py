#!/usr/bin/env python3
"""A1 yield calibration prototype (PLAN.md Track A).

Partition-first harvester, measurement mode. For each grid cell
(B, B'-ratio, j): Q+ = odd primes <= B minus {5}; Q- = primes in (B, B'].
Sample N random j-subsets of Q- (squarefree m = product), and measure, per
realized bit-size bin of m:
    n_sampled -> n_mod40 (m = 1 mod 40) -> n_side_smooth ((m+1)/2 fully
    Q+-smooth) -> n_prime (2m+1 BPSW) = hits.
Also records, for hits: which Q- primes and which Q+ max-exponents occur
(demand accounting), and for near-misses the size of the blocking cofactor.

Output: data/generated/a1_yield_grid.json (+ per-cell progress lines).
Deterministic (seeded per cell).
"""
import json, math, os, random, sys, time
from phase1a_calibration import primes_upto, is_prime

GEN = os.path.join(os.path.dirname(__file__), "..", "data", "generated")

def run_cell(B, ratio, j, N, rng):
    Bp = B * ratio
    all_p = primes_upto(Bp)
    Qplus = [q for q in all_p if 2 < q <= B and q != 5]
    Qminus = [q for q in all_p if B < q <= Bp]
    t = len(Qminus)
    bins = {}
    def bin_of(m): return m.bit_length()
    demand_minus, demand_plus = set(), {}
    nearmiss = []
    for it in range(N):
        qs = rng.sample(Qminus, j)
        m = 1
        for q in qs: m *= q
        b = bin_of(m)
        st = bins.setdefault(b, [0, 0, 0, 0])   # sampled, mod40, smooth, prime
        st[0] += 1
        if m % 40 != 1:
            continue
        st[1] += 1
        v = (m + 1) // 2
        vexp = {}
        for q in Qplus:
            if q > v: break
            e = 0
            while v % q == 0:
                v //= q; e += 1
            if e: vexp[q] = e
        if v != 1:
            if v.bit_length() <= 64 and len(nearmiss) < 50000:
                nearmiss.append(v.bit_length())
            continue
        st[2] += 1
        p = 2 * m + 1
        if not is_prime(p):
            continue
        st[3] += 1
        demand_minus.update(qs)
        for q, e in vexp.items():
            demand_plus[q] = max(demand_plus.get(q, 0), e)
    lam_minus = sum(math.log2(q) for q in demand_minus)
    lam_plus = sum(e * math.log2(q) for q, e in demand_plus.items())
    total_hits = sum(s[3] for s in bins.values())
    total_smooth = sum(s[2] for s in bins.values())
    return dict(B=B, Bprime=Bp, t=t, n_Qplus=len(Qplus), j=j, N=N,
                bins={str(k): v for k, v in sorted(bins.items())},
                hits=total_hits, side_smooth=total_smooth,
                distinct_Qminus_used=len(demand_minus),
                lambda_minus_bits=round(lam_minus, 1),
                lambda_plus_bits=round(lam_plus, 1),
                nearmiss_cofactor_bits_histogram={
                    str(b): nearmiss.count(b) for b in sorted(set(nearmiss))},
                log2_comb_t_j=round(math.lgamma(t + 1) / math.log(2)
                                    - math.lgamma(j + 1) / math.log(2)
                                    - math.lgamma(t - j + 1) / math.log(2), 1))

def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 2_000_000
    grid = [(B, r, j)
            for B in (547, 1259, 2003)
            for r in (5, 10)
            for j in (3, 4)]
    results = []
    for i, (B, r, j) in enumerate(grid):
        rng = random.Random(hash((B, r, j)) & 0xFFFFFFFF)
        t0 = time.time()
        cell = run_cell(B, r, j, N, rng)
        cell["seconds"] = round(time.time() - t0, 1)
        results.append(cell)
        smoothrate = cell["side_smooth"] / max(1, sum(
            s[1] for s in ({int(k): v for k, v in cell["bins"].items()}).values()))
        print(f"[{i+1}/{len(grid)}] B={B} B'={B*r} j={j}: "
              f"hits={cell['hits']} smooth={cell['side_smooth']} "
              f"(rate|mod40={smoothrate:.2e}) "
              f"lam-={cell['lambda_minus_bits']} lam+={cell['lambda_plus_bits']} "
              f"({cell['seconds']}s)", flush=True)
    with open(os.path.join(GEN, "a1_yield_grid.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("saved data/generated/a1_yield_grid.json")

if __name__ == "__main__":
    main()
