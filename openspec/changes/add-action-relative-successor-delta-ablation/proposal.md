## Why

The real-context-weighted current-state classifier failed broadly on 10,688
fresh rows: 2,004 interventions produced 481 severe harms, and even evidence
margin at least 6 reached only `0.458` precision. The bound postmortem shows
that floor, HP, action family, item vetoes, and threshold changes cannot isolate
safety; the missing information is the state caused by the candidate relative
to the state caused by the guard action.

## What Changes

- Collect one immutable action-relative corpus from new seeds that preserves
  the existing paired continuation returns and additionally records the
  one-step mapped successor, immediate reward, and terminal disposition for
  every canonical guard and candidate branch.
- Use fit seeds `275000..275767`, calibration seeds `275768..276023`, and fresh
  evaluation seeds `277000..277255`, with battle indices `0,3,6,9,10` and at
  most two retained source states per profile.
- Recompute the existing real-context support evidence and close before fitting
  if the new current-state rows do not pass the unchanged coverage, ESS,
  concentration, balance, legality, and seed-isolation gates.
- Run one paired CPU ablation on the same rows and fixed weighted recipe: a
  current-state item-semantic control and a successor-delta candidate that adds
  frozen candidate/guard successor-latent difference, immediate-reward
  difference, and disposition features.
- Keep architecture width, labels, Adam `0.001`, 4,096 updates, class/ranking
  sampling counts, loss, weighted 95th-percentile calibration, and offline
  thresholds fixed. Load fresh evaluation only after both arms and thresholds
  are frozen; do not sweep or retry after metric access.
- Grant a later fresh matched LightSTS policy gate only if the successor arm
  passes every original raw-safety and weighted-value gate. Relative improvement
  without a hard pass is descriptive representation evidence only.

Success is a source-bound successor representation that passes at least 30 raw
interventions, weighted precision `0.65`, weighted mean selected advantage
above `0.18881003558635712`, weighted regret below `3.1811342239379883`, and
zero raw severe, illegal, or forbidden selections. A secondary signal verdict
requires at least `0.10` higher weighted precision, at least `0.10` higher
weighted mean selected advantage, and at least 50% lower raw severe-harm rate
than the paired control, but grants no policy authority.

There is no new live evidence in this change. Production r16 remains unchanged
and is the rollback boundary. Non-goals are threshold or item-veto tuning,
arbitrary real-state import, online training, CommunicationMod, Slay the Spire,
production checkpoint writes, qualification, promotion, or exact simulator
equivalence.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-successor-delta-ablation`: Immutable one-step
  branch-successor collection, fixed paired representation ablation, fresh
  safety/value decisions, and fail-closed authority boundaries.

### Modified Capabilities

None.

## Impact

The change adds a development-only native corpus runner, successor-feature
encoder/head, focused tests, source-only registrations, one bounded corpus, two
fixed CPU fits, and immutable reports. It reuses the existing registered native
module, simulator-only production-r16 shadow, items export, r14/r15 real replay
target, current context cells, paired-return recipe, action-relative labels,
and offline gates. It changes no production runtime, action space, reward,
CommunicationMod configuration, production checkpoint, or live policy.
