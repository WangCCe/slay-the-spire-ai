## 1. Freeze The Recovery Baseline

- [ ] 1.1 Record the current verifier failure against the immutable 2026-07-15 blocked artifact, its registration/run-lock/ledger/claim/closeout hashes, and the exact set of absent normal OPE artifacts without modifying the external root.
- [ ] 1.2 Add a repository fixture builder for normal and blocked study shapes that preserves v1 field semantics while keeping tests independent of the external game directory.
- [ ] 1.3 Add red verifier regressions proving the valid blocked fixture currently fails at `normal closeout has a global stop` and that the existing normal fixture remains the control.

## 2. Independently Verify Blocked Closeouts

- [ ] 2.1 Refactor ledger replay to return a validated terminal prefix and optional global stop without weakening chain, ordering, marker, active-slot, or duplicate-stop checks.
- [ ] 2.2 Return the validated finalization claim and select normal versus blocked verification only from ledger state plus claim mode; reject every mixed combination.
- [ ] 2.3 Implement independent blocked JSON and Markdown reconstruction, exact slot/source/blocker/limitation/all-false-gate checks, and required absence of every normal pool/OPE output.
- [ ] 2.4 Add deterministic tamper regressions for stop reason, claim mode, slot accounting, source binding, closeout hash, blocker, gate, limitation, Markdown, forbidden artifact, and normal-path fallback.
- [ ] 2.5 Run the standalone verifier read-only against the immutable 2026-07-15 artifact and record the passing blocked-branch summary; commit the verifier behavior as one cohesive risk-class change.

## 3. Define The Two-Phase Handshake

- [ ] 3.1 Add red tests for strict handshake environment parsing, deterministic slot token binding, exclusive canonical attempt/ready/release publication, PID/config/run-lock validation, deadline handling, and stale-file rejection.
- [ ] 3.2 Implement a focused shared handshake module with no effect when its explicit environment is absent.
- [ ] 3.3 Add red `main.py` startup-order tests proving the child receives one parseable state with callbacks disabled, emits no action, waits for release before exploration/agent initialization, and retains the state for exactly-once normal processing.
- [ ] 3.4 Integrate the child gate before exploration runtime and agent creation while preserving ordinary and non-study combat-RL coordinator startup behavior.

## 4. Claim Slots Only After Readiness

- [ ] 4.1 Add registration v2 tests and generation for the fixed protocol version, 30-second readiness and 10-second release deadlines, attempt/ready/release names, implementation binding, and fail-closed continuation rule; preserve v1 read-only verification and reject v1 `start` or `run-next`.
- [ ] 4.2 Add red runner tests that publish an exclusive attempt and capture the marker baseline before the exact child starts while holding the ledger unlaunched, then assert unchanged markers and `slot_started` after verified readiness and immediately before release.
- [ ] 4.3 Replace the synchronous child call with a bounded process lifecycle that validates readiness, publishes release, waits for terminal accounting, and cleans up the child on every failure path.
- [ ] 4.4 Cover timeout, early exit, malformed or mismatched readiness, orphaned or duplicate attempts, marker growth, premature manifest/trace creation, release failure, host-style recovery before and after claim, global-stop launch blocking, and no retry/replacement behavior.
- [ ] 4.5 Extend dry-run and blinded structural monitoring with handshake paths and safe existence/hash/status fields only; keep outcome and policy-evaluation fields forbidden.
- [ ] 4.6 Commit the handshake, registration, runner, and monitor behavior as one cohesive risk-class change.

## 5. Verify Without Starting A Study

- [ ] 5.1 Run focused Windows pytest for verifier, finalizer, registration, runner, handshake, `main.py` startup, exploration runtime, and monitor regressions with a writable repo basetemp.
- [ ] 5.2 Run the full Windows pytest suite with cache disabled and a writable repo basetemp; fix only failures caused by this change.
- [ ] 5.3 Run strict OpenSpec validation, `git diff --check`, Python compile/import checks, handshake schema byte checks, and confirm the old external artifact hashes remain unchanged.
- [ ] 5.4 Perform one bounded no-action CommunicationMod handshake smoke outside any registered study: require attempt/ready/release success with no ledger slot, exploration manifest, trace, AI marker, checkpoint mutation, or persistent config drift, then stop the game process.
- [ ] 5.5 Obtain an independent final review of verifier independence, branch fail-closed behavior, process/reboot races, normal-runtime inertness, test coverage, and authority boundaries; address accepted findings with regressions.
- [ ] 5.6 Write and commit a closeout report stating implementation evidence and remaining limits; do not generate a fresh registration or authorize OPE, training, reward design, gameplay-policy edits, or live promotion.
