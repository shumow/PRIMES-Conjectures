"""S2 (arithmetic obstruction analysis): explain the first-wave binary obstructions.

Plan: PLAN.md, current section 4 (S2). Inputs are the frozen first-wave artifacts
``data/generated/fs_harvest.json.gz`` (five serialized actual-prime instances:
the pilot anchor and the four Track C cells) and the frozen pilot
``data/generated/real_pool_pilot.json.gz``; both are read-only here. This module
owns only the ``bf_obstructions`` artifacts. Run from the repository root:

    python -B code/bf_obstructions.py --output data/generated/bf_obstructions.json.gz
    python -B code/bf_obstructions.py --verify data/generated/bf_obstructions.json.gz

Mathematical content (proved in doc/bf-obstructions-findings.md and checked here):

* **Legendre shadow.** For an odd prime power block ``(Z/l^e)*`` the 2-primary
  discrete-log coordinate of a unit ``x`` is odd exactly when ``x`` is a quadratic
  non-residue modulo ``l``.  Hence the pilot's GF(2) necessary check *is* the
  Legendre-symbol system: rows are the odd block primes (plus the parity row),
  the entry for pool prime ``p`` is ``[(p/l) = -1]``, the real target is ``0`` on
  minus-side rows, ``[l = 3 mod 4]`` on plus-side rows and ``1`` on the parity row.
  No discrete logarithm is needed to run the check.
* **Forced 3-relation.** In every harvest family of this project ``3`` is a plus
  base prime and no minus base prime is ``3``, so every pool prime is ``2 mod 3``
  and ``3 | p+1``.  The 2-primary row of the plus-3 block therefore equals the
  parity row on all generators and on the target.  The character
  ``chi_3 + parity`` annihilates every generator and contains the target in its
  kernel: it is a structural (family-forced) codimension-one relation, never an
  obstruction.
* **Exact subgroup index (anchor).** Certificates below show the generated
  subgroup of the full 483-prime anchor has index exactly two in the assembled
  group, with ``chi_3 + parity`` the unique nontrivial annihilating character, and
  re-derive the real target's membership independently of Track B.

Status vocabulary follows the plan: direct checks are ``verified``; exhaustive
declared scopes are ``completed_scope``; watchdog stops are ``timeout_enforced``
(inconclusive); nothing here is a Boolean solution or a counterexample claim.
"""
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Sequence
import argparse
import gzip
import hashlib
import json
import math
import platform
import tempfile
import time

from fs_controls import run_limited
from real_pool_verify import (
    PrimeRecord, RealInstance, instance_from_json, source_digest, trial_factors,
    verify_encoding, verify_obstruction, verify_saved_report,
)

SCHEMA = "bf-obstructions/v1"
TRACK = "S2 (arithmetic obstruction analysis)"
PLAN = "PLAN.md current section 4 (S2); shared budgets section 6"
STARTING_COMMIT = "0c9f03fb1e00dfd85cb9e2b37e15ed1e727c4915"
BASELINE_MAIN = "c114e84465495d5e414590393b41eb3dca341821"
HERE = Path(__file__).resolve().parent
DEFAULT_HARVEST = HERE.parent / "data" / "generated" / "fs_harvest.json.gz"
DEFAULT_PILOT = HERE.parent / "data" / "generated" / "real_pool_pilot.json.gz"
DEFAULT_OUTPUT = HERE.parent / "data" / "generated" / "bf_obstructions.json.gz"
EXPECTED_HARVEST_SHA256 = "75f1599b05a84f0c8e7f24fa349de1628ea2811a58cb4558c84bbc02a0410bad"
EXPECTED_PILOT_SHA256 = "008cf08ce3f0d3a2f987bff26d5abd04bf4c41050f949ae0fdc4f4192b6969de"
SOURCES = ("bf_obstructions.py", "real_pool_verify.py", "real_pool_pilot.py",
           "fs_controls.py", "fs_harvest.py")

ANCHOR = "fs-anchor-rerun-medium-complete"
CELLS = (ANCHOR, "fs-c1-four-factors", "fs-c2-wider-minus",
         "fs-c3-wider-plus-complete", "fs-c4-both-wider")
PARITY = ("parity", 2)
FORCED_RELATION = frozenset({("plus", 3), PARITY})

# Declared before any computation (plan section 6): a finite probe list, one
# worker process, an enforced 60 s wall per computational probe, no retries, no
# parameter sweeps, no new harvesting.  Budgets are never raised to force a result.
BUDGETS = {
    "wall_seconds_per_probe": 60.0,       # enforced by fs_controls.run_limited (process watchdog)
    "min_weight_cap": 4,                  # exhaustive separating-character search weight cap
    "worker_processes": 1,                # one spawned worker at a time; no parallelism
    "aggregate_wall_seconds_declared": 1800.0,  # declared ceiling for the whole run (observed)
    "new_harvesting": False,              # only existing certified primes are used
    "index_certificates_stored_for": [ANCHOR],  # full certificates kept for the anchor only
}

PROBES = (
    ("P0", "Reload both frozen inputs, check their SHA256, rebuild and re-verify the five instances, "
           "re-check the four recorded GF(2) characters directly against original generators and target."),
    ("P1", "Legendre shadow: every 2-primary coordinate of every vector and the target equals the "
           "arithmetic quadratic-residue prediction (direct check, all five instances)."),
    ("P2", "Forced 3-relation: all pool primes are 2 mod 3; the plus-3 row equals the parity row; the "
           "GF(2) left kernel contains chi_3+parity; report whether it is exactly that (all five)."),
    ("P3", "Arithmetic description of each recorded obstruction: side/prime breakdown, sign-carrying "
           "rows (plus primes 3 mod 4, parity), target value, canonical form modulo the forced relation."),
    ("P4", "Minimum-weight separating character per obstructed cell, exhaustive up to weight 4 "
           "(watchdog 60 s each)."),
    ("P5", "Transfer tests: evaluate each recorded character as a Legendre functional on certified "
           "primes of the same declared family taken from the other pools; completeness cross-checks."),
    ("P6", "Union shadow probes: the Legendre mod-2 system of declared union pools (c2 family: c2 + anchor; "
           "c4 family: c4 + c3 + eligible anchor) with their own block sets and LCMs (watchdog 60 s each)."),
    ("P7", "Exact subgroup index with algorithm-free certificates: anchor 2-primary and all odd primary "
           "parts (stored); 2-primary summaries for c1-c4 (watchdog 60 s per primary part)."),
)

# Transfer tests use only families that contain certified primes from another pool.
TRANSFERS = {
    "fs-c2-wider-minus": (ANCHOR,),
    "fs-c4-both-wider": ("fs-c3-wider-plus-complete", ANCHOR),
    "fs-c3-wider-plus-complete": (ANCHOR, "fs-c4-both-wider"),
    "fs-c1-four-factors": (),
}
UNIONS = (
    ("c2-family-union", "fs-c2-wider-minus", (ANCHOR,)),
    ("c4-family-union", "fs-c4-both-wider", ("fs-c3-wider-plus-complete", ANCHOR)),
)

LIMITS = [
    "The Legendre system is the mod-2 shadow of the assembled group; passing it is necessary, "
    "not sufficient, for integer membership, and says nothing about Boolean feasibility.",
    "A union probe declares a new pool with its own full-pool LCMs; its result is a statement "
    "about that declared pool, not about the sampled cell or about selected-subset LCMs.",
    "A GF(2) solution vector certifies consistency of the mod-2 system only; it is not a subset "
    "solution of the group problem and not a counterexample candidate.",
    "Family membership tests use the cells' declared harvest configurations; a certified prime of "
    "one pool is a family member of another cell only if it meets that cell's declared bounds.",
    "Minimum-weight results are exhaustive only up to the declared weight cap.",
    "Exact-index certificates are algorithm-free lower bounds on |H| and |H^perp| whose product "
    "equals |G|; the verifier never runs Howell or Smith elimination.",
    "No production search was run, no budget was raised, no new prime was harvested.",
]


# ---------------------------------------------------------------------------
# Arithmetic: Legendre shadow and forced relation
# ---------------------------------------------------------------------------

def quadratic_nonresidue(p: int, ell: int) -> int:
    """1 if p is a quadratic non-residue modulo the odd prime ell, else 0 (Euler)."""
    if ell < 3 or ell % 2 == 0 or p % ell == 0:
        raise ValueError("Legendre symbol needs an odd prime modulus and a coprime argument")
    return 1 if pow(p, (ell - 1) // 2, ell) == ell - 1 else 0


def _is_power_of_two(n: int) -> bool:
    return n >= 1 and n & (n - 1) == 0


def coordinate_labels(instance: RealInstance) -> dict:
    """Map every coordinate index to its (side, block prime); the last is the parity row."""
    labels = {}
    for block in instance.blocks:
        for j in block.columns:
            labels[j] = (block.side, block.prime)
    labels[len(instance.orders) - 1] = PARITY
    if len(labels) != len(instance.orders):
        raise ValueError("blocks do not cover the coordinates")
    return labels


def two_primary_coordinates(instance: RealInstance) -> list:
    """(j, side, prime) for every block coordinate whose order is a power of two."""
    labels = coordinate_labels(instance)
    out = []
    for j, order in enumerate(instance.orders[:-1]):
        if _is_power_of_two(order):
            side, prime = labels[j]
            out.append((j, side, prime))
    return out


def shadow_target_bit(side: str, prime: int) -> int:
    """Mod-2 coordinate of the real target (1 mod Lambda-, -1 mod Lambda+)."""
    if side == "minus":
        return 0
    if side == "plus":
        return 1 if prime % 4 == 3 else 0
    if (side, prime) == PARITY:
        return 1
    raise ValueError("unknown row kind")


def legendre_shadow_check(instance: RealInstance) -> dict:
    """Direct check of the Legendre shadow on every 2-primary coordinate (raises on mismatch)."""
    coords = two_primary_coordinates(instance)
    checked = 0
    for j, side, ell in coords:
        for record, vector in zip(instance.records, instance.vectors):
            if vector[j] % 2 != quadratic_nonresidue(record.p, ell):
                raise ValueError(f"Legendre shadow fails at coordinate {j} for p={record.p}")
            checked += 1
        if instance.target[j] % 2 != shadow_target_bit(side, ell):
            raise ValueError(f"target shadow fails at coordinate {j}")
    if any(vector[-1] != 1 for vector in instance.vectors) or instance.target[-1] != 1:
        raise ValueError("parity row is not the all-ones row")
    return {"two_primary_coordinates": len(coords), "vector_entries_checked": checked,
            "target_entries_checked": len(coords), "status": "verified"}


def forced_three_relation(instance: RealInstance) -> dict:
    """Direct check of the forced relation chi_3 + parity (raises if it fails)."""
    for record in instance.records + instance.excluded_nonunits:
        if record.p % 3 != 2 or (record.p + 1) % 3:
            raise ValueError(f"pool prime {record.p} is not 2 mod 3")
        if dict(record.minus).get(3):
            raise ValueError("3 divides p-1 for a pool prime")
    three = [j for j, side, ell in two_primary_coordinates(instance) if side == "plus" and ell == 3]
    if len(three) != 1 or instance.orders[three[0]] != 2:
        raise ValueError("the plus-3 block must contribute exactly one order-two coordinate")
    j3 = three[0]
    if any(vector[j3] != 1 for vector in instance.vectors) or instance.target[j3] != 1:
        raise ValueError("plus-3 row differs from the parity row")
    return {"plus_three_coordinate": j3, "parity_coordinate": len(instance.orders) - 1,
            "pool_primes_two_mod_three": len(instance.records), "status": "verified"}


# ---------------------------------------------------------------------------
# GF(2) machinery (rows are bitmasks over generators)
# ---------------------------------------------------------------------------

def shadow_system(records: Sequence[PrimeRecord]) -> tuple:
    """Legendre mod-2 system of a declared pool with its own block set.

    Returns (labels, rows, target_bits): labels are (side, prime) for every odd
    prime dividing some p-1 (minus) or p+1 (plus) in the pool, then the parity
    row; rows are bitmasks over the pool index; target bits follow shadow_target_bit.
    """
    if not records or len({record.p for record in records}) != len(records):
        raise ValueError("a declared pool needs distinct prime records")
    blocks = set()
    for record in records:
        blocks.update(("minus", q) for q, _ in record.minus if q != 2)
        blocks.update(("plus", q) for q, _ in record.plus if q != 2)
    if {q for side, q in blocks if side == "minus"} & {q for side, q in blocks if side == "plus"}:
        raise ValueError("declared pool has overlapping odd side supports")
    labels = sorted(blocks)
    rows, bits = [], []
    for side, ell in labels:
        rows.append(sum(quadratic_nonresidue(record.p, ell) << i for i, record in enumerate(records)))
        bits.append(shadow_target_bit(side, ell))
    labels.append(PARITY)
    rows.append((1 << len(records)) - 1)
    bits.append(1)
    return labels, rows, bits


def gf2_left_kernel(rows: Sequence[int]) -> tuple:
    """Basis (as bitmasks over row indices) of {c : XOR of rows[i] for i in c == 0}, and the rank."""
    pivots: dict = {}
    kernel = []
    for i, row in enumerate(rows):
        value, combo = row, 1 << i
        while value:
            low = value & -value
            if low in pivots:
                pivot_value, pivot_combo = pivots[low]
                value ^= pivot_value
                combo ^= pivot_combo
            else:
                pivots[low] = (value, combo)
                break
        if not value:
            kernel.append(combo)
    return kernel, len(pivots)


def gf2_particular_solution(rows: Sequence[int], bits: Sequence[int], variables: int) -> Optional[int]:
    """A bitmask x over `variables` with popcount(rows[r] & x) == bits[r] mod 2 for all r, or None."""
    if len(rows) != len(bits):
        raise ValueError("row/right-hand-side length mismatch")
    pivots: dict = {}
    for row, bit in zip(rows, bits):
        value, rhs = row, bit & 1
        while value:
            low = value & -value
            if low in pivots:
                pivot_value, pivot_rhs = pivots[low]
                value ^= pivot_value
                rhs ^= pivot_rhs
            else:
                pivots[low] = (value, rhs)
                break
        if not value and rhs:
            return None
    solution = 0
    for low in sorted(pivots, reverse=True):
        value, rhs = pivots[low]
        if (bin(value & solution).count("1") + rhs) % 2:
            solution |= low
    for row, bit in zip(rows, bits):
        if bin(row & solution).count("1") % 2 != bit & 1:
            raise ArithmeticError("GF(2) back-substitution failed")
    if solution >> variables:
        raise ArithmeticError("solution uses variables outside the pool")
    return solution


def separating_kernel_elements(kernel: Sequence[int], bits: Sequence[int]) -> list:
    return [combo for combo in kernel
            if sum(bits[k] for k in range(len(bits)) if combo >> k & 1) % 2 == 1]


def combo_labels(combo: int, labels: Sequence[tuple]) -> list:
    return [list(labels[k]) for k in range(len(labels)) if combo >> k & 1]


def shadow_analysis(labels: Sequence[tuple], rows: Sequence[int], bits: Sequence[int],
                    variables: int) -> dict:
    """Rank, left-kernel dimension, the forced relation, and a direct certificate either way."""
    kernel, rank = gf2_left_kernel(rows)
    index = {tuple(label): k for k, label in enumerate(labels)}
    forced_mask = 0
    for label in FORCED_RELATION:
        if label in index:
            forced_mask |= 1 << index[label]
    forced_in_kernel = (bin(forced_mask).count("1") == 2 and
                        all(rows[k] == rows[index[PARITY]] for k in range(len(rows)) if forced_mask >> k & 1))
    separating = separating_kernel_elements(kernel, bits)
    result = {
        "rows": len(rows), "variables": variables, "rank": rank, "kernel_dimension": len(kernel),
        "forced_relation_in_kernel": forced_in_kernel,
        "kernel_is_exactly_forced_relation": forced_in_kernel and len(kernel) == 1,
        "separating_kernel_basis_elements": len(separating),
    }
    if separating:
        best = min(separating, key=lambda combo: bin(combo).count("1"))
        result.update(status="obstructed", certificate={
            "kind": "legendre_character", "weight": bin(best).count("1"),
            "labels": combo_labels(best, labels)})
    else:
        solution = gf2_particular_solution(rows, bits, variables)
        if solution is None:
            raise ArithmeticError("no separating character yet no GF(2) solution")
        result.update(status="consistent", certificate={
            "kind": "gf2_solution_indices",
            "indices": [i for i in range(variables) if solution >> i & 1],
            "scope": "mod-2 shadow only; not a subset solution of the group problem"})
    return result


def check_shadow_certificate(labels: Sequence[tuple], rows: Sequence[int], bits: Sequence[int],
                             variables: int, certificate: dict) -> str:
    """Direct, elimination-free check of a stored shadow certificate."""
    if certificate["kind"] == "legendre_character":
        index = {tuple(label): k for k, label in enumerate(labels)}
        chosen = [index[tuple(label)] for label in certificate["labels"]]
        if len(set(chosen)) != len(chosen) or not chosen:
            raise ValueError("invalid character support")
        acc = 0
        for k in chosen:
            acc ^= rows[k]
        if acc or sum(bits[k] for k in chosen) % 2 != 1:
            raise ValueError("stored character does not annihilate the pool or does not separate")
        return "obstructed"
    if certificate["kind"] == "gf2_solution_indices":
        indices = certificate["indices"]
        if len(set(indices)) != len(indices) or any(not 0 <= i < variables for i in indices):
            raise ValueError("invalid solution indices")
        mask = sum(1 << i for i in indices)
        if any(bin(row & mask).count("1") % 2 != bit for row, bit in zip(rows, bits)):
            raise ValueError("stored GF(2) solution fails the system")
        return "consistent"
    raise ValueError("unknown certificate kind")


# ---------------------------------------------------------------------------
# Recorded characters as Legendre functionals
# ---------------------------------------------------------------------------

def character_labels(instance: RealInstance, modulus: int, terms: Sequence[Sequence[int]]) -> list:
    """Translate a recorded modulus-2 character into (side, prime) / parity labels."""
    if modulus != 2:
        raise ValueError("only modulus-two characters have a Legendre reading")
    labels = coordinate_labels(instance)
    valid = {j for j, _, _ in two_primary_coordinates(instance)} | {len(instance.orders) - 1}
    out = []
    for j, coefficient in terms:
        if coefficient != 1 or j not in valid:
            raise ValueError("character term is not a 2-primary coordinate with coefficient one")
        out.append(labels[j])
    if len(set(out)) != len(out):
        raise ValueError("repeated block in character")
    return out


def evaluate_character(labels: Sequence[tuple], p: int) -> int:
    total = 0
    for side, ell in labels:
        total += 1 if (side, ell) == PARITY else quadratic_nonresidue(p, ell)
    return total % 2


def character_target_value(labels: Sequence[tuple]) -> int:
    return sum(shadow_target_bit(side, ell) for side, ell in labels) % 2


def describe_character(labels: Sequence[tuple]) -> dict:
    """Arithmetic breakdown of a Legendre character and its canonical form."""
    label_set = {tuple(label) for label in labels}
    minus = sorted(ell for side, ell in label_set if side == "minus")
    plus = sorted(ell for side, ell in label_set if side == "plus")
    canonical = label_set ^ FORCED_RELATION if ("plus", 3) in label_set else set(label_set)
    canonical_plus = sorted(ell for side, ell in canonical if side == "plus")
    return {
        "weight": len(label_set),
        "minus_primes": minus,
        "plus_primes": plus,
        "sign_carrying_plus_primes": [ell for ell in plus if ell % 4 == 3],
        "includes_parity": PARITY in label_set,
        "target_value": character_target_value(sorted(label_set)),
        "canonical_modulo_forced_relation": {
            "labels": [list(label) for label in sorted(canonical)],
            "minus_only_plus_parity": not canonical_plus and PARITY in canonical,
            "minus_primes": sorted(ell for side, ell in canonical if side == "minus"),
            "plus_primes": canonical_plus,
        },
    }


# ---------------------------------------------------------------------------
# Family membership, transfer tests, minimum weight
# ---------------------------------------------------------------------------

def in_declared_family(record: PrimeRecord, config: dict) -> bool:
    """Does a certified record meet a cell's declared harvest family (bounds, j, caps)?"""
    plus_bound, minus_bound = int(config["plus_bound"]), int(config["minus_bound"])
    factors, cap = int(config["factors"]), int(config["prime_power_cap"])
    minus, plus = dict(record.minus), dict(record.plus)
    if record.p % 80 != 3 or record.p >= 1 << 64 or minus.get(2) != 1 or plus.get(2) != 2:
        return False
    medium = [q for q in minus if q != 2]
    if len(medium) != factors or any(not plus_bound < q <= minus_bound or minus[q] != 1 for q in medium):
        return False
    if any(q != 2 and (q > plus_bound or q == 5) for q in plus):
        return False
    return all(q**e <= cap for q, e in plus.items())


def transfer_test(labels: Sequence[tuple], records: Sequence[PrimeRecord]) -> dict:
    violations = [record.p for record in records if evaluate_character(labels, record.p)]
    return {"members_tested": len(records), "violations": len(violations),
            "violating_primes_sample": violations[:8]}


def minimum_weight_separating(rows: Sequence[int], bits: Sequence[int], max_weight: int) -> dict:
    """Exhaustive search for the lightest row combination that annihilates all generators
    and separates the target, up to max_weight (<= 4). Rows are bitmasks over generators."""
    if not 1 <= max_weight <= 4:
        raise ValueError("weight cap must be between 1 and 4")
    count = len(rows)
    for i in range(count):
        if rows[i] == 0 and bits[i]:
            return {"status": "found", "weight": 1, "indices": [i]}
    by_value: dict = {}
    for i, row in enumerate(rows):
        by_value.setdefault(row, []).append(i)
    if max_weight >= 2:
        for i in range(count):
            for k in by_value.get(rows[i], ()):
                if k > i and bits[i] ^ bits[k]:
                    return {"status": "found", "weight": 2, "indices": [i, k]}
    if max_weight >= 3:
        for i in range(count):
            for k in range(i + 1, count):
                for m in by_value.get(rows[i] ^ rows[k], ()):
                    if m > k and bits[i] ^ bits[k] ^ bits[m]:
                        return {"status": "found", "weight": 3, "indices": [i, k, m]}
    if max_weight >= 4:
        pairs: dict = {}
        for i in range(count):
            for k in range(i + 1, count):
                pairs.setdefault(rows[i] ^ rows[k], []).append((i, k))
        for group in pairs.values():
            for a in range(len(group)):
                for b in range(a + 1, len(group)):
                    i, k = group[a]
                    m, n = group[b]
                    if len({i, k, m, n}) == 4 and bits[i] ^ bits[k] ^ bits[m] ^ bits[n]:
                        return {"status": "found", "weight": 4, "indices": [i, k, m, n]}
    return {"status": "completed_scope", "weight": None, "indices": None,
            "scope": f"no separating character of weight <= {max_weight}"}


# ---------------------------------------------------------------------------
# Exact primary subgroup index with algorithm-free certificates
# ---------------------------------------------------------------------------

def _valuation(x: int, ell: int) -> int:
    if x == 0:
        raise ValueError("valuation of zero")
    v = 0
    while x % ell == 0:
        x //= ell
        v += 1
    return v


def howell_form(rows: Sequence[Sequence[int]], ell: int, exponent: int, track: bool) -> list:
    """Howell form of the row module of `rows` in (Z/ell^exponent)^R.

    Returns [(row, pivot_column, pivot_valuation, combination)] where each row is a
    combination (coefficients modulo ell^exponent over the input rows) of the inputs,
    pivot columns strictly increase, and every later row vanishes at earlier pivots.
    """
    modulus = ell**exponent
    width = len(rows[0]) if rows else 0
    work = [[x % modulus for x in row] for row in rows]
    combos = ([[1 if k == i else 0 for k in range(len(rows))] for i in range(len(rows))]
              if track else [None] * len(rows))
    result = []
    for column in range(width):
        best = None
        for idx, row in enumerate(work):
            if row[column]:
                v = _valuation(row[column], ell)
                if best is None or v < best[0]:
                    best = (v, idx)
                    if v == 0:
                        break
        if best is None:
            continue
        v, idx = best
        pivot, pivot_combo = work.pop(idx), combos.pop(idx)
        unit_inverse = pow(pivot[column] // ell**v, -1, modulus)
        if unit_inverse != 1:
            pivot = [x * unit_inverse % modulus for x in pivot]
            if track:
                pivot_combo = [x * unit_inverse % modulus for x in pivot_combo]
        power = ell**v
        kept, kept_combos = [], []
        for row, combo in zip(work, combos):
            if row[column]:
                multiplier = row[column] // power
                row = [(a - multiplier * b) % modulus for a, b in zip(row, pivot)]
                if track:
                    combo = [(a - multiplier * b) % modulus for a, b in zip(combo, pivot_combo)]
            if any(row):
                kept.append(row)
                kept_combos.append(combo)
        work, combos = kept, kept_combos
        closure = modulus // power
        extra = [x * closure % modulus for x in pivot]
        if any(extra):
            work.append(extra)
            combos.append([x * closure % modulus for x in pivot_combo] if track else None)
        result.append((pivot, column, v, pivot_combo))
    if any(any(row) for row in work):
        raise ArithmeticError("Howell elimination left an unreduced row")
    return result


def snf_kernel(matrix: Sequence[Sequence[int]], ell: int, exponent: int) -> list:
    """Generators of {b in (Z/ell^exponent)^R : matrix . b = 0} via Smith reduction
    with tracked column operations (matrix given as N rows of length R)."""
    modulus = ell**exponent
    height = len(matrix)
    width = len(matrix[0]) if matrix else 0
    work = [[x % modulus for x in row] for row in matrix]
    columns = [[1 if i == j else 0 for i in range(width)] for j in range(width)]
    valuations = []
    k = 0
    while k < min(height, width):
        best = None
        for i in range(k, height):
            row = work[i]
            for j in range(k, width):
                if row[j]:
                    v = _valuation(row[j], ell)
                    if best is None or v < best[0]:
                        best = (v, i, j)
                        if v == 0:
                            break
            if best is not None and best[0] == 0:
                break
        if best is None:
            break
        v, i, j = best
        if i != k:
            work[k], work[i] = work[i], work[k]
        if j != k:
            for row in work:
                row[k], row[j] = row[j], row[k]
            columns[k], columns[j] = columns[j], columns[k]
        power = ell**v
        unit_inverse = pow(work[k][k] // power, -1, modulus)
        if unit_inverse != 1:
            work[k] = [x * unit_inverse % modulus for x in work[k]]
        pivot_row = work[k]
        for i in range(k + 1, height):
            if work[i][k]:
                multiplier = work[i][k] // power
                work[i] = [(a - multiplier * b) % modulus for a, b in zip(work[i], pivot_row)]
        # Column k is now nonzero only in row k (rows above were cleared at their own
        # steps), so a column operation col_j -= m col_k changes only entry (k, j).
        for j in range(k + 1, width):
            if pivot_row[j]:
                multiplier = pivot_row[j] // power
                pivot_row[j] = 0
                columns[j] = [(a - multiplier * b) % modulus for a, b in zip(columns[j], columns[k])]
        valuations.append(v)
        k += 1
    generators = []
    for i, v in enumerate(valuations):
        scale = ell**(exponent - v)
        if scale < modulus:
            vector = [x * scale % modulus for x in columns[i]]
            if any(vector):
                generators.append(vector)
    generators.extend(columns[len(valuations):])
    return generators


def primary_coordinates(orders: Sequence[int], ell: int) -> list:
    return [j for j, order in enumerate(orders) if trial_factors(order) == {ell: _valuation(order, ell)}]


def primary_index_certificate(orders: Sequence[int], vectors: Sequence[Sequence[int]], ell: int) -> dict:
    """Compute [G_ell : H_ell] with triangular witnesses (lower bound on |H|) and
    triangular annihilating characters (lower bound on |H^perp|)."""
    coords = primary_coordinates(orders, ell)
    if not coords:
        raise ValueError("no coordinates for this prime")
    exps = [_valuation(orders[j], ell) for j in coords]
    exponent = max(exps)
    modulus = ell**exponent
    scales = [modulus // orders[j] for j in coords]
    embedded = [[vector[j] * s % modulus for j, s in zip(coords, scales)] for vector in vectors]
    witnesses = []
    for row, column, v, combo in howell_form(embedded, ell, exponent, track=True):
        witnesses.append({"coefficients": combo, "pivot": coords[column]})
    kernel = snf_kernel(embedded, ell, exponent) if embedded else [
        [1 if i == j else 0 for i in range(len(coords))] for j in range(len(coords))]
    reduced = []
    for b in kernel:
        native = [b[i] % orders[j] for i, j in enumerate(coords)]
        if any(native):
            reduced.append([x * s % modulus for x, s in zip(native, scales)])
    characters = []
    for row, column, v, _ in (howell_form(reduced, ell, exponent, track=False) if reduced else []):
        characters.append({"coefficients": [row[i] // scales[i] for i in range(len(coords))],
                           "pivot": coords[column]})
    return {"prime": ell, "exponent": exponent, "coordinates": coords,
            "witnesses": witnesses, "characters": characters}


def _order_in(x: int, modulus: int) -> int:
    return modulus // math.gcd(x % modulus, modulus)


def verify_primary_index_certificate(orders: Sequence[int], vectors: Sequence[Sequence[int]],
                                     target: Sequence[int], certificate: dict,
                                     expected_prime: Optional[int] = None) -> dict:
    """Algorithm-free check: witnesses lie in H and are triangular; characters annihilate
    H and are triangular; the two coset lower bounds multiply to |G_ell|. Then the
    characters generate H^perp, so target membership is decided by them directly.
    `expected_prime` binds the certificate to the primary part it is filed under."""
    ell = certificate["prime"]
    if not isinstance(ell, int) or isinstance(ell, bool) or ell < 2:
        raise ValueError("certificate prime must be an integer at least two")
    if expected_prime is not None and ell != expected_prime:
        raise ValueError("certificate is filed under a different prime than it certifies")
    coords = list(certificate["coordinates"])
    if coords != primary_coordinates(orders, ell):
        raise ValueError("certificate coordinates differ from the group's primary part")
    exponent = certificate["exponent"]
    modulus = ell**exponent
    if any(modulus % orders[j] for j in coords) or modulus != max(orders[j] for j in coords):
        raise ValueError("certificate exponent does not match the component orders")
    position = {j: i for i, j in enumerate(coords)}
    witnesses = list(certificate["witnesses"])
    elements = []
    for witness in witnesses:
        coefficients = list(witness["coefficients"])
        if len(coefficients) != len(vectors) or any(
                not isinstance(c, int) or isinstance(c, bool) or not 0 <= c < modulus for c in coefficients):
            raise ValueError("witness coefficients must be canonical integers")
        element = [0] * len(coords)
        for c, vector in zip(coefficients, vectors):
            if c:
                element = [(e + c * vector[j]) for e, j in zip(element, coords)]
        elements.append([e % orders[j] for e, j in zip(element, coords)])
    bound_h = 1
    for idx, (witness, element) in enumerate(zip(witnesses, elements)):
        pivot = witness["pivot"]
        if pivot not in position or (idx and pivot <= witnesses[idx - 1]["pivot"]):
            raise ValueError("witness pivots must be increasing coordinate indices")
        i = position[pivot]
        if element[i] == 0 or any(later[i] for later in elements[idx + 1:]):
            raise ValueError("witnesses are not triangular at their pivots")
        bound_h *= _order_in(element[i], orders[pivot])
    characters = list(certificate["characters"])
    bound_dual = 1
    for idx, character in enumerate(characters):
        coefficients = list(character["coefficients"])
        if len(coefficients) != len(coords) or any(
                not isinstance(b, int) or isinstance(b, bool) or not 0 <= b < orders[j]
                for b, j in zip(coefficients, coords)):
            raise ValueError("character coefficients must be canonical in the dual group")
        weights = [b * (modulus // orders[j]) for b, j in zip(coefficients, coords)]
        for vector in vectors:
            if sum(w * vector[j] for w, j in zip(weights, coords)) % modulus:
                raise ValueError("character does not annihilate every generator")
        pivot = character["pivot"]
        if pivot not in position or (idx and pivot <= characters[idx - 1]["pivot"]):
            raise ValueError("character pivots must be increasing coordinate indices")
        i = position[pivot]
        if coefficients[i] == 0 or any(later["coefficients"][i] for later in characters[idx + 1:]):
            raise ValueError("characters are not triangular at their pivots")
        bound_dual *= _order_in(coefficients[i], orders[pivot])
    group_order = math.prod(orders[j] for j in coords)
    if bound_h * bound_dual != group_order:
        raise ValueError("coset lower bounds do not multiply to the primary group order")
    member = all(
        sum(b * (modulus // orders[j]) * target[j] for b, j in zip(character["coefficients"], coords))
        % modulus == 0 for character in characters)
    return {"prime": ell, "index": bound_dual, "subgroup_order": bound_h,
            "group_order": group_order, "target_member": member,
            "witnesses": len(witnesses), "characters": len(characters)}


def brute_force_subgroup(orders: Sequence[int], vectors: Sequence[Sequence[int]]) -> set:
    """Tiny-group oracle used by the tests only."""
    zero = tuple([0] * len(orders))
    seen, frontier = {zero}, [zero]
    while frontier:
        nxt = []
        for x in frontier:
            for vector in vectors:
                y = tuple((a + b) % m for a, b, m in zip(x, vector, orders))
                if y not in seen:
                    seen.add(y)
                    nxt.append(y)
        frontier = nxt
    return seen


# ---------------------------------------------------------------------------
# Watchdog workers (module level so the spawned process can import them)
# ---------------------------------------------------------------------------

def _work_index(payload):
    """Large certificates are written to a file by the worker: the shared watchdog
    joins the child before draining its result queue, so a result larger than the
    pipe buffer would block the child until the deadline (reported to the
    coordinator as a shared-interface note). Only a small summary crosses the queue."""
    orders, vectors, ell, out_path = payload
    certificate = primary_index_certificate(orders, vectors, ell)
    Path(out_path).write_text(json.dumps(certificate), encoding="utf-8")
    return {"path": out_path, "witnesses": len(certificate["witnesses"]),
            "characters": len(certificate["characters"])}


def _index_limited(orders, vectors, ell, label: str) -> dict:
    """Run the index computation under the watchdog and load its file-borne certificate."""
    with tempfile.TemporaryDirectory(prefix="bf_obstructions_") as folder:
        out_path = str(Path(folder) / f"index_{ell}.json")
        limited = _limited(_work_index, (orders, vectors, ell, out_path), label)
        if limited["status"] == "ok":
            limited["value"] = json.loads(Path(out_path).read_text(encoding="utf-8"))
    return limited


def _work_min_weight(payload):
    rows, bits, cap = payload
    return minimum_weight_separating(rows, bits, cap)


def _work_shadow(payload):
    labels, rows, bits, variables = payload
    return shadow_analysis([tuple(label) for label in labels], rows, bits, variables)


def _limited(fn, payload, label: str) -> dict:
    kind, value, elapsed = run_limited(fn, payload, BUDGETS["wall_seconds_per_probe"])
    if kind == "ok":
        return {"status": "ok", "value": value, "seconds": elapsed, "probe": label}
    status = "timeout_enforced" if kind == "timeout" else "worker_error"
    return {"status": status, "value": None, "detail": value, "seconds": elapsed, "probe": label}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def _hash_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_cells(harvest_path: Path = DEFAULT_HARVEST) -> tuple:
    """Load fs_harvest.json.gz read-only; rebuild and re-verify every instance."""
    payload = harvest_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_HARVEST_SHA256:
        raise ValueError("fs_harvest artifact hash differs from the frozen first-wave input")
    data = json.loads(gzip.decompress(payload) if harvest_path.suffix == ".gz" else payload)
    if data.get("schema") != "fs-harvest/v2":
        raise ValueError("unexpected fs_harvest schema")
    cells = {}
    for cell in data["cells"]:
        if cell["status"] != "encoded_and_verified":
            raise ValueError("unexpected cell status")
        instance = instance_from_json(cell["instance"])
        verify_encoding(instance)
        cells[cell["name"]] = (cell, instance)
    if tuple(cells) != CELLS:
        raise ValueError("unexpected cell set or order")
    return digest, cells


def pilot_cross_check(cells: dict, pilot_path: Path = DEFAULT_PILOT) -> dict:
    """The anchor rerun must coincide with the frozen pilot's medium-complete instance."""
    payload = pilot_path.read_bytes()
    digest = hashlib.sha256(payload).hexdigest()
    if digest != EXPECTED_PILOT_SHA256:
        raise ValueError("pilot artifact hash differs from the frozen input")
    data = json.loads(gzip.decompress(payload))
    verify_saved_report(data)
    run = next(r for r in data["runs"] if r["name"] == "medium-complete-family")
    pilot = instance_from_json(run["instance"])
    anchor = cells[ANCHOR][1]
    identical = (pilot.records == anchor.records and pilot.orders == anchor.orders
                 and pilot.vectors == anchor.vectors and pilot.target == anchor.target)
    if not identical:
        raise ValueError("anchor rerun differs from the frozen pilot instance")
    return {"pilot_sha256": digest, "anchor_identical_to_pilot_medium_complete": True,
            "primes": len(anchor.records)}


def recorded_character(cell: dict) -> Optional[dict]:
    checks = cell["structure"]["necessary_target_checks"]
    if checks["coordinate_obstructions"]:
        raise ValueError("unexpected coordinate obstruction in a first-wave cell")
    found = [entry for entry in checks["prime_field_checks"] if entry["consistent"] is False]
    if not found:
        return None
    if len(found) != 1 or found[0]["prime"] != 2:
        raise ValueError("unexpected non-binary prime-field obstruction")
    obstruction = found[0]["obstruction"]
    return {"modulus": int(obstruction["modulus"]),
            "terms": [[int(j), int(c)] for j, c in obstruction["terms"]]}


def direct_character_check(instance: RealInstance, modulus: int, terms: Sequence[Sequence[int]]) -> None:
    """Independent direct recheck (also run through the shared verify_obstruction)."""
    for j, c in terms:
        if c * instance.orders[j] % modulus:
            raise ValueError("character undefined on a component")
    for vector in instance.vectors:
        if sum(c * vector[j] for j, c in terms) % modulus:
            raise ValueError("character fails to annihilate a generator")
    if sum(c * instance.target[j] for j, c in terms) % modulus == 0:
        raise ValueError("character fails to separate the target")
    verify_obstruction(instance.orders, instance.vectors, instance.target, modulus,
                       [(j, c) for j, c in terms])


# ---------------------------------------------------------------------------
# Analysis driver
# ---------------------------------------------------------------------------

def _hex(n: int) -> str:
    return hex(n)


def analyze(harvest_path: Path = DEFAULT_HARVEST, pilot_path: Path = DEFAULT_PILOT) -> dict:
    started = time.monotonic()
    harvest_sha, cells = load_cells(harvest_path)
    cross = pilot_cross_check(cells, pilot_path)
    report_cells = []
    anchor_index = None
    for name in CELLS:
        cell, instance = cells[name]
        config = cell["harvest"]["config"]
        entry = {"name": name, "config": config, "pool_size": len(instance.records),
                 "components": len(instance.orders)}
        entry["legendre_shadow"] = legendre_shadow_check(instance)
        entry["forced_three_relation"] = forced_three_relation(instance)
        labels, rows, bits = shadow_system(instance.records)
        own_two_primary = {(side, ell) for _, side, ell in two_primary_coordinates(instance)} | {PARITY}
        if set(labels) != own_two_primary:
            raise ArithmeticError("declared block set differs from the instance's 2-primary blocks")
        shadow = _limited(_work_shadow, (labels, rows, bits, len(instance.records)), f"{name}:shadow")
        entry["shadow"] = shadow
        if shadow["status"] == "ok":
            check_shadow_certificate(labels, rows, bits, len(instance.records), shadow["value"]["certificate"])
        recorded = recorded_character(cell)
        if recorded is None:
            entry["recorded_character"] = None
        else:
            direct_character_check(instance, recorded["modulus"], recorded["terms"])
            char_labels = character_labels(instance, recorded["modulus"], recorded["terms"])
            if any(evaluate_character(char_labels, record.p) for record in instance.records):
                raise ArithmeticError("Legendre reading of the character fails on its own pool")
            if character_target_value(char_labels) != 1:
                raise ArithmeticError("Legendre reading of the character does not separate the target")
            entry["recorded_character"] = {
                **recorded, "direct_recheck": "verified", "labels": [list(l) for l in char_labels],
                "description": describe_character(char_labels),
            }
            entry["minimum_weight"] = _limited(_work_min_weight, (rows, bits, BUDGETS["min_weight_cap"]),
                                               f"{name}:min_weight")
            if entry["minimum_weight"]["status"] == "ok":
                found = entry["minimum_weight"]["value"]
                if found["status"] == "found":
                    found["labels"] = combo_labels(sum(1 << k for k in found["indices"]), labels)
                    found["description"] = describe_character([tuple(l) for l in found["labels"]])
                    check_shadow_certificate(labels, rows, bits, len(instance.records),
                                             {"kind": "legendre_character", "labels": found["labels"]})
            transfers = []
            own = {record.p for record in instance.records}
            for other in TRANSFERS[name]:
                other_records = cells[other][1].records
                members = [r for r in other_records if in_declared_family(r, config) and r.p not in own]
                overlap = sum(1 for r in other_records if r.p in own)
                test = transfer_test(char_labels, members)
                test.update(source_pool=other, overlap_with_own_pool=overlap)
                transfers.append(test)
            entry["transfer_tests"] = transfers
        # exact 2-primary index (certificate stored for the anchor only)
        limited = _index_limited(instance.orders, instance.vectors, 2, f"{name}:index:2")
        if limited["status"] == "ok":
            certificate = limited["value"]
            checked = verify_primary_index_certificate(instance.orders, instance.vectors,
                                                      instance.target, certificate, expected_prime=2)
            stored = name in BUDGETS["index_certificates_stored_for"]
            summary = {"status": "verified" if stored else "verified_at_generation_only",
                       "seconds": limited["seconds"],
                       "log2_index": checked["index"].bit_length() - 1,
                       "index_hex": _hex(checked["index"]),
                       "log2_group_order": checked["group_order"].bit_length() - 1,
                       "target_member_2primary": checked["target_member"],
                       "witnesses": checked["witnesses"], "characters": checked["characters"],
                       "certificate_stored": stored}
            if _hex(checked["index"]) != _hex(1 << summary["log2_index"]):
                raise ArithmeticError("2-primary index is not a power of two")
            entry["index_2primary"] = summary
            if name == ANCHOR:
                anchor_index = {"2": certificate}
        else:
            entry["index_2primary"] = {"status": limited["status"], "seconds": limited["seconds"],
                                       "detail": limited.get("detail")}
        report_cells.append(entry)
        print(f"{name}: shadow {shadow['status']}/{shadow['value']['status'] if shadow['status']=='ok' else '-'}, "
              f"index2 {entry['index_2primary'].get('log2_index', entry['index_2primary']['status'])}",
              flush=True)
    # anchor odd primary parts
    anchor_instance = cells[ANCHOR][1]
    odd_primes = sorted({next(iter(trial_factors(order))) for order in anchor_instance.orders} - {2})
    odd_results = []
    anchor_full = {"odd_primes": len(odd_primes), "certificates_stored": anchor_index is not None}
    for ell in odd_primes:
        limited = _index_limited(anchor_instance.orders, anchor_instance.vectors, ell,
                                 f"{ANCHOR}:index:{ell}")
        if limited["status"] != "ok":
            odd_results.append({"prime": ell, "status": limited["status"], "seconds": limited["seconds"]})
            continue
        checked = verify_primary_index_certificate(anchor_instance.orders, anchor_instance.vectors,
                                                   anchor_instance.target, limited["value"],
                                                   expected_prime=ell)
        if anchor_index is not None:
            anchor_index[str(ell)] = limited["value"]
        odd_results.append({"prime": ell, "status": "verified", "index": checked["index"],
                            "target_member": checked["target_member"], "seconds": limited["seconds"],
                            "coordinates": len(limited["value"]["coordinates"])})
    anchor_full["odd_results"] = odd_results
    verified_odd = [r for r in odd_results if r["status"] == "verified"]
    anchor_full["all_odd_parts_verified"] = len(verified_odd) == len(odd_primes)
    anchor_full["odd_index_product"] = math.prod(r["index"] for r in verified_odd)
    two = next(e for e in report_cells if e["name"] == ANCHOR)["index_2primary"]
    if two.get("status") == "verified" and anchor_full["all_odd_parts_verified"]:
        total = int(two["index_hex"], 16) * anchor_full["odd_index_product"]
        anchor_full["total_index"] = total
        anchor_full["real_target_member"] = (two["target_member_2primary"]
                                             and all(r["target_member"] for r in verified_odd))
        anchor_full["status"] = "verified"
    else:
        anchor_full["status"] = "incomplete"
    print(f"anchor full index: {anchor_full.get('total_index')} ({anchor_full['status']})", flush=True)
    # union probes
    unions = []
    for label, cell_name, sources in UNIONS:
        config = cells[cell_name][0]["harvest"]["config"]
        pool = {record.p: record for record in cells[cell_name][1].records}
        for source in sources:
            for record in cells[source][1].records:
                if in_declared_family(record, config) and record.p not in pool:
                    pool[record.p] = record
        records = [pool[p] for p in sorted(pool)]
        if not all(in_declared_family(r, config) for r in records):
            raise ArithmeticError("union pool contains a non-member")
        labels, rows, bits = shadow_system(records)
        limited = _limited(_work_shadow, (labels, rows, bits, len(records)), f"{label}:shadow")
        union = {"label": label, "family_of": cell_name, "sources": [cell_name, *sources],
                 "declared_pool_size": len(records),
                 "lambda_minus_bits": math.lcm(*(r.p - 1 for r in records)).bit_length(),
                 "lambda_plus_bits": math.lcm(*(r.p + 1 for r in records)).bit_length(),
                 "primes_hex": [_hex(r.p) for r in records], "shadow": limited}
        if limited["status"] == "ok":
            check_shadow_certificate(labels, rows, bits, len(records), limited["value"]["certificate"])
        unions.append(union)
        print(f"{label}: {limited['value']['status'] if limited['status']=='ok' else limited['status']}",
              flush=True)
    # completeness cross-checks between declared families
    c3_config = cells["fs-c3-wider-plus-complete"][0]["harvest"]["config"]
    c3_pool = {r.p for r in cells["fs-c3-wider-plus-complete"][1].records}
    eligible = [r.p for r in anchor_instance.records if in_declared_family(r, c3_config)]
    completeness = {"anchor_primes_in_c3_family": len(eligible),
                    "all_present_in_complete_c3_pool": all(p in c3_pool for p in eligible)}
    report = {
        "schema": SCHEMA, "track": TRACK, "plan": PLAN,
        "starting_commit": STARTING_COMMIT, "baseline_main": BASELINE_MAIN,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "python": platform.python_version(),
        "source_hash_normalization": "CRLF-to-LF",
        "source_sha256": {name: source_digest(HERE / name) for name in SOURCES},
        "inputs": {"fs_harvest.json.gz": harvest_sha, "real_pool_pilot.json.gz": cross["pilot_sha256"]},
        "budgets": BUDGETS, "probes": [list(p) for p in PROBES], "limits": LIMITS,
        "pilot_cross_check": cross, "cells": report_cells, "anchor_full_index": anchor_full,
        "anchor_index_certificates": anchor_index, "union_probes": unions,
        "completeness_cross_check": completeness,
        "elapsed_seconds": time.monotonic() - started,
    }
    return report


# ---------------------------------------------------------------------------
# Standalone verification (never runs Howell/Smith elimination or the searches)
# ---------------------------------------------------------------------------

def verify_report(report: dict, harvest_path: Path = DEFAULT_HARVEST,
                  pilot_path: Path = DEFAULT_PILOT) -> dict:
    if report.get("schema") != SCHEMA or report.get("source_hash_normalization") != "CRLF-to-LF":
        raise ValueError("unknown report schema")
    if report["starting_commit"] != STARTING_COMMIT:
        raise ValueError("unexpected starting commit")
    if report["source_sha256"].get("bf_obstructions.py") != source_digest(HERE / "bf_obstructions.py"):
        raise ValueError("S2 source hash mismatch")
    harvest_sha, cells = load_cells(harvest_path)
    if report["inputs"]["fs_harvest.json.gz"] != harvest_sha:
        raise ValueError("input hash mismatch")
    cross = pilot_cross_check(cells, pilot_path)
    if report["inputs"]["real_pool_pilot.json.gz"] != cross["pilot_sha256"]:
        raise ValueError("pilot hash mismatch")
    summary = {"cells": 0, "characters_rechecked": 0, "shadow_certificates": 0,
               "transfer_tests": 0, "index_certificates": 0, "union_probes": 0,
               "min_weight_found_checked": 0, "min_weight_completed_scope": 0}
    if [e["name"] for e in report["cells"]] != list(CELLS):
        raise ValueError("cell list differs")
    anchor_instance = cells[ANCHOR][1]
    _verify_index_section(report, anchor_instance, summary)
    for entry in report["cells"]:
        cell, instance = cells[entry["name"]]
        config = cell["harvest"]["config"]
        if entry["pool_size"] != len(instance.records) or entry["config"] != config:
            raise ValueError("cell scope differs")
        if legendre_shadow_check(instance) != entry["legendre_shadow"]:
            raise ValueError("Legendre shadow annotation differs")
        if forced_three_relation(instance) != entry["forced_three_relation"]:
            raise ValueError("forced relation annotation differs")
        labels, rows, bits = shadow_system(instance.records)
        shadow = entry["shadow"]
        if shadow["status"] == "ok":
            value = shadow["value"]
            status = check_shadow_certificate(labels, rows, bits, len(instance.records), value["certificate"])
            if status != value["status"] or value["rows"] != len(rows):
                raise ValueError("shadow status disagrees with its certificate")
            # Rank/kernel numbers are algorithmic annotations; the forced relation is direct.
            if value["forced_relation_in_kernel"] is not True:
                raise ValueError("forced relation must be in the kernel of every cell")
            summary["shadow_certificates"] += 1
        recorded = entry["recorded_character"]
        if (recorded is None) != (recorded_character(cell) is None):
            raise ValueError("recorded-character presence differs from the first-wave artifact")
        if recorded is not None:
            if recorded_character(cell) != {"modulus": recorded["modulus"], "terms": recorded["terms"]}:
                raise ValueError("recorded character differs from the first-wave artifact")
            direct_character_check(instance, recorded["modulus"], recorded["terms"])
            char_labels = character_labels(instance, recorded["modulus"], recorded["terms"])
            if [list(l) for l in char_labels] != recorded["labels"]:
                raise ValueError("character labels differ")
            if describe_character(char_labels) != recorded["description"]:
                raise ValueError("character description differs")
            if any(evaluate_character(char_labels, r.p) for r in instance.records):
                raise ValueError("Legendre reading fails on the pool")
            summary["characters_rechecked"] += 1
            own = {r.p for r in instance.records}
            expected = []
            for other in TRANSFERS[entry["name"]]:
                other_records = cells[other][1].records
                members = [r for r in other_records if in_declared_family(r, config) and r.p not in own]
                test = transfer_test(char_labels, members)
                test.update(source_pool=other,
                            overlap_with_own_pool=sum(1 for r in other_records if r.p in own))
                expected.append(test)
            if expected != entry["transfer_tests"]:
                raise ValueError("transfer test annotations differ")
            summary["transfer_tests"] += len(expected)
            mw = entry["minimum_weight"]
            if mw["status"] == "ok":
                found = mw["value"]
                if found["status"] == "found":
                    check_shadow_certificate(labels, rows, bits, len(instance.records),
                                             {"kind": "legendre_character", "labels": found["labels"]})
                    if len(found["labels"]) != found["weight"]:
                        raise ValueError("weight annotation differs")
                    summary["min_weight_found_checked"] += 1
                elif found["status"] == "completed_scope":
                    # Direct recheck of the weights the verifier can afford: no zero row with
                    # target bit one and no equal-row pair with differing target bits.
                    if minimum_weight_separating(rows, bits, 2)["status"] != "completed_scope":
                        raise ValueError("a weight <= 2 separating character exists")
                    summary["min_weight_completed_scope"] += 1
                else:
                    raise ValueError("unknown minimum-weight status")
        if entry["name"] != ANCHOR and (entry["index_2primary"].get("status") == "verified"
                                        or entry["index_2primary"].get("certificate_stored")):
            raise ValueError("only the anchor stores a verified index certificate")
        summary["cells"] += 1
    for union in report["union_probes"]:
        label, cell_name, sources = next(u for u in UNIONS if u[0] == union["label"])
        config = cells[cell_name][0]["harvest"]["config"]
        pool = {record.p: record for record in cells[cell_name][1].records}
        for source in sources:
            for record in cells[source][1].records:
                if in_declared_family(record, config) and record.p not in pool:
                    pool[record.p] = record
        records = [pool[p] for p in sorted(pool)]
        if [_hex(r.p) for r in records] != union["primes_hex"]:
            raise ValueError("declared union pool differs")
        if union["shadow"]["status"] == "ok":
            labels, rows, bits = shadow_system(records)
            value = union["shadow"]["value"]
            if check_shadow_certificate(labels, rows, bits, len(records), value["certificate"]) != value["status"]:
                raise ValueError("union shadow status disagrees with its certificate")
            summary["union_probes"] += 1
    c3_config = cells["fs-c3-wider-plus-complete"][0]["harvest"]["config"]
    c3_pool = {r.p for r in cells["fs-c3-wider-plus-complete"][1].records}
    eligible = [r.p for r in anchor_instance.records if in_declared_family(r, c3_config)]
    if report["completeness_cross_check"] != {"anchor_primes_in_c3_family": len(eligible),
                                              "all_present_in_complete_c3_pool": all(p in c3_pool for p in eligible)}:
        raise ValueError("completeness cross-check differs")
    return summary


def _verify_index_section(report: dict, anchor_instance: RealInstance, summary: dict) -> None:
    """Anchor index certificates: always required, always checked, never read from annotations."""
    anchor_entry = next(e for e in report["cells"] if e["name"] == ANCHOR)
    index2 = anchor_entry["index_2primary"]
    certificates = report["anchor_index_certificates"]
    if index2.get("status") != "verified" or index2.get("certificate_stored") is not True:
        raise ValueError("the anchor's 2-primary index must be a stored, verified certificate")
    if not isinstance(certificates, dict) or "2" not in certificates:
        raise ValueError("anchor 2-primary certificate missing")
    anchor_two = verify_primary_index_certificate(anchor_instance.orders, anchor_instance.vectors,
                                                  anchor_instance.target, certificates["2"],
                                                  expected_prime=2)
    if (anchor_two["index"] != int(index2["index_hex"], 16)
            or index2["log2_index"] != anchor_two["index"].bit_length() - 1
            or anchor_two["target_member"] is not index2["target_member_2primary"]
            or anchor_two["witnesses"] != index2["witnesses"]
            or anchor_two["characters"] != index2["characters"]):
        raise ValueError("anchor 2-primary index annotation differs from its certificate")
    summary["index_certificates"] += 1
    full = report["anchor_full_index"]
    odd_primes = sorted({next(iter(trial_factors(o))) for o in anchor_instance.orders} - {2})
    if full["odd_primes"] != len(odd_primes):
        raise ValueError("odd prime count differs from the group")
    if full["status"] == "verified":
        # Derive the expected primary parts from the group; every one needs a complete,
        # correctly bound certificate, and the full result is recomputed from the
        # checked values rather than read from annotations.
        certificates = report["anchor_index_certificates"]
        if set(certificates) != {"2"} | {str(ell) for ell in odd_primes}:
            raise ValueError("certificate set differs from the group's primary parts")
        if full.get("all_odd_parts_verified") is not True or full.get("certificates_stored") is not True:
            raise ValueError("full index claims verified without complete stored certificates")
        results = list(full["odd_results"])
        if [r["prime"] for r in results] != odd_primes:
            raise ValueError("odd prime list differs from the group")
        product = 1
        member = True
        for ell, result in zip(odd_primes, results):
            if result["status"] != "verified":
                raise ValueError("odd result not verified yet full status claims verified")
            checked = verify_primary_index_certificate(anchor_instance.orders, anchor_instance.vectors,
                                                       anchor_instance.target, certificates[str(ell)],
                                                       expected_prime=ell)
            if (checked["index"] != result["index"] or checked["target_member"] is not result["target_member"]
                    or result["coordinates"] != len(certificates[str(ell)]["coordinates"])):
                raise ValueError("odd primary certificate disagrees with its annotation")
            product *= checked["index"]
            member = member and checked["target_member"]
            summary["index_certificates"] += 1
        if full["odd_index_product"] != product:
            raise ValueError("odd index product annotation differs")
        if full["total_index"] != anchor_two["index"] * product:
            raise ValueError("total index annotation differs")
        if full["real_target_member"] is not (member and anchor_two["target_member"]):
            raise ValueError("membership annotation differs")
    elif full["status"] == "incomplete":
        if "total_index" in full or "real_target_member" in full:
            raise ValueError("an incomplete full-index result must not carry a total or membership")
    else:
        raise ValueError("unknown full-index status")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--harvest", type=Path, default=DEFAULT_HARVEST)
    parser.add_argument("--pilot", type=Path, default=DEFAULT_PILOT)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", type=Path, help="verify a saved S2 report without elimination")
    parser.add_argument("--replace", action="store_true")
    args = parser.parse_args()
    if args.verify:
        payload = args.verify.read_bytes()
        if args.verify.suffix == ".gz":
            payload = gzip.decompress(payload)
        print(json.dumps(verify_report(json.loads(payload), args.harvest, args.pilot), indent=2))
        return
    if args.output.resolve() in (args.harvest.resolve(), args.pilot.resolve()):
        parser.error("output cannot replace a frozen input artifact")
    if args.output.exists() and not args.replace:
        parser.error("output exists; use --replace or another --output")
    report = analyze(args.harvest, args.pilot)
    verify_report(report, args.harvest, args.pilot)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = (json.dumps(report, indent=1) + "\n").encode("utf-8")
    with args.output.open("wb" if args.replace else "xb") as output:
        output.write(gzip.compress(payload, mtime=0) if args.output.suffix == ".gz" else payload)
    print(f"Saved {args.output}", flush=True)


if __name__ == "__main__":
    main()
