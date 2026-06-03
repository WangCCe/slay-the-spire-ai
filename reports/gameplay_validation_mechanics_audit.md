# Gameplay Validation Mechanics Audit

## Round 1 - 2026-06-03

- Preflight: git clean at `d306cd8 Unify combat ending player HP reads`.
- Baseline: `D:\anaconda\envs\stsai\python.exe -m pytest -q --basetemp C:\Users\20571\Documents\Codex\2026-06-03\d-pycharmprojects-slay-the-spire-ai\.pytest-basetemp` -> 1453 passed before changes.
- Validation: CommunicationMod ran `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance` with Windows Python.
- Outcome: no Ironclad `victory=true`; AI markers `1780450800` through `1780452924`; latest visible run `1780452921.run` died at floor 16 to Hexaghost.
- Failure type: lethal-sequence execution drift during RL energy-guard fallback takeover. A proven sequence could be planned, but `OptimizedAgent` invalidated the cached sequence after the first card left hand, replanned mid-turn, and could abandon the remaining lethal line.
- Fix: keep executing cached combat sequences when the next planned action is still available, and advance `current_action_index` after returning a newly planned first action.
- Regression: `test_optimized_agent_continues_cached_sequence_after_played_card_leaves_hand`.
- Verification after fix: focused related tests `56 passed`; full pytest `1454 passed`.
- Next candidate: inspect post-fix bounded validation for remaining Act 1 boss deaths and late Act 2 boss deaths, especially low-HP turns where fallback selects zero-damage setup cards or Havoc before lethal/defense.

## Round 2 - 2026-06-03

- Preflight: git clean at `c35d6df Penalize lethal current combat lines`.
- Baseline: full pytest with an isolated `STS_AI_LOG_FILE`, disabled pytest cache, and unique basetemp -> 1455 passed before changes.
- Validation: controlled CommunicationMod restart with Windows Python ran `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance`.
- Outcome before interruption: no Ironclad `victory=true`; new completed runs were `1780455201.run` (floor 19, killed by Shell Parasite) and `1780455267.run` (floor 16, killed by Slime Boss).
- Failure type: HAND_SELECT selection-count mismatch during a floor 16 boss state. The game already had one selected card with `max_cards=3`, but `SimpleAgent.handle_screen()` still requested three more cards. `CardSelectAction` rejected the action with `Too many cards selected (provided 3, max 2)`, and the batch loop repeatedly retried the same in-game screen without producing further `.run` records.
- Fix: HAND_SELECT now computes remaining required cards as `num_cards - len(selected_cards)`, avoids reselecting already-selected card objects, and confirms when the required count is already satisfied.
- Regression: `test_hand_select_only_selects_remaining_required_cards`.
- Verification after fix: focused regression `1 passed`; related card-select/agent/RL context tests `27 passed`; full pytest `1456 passed`.
- Next candidate: restart bounded validation after this commit and inspect remaining floor 16 boss deaths, especially RL EndTurnAction choices that force fallback takeover at low HP.

## Round 3 - 2026-06-03

- Preflight: git clean at `94d9c9e Respect remaining hand select count`.
- Baseline: full pytest with isolated `STS_AI_LOG_FILE`, disabled pytest cache, and unique basetemp -> 1456 passed.
- Validation: controlled CommunicationMod fresh run with Windows Python; log reached `Max games reached (20); exiting.`
- Outcome: no Ironclad `victory=true`. Visible new run files after the fresh start were 19 deaths: Act 1 boss deaths to The Guardian/Hexaghost dominated, with later deaths to Collector, Champ, Cultist and Chosen, Sentry and Sphere, and Gremlin Gang.
- Failure type: HAND_SELECT no longer over-selected, but the queued optional confirm skipped HAND_SELECT confirmations when `confirm` was already available and `confirm_up` was false. Logs showed repeated HAND_SELECT callbacks and repeated `KEY action: key=CARD_*` selections followed by `Skipping optional card-select confirm`.
- Fix: allow stale optional card-select confirm on HAND_SELECT only when the `confirm` command is actually available, while preserving the existing guard that avoids confirming HAND_SELECT screens without confirm.
- Regression: `test_stale_card_select_confirm_fires_for_hand_select_with_confirm_available`.
- Verification after fix: focused regression `1 passed`; related card-select/agent tests `23 passed`; full pytest `1457 passed`.
- Next candidate: rerun bounded validation and inspect repeated Act 1 boss deaths, especially low-HP Hexaghost/Guardian turns where RL ends turn and fallback takeover chooses defensive or setup lines that still leave lethal current-turn damage.

## Round 4 - 2026-06-03

- Preflight: `ce442d7 Confirm stale hand select screens`; same completed CommunicationMod batch was used for follow-up attribution before launching the next bounded validation.
- Baseline evidence: latest visible run from that batch, `1780458068.run`, died at floor 16 to Hexaghost with no `victory=true` in the batch.
- Failure type: healing-potion conservation risk. Logs showed `[POTION_GUARD] Using Blood Potion: incoming=16 hp=73/80 room=MonsterRoom monsters=3`, spending the run's only percent-heal potion in a high-HP normal fight. The later Hexaghost lethal turn ended at 9 HP before 24 incoming; keeping Blood Potion would have enabled survival with the already-selected 10 block line. Run potion usage fields were not treated as authoritative because logs showed the actual potion usage.
- Fix: healing/regen/fairy potion scoring now requires immediate lethal pressure, low-HP pressure, or moderate boss pressure. Damage, block, energy, and other potion classes keep the existing dangerous-combat thresholds.
- Regression: `test_potion_guard_saves_healing_potion_when_hp_is_high`; positive guard `test_potion_guard_uses_healing_potion_to_survive_lethal_turn`.
- Verification after fix: focused healing-potion regressions `2 passed`; `tests/test_combat_rl_guards.py` `36 passed`; full pytest `1459 passed`.
- Next candidate: rerun bounded validation from `ce442d7` plus this potion fix and inspect remaining Act 1 boss deaths, especially low-HP boss turns where saved potion use, fallback takeover, and current-turn lethal scoring interact.

## Round 5 - 2026-06-03

- Preflight: git clean at `0888c65 Conserve healing potions for emergencies`; CommunicationMod still used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance`.
- Baseline: full pytest with isolated `STS_AI_LOG_FILE`, disabled pytest cache, and unique basetemp -> 1459 passed.
- Validation: controlled CommunicationMod fresh run started at 11:55 CST. It completed 8 visible runs with no `victory=true`: deaths to Automaton twice, Hexaghost three times, Slime Boss once, 3 Sentries once, and Centurion and Healer once. The 9th game marker was `1780459838`, but no matching `.run` was written.
- Interruption: the batch was intentionally stopped with `restart_sts_modded.ps1 -SkipLaunch` after the repeated potion-action evidence was selected as the focused fix target, so the 9th game marker without a completed `.run` is a manual stop, not an organic no-log blocker.
- Failure type: potion command pacing/state-stability risk. Runtime logs selected `PotionAction` repeatedly, including guard-selected Block/Elixir/Energy/Blessing/Smoke Bomb/Strength/Dexterity potions; one combat selected Smoke Bomb and then Blessing of the Forge on consecutive callbacks before any explicit state-stabilizing wait. All completed run files still reported `potions_floor_usage=[]`, so policy changes would be premature until the action execution boundary is stabilized.
- Fix: `PotionAction.execute()` now queues `WaitAction(timeout=1)` after potion use/discard commands, matching the stabilization pattern already used for shop potion purchases and forcing a state update opportunity before the next decision.
- Regression: `test_potion_action_execute_uses_get_real_potions_without_raw_potions` now asserts both the `potion use 0` command and the queued `WaitAction`.
- Verification after fix: focused regression red `1 failed` for missing queued wait, then green `1 passed`; `tests/test_combat_rl_guards.py` `36 passed`; full pytest `1459 passed`.
- Next candidate: rerun bounded validation from `50ce48e Stabilize potion action updates` and verify whether completed run files now show non-empty potion usage when logs select PotionAction; if potion records remain empty, inspect sent command/effect confirmation at the CommunicationMod boundary before changing potion selection policy.
