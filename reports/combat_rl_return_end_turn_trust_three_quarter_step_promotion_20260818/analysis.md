# Three-quarter-step End Turn trust combat promotion

## Decision

Promote frozen r15 as the production combat baseline for bounded five-game
evaluation launches. Keep the prior r8 production configuration as the fixed
rollback artifact.

## Basis

- R15 passed the fixed full-return, one-step, parent-agreement, off-target, and
  positive-energy End Turn guards on consumed replay r6/r8/r9/r10.
- On untouched r11, full-return SmoothL1 improved from `43.258408` to
  `43.217285`, one-step SmoothL1 improved from `3.903554` to `3.878391`, parent
  agreement was `99.2188%`, and positive-energy End Turns fell from 2,018 to
  2,004.
- The matched live gate passed every preregistered condition: one candidate
  floor win, zero parent floor wins, 19 ties, and 478 versus 475 total floors.
  R15 entered Act 2 11 times versus 10; both arms reached the Act 2 boss seven
  times and entered Act 3 once.
- Both live arms completed 20/20 games without native recovery, policy runtime
  failures, or invalid seed ordering.

## Scope

Production remains evaluation-only with epsilon zero, conservative routing,
and a five-game launch bound. It loads only frozen r15 weights and does not load
optimizer or replay state.

Nineteen of 20 live pairs tied and neither arm won a run. This is a conservative
low-risk baseline replacement, not evidence of a large effect or completion of
the first-victory goal.

## Next iteration

Use consumed r11 plus older consumed replay for one bounded successor fit before
spending another fresh cohort. Require the same cross-replay action guards; only
then collect a new zero-update replay under promoted r15 for untouched
confirmation. This keeps the next cycle weighted toward actual training.
