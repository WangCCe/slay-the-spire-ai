# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 389
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=64, event=57, route=242, shop=26
- Evidence quality: complete=375, partial=14

## Bottled Agreement

- Current/Bottled action-id matches: 267/389

## Live Outcomes

- Matched outcomes included in gate: 184

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 389, 'category_counts': {'route': 242, 'card_reward': 64, 'event': 57, 'shop': 26}, 'complete_category_counts': {'route': 228, 'card_reward': 64, 'event': 57, 'shop': 26}, 'matched_outcomes': 184}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
