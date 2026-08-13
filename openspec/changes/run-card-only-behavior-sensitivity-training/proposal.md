## Why

The r7 card-only pilot completed four real policy-gradient updates, but the
final policy changed too few greedy actions to change any development-cohort
outcome. Training also spent half of every residual chunk rerunning a frozen
native control that did not participate in the candidate gradient.

## What Changes

- Add an exact candidate-only card rollout and cross-fitted update path so each
  training environment access contributes candidate experience.
- Continue from the bound r7 `checkpoint_004` for exactly 16 additional
  candidate optimizer steps on the same 64 already-consumed development seeds.
- Keep the existing four-fold baseline, formal reward, 56-pair support floor,
  eight-pair Courier censor bound, transactional checkpoint restore, and fixed
  5%-95% family-coverage stop.
- Measure exact-action flips, family flips, and policy movement against the r7
  entry checkpoint on the fixed validation probe after every update.
- Run native control only once and frozen candidate only once at the terminal
  comparison, with at most 1,152 total environment accesses and eight charged
  hours.
- Require at least four fixed-probe exact-action flips without family collapse,
  plus supported-pair floor and victory non-inferiority, before permitting a
  separate fresh-evaluation proposal.
- Do not access protected or fresh cohorts, tune after observing results, run
  live gameplay, alter CommunicationMod, or expose exploratory checkpoints to
  production loading.

## Capabilities

### New Capabilities

- `noncombat-card-only-behavior-sensitivity-training`: Defines candidate-only
  residual collection, continuation identity, behavior diagnostics, bounded
  execution, terminal comparison, and rollback semantics.

### Modified Capabilities

None.

## Impact

The change affects the non-combat empirical-successor runtime, a new bounded
training runner, focused tests, OpenSpec artifacts, and simulator-only reports.
Success means 16 additional optimizer steps complete, at least four of the 175
fixed probe actions change without concentration, and the final supported
candidate comparison is non-inferior to native control. Failure or interruption
restores the last complete exploratory checkpoint and leaves native SimpleAgent
as the effective policy. No live loader, game process, protected seed inventory,
or production checkpoint is changed.
