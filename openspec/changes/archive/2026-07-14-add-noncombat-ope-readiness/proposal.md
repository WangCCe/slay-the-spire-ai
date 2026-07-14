## Why

The post-review B2 batch now passes the known-propensity collection gate with
25 joined trajectories and 230 confirmed decisions, but OPE remains unsafe:
there is no versioned reward horizon, target-policy distribution contract,
trajectory-level weighting rule, censoring policy, or overlap/variance gate.
Defining those boundaries now prevents repeated per-decision outcomes or a
small number of rare shop alternatives from being mistaken for policy-value or
causal evidence.

## What Changes

- Add an offline-only OPE-readiness audit that consumes confirmed
  known-propensity samples and groups every calculation by exact run trajectory.
- Require an explicit, hash-bound target-policy distribution for every audited
  decision; deterministic Current, Bottled, or pilot labels alone are not
  accepted as target probabilities.
- Add a versioned outcome contract that fixes the terminal run horizon,
  supported outcome channels, complete-run requirement, and fail-closed
  handling for missing, ambiguous, inconsistent, or mixed trajectory outcomes.
- Report exact behavior/target support, zero-support rows, trajectory importance
  weights, effective sample size, weight concentration, outcome variation, and
  identity-policy self-checks without claiming uplift.
- Emit deterministic JSON and Markdown readiness artifacts whose success metric
  is reproducible trajectory accounting and explicit blockers. The B2 proof of
  concept must reconstruct 25 trajectories and remain blocked for candidate
  policy OPE, formal non-combat RL, and live promotion.
- Keep training, policy optimization, causal estimates, gameplay policy edits,
  CommunicationMod configuration, checkpoints, and live promotion out of scope.
- Keep the rollback boundary offline: removing the audit module, tests, and
  generated reports restores the previous behavior without changing gameplay
  or production artifacts.

## Capabilities

### New Capabilities

- `noncombat-ope-readiness`: Defines trajectory, outcome, target-policy,
  overlap, weight, effective-sample-size, deterministic-report, and fail-closed
  readiness requirements for offline non-combat OPE evidence.

### Modified Capabilities

- `noncombat-rl-decision-loop`: Connects a qualified known-propensity dataset to
  the separate reward and estimator-readiness audit while preserving formal-RL,
  causal, training, and live-promotion blocks.

## Impact

- Adds an offline analysis module and focused tests under `analysis_scripts/`
  and `tests/`.
- Adds deterministic target-policy/outcome/readiness artifact schemas and a B2
  proof-of-concept report under `reports/`.
- Updates only OpenSpec contracts for the non-combat decision loop; no live
  agent, launcher, checkpoint discovery, CommunicationMod protocol, or gameplay
  decision path changes.
- Uses the standard library and existing canonical sample schemas; no new
  runtime dependency is required.
