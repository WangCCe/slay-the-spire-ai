# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: blocked
- Samples: 470
- Blocking reasons: missing_complete_shop_samples, missing_complete_event_samples, missing_complete_route_samples, missing_complete_card_reward_samples, candidate_actions_missing, matched_live_outcomes_missing

## Sample Coverage

- Categories: card_reward=56, event=101, route=268, shop=45
- Evidence quality: partial=470

## Bottled Agreement

- Current/Bottled action-id matches: 1/470

## Live Outcomes

- Matched outcomes included in gate: 0

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'missing', 'reward': 'present', 'evaluation': 'missing'}
- Metrics: {'sample_count': 470, 'category_counts': {'card_reward': 56, 'route': 268, 'shop': 45, 'event': 101}, 'complete_category_counts': {}, 'matched_outcomes': 0}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
