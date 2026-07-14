## Why

The frozen B3-B7 pool now passes known-propensity qualification and the
deterministic-Current overlap screens with 125 complete trajectories, 87
nonzero-weight trajectories, and ESS 66.30, but the repository still has no
validated value estimator or uncertainty contract. Implementing those checks
now separates trustworthy estimator plumbing from the much stronger claim
that the current 1-win dataset proves a policy improvement.

## What Changes

- Add an offline-only estimator-validation capability for complete-run
  trajectory weights and terminal outcomes.
- Define self-normalized trajectory importance sampling as the primary bounded
  estimator and ordinary trajectory importance sampling as an explicit
  high-variance diagnostic, without clipping or per-decision outcomes.
- Add paired whole-trajectory bootstrap intervals for target value, behavior
  value, and uplift, using a deterministic hash-based resampling contract.
- Add leave-one-trajectory-out influence diagnostics and separate estimator,
  dataset, and candidate-comparison readiness gates.
- Require exact behavior-identity, synthetic known-truth, bootstrap-enumeration,
  row-order, and fixed coverage-calibration evidence before estimator
  validation can pass.
- Generate a B3-B7 estimator report whose success metric is reproducible,
  independently checked estimator accounting. Candidate superiority remains
  blocked unless the primary victory-uplift interval, estimator-direction, and
  leave-one-run-out gates all pass.
- Keep causal claims, formal non-combat RL training, live policy promotion,
  gameplay policy changes, behavior exploration rates, run records,
  CommunicationMod configuration, and checkpoints out of scope.
- Keep rollback offline: removing the estimator module, tests, OpenSpec delta,
  and generated reports restores the previous estimate-free readiness state.

## Capabilities

### New Capabilities

- `noncombat-ope-estimator-validation`: Defines trajectory-level estimators,
  deterministic uncertainty, synthetic calibration, sensitivity diagnostics,
  candidate-comparison gates, and fail-closed estimator artifacts.

### Modified Capabilities

- `noncombat-ope-readiness`: Accepts a hash-bound successful estimator
  validation artifact as a separate readiness input while preserving distinct
  overlap, policy-comparison, training, causal, and live-promotion gates.

## Impact

- Adds offline analysis code and focused tests under `analysis_scripts/` and
  `tests/`; no live agent import path changes.
- Adds versioned estimator-validation and estimate artifact schemas plus a
  frozen B3-B7 report under `reports/`.
- Reuses the canonical sample, target-manifest, exact trajectory-weight, and
  independent-verifier contracts already implemented by
  `noncombat-ope-readiness`.
- Uses only the Python standard library and deterministic exact arithmetic; no
  new runtime dependency or production checkpoint format is introduced.
