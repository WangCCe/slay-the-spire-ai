## Why

The replacement v2 launch qualification proved that the registered child and CommunicationMod exchanged protocol `ready`, but Slay the Spire cold startup did not produce the first callback-free state before the fixed 30-second study-handshake deadline. The child failed closed at 30 seconds while CommunicationMod initialization was still in progress, so the same registered contract could falsely stop every cold-start study slot before gameplay.

## What Changes

- Increase the single hash-bound study-handshake readiness deadline from 30 seconds to 120 seconds across the producer, child validator, runner, independent verifier, tests, and future launchable registrations.
- Add a deterministic regression in which the first CommunicationMod state arrives after 45 seconds and require the default contract to complete attempt/ready/release without callbacks or gameplay.
- Preserve the 10-second release deadline, protocol schemas, artifact names, fail-closed behavior, ordinary-gameplay startup, and all non-combat behavior, schedule, estimator, and authority contracts.
- Treat every registration containing the old 30-second deadline as immutable historical evidence. Do not rewrite either failed qualification root or launch the pending v2 study under its current registration hash.
- Require the pending v2 study to regenerate and independently review its registration and use a new qualification identity only after this change is verified and committed.

Success means the focused regression accepts a state delivered at 45 seconds under the new 120-second contract, timeout and malformed-handshake cases still fail closed, focused and full pytest pass, strict OpenSpec validation passes, and no game, run lock, ledger, training, or policy change occurs during this fix.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-outcome-evidence-expansion`: increase the required launchable handshake readiness deadline while preserving the existing preclaim, blinding, isolation, and authority boundaries.

## Impact

- Runtime contract: `spirecomm/communication/study_handshake.py` and registration generation in `analysis_scripts/noncombat_outcome_evidence_expansion.py`.
- Independent verification: `analysis_scripts/verify_noncombat_outcome_evidence_expansion.py` must independently expect the new fixed value without importing the producer constant.
- Regression and exact-contract coverage: study-handshake, outcome-evidence expansion, runner, verifier, and committed-registration tests and artifacts.
- Live evidence: immutable r2 failure record self-hash `8bb9b396e129e017fd84fb4aabe7fa6d02bb51b0c7c147836dbf29e7c289c95c` and file SHA-256 `3fbace492dd0f849bdf86deff1df97dfc4ae3b77a427545413ac48170c9c2540`.
- Non-goals: no exploration-rate, seed, schedule, reward, policy, estimator, threshold, training, checkpoint, CommunicationMod Java, or gameplay decision change.
- Rollback boundary: before any newly reviewed qualification root is created, this source change may be reverted normally; after a new qualification identity is attempted, preserve that identity and follow the existing no-retry governance instead of reverting evidence.
