## Why

The provenance-bound `sts_lightspeed` adapter now demonstrates a deterministic
offline four-category environment, but its declared first-candidate baseline
wins 0/20 runs and the adapter POC grants no training authority. One
pre-registered simulator-only smoke is needed to determine whether the existing
candidate-ranker representation can support a legal, reproducible policy-
gradient loop before considering formal non-combat RL.

## What Changes

- Add a registered, CPU-only simulator-training smoke with exact adapter/source
  identity, disjoint fixed train and holdout seeds, finite episode/update/time
  bounds, and one allowed run with no hyperparameter sweep or adaptive retry.
- Add a versioned simulator policy feature view that removes seed, terminal
  outcome, provenance, and baseline-history leakage while retaining canonical
  state and legal candidate data.
- Train a candidate-masked policy with a training-only return based on
  non-negative floor progress plus a simulator victory bonus. Bottled labels,
  live outcomes, OPE weights, and gameplay heuristics do not enter the reward.
- Evaluate the frozen initial and trained greedy policies on the same untouched
  holdout seeds, reporting paired terminal-floor and victory differences,
  candidate legality, four-category coverage, resource use, and a pre-declared
  confidence interval without selecting a favorable rerun.
- Reproduce the smoke from the same input and require canonical metrics,
  predictions, model weights, and report identities to match before calling the
  pipeline demonstrated.
- Publish fail-closed JSON and Markdown evidence with separate structural and
  heldout-signal verdicts. A passed smoke may justify only another reviewed
  proposal; formal RL, live loading, qualification, OPE, gameplay, and promotion
  remain unauthorized.

The implementation success metric is deterministic completion within the
registered bounds with 100% candidate legality, disjoint seeds, complete source
identity, and an honest paired holdout result. A positive policy signal requires
the pre-registered lower confidence bound for paired terminal-floor improvement
to exceed zero; absence of that signal is a valid `quality_not_demonstrated`
result, not a reason to tune or rerun.

Non-goals are simulator/live mechanics equivalence, formal or long-running RL,
live gameplay evaluation, policy promotion, Bottled imitation, reward tuning,
hyperparameter search, and changes to CommunicationMod or production
checkpoints. Rollback is deletion of the isolated smoke code and report
artifacts; the live runtime, external simulator checkout, and existing evidence
inventories remain untouched.

## Capabilities

### New Capabilities

- `noncombat-simulator-training-smoke`: Registered simulator-only rollout,
  training, reproducibility, paired holdout evaluation, verdict, and authority
  contracts for one bounded non-combat RL smoke.

### Modified Capabilities

- `noncombat-simulator-adapter`: Permit a separately reviewed bounded smoke to
  invoke the offline adapter while preserving provenance and every live/formal
  authority guard.
- `noncombat-rl-decision-loop`: Keep simulator rewards, trajectories, returns,
  models, and evaluation metrics in a separate evidence class that cannot
  upgrade live OPE, supported outcomes, or promotion readiness.

## Impact

- Adds offline analysis/training modules, registration and report schemas,
  focused tests, a frozen smoke input, and isolated report/model artifacts.
- Reuses the optional native adapter and existing PyTorch candidate-ranker
  architecture; it adds no live startup dependency and no automatic model
  discovery path.
- Reads the explicit local `sts_lightspeed` checkout and native module only when
  the smoke command is invoked. It does not modify the external checkout.
- Leaves CommunicationMod configuration, gameplay launchers, combat
  checkpoints, live decision traces, `.run` files, and known-propensity evidence
  unchanged.
