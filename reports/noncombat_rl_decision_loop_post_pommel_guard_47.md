# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 3157
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=455, event=578, route=1938, shop=186
- Evidence quality: complete=3050, partial=107

## Bottled Agreement

- Current/Bottled action-id matches: 2271/3157

## Live Outcomes

- Matched outcomes included in gate: 717

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 3157, 'category_counts': {'event': 578, 'route': 1938, 'card_reward': 455, 'shop': 186}, 'complete_category_counts': {'event': 578, 'route': 1831, 'card_reward': 455, 'shop': 186}, 'matched_outcomes': 717}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
