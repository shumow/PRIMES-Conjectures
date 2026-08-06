#!/usr/bin/env python3
"""Phase 1a calibration: twin smooths -> dictionary filter -> coloring tax.

Generates all B-smooth integers up to X natively (no external datasets),
finds twin smooth pairs (m, m+1), applies the dictionary filters of
working-paper Lemma 4.1 (m = 1 mod 40, p = 2m+1 prime), and measures:
  - survivor counts at each filter stage
  - omega distributions (distinct odd primes per side)
  - expected survivors of a random balanced side-partition
  - greedy/local-search optimized partition survivors (Question 5.1)
  - demand bits (lcm over surviving pool) vs supply

Usage: python3 phase1a_calibration.py [B] [X]  (defaults B=547, X=10**9)
"""
import sys, math, random, json
from array import array

def primes_upto(n):
    sieve = bytearray([1]) * (n + 1)
    sieve[0:2] = b"\x00\x00"
    for i in range(2, int(n**0.5) + 1):
        if sieve[i]:
            sieve[i*i::i] = bytearray(len(sieve[i*i::i]))
    return [i for i in range(n + 1) if sieve[i]]

def smooth_upto(primes, X):
    """All B-smooth integers <= X, ascending (sorted array)."""
    out = array("q", [1])
    for p in primes:
        cur = out
        add = array("q")
        for v in cur:
            m = v * p
            while m <= X:
                add.append(m)
                m *= p
        out = array("q", sorted(cur + add))
    return out

def is_prime(n):
    """Deterministic Miller-Rabin for n < 3.3e24."""
    if n < 2:
        return False
    for p in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        if n % p == 0:
            return n == p
    d, s = n - 1, 0
    while d % 2 == 0:
        d //= 2; s += 1
    for a in (2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37):
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for _ in range(s - 1):
            x = x * x % n
            if x == n - 1:
                break
        else:
            return False
    return True

def odd_prime_factors(n, primes):
    fac = {}
    for p in primes:
        if p * p > n:
            break
        while n % p == 0:
            fac[p] = fac.get(p, 0) + 1
            n //= p
    if n > 1:
        fac[n] = fac.get(n, 0) + 1
    fac.pop(2, None)
    return fac

def coloring_greedy(elements, order):
    """elements: list of (minus_set, plus_set). Assign primes to sides greedily."""
    side = {}  # prime -> '-' or '+'
    survivors = []
    for i in order:
        mn, pl = elements[i]
        ok = all(side.get(q, "-") == "-" for q in mn) and \
             all(side.get(q, "+") == "+" for q in pl)
        if ok:
            for q in mn:
                side[q] = "-"
            for q in pl:
                side[q] = "+"
            survivors.append(i)
    return survivors, side

def main():
    B = int(sys.argv[1]) if len(sys.argv) > 1 else 547
    X = int(sys.argv[2]) if len(sys.argv) > 2 else 10**9
    rng = random.Random(0xA95)  # deterministic
    ps = primes_upto(B)
    print(f"B={B} (pi={len(ps)}), X={X:.0e}")

    sm = smooth_upto(ps, X)
    print(f"smooth numbers <= X: {len(sm)}")

    twins = [sm[i] for i in range(len(sm) - 1) if sm[i + 1] == sm[i] + 1]
    print(f"twin pairs (m, m+1): {len(twins)}")

    slice40 = [m for m in twins if m % 40 == 1]
    print(f"  after m = 1 (mod 40): {len(slice40)}")

    pool = [m for m in slice40 if is_prime(2 * m + 1)]
    print(f"  after p = 2m+1 prime: {len(pool)}  (pre-coloring pool)")

    if not pool:
        print("pool empty at this (B, X) — increase X or B")
        return

    # factor signatures
    elements, om, op = [], [], []
    for m in pool:
        fm = odd_prime_factors(m, ps)
        fp = odd_prime_factors((m + 1) // 2, ps)
        assert 5 not in fm and 5 not in fp, m
        assert not (set(fm) & set(fp)), m
        elements.append((frozenset(fm), frozenset(fp)))
        om.append(len(fm)); op.append(len(fp))
    n = len(elements)
    print(f"omega stats: minus mean {sum(om)/n:.2f} max {max(om)}, "
          f"plus mean {sum(op)/n:.2f} max {max(op)}, "
          f"total mean {(sum(om)+sum(op))/n:.2f}")

    # random balanced partition: expected survivors = sum 2^-(om+op)
    # (each element's demanded primes must all land on its required side)
    e_rand = sum(2.0 ** -(a + b) for a, b in zip(om, op))
    print(f"E[survivors | random partition] = {e_rand:.2f} "
          f"({100*e_rand/n:.3f}% of pool)")

    # optimized coloring: greedy by ascending omega + random-restart local search
    idx = sorted(range(n), key=lambda i: om[i] + op[i])
    best, best_side = coloring_greedy(elements, idx)
    for _ in range(200):
        order = idx[:]
        rng.shuffle(order)
        # bias: keep roughly ascending but perturbed
        order.sort(key=lambda i: om[i] + op[i] + rng.random() * 3)
        surv, side = coloring_greedy(elements, order)
        if len(surv) > len(best):
            best, best_side = surv, side
    print(f"optimized partition survivors: {len(best)} "
          f"({100*len(best)/n:.2f}% of pool) "
          f"[vs random expectation {100*e_rand/n:.3f}%]")

    # demand bits for the surviving subpool
    used = {}
    for i in best:
        m = pool[i]
        for q, e in odd_prime_factors(m, ps).items():
            used[q] = max(used.get(q, 0), e)
        for q, e in odd_prime_factors((m + 1) // 2, ps).items():
            used[q] = max(used.get(q, 0), e)
    demand_bits = sum(e * math.log2(q) for q, e in used.items()) + 3  # +2-part
    print(f"demand: {len(used)} primes, lcm ~ {demand_bits:.0f} bits; "
          f"supply/demand = {len(best)/demand_bits:.3f} (need >~ 1-2 w/ slack)")

    result = dict(B=B, X=X, n_smooth=len(sm), n_twins=len(twins),
                  n_slice40=len(slice40), n_pool=n,
                  omega_minus_mean=sum(om)/n, omega_plus_mean=sum(op)/n,
                  e_random=e_rand, opt_survivors=len(best),
                  demand_bits=demand_bits, n_used_primes=len(used))
    with open(f"../data/calibration_B{B}_X{X}.json", "w") as f:
        json.dump(result, f, indent=1)
    print("saved to data/")

if __name__ == "__main__":
    main()
