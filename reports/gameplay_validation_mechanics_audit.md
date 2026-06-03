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

## Round 6 - 2026-06-03

- Preflight: git clean at `3d7164b Consolidate round five audit note`; full pytest baseline with disabled pytest cache and unique basetemp -> `1459 passed`.
- Validation: controlled CommunicationMod fresh run from `3d7164b`; `restart_sts_modded.ps1 -FreshRun` moved the leftover `IRONCLAD.autosave` from the manually stopped Round 5 batch before launch.
- Outcome before stopping for a focused fix: no Ironclad `victory=true`; completed new run `1780460697.run` died at floor 16 to Hexaghost and still reported `potions_floor_usage=[]`. Runtime logs from the same run selected `PotionAction` for Block Potion/Fear Potion; the following in-progress run also selected Dexterity Potion and Skill Potion before the batch was manually stopped for the focused fix.
- Failure type: potion command wait sequencing. The first potion-action stabilization fix queued `WaitAction(timeout=1)`, but `WaitAction` defaults to `requires_game_ready=False`, so the main loop could send `potion use ...` and `wait 1` back-to-back in the same action drain before the potion command response restored `game_is_ready`. That did not actually prove a post-potion state refresh.
- Fix: the wait queued by `PotionAction.execute()` is now ready-gated by setting `requires_game_ready=True`, so the coordinator waits for the potion command response before sending the stabilizing `wait 1`.
- Regression: `test_potion_action_execute_uses_get_real_potions_without_raw_potions` now asserts the queued `WaitAction` is `requires_game_ready=True`.
- Verification after fix: focused regression red `1 failed` on the non-ready-gated wait, then green `1 passed`; `tests/test_combat_rl_guards.py` `36 passed`; full pytest `1459 passed`.
- Next candidate: rerun bounded validation from the ready-gated potion wait commit. If completed run files still show zero potion usage after logged PotionAction decisions, add direct command/effect instrumentation at `PotionAction.execute()` and CommunicationMod response handling before changing gameplay potion policy.

## Round 7 - 2026-06-03

- Preflight: git clean at `ef583bf Gate potion wait on command readiness`; the ready-gated potion wait fix had full pytest verification -> `1459 passed`.
- Validation: controlled CommunicationMod fresh run with Windows Python after clearing a stale `Continue` autosave state; `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance` reached `Max games reached (20); exiting.`
- Outcome: no Ironclad `victory=true`; 20 AI markers were written and 19 completed `.run` files were visible from this fresh batch. The completed deaths were Act 1 boss-heavy, including six The Guardian deaths, two Slime Boss deaths, one Hexaghost death, plus several Act 2/3 deaths. Marker `1780462402` had no visible completed `.run`, but the batch continued writing later run files and did not show current Python tracebacks, so it was recorded as a side observation rather than the selected blocker.
- Failure type: energy-potion conservation risk. In latest completed run `1780464272.run`, the AI died to The Guardian on floor 16. Runtime logs showed `[POTION_GUARD] Using Energy Potion: incoming=0 hp=68/80 room=MonsterRoomBoss` on boss turn 1, then a later lethal Guardian turn with `8 HP`, `incoming=32`, and a hand where saving Energy Potion would have enabled the defensive `Shockwave+` plus three Defends line instead of dying without enough energy.
- Fix: energy/draw/randomize-cost potions no longer get a positive danger-guard score merely because the room is elite or boss; the guard now uses them only when there is meaningful current-turn incoming damage. Other potion categories keep their existing boss/elite danger behavior.
- Regression: `test_potion_guard_saves_energy_potion_on_safe_boss_turn` reproduced the unsafe boss-turn Energy Potion use and failed red; `test_potion_guard_uses_energy_potion_under_current_turn_pressure` keeps the lethal-pressure positive path.
- Verification after fix: focused Energy Potion tests `2 passed`; `tests/test_combat_rl_guards.py` `38 passed`; full pytest `1461 passed`.
- Next candidate: rerun bounded validation from this energy-potion conservation commit and inspect repeated Guardian/Slime Boss deaths, especially whether saved Energy Potion appears in late lethal boss turns and whether the missing marker-without-run observation recurs.

## Round 8 - 2026-06-03

- Preflight: git clean at `ff577d4 Conserve energy potions for pressure turns`; post-commit full pytest baseline -> `1461 passed`.
- Validation: controlled CommunicationMod fresh run with Windows Python. The batch was stopped manually after the selected crash was attributed, so it intentionally did not reach the 20-game bound. Before stopping, it wrote 3 AI markers and 2 completed `.run` files: `1780465389.run` died at floor 16 to Slime Boss and `1780465520.run` died at floor 25 to Snake Plant.
- Failure type: stale queued card action crash. During game #1 on floor 10, Elixir opened HAND_SELECT, stale card-select confirms produced invalid confirm errors, RL then played True Grit, and fallback planned Burning Pact from the latest hand. Before the queued `PlayCardAction` executed, the bound card UUID was no longer in `last_game_state.hand`, so `PlayCardAction.execute()` raised `Specified card for CardAction is not in hand`, aborting `play_one_game` and causing the batch loop to resume mid-run as game #2.
- Fix: when a UUID-bound `PlayCardAction` no longer finds that UUID in the latest hand, execution now logs a warning, sends `state`, and returns without sending a stale `play` command or raising. This lets the next state callback replan from the actual game state instead of failing the run.
- Regression: `test_play_card_action_requests_state_when_uuid_card_left_hand` reproduced the exception path red and now asserts the safe `state` request.
- Verification after fix: focused stale-card regression `1 passed`; related action/RL guard tests `40 passed`; full pytest `1462 passed`.
- Next candidate: rerun bounded validation from this stale-card guard commit and check whether HAND_SELECT stale confirm errors still occur without aborting runs. If they recur but no longer crash, inspect the Elixir/HAND_SELECT selection loop as a separate focused target.

## Round 9 - 2026-06-03

- Preflight: git clean at `0208f87 Guard stale queued card actions`; post-commit full pytest baseline -> `1462 passed`.
- Validation: controlled CommunicationMod fresh run with Windows Python. The batch was stopped manually after the selected repeated-error issue was attributed. Before stopping, it completed 3 visible `.run` files with no `victory=true`: `1780466186.run` died at floor 16 to Slime Boss, `1780466237.run` died at floor 16 to The Guardian, and `1780466425.run` died at floor 33 to Automaton.
- Failure type: repeated command-error propagation. Stale `confirm` commands still occurred after HAND_SELECT or screen transitions, but the immediate damage was that the same `Invalid command: confirm` error was passed through `Coordinator.receive_game_state_update()` to `CombatRLAgent.handle_error()` on consecutive state updates. That incremented `rl_failure_count` three times for one stale-confirm episode, disabled RL for the rest of the run, and polluted the validation signal.
- Fix: coordinator command-error handling now deduplicates consecutive identical errors until a clean state arrives. It clears the queue, processes the first distinct error through `error_callback`, suppresses repeated identical errors, clears `last_error`, and requests `state` when no recovery action is queued.
- Regression: `test_repeated_command_error_is_handled_once_and_resyncs_state` reproduced two consecutive `Invalid command: confirm` messages red and now asserts one callback plus two state resyncs.
- Verification after fix: focused repeated-error regression `1 passed`; related coordinator/card/action tests `10 passed`; full pytest `1463 passed`.
- Next candidate: rerun bounded validation from this coordinator error-dedupe commit. If stale confirms still occur but no longer disable RL, inspect the source of repeated HAND_SELECT confirms; if no protocol errors recur, return to Act 1 boss failure attribution.
