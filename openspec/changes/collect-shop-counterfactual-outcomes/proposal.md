## Why

The native adapter now fails closed around known-invalid Courier and potion
transactions, but no action-level shop outcome corpus or shop ranker training
has ever run. A bounded supported-domain collection is the shortest way to
decide whether shop learning has usable signal.

## What Changes

- On fixed fresh seeds `95000..95063`, visit supported A0 shop states and
  evaluate every legal shop action under frozen Current-policy continuation.
- Treat Courier support blockers and other registered simulator boundaries as
  explicit censors; abort on unknown blockers or incomplete action rows.
- Bind source snapshot, candidates, Current action, branch outcomes, model-free
  return, action kind, deterministic replay, native module, and source commit.
- Require at least 24 complete shop states, 12 informative states, four action
  kinds, and eight exact replays for a learning proposal.
- Do not fit a model, train, load production checkpoints, launch gameplay,
  retry the cohort, or change thresholds in this change.
- Roll back by retaining Current and discarding the source-only corpus.

## Capabilities

### New Capabilities

- `noncombat-shop-counterfactual-outcomes`: Supported-domain shop action branch
  collection, censor accounting, replay proof, and learning-signal verdict.

### Modified Capabilities

None.

## Impact

This adds one offline analysis runner, focused tests, OpenSpec artifacts, and a
bounded native report. It reuses the bound A0 adapter, Current bridge, strict
primary return, and existing counterfactual continuation. CommunicationMod,
live policy, production checkpoints, and protected seed inventories are not
accessed.
