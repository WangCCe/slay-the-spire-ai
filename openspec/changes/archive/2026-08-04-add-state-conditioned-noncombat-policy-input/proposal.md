## Why

The r2 terminal postmortem proved that the registered linear feature composition
cancels shared state from relative candidate scores, while the separately
implemented state-conditioned ranker has no validated API v3 input boundary.
The successor design audit therefore selects a source-only integration layer
before any new experiment, so architecture repair is verified independently of
training, cohorts, and policy-quality claims.

## What Changes

- Add a versioned source-only projection that converts one exact API v3
  decision into a separate CPU float32 state tensor and candidate tensor matrix.
- Reuse the existing recursive policy-leakage removal and candidate validation
  semantics without modifying the r2-bound experiment implementation.
- Bind projection, feature, hash-width, dtype, device, and ranker architecture
  identities in stable metadata.
- Add a canonical scored-decision row builder for the existing anti-collapse
  diagnostic summarizer.
- Add regressions for all four target categories, deterministic repeatability,
  source non-mutation, candidate permutation, leakage exclusion, malformed
  inputs, and integrated state-only ordering reversal.
- Keep native loading, environment construction, seed access, experiments,
  training, gameplay, model loading, reward work, and policy promotion out of
  scope.

Success means focused regressions and the repository commit gate pass, the r2
verifier remains unchanged and passing, and no experiment or production path
is activated. Rollback is deletion of the additive module, regressions, and
spec; no historical artifact, checkpoint, registration, or gameplay behavior
is migrated.

## Capabilities

### New Capabilities

- `noncombat-state-conditioned-policy-input`: Validated separate state/candidate
  feature projection, stable input identity, and canonical diagnostic-row
  construction for future non-combat policy evaluation.

### Modified Capabilities

None.

## Impact

The change adds one analysis module and focused tests, and depends on the
existing API v3 projection, policy feature encoder, state-conditioned ranker,
and standard-library diagnostics. It does not change Communication Mod,
production agent behavior, the native simulator, r2 evidence, Current/Bottled
roles, formal-RL readiness, or any authority boundary.
