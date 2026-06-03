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
