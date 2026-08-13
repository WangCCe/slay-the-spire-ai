## Why

The fixed event-option outcome POC produced 122 complete sources, 49 informative
sources, 21 event ids, and 16 exact replays, so event decisions now have enough
simulator-backed action credit to justify one learning experiment. Current is
already outcome-maximizing on 80.33% of sources including ties, so the experiment
must test a conservative learned override rather than replace Current blindly.

## What Changes

- Collect fresh, disjoint train and single-use development event partitions with
  state/candidate features and terminal branch returns.
- Fit a bounded state-conditioned pairwise ranker using train data only.
- Select epoch and a conservative Current-override margin using a train-internal
  tune split before any development access.
- Compare raw, gated, untrained, and Current policies on development mean regret,
  maximum regret, unique-best accuracy, pairwise accuracy, and action changes.
- Publish a fixed go/no-go verdict and exact source/data/model identities.
- Do not launch gameplay, alter production policy, or promote the model.

## Capabilities

### New Capabilities

- `noncombat-event-option-counterfactual-ranking-training`: Bounded event-option
  ranker training, conservative Current fallback, single-use development, and
  policy-quality gates.

### Modified Capabilities

None.

## Impact

The change adds one offline training runner, focused tests, an OpenSpec contract,
and one report directory. It reuses the exact API v3 projection, registered
native simulator, frozen Current continuation, and CPU ranker; gameplay,
CommunicationMod, production checkpoints, and live policy behavior are
unchanged. Rollback removes the runner and artifacts.
