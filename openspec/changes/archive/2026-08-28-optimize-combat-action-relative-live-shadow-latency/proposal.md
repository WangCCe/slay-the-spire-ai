## Why

The first production-r16 action-relative live shadow passed identity, support,
neutrality, legality, EndTurn safety, budget, and error gates but failed its
registered latency ceiling: p95 inference was 41.089705ms versus 20ms. The
selection path currently repeats the frozen parent latent computation once for
every legal candidate of the same state, so the failure has a narrow,
evidence-backed implementation cause that does not require retraining.

## What Changes

- Compute the frozen parent latent once per distinct batch row during
  action-relative candidate selection and reuse it for every allowed candidate.
- Prove exact action, gate, ranking, and prediction parity against the current
  repeated-state reference across multi-row masks, forbidden actions, and
  abstentions.
- Add a bounded CPU microbenchmark using the retained production-r16 parent and
  unchanged development artifact before opening a new live cohort.
- If parity and the offline latency preflight pass, register one new
  behavior-neutral five-game live shadow with the unchanged 512-decision,
  100-eligible, and 20ms readiness gates.
- Do not refit the scorer, tune its threshold, change gameplay guards, grant
  candidate action authority, or reuse the completed r1 trace as fresh evidence.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-action-relative-advantage-residual`: Candidate selection must reuse
  one frozen parent latent per state while remaining numerically and
  behaviorally equivalent to the repeated-state reference.

## Impact

Affected code is limited to
`spirecomm/ai/rl/v2/action_relative_advantage_residual.py`, focused residual and
live-shadow tests, a read-only microbenchmark report, and a separately committed
r2 live registration/report if offline gates pass. The retained model artifact,
production-r16 checkpoint, CommunicationMod behavior, and readiness thresholds
remain unchanged. Rollback restores the previous candidate-pair scoring path and
does not require checkpoint or config migration.
