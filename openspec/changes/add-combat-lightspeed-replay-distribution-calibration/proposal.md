## Why

The fresh guard-aware bootstrap comparison materially changed 22,175 bootstrap
actions yet degraded later-battle reward against both its raw LightSTS control
and production r16. The repository already contains two complete zero-update
production-r16 real-game replay snapshots totaling 7,685 transitions, but there
is no source-bound tool that compares those real RL-v2 transitions with an
equivalent frozen-r16 LightSTS collection before another simulator fit.

## What Changes

- Add a read-only replay-distribution calibration runner that validates
  complete weights-only schema-v1 or schema-v2 real checkpoint replay snapshots and collects a fixed,
  zero-epsilon frozen-r16 LightSTS corpus without optimizer construction or
  updates.
- Compare both sources within explicit floor strata using state, action-mask,
  executed-action, reward, terminal, card, potion, and relic support summaries.
- Publish deterministic source bindings, per-stratum descriptive deltas,
  support overlap, ranked mismatch signals, exclusions, and a manifest.
- Register and execute one fresh bounded POC against the committed complete r14
  and r15 replay snapshots.
- Keep gameplay, CommunicationMod, model fitting, training, OPE, policy-quality
  claims, mechanics-equivalence claims, packaging, qualification, and promotion
  outside this change.
- Success means the report is source-complete, deterministic on repeated
  in-memory inputs, covers at least two common floor strata with non-empty
  transitions from both sources, and ranks descriptive mismatches without
  granting downstream policy authority. It does not require small divergence.
- Rollback consists of removing the standalone runner, focused tests, spec, and
  reports; production runtime, checkpoints, and CommunicationMod configuration
  remain unchanged.

## Capabilities

### New Capabilities

- `combat-lightspeed-replay-distribution-calibration`: Source-bound descriptive
  comparison of real-game RL-v2 replay and frozen-parent LightSTS replay across
  common progression strata.

### Modified Capabilities

None.

## Impact

- Adds one offline analysis runner under `analysis_scripts/` and focused tests
  under `tests/`.
- Reads committed real replay checkpoints and the immutable LightSTS native
  module through existing safe checkpoint and bridge APIs.
- Reuses the existing production-r16 simulator shadow only as a frozen behavior
  model and writes new report artifacts under `reports/`.
- Does not modify production gameplay code, checkpoint bytes, optimizer state,
  Steam, or CommunicationMod.
