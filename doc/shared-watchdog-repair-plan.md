# Shared watchdog repair: large-result delivery and frozen provenance

**Original planning status (2026-10-29):** no runtime repair or regression run yet.
The user selected repairing the existing API with strict historical-source
compatibility, rather than leaving the old helper defective behind a new API.
This plan does not authorize a solver pilot, harvest, replication or budget increase.
The subsequent [implementation record](#9-implementation-record-2026-10-30)
reports execution of the approved engineering work, separately from this plan.
The repair is now merged through
[PR #14](https://github.com/shumow/PRIMES-Conjectures/pull/14). See the
[accepted post-merge follow-ups](#10-accepted-post-merge-review-follow-ups)
for the current documentation, diagnostics and research-planning gates.

**Starting main:** `e6b756c20365ea40245aaa6734f9f3044ac791ed`, after
[PR #11](https://github.com/shumow/PRIMES-Conjectures/pull/11) and
[PR #12](https://github.com/shumow/PRIMES-Conjectures/pull/12).
The study and coordinator documentation are already on main; do not repeat that landing.

## 1. Verified problem and constraints

At the starting baseline,
[`fs_controls.run_limited`](https://github.com/shumow/PRIMES-Conjectures/blob/e6b756c20365ea40245aaa6734f9f3044ac791ed/code/fs_controls.py#L80) called
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
would still fail [S1's original control-input source check](https://github.com/shumow/PRIMES-Conjectures/blob/e6b756c20365ea40245aaa6734f9f3044ac791ed/code/bf_solver.py#L406).
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

Original planning evidence consists of source inspection, existing S2/S3 defect reports
and workaround tests, and metadata/hash reads. At that planning stage, the
new reproduction, repair and mathematical verification had not been executed,
and no new experiment had been performed.

## 9. Implementation record (2026-10-30)

This is the pre-publication implementation snapshot. Section 10 records the
later independent review and main merge; its remaining-gate text below is
historical, not an instruction to repeat that landing.

The approved plan was pushed and normally merged through
[PR #13](https://github.com/shumow/PRIMES-Conjectures/pull/13), producing main
`08e2417670b61f316b368b2ff3df91a056ad86a0`. Implementation is isolated on
`fix/watchdog-large-result` descended from that main commit. The repair itself
has not been pushed or merged at this record.

### Observed red regression

The direct 4 MiB return failed on the original helper on both Windows runtimes:
the completion marker existed, but `kind` was `timeout` after 30.049 seconds
(Python 3.14) and 30.078 seconds (Python 3.9). This distinguishes the completed
callback/blocked delivery from a slow callback or failed startup.
The independent subprocess ceiling was 60 seconds; these were synthetic unit
fixtures, not solver-control calls.

### Implemented changes

- The canonical helper keeps its signature and three-kind tuple contract,
  but writes a complete trusted-worker envelope to a private per-call file.
  It no longer creates a result queue. Atomic publication, exit checks,
  serialization errors, deadline classification and bounded terminate/kill
  cleanup are covered; interrupts propagate and cleanup errors remain visible.
- The [source-version helper](../code/watchdog_source_versions.py) accepts
  complete actual-current or explicitly cataloged historical manifests for
  the four schema/context pairs in section 3. Missing/extra/unknown hashes,
  wrong schemas and mixed versions are rejected.
- Both S1's input-control check and its three report checks use that recognition.
  Current producers include the helper's actual source digest. All mathematical,
  input/protocol, gating, budget and candidate checks remain in place; library
  return dictionaries and CLI JSON contracts are unchanged.
- S2/S3's source-hashed workaround modules, every original report and every
  recorded historical outcome remain unchanged. Successful source recognition
  does not authenticate historical timings or substitute for mathematical proof.

### Validation

| Validation | Windows Python 3.14.5 | Windows Python 3.9.13 |
|---|---:|---:|
| Focused transport/source-version tests | 20 passed, 0 skips | 20 passed, 0 skips |
| Complete suite, including existing CP-SAT 9.15.6755 | 274 passed, 0 skips | 274 passed, 0 skips |

The combined suite took 442.783 seconds and 439.990 seconds respectively
(unittest timings). Both validation runs rechecked the ten raw artifact hashes
in section 8 and verified unchanged repair source/test snapshots before/after.
They include the existing producer-disabled saved-report and tamper regressions.
Those source-snapshot receipts and logs are local execution audit records,
not checked-in repository evidence. The test sources/commands and subsequent
independent review are the repository-visible reproduction route.

The new tests exercise exact type/length/bytes for the multi-MiB return, nested
dataclass/enum/large-integer values, large error messages, unpickleable results,
startup/output/read errors, abrupt/missing/corrupt results, publish-then-linger,
timeouts and subsequent calls, late decoding, invalid allowances, interruption,
cleanup failures and bounded kill fallback. Owned process handles and temporary
paths are checked. Expected child stderr from a deliberate write failure is
not counted as a test failure.

POSIX was not exercised here. Pylance syntax requests timed out; the successful
runtime suites on both interpreters provide parsing/execution evidence, not a
claim that editor diagnostics passed. No dependency was added and no production
pilot, harvest, full-pool control or real-target search was run.

**Remaining gate at this snapshot:** independent review of transport lifecycle and complete
source-version acceptance, followed by explicit publication/merge authorization.
No new research experiment or renewed allowance follows from these tests.

## 10. Accepted post-merge review follow-ups

**Review and landing are complete.** The
[fresh-context review](https://github.com/shumow/PRIMES-Conjectures/pull/14#pullrequestreview-5730974881)
approved head `36784c289c21d36b08e007a9e557cc9da0ef2bf3`. The normal merge
`b2d5042f8f6b830f36933b49c9c96be4d9e0d0cc` has parents `08e2417` and
`36784c2` and preserves reviewed tree `f81c0a810c1280380a93792eb4396c6efdb7593f`.
The [post-merge comment](https://github.com/shumow/PRIMES-Conjectures/pull/14#issuecomment-6566145113)
restates the nonblocking follow-ups. All four review observations are accepted;
the diagnostics addition is a separate code change, not a docs-only correction.

### Independent POSIX evidence

The reviewer reran the direct 4 MiB return on macOS, with this old/new result:

| Python | Original helper at `08e2417` | Reviewed repair at `36784c2` |
|---|---|---|
| 3.9.6 | timeout, 30.008 seconds | `ok`, 4,194,304 bytes, 0.062 seconds |
| 3.13.14 | timeout, 30.008 seconds | `ok`, 4,194,304 bytes, 0.133 seconds |

Both interpreters passed the 20 focused regressions. Each combined run
discovered 274 tests, with 271 passing and three optional native OR-Tools tests
skipped (89.6 and 64.4 seconds respectively). The original Windows runs cover
those native tests. The reviewer independently checked the full frozen source
catalog against pinned Git objects and confirmed unchanged data and merge tree.
This closes the missing POSIX review coverage; it is not Linux/WSL coverage or
a fresh run by this planning update.

### A. Documentation closeout

**Execution status (2026-11-02):** completed on `work/post-watchdog-followups`.
The README/onboarding now distinguish the merged 274-test baseline from its
historical 254-test study, cite independent POSIX/native-skip evidence, mark the
repair landing complete and explain the timing and local-receipt limitations.
No tests or experiments were rerun for that documentation-only change.

Update the current [README test summary](../README.md#running-the-audit-checks)
and [agent onboarding](../AGENTS.md#2-current-state-what-is-done) to identify
the current 274-test suite (254 previous tests plus 20 watchdog/source-version
tests). Mark the agent coordinator gate as completed and point to the separately
bounded research proposal, with the diagnostics follow-up identified explicitly.
Do not globally replace the historical 254-test study-validation record.

Record macOS/POSIX and Windows evidence separately, including native-test skips.
Keep the original lack-of-POSIX statement in section 9 as a dated implementation
snapshot; do not claim that Windows validation itself covered POSIX.

Clarify the public watchdog semantics in current guidance:

- `elapsed` includes result transfer and cleanup, not only callback time.
- A worker result finishing parent-side handling after the deadline is returned
  as `timeout`, never counted as a late successful call.
- S1 already guards late results independently. Do not remove those guards,
  extend a budget, or retrospectively reinterpret recorded timings.
- Parent deserialization/OS I/O and memory are not independently hard-capped;
  cleanup overhead can exceed the deadline and remains visible.

These are documentation corrections to existing behavior, not another transport
redesign. Link the reviewed commit, commands and review permalink instead of
claiming that the seven-file validation receipts are in the repository.
Do not add routine local logs or secrets merely to make the earlier receipt
claim appear independently reproducible.

### B. Expose the matched producer source version

**Execution status (2026-11-02):** completed and tested on
`work/post-watchdog-followups`; see [section 11](#11-source-version-diagnostics-follow-up-2026-11-02).
The following requirements remain the acceptance contract, not unfinished
instructions to implement the same change again.

The [catalog helper](../code/watchdog_source_versions.py) returns `current` or
`frozen-2026-10-study`, but its four S1 call sites discard that value. Add
`source_version` to the **verification summary** of all three S1 modules,
including their JSON `--verify` output. Preserve existing summary values and
signatures; update exact-summary consumers/tests deliberately for the additive
field. The label must come from the already enforced complete report-manifest
match, not a guess based on schema, filename or the controls input.

The controls input has its own manifest check. If its matched version is also
exposed, label it separately; do not conflate an archived controls input with
the producer of the report being verified. Keep diagnostic metadata outside
the source-hashed saved report and its input-provenance dictionary so that
the frozen input/scope checks and archived bytes remain unchanged.

Required checks before landing this separate change:

1. All three archived S1 summaries and CLI paths identify
   `frozen-2026-10-study`; synthetic in-memory fixtures with complete
   actual-current manifests identify `current`. Such fixtures are test data,
   not evidence of a newly executed historical pilot.
2. Unknown, mixed, missing/extra or wrong-schema source maps still fail;
   recognized sources plus a false witness, protocol, input or status still
   fail. Retain the independent producer-disabled checks.
3. Future source manifests still hash the actual modified verifier/helper
   bytes. Do not add intermediate historical versions without a real preserved
   artifact requiring them, accept hashes piecemeal, or relax the catalog.
4. Existing summary fields, all protocol/input checks and the ten artifact
   hashes in section 8 remain intact. No report is regenerated or relabeled.
5. Run the affected library/CLI/provenance regressions on Python 3.9 and a
   current supported runtime. Expand the test selector only if a concrete
   failure shows another affected surface; no full-pool experiment is needed.

### C. Evidence and release boundary

The private validation receipts show what the implementation session measured,
but cannot serve as independently checkable repository evidence on their own.
The committed tests, pinned implementation, reproduction commands and linked
independent review are the public evidence for this landing. New claims must
name the commit, interpreter/platform, selector and any skips; do not imply
that uncommitted receipts are available to a reader.

Complete A as a documentation-only change and B as its own tested code change,
then obtain the normal authorized review/landing for each. The original
planning update did neither automatically; their execution is recorded above
and in section 11. The reviewer found no blocking correctness issue
and the merged transport need not be reimplemented or remerged.

After these small engineering closeouts, the next scientific deliverable is
the bounded research proposal described in the current [root plan](../PLAN.md).
It must justify an approach beyond the cap-17 calibration, respect the real
93-/191-factor requirements, declare fresh validation cases and aggregate
budgets, and receive explicit approval before execution. The existing 30 S1
full-pool calls, observed holdouts and completed S3 scan remain historical.

## 11. Source-version diagnostics follow-up (2026-11-02)

The approved reviewer-correction plan `b032524` was published on
`docs/watchdog-review-followups`. Documentation closeout was completed separately
at `422a6e2`. This code follow-up is isolated on `work/post-watchdog-followups`;
no new main merge or experimental execution is part of it.

All three S1 `verify_report` functions retain the string returned by their
existing complete-report-manifest check and add it as `source_version` to the
verification summary. Their existing CLI paths serialize the same summary,
so `--verify` exposes the field without new flags or separate logic:

- `current`: the report's complete producer manifest matches actual current
  source bytes, including the source-version helper.
- `frozen-2026-10-study`: the complete manifest matches the explicitly approved
  historical producer version, not the current filesystem.

The label is not derived from the controls input. A current-manifest test
fixture can correctly report `current` while using archived controls. No
version key is written into an archived report or its input dictionary.
The catalog, accepted source versions, protocol, solver parameters, mathematical
checks and all pre-existing summary values are unchanged. This is a deliberate
additive output-contract change; the two exact-summary tests were updated.

The new regression first reproduced the absent field as `KeyError` for all
three archived S1 summaries. After the change:

| Affected validation | Windows Python 3.14.5 | Windows Python 3.9.13 |
|---|---:|---:|
| S1 model/runner/checker/CLI tests plus source-version catalog tests | 102 passed, 0 skips | 102 passed, 0 skips |
| Runtime | 178.361 seconds | 229.125 seconds |

Both use the existing optional CP-SAT 9.15.6755 environment. The tests include
all three actual archived reports through library and CLI verification,
explicitly synthetic current-manifest copies, unchanged old summary values,
rejected bad sources/inputs/protocols/candidates/status claims, and unmodified
report/input dictionaries. Search, worker, model and certificate producers are
patched to fail in the new diagnostic report tests. Synthetic current-manifest
copies are test fixtures, not claims that a new pilot was run.

The affected-suite command selects the existing S1 modules, the new diagnostics
module and the unchanged catalog tests in one runner. The successful run did
not require escalation to a new full-suite run. This follow-up adds four tests;
the 274-test full Windows/POSIX results above remain evidence for the earlier
merged repair, not a claim of a new complete run after this change.

All ten raw artifact hashes were checked before/after each run. The validation
receipts pin the six changed code/test files, remain local audit records and
are not repository artifacts. Committed tests and the implementation are the
reproduction route. No new dependency, native search configuration, pilot,
harvest or full-pool control was introduced. New diagnostic code has not been
independently exercised on POSIX here; the earlier review covers the earlier
repair only.
