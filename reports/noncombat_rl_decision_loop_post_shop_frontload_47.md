# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 3182
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=490, event=587, route=1924, shop=181
- Evidence quality: complete=3072, partial=110

## Bottled Agreement

- Current/Bottled action-id matches: 2241/3182

## Live Outcomes

- Matched outcomes included in gate: 718

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 3182, 'category_counts': {'event': 587, 'route': 1924, 'card_reward': 490, 'shop': 181}, 'complete_category_counts': {'event': 587, 'route': 1814, 'card_reward': 490, 'shop': 181}, 'matched_outcomes': 718}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
