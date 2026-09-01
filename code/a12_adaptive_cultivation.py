#!/usr/bin/env python3
"""A12: test the 'merge harvest + solve' idea (adaptive/on-demand cultivation).

User proposal: don't fix the pool then solve; instead SELECT the next smooth
pair based on the characteristics of the current PARTIAL solution -- column
generation / branch-and-price with a number-theoretic pricing oracle.

This tests the most OPTIMISTIC form (assume any density-rho vector is
harvestable on demand -- ignores the real N1 constraint that low identity-
support is expensive): at each step generate a large fresh batch of candidate
moves and greedily add the one that best reduces the deficit, with restarts to
escape local minima. Question: does adaptive + unlimited-fresh-moves descend to
the target at low density and rising dimension D, where fixed-pool local search
(a6, stalled ~19) and non-adaptive Wagner (a10, reach ~20) both cap out?

If it reaches D >> 20 at rho=0.004, the merge idea beats prior methods and is
worth pursuing. If it stalls near ~20 too, the density-reach wall is intrinsic
to the whole method class (adaptive or not, fixed or on-demand).
"""
import random, sys, time

def fresh_vec(D, rho, ell, rng):
    return tuple(0 if rng.random() < rho else rng.randrange(1, ell)
                 for _ in range(D))

def nnz(s, target, ell):
    return sum(1 for a, b in zip(s, target) if (a - b) % ell != 0)

def add(s, v, ell):
    return tuple((a + b) % ell for a, b in zip(s, v))

def cultivate(D, rho, ell, rng, K, target, max_steps, restarts):
    """Adaptive greedy descent with fresh on-demand moves. Returns min deficit
    (nnz) reached; 0 = solved."""
    best_overall = D + 1
    for _ in range(restarts):
        s = tuple([0] * D)
        cur = nnz(s, target, ell)
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
                if stalls > 30:
                    break
        best_overall = min(best_overall, cur)
    return best_overall

def main():
    rng = random.Random(int(sys.argv[1]) if len(sys.argv) > 1 else 1)
    ell = 3
    rho = 0.004
    K = 4000          # fresh candidate moves generated per step (on-demand)
    print(f"Adaptive on-demand cultivation over (Z/{ell})^D, rho={rho}, "
          f"K={K} fresh moves/step. target = identity.")
    print("Deficit reached (0 = SOLVED). Compare: a6 fixed-pool stalled ~19; "
          "a10 Wagner reach ~20.")
    print(f"{'D':>5}{'min deficit':>13}{'solved?':>9}{'sec':>8}")
    for D in [15, 20, 30, 50, 100, 200]:
        # nonzero planted target = sum of ~D/2 fresh density-rho vectors, so a
        # real nonempty solution provably exists; start s=0 has deficit ~D.
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
