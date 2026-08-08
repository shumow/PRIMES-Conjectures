#!/usr/bin/env python3
"""A2 extended yield grid: j in {3,4,5,6}, finer (B, B') around the A1 sweet
spot, with exponent-capped demand accounting. Produces the production-spec
projection and the G2 verdict. Output: data/generated/a2_grid.json.
"""
import json, math, os, random, sys, time
from phase1a_calibration import primes_upto, is_prime

GEN = os.path.join(os.path.dirname(__file__), "..", "data", "generated")

def cell(B, Bp, j, N, rng, ps):
    Qplus = [q for q in ps if 2 < q <= B and q != 5]
    Qminus = [q for q in ps if B < q <= Bp]
    t = len(Qminus)
    if t < j:
        return None
    hits = 0
    used_minus, used_plus = set(), set()
    bitsum = 0
    for _ in range(N):
        qs = rng.sample(Qminus, j)
        m = 1
        for q in qs:
            m *= q
        if m % 40 != 1:
            continue
        v = (m + 1) // 2
        for q in Qplus:
            while v % q == 0:
                v //= q
            if v == 1:
                break
        if v != 1:
            continue
        if not is_prime(2 * m + 1):
            continue
        hits += 1
        used_minus.update(qs)
        bitsum += m.bit_length()
    rate = hits / N
    logC = (math.lgamma(t + 1) - math.lgamma(j + 1)
            - math.lgamma(t - j + 1)) / math.log(2)
    proj_pool = 2 ** logC * rate
    # demand: full Q- lcm (each used prime once, squarefree) + Q+ ceiling.
    # Q+ exponents capped: e_q such that q^e <= 2^13 (harvest rejects larger).
    lam_minus = sum(math.log2(q) for q in Qminus)   # worst case: all used
    lam_plus = 0.0
    for q in Qplus:
        e = max(1, int(13 / math.log2(q)))
        lam_plus += e * math.log2(q)
    demand = lam_minus + lam_plus
    return dict(B=B, Bp=Bp, j=j, t=t, N=N, hits=hits, rate=rate,
                logC=round(logC, 1), proj_pool=proj_pool,
                lam_minus=round(lam_minus, 0), lam_plus=round(lam_plus, 0),
                demand=round(demand, 0), ratio=round(proj_pool / demand, 2),
                mean_bits=round(bitsum / hits, 1) if hits else 0)

def main():
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 5_000_000
    ps = primes_upto(40000)
    grid = [(B, Bp, j)
            for B in (1009, 1259, 1601, 2003)
            for Bp in (B * 10, B * 15, B * 20)
            for j in (4, 5, 6)]
    results = []
    for (B, Bp, j) in grid:
        rng = random.Random(hash((B, Bp, j)) & 0xFFFFFFFF)
        t0 = time.time()
        c = cell(B, Bp, j, N, rng, ps)
        if c is None:
            continue
        c["seconds"] = round(time.time() - t0, 1)
        results.append(c)
        print(f"B={B} B'={Bp} j={j}: hits={c['hits']} rate={c['rate']:.2e} "
              f"proj={c['proj_pool']:.3g} demand={c['demand']:.0f} "
              f"ratio={c['ratio']} <{c['mean_bits']}b> ({c['seconds']}s)",
              flush=True)
    results.sort(key=lambda r: -r["ratio"])
    with open(os.path.join(GEN, "a2_grid.json"), "w") as f:
        json.dump(results, f, indent=1)
    print("\nTOP 5 by ratio:")
    for r in results[:5]:
        print(f"  B={r['B']} B'={r['Bp']} j={r['j']}: ratio={r['ratio']} "
              f"pool~{r['proj_pool']:.2g} demand~{r['demand']:.0f}b "
              f"mean {r['mean_bits']}b")

if __name__ == "__main__":
    main()
