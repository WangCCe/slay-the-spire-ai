# Card-Acceptance Empirical Successor Source Qualification - 2026-08-10

## Focused Pytest

- OpenSpec task: `5.1`
- Source commit: `3665db89c583c7a9166e6d0cb1fba027749c78f5`
- Interpreter: `D:\anaconda\envs\stsai\python.exe`
- Pytest temp root: `%TEMP%\codex-pytest-stsai\successor-5_1-20260810`
- Result: `373 passed, 5 skipped in 244.44s (0:04:04)`
- Invocation count: one; the suite was not retried or split for timing.

The focused suite covered the successor control plane, Torch runtime, seed
inventory, and independent verifier together with the card-acceptance policy
and objective, state-conditioned input/ranker, formal reward, simulator adapter,
and hierarchical advantage-attribution contracts.

The five skips are the simulator-adapter integration cases that require the
explicit `STS_LIGHTSPEED_ADAPTER_MODULE`, `STS_LIGHTSPEED_ROOT`, and
`STS_LIGHTSPEED_MINGW_BIN` native configuration. Leaving those variables absent
is intentional for this source-only qualification. No cohort was materialized,
no seed was discovered or accessed, no native simulator or production model was
loaded, and neither Slay the Spire nor CommunicationMod was started.

The slowest nodes were the paired chunk update at `22.43s`, independent
checkpoint reconstruction at `17.32s`, frozen-state mutation rejection at
`12.72s`, and fresh-process deterministic advantage rendering at `12.31s`.
The approximately four-minute focused boundary is appropriate for source
qualification, but it is not the default per-edit feedback loop. The configured
commit and full gates remain deferred to task `5.5` and will each run once at
their reviewed boundary.

## Fresh-Process Isolation And Publication

- OpenSpec task: `5.2`
- First process: three import/CLI isolation probes, deterministic float64 gzip
  encoding, and terminal publication plus independent reconstruction;
  `5 passed in 1.84s`.
- Second process: the same terminal publication fixture plus independent
  reconstruction; `1 passed in 0.49s`.
- Managed publication inventory: six files in each process, byte-identical.
- Managed inventory SHA-256 in both processes:
  `865dfa321f78481b566475d1af94413732d55cddafcf1d5ab0d984242c644a1a`.

The import probes used isolated `-I` child interpreters and rejected Torch,
native adapter, successor runtime/seed inventory, and consumed-runner imports at
the control/verifier boundaries. The contract CLI produced canonical identical
bytes twice in fresh child processes.

The complete temporary execution directories differed only in
`.execution.lease.owner.token`. That control file intentionally has one unique
lease-acquisition token per process and is excluded from the managed artifact
manifest. All six managed files (`access_journal.jsonl`,
`resource_ledger.jsonl`, `evidence/summary.json`, `terminal_intent.json`,
`terminal.json`, and `artifact_manifest.json`) had identical relative paths,
sizes, and file SHA-256 values across the two processes. The initial sandboxed
read of the pytest temp roots was denied; the tests were not rerun, and one
exact-path elevated read-only comparison completed the check.

No cohort, seed, native simulator, production model, gameplay process, or
CommunicationMod process was accessed during this qualification.

## Consumed-Evidence Preservation Reobservation

- OpenSpec task: `5.3`
- Reviewed baseline source commit:
  `6f620434ba962216fb4cab11bd4bb0a8aefc4674`
- Reviewed baseline source tree:
  `ad7c1c4f18af90966577c01a2851444ff66c66e1`
- Reviewed manifest SHA-256:
  `6d5ec05d51a53a73c053e1591b3fb85d746c06efdc5c1b96f82a176e3de4e992`
- Reobserved inventory: 5 consumed source files, 13 standalone artifact
  files, and 3 complete artifact roots.

The qualification found that the reviewed manifest had no reusable validator,
so a standard-library source-only verifier was added to the successor control
plane. It binds the reviewed manifest ID/digest, baseline commit/tree, and all
three ordered closed path arrays; reconstructs source Git blob IDs, file
SHA-256 values, sizes, directory entries, counts, byte totals, and canonical
directory inventory digests; rejects symlinks and noncanonical JSON; and parses
consumed Python imports with `ast` without importing those modules.

RED produced seven expected failures because the verification entry point and
fixed preservation constants did not exist. GREEN passed the real repository
reobservation, one exact synthetic baseline, and the changed, missing, extra,
reordered, and successor-importing mutation matrix: `7 passed in 1.32s`. The
complete successor control file then passed `123 passed in 11.12s`, including
the fresh-process import-isolation checks.

No consumed source or empirical artifact was edited, imported, interpreted as
fresh evidence, or used to authorize native/model/seed access.

## Independent Review Hardening

- OpenSpec task: `5.4`
- Independent reviewer: `Noether`
- Initial review: four actionable findings covering launch-time revocation at
  the inventory API/CLI boundary, source-qualification binding before seed
  discovery, real Git publication identity, and dynamic import bypasses.
- Review RED: `6 failed, 5 passed in 14.03s`.
- Concentrated GREEN: `16 passed in 22.70s`.
- First expanded affected-file suite: `168 passed in 111.35s (0:01:51)`.
- Strict OpenSpec validation: passed.

The fixes require both `build-inventory` and `verify-inventory` to validate an
exact approval record and a fresh launch observation before source discovery.
They also require the request commit to equal clean tracked `HEAD` and pushed
`origin/master`, bind the request's source-inventory digest, and require the
embedded consumed-evidence preservation result to be verified. The published
seed inventory schema is now `v2` and retains the build launch digest plus the
source-inventory digest; post-build verification validates a fresh launch
without rewriting the original build binding.

The preservation verifier now proves the reviewed baseline commit/tree and
manifest publication commit/tree against the real Git object graph and the
recorded pushed remote ref. Its AST guard resolves literal or module-constant
`importlib.import_module`, imported `import_module` aliases, and `__import__`,
failing closed on unresolved dynamic imports. The source-inventory schema was
advanced to `v2` because preservation is now part of its canonical body.

The first re-review confirmed the source-eligibility and real-Git publication
findings resolved, but identified two remaining gaps: the independent verifier
could not reconstruct the new launch/source digest bindings, and
`getattr(importlib, "import_module")` could still bypass the dynamic-import
guard. The second review RED produced the expected `6 failed, 7 passed in
22.06s`.

Seed inventory schema `v3` now embeds a canonical, self-digested authority
evidence envelope containing the exact request, authorization, approval record,
original build launch observation, and source inventory. Producer verification
revalidates the original build envelope separately from the fresh current
verify-launch observation. The standard-library independent verifier separately
reconstructs nested document digests, approval mode and provenance, approval
and launch observation bindings and time watermarks, exact inventory authority
maps, source qualification, and all envelope-to-inventory relationships.
Replacing either the launch or source digest and recomputing the whole inventory
digest now fails.

The dynamic import guard now recognizes literal `getattr` lookup of
`import_module` and callable aliases in addition to direct, imported, nested,
and `__import__` forms. Final focused GREEN was `13 passed in 20.17s`; the first
GREEN attempt had `12 passed, 1 failed` solely because a successful source
rejection used a generic authority error string, which was then made specific.
The final complete affected-file suite passed `173 passed in 119.70s
(0:01:59)`. This supersedes the earlier `168`-test expansion and the narrower
task `5.3` count. Final independent re-review remains the last condition before
task `5.4` is marked complete.

The next independent pass found two deeper semantic variants: a fully rehashed
standing-delegation scope drift and a `getattr` callable alias. Their focused
RED was `3 failed, 8 passed in 20.63s`. The verifier now mirrors the fixed
standing scope, exclusions, revocation rule, resolver, grant/watermark task
provenance, and the external-human bound request terms and request-publication
ordering. Regressions mutate those nested meanings and recompute every affected
delegation, observation, approval, authorization, envelope, and outer inventory
digest. A real external-human authority fixture covers both valid and drifted
paths. The import guard now propagates both `getattr` callable provenance and
import-callable provenance to a fixed point.

Final focused standing/external/import GREEN was `14 passed in 20.18s`; the
complete affected-file suite passed `179 passed in 120.14s (0:02:00)`. This
supersedes both prior expanded counts. One final independent confirmation of
these exact two fixes remains before task `5.4` is complete.

The following review pass found two additional fixed-contract gaps: request
resources/exclusions/configuration were not independently reconstructed, and an
`importlib` module object alias was not propagated. Focused RED was `5 failed,
9 passed in 23.47s`; four failures were the intended implementation gaps, while
the external attack fixture itself was initially blocked by the producer's
correct exact-request validator and was rewritten as a pure JSON re-signing
probe. The independent verifier now fixes the exact configuration identity,
`1,152`-seed inventory resource ceiling, ordered exclusions, execution and
downstream authority maps, empty prerequisites, request/authorization identifier
forms, and canonical absolute output root. Both standing and external fixtures
modify the request and recompute every dependent digest before rejection.

The import guard's fixed point now propagates `importlib` module aliases as well
as `getattr` and import callables. Final focused GREEN was `16 passed in 22.33s`;
the complete affected-file suite passed `184 passed in 118.89s (0:01:58)`.
This is the current superseding source-only result pending final independent
confirmation.

The next review confirmed the fixed request and alias findings closed, then
identified one producer-equivalence edge: whitespace or NUL-only authority
strings. Exact full-chain RED was `4 failed, 2 passed in 0.77s`. A shared
standard-library strict nonempty validator now requires a string with nonblank
content and no NUL for standing/external grant or approval text, provenance
message/task IDs, and approval/launch watermark IDs. Focused GREEN was `8 passed
in 0.63s`; the complete affected-file suite passed `188 passed in 121.12s
(0:02:01)`. This supersedes all earlier affected-file counts.

Final independent re-review reported no actionable findings and explicitly
confirmed the original four findings, all later authority/request full-chain
findings, all three dynamic-import alias classes, and strict nonempty semantics
closed. Residual risk is limited to the specification's declared procedural
trust boundary for human identity/current-conversation truth and the deliberate
fail-closed requirement to update the independent fixed configuration identity
if the producer contract changes. OpenSpec task `5.4` is complete.

## Configured Repository Gates

- OpenSpec task: `5.5`
- Commit gate invocation count: one.
- Commit gate result: `3895 passed, 16 skipped in 511.96s (0:08:31)`;
  gate duration `515.35s`, exit code `0`.
- Full gate invocation count: one.
- Full gate result: `5725 passed, 18 skipped in 2446.07s (0:40:46)`;
  gate duration `2449.76s`, exit code `0`.
- Neither gate was retried, split, or rerun solely for timing.

Both configured boundaries passed after the code/spec/authority review was
closed and the implementation was frozen. The full gate is materially slower
than the commit gate because it includes the registered full-only targets; the
observed durations are retained as test-layering evidence rather than grounds
to alter this qualification run.

## Gameplay Applicability

- OpenSpec task: `5.6`
- Fresh gameplay validation: not applicable.

The implementation diff is confined to source-only `analysis_scripts`, focused
tests, this qualification report, and the OpenSpec task ledger. It does not
change production agent imports, CommunicationMod configuration, production
checkpoint discovery/loading, or live gameplay policy behavior. No game,
CommunicationMod process, native simulator, model, checkpoint, cohort, or seed
was started, loaded, materialized, or accessed during source qualification.
