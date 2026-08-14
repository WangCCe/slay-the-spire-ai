# Combat RL Legacy Replay Collection R1

## Result

The resume repair worked in live gameplay. Ten games collected 1,565 accepted
transitions while preserving the entry online weights, target weights, Adam step,
and epsilon exactly. The final schema-2 checkpoint is a valid continuation
artifact with `episode=15`, `learning_starts=4096`, and no truncated replay.

## Integrity

- Entry and final online state hash: `d9b577...20f60c`
- Entry and final Adam step: `2679`
- Replay: `1565 / 4096`; 2,531 transitions remain before learning
- Episode count: `5 -> 15`, aligned with `ep15_steps13413`
- Replay rejection, episode-close failure, checkpoint-save failure, RL-agent
  failure, and NaN matches: all zero
- CommunicationMod error log growth: zero bytes
- Atomic checkpoint temporary files remaining: zero

## Gameplay

Floors were `[20, 16, 41, 33, 16, 16, 16, 16, 28, 16]` (mean 21.8).
Four games entered Act 2, two reached the Act 2 boss, one entered Act 3, and none
won. These are collection outcomes, not policy-quality evidence: the online
policy was unchanged and actions still used training exploration plus expert mix.

## Next Step

Continue from `rl_combat_model_ep15_steps13413.pth` in one bounded training batch.
At the observed 156.5 transitions per game, approximately 17 additional games
are needed to cross the 4,096-transition threshold. Use an 18-game cap so the
final portion of the batch performs real optimizer updates, then run one fresh,
preregistered, zero-epsilon matched gate against the frozen entry policy.
