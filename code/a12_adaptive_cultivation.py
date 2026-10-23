#!/usr/bin/env python3
"""A12: finite-budget synthetic greedy on-demand cultivation.

At each step sample K candidate vectors, accept an improving one if present,
otherwise perturb. This does not implement a number-theoretic pricing oracle
or exclude other adaptive strategies. Unlike A8/A10, rho is literal P(0);
nonzero coordinates are sampled uniformly from 1..ell-1.

The returned statistic is the minimum deficit of a visited state, not a
verified odd-cardinality subset or a counterexample.
"""
import random, sys, time

def fresh_vec(D, rho, ell, rng):
    if D < 0 or not 0 <= rho <= 1 or ell < 2:
        raise ValueError("invalid vector dimension, zero probability or group order")
    return tuple(0 if rng.random() < rho else rng.randrange(1, ell)
                 for _ in range(D))

def nnz(s, target, ell):
    return sum(1 for a, b in zip(s, target) if (a - b) % ell != 0)

def add(s, v, ell):
    return tuple((a + b) % ell for a, b in zip(s, v))

def cultivate(D, rho, ell, rng, K, target, max_steps, restarts):
    """Adaptive greedy descent with fresh on-demand moves. Returns min deficit
    (nnz) reached; 0 = solved."""
    if D < 0 or len(target) != D or K < 1 or max_steps < 0 or restarts < 1:
        raise ValueError("target must match D and sampling/restart budgets must be valid")
    if not 0 <= rho <= 1 or ell < 2:
        raise ValueError("rho must be in [0, 1] and the group order at least 2")
    best_overall = D + 1
    for _ in range(restarts):
        s = tuple([0] * D)
        cur = nnz(s, target, ell)
        best_overall = min(best_overall, cur)
        stalls = 0
        for step in range(max_steps):
            if cur == 0:
                return 0
            # generate K fresh candidate moves; pick the one minimizing deficit
            best_v, best_c = None, cur
            for _ in range(K):
                v = fresh_vec(D, rho, ell, rng)
                c = nnz(add(s, v, ell), target, ell)
                if c < best_c:
                    best_c, best_v = c, v
            if best_v is not None:
                s = add(s, best_v, ell); cur = best_c; stalls = 0
            else:
                # no improving move in the batch: accept a neutral/worse move to
                # perturb (simulated-annealing-style escape), then continue
                v = fresh_vec(D, rho, ell, rng)
                s = add(s, v, ell); cur = nnz(s, target, ell); stalls += 1
            best_overall = min(best_overall, cur)
            if stalls > 30:
                break
    return best_overall

def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    ell = 3
    rho = 0.004
    K = 4000          # fresh candidate moves generated per step (on-demand)
    print(f"Adaptive on-demand cultivation over (Z/{ell})^D, rho={rho}, "
          f"K={K} fresh moves/step; 3 restarts; target = planted sum.")
    print("rho is literal P(0), unlike A8/A10. Minimum visited deficit (0 = hit).")
    print("Finite synthetic heuristic, not an odd-subset certificate or a no-go theorem.")
    print(f"{'D':>5}{'min deficit':>13}{'solved?':>9}{'sec':>8}")
    for D in [15, 20, 30, 50, 100, 200]:
        # The target is reachable in the abstract move family, not necessarily
        # by the finite sequence of candidates sampled during this search.
        target = tuple([0] * D)
        for _ in range(max(3, D // 2)):
            target = add(target, fresh_vec(D, rho, ell, rng), ell)
        start_deficit = nnz(tuple([0] * D), target, ell)
        t0 = time.time()
        md = cultivate(D, rho, ell, rng, K, target,
                       max_steps=8 * D + 60, restarts=3)
        dt = time.time() - t0
        print(f"{D:>5}  start~{start_deficit:>4}  ->{md:>5}"
              f"{('  SOLVED' if md == 0 else '  stalled'):>9}{dt:>8.1f}")

if __name__ == "__main__":
    main()
