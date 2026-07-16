## Why

The 2026-07-15 v1 outcome-evidence study is permanently blocked and cannot be resumed, while the underlying evidence question remains unresolved. The recovery change now provides a launchable v2 handshake and an independent blocked-closeout verifier, so the next step is a separately reviewed v2 registration with a new artifact root rather than training, policy tuning, or reuse of v1 evidence. The first pre-lock qualification attempt for this registration stopped before ready/release because an external PowerShell log monitor encountered a Windows sharing violation; it created no registered study artifact and exposed no runtime implementation defect.

## What Changes

- Create one canonical v2 registration for a new 24-by-25 known-propensity eval schedule with new deterministic slot IDs, seeds, paths, and artifact root while preserving the registered exploration rates, action budget, evidence thresholds, deterministic-Current target, and validated estimator contracts.
- Add a pre-collection qualification gate that replays the canonical registration, dry-runs every registered child command, and proves the real CommunicationMod child can complete the no-action attempt/ready/release handshake without claiming a ledger slot or creating gameplay evidence. Preserve the first failed qualification root byte-for-byte and repeat the complete gate only in the explicitly reviewed `noncombat_outcome_evidence_expansion_20260716_v2_qualification_r2` root.
- Freeze a clean source commit and v2 run lock only after qualification and independent review pass. Reject any implementation, registration, command, CommunicationMod, checkpoint, or qualification-binding drift before or during collection.
- Execute the 24 ordered slots blindly through the v2 handshake. Preserve launch-at-most-once, non-replacement, fixed-rate, fixed-threshold, and global-stop behavior; expose only structural monitor fields until collection terminates.
- Finalize exactly once after either all slots are terminal or one registered global stop closes collection, then require the standalone verifier to replay the applicable normal or blocked branch.
- Keep OPE interpretation, formal non-combat RL training, reward design, Bottled-driven live actions, gameplay-policy edits, and live promotion unauthorized. A passing evidence gate permits only a later separately approved analysis or training proposal.

Success is an independently verified `ready`, `inconclusive`, or `blocked` closeout from the new v2 root. A favorable policy estimate is not required, and no observed result may extend the schedule, lower a threshold, replace a slot, or change the target policy.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-outcome-evidence-expansion`: require a bound no-action launch qualification before a fresh v2 run lock, and define execution and closeout of a separately registered v2 study without changing historical v1 evidence.

## Impact

- Primary code and tools: read-only reuse of `analysis_scripts/noncombat_outcome_evidence_expansion.py`, `scripts/run_noncombat_outcome_evidence_expansion.py`, the independent verifier, and their existing tests. No gameplay, runner, estimator, or verifier implementation change is planned; a discovered defect blocks this change and requires a separate regression-backed fix plus a fresh registration review.
- Planning and evidence artifacts: one committed v2 registration and amended registration review, one immutable external qualification-failure record, one separately attested successful pre-lock qualification record that is copied into the repository only after the run-lock window closes, one new external study root, blinded monitor artifacts, and a deterministic final closeout and verifier audit.
- Live execution: Windows-only CommunicationMod eval through `D:\anaconda\envs\stsai\python.exe`; no WSL gameplay process, training flag, checkpoint mutation, or ordinary-gameplay handshake is introduced.
- Historical compatibility: the immutable 2026-07-15 v1 root remains read-only and excluded from every v2 pool, estimate, and authority decision.
- Rollback boundary: before `start`, preserve every failed qualification identity, restore the pre-study CommunicationMod baseline, and collect no evidence. A replacement qualification root requires an explicit reviewed amendment and a complete fresh qualification; it is never an in-place retry. Once `start` publishes any registered study artifact, any integrity failure follows the registered blocked or recovery path and restores live configuration only after independent verification.
