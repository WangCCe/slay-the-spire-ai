## Why

The consumed state-conditioned experiment improved paired canary floor by
`+10.75` but selected `take` on all `1,458` trained card-reward decisions and
stopped before holdout. The read-only trajectory and action-family audits now
show an evidence-backed intervention boundary: replace flat candidate sampling
with the checked-in hierarchical family distribution while keeping reward,
model, optimizer, and deterministic evaluation controls fixed.

## What Changes

- Add a new, additive simulator-only successor identity; preserve the consumed
  runner, verifier, tests, registration, checkpoints, terminal artifacts, and
  untouched holdout identities byte-for-byte.
- Define candidate `kind` as the action family, sample family first and then a
  candidate within that family, and train on the exact sum of selected family
  and conditional log probabilities.
- Freeze separately named family and expected-conditional entropy coefficients
  at `0.01` each. Their equal initial values preserve the prior numeric entropy
  multiplier, not the entropy magnitude or gradient, while making both terms
  independently bound, reported, tested, and immutable.
- Keep the state-conditioned ranker, exact API v3 policy input, formal reward,
  Adam configuration, normalized returns, gradient ceiling, and frozen seeded
  initialization control unchanged so the policy distribution is the only
  intended learning intervention.
- Keep deterministic evaluation on the unique maximum raw score. Never use
  joint-probability argmax; fail closed on a raw-score tie instead of adding a
  hidden tie-break rule.
- Add registered family-aware trajectory diagnostics, an exact persistent
  training-collapse stop, and card-reward/shop canary gates. A failed canary
  leaves the new holdout untouched.
- Require a fresh deterministic exclusion inventory that excludes every
  historical, consumed, reserved, diagnostic, training, canary, and holdout
  identity, including the prior experiment's unvisited holdout.
- Cap a later empirical execution at `4,096` training episodes, `2,560`
  evaluation/replay episodes, `6,656` total episodes, `64` episodes per update,
  CPU only, and `28,800` charged seconds. These are ceilings, not current
  authority to materialize cohorts or run the experiment.
- Split the implementation into a standard-library control plane, a lazily
  imported Torch runtime, and an independent standard-library verifier. Reuse
  only stable low-level public APIs; do not refactor or import private logic
  from the consumed experiment.
- Stage source implementation, fresh registration, exact execution
  authorization, one evidence-bearing execution, and closeout as separately
  reviewed and committed boundaries.

Success for this change is an independently reviewed, source-only successor
contract whose synthetic and fixture tests prove two-stage replay, split-loss
gradients, one-family fallback, raw-score tie failure, immutable cohort and
resource terms, holdout isolation, and no Torch/native import from control-only
commands. A later empirical success additionally requires a structurally valid
canary, no family saturation, complete holdout, and a positive registered
paired floor signal; victory remains a separate stronger signal.

Non-goals are reward redesign, coefficient tuning, reference-policy training,
formal RL readiness, policy-quality claims, target-supported outcome claims,
production checkpoint loading, gameplay, CommunicationMod, qualification, and
promotion. Before registration, rollback is deletion of additive successor
files. After a registration is pushed its contract is immutable; after any
empirical seed is accessed, failures are preserved under the same logical
identity and cannot be repaired by changing source, cohorts, thresholds, or
controls.

## Capabilities

### New Capabilities

- `noncombat-hierarchical-simulator-learning-successor`: Defines the isolated
  hierarchical policy runtime, immutable experiment contract, fresh-cohort and
  authorization boundaries, bounded execution lifecycle, anti-collapse gates,
  raw-score evaluation, and independent terminal verification.

### Modified Capabilities

None.

## Impact

- Adds successor-specific modules under `analysis_scripts/`, focused tests,
  source-only control reports, and later separately authorized empirical
  artifacts.
- Reuses public contracts from the state-conditioned ranker/input, simulator
  adapter, formal reward, action-family distribution, and hierarchical
  objective capabilities.
- Does not change agent behavior, `main.py`, CommunicationMod configuration,
  production checkpoints, the game, prior empirical artifacts, or any consumed
  experiment source.
