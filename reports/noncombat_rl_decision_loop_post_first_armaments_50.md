# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 3355
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=500, event=610, route=2061, shop=184
- Evidence quality: complete=3240, partial=115

## Bottled Agreement

- Current/Bottled action-id matches: 2390/3355

## Live Outcomes

- Matched outcomes included in gate: 518

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 3355, 'category_counts': {'event': 610, 'route': 2061, 'card_reward': 500, 'shop': 184}, 'complete_category_counts': {'event': 610, 'route': 1946, 'card_reward': 500, 'shop': 184}, 'matched_outcomes': 518}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
