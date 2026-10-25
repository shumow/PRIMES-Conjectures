# S2 findings: the arithmetic behind the first-wave binary obstructions

**Track:** S2 (arithmetic obstructions) per `PLAN.md` §4 ·
**Branch:** `research/boolean-obstruction-analysis` ·
**Starting commit:** `0c9f03fb1e00dfd85cb9e2b37e15ed1e727c4915`
(integration head; baseline main `c114e844…`) ·
**Interpreter:** Python 3.11.17, standard library only ·
**Inputs (read-only):** `data/generated/fs_harvest.json.gz`
(sha256 `75f1599b05a84f0c…`, five serialized instances) and
`data/generated/real_pool_pilot.json.gz` (sha256 `008cf08ce3f0d3a2…`).
**Deliverables (S2-owned only):** `code/bf_obstructions.py`,
`code/test_bf_obstructions_correctness.py`,
`data/generated/bf_obstructions.json.gz` (schema `bf-obstructions/v1`), this
report. No shared file, dataset, paper or plan was modified; no prime was
harvested.

Reproduce from the repository root:

```text
python -B -m unittest discover -s code -p "*correctness.py" -v
python -B code/bf_obstructions.py --verify data/generated/bf_obstructions.json.gz
python -B code/bf_obstructions.py --output <new path>
```

## 0. Declared probes and budgets (fixed before computation)

Eight probes P0–P7 (listed in `bf_obstructions.PROBES`), one worker process,
an enforced 60 s wall per computational probe via the shared process watchdog
(`fs_controls.run_limited`), minimum-weight search capped at weight 4, no
retries, no parameter sweeps, no new harvesting, certificates stored in full
for the anchor only. Budgets were not raised. Outcomes use the plan's
vocabulary: `verified` (direct check), `completed_scope` (exhaustive declared
scope), `timeout_enforced` (inconclusive). Zero timeouts and zero worker
errors occurred; every probe completed inside its 60 s wall.

## 1. Two theorems that explain what the binary check is

**Proposition 1 (Legendre shadow).** Let `ℓ` be an odd prime, `e ≥ 1`, and
let `C = (Z/ℓ^e)^×` be cyclic with generator `g`. Write a unit as `x = g^a`
and let `c(x) = a mod 2^v` (`v = v₂(ℓ−1)`) be its 2-primary discrete-log
coordinate. Then `c(x) ≡ 0 (mod 2)` iff `x` is a quadratic residue modulo
`ℓ`. *Proof.* `|C|` is even, so `x` is a square in `C` iff `a` is even; a unit
is a square modulo `ℓ^e` iff it is a square modulo `ℓ` (Hensel, `ℓ` odd); and
`a mod 2^v` has the parity of `a`. ∎

Consequently, for a pool prime `p` the mod-2 reduction of its 2-primary
coordinate at block `ℓ` is `[(p/ℓ) = −1]`; the real target `(1 mod Λ₋, −1 mod
Λ₊)` reduces to `0` on every minus-side row, to `[ℓ ≡ 3 (mod 4)]` on a
plus-side row `ℓ` (since `(−1/ℓ) = −1` iff `ℓ ≡ 3 mod 4`), and to `1` on the
parity row (the `(Z/4)^×` factor). The pilot's GF(2) prime-field check is
therefore **exactly the system of Legendre symbols**: a 0/1 vector `x`
passes iff `∏_{i∈x} (p_i/ℓ) = +1` for every minus block prime, `= (−1/ℓ)` for
every plus block prime, and `|x|` is odd. No discrete logarithm is needed to
run it. Verified directly (P1) on **all 2-primary coordinates of all five
instances**: 393·483 + 95·13 + 540·253 + 365·225 + 739·430 = **727,569
vector entries and 2,132 target entries, zero mismatches**.

Two corollaries fix the vocabulary of everything below. (i) A separating
mod-2 character is a set `T` of block rows (possibly with the parity row)
such that every pool prime is a non-residue modulo an *even* number of the
primes in `T` (counting the parity row as a constant 1), while the target
value `#{ℓ ∈ T ∩ plus : ℓ ≡ 3 mod 4} + [parity ∈ T]` is *odd*. The target can
only be "seen" through **sign-carrying rows**: plus primes `≡ 3 (mod 4)` and
the parity row; minus rows and plus rows `≡ 1 (mod 4)` contribute nothing to
it. (ii) Since the real target is `2`-torsion in `G` (its odd-primary
components are `0`: `1` and `−1` both have trivial odd part), every character
that can separate it from the generated subgroup is 2-primary. This is why
all first-wave certificates have modulus 2 or 8 and why the odd prime-field
systems are trivially consistent (homogeneous).

**Proposition 2 (the forced 3-relation).** In every harvest family of this
project, `3` is a plus base prime and no minus base prime equals `3`
(`Q₋ ⊂ (B, B′]` with `B ≥ 3`). Then for every pool prime, `p ≡ 2 (mod 3)`
and `3 | p+1`. *Proof.* `m = (p−1)/2` is a product of minus base primes, so
`3 ∤ m`; if `m ≡ 1 (mod 3)` then `p = 2m+1 ≡ 0 (mod 3)`, impossible; hence
`m ≡ 2`, `3 | m+1 = (p+1)/2`. ∎ Therefore the plus-3 block exists in every
non-empty pool, its 2-primary coordinate (order 2) equals `1` for every pool
prime and for the target (`−1 ≡ 2 mod 3`), i.e. **the plus-3 row equals the
parity row on generators and target**. The character `χ₃ + π` annihilates the
generated subgroup and contains the target in its kernel. It is a
structural, family-forced, codimension-one relation and never an
obstruction; equivalently, every pool prime and every candidate `n` is
`≡ −1 (mod 12)`, so `(3/p) = 1` for all of them. Verified (P2) on all five
instances (every one of the 1,404 pool primes is `2 mod 3`; the plus-3 row is
the all-ones row in every cell).

## 2. The anchor: codimension one is exactly the forced relation, and the exact index is 2

| Anchor (483 primes, 1,132 components) | result |
|---|---|
| GF(2) rows / rank / left-kernel dimension | 394 / 393 / **1** |
| left kernel | **exactly `⟨χ₃ + π⟩`** (P2) |
| 2-primary part: `log₂|G₂|`, `log₂|H₂|`, index | 769, 768, **2** |
| 97 odd primary parts | all **index 1** (`H_ℓ = G_ℓ`) |
| **exact full index `[G : H]`** | **2** |
| real target membership (re-derived from the full annihilator) | **member**, agreeing with Track B |

Track B established index ≥ 2 and left the exact prime-power index unknown.
P7 settles it with algorithm-free certificates (stored in the dataset): for
each prime `ℓ`, a triangular set of witnesses (integer combinations of pool
vectors with increasing pivot coordinates and zeros below pivots) gives the
coset lower bound `|H_ℓ| ≥ ∏ ord(pivot entries)`, and a triangular set of
annihilating characters gives `|H_ℓ^⊥| ≥ ∏ ord(pivot coefficients)`; since
`|H_ℓ|·|H_ℓ^⊥| = |G_ℓ|`, equality of the product with `|G_ℓ|` certifies both
exactly, and then the listed characters generate the whole annihilator, so
target membership is decided by evaluating them. The verifier
(`verify_primary_index_certificate`) performs only these direct checks; the
test suite patches the Howell and Smith routines to raise while the saved
report is verified. The 2-primary annihilator of the anchor consists of the
single character `χ₃ + π` (weight 2, pivot at the plus-3 coordinate).

So the anchor's "codimension-one binary quotient constraint whose kernel
contains the real target" (plan §4 item 2) is **fully explained**: it is the
forced relation of Proposition 2, it holds for every pool of every cell, it
is the *only* relation on the anchor at any 2-power level, and the odd parts
are saturated (consistent with Track B's full odd prime-field ranks via
Nakayama, now certified directly). Membership of the real target is therefore
*exactly* the statement that the target satisfies `χ₃ + π = 0`, which it
does for the trivial reason that `n ≡ −1 (mod 12)`. This says nothing about
Boolean feasibility (plan §1).

## 3. The four obstructed pools in arithmetic terms (P0, P3, P4)

All four recorded characters re-verify directly against the original
generators and target (and through the shared `verify_obstruction`). Their
Legendre readings:

| cell | N | rows / rank / kernel | recorded character (weight) | sign-carrying rows | canonical form modulo `χ₃+π` |
|---|---:|---|---|---|---|
| c1 (547/2735, j=4, sampled) | 13 | 96 / 13 / 83 | 7 minus + plus-3 (8) | {3} | parity + 7 minus rows |
| c2 (547/5470, j=3, sampled) | 253 | 541 / 253 / 288 | 137 minus + plus-3 (138) | {3} | parity + 137 minus rows |
| c3 (1259/2735, j=3, **complete**) | 225 | 366 / 225 / 141 | 90 minus + 21 plus (111) | 11 plus primes ≡ 3 (4) | 90 minus + 21 plus rows |
| c4 (1259/6295, j=3, sampled) | 430 | 740 / 430 / 310 | 196 minus + plus-3 (197) | {3} | parity + 196 minus rows |

Reading: in c1, c2, c4 the certificate says *every pool prime is a quadratic
non-residue modulo an odd number of the listed minus primes* (the plus-3 term
is just the parity row in disguise), whereas the target — being `≡ 1` modulo
every minus prime — is a non-residue modulo none of them. In c3 the mixture
is 90 minus rows and 21 plus rows, of which 11 are `≡ 3 (mod 4)`, so the
target's value is 1 through those eleven sign-carrying rows. In every cell the
only coordinate dependence the obstruction has on the plus side (where the
target is nonzero) is through sign-carrying rows, as Proposition 1 predicts.

**Are these obstructions sparse/structured?** P4 searched exhaustively for
the lightest separating character up to weight 4 (`completed_scope`, under
60 s each):

| cell | lightest separating character |
|---|---|
| c1 | **weight 3**: `{minus 1453, minus 1667, plus 479}` — with 13 primes and `C(96,3) ≈ 1.4·10⁵` triples each annihilating with chance `2⁻¹³`, about 17 such coincidences are expected; this is sampling noise, not structure |
| c2, c3, c4 | **none of weight ≤ 4**; the only duplicate row pair is the forced `(plus-3, parity)` pair, which does not separate |

So the obstructions are dense, generic characters of an undersupplied
system, not short congruence patterns.

## 4. Forced by the family, or caused by the capped sample? (P5, P6)

The plan's central distinction has three tiers here:

1. **Structurally forced** (holds for every admissible prime of every cell,
   by proof): only `χ₃ + π` (Proposition 2). It is in the left kernel of all
   five pools and is never separating.
2. **Family-exhaustive** (true of the complete family pool, by complete
   enumeration + certificate): **c3**. Its 141-dimensional kernel and its
   obstruction are facts about the whole 1259/2735/j=3 family, because the
   pool *is* the family (`family_exhausted`, 1,198,144 draws). Cross-check:
   all 84 anchor primes that meet c3's declared bounds are present in the c3
   pool (P5), as completeness requires; its character has no further family
   members to be tested on (0 violations on 0 fresh members, by
   construction). "Family-exhaustive" is a statement about this one small
   family (225 primes against 365 blocks), established by enumeration; it is
   not a congruence law and does not transfer to the enclosing c4 family,
   where the same bounds on the plus side meet a wider minus base.
3. **Sample-dependent** (fails on unsampled members of the declared family):
   **c2 and c4**, demonstrated by transfer tests. Each recorded character,
   read as a Legendre functional on primes (which is coordinate-free and
   agrees with the group character on the cell's own group), was evaluated on
   certified primes of *other* pools that meet the cell's declared bounds:

| character | tested on | family members not in own pool | violations |
|---|---|---:|---:|
| c2 | anchor (all 483 anchor primes are in the 547/5470 family; 58 already in c2) | 425 | **215** |
| c4 | c3 (all 225 are c4-family; 29 already in c4) | 196 | **114** |
| c4 | anchor primes with all minus factors > 1259 (84; 8 already in c4) | 76 | **43** |
| c1 | — no other pool contains j=4 primes | 0 | untestable |

   Roughly half of the fresh family members violate each character, exactly
   as a random functional would. These GF(2) obstructions are therefore
   artifacts of the truncated samples, **not** constraints of the declared
   families.

**Union shadow probes (P6).** To ask whether the *family* (not the sample)
is binary-obstructed at the scale of the available certified primes, two
union pools were declared, each with its own block set and full-pool LCMs
(the plan's rule: adding primes changes the ambient coordinates, so the
group/target is rebuilt — here at the Legendre level, which needs no
discrete logs):

| declared pool | N | rows | rank | kernel | result (direct certificate) |
|---|---:|---:|---:|---:|---|
| c2 ∪ anchor (c2 family, 547/5470, j=3) | 678 | 602 | 601 | 1 = `⟨χ₃+π⟩` | **consistent**: a GF(2) solution vector is stored and re-checked |
| c4 ∪ c3 ∪ eligible anchor (c4 family, 1259/6295, j=3) | 626 | 756 | 626 | 130 | **obstructed**: separating Legendre character stored and re-checked |

The c2-family union is the first pool outside the anchor whose binary
system is consistent, and its left kernel is *exactly* the forced relation —
the same shape as the anchor. The c4-family union remains obstructed with
`N = 626 < 755` effective rows, consistent with undersupply rather than
with a family-specific congruence pattern (its characters are again dense).
A consistent mod-2 shadow is a *necessary* condition only: it is not
integer membership (that needs the full 2-primary system — quartic and
higher power-residue characters — and was not computed for the unions) and
not Boolean feasibility. The stored GF(2) solution vector is not a subset
solution of anything.

## 5. What this does and does not establish

- **Established (verified/certified):** Propositions 1–2 and their direct
  verification on every coordinate; the anchor's exact index 2 with
  `χ₃ + π` as the unique nontrivial character and the odd parts saturated;
  independent re-derivation of the real target's membership; the arithmetic
  reading of the four recorded characters; the sample-artifact status of the
  c2 and c4 obstructions; the family-exhaustive status of c3's; the
  consistency of the declared c2-family union pool and the obstruction of
  the declared c4-family union pool at the Legendre level.
- **Completed scopes (algorithmic, declared caps):** no separating character
  of weight ≤ 4 exists for c2, c3, c4; the verifier re-checks weights ≤ 2
  directly and accepts the weight-3/4 scope as a declared exhaustive search.
- **Not established / explicitly not claimed:** that any family's complete
  pool is integer-reachable or Boolean-feasible; any necessary-or-sufficient
  theorem in terms of `N` vs rows, nullity, or supply ratio (plan §4 forbids
  this and nothing here supports it — the heuristic `2^{−(rows−rank)}`
  account of §3 of the Track C report remains a heuristic); anything about
  selected-subset LCMs; any connection to a geometric mechanism (none was
  assumed and none is needed to explain these pools).
- **Unproved hypothesis (labelled):** the c1 (j=4) obstruction is likewise a
  sampling artifact; no other pool supplies j=4 family members, so it is
  untestable with existing artifacts. Its weight-3 character is consistent
  with chance at N = 13.

## 6. Deliverables requested by the plan: one screening rule and one falsifiable hypothesis

**Screening rule (justified by Proposition 1).** Before building discrete
logarithms for any candidate pool, run the Legendre pre-screen: for every
odd prime `ℓ` dividing some `p ± 1` form the row `[(p/ℓ) = −1]`, with target
`0` (minus side), `[ℓ ≡ 3 mod 4]` (plus side) and the all-ones parity row
with target 1, and test GF(2) consistency. This is *exactly* the pilot's
binary necessary check — not a heuristic — at cost `O(N·R)` modular
exponentiations, with no group construction. Two refinements follow from
Proposition 2: the effective binary row count is `R − 1` (the plus-3 row
duplicates parity), and any candidate separating character must contain an
odd number of sign-carrying rows (plus primes `≡ 3 mod 4`, or parity), so a
pool whose plus side contains no prime `≡ 3 (mod 4)` other than 3 can only be
mod-2 obstructed through parity-type characters. For S3 the pre-screen is
cheap enough to run on partial shards as the complete scan proceeds, with the
understanding that the row set grows with the pool, so consistency is not
monotone and only the final declared pool's result counts.

**Falsifiable hypothesis (for S3's complete c2 scan).** *The complete
547/5470/j=3 pool passes the Legendre pre-screen with GF(2) left kernel
exactly `⟨χ₃ + π⟩`.* It is motivated by the declared 678-prime union already
having that property and by the c2 family's expected supply (≈ 2,000 primes)
exceeding its maximum possible block count (620 minus + 99 plus + 1). It is
falsified if the completed pool (or the pool at the 4,096 cap, declared as
such) has a separating binary character; it is *not* a prediction of
integer membership, let alone Boolean feasibility, and passing it would
leave the Boolean problem exactly as open as it is for the anchor. A
companion negative prediction: the c4 family (1259/6295) will still fail the
pre-screen at the sample sizes S3 contemplates unless `N` clearly exceeds
`≈ 810` effective rows.

**One recommendation.** Treat the first-wave "GF(2) obstruction" rows of
c1/c2/c4 as supply measurements, not as family properties; adopt the
Legendre pre-screen as the standard necessary check for S3 shards; and do
not spend any solver budget on the sampled c2/c4 pools (their obstructions
are sampling artifacts, and their complete-family status is S3's question).
Nothing here authorizes the larger harvest or any search.

## 7. Handback checklist (plan §7)

- Branch `research/boolean-obstruction-analysis`, start `0c9f03f`; files
  added: the four S2-owned files only.
- Tests: `python -B -m unittest discover -s code -p "*correctness.py"` —
  the S2 suite adds 17 `unittest.TestCase` tests (tiny brute-force oracles
  for the GF(2), minimum-weight and primary-index machinery; falsified
  certificates rejected; saved report verified with Howell/Smith/kernel
  routines patched to raise); full repo suite 133/133 green on Python
  3.11.17 (68 s). `--verify` of the saved report: 5 cells, 4 characters
  re-checked, 5 + 2 shadow certificates, 5 transfer tests, 98 index
  certificates, 23 s. The final analysis run took 126 s wall (largest probe:
  c4's 2-primary index, 30.9 s under the 60 s watchdog).
- Dataset `bf_obstructions.json.gz`: schema `bf-obstructions/v1`, source
  SHA256s (LF-normalized) of the S2 module and the four baseline files it
  imports, both input SHA256s, interpreter, declared budgets and probe list,
  per-cell outcomes with timings, the anchor's full index certificates (98
  primary parts), the union pools' prime lists and certificates, transfer
  counts. Verify with `--verify` (never runs the elimination code).
- Budgets: 60 s watchdog per probe, never raised; zero `timeout_enforced`,
  zero `worker_error`; no new harvesting; no solver run.
- **Shared defect report for the coordinator (not fixed here; shared file):**
  `fs_controls.run_limited` joins the worker *before* draining its result
  queue, so a worker whose result pickles to more than the OS pipe buffer
  (≈ 64 KiB) blocks on the queue's feeder write while the parent waits in
  `join`, and is then killed at the deadline and reported as a spurious
  `timeout`. Minimal reproduction: `run_limited(lambda p: [0] * 200000, None,
  60.0)` (module-level callable) returns `("timeout", None, 60.0)` although
  the work takes milliseconds. Track A's results were small enough not to
  trigger it. S2's index workers therefore write their certificates to a
  temporary file and return only a short summary through the queue
  (`_index_limited`); the first S2 run, before this workaround, recorded four
  spurious `timeout_enforced` outcomes for computations that take 6–50 s
  in-process, and was discarded. Suggested shared fix: read the queue with
  `get(timeout=seconds)` before `join`, or use a file-backed result.
- Shared-interface note (no action required): the first-wave
  `necessary_checks` stores one arbitrary separating character from GF(2)
  elimination; a Legendre-labelled form (block prime and side per term)
  would make future certificates self-describing. Not a defect.
- Pushed: branch only, when authorized; no PR opened.
