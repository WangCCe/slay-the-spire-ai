# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 420
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=68, event=69, route=256, shop=27
- Evidence quality: complete=406, partial=14

## Bottled Agreement

- Current/Bottled action-id matches: 280/420

## Live Outcomes

- Matched outcomes included in gate: 260

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 420, 'category_counts': {'shop': 27, 'route': 256, 'card_reward': 68, 'event': 69}, 'complete_category_counts': {'shop': 27, 'route': 242, 'card_reward': 68, 'event': 69}, 'matched_outcomes': 260}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
