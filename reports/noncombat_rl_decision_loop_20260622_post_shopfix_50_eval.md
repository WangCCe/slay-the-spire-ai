# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 408
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=64, event=71, route=249, shop=24
- Evidence quality: complete=394, partial=14

## Bottled Agreement

- Current/Bottled action-id matches: 280/408

## Live Outcomes

- Matched outcomes included in gate: 198

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 408, 'category_counts': {'route': 249, 'shop': 24, 'card_reward': 64, 'event': 71}, 'complete_category_counts': {'route': 235, 'shop': 24, 'card_reward': 64, 'event': 71}, 'matched_outcomes': 198}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
