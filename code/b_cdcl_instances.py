#!/usr/bin/env python3
"""B6/P1: instances + encodings for the algebraic-CDCL falsification ladder.

Direction 6 of doc/option-b-problem.md, plan doc/b6-cdcl-plan.md. Reuses the
brief's harness (a8_omega_solver.make_structured) unmodified; provides:
  - sized_instance(): ratio-10 / A10-match pool sizing, planting policies
  - cpsat_solve(): OR-tools CP-SAT encoding (mod-l via slack ints + parity row)
  - z3_solve():    Z3 LIA encoding (native % + parity)
  - verify_solution(): residues + odd cardinality, trusted checker
Run from code/. Nothing here modifies existing modules.
"""
import math
import random
import time

from a8_omega_solver import make_structured

# ---------- instance construction ----------

def demand_bits(orders):
    return sum(math.log2(o) for o in orders)


def sized_instance(D, rho, regime, seed, planting="half"):
    """Build a make_structured instance with pool size set by `regime`:
    'ratio10' -> N ~ 10 x demand bits (real pool/demand shape);
    'a10'     -> N = 20000 (the pool A10's Wagner reach was measured at).
    planting: 'half' -> planted support ~N/2 (statistically invisible);
              'small' -> planted support ~demand-bits (realistic-shape).
    Two-pass trick: same seed => same orders draw, so we can size N from the
    orders without touching make_structured."""
    r1 = random.Random(seed)
    orders, _, _, _ = make_structured(D, rho, 1, 1, r1)
    dem = demand_bits(orders)
    if regime == "ratio10":
        N = max(int(10 * dem), 4 * D)
    elif regime == "a10":
        N = 20000
    else:
        raise ValueError(regime)
    if planting == "half":
        k = N // 2
    elif planting == "small":
        k = max(3, int(dem))
    else:
        raise ValueError(planting)
    if k % 2 == 0:
        k += 1
    r2 = random.Random(seed)
    orders2, pool, target, S = make_structured(D, rho, N, k, r2)
    assert orders2 == orders
    return {"orders": orders, "pool": pool, "target": target, "planted": S,
            "N": N, "D": D, "rho": rho, "regime": regime, "planting": planting,
            "demand_bits": dem, "seed": seed}


def verify_solution(chosen, inst, require_odd=True):
    orders, pool, target = inst["orders"], inst["pool"], inst["target"]
    if require_odd and len(chosen) % 2 != 1:
        return False
    acc = [0] * len(orders)
    for i in chosen:
        row = pool[i]
        for j, o in enumerate(orders):
            acc[j] = (acc[j] + row[j]) % o
    return acc == list(target)

# ---------- CP-SAT encoding ----------

def cpsat_solve(inst, time_s, workers=8, add_parity=True, log=False):
    from ortools.sat.python import cp_model
    orders, pool, target = inst["orders"], inst["pool"], inst["target"]
    N, D = inst["N"], inst["D"]
    t0 = time.time()
    m = cp_model.CpModel()
    x = [m.new_bool_var(f"x{i}") for i in range(N)]
    for j, o in enumerate(orders):
        coefs = [pool[i][j] for i in range(N)]
        tot = sum(coefs)
        s = m.new_int_var(0, tot // o, f"s{j}")
        m.add(cp_model.LinearExpr.weighted_sum(x, coefs) == target[j] + o * s)
    if add_parity:
        sp = m.new_int_var(0, N // 2, "sp")
        m.add(cp_model.LinearExpr.sum(x) == 1 + 2 * sp)
    build_s = time.time() - t0
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = float(time_s)
    solver.parameters.num_workers = workers
    solver.parameters.log_search_progress = log
    st = solver.solve(m)
    name = solver.status_name(st)
    chosen = None
    if name in ("OPTIMAL", "FEASIBLE"):
        chosen = [i for i in range(N) if solver.value(x[i])]
    return {"solver": "cpsat", "status": name, "chosen": chosen,
            "build_s": round(build_s, 2), "solve_s": round(solver.wall_time, 2),
            "conflicts": solver.num_conflicts, "branches": solver.num_branches}

# ---------- Z3 encoding ----------

def z3_solve(inst, time_s, add_parity=True):
    import z3
    orders, pool, target = inst["orders"], inst["pool"], inst["target"]
    N = inst["N"]
    t0 = time.time()
    xs = [z3.Int(f"x{i}") for i in range(N)]
    s = z3.Solver()
    s.set("timeout", int(time_s * 1000))
    for v in xs:
        s.add(v >= 0, v <= 1)
    for j, o in enumerate(orders):
        s.add(z3.Sum([pool[i][j] * xs[i] for i in range(N)
                      if pool[i][j] != 0]) % o == target[j])
    if add_parity:
        s.add(z3.Sum(xs) % 2 == 1)
    build_s = time.time() - t0
    t1 = time.time()
    res = s.check()
    solve_s = time.time() - t1
    chosen = None
    if res == z3.sat:
        mdl = s.model()
        chosen = [i for i in range(N) if mdl[xs[i]].as_long() == 1]
    return {"solver": "z3", "status": str(res), "chosen": chosen,
            "build_s": round(build_s, 2), "solve_s": round(solve_s, 2),
            "conflicts": None, "branches": None}

# ---------- P2: oracle cross-validation ----------

def p2_oracle_gate(n_instances=20, time_s=20, verbose=True):
    """Gate G-b6-0 (correctness, not hardness): on EASY seeded instances
    (small moduli via primes_cap=13, D<=8, N<=36), CP-SAT must find solutions
    that verify (residues + parity), and the exact MITM oracle must confirm a
    residue-solution exists. Hardness is measured by the P3 grid, not here —
    an early probe showed CP-SAT/Z3 time out on rho=0.004 instances already
    at D=6 with realistic moduli, so gating on solver success there would
    conflate encoding bugs with genuine search hardness.
    Z3 is recorded but NOT gating: both the %-encoding and the slack-equality
    LIA encoding time out even on rho=0.5, D=7, N=36 instances that CP-SAT
    solves in 0.15s — Z3's LIA engine is dominated on dense PB equalities.
    Returns (passes, total, rows)."""
    from a6_oddsolver import mitm_frontier
    rows, passes = [], 0
    for k in range(n_instances):
        D = 4 + (k % 5)                      # 4..8
        rho = 0.004 if k % 2 == 0 else 0.5
        r1 = random.Random(1000 + k)
        orders, _, _, _ = make_structured(D, rho, 1, 1, r1, primes_cap=13)
        N = min(36, max(24, int(2.5 * demand_bits(orders))))
        pk = (N // 2) | 1
        r2 = random.Random(1000 + k)
        orders, pool, target, S = make_structured(D, rho, N, pk, r2,
                                                  primes_cap=13)
        inst = {"orders": orders, "pool": pool, "target": target, "N": N,
                "D": D, "rho": rho, "demand_bits": demand_bits(orders)}
        rc = cpsat_solve(inst, time_s)
        okc = rc["chosen"] is not None and verify_solution(rc["chosen"], inst)
        om, _msg = mitm_frontier(orders, pool, target, N, time_budget=20)
        oko = om is not None            # oracle confirms residue-solution
        ok = okc and oko
        passes += ok
        rows.append({"k": k, "D": D, "rho": rho, "N": N, "cpsat": okc,
                     "mitm": oko, "cpsat_s": rc["solve_s"]})
        if verbose:
            print(f"[P2 {k:02d}] D={D} rho={rho} N={N} "
                  f"cpsat={okc}({rc['solve_s']}s) "
                  f"mitm={oko} -> {'OK' if ok else 'FAIL'}", flush=True)
    return passes, n_instances, rows


if __name__ == "__main__":
    p, t, _ = p2_oracle_gate()
    print(f"P2 oracle gate: {p}/{t}")
