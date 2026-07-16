## Context

The v2 replacement qualification launched the exact Windows child from a tracked-clean candidate. The child queued protocol `ready` at 23:53:22.797 and CommunicationMod logged receipt at 23:53:22.798, proving that process startup and both sides of the stdout pipe worked. The child then waited for one retained CommunicationMod state, as required before study-ready publication, and failed at 23:53:52.859 because `READINESS_TIMEOUT_SECONDS` is fixed at 30. CommunicationMod did not register its mod badge until 23:54:02.220 and observed the child death at 23:54:03.046.

The same constant is validated by the child attempt schema, emitted into every launchable registration, consumed by the parent runner, and independently reconstructed by the standalone verifier. A qualification-only timeout override would therefore test a different contract from the registered study and is not acceptable.

The immutable r2 failure record proves that no study-ready or release file, run lock, ledger, gameplay output, marker growth, checkpoint mutation, training, or registered study root resulted. This change starts from that fail-closed boundary and does not authorize another qualification identity by itself.

## Goals / Non-Goals

**Goals:**

- Make the fixed launchable handshake tolerate a cold first CommunicationMod state that arrives after 30 seconds but strictly before the 120-second deadline.
- Keep the parent and child on one exact hash-bound readiness deadline.
- Preserve callback suppression, preclaim ordering, exclusive handshake artifacts, process-exit checks, and all existing fail-closed paths.
- Prove the fix with a deterministic fake-clock regression before changing production code.
- Keep the independent verifier structurally independent by encoding the reviewed 120-second contract directly.

**Non-Goals:**

- Do not change the 10-second release deadline, protocol or registration schema versions, artifact names, slot schedule, seeds, exploration rates, alternative budget, target policy, estimator, thresholds, or authority gates.
- Do not modify CommunicationMod Java, optimize game startup, require SuperFastMode, prewarm the game, or weaken the requirement to receive a real CommunicationMod state.
- Do not start training, create a run lock, launch the pending study, or create an r3 qualification root inside this change.
- Do not rewrite either failed qualification root or reinterpret either failure as a registered slot.

## Decisions

### 1. Replace the shared 30-second readiness deadline with 120 seconds

`READINESS_TIMEOUT_SECONDS` remains a single fixed protocol constant and changes from 30 to 120. Both the child wait and parent wait continue to use the attempt-bound value, so neither side can silently wait longer than the value committed into the registration.

The monotonic deadline is an exclusive upper bound: state or ready first observed at or after 120 seconds is rejected, and release first observed at or after 10 seconds is rejected. This keeps exact-deadline races fail-closed instead of allowing a late success to bypass the timeout check.

The observed cold-start path exceeded 39 seconds before CommunicationMod post-initialization. A 120-second bound provides roughly three times that observed interval while remaining short relative to a 25-game slot and preserving deterministic failure.

Alternative considered: use 60 seconds. Rejected because it leaves little margin for a reboot, cold filesystem cache, slower mod initialization, or host contention and would risk consuming another immutable qualification identity for the same timing class.

### 2. Keep one readiness phase and the existing release phase

The attempt record continues to contain `readiness_timeout_seconds=120` and `release_timeout_seconds=10`. No schema field is added. The child still publishes study-ready only after receiving and retaining one callback-free state, and still waits for a matching release before exploration or agent initialization.

Alternative considered: add separate process-start, game-initialization, and state-readiness deadlines. Rejected because the current evidence identifies one undersized bound, while a schema expansion would increase producer, runner, verifier, migration, and qualification risk without improving the required gate.

Alternative considered: publish study-ready immediately after sending protocol `ready`. Rejected because that would stop proving CommunicationMod-to-child state delivery and weaken the preclaim gate.

### 3. Reproduce the defect with a fake clock at 45 seconds

The red regression will drive `perform_child_handshake_if_configured` with a coordinator that returns no state until simulated time 45, then returns one retained state. The release is published only after the ready file appears. Under the existing 30-second contract the test must fail with `child readiness deadline exceeded`; under 120 seconds it must publish and validate ready/release without callbacks.

The regression uses no wall-clock sleep, game process, network, or checkpoint. Existing malformed, timeout, duplicate, and ordinary-gameplay tests remain unchanged and must continue to pass.

Alternative considered: encode only `assert READINESS_TIMEOUT_SECONDS == 120`. Rejected as insufficient because it would not prove that the real wait loop accepts the observed timing class.

### 4. Keep independent verification deliberately duplicated

The standalone verifier will change its independently reconstructed launchable contract from literal 30 to literal 120 rather than importing the producer constant. Exact registration and dry-run tests will be regenerated from the reviewed contract, and historical schema-v1 evidence remains read-only.

Alternative considered: share the constant with the verifier. Rejected because a correlated producer bug could then make generation and verification agree on an unreviewed value.

### 5. Treat registration regeneration and r3 qualification as later gates

This change may update shared implementation and its generic tests, but it does not silently reuse the pending registration. After this change is committed and reviewed, `run-v2-known-propensity-outcome-evidence-study` must be explicitly amended to preserve r2, regenerate the exact v2 registration under the new source, bind the new hashes, and authorize a previously absent r3 root. The complete qualification gate then starts from that later tracked-clean commit.

## Risks / Trade-offs

- [A genuinely dead child that remains alive can take up to 90 seconds longer to reject] -> Keep active process-exit checks on every parent poll and the bounded 120-second child deadline; do not add retries.
- [Producer and verifier can drift during the literal update] -> Require focused producer/runner/handshake/verifier tests plus exact registration replay and full pytest before commit.
- [A registration with 30 seconds could be accidentally launched after the code change] -> Existing exact contract validation and registration hashes reject it; the pending study must regenerate and re-review before any `start` call.
- [The fix could be mistaken for study authorization] -> Keep all authority booleans closed, create no external r3 root in this change, and preserve both failed roots byte-for-byte.
- [A future cold startup could exceed 120 seconds] -> Fail closed and preserve that new identity; do not retry or dynamically extend the reviewed deadline.

## Migration Plan

1. Add and run the 45-second fake-clock regression against the current 30-second implementation; retain the expected red failure.
2. Change the shared readiness constant to 120 and update independently duplicated verifier expectations plus exact-contract tests.
3. Run focused handshake, expansion, runner, verifier, and registration tests; then run the full Windows pytest suite, compile/import checks, strict OpenSpec validation, and whitespace checks.
4. Obtain independent review and commit this fix without launching Slay the Spire or changing external evidence.
5. In a separately reviewed amendment, preserve r2 hashes, regenerate the pending v2 registration and review, select a previously absent r3 qualification root, and repeat the complete qualification gate.

Rollback before step 5 is a normal source revert. Once any r3 qualification artifact exists, that external identity is immutable and rollback follows the existing no-retry qualification rules.

## Open Questions

None. The value, regression timing, unchanged release bound, isolation boundary, and later registration/qualification gates are fixed by the approved design.
