# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 3600
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=542, event=645, route=2203, shop=210
- Evidence quality: complete=3484, partial=116

## Bottled Agreement

- Current/Bottled action-id matches: 2542/3600

## Live Outcomes

- Matched outcomes included in gate: 621

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 3600, 'category_counts': {'event': 645, 'route': 2203, 'card_reward': 542, 'shop': 210}, 'complete_category_counts': {'event': 645, 'route': 2087, 'card_reward': 542, 'shop': 210}, 'matched_outcomes': 621}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
