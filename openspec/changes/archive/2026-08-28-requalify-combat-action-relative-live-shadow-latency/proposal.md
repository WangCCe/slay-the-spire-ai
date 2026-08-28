## Why

The first latent-reuse preflight stopped because six of 280 eligible fixed-
schedule rows exceeded a `1e-6` prediction tolerance even though all actions
and gates matched. A read-only diagnosis found a maximum best-score delta of
`2.861023e-6`, maximum candidate delta of `6.377697e-6`, minimum threshold
margin of `0.008984`, and minimum ranking margin of `0.000790`, so the failed
contract was stricter than ordinary float32 batch-shape equivalence and blocked
a behavior-preserving latency optimization.

## What Changes

- Preserve the post-failure 288-row numeric audit as diagnostic-only evidence.
- Define float32 selection equivalence as `rtol=1e-5` and `atol=1e-5` for
  predictions while still requiring exact actions, gates, abstentions,
  legality, forbidden-action handling, and telemetry.
- Reapply one-parent-latent-per-state selection and run a new immutable CPU
  preflight with the unchanged production-r16 parent, residual artifact,
  held-out corpus, speed targets, and deterministic measurement schedule.
- If the new offline preflight passes, run one behavior-neutral five-game live
  shadow with the unchanged 512-decision, 100-eligible, and 20ms p95 gates.
- Do not retrain, alter the scorer or threshold, grant candidate action
  authority, relax the live latency gate, or reinterpret the failed r1 attempt.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-action-relative-advantage-residual`: Define numerically grounded
  float32 equivalence for state-unique parent-latent candidate selection while
  retaining exact behavioral and safety equivalence.

## Impact

Affected code remains limited to action-relative selection, focused parity and
benchmark tests, compact diagnostic/preflight reports, and a new live-shadow
registration/report only if the offline gate passes. The retained artifact,
production-r16 checkpoint, CommunicationMod production behavior, training
state, gameplay guards, readiness thresholds, and candidate authority remain
unchanged. Rollback restores repeated-state candidate scoring and requires no
checkpoint or configuration migration.
