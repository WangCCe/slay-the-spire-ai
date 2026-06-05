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

## Round 10 - 2026-06-03

- Preflight: git clean at `5300275 Deduplicate repeated command errors`; post-commit full pytest baseline -> `1463 passed`.
- Validation: controlled CommunicationMod fresh run with Windows Python. The batch was stopped manually after the remaining HAND_SELECT stale-confirm source was attributed. Before stopping, it completed 7 visible `.run` files with no `victory=true`; all seven died at floor 16 to Act 1 bosses, dominated by Slime Boss.
- Failure type: HAND_SELECT command pacing. The coordinator dedupe fix worked: repeated `Invalid command: confirm` responses were suppressed instead of three-striking RL. The source still remained: `CardSelectAction` queued multiple HAND_SELECT `KeyAction`s and an optional stale confirm, all with `requires_game_ready=False`, so a single callback could send several card keys and `confirm` before any state response reflected the selections. That produced repeated stale confirm errors in game #8.
- Fix: `KeyAction` now supports explicit ready gating and response waiting. `CardSelectAction` uses ready-gated, response-waiting key commands for HAND_SELECT only, and the final optional HAND_SELECT confirm is also ready-gated. GRID selection keeps its existing immediate stale-confirm behavior.
- Regression: `test_hand_select_card_select_waits_between_keys_and_confirm` reproduced the old immediate HAND_SELECT queue red and now asserts key actions plus final confirm require game readiness, with HAND_SELECT keys waiting for responses.
- Verification after fix: focused HAND_SELECT queue regression `1 passed`; related card/coordinator/action tests `11 passed`; full pytest `1464 passed`.
- Next candidate: rerun bounded validation from this HAND_SELECT pacing commit. If protocol errors stop, attribute the repeated Act 1 boss deaths; if HAND_SELECT confirm errors persist, inspect whether `SimpleAgent.handle_screen()` is reselecting too many cards before selected-card state updates arrive.

## Round 11 - 2026-06-03

- Preflight: git clean at `18189dd Gate hand select key confirms`; post-commit full pytest baseline -> `1464 passed`.
- Validation: controlled CommunicationMod fresh run with Windows Python reached `Max games reached (20); exiting.` The batch produced 20 AI markers and 19 visible completed `.run` files; none had `victory=true`.
- Outcome: visible deaths included four Hexaghost, four The Guardian, two Slime Boss, one 3 Sentries, and several Act 2 boss/event deaths. The highest-floor visible failures were floor 33 Champ/Automaton/Collector and floor 31 Sentry and Sphere.
- Failure type: unsafe automatic Elixir use. With protocol errors quiet, logs showed `[POTION_GUARD] Using Elixir` twice in ordinary dangerous combats. The latest selected failure was `1780470582.run`, which died on floor 27 to Colosseum Slavers after guard-used Elixir opened HAND_SELECT on turn 1, exhausted three selected cards, and left only `Bloodletting` plus `Blood for Blood`; the turn ended with `energy_remaining=4` and an empty hand before the run died four turns later.
- Fix: potion guard scoring now refuses `exhaust_hand_select` / `Elixir` in automatic danger-guard use, so Elixir no longer falls through to the generic unknown-potion positive score for `incoming >= 18`, elite, or boss states.
- Regression: `test_potion_guard_does_not_auto_use_elixir_hand_select_potion` reproduced the Colosseum-style high-incoming state red, then passed after the scoring guard.
- Verification after fix: focused regression `1 passed`; `tests/test_combat_rl_guards.py` `39 passed`; default full pytest first hit a Windows temp permission error (`C:\Users\20571\AppData\Local\Temp\pytest-of-20571`), then isolated full pytest with repo-local basetemp and disabled cache provider passed `1465 passed`.
- Next candidate: rerun bounded validation from this Elixir guard commit. If potion policy remains the clearest signal, inspect boss-opening debuff use such as `Weak Potion` on Hexaghost turn 1 with only `incoming=5`; otherwise return to the dominant Act 1 boss deaths and late Act 2/3 boss failures.

## Round 12 - 2026-06-03

- Preflight: git clean at `23ef5de Skip automatic Elixir guard use`; post-commit full pytest baseline with isolated repo-local basetemp -> `1465 passed`.
- Validation: CommunicationMod stayed on Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance`. The first fresh launch reached the Slay the Spire main menu but did not start a run; process/log checks and offline model-load probes indicated a one-off CommunicationMod/pipe startup deadlock, not a code model-load blocker. A controlled restart then ran the bounded batch to `Max games reached (20); exiting.`
- Outcome: no Ironclad `victory=true`; the restarted batch wrote 20 AI markers and 18 visible completed `.run` files. The best visible run was `1780475627.run`, floor 50, died to Donu and Deca. Other visible deaths included repeated Act 1 bosses, Act 2 hallway/elites, and Act 2 bosses.
- Failure type: unsafe automatic utility/choice potion use on safe boss turns. Runtime logs showed repeated `POTION_GUARD` uses of `Attack Potion`, `Gambler's Brew`, `Blessing of the Forge`, and `Distilled Chaos` on `MonsterRoomBoss` turns with `incoming=0` or only `incoming=5`. These potions can open card-choice or hand-select-like decision screens or consume a one-time burst resource, so boss-room presence alone is not a sufficient danger signal. Matching logs also showed the same potion family being useful under `incoming>=18` normal combat pressure.
- Fix: potion guard scoring now treats utility/choice effects (`card_choice_*`, `discard_draw`, `play_top_cards`, `upgrade_hand`, `duplicate_next_card`, `return_discard_card`, and similar generated-card utility effects) as current-pressure tools. They no longer get a positive automatic score merely because the room is elite or boss, but they remain eligible when current incoming damage is at least 18.
- Regression: `test_potion_guard_saves_utility_choice_potion_on_safe_boss_turn` reproduced the boss-opening `Attack Potion` use red; `test_potion_guard_uses_utility_choice_potion_under_current_turn_pressure` preserves the high-pressure positive path.
- Verification after fix: focused utility-choice tests `2 passed`; `tests/test_combat_rl_guards.py` `41 passed`; full pytest with disabled cache provider and repo-local basetemp passed `1467 passed`.
- Next candidate: rerun bounded validation from this commit. If potion noise drops, inspect dominant remaining boss failures, especially floor 50 Donu/Deca and repeated Act 1 boss deaths where RL opens with `EndTurnAction` and fallback takeover must carry the whole turn.

## Round 13 - 2026-06-03

- Preflight: git clean at `f50c3c5 Conserve utility potions for pressure turns`; CommunicationMod config still used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance`.
- Baseline: full pytest with disabled cache provider and repo-local basetemp passed `1467 passed`.
- Validation: controlled CommunicationMod fresh run started at 17:17 CST. The batch reached a successful Ironclad validation game before the 20-game bound, so the automation was stopped with `restart_sts_modded.ps1 -SkipLaunch` after confirming the run record.
- Outcome: goal stop condition reached. `1780479519.run` recorded `floor_reached=51`, `victory=true`, score `664`, ascension `0`, character `IRONCLAD`, playtime `203`, with no `killed_by`.
- Failure/fix selection: no new fix was selected because the audit objective was satisfied by the victory record. Earlier non-victory games in the same batch still showed deaths to Act 1 bosses and Act 2 fights, and logs contained a few low-pressure boss potion uses for setup/status potions, but those remain candidates rather than blockers after the successful run.
- Verification after outcome: the victory `.run` was parsed directly from `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1780479519.run`; the validation processes were stopped cleanly and no new gameplay batch was launched.
- Next candidate if continuing beyond the first-win goal: inspect low-pressure boss use of setup/status potions such as `Flex Potion`, `Fear Potion`, `Liquid Bronze`, and `Ancient Potion`, separating burst/status tools from permanent scaling before writing any policy regression.

## Round 14 - 2026-06-04

- Preflight: git tracked tree clean at `7607393 Guard Act 1 pre-boss potion use`; `git status --short` initially warned on three pytest basetemp ACL leftovers, which were later removed. CommunicationMod config used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance --truncate-log-after-backup`.
- Baseline: full pytest with disabled cache provider and repo-local basetemp passed `1481 passed`.
- Validation: controlled CommunicationMod fresh run reached `Max games reached (20); exiting.` It wrote 20 AI markers and 19 visible completed `.run` files; marker `1780549210` had no matching visible `.run`.
- Outcome: no Ironclad `victory=true`. Visible deaths included four Slime Boss, four Hexaghost, one Guardian, two 3 Byrds, two Shelled Parasite and Fungi, and several Act 2 fights. Compared with the previous Act 1 boss replay snapshot, Slime/Hex deaths appeared lower (`8/19` visible records versus `10/20`), but the missing run record makes this only a directional signal. `POTION_SAVE_GUARD` fired frequently before Act 1 bosses, while some actual pre-boss `PotionAction` callbacks still occurred.
- Failure type: stale queued EndTurnAction crossed a combat turn boundary. In `1780549029.run` on floor 20, killed by 3 Byrds, logs showed RL selected `EndTurnAction` on turn 1 with `energy=0`, then that stale action executed after the game had advanced to fresh turns with `energy=3` and large hands, directly ending turns 2 through 5.
- Fix: `EndTurnAction` now carries optional `expected_floor` and `expected_turn`; if execution sees a different latest combat context, it requests `state` instead of sending `end`. `CombatRLAgent` stamps EndTurn actions returned from RL, fallback takeover, fallback replacement, and final OptimizedAgent fallback with the current combat context.
- Regression: `test_end_turn_action_requests_state_when_turn_snapshot_is_stale` and `test_rl_end_turn_action_is_stamped_with_combat_turn_context` reproduced the bug red (`end` sent instead of `state`; missing context stamp) before the fix.
- Verification after fix: new focused regressions `2 passed`; related action/RL guard files `54 passed`; full pytest with disabled cache provider and repo-local basetemp passed `1483 passed`.
- Next candidate: rerun bounded validation from this stale-EndTurn guard commit and check whether 3 Byrds no longer shows multi-turn direct-end behavior. Continue tracking Slime/Hex pre-boss potion burn separately from boss-window potion use, because the current batch suggests the pre-boss guard is active but not yet enough to prove boss survival improvement.

## Round 15 - 2026-06-05

- Preflight: git tracked tree clean at `b52365d Add validation workflow diagnostics`; CommunicationMod config used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance --truncate-log-after-backup`.
- Baseline: full pytest with disabled cache provider and repo-local basetemp passed `1512 passed`.
- Validation: controlled CommunicationMod fresh run from `b52365d` was stopped after a focused failure target was attributed. It completed 3 visible `.run` files after cutoff `1780590624`: `1780619220.run` died at floor 22 to Snake Plant, `1780619304.run` died at floor 14 to Exordium Thugs, and `1780619373.run` died at floor 16 to Slime Boss. No `victory=true` appeared, and `communication_mod_errors.log` had no active Python traceback.
- Failure type: unsafe fallback Elixir auto-use. In `1780619304.run`, live decision trace showed the AI at 13 HP versus 10 incoming using Elixir from `OptimizedAgent`/fallback potion logic after playing two attacks. Elixir opened HAND_SELECT and exhausted the remaining Defends/Bash, leaving 0 block before the Thug hit and causing a lethal next turn. The existing `CombatRLAgent` potion guard already skipped Elixir, so the selected risk was the fallback/optimized automatic potion path.
- Fix: automatic potion helpers now identify `exhaust_hand_select` / `ElixirPotion` as unsafe for blind use. `OptimizedAgent.use_next_potion()` skips those potions in high-danger generic scoring, and `SimpleAgent.use_next_potion()` skips them as well so boss fallback does not reintroduce the same hand-select risk.
- Regression: `test_optimized_agent_does_not_auto_use_elixir_hand_select_potion_in_danger` and `test_optimized_agent_boss_fallback_does_not_auto_use_elixir_hand_select_potion` reproduced the two automatic-use paths red before the fix.
- Verification after fix: focused regressions red `2 failed`, then green `2 passed`; related agent/CombatRL potion tests `107 passed`; full pytest with disabled cache provider and repo-local basetemp passed `1514 passed`.
- Next candidate: rerun bounded validation from this commit and confirm that fallback no longer burns Elixir into HAND_SELECT. If that signal is quiet, inspect the remaining Slime Boss death and the Act 2 low-HP Snake Plant/Snecko decisions rather than broad potion policy tuning.

## Round 16 - 2026-06-05

- Preflight: git tracked tree clean at `3195618 Skip fallback Elixir auto-use`; CommunicationMod config still used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance --truncate-log-after-backup`.
- Baseline: the previous commit had just passed full pytest `1514 passed`; post-fix verification for this round passed full pytest `1515 passed`.
- Validation: controlled CommunicationMod fresh run from `3195618` was stopped after a focused second Elixir entry point was attributed. It completed 6 visible `.run` files after cutoff `1780619680` with no `victory=true`: deaths to Champ, Collector, Exordium Wildlife, The Guardian twice, and Slime Boss. No CommunicationMod Python traceback was active.
- Failure type: RL action-space Elixir auto-use bypassed the fallback guard. Decision trace for the Slime Boss run showed `CombatRLAgent` returning `PotionAction` for `ElixirPotion` on floor 16 turn 2, even though fallback and potion-guard scoring no longer auto-use Elixir. That means the learned action decoder path could still open HAND_SELECT and exhaust playable cards.
- Fix: `CombatRLAgent._should_override_low_value_potion()` now treats `exhaust_hand_select` / `ElixirPotion` as an always-replace unsafe blind potion action before boss/elite exceptions. `CombatRLAgent._score_potion_for_guard()` also uses the shared `potion_is_exhaust_hand_select()` helper.
- Regression: `test_rl_elixir_action_is_replaced_even_in_boss_combat` reproduced the Slime Boss RL-action path red, then passed after the guard.
- Verification after fix: focused regression red `1 failed`, then green `1 passed`; related agent/CombatRL potion tests `108 passed`; full pytest with disabled cache provider and repo-local basetemp passed `1515 passed`.
- Next candidate: rerun bounded validation from this commit and confirm that no `PotionAction` uses `ElixirPotion` from either guard, fallback, or RL action-space paths. If Elixir stays quiet, inspect repeated Act 1 boss deaths and the Act 2 boss deaths separately.

## Round 17 - 2026-06-05

- Preflight: git tracked tree clean at `36787bb Block RL Elixir auto-use`; CommunicationMod config still used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance --truncate-log-after-backup`.
- Baseline: the previous commit had just passed full pytest `1515 passed`; post-fix verification for this round passed full pytest `1516 passed`.
- Validation: controlled CommunicationMod fresh run from `36787bb` was stopped after a focused Act 1 boss survival failure was attributed. It completed 4 visible `.run` files after cutoff `1780621037` with no `victory=true`: three Hexaghost deaths and one Guardian death. The trace scan after cutoff found `elixir_potion_actions_after_cutoff=0`, so the selected failure moved away from Elixir.
- Failure type: current-turn survival fallback ignored player end-turn Burn damage. In `1780621787.run`, Hexaghost floor 16 turn 8 had player HP 9, block 0, incoming 8, and an unplayed `Burn` in hand. RL initially ended turn, energy guard handed off to fallback, and fallback selected attacks (`Thunderclap`, `Bash`) instead of `Defend`. Incoming 8 plus Burn 2 killed from 9 HP; playing `Defend` would have survived the turn.
- Fix: `CombatRLAgent` survival fallback now counts unplayed hand Burn damage together with monster incoming damage before asking fallback for an action. When current HP would not survive incoming plus Burn after current block, energy guard/takeover chooses the highest-confidence playable block card instead of blindly accepting fallback's attack or first playable card.
- Regression: `test_energy_guard_counts_burn_damage_when_selecting_survival_fallback` reproduced the Hexaghost hand red by making fallback choose `Thunderclap`; after the fix, the replacement chooses `Defend`.
- Verification after fix: focused regression red `1 failed`, then green `1 passed`; related CombatRL/agent guard tests `109 passed`; full pytest with disabled cache provider and repo-local basetemp passed `1516 passed`.
- Next candidate: rerun bounded validation from this commit and inspect whether Hexaghost deaths still contain same-turn Burn lethal lines. If this signal quiets, compare remaining Act 1 boss deaths by boss and turn phase before touching broader fallback/RL policy.

## Round 18 - 2026-06-05

- Preflight: git tracked tree clean at `a48a238 Count Burn damage in survival fallback`; CommunicationMod config still used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance --truncate-log-after-backup`.
- Baseline: full pytest with disabled cache provider and repo-local basetemp passed `1516 passed`.
- Validation: controlled CommunicationMod fresh run from `a48a238` was stopped after the selected potion-action bypass was attributed. It completed 5 visible `.run` files after cutoff `1780621790` with no `victory=true`: Slime Boss, Guardian, Hexaghost, Writhing Mass at floor 46, and another Hexaghost. The batch was then stopped with `restart_sts_modded.ps1 -SkipLaunch` to preserve the current trace.
- Failure type: RL action-space Elixir guard only handled `PotionAction` objects carrying a bound `potion`. The v2 decoder emits index-only `PotionAction(use=True, potion_index=slot)`, and decision trace showed that shape using `ElixirPotion` on Hexaghost floor 16 turn 2 (`1780623209.run`), opening HAND_SELECT despite the previous Elixir guard.
- Fix: `CombatRLAgent` now resolves the potion for a `PotionAction` from either the bound `action.potion` or `action.potion_index` against the current game potions before deciding whether the action is an unsafe exhaust-hand-select potion. Combat action logging also includes the resolved potion name and index for index-only potion actions.
- Regression: `test_rl_elixir_index_action_is_replaced_even_in_boss_combat` reproduced the real v2 decoder path red with `PotionAction(True, potion_index=0)` and a current Elixir slot, then passed after the guard resolved the indexed potion.
- Verification after fix: focused regression red `1 failed`, then green `1 passed`; related CombatRL/agent/potion tests `116 passed`; full pytest with disabled cache provider and repo-local basetemp passed `1517 passed`.
- Next candidate: rerun bounded validation from this commit and confirm trace contains no `ElixirPotion` `PotionAction` from bound or index-only RL paths. If Elixir stays quiet, inspect the remaining Act 1 boss deaths and the floor 46 Writhing Mass death separately.

## Round 19 - 2026-06-05

- Preflight: git tracked tree clean at `2152394 Resolve indexed RL Elixir actions`; CommunicationMod config used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance --truncate-log-after-backup`.
- Baseline: full pytest with disabled cache provider and repo-local basetemp passed `1517 passed`.
- Validation: controlled CommunicationMod fresh run initially reached the main menu but did not enter a run because the Slay the Spire window was opened at `1920x1080` under Windows scaling and the launch UI was partially clipped. `D:\SteamLibrary\steamapps\common\SlayTheSpire\info.displayconfig` was backed up and temporarily set to `1280x720`, then the restarted bounded batch reached `Max games reached (20); exiting.`
- Outcome: no Ironclad `victory=true`. The batch wrote 20 visible `.run` files from `1780638179.run` through `1780640095.run`. Visible deaths included five Hexaghost, four The Guardian, two Slime Boss, three Act 2 hallway deaths, two Act 2 bosses, and early Act 1 hallway deaths. The decision trace search found zero `ElixirPotion`, `PotionAction`, or `potion_index` hits, so the indexed Elixir fix stayed quiet.
- Failure type: fallback-turn takeover could still end a turn when fallback also returned `EndTurnAction`. The decision trace showed boss states where `EndTurnAction` was emitted with energy and playable cards still available, including Guardian floor 16 turn 5 at 5 HP with 3 energy and playable attacks while Guardian intended `DEFEND`. This means the energy guard could correctly start takeover after RL ended early, but the takeover branch then trusted fallback's own EndTurn instead of applying the same non-end replacement policy.
- Fix: during active fallback-turn takeover, `CombatRLAgent` now treats a fallback `EndTurnAction` like a wasteful end-turn candidate: it asks `_get_non_end_turn_fallback()` for a playable replacement and only allows EndTurn when no replacement exists.
- Regression: `test_energy_guard_takeover_replaces_fallback_end_turn_with_playable_card` reproduced the Guardian-style active-takeover state red before the fix, asserting that playable attacks should be used instead of ending.
- Verification after fix: focused regression red `1 failed`, then green `1 passed`; `tests/test_combat_rl_guards.py` passed `60 passed`; full pytest with disabled cache provider and repo-local basetemp passed `1518 passed`.
- Next candidate: rerun bounded validation from this commit and check whether Act 1 boss deaths still contain `EndTurnAction` with energy plus playable cards during active fallback takeover. If that signal quiets but Act 1 boss deaths remain dominant, inspect boss-specific high-pressure defense/offense selection rather than broader cleanup or training.

## Round 20 - 2026-06-05

- Preflight: git tracked tree clean at `6464e0b Guard fallback takeover end turns`; CommunicationMod config used Windows Python with `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance --truncate-log-after-backup`; Slay the Spire display config remained at the temporary `1280x720` validation size from Round 19.
- Baseline: full pytest with disabled cache provider and repo-local basetemp passed `1518 passed`.
- Validation: controlled CommunicationMod fresh run from `6464e0b` was stopped after the selected trace failure was attributed. It completed 10 visible `.run` files after cutoff `1780640095` with no `victory=true`: six Act 1 boss deaths (`Slime Boss` twice and `The Guardian` four times), two `Collector` deaths, one `Automaton` death, and one `Snake Plant` death. No active Python traceback appeared in `communication_mod_errors.log`.
- Failure type: decision trace recorded raw RL potion candidates before the combat guards had validated or replaced them. Live trace after the cutoff showed post-fix `ElixirPotion` / `PotionAction` entries, including Elixir in Act 2 (`Collector` floor 33 and `Snecko` floor 25), even though `POTION_SAVE_GUARD` / Elixir replacement logic was supposed to prevent those actions from being sent. Root cause: `CombatRLAgent` called `_with_combat_action_context()` immediately after `rl_agent.get_next_action_in_game()`, so the trace wrote the raw RL action before `POTION_SAVE_GUARD`, Elixir replacement, energy guard, and other override branches selected the final action. Bound potion actions also leaked `potion_index=-1` into trace because slot resolution was deferred until `PotionAction.execute()`.
- Fix: decision trace now resolves bound potion objects to their current potion slot, including `get_real_potions()` fallback, before writing `action.potion_index`. `CombatRLAgent` now traces only the final action returned to CommunicationMod: raw RL candidates are logged for debugging but not written to `ai_decision_trace.jsonl` until they survive guard validation or are replaced.
- Regression: `test_decision_trace_resolves_bound_potion_index` reproduced the `potion_index=-1` trace leak red; `test_rl_elixir_replacement_trace_records_final_action_only` reproduced the raw Elixir trace pollution red by asserting that a guarded Elixir candidate writes only the final `PlayCardAction`.
- Verification after fix: focused regressions red `2 failed`, then green `2 passed`; related trace/combat/potion/action-space tests passed `105 passed`; full pytest with disabled cache provider and repo-local basetemp passed `1520 passed`.
- Next candidate: rerun bounded validation from this trace-final-action commit and confirm the post-fix trace no longer contains guarded raw `ElixirPotion` `PotionAction` entries or bound-potion `potion_index=-1` leaks. If that signal quiets, return to the dominant Act 1 boss deaths and inspect boss-specific high-pressure defense/offense selection with the now-trustworthy final-action trace.
