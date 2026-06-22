# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 3706
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=584, event=684, route=2262, shop=176
- Evidence quality: complete=3582, partial=124

## Bottled Agreement

- Current/Bottled action-id matches: 2620/3706

## Live Outcomes

- Matched outcomes included in gate: 447

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 3706, 'category_counts': {'event': 684, 'route': 2262, 'card_reward': 584, 'shop': 176}, 'complete_category_counts': {'event': 684, 'route': 2138, 'card_reward': 584, 'shop': 176}, 'matched_outcomes': 447}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
