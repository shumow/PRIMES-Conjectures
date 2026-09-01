#!/usr/bin/env python3
"""B6/P3b: measure the prune-fire depth profile of Davis-Putnam-style sound
pruning rules on the odd-part instances (doc/b6-cdcl-plan.md P3b).

Rules measured, per random branch (random variable order, random 0/1 values):
  R1 per-prime rank feasibility: after fixing d variables, is each residual
     GF(l) linear system (0/1 restriction dropped) still feasible? Prune on
     first infeasibility. Exact Gaussian elimination once the number of
     unassigned variables u <= n_l + SLACK; for u above that the system is
     feasible except with probability <= l^-(u - n_l) (documented
     approximation, checked by the exact region).
  R3 counting heuristic (unsound): fires when u < demand bits, i.e. expected
     completions 2^u / |G| < 1. Deterministic in u; reported analytically.
  R2 parity: residual parity is satisfiable while u >= 1; fires at u = 0.

Output: distribution of R1 first-fire depth (reported as u* = unassigned vars
remaining at first fire), per-prime group sizes, demand bits. The DP question
this answers: at what depth does sound pruning start cutting the tree?
u* ~ n_l(max)+O(1) with negligible shallow cuts = pruning fires only when the
search is essentially finished = generalized-DP pruning has no leverage here.

Usage (from code/):
  python3 b_dp_prune_depth.py --D 20,50 --rho 0.004 --regimes ratio10,a10 \
      --trials 200 --out ../data/generated/b6_prune_depth.json
"""
import argparse
import json
import math
import random
import sys
from collections import Counter, defaultdict

from b_cdcl_instances import sized_instance

SLACK = 24   # exact-check window above n_l; miss probability <= l^-SLACK


def gf_rank_feasible(rows, rhs, l):
    """Feasibility of rows*x = rhs over GF(l) via Gaussian elimination.
    rows: list of coefficient lists (may be empty)."""
    m = [r[:] + [b % l] for r, b in zip(rows, rhs)]
    nrow, piv = len(m), 0
    ncol = len(m[0]) - 1 if m else 0
    for c in range(ncol):
        sel = next((r for r in range(piv, nrow) if m[r][c] % l), None)
        if sel is None:
            continue
        m[piv], m[sel] = m[sel], m[piv]
        inv = pow(m[piv][c], l - 2, l)
        m[piv] = [(v * inv) % l for v in m[piv]]
        for r in range(nrow):
            if r != piv and m[r][c] % l:
                f = m[r][c]
                m[r] = [(a - f * b) % l for a, b in zip(m[r], m[piv])]
        piv += 1
        if piv == nrow:
            break
    for r in range(piv, nrow):
        if m[r][ncol] % l and not any(v % l for v in m[r][:ncol]):
            return False
    return True


def trial_first_fire(inst, rng):
    """One random branch; returns u at first R1 fire (0 if never before full
    assignment, then final-check result)."""
    orders, pool, target, N = inst["orders"], inst["pool"], inst["target"], \
        inst["N"]
    groups = defaultdict(list)          # prime l -> component indices
    for j, o in enumerate(orders):
        groups[o].append(j)
    n_max = max(len(v) for v in groups.values())
    order_perm = list(range(N))
    rng.shuffle(order_perm)
    values = [rng.randrange(2) for _ in range(N)]
    # residual rhs per component as variables get fixed
    resid = list(target)
    assigned = 0
    for step, i in enumerate(order_perm):
        if values[i]:
            row = pool[i]
            for j, o in enumerate(orders):
                resid[j] = (resid[j] - row[j]) % o
        assigned += 1
        u = N - assigned
        if u > n_max + SLACK:
            continue                    # feasible w.p. >= 1 - l^-SLACK
        unassigned = order_perm[step + 1:]
        for l, comps in groups.items():
            rows = [[pool[i2][j] % l for i2 in unassigned] for j in comps]
            rhs = [resid[j] for j in comps]
            if not gf_rank_feasible(rows, rhs, l):
                return u, n_max
    return 0, n_max                     # never fired before full assignment


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--D", default="20,50")
    ap.add_argument("--rho", default="0.004")
    ap.add_argument("--regimes", default="ratio10,a10")
    ap.add_argument("--trials", type=int, default=200)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--out", default="../data/generated/b6_prune_depth.json")
    a = ap.parse_args()
    results = []
    for D in [int(v) for v in a.D.split(",")]:
        for rho in [float(v) for v in a.rho.split(",")]:
            for regime in a.regimes.split(","):
                inst = sized_instance(D, rho, regime, a.seed)
                rng = random.Random(999)
                fires = Counter()
                n_max = None
                for _ in range(a.trials):
                    u, n_max = trial_first_fire(inst, rng)
                    fires[u] += 1
                dist = dict(sorted(fires.items()))
                med = sorted(x for x, c in fires.items()
                             for _ in range(c))[len(list(fires.elements()))//2]
                row = {
                    "D": D, "rho": rho, "regime": regime, "N": inst["N"],
                    "demand_bits": round(inst["demand_bits"], 1),
                    "n_max_per_prime": n_max, "trials": a.trials,
                    "R1_first_fire_u_median": med,
                    "R1_first_fire_u_dist": dist,
                    "R3_fires_at_u": math.ceil(inst["demand_bits"]),
                    "R2_fires_at_u": 0,
                    "note": ("u = unassigned vars at first sound prune; "
                             "R1 exact for u<=n_max+%d, else feasible whp"
                             % SLACK),
                }
                results.append(row)
                print(f"[P3b] D={D} rho={rho} {regime} N={inst['N']} "
                      f"demand={row['demand_bits']} n_max={n_max} "
                      f"R1 median u*={med} (R3 analytic u*="
                      f"{row['R3_fires_at_u']})", flush=True)
    with open(a.out, "w") as f:
        json.dump(results, f, indent=1)
    print(f"[P3b] saved -> {a.out}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
