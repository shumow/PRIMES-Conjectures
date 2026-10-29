# Shared watchdog repair: large-result delivery and frozen provenance

**Status:** implementation plan only; no runtime repair or regression run yet.
The user selected repairing the existing API with strict historical-source
compatibility, rather than leaving the old helper defective behind a new API.
This plan does not authorize a solver pilot, harvest, replication or budget increase.

**Starting main:** `e6b756c20365ea40245aaa6734f9f3044ac791ed`, after
[PR #11](https://github.com/shumow/PRIMES-Conjectures/pull/11) and
[PR #12](https://github.com/shumow/PRIMES-Conjectures/pull/12).
The study and coordinator documentation are already on main; do not repeat that landing.

## 1. Verified problem and constraints

[`fs_controls.run_limited`](../code/fs_controls.py#L80) currently calls
`process.join(seconds)` before `out_queue.get(timeout=5)`. A child returning
a sufficiently large value can block while its queue feeder flushes the pipe;
the parent waits for that child to exit without reading the pipe. Completed
work is then reported as a timeout. The later five-second read cannot prevent
this cycle. The timeout branch also bypasses the normal queue close.

Existing tests cover small results, a worker exception and an enforced timeout,
but not a large value returned directly through this public helper.
The [S3 large-result test](../code/test_bf_harvest_correctness.py#L247)
tests a file-backed *workaround*, not the broken generic return path.

Prior art to retain:

- [S2 index-certificate handoff](../code/bf_obstructions.py#L740):
  the worker writes the certificate and returns a small summary.
- [S3 membership handoff](../code/bf_harvest.py#L573):
  the same pattern avoids the recorded roughly 440 KB certificate deadlock.
- [S3 known-source versions](../code/bf_harvest.py#L332):
  explicit historical implementation recognition already exists. The repair
  below must use complete source manifests for S1, not arbitrary hash exceptions.

The public contract remains `run_limited(fn, payload, seconds)` returning
`(kind, value, elapsed)`, where `kind` is `ok`, `timeout` or `worker_error`.
Keep one spawned worker, Windows support, Python 3.9+ and standard-library-only
operation. No retries, extra solve calls, hidden budget extension or OS-enforced
RSS claim belongs in this repair.

## 2. Recommended transport: a parent-owned file, not a result queue

Repair the existing function and its private worker entry in place.
Use a fresh parent-owned temporary directory per call and a fixed result path.
Use standard-library pickle for the existing Python-object return contract;
JSON alone would not preserve dataclasses, enums and other existing return types.
Only load a file created by this invocation's trusted worker, never an arbitrary
external pickle or a worker-supplied path.

1. Validate the time allowance before allocating resources or starting work.
   Accept finite nonnegative `int`/`float` values excluding booleans, reject
   invalid/negative/nonfinite values explicitly, and return a zero-budget
   timeout without starting a worker.
2. Start a monotonic deadline before setup/startup. Deduct elapsed startup
   from the remaining worker wait rather than granting another full interval.
3. The module-level spawned entry executes `fn(payload)` once and writes a
   complete `(kind, value)` envelope to a temporary file. Close it before an
   atomic replacement of the designated completed-result path.
4. Ordinary worker exceptions retain a useful exception type/message as
   `worker_error`. A result-serialization failure must itself produce a
   classified error when possible; it must not become a missing-result timeout.
5. The parent supervises process completion until the deadline, without a
   result queue or a blocking receive of a partially transmitted pickle.
   Publishing a file is not enough: the worker must also finish successfully.
6. On expiry, terminate, reap and, if necessary, kill only this call's worker.
   Bound cleanup waits; replace the current unbounded post-kill join.
   Never decode a timed-out worker's partial output as a successful result.
7. After a successful exit, read and validate the completed envelope.
   Missing/corrupt output, unexpected tags, nonzero exits, startup failures and
   file I/O failures must surface explicitly, not as `ok` or mathematical negatives.
8. Reap/close the process and remove owned temporary files on every path,
   including interruption. Cleanup failures must be visible and must not mask
   the original failure or falsely claim clean success.

`elapsed` must measure the whole call, including transfer and cleanup.
Accept no result whose parent-side handling finishes after its deadline.
Cleanup can overrun a deadline and that overrun must be reported honestly.
The worker watchdog does not make arbitrary parent deserialization, OS I/O or
memory consumption independently hard-capped; do not document such a guarantee.

This avoids both the known feeder deadlock and a simplistic queue-read fix
whose timeout covers initial readability but not a subsequent incomplete frame.
It also avoids introducing a receiver thread with another lifecycle to manage.

## 3. Provenance migration is part of the fix

An in-place edit changes the LF-normalized digest of `fs_controls.py` from:

```text
8a5d440a03ce9a37693288dccdd3213240b77633c5b1d6bfd26dd7707515cf4d
```

Four frozen source manifests include that exact file:

| Record | Manifest entries | Existing coupling |
|---|---:|---|
| [First-wave controls](../data/generated/fs_controls.json.gz), `fs-controls/v1.1` | 7 | S1 checks this input's sources in `_context`. |
| [S1 Round 1](../data/generated/bf_solver.json.gz), `bf-solver/v1` | 8 | `verify_report` requires equality with live `_sources()`. |
| [S1 Round 2](../data/generated/bf_solver_preprocessing.json.gz), `bf-solver-preprocessing/v1` | 9 | Inherits Round 1's sources and checks the whole map. |
| [S1 Round 3](../data/generated/bf_solver_information_sets.json.gz), `bf-solver-information-sets/v1` | 10 | Inherits the prior maps and checks the whole map. |

**Both layers must be handled:** changing only the three saved-report checks
would still fail [S1's control-input source check](../code/bf_solver.py#L406).
Changing those verifier files also changes their own producer-source hashes.
Do not fix this by rewriting archived JSON, skipping `fs_controls.py`, accepting
individual old-or-new hashes, or replacing actual source digests with old literals.

### Strict source-version design

Add one small, verifier-focused source-version helper, provisionally
`code/watchdog_source_versions.py`:

- Extract the four full historical source maps from the pinned baseline above,
  verify their entries against its source bytes, then check in explicit,
  reviewed schema-specific manifests. Do not learn allowed hashes from the
  report currently being verified.
- Accept either the complete actual-current manifest or the complete approved
  historical manifest for that schema/context, with CRLF-to-LF normalization.
  Reject unknown maps, missing/extra entries, mixed versions, wrong-schema
  catalogs and altered hashes. No per-file fallback or broad exception handling.
- Retain all existing implementation/protocol/input/scope, case-gating,
  candidate and mathematical checks. A recognized source map is not evidence
  that a claimed historical execution or timing is authentic.
- Apply this validation to S1's control-input provenance and all three S1
  saved-report source checks. Keep verification independent of workers,
  solvers, carry builders, affine producers and certificate generators.
- Future producers must record their **actual modified code**, including this
  helper wherever used. Extend Round 1's source collection; Round 2/3 must
  inherit it. Do not hardcode a mutable current-code hash into its own catalog.
- Distinguish frozen-producer recognition from a current-filesystem match in
  documentation/diagnostics. Preserve existing library return shapes and CLI
  JSON contracts unless an explicit, separately reviewed version change is needed.

The independent arithmetic checks still run for every accepted report.
Do not substitute a raw artifact-hash allowlist for mathematical verification.
All artifact bytes, recorded source maps, historical outcomes and old protocol
hashes stay unchanged.

## 4. Caller and file scope

| Surface | Required work |
|---|---|
| [`fs_controls.py`](../code/fs_controls.py) | Repair `run_limited` and its private worker; retain the public API and solver/budget logic. |
| [`bf_solver.py`](../code/bf_solver.py) | Update source collection and the two provenance layers; do not change the model, controls or parameters. |
| [`bf_solver_preprocessing.py`](../code/bf_solver_preprocessing.py) | Recognize the complete frozen source version; keep exact-k filtering and arithmetic gates unchanged. |
| [`bf_solver_information_sets.py`](../code/bf_solver_information_sets.py) | Same provenance treatment; preserve the algorithm, blind interface, limits and case protocol. |
| [`bf_obstructions.py`](../code/bf_obstructions.py), [`bf_harvest.py`](../code/bf_harvest.py) | Exercise their existing call paths without refactoring away their file-backed workarounds or changing frozen modules unnecessarily. |
| Tests | Add `test_watchdog_transport_correctness.py` and `test_watchdog_source_versions_correctness.py`; retain existing watchdog and report-tampering tests. |
| Documentation | Update the current defect/workaround guidance after implementation; describe legacy provenance and the new transport accurately. |

Call routing to verify includes direct imports in S1/S2, S1 Round 2/3's
`baseline.run_limited` aliases, S3's qualified call and the first-wave runner.
Preserve the existing monkeypatch points used by tests.
Do not touch the mathematical baseline modules or old schemas merely to
silence provenance failures.

## 5. Implementation order and gates

1. **Baseline ledger:** record all ten artifact hashes in section 8 and
   current source maps. Confirm a clean branch from current main containing
   this plan. No production command is needed.
2. **Red regression:** reproduce the generic large-return defect before
   changing transport. A module-level fixture creates at least 4 MiB of
   deterministic data, writes a completion marker, then returns that data.
   The test expects exact successful delivery. Demonstrate that the old helper
   times out despite the marker proving the callback completed.
3. **Coupled repair:** implement the file-backed transport and strict provenance
   compatibility together. Do not publish a watchdog-only intermediate state
   that makes the existing frozen-report suite fail.
4. **Focused validation:** pass the transport/source-version matrix below,
   including old tamper tests and producer-disabled archived verification.
5. **Integration and review:** run the complete affected suite on Python 3.9
   and 3.14, inspect the final artifact/source ledger, and obtain independent
   review of transport lifecycle and provenance recognition before landing.

If the red regression does not reproduce, investigate its fixture/startup
evidence before claiming success. Do not assume a universal 64 KiB pipe size.
Use a fixed generous functional-test allowance (for example 30 seconds),
an independent outer harness ceiling (for example 60 seconds), and teardown
for every owned process. Do not supervise the watchdog using itself.
These are synthetic IPC tests, not new full-pool control calls or timing claims.

## 6. Required acceptance matrix

| Case | Required result |
|---|---|
| Small value and `None` | Exact payload, `ok`, finite measured elapsed. |
| Direct multi-MiB return | Exact type, length and byte-for-byte value; no spurious timeout. |
| Certificate-shaped nested values | Preserve integer sizes, containers and representative dataclass/enum types. |
| Ordinary and large-message worker exceptions | `worker_error` with useful original detail; never timeout or infeasibility. |
| Unpickleable return / output write failure | Explicit delivery/serialization error, no missing-result success. |
| Abrupt/nonzero worker exit, no result | Prompt `worker_error` with exit context. |
| Missing, truncated or malformed envelope | Explicit error, no indefinite read or `ok`. |
| Real timeout; publish-then-linger / late completion | Reap the worker and return timeout; accept no late value. |
| Zero / invalid allowances | No work for zero; explicit validation errors before spawn for invalid inputs. |
| Success, error, timeout, interruption | No live owned worker, open process handle or leftover temporary directory. |
| Repeated calls and the call after a timeout | No stale payload, leaked state, helper thread or cross-call path collision. |
| Known legacy and actual-current manifests | Both supported through their explicit complete versions. |
| Unknown, mixed, missing, extra or wrong-schema source entries | Rejected, even when candidate mathematics would otherwise pass. |
| Valid source map plus false witness/status/input/protocol | Rejected by the unchanged independent checks. |
| All archived reports | Existing read-only verification passes; every byte hash remains unchanged. |

Keep the large-return test distinct from S3's existing tiny-summary/file test.
Prove cleanup with owned process/temporary-path observations, not only a
reported `kind` or the absence of an exception. Exercise real Windows spawn
and POSIX where available; do not claim a platform was tested if it was not.

## 7. Validation and release boundary

First use one focused discovery command for the two new test modules:

```powershell
python -B -m unittest discover -s code -p "test_watchdog_*correctness.py" -v
```

Then run the existing combined suite once on each supported validation
interpreter after the focused tests pass:

```powershell
python -B -m unittest discover -s code -p "*correctness.py" -v
```

The baseline is 254 tests before adding the regressions; report the actual new
count. Native CP-SAT tests may use the already approved isolated dependency.
If absent, report the three optional skips rather than claiming native coverage.
Use real test modules/launchers for spawn, not stdin-based worker execution.

Recheck the three S1 artifacts with search/worker/certificate producers patched
to raise, plus existing pilot, first-wave and S2/S3 verification. Preserve the
full S3 membership sidecar and its directly checked certificate. Compare the
ten raw hashes below before/after; do not regenerate any report to make tests pass.

Land one coherent, tested infrastructure/provenance change with its tests and
documentation through an authorized review PR. Recheck live base/head and
review the complete source-version acceptance policy. No automatic push,
merge, research run, budget renewal or retrospective reclassification of
historical timeouts follows from this planning document.

Only after this gate is complete should the separate bounded research proposal
address the cap-17 versus real 93-/191-factor gap. All 30 S1 full-pool calls
remain historical, and their observed holdouts do not become fresh again.

## 8. Immutable artifact ledger at the planning baseline

These are raw file SHA256 values, not normalized-code hashes:

| Artifact under `data/generated/` | SHA256 |
|---|---|
| `real_pool_pilot.json.gz` | `008cf08ce3f0d3a2f987bff26d5abd04bf4c41050f949ae0fdc4f4192b6969de` |
| `fs_controls.json.gz` | `ad3c7cc4b909b174e8e19b279324d7e9856d3d0b232b913dff458f8fd8aa3b21` |
| `fs_reachability.json.gz` | `5cb53396e98cc6a387a0db7a63183daef2706f9df16810df309efb0c4ee88ad3` |
| `fs_harvest.json.gz` | `75f1599b05a84f0c8e7f24fa349de1628ea2811a58cb4558c84bbc02a0410bad` |
| `bf_obstructions.json.gz` | `db7879921b60613b5218ec2374573416e09789298134032bb9b735e903995436` |
| `bf_harvest.json.gz` | `f2670b133827d302a85bc0813348d7f76ce548fd39f27f5f1632b3c51f9322a5` |
| `bf_harvest_membership.json` | `007f83dd0e6b34d79dc9f95302be65a4d7bc1e297cbd5335b1d3ddda22459415` |
| `bf_solver.json.gz` | `67b7dd568c925432546d8f43373cab4a8e638abe79fa3802873202243dd5b9a5` |
| `bf_solver_preprocessing.json.gz` | `d100e499dfa7c6b3ae5b2cac7ff67e00ed46dea08e6078693cf0671fdfbb2e1a` |
| `bf_solver_information_sets.json.gz` | `d62ac9ba58789262180a71589eb0c3ae9e7e42c0272e1e1a8f2dfbb5d8c149e7` |

Planning evidence consists of source inspection, existing S2/S3 defect reports
and workaround tests, and metadata/hash reads. This plan has not executed the
new reproduction, implemented the repair, rerun mathematical verification or
performed a new experiment.
