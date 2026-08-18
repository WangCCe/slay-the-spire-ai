# Promoted-r15 successor combat promotion

## Decision

Promote frozen r16 as the production combat baseline for bounded five-game
evaluation launches. Keep the prior r15 production configuration as the fixed
rollback artifact.

## Basis

- R16 passed the fixed full-return, one-step, parent-agreement, off-target, and
  positive-energy End Turn guards on consumed replay r6/r8/r9/r10.
- On untouched r12, full-return SmoothL1 improved from `44.324028` to
  `44.299255`, one-step SmoothL1 improved from `4.172118` to `4.154759`, parent
  agreement was `99.4035%`, and positive-energy End Turns fell from 1,815 to
  1,804.
- The matched live gate passed every preregistered condition: one candidate
  floor win, zero parent floor wins, 19 ties, and 493 versus 476 total floors.
  R16 entered Act 2 13 times versus 12 and reached the Act 2 boss seven times
  versus six.
- Both live arms completed 20/20 games without native recovery, policy runtime
  failures, or invalid seed ordering.

## Scope

Production remains evaluation-only with epsilon zero, conservative routing,
and a five-game launch bound. It loads only frozen r16 weights and does not load
optimizer or replay state.

Nineteen of 20 live pairs tied and neither arm won a run. This is a conservative
low-risk baseline replacement, not evidence of a large effect or completion of
the first-victory goal.

## Next iteration

Use consumed r12 plus older consumed replay for one bounded successor fit before
spending another fresh cohort. Require the same cross-replay action guards; only
then collect a new zero-update replay under promoted r16 for untouched
confirmation. This keeps the next cycle weighted toward actual training.
