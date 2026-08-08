#!/usr/bin/env python3
"""A2: validate the A1 yield model against the complete B=547 corpus, then
extend (j=5,6; finer grid) and freeze the harvest spec.

Part 1 (VALIDATION, the scientifically load-bearing part): the complete
TwinSmooths corpus is an exhaustive twin population to 122 bits. For an
asymmetric split (Q+ = odd primes <= Bs except 5; Q- = primes in (Bs, Bp]),
a REAL pool element qualifies for our harvest iff every prime factor of m
lies in (Bs, Bp] and lpf((m+1)/2) <= Bs. We count those directly from the
complete corpus (ground truth) and compare to what the A1-style sampler
predicts for the same (Bs, Bp, size-window). Agreement validates the model.

Part 2 (EXTEND): j in {3,4,5,6}, finer grid; report projected pool/demand.

Raw corpus stays in scratchpad; only aggregate comparison stats are written
to data/generated/a2_validation.json.
"""
import glob, json, math, os, random, sys, time
from phase1a_calibration import primes_upto, is_prime, odd_prime_factors

S = ("/private/tmp/claude-501/-Users-dbone-PRIMES-Conjectures/"
     "54a16275-018f-4b77-9469-c9fc73711d9d/scratchpad/twins_data/twins")
GEN = os.path.join(os.path.dirname(__file__), "..", "data", "generated")

def corpus_files(B):
    out = []
    for f in glob.glob(S + "/*.txt"):
        base = os.path.basename(f).replace(".txt", "")
        if "stats" in base or "bit" in base:
            continue
        if int(base.split("_")[0]) <= B:
            out.append(f)
    return sorted(out)

def load_real_pool(Bcorpus, ps):
    """Real pool elements (m with m=1 mod 40, 2m+1 prime) from complete corpus,
    with odd-side factor sets. Returns list of (m, set(minus primes of m),
    lpf of (m+1)/2, set(plus primes))."""
    pool = []
    for f in corpus_files(Bcorpus):
        for line in open(f):
            m = int(line)
            if m % 40 != 1:
                continue
            if not is_prime(2 * m + 1):
                continue
            fm = odd_prime_factors(m, ps)
            fp = odd_prime_factors((m + 1) // 2, ps)
            pool.append((m, set(fm), max(fp) if fp else 1, set(fp)))
    return pool

def real_yield(pool, Bs, Bp, blo, bhi):
    """Count real pool elements qualifying for asymmetric harvest (Bs, Bp]
    with m in bit-window [blo, bhi]."""
    c = 0
    for m, mfac, lpf_plus, pfac in pool:
        b = m.bit_length()
        if not (blo <= b <= bhi):
            continue
        if lpf_plus > Bs:                      # (m+1)/2 must be Q+-smooth
            continue
        if any(q <= Bs or q > Bp for q in mfac):  # m factors must be in (Bs,Bp]
            continue
        c += 1
    return c

def sampler_yield(Bs, Bp, blo, bhi, N, rng, ps):
    """Predict pool count in window [blo,bhi] for asymmetric split, summing
    over j, by importance sampling squarefree products of Q- primes."""
    Qminus = [q for q in ps if Bs < q <= Bp]
    Qplus = [q for q in ps if 2 < q <= Bs and q != 5]
    Qplus_set = set(Qplus)
    t = len(Qminus)
    # For each j, estimate P(hit) over random j-subsets whose product is in
    # window, times count of such subsets. Restrict j to those that can land
    # in-window: product ~ (geomean)^j.
    gm = math.exp(sum(math.log(q) for q in Qminus) / t)
    total = 0.0
    breakdown = {}
    for j in range(2, 9):
        lo_ok = j * math.log2(min(Qminus))
        hi_ok = j * math.log2(max(Qminus))
        if hi_ok < blo or lo_ok > bhi:
            continue
        hits = 0
        inwin = 0
        for _ in range(N):
            qs = rng.sample(Qminus, j)
            m = 1
            for q in qs:
                m *= q
            if not (blo <= m.bit_length() <= bhi):
                continue
            inwin += 1
            if m % 40 != 1:
                continue
            v = (m + 1) // 2
            ok = True
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
        if inwin == 0:
            continue
        logC = (math.lgamma(t + 1) - math.lgamma(j + 1)
                - math.lgamma(t - j + 1)) / math.log(2)
        frac_inwin = inwin / N
        frac_hit_of_inwin = hits / inwin
        est = 2 ** logC * frac_inwin * frac_hit_of_inwin
        breakdown[j] = dict(est=est, hits=hits, inwin=inwin,
                            logC=round(logC, 1))
        total += est
    return total, breakdown

def main():
    ps = primes_upto(20030)
    t0 = time.time()
    print("loading real pool from complete B=547 corpus...", flush=True)
    real = load_real_pool(547, primes_upto(547))
    print(f"real pool: {len(real)} ({time.time()-t0:.0f}s)", flush=True)

    # Validation cells: asymmetric splits within B<=547, 30-45 bit window
    val_cells = [(100, 547, 28, 40), (150, 547, 30, 44),
                 (200, 547, 32, 46), (100, 547, 24, 36)]
    validation = []
    for (Bs, Bp, blo, bhi) in val_cells:
        realc = real_yield(real, Bs, Bp, blo, bhi)
        rng = random.Random(hash((Bs, Bp, blo, bhi)) & 0xFFFFFFFF)
        pred, bd = sampler_yield(Bs, Bp, blo, bhi, 3_000_000, rng, ps)
        ratio = pred / realc if realc else float('nan')
        validation.append(dict(Bs=Bs, Bp=Bp, window=[blo, bhi],
                               real=realc, predicted=round(pred, 1),
                               pred_over_real=round(ratio, 2),
                               breakdown=bd))
        print(f"VAL Bs={Bs} Bp={Bp} win=[{blo},{bhi}]: real={realc} "
              f"pred={pred:.1f} ratio={ratio:.2f}", flush=True)

    with open(os.path.join(GEN, "a2_validation.json"), "w") as f:
        json.dump(dict(real_pool_size=len(real), validation=validation),
                  f, indent=1)
    print(f"saved a2_validation.json ({time.time()-t0:.0f}s)")

if __name__ == "__main__":
    main()
