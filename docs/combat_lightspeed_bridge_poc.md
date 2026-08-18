# Combat LightSTS Bridge POC

## Verdict

The source-only POC is ready to support a separately scoped live-divergence
calibration design. It is not authorized to generate training replay, load a
model, train, qualify, or promote a combat policy.

The fixed `0..31` seed calibration observed:

- 32 completed seeds.
- 451 supported RL v2 states and 451 executed actions.
- 451 clone-isolation checks and 451 deterministic-successor checks.
- 351 `play_card` actions and 100 `end_turn` actions.
- 31 `player_victory` terminal combats.
- One explicit `unsupported_input_state:CARD_SELECT` boundary.
- Zero mapping errors and zero decision-bound truncations.

The source-bound evidence is in
`reports/combat_lightspeed_bridge_poc_20260819/`. The manifest binds the report
and summary, while the report binds the adapter sources, native module,
compiled simulator sources, simulator commit, and submodules.

## Next Gate

Before simulator combat transitions can enter replay generation or fitting:

1. Define a source-bound import or replay surface for matched real battle starts.
2. Replay matched legal actions in LightSTS and the game, comparing legality and successor state.
3. Pre-register material divergence thresholds and classified failure handling.
4. Add explicit support or exclusion rules for `CARD_SELECT` states.

Until that gate passes, LightSTS combat evidence demonstrates bridge
determinism and mapping coverage only. It is not mechanics-equivalence or
policy-quality evidence.
