## Why

The clipping ablation ruled out baseline lower clipping as a material cause of
weak card-policy behavior sensitivity. Function-space evidence instead shows
that almost all parameter L2 movement accumulates in the large hidden matrices,
so the next question is whether direct scorer-only optimization can retain the
useful one-step policy movement while avoiding representation drift.

## What Changes

- Collect one 64-seed consumed-development cohort from exact checkpoint `004`.
- Publish a deterministic, bounded, lossless replay artifact containing only the
  stored decisions, features, candidates, rewards, outcomes, and post-collection
  generator states needed for offline card optimizer updates.
- Decode the replay from disk before any optimizer step; do not update from the
  live in-memory rollout objects.
- Compare branch A using current full-model Adam with branch B using the exact
  scorer parameter subset and corresponding sliced Adam state.
- Require branch A to reproduce historical checkpoint `005` model, optimizer,
  and bootstrap state before interpreting branch B.
- Persist compact function/gradient/parameter evidence and stop after one step.

Success means scorer-only retains at least 80% of branch A's fixed-probe mean
joint total variation from entry while every hidden parameter remains byte
identical and neither branch collapses. Failure rolls both branches back to
checkpoint `004` and does not authorize a longer run.

## Capabilities

### New Capabilities

- `noncombat-card-only-scorer-optimizer-replay-ablation`: Defines the durable
  replay format, exact current-step reproduction, scorer-only optimizer slice,
  one-step comparison, and downstream authority boundary.

### Modified Capabilities

None.

## Impact

The change adds an experiment-scoped replay codec, scorer optimizer helper,
runner, focused tests, one replay artifact, local branch checkpoints, and compact
reports. It does not change production policy loading, CommunicationMod, game
behavior, rewards, architecture, protected cohorts, or native SimpleAgent
rollback behavior.
