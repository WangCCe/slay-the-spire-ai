# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 364
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=63, event=65, route=228, shop=8
- Evidence quality: complete=352, partial=12

## Bottled Agreement

- Current/Bottled action-id matches: 255/364

## Live Outcomes

- Matched outcomes included in gate: 171

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 364, 'category_counts': {'card_reward': 63, 'route': 228, 'event': 65, 'shop': 8}, 'complete_category_counts': {'card_reward': 63, 'route': 216, 'event': 65, 'shop': 8}, 'matched_outcomes': 171}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
