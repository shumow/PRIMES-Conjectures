#!/usr/bin/env python3
"""B6/P3: falsification grid for off-the-shelf algebraic-CDCL solvers.

Runs CP-SAT / Z3 over make_structured instances across (D, rho, regime, seed),
judged against the measured Wagner-4 reach (~20 comps at rho=0.004, N=20k;
FINDINGS A10) and the exact frontier (~15 comps; FINDINGS A6).
Appends one JSON line per run to the output (crash-safe, resumable by eye).

Usage (from code/):
  python3 b_cdcl_falsify.py --solvers cpsat,z3 --regimes ratio10,a10 \
      --D 20,30,40,50 --rho 0.004,0.5 --seeds 0,1 --cap 120 \
      --out ../data/generated/b6_cdcl_grid.jsonl
Z3 is skipped for the a10 (N=20000) regime unless --z3-large is given
(model build alone is prohibitive there).
"""
import argparse
import json
import sys
import time

from b_cdcl_instances import sized_instance, cpsat_solve, z3_solve, \
    verify_solution


def run_cell(solver, D, rho, regime, seed, cap, planting, workers):
    inst = sized_instance(D, rho, regime, seed, planting)
    if solver == "cpsat":
        r = cpsat_solve(inst, cap, workers=workers)
    else:
        r = z3_solve(inst, cap)
    ok = r["chosen"] is not None and verify_solution(r["chosen"], inst)
    return {
        "solver": solver, "D": D, "rho": rho, "regime": regime,
        "N": inst["N"], "planting": planting, "seed": seed,
        "demand_bits": round(inst["demand_bits"], 1), "cap_s": cap,
        "status": r["status"], "solved": bool(ok),
        "support": len(r["chosen"]) if r["chosen"] else None,
        "build_s": r["build_s"], "solve_s": r["solve_s"],
        "conflicts": r["conflicts"], "branches": r["branches"],
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--solvers", default="cpsat,z3")
    ap.add_argument("--regimes", default="ratio10,a10")
    ap.add_argument("--D", default="20,30,40,50")
    ap.add_argument("--rho", default="0.004,0.5")
    ap.add_argument("--seeds", default="0,1")
    ap.add_argument("--cap", type=float, default=120.0)
    ap.add_argument("--planting", default="half")
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--z3-large", action="store_true")
    ap.add_argument("--out", default="../data/generated/b6_cdcl_grid.jsonl")
    a = ap.parse_args()

    cells = []
    for D in [int(v) for v in a.D.split(",")]:
        for rho in [float(v) for v in a.rho.split(",")]:
            for regime in a.regimes.split(","):
                for seed in [int(v) for v in a.seeds.split(",")]:
                    for solver in a.solvers.split(","):
                        if solver == "z3" and regime == "a10" \
                                and not a.z3_large:
                            continue
                        cells.append((solver, D, rho, regime, seed))
    # cheap cells first so early output is informative
    cells.sort(key=lambda c: (c[1], c[3] == "a10", c[0]))
    print(f"[grid] {len(cells)} runs, cap {a.cap}s each", flush=True)
    t0 = time.time()
    with open(a.out, "a") as f:
        for i, (solver, D, rho, regime, seed) in enumerate(cells):
            row = run_cell(solver, D, rho, regime, seed, a.cap,
                           a.planting, a.workers)
            f.write(json.dumps(row) + "\n")
            f.flush()
            print(f"[{i+1}/{len(cells)} t={time.time()-t0:.0f}s] "
                  f"{solver} D={D} rho={rho} {regime} N={row['N']} "
                  f"seed={seed} -> {row['status']} solved={row['solved']} "
                  f"({row['solve_s']}s, conf={row['conflicts']})", flush=True)
    print(f"[grid] done in {time.time()-t0:.0f}s -> {a.out}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
