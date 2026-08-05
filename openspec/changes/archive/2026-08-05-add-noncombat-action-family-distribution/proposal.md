## Why

The consumed state-conditioned simulator experiment collapsed to selecting the
`take` family for every trained canary card reward. Its terminal source-only
audit found both a structural candidate-count pressure and learned score
amplification: three or more `take` candidates compete against one `skip`,
while candidate entropy materially overstates action-family diversity. Before
another experiment can be considered, the repository needs a source-only
distribution boundary whose family probabilities and entropy semantics can be
proved independently of simulator outcomes.

## What Changes

- Add an additive CPU-only policy-distribution helper that groups complete legal
  candidates by their validated `kind` and factorizes probability into an
  action-family distribution and a conditional candidate distribution.
- Select and document one cardinality-normalized family aggregation rule after
  comparing max pooling, log-mean-exp pooling, and a separate learned family
  head against explicit mathematical and interface constraints.
- Expose candidate log probabilities plus separate family, conditional, and
  joint entropy values suitable for a later independently registered training
  design.
- Add synthetic regressions for normalization, equal-score cardinality bias,
  family-mass duplicate invariance where supported by the selected rule,
  permutation behavior, single-family fallback, finite gradients, and fail-
  closed inputs.
- Publish a deterministic source-only design report. Success means all claimed
  invariants are directly reproduced; it does not mean the intervention
  improves policy quality or prevents empirical collapse.
- Do not edit or rerun a consumed experiment, load native modules, access a
  seed or holdout, train or select a model, set entropy coefficients, launch
  gameplay, or grant formal-RL, qualification, loading, or promotion authority.
  Rollback is deletion of the additive helper, tests, report, and this change;
  no production or empirical artifact is modified.

## Capabilities

### New Capabilities

- `noncombat-action-family-distribution`: Defines the source-only action-family
  probability factorization, entropy decomposition, invariants, diagnostics,
  and no-authority boundary.

### Modified Capabilities

None.

## Impact

The change is limited to a new module under `analysis_scripts/`, focused tests,
a deterministic report, project-direction documentation, and OpenSpec
artifacts. Existing rankers, simulator runners, registrations, checkpoints,
production policy paths, CommunicationMod configuration, and native modules
remain unchanged.
