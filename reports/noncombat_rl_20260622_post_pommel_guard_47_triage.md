# Post-Pommel Guard 47-Run Triage

## Batch

- Cutoff: `1782114784`
- Verifiable AI `.run` records: 47
- Victories: 0
- Best floor: 33
- Average floor: 21.0
- Batch log status: `Max games reached (50); exiting`

## Noncombat Decision Loop

- Report: `reports/noncombat_rl_decision_loop_post_pommel_guard_47.md`
- Samples: 3157
- Category coverage: card_reward=455, event=578, route=1938, shop=186
- Complete samples: 3050
- Matched outcomes: 717
- Promotion status: allowed, but formal non-combat RL remains blocked by the training guard.

The prior Pommel/Armaments and Shrug/Twin reward mismatches did not recur as a strong new card-reward cluster. The remaining policy-ready mismatches are low-count or route-diagnostic, so they are not enough for another reward or route policy patch by themselves.

## Potion Evidence Cross-Check

Run records still report zero entries in `potions_floor_usage` across this batch, but that field is not reliable enough for code changes by itself:

- `.run` potion usage total: 0
- `.run` potions obtained total: 189
- Decision trace `PotionAction` count since cutoff: 207
- Decision trace boss `PotionAction` count: 49
- `ai_debug.log` includes `[POTION_GUARD] Using ...` and `[CALLBACK] Got action: PotionAction`

Conclusion: do not patch a "never uses potions" bug from `.run` records alone. Trace/log evidence proves potion actions were issued.

## Failure Shape

- Act 1 boss deaths: 25/47
  - Hexaghost: 12
  - The Guardian: 10
  - Slime Boss: 3
- Act 2 deaths: 20/47
  - Automaton: 4
  - Collector: 4
  - Cultist and Chosen: 3
  - Sentry and Sphere: 3

Act 1 boss deaths were not caused by route aggression: almost all routes avoided elites. The stronger split is boss readiness and combat execution:

- Runs surviving Act 1 boss: average deck size 19.35, attack additions 6.65, pre-boss HP 74.2
- Runs dying to Act 1 boss: average deck size 14.8, attack additions 3.68, pre-boss HP 61.64

## Actionable Bug

Boss combat trace showed repeated `EndTurnAction` decisions while energy, playable cards, and `available_commands=["play", ...]` were still present. The existing wasteful-end guard only checked `game.play_available`, which is not always present on live state objects even when trace serialization reports `available_commands`.

Fix target:

- Add a `CombatRLAgent._command_available(...)` helper that prefers `available_commands` and falls back to legacy booleans.
- Use it for wasteful-end detection and current `PlayCardAction` playability validation.

Regression:

- `test_wasteful_end_turn_uses_available_commands_when_play_flag_missing`

Focused verification:

- `tests/test_combat_rl_guards.py::test_wasteful_end_turn_uses_available_commands_when_play_flag_missing`: passed
- `tests/test_combat_rl_guards.py`: 137 passed
- Full pytest: 2164 passed
