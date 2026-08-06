## Why

The completed hierarchical card-reward audit found positive aggregate direct
`take`-logit pressure in all eight chunks, but a supported effective-floor
band had nonpositive pressure. Its 3,559 eligible decisions still use
trajectory-confounded normalized reward to go, and the row-local logit
derivative does not identify the update applied through the shared ranker.
Before selecting another algorithm or empirical cohort, the repository needs a
source-only contract that turns both limitations into explicit, synthetic,
reviewable evidence requirements.

## What Changes

- Add an additive CPU source-only contract for advantage records whose baseline
  prediction and scaling provenance exclude the complete held-out trajectory.
  The contract validates supplied provenance and arithmetic but does not fit or
  select a critic, baseline architecture, feature set, fold count, or empirical
  dataset.
- Add a named shared-parameter gradient ledger over supplied synthetic loss
  components and a separately supplied full loss. It reconstructs the complete
  pre-clip gradient, applies only the one registered uniform global-norm clip
  factor, and reports component norms, dot products, cosines, and reconstruction
  residuals without entering Adam or claiming that optimizer updates or causal
  effects decompose additively.
- Define the minimum evidence a future registration must expose: stable
  trajectory/fold identity, fit and scale provenance, raw return, baseline,
  advantage, ordered parameter identity, component gradient vectors, clip
  factor, and reconstruction residuals.
- Publish deterministic synthetic evidence using a tiny shared ranker to prove
  held-out-trajectory rejection, exact gradient additivity, clipping identity,
  and a case where row-local family pressure does not determine the complete
  shared-parameter direction.
- Keep production runtimes, consumed evidence, reward, objective coefficients,
  optimizer, architecture, checkpoints, cohorts, game files, and
  CommunicationMod unchanged. Every loading, fitting, execution, training,
  gameplay, qualification, formal-RL, and promotion authority remains false.

Success means focused synthetic tests and an independent review reproduce the
same canonical report, prove source/runtime import isolation, reject provenance
or gradient drift, and leave the existing commit gate green. It does not
require or authorize an empirical result. The rollback boundary is deletion of
the new additive contract, tests, report, direction entry, and this OpenSpec
change before archival; no consumed artifact or runtime history is rewritten.

## Capabilities

### New Capabilities

- `noncombat-hierarchical-advantage-attribution-contract`: Defines
  trajectory-disjoint advantage provenance, exact shared-parameter gradient
  component accounting, deterministic synthetic evidence, future-registration
  observability requirements, and the no-authority boundary.

### Modified Capabilities

None.

## Impact

The change is additive under `analysis_scripts/`, `tests/`, `reports/`,
`docs/project_direction.md`, and this OpenSpec change. It may use CPU Torch on
caller-supplied synthetic tensors and modules, but it does not import or edit
the hierarchical experiment control plane/runtime, load a checkpoint or native
module, construct a simulator environment, access a seed, fit a model, or start
Slay the Spire. A later algorithm and experiment proposal must separately
select any baseline estimator and empirical registration. The synthetic
fixtures may depend on the checked-in hierarchical objective and family
distribution, but this change does not modify either capability.
