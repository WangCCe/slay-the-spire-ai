## Why

The max-pooled action-family distribution is mathematically valid, but a
read-only POC over the frozen scored rows shows that its integration semantics
are not interchangeable. Joint-probability argmax changes 24.2% of trained
canary card-reward choices and 57.3% of trained canary shop choices, while
event and route have one family and therefore zero family entropy. These effects
must be measured and bounded before any training objective or deterministic
evaluation rule is proposed.

## What Changes

- Add a strict read-only audit that consumes only the checked-in terminal
  collapse audit plus the exact `training_rows.json` and `evaluation.json`
  bytes already bound by that audit.
- Revalidate source size and SHA-256, canonical JSON, terminal canary-stop
  identity, unaccessed holdout wrapper, row counts, candidate identities,
  score alignment, and exact all-false authority before analysis.
- Apply the checked-in max-pooled distribution implementation to every frozen
  training, initial-canary, and trained-canary diagnostic row, with flat
  candidate softmax as the descriptive counterfactual control.
- Report category and phase counts, kind sets, flat versus hierarchical family
  mass, family/conditional/joint entropy, score-argmax versus joint-probability-
  argmax transitions, exact one-family fallback, tie boundaries, and card-
  reward/shop concentration effects.
- Publish canonical JSON and deterministic Markdown. Success means every input
  and mathematical invariant recomputes, output reproduction is byte-identical,
  and conclusions distinguish stochastic distribution, deterministic
  selection, and entropy-objective semantics.
- Do not open checkpoints or any unlisted artifact, inspect holdout rows, replay
  a seed, load native modules, construct an environment, train or select a
  model, choose an entropy coefficient, modify the distribution helper, launch
  gameplay, or authorize an experiment. Rollback is deletion of this additive
  audit, tests, reports, docs, and OpenSpec change; source evidence remains
  byte-for-byte unchanged.

## Capabilities

### New Capabilities

- `noncombat-action-family-counterfactual-audit`: Defines strict frozen-score
  source binding, max-pooled counterfactual metrics, deterministic publication,
  interpretation limits, and no-authority boundaries.

### Modified Capabilities

None.

## Impact

The change adds one analysis script, focused tests, two deterministic report
files, project-direction documentation, and OpenSpec artifacts. It reads but
does not modify the existing collapse audit and its two hash-bound source
artifacts. No runner, ranker, policy input, registration, checkpoint,
CommunicationMod configuration, simulator, production policy, or gameplay path
is changed.
