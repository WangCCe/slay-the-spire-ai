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
