# Post-Victory Combat RL Retraining Validation

## Objective

Build a post-victory retraining loop from commit `30317b7` that compares each
continued-training slice against a fixed Ironclad A0 eval protocol before any
checkpoint promotion. Training pauses whenever eval evidence exposes a
high-confidence mechanics, protocol, or decision-boundary issue.

## Fixed Baseline Inputs

- Repo commit: `30317b7 Record first Ironclad validation victory`
- Gameplay Python: `D:\anaconda\envs\stsai\python.exe`
- CommunicationMod command: `scripts/run_training_batch.py --eval --max-games 20 --phase conservative --restart-guidance`
- Expanded mode: `main.py --agent combat_rl --rl-version v2 --elite-route conservative --max-games 20 --ascension 0 --eval`
- Loaded checkpoint: `checkpoints\rl_combat_model_ep39_steps10991.pth`
- Eval mode: low-exploration inference, not training

## Baseline Batch 1 - 2026-06-03

- Start: `2026-06-03T22:17:06+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Result: `Max games reached (20); exiting.`
- AI markers: 20
- Unique completed `.run` files: 19
- Wins: 0
- Win rate: 0.0%
- Average floor: 22.3
- Median floor: 21
- Max floor: 36
- Average playtime: 118.8 seconds

Death distribution:

| Count | Killed by |
| ---: | --- |
| 2 | 3 Cultists |
| 2 | Collector |
| 2 | Hexaghost |
| 2 | Slime Boss |
| 2 | The Guardian |
| 1 | 2 Orb Walkers |
| 1 | Blue Slaver |
| 1 | Champ |
| 1 | Chosen and Byrds |
| 1 | Cultist and Chosen |
| 1 | Sentry and Sphere |
| 1 | Shelled Parasite and Fungi |
| 1 | Snake Plant |
| 1 | Spheric Guardian |

Protocol and guard signals:

- Tracebacks: 0
- RL disabled events: 0
- `CombatRLAgent error`: 1 event
- `Invalid command: play`: 1 stale queued-play event, counted across 3 log lines
- `Invalid command: proceed`: 2 out-of-game start-boundary observations
- `[POTION_GUARD]` uses: 19
- Safe boss potion uses with `incoming=0` or `incoming=5`: 4

## Pause Before Training - Stale Queued Play

The first baseline batch exposed a protocol-boundary bug before any training
slice was started. At `2026-06-03 22:51:33`, RL selected a `PlayCardAction` in
combat. The next state had already transitioned to `COMBAT_REWARD`, but the
queued action still executed and sent `play`, which CommunicationMod rejected:
`Invalid command: play. Possible commands: [potion, proceed, key, click, wait, state]`.

Fix:

- `PlayCardAction.execute()` now treats an explicit current command set without
  `play` as stale, sends `state`, and returns instead of issuing a stale `play`
  command.
- Regression: `test_play_card_action_requests_state_when_play_command_is_stale`.

Verification:

- Red: the new regression failed with `sent_messages == ['play 1 0']`.
- Green focused: `tests/test_play_card_action_guards.py` -> 2 passed.
- Green related: play-card, combat-RL, and combat-reward guard tests -> 45 passed.
- Green full suite: 1468 passed.

## Next Step

Do not promote or continue training from this batch. Commit the stale queued-play
fix, then rerun the same 20-game eval protocol from the fixed commit. If that
eval has no protocol-boundary blocker, use it as the retraining baseline and
start the first small continued-training slice from
`rl_combat_model_ep39_steps10991.pth`.

## Fixed Baseline Batch 2 - 2026-06-03

- Start: `2026-06-03T23:11:12+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Repo commit: `fd3181a Guard stale queued card plays`
- Result: stopped early after the stale-play blocker reproduced again.
- Completed `.run` files before stop: 6
- Wins: 0
- Win rate: 0.0%
- Average floor: 19.7
- Median floor: 16
- Max floor: 33

Death distribution before stop:

| Count | Killed by |
| ---: | --- |
| 2 | Collector |
| 2 | The Guardian |
| 1 | Hexaghost |
| 1 | Slime Boss |

Protocol signal:

- `Invalid command: play`: 1 event at `2026-06-03 23:14:52`.
- The prior stale-command guard was insufficient. Live logs showed
  `[ENERGY_GUARD]` replacing an RL `EndTurnAction` with `PlayCardAction`, then
  continuing fallback turn takeover and issuing another `PlayCardAction` before
  the post-play state boundary had stabilized. CommunicationMod then reported
  `COMBAT_REWARD` plus a delayed `Invalid command: play`.

Follow-up fix:

- `PlayCardAction.execute()` now queues a ready-gated `WaitAction(timeout=1)`
  after every successful `play`, matching the serialization already used for
  potion actions. This prevents immediate next callbacks from chaining another
  play off a stale post-action state.
- Regression: `test_play_card_action_queues_ready_wait_after_successful_play`.

Verification:

- Red: the new regression failed because no post-play wait was queued.
- Green focused: `tests/test_play_card_action_guards.py` -> 3 passed.
- Green related: play-card, combat-RL, and combat-reward guard tests -> 46 passed.

Next step: rerun the same 20-game eval protocol from the new fixed commit. Do
not begin continued training until the eval baseline is clean of this protocol
blocker.

## Fixed Baseline Batch 3 - 2026-06-03

- Start: `2026-06-03T23:36:16+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Repo commit: `ab957e6 Serialize card plays after command`
- Result: stopped early after a shop command-boundary blocker reproduced.
- Completed `.run` files before stop: 1
- Wins: 0
- Run: `1780501050.run`, floor 16, killed by Slime Boss.

Protocol signal:

- `Invalid command: cancel`: 1 event at `2026-06-03 23:39:45`.
- `Invalid command: proceed`: 1 event at `2026-06-03 23:39:45`.
- Live logs showed `SHOP_SCREEN` buying a potion, then attempting `cancel` when
  CommunicationMod only advertised `[choose, potion, proceed, key, click, wait,
  state]`, followed by attempting `proceed` when the room only advertised
  `[choose, potion, return, key, click, wait, state]`.

Follow-up fix:

- `CancelAction.execute()` now resolves the exact current cancel-group command
  from `cancel`, `leave`, `return`, or `skip`, and requests `state` when no
  cancel-group command is currently available.
- `ProceedAction.execute()` now sends `proceed` or `confirm` only when currently
  advertised, and requests `state` otherwise.
- Regressions:
  `test_cancel_action_uses_current_return_command_alias`,
  `test_cancel_action_requests_state_when_cancel_group_is_stale`, and
  `test_proceed_action_requests_state_when_proceed_is_stale`.

Verification:

- Red: all three new regressions failed against the old fixed-command behavior.
- Green focused: action guards -> 6 passed.
- Green shop/basic focused: 32 passed.
- Green RL action-space focused: 69 passed.

Next step: commit the exact-command guard fix, then rerun the same 20-game eval
protocol from that commit. Training remains paused.

## Fixed Baseline Batch 4 - 2026-06-03/04

- Start: `2026-06-03T23:49:13+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Repo commit: `0e10cea Guard stale exit commands`
- Result: stopped early after a shop exit serialization blocker reproduced.
- Completed `.run` files before stop: 10
- Wins: 0
- Win rate: 0.0%
- Average floor: 23.5
- Median floor: 22.5
- Max floor: 33

Death distribution before stop:

| Count | Killed by |
| ---: | --- |
| 4 | The Guardian |
| 1 | Automaton |
| 1 | Centurion and Healer |
| 1 | Chosen and Byrds |
| 1 | Sentry and Sphere |
| 1 | Shelled Parasite and Fungi |
| 1 | Snake Plant |

Protocol signal:

- `Invalid command: leave`: 1 event at `2026-06-04 00:10:25`.
- `Invalid command: proceed`: 1 event at `2026-06-04 00:10:26`.
- Live logs showed `SHOP_SCREEN` buying a potion, then returning consecutive
  shop-exit actions across a transition frame. The first `CancelAction`
  advanced the state; the next exit action still sent `leave` while
  CommunicationMod advertised `proceed`. The subsequent `SHOP_ROOM` state then
  repeated `ProceedAction` while the room only advertised `return`.

Follow-up fix:

- `LeaveAction.execute()` now checks current `available_commands` and requests
  `state` instead of sending stale `leave`.
- `CancelAction.execute()`, `LeaveAction.execute()`, and
  `ProceedAction.execute()` now queue a ready-gated `WaitAction(timeout=1)`
  after a successful exit command, matching the serialization used for card
  play and potion actions.
- Regressions:
  `test_cancel_action_queues_ready_wait_after_successful_exit_alias`,
  `test_leave_action_requests_state_when_leave_command_is_stale`,
  `test_leave_action_queues_ready_wait_after_successful_leave`, and
  `test_proceed_action_queues_ready_wait_after_successful_proceed`.

Verification:

- Red: the four new regressions failed against the old behavior.
- Green focused: action guards -> 10 passed.
- Green related: play-card, potion, shop-screen, and RL v2 action-space tests
  -> 63 passed.
- Green full suite: 1476 passed.

Next step: commit the shop-exit serialization fix, then rerun the same
20-game eval protocol from the new fixed commit. Training remains paused until
the eval baseline completes without protocol or mechanics blockers.

## Fixed Baseline Batch 5 - 2026-06-04

- Start: `2026-06-04T00:23:07+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Repo commit: `5632865 Serialize shop exit commands`
- Result: stopped early after a queue-boundary blocker crossed the game-over
  to next-run startup boundary.
- Completed `.run` files before stop: 12
- Wins: 0
- Win rate: 0.0%
- Average floor: 24.6
- Median floor: 23
- Max floor: 33

Death distribution before stop:

| Count | Killed by |
| ---: | --- |
| 2 | Champ |
| 2 | Collector |
| 1 | 3 Cultists |
| 1 | Automaton |
| 1 | Cultist and Chosen |
| 1 | Hexaghost |
| 1 | Large Slime |
| 1 | Slime Boss |
| 1 | Snake Plant |
| 1 | The Guardian |

Protocol signal:

- `Invalid command: wait`: 1 event at `2026-06-04 00:50:54`.
- `Invalid command: play`: 1 late event at `2026-06-04 00:51:23`.
- The `wait` event had a clear queue-leak signature: after `GAME_OVER`, a
  ready-gated `WaitAction` remained at the front of the queue. The next update
  reported `in_game=False` with only `[start, state]` available, but the stale
  wait executed before the newly queued `StartGameAction`.
- The `play` event arrived after the state had already transitioned to
  `COMBAT_REWARD`; it is recorded as the next candidate if it reproduces after
  the out-of-game queue leak is removed.

Follow-up fix:

- `Coordinator.receive_game_state_update()` now clears stale queued actions
  before invoking the out-of-game callback and queuing the next start action.
- Regression:
  `test_out_of_game_update_clears_stale_ready_wait_before_start_action`.

Verification:

- Red: the new regression failed with a queue of
  `[WaitAction, StartGameAction]`.
- Green focused: deferred/coordinator callback tests -> 6 passed.
- Green related: deferred, startup, play-card, shop-screen, and potion action
  tests -> 33 passed.
- Green full suite: 1477 passed.

Next step: commit the out-of-game queue cleanup, then rerun the same 20-game
eval protocol. If `Invalid command: play` recurs without the stale wait leak,
pause again and diagnose play-response ordering as the next focused blocker.

## Fixed Baseline Batch 6 - 2026-06-04

- Start: `2026-06-04T01:04:29+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Repo commit: `28ddb95 Clear stale actions before next run`
- Result: stopped early after the late `play` command error reproduced without
  the prior out-of-game `wait` leak.
- Completed `.run` files before stop: 6
- Wins: 0
- Win rate: 0.0%
- Average floor: 21.8
- Median floor: 18
- Max floor: 33

Death distribution before stop:

| Count | Killed by |
| ---: | --- |
| 2 | Collector |
| 1 | Centurion and Healer |
| 1 | Gremlin Gang |
| 1 | Hexaghost |
| 1 | The Guardian |

Protocol signal:

- `Invalid command: wait`: 0 events after the out-of-game queue cleanup.
- `Invalid command: play`: 1 event at `2026-06-04 01:13:26`.
- The play error arrived after the coordinator had already observed
  `ScreenType.COMBAT_REWARD` with available commands
  `[proceed, key, click, wait, state]`. The run continued through reward, map,
  and rest states; this identified a transition-late command error rather than
  a fresh in-combat action selection problem.

Follow-up fix:

- `Coordinator` now classifies `Invalid command: play` received while the last
  known state is `COMBAT_REWARD` and `play` is no longer advertised as a
  transition-late command error.
- Transition-late play errors request `state` directly and do not call the
  agent error callback, preventing a recoverable ordering artifact from being
  counted as a `CombatRLAgent error`.
- Regression:
  `test_late_play_error_on_combat_reward_resyncs_without_error_callback`.

Verification:

- Red: the new regression failed because the old path called
  `error_callback`.
- Green focused: deferred/coordinator callback tests -> 7 passed.
- Green related: deferred, startup, play-card, combat-reward, and live batch
  diagnostics tests -> 25 passed after rerunning with workspace basetemp.
- Green full suite: 1478 passed.

Next step: commit the transition-late play handling, then rerun the same
20-game eval protocol from the new fixed commit. Training remains paused until
the baseline completes cleanly.

## Fixed Baseline Batch 7 - 2026-06-04

- Start: `2026-06-04T01:25:34+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Repo commit: `883560f Resync late play errors after combat`
- Result: completed 20 `.run` files and batch post-analysis.
- Wins: 0
- Win rate: 0.0%
- Average floor: 23.0
- Median floor: 22.5
- Max floor: 33
- Average playtime: 120.2 seconds

Death distribution:

| Count | Killed by |
| ---: | --- |
| 6 | Hexaghost |
| 3 | Collector |
| 2 | Chosen and Byrds |
| 2 | Cultist and Chosen |
| 2 | Sentry and Sphere |
| 2 | Slime Boss |
| 1 | Champ |
| 1 | Slavers |
| 1 | The Guardian |

Protocol signal:

- `Invalid command:*`: 0 matching events in available logs for this batch.
- `CombatRLAgent error`: 0 matching events in available logs for this batch.
- `TRANSITION_LATE_COMMAND_ERROR`: 0 matching events in available logs for this
  batch.
- `communication_mod_errors.log` showed the expected batch command and
  post-analysis path, with no traceback in the inspected tail.

Observability caveat:

- `ai_debug.log` reached the 10MB limit and stopped showing new writes after
  `2026-06-04 01:53:32`, while `.run` files continued through
  `2026-06-04 02:07:46`. This baseline is usable for `.run` outcome metrics and
  available-log protocol checks, but future eval slices should keep this log
  coverage gap in mind.

Baseline decision:

- This is the first clean fixed eval baseline after the post-victory guard
  fixes.
- Proceed to the first small continued-training slice from
  `checkpoints\rl_combat_model_ep39_steps10991.pth`.
- After training, rerun the same eval protocol and compare against this baseline
  on win rate, average/median floor, death distribution, and protocol signals.

## Training Slice T1 - 2026-06-04

- Start: `2026-06-04T02:16:36+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Repo commit at launch: `4fa2cc7 Record clean fixed eval baseline`
- Command:
  `scripts/run_training_batch.py --max-games 5 --phase conservative --restart-guidance --truncate-log-after-backup`
- Result: stopped early after a stale card-select `choose` command crossed
  back to a rest-state frame.
- Completed `.run` files before stop: 3
- Wins: 0
- Win rate: 0.0%
- Average floor: 20.3
- Median floor: 16
- Max floor: 27

Death distribution before stop:

| Count | Killed by |
| ---: | --- |
| 1 | Sentry and Sphere |
| 1 | Slime Boss |
| 1 | The Guardian |

Training/checkpoint signal:

- The batch loaded `checkpoints\rl_combat_model_ep39_steps10991.pth`.
- It saved at least `rl_combat_model_ep1_steps11074.pth` and
  `rl_combat_model_ep4_steps11143.pth` before the stop.
- These checkpoints are not promoted; this slice did not complete a clean
  train-plus-eval comparison.

Protocol signal:

- `Invalid command: choose`: 1 event at `2026-06-04 02:18:52`.
- Live logs showed `CardSelectAction` selecting `Fiend Fire` from a smith
  grid, then the game returning to `REST` while a delayed choose response still
  arrived. The current advertised commands were
  `[potion, proceed, key, click, wait, state]`, so a queued or late
  `ChooseAction` needed to resync instead of sending `choose 0`.

Follow-up fix:

- `ChooseAction.execute()` now checks current `available_commands` and requests
  `state` instead of sending `choose` when the action is stale for the current
  screen.
- Regression:
  `test_choose_action_requests_state_when_choose_command_is_stale`.

Verification:

- Red: the new regression failed against the old behavior with
  `sent_messages == ["choose 0"]`.
- Green focused: card-select guard tests -> 6 passed.
- Green related: card-select, deferred-state, event-choice, shop-screen, and
  RL v2 action-space tests -> 71 passed.
- Green full suite: 1479 passed.

Next step: commit the stale choose guard, then rerun the same 5-game training
slice from the new commit. Only after a clean training slice should the workflow
return to the fixed 20-game eval comparison against Batch 7.

## Training Slice T1 Retry - 2026-06-04

- Start: `2026-06-04T02:37:36+08:00`
- Launch: controlled `restart_sts_modded.ps1 -FreshRun`
- Repo commit at launch: `647cdfd Guard stale choose commands`
- Pytest baseline at launch commit: 1479 passed.
- Command:
  `scripts/run_training_batch.py --max-games 5 --phase conservative --restart-guidance --truncate-log-after-backup`
- Result: completed 5 `.run` files and reached the configured max-games exit.
- Wins: 0
- Win rate: 0.0%
- Average floor: 16.8
- Median floor: 16
- Max floor: 18
- Average playtime: 73.8 seconds

Death distribution:

| Count | Killed by |
| ---: | --- |
| 3 | The Guardian |
| 1 | 3 Byrds |
| 1 | Hexaghost |

Run files:

| Run | Floor | Result |
| --- | ---: | --- |
| `1780511979.run` | 18 | killed by 3 Byrds |
| `1780512060.run` | 16 | killed by The Guardian |
| `1780512130.run` | 16 | killed by Hexaghost |
| `1780512201.run` | 16 | killed by The Guardian |
| `1780512286.run` | 16 | killed by The Guardian |

Training/checkpoint signal:

- The batch loaded and backed up
  `checkpoints\rl_combat_model_ep6_steps11308.pth`.
- New combat checkpoints written during the slice:
  `rl_combat_model_ep1_steps11436.pth`,
  `rl_combat_model_ep3_steps11542.pth`,
  `rl_combat_model_ep5_steps11635.pth`,
  `rl_combat_model_ep7_steps11732.pth`, and
  `rl_combat_model_ep9_steps11848.pth`.
- No checkpoint is promoted yet; this slice only proves the stale choose guard
  allowed bounded training to complete cleanly.

Protocol signal:

- `Invalid command:*`: 0 matching events in the current truncated
  `ai_debug.log` for this slice.
- `Traceback`: 0 matching events in the current truncated `ai_debug.log` for
  this slice.
- `CombatRLAgent error`: 0 matching events in the current truncated
  `ai_debug.log` for this slice.
- `TRANSITION_LATE_COMMAND_ERROR`: 0 matching events in the current truncated
  `ai_debug.log` for this slice.
- `Max games reached (5); exiting.` observed at `2026-06-04 02:44:50`.

Decision:

- Proceed to the fixed 20-game eval protocol from the latest trained combat RL
  checkpoint, then compare against Fixed Baseline Batch 7.
- Do not promote the checkpoint unless eval improves win/floor or failure
  distribution without adding protocol or mechanics risk.
