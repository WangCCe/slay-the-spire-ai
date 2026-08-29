## Why

The consumed r2 first-successor corpus closed before fitting because fresh
real-context coverage was `0.803383`, fresh ESS was `243.204`, and late-floor
support missed the unchanged gates. A read-only projection over existing,
seed-disjoint LightSTS corpora found that a targeted battle-3 and battle-10
supplement can address those failures with materially more margin than another
uniform five-battle collection.

No live-game evidence is claimed for this change. Its evidence is limited to
the consumed r2 corpus and historical development-only LightSTS context rows;
live gameplay remains a later validation stage if a separately fitted candidate
earns it.

## What Changes

- Add a source-bound supplemental first-successor corpus collector that reuses
  the r2 schema and immutable r16/native/items/real-replay bindings without
  modifying or retrying the consumed r2 execution.
- Register a fresh, collision-free, partition-isolated cohort biased toward
  battle 3 for train support and battles 3 and 10 for fresh support. The
  preregistered budget is based on the stable projection point: 384 train
  battle-3 profiles, 1,024 fresh battle-3 profiles, and 1,536 fresh battle-10
  profiles.
- Merge only source states and complete supported candidate pairs from the
  supplement with the immutable r2 fit, calibration, and fresh partitions, then
  rerun the unchanged real-context support and integrity gates.
- Stop and publish a development-only report before optimizer construction if
  any unchanged support gate still fails. Passing support permits only a later,
  separately registered weighted fit using the existing ablation contract.
- Keep gameplay, CommunicationMod, production checkpoint loading or writing,
  policy evaluation, qualification, and promotion outside this change.

Success is a merged corpus that passes every existing context-support and
integrity condition with immutable provenance and disjoint seeds. The rollback
boundary is the new supplement output: the existing r2 artifacts and runner
remain unchanged, and a failed or interrupted supplement is closed rather than
retried under the same identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-action-relative-successor-delta-ablation`: Add a bounded,
  fresh-heavy context-support supplement and immutable merged-support decision
  before any successor-delta fitting.

## Impact

- Affected code: a new focused analysis runner, its tests, and the existing
  first-successor corpus validation and context-weight helpers reused as public
  implementation dependencies.
- Affected artifacts: one new registration/preflight, supplemental corpus
  partitions, merged support report, and immutable publication manifest under a
  new report identity.
- Runtime: one bounded CPU LightSTS collection using the already hash-bound
  native adapter; no game process or CommunicationMod session is required.
- Compatibility: no production API, checkpoint, gameplay policy, or consumed
  report is changed.
