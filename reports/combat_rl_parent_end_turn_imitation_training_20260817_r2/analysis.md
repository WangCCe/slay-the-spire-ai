# Targeted Parent-EndTurn Imitation Training r2

## Decision

Retain the promoted parent and stop this weight-0.2 training recipe. The five-game
smoke completed cleanly, but the output checkpoint failed the preregistered
directional guard: its positive-energy EndTurn share on the final replay was
`0.653303`, above the promoted parent's `0.639500`.

This training context has no promotion authority. It also does not authorize an
additional batch because the preregistration required every offline rule to pass.

## Training Evidence

- Exactly 5 games completed, adding 1,193 transitions and 298 optimizer steps.
- The final checkpoint is finite and remains close to the promoted parent
  (`0.010102` whole-model relative L2).
- The frozen parent anchor exactly matches the promoted parent.
- The targeted objective was active at the final update: loss `2.684663` across
  55 eligible parent-EndTurn correction states.
- Runtime evidence contains no action failures, replay rejections, tracebacks, or
  critical errors during the experiment window.
- The production CommunicationMod configuration was restored and no training or
  game processes remain.

## Offline Comparison

The output retained acceptable parent agreement (`0.905273`, gate `>= 0.88`) and
improved Smooth L1 from `3.778944` to `2.825340` (gate `<= 1.1x` parent). It also
changed `0.7443%` of the 1,881 targeted correction states to their executed
non-EndTurn action, versus `0%` for the parent.

That small targeted movement was outweighed by other policy drift: positive-energy
EndTurn predictions increased from 1,946 to 1,988 of 3,043 states. Continuing this
recipe would therefore spend more live games in the wrong aggregate direction.

## Next Step

Run a bounded offline training sweep at approximately the observed 298-update
exposure, varying only the targeted imitation weight. Select a successor only if
it lowers positive-energy EndTurn share below the parent while preserving parent
agreement and TD fit. Do not launch another live training batch from this output.
