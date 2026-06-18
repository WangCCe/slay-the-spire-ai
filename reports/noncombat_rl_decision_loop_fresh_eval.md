# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 397
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=60, event=76, route=246, shop=15
- Evidence quality: complete=383, partial=14

## Bottled Agreement

- Current/Bottled action-id matches: 264/397

## Live Outcomes

- Matched outcomes included in gate: 145

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 397, 'category_counts': {'event': 76, 'route': 246, 'card_reward': 60, 'shop': 15}, 'complete_category_counts': {'event': 76, 'route': 232, 'card_reward': 60, 'shop': 15}, 'matched_outcomes': 145}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
