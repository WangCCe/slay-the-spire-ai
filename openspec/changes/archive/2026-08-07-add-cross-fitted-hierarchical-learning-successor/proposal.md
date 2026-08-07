## Why

The consumed hierarchical successor stopped after 512 episodes because its
greedy card-reward family saturated on `take`, while the follow-up audit showed
that row-local pressure was not enough to explain the shared-parameter update.
The checked-in advantage-attribution contract now makes one narrow empirical
successor possible: replace batch-normalized returns with trajectory-disjoint
state-value advantages and measure the resulting complete gradient direction.

## What Changes

- Add a new simulator-only successor identity while preserving the consumed
  hierarchical runner, registration, checkpoints, terminal bundle, and every
  previously used or reserved seed.
- Fit a deterministic 128-dimensional state-only linear ridge baseline inside
  each 64-episode update. Use four trajectory-disjoint folds, complete
  non-held-out fit sets, trajectory-balanced squared error, an unpenalized
  intercept, fixed ridge coefficient `0.001`, predictions clipped to the formal
  return range `[0, 3]`, and fixed unit advantage scale.
- Make the held-out residual advantage the primary learning intervention while
  preserving the ranker, policy input, hierarchical sampling, reward, Adam
  configuration, entropy coefficients, gradient ceiling, and seeded
  initialization. Explicitly register the ledger-derived float64 clip-factor
  installation as a second numeric-path intervention instead of claiming
  bitwise equivalence to the consumed float32 Torch clipping path.
- Apply the checked-in five-component shared-gradient ledger before every
  optimizer step. Retain the raw component and complete gradients, one uniform
  clip factor, the actual Adam state transition, and a same-batch
  legacy-objective gradient diagnostic under the consumed return normalization.
- Bound a later mechanism experiment to eight updates, 512 unique fresh
  scheduled trajectories, at most 576 environment episode accesses including
  one same-identity incomplete-chunk replay reserve, no canary or holdout
  cohort, CPU only, ascension `0`, and 14,400 charged seconds. Bind the loaded
  native module and build provenance, the pushed `origin/master` source tree,
  and unchanged CommunicationMod and production-checkpoint isolation before
  and after execution. Retain the exact four-chunk family-saturation stop as a
  negative mechanism result rather than a policy-quality gate.
- Publish fold/fit provenance, sparse pre-decision state features, returns,
  predictions, advantages, fitted baseline parameters and diagnostics, raw
  gradient payloads, pre/post Adam states, per-access seed journal, checkpoints,
  resource use, and an independently verified terminal inventory. Recover only
  uniquely reconstructable checkpoint-envelope or terminal-publication writes
  without another seed access or optimizer update. Poor predictive fit is
  reported and never triggers a
  fallback, alternate estimator, coefficient change, or retry.
- Require a clean pushed implementation before a fresh exclusion inventory and
  all-false registration can be created. Require an exact reviewed execution
  request and a separate explicit human approval before an authorization may be
  published or any native loading, environment construction, seed access,
  baseline fitting, or policy training may begin. The execution gate loads and
  validates the registered native module before importing Torch, and only then
  may drive the immutable schedule to a closed terminal bundle.

Success for this change is a source-only, independently reviewed successor
contract whose synthetic tests prove leakage exclusion, cross-fit arithmetic,
deterministic ridge fitting, raw gradient reconstruction, actual optimizer
gradient installation and Adam transition replay, checkpoint resume, bounded
artifact publication, and terminal verification. A later empirical execution
succeeds operationally when
it produces one structurally valid terminal mechanism bundle, including a
valid negative saturation result; it does not need to improve floor or win.

Non-goals are estimator or coefficient tuning, reward or architecture changes,
canary/holdout policy evaluation, comparison with Bottled or Current, formal RL
readiness, production checkpoint loading, gameplay, CommunicationMod,
qualification, policy promotion, or a causal policy-quality claim. Before a
registration is pushed, rollback deletes only additive successor files. After
registration or seed access, rollback means cancellation or preservation of
the immutable attempt, never changing its estimator, folds, cohort, thresholds,
or controls.

## Capabilities

### New Capabilities

- `noncombat-cross-fitted-hierarchical-learning-successor`: Defines the
  trajectory-disjoint state-value baseline, held-out advantage objective,
  shared-gradient evidence, bounded fresh mechanism experiment, immutable
  lifecycle, and independent terminal verification.

### Modified Capabilities

None.

## Impact

- Adds successor-specific control-plane, Torch-runtime, independent-verifier,
  and source-only seed-inventory modules under `analysis_scripts/`, focused
  tests, and later separately authorized registration and terminal report
  artifacts.
- Reuses public contracts from the policy input, candidate feature projection,
  state-conditioned ranker, simulator adapter, formal reward, hierarchical
  distribution/objective, and advantage-attribution capabilities.
- Does not change `main.py`, agent behavior, CommunicationMod configuration,
  production checkpoints, gameplay, or any consumed empirical artifact.
