## Why

The event-option ranker passed all fixed development gates, improving mean and
p95 regret while holding maximum regret constant. Its selected confidence gate
collapsed to raw ranker behavior, so one disjoint no-training shadow cohort is
required before considering any integration or broader RL use.

## What Changes

- Load the exact manifest-bound event model from the completed training report.
- Collect one fresh fixed event-option outcome partition on disjoint seeds.
- Compare the bound selected policy with Current using fixed support, mean,
  p95, maximum-regret, and correction/regression gates.
- Publish canonical per-source predictions, event support, identities, and a
  terminal replicate/no-replicate verdict.
- Do not fit, tune, retry, promote, or launch gameplay.

## Capabilities

### New Capabilities

- `noncombat-event-option-ranker-shadow-evaluation`: Bound-model, no-training,
  disjoint simulator shadow evaluation and terminal replication gates.

### Modified Capabilities

None.

## Impact

This adds one offline evaluator, focused tests, a spec, and one report. It reads
the committed event model and registered native/Current inputs; no production
checkpoint, CommunicationMod configuration, or live policy behavior changes.
Rollback removes the evaluator and report.
