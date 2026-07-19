## 1. Lock The Regression Contract

- [x] 1.1 Add exact schema and rendering fixtures for request/result/review-binding v3, bootstrap-evidence v1, deterministic launch-token derivation, fixed direct-child paths, canonical ASCII JSON, and self-hash fields while retaining immutable v1/v2 fixtures.
- [x] 1.2 Add red producer tests proving the trusted launcher exclusively creates the claim before runner execution, treats every claim-path entry as consumed, rejects a second invocation, and remains silent on CommunicationMod stdout/stderr.
- [ ] 1.3 Add red subprocess tests for runner hash/path rejection, wrong HEAD, tracked or executable-source drift, unsafe Git metadata/configuration, malformed request anchors, invalid S-to-R review, and request-bound isolation drift; require the exact last completed stage and no active request or child.
- [ ] 1.4 Add red crash-matrix and verifier tests for termination after every stage, controlled failure records, missing failure records, malformed/torn claim bytes, stage gaps/reordering/hash drift, duplicate or extra entries, active-request-without-handoff, and uniformly false authority.

## 2. Implement V3 Pre-Request Evidence

- [x] 2.1 Implement one minimal pure-stdlib no-follow bootstrap publisher for exclusive durable claim/stage/failure records, canonical serialization, bounded sanitized diagnostics, parent/final identity rechecks, and never-overwrite semantics.
- [x] 2.2 Implement request v3 construction/loading and validation for bootstrap schema, guarded root and fixed paths, ordered stages, token derivation inputs, external R/request/runner anchors, preexisting static inventory, and v1/v2 launch rejection.
- [x] 2.3 Extend the trusted launcher and runner-entry boundary to validate fixed bootstrap anchors, publish `launcher_verified` and `runner_entered`, preserve isolated/no-site and source-only startup, and exit silently with a bounded pre-request failure when possible.
- [x] 2.4 Publish `source_verified`, `request_reviewed`, and `isolation_verified` only after their existing checks complete; ensure recording a stage does not repeat Git/source/inventory/isolation work or mutate protected live state.
- [x] 2.5 Publish the exact active request followed by a request-bound handoff, forbid attempt or child launch before valid handoff, and bind the bootstrap inventory/final-stage/handoff hashes into v3 review and terminal records.

## 3. Extend Independent Replay

- [x] 3.1 Independently reconstruct v3 token inputs, guarded direct-child paths, canonical bytes, claim consumption, static anchors, ordered stage/self-hash chain, bounded failure classes, and handoff without importing producer result builders or trusting current worktree bytes.
- [x] 3.2 Implement deterministic `reviewed_prepared`, `pre_request_partial`, `sealed_invalid`, `active_request_partial`, and existing verified-terminal classification with exact last-stage reporting and no retry or positive authority for every incomplete state.
- [x] 3.3 Require an exact v3 bootstrap chain and handoff before terminal verification; reject missing, extra, malformed, linked, non-regular, mutated, reordered, synthetic, or externally mismatched evidence without deleting or repairing the root.
- [x] 3.4 Replay preserved r1-r6 request/result/audit/report fixtures byte-for-byte through the historical v1/v2 branches and prove no classification, hash, authority, or launchability changes.

## 4. Prove Isolation And Compatibility

- [ ] 4.1 Run the complete injected-failure matrix in subprocesses and prove each consumed identity rejects a second invocation before active request, attempt, or child creation.
- [ ] 4.2 Prove every pre-request path preserves marker, run, checkpoint, global-log, registered-study-root, run-lock, ledger, manifest, trace, model, and policy state and never invokes `start` or a training command.
- [ ] 4.3 Prove CommunicationMod-equivalent whitespace splitting reproduces the exact v3 launcher vector, qualification remains stream-silent, child stream ownership is unchanged after handoff, and ordinary gameplay/eval/training startup creates no bootstrap artifacts.
- [ ] 4.4 Run a bounded production-Windows-Python subprocess smoke for reviewed launcher-to-handoff fixtures without Java or gameplay; record exact artifacts and keep real CommunicationMod validation deferred to a separate approved replacement amendment.

## 5. Verify And Close The Offline Change

- [ ] 5.1 Run focused Windows pytest for qualification runner, verifier, handshake, and runtime-error slices with cache disabled and a writable repository basetemp.
- [ ] 5.2 Run the complete Windows pytest suite with cache disabled and a writable repository basetemp; resolve every regression before review.
- [ ] 5.3 Run `openspec validate --all --strict`, `git diff --check`, canonical byte/hash checks, stale-placeholder scans, and an independent source-only review of the exact implementation diff.
- [ ] 5.4 Record an offline closeout containing test counts, v3 schema/hash fixtures, crash-matrix coverage, historical r1-r6 replay, isolation results, non-goals, rollback boundary, and all-false live/study/training authority.
- [ ] 5.5 Only after the implementation and closeout pass review, mark the pending observability tasks in `add-tracked-outcome-qualification-orchestrator` and `run-v2-known-propensity-outcome-evidence-study` complete; leave r7 preparation, game launch, live qualification, and `start` to a separate explicit amendment.
