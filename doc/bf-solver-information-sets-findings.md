# S1 next step: support-blind information-set search

**Branch:** `research/boolean-solver-calibration`

**Starting combined S1/study commit:** `6c954e9c5da7d8b71ba1d5eaea60522d0775fbf8`

**Status:** prototype and correctness tests only. No full-pool control
outcome has been inspected for this configuration.

S2 and S3's reviewed revisions are now on the study integration branch and
have been merged into S1 without altering either earlier S1 source-hashed
implementation or artifact. This versioned module avoids invalidating those
reports. No new optional backend or dependency is introduced.

## Algorithm and scope

The public worker receives a problem with `exact_size=None`. The support,
planting indices, seed labels and prime records stay in the parent. The
algorithm has its own fixed selection envelope: **odd size at least the
minimum and at most 17**. This is not a claim of complete general solving.

For each of at most eight information sets:

1. Permute the Boolean columns (identity first, then seven fixed-seed
   shuffles independent of the planting streams).
2. Apply the audited GF(2) solver to the parity projection of every original
   even-order component, together with odd cardinality.
3. Enumerate the particular solution XOR combinations of at most three
   free-coordinate kernel basis masks.
4. Use the exact resulting selection mask to enforce the size envelope,
   map back to original prime indices, and check **every original modular
   equation**. Independently check returned subsets and prime residues.

The XOR operations update the selection vector exactly. They do **not**
assume that full-group residuals are additive under overlapping moves.
Higher 2-power carries and odd-primary equations are never dropped from
candidate acceptance.

For the pilot's nullity 90, a full information set has
`1 + 90 + C(90,2) + C(90,3) = 121,576` states. Eight sets have at most
972,608 states. A sparse planted selection may occupy few free coordinates
in one set; that motivates the method, but is not a recovery guarantee.

## Predeclared candidate pilot

One configuration: one worker; 60 seconds per call including startup,
projection, elimination, enumeration and checking; 512 MiB completed-worker
memory target (not an OS cap); eight information sets; free-coordinate
weight at most three; one million states; at most 10,000 full-target
candidate checks; fixed solver seed 1729.

The prototype declares an **18-call maximum**, with gates:

| Phase | Parent-known controls (not worker hints) | Calls |
|---|---|---:|
| 0 | Support 3, development 101/202/303 | 3 |
| 1 | Support 5, development 101/202/303 and fresh holdouts 32452843/49979687/67867967 | 6 |
| 2 | Support 9, development 101/202/303 | 3 |
| 3 | Support 17, development 101/202/303 and fresh holdouts 86028121/104395301/122949829 | 6 |

All cases of each prior phase must solve before a later phase runs.
The six holdout seeds differ from all previously evaluated holdouts.
Development controls reuse frozen first-wave targets; holdouts use the
existing `bf-solver-holdout/20261024/<seed>` namespace with these new seeds.
No witness is supplied as a hint or warm start.

The aggregate solver-call ceiling is 1,080 seconds, not a larger per-call
budget. No real target, larger pool, harvest, parameter sweep or adaptive
retry is authorized by this prototype. Failure is inconclusive outside the
explored affine masks and selection envelope.

Before any full-pool pilot, finish the runner/report verification, freeze
the source and protocol in a commit, and check it against independent small
oracles. The declaration above is not a claim that the pilot has run.

## Prototype validation

- All **18 focused tests** pass on Python 3.14.5 and 3.9.13 (0.977 and
  1.191 seconds).
- The combined **233-test suite** passes on both runtimes, including the
  integrated S2/S3 regressions and the prior optional-backend tests.
- Independent tests compare 300 small binary affine families and 1,184
  small subset decisions with exhaustive enumeration. Additional structured
  fixtures recover different synthetic supports without supplying their
  cardinality to the worker.
- Tests cover exact overlapping XOR masks, retained odd/higher-power
  equations, state/selection/deadline limitations, fresh-holdout separation,
  worker payload isolation, explicit errors and an actual tiny spawned run.
- Every earlier S1 source-hashed implementation and artifact is unchanged.
  No full-483 control, real-target search, membership run or harvest was
  executed while developing this prototype.

Print the declared candidate protocol without running a study:

```powershell
python -B code\bf_solver_information_sets.py --protocol
python -B -m unittest discover -s code -p "test_bf_solver_information_sets_correctness.py" -v
```

The CLI deliberately refuses a default production invocation. The next step
is the committed runner/report contract and its independent-verifier tests,
not an unrecorded one-off full-pool trial.
