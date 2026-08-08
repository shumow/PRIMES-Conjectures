#!/usr/bin/env python3
"""Definitive B=547 pool extraction + coloring measurement.

Streams the complete TwinSmooths/twins_data corpus (82M pairs, private repo,
scratchpad clone — raw data must NOT enter the public repo), applies the
dictionary filters (m = 1 mod 40, 2m+1 prime), factors both sides, and runs
the partition-space coloring search at full scale. Outputs aggregate
statistics only (data/generated/b547_pool_stats.json).
"""
import glob, json, math, os, random, sys, time
from phase1a_calibration import primes_upto, is_prime, odd_prime_factors

S = ("/private/tmp/claude-501/-Users-dbone-PRIMES-Conjectures/"
     "54a16275-018f-4b77-9469-c9fc73711d9d/scratchpad/twins_data/twins")
GEN = os.path.join(os.path.dirname(__file__), "..", "data", "generated")
B = 547

def data_files():
    out = []
    for f in glob.glob(S + "/*.txt"):
        base = os.path.basename(f).replace(".txt", "")
        if "stats" in base or "bit" in base:
            continue
        if int(base.split("_")[0]) <= B:
            out.append(f)
    return sorted(out)

def main():
    t0 = time.time()
    ps = primes_upto(B)
    total = 0
    cong = []
    for f in data_files():
        for line in open(f):
            total += 1
            m = int(line)
            if m % 40 == 1:
                cong.append(m)
    print(f"streamed {total} twins, {len(cong)} with m=1 mod 40 "
          f"({time.time()-t0:.0f}s)", flush=True)

    pool = [m for m in cong if is_prime(2 * m + 1)]
    print(f"pool (2m+1 prime): {len(pool)} ({time.time()-t0:.0f}s)", flush=True)

    # factor signatures as bitmasks over the odd-prime universe
    universe = [q for q in ps if q > 2]
    qidx = {q: i for i, q in enumerate(universe)}
    elems = []
    om_sum = op_sum = 0
    for m in pool:
        fm = odd_prime_factors(m, ps)
        fp = odd_prime_factors((m + 1) // 2, ps)
        mmask = pmask = 0
        for q in fm: mmask |= 1 << qidx[q]
        for q in fp: pmask |= 1 << qidx[q]
        elems.append((mmask, pmask))
        om_sum += len(fm); op_sum += len(fp)
    n = len(elems)
    print(f"omega: minus {om_sum/n:.2f} plus {op_sum/n:.2f} "
          f"total {(om_sum+op_sum)/n:.2f}", flush=True)

    e_rand = sum(2.0 ** -(bin(a).count('1') + bin(b).count('1'))
                 for a, b in elems)

    # partition local search: M = set of minus-side primes (bitmask)
    # element compatible iff mmask subset of M and pmask disjoint from M
    def survivors(M):
        full = (1 << len(universe)) - 1
        notM = full & ~M
        return sum(1 for a, b in elems if (a & notM) == 0 and (b & M) == 0)

    rng = random.Random(547)
    best_cnt, best_M = -1, 0
    for restart in range(30):
        M = 0
        for i in range(len(universe)):
            if rng.random() < 0.5: M |= 1 << i
        cur = survivors(M)
        improved = True
        while improved:
            improved = False
            for i in range(len(universe)):
                M2 = M ^ (1 << i)
                c2 = survivors(M2)
                if c2 > cur:
                    M, cur = M2, c2
                    improved = True
        if cur > best_cnt:
            best_cnt, best_M = cur, M
        print(f"  restart {restart}: local opt {cur} (best {best_cnt}, "
              f"{time.time()-t0:.0f}s)", flush=True)

    # demand bits for surviving subpool
    used = {}
    full = (1 << len(universe)) - 1
    notM = full & ~best_M
    surv_idx = [i for i, (a, b) in enumerate(elems)
                if (a & notM) == 0 and (b & best_M) == 0]
    for i in surv_idx:
        m = pool[i]
        for q, e in odd_prime_factors(m, ps).items():
            used[q] = max(used.get(q, 0), e)
        for q, e in odd_prime_factors((m + 1) // 2, ps).items():
            used[q] = max(used.get(q, 0), e)
    demand = sum(e * math.log2(q) for q, e in used.items()) + 3

    out = dict(B=B, total_twins=total, congruence_pass=len(cong),
               pool=len(pool), omega_minus_mean=om_sum/n,
               omega_plus_mean=op_sum/n, e_random=e_rand,
               best_partition_survivors=best_cnt,
               survivor_demand_bits=round(demand, 1),
               ratio=round(best_cnt / demand, 4),
               minutes=round((time.time()-t0)/60, 1))
    with open(os.path.join(GEN, "b547_pool_stats.json"), "w") as f:
        json.dump(out, f, indent=1)
    print(json.dumps(out, indent=1), flush=True)

if __name__ == "__main__":
    main()
