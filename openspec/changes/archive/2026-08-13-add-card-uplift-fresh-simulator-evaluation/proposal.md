## Why

The frozen 79-parameter card-uplift residual passed train cross-fit,
development, and the independent reserved audit, but those state-level results
do not show whether its card choices improve complete simulator runs. A fresh
paired whole-run evaluation is the next bounded test before any live adapter.

## What Changes

- Preserve failed r1 seeds `90000..90063` as consumed and register untouched
  seeds `90100..90163` for the sole successor paired simulator evaluation.
- Compare a frozen r7-plus-residual candidate against the native baseline in
  independent environments on every seed.
- Let the candidate intervene only at ordinary four-action card rewards; all
  other candidate and all control decisions use the native baseline.
- Publish paired terminal-floor, victory, intervention, support, legality, and
  deterministic bootstrap evidence under fixed noninferiority gates.

## Capabilities

### New Capabilities

- `noncombat-card-uplift-fresh-simulator-evaluation`: Defines the frozen
  card-only paired rollout, fresh cohort, metrics, gates, isolation, and result
  authority.

### Modified Capabilities

None.

## Impact

- Adds one bounded simulator evaluator, one registration, focused tests, and a
  result report.
- Consumes at most 64 paired seeds and 128 complete episode rollouts, with a
  two-hour wall-clock ceiling.
- Does not fit or tune a model, start the game or CommunicationMod, modify a
  production checkpoint, or promote the candidate. Rollback remains the native
  baseline and the frozen r7 checkpoint remains unchanged.
