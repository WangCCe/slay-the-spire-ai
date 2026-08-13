## Why

The card-only policy completed 20 real policy-gradient chunks but changed at
most one of 175 fixed-probe greedy actions, while clipping and scorer-only
ablations ruled out two narrower optimizer explanations. The warm-start policy's
median two-stage margin near 4.9 leaves its softmax saturated, so a margin-
controlled training construction is needed before spending another long run.

## What Changes

- Restore the bound r7 card checkpoint, freeze its two hierarchical heads, and
  preserve its greedy ordering while dividing both base logits by fixed
  temperature `4.0`.
- Add one zero-initialized, bias-free residual projection to each frozen
  64-dimensional hidden representation; train only those 128 weights with a
  fresh Adam optimizer.
- Run a one-step lossless-replay gate first; require exact entry greedy
  preservation, valid probability/gradient accounting, and material fixed-probe
  function movement before any environment access.
- Only on gate pass, run a four-chunk candidate-only card policy-gradient pilot
  while native SimpleAgent owns all non-card decisions.
- Use already-consumed development seeds for training and terminal mechanism
  comparison; do not access fresh or protected cohorts in this change.
- Publish per-chunk action flips, margins, policy movement, outcomes, checkpoints,
  and a terminal proposal-readiness verdict.
- Do not tune temperature or thresholds after replay/outcome access, launch
  gameplay, load production checkpoints, qualify, or promote.

## Capabilities

### New Capabilities

- `noncombat-card-margin-controlled-training`: Fixed-temperature hierarchical
  card policy, replay sensitivity gate, bounded native-baseline training, and
  terminal behavior/value evidence.

### Modified Capabilities

None.

## Impact

This adds an experiment-only frozen-base residual policy, replay gate, training runner,
focused tests, and reports. It reuses the bound warm checkpoint, lossless replay,
native simulator adapter, Current card objective, and consumed development
schedule. CommunicationMod, live policy code, production checkpoints, protected
cohorts, and native SimpleAgent remain unchanged. Rollback discards the
experiment checkpoint and retains native SimpleAgent.
