# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1795
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=277, event=339, route=1101, shop=78
- Evidence quality: complete=1738, partial=57

## Bottled Agreement

- Current/Bottled action-id matches: 1305/1795
- Oracle modes: native_bottled=1795

## Current-vs-Bottled Disagreements

- Action-id disagreements: 425/1795
- Complete high-confidence disagreements: 289
- By category: card_reward=185, event=27, route=206, shop=7

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (112x, high=112, complete=112, examples=trace:191283, trace:191284, trace:191308)
- route: route:choice:0 -> route:choice:1 (61x, high=61, complete=61, examples=trace:191366, trace:191367, trace:191771)
- card_reward: card_reward:take:headbutt -> card_reward:skip (20x, high=0, complete=20, examples=trace:191565, trace:191886, trace:192167)
- card_reward: card_reward:take:clothesline -> card_reward:skip (16x, high=0, complete=16, examples=trace:192547, trace:192641, trace:192763)
- event: event:choice:0 -> event:choice:1 (13x, high=13, complete=13, examples=trace:191537, trace:191579, trace:194902)
- event: event:choice:1 -> event:choice:0 (12x, high=12, complete=12, examples=trace:191306, trace:191570, trace:192650)
- route: route:choice:0 -> route:choice:2 (12x, high=12, complete=12, examples=trace:192049, trace:192050, trace:192205)
- card_reward: card_reward:take:anger -> card_reward:skip (8x, high=0, complete=8, examples=trace:191397, trace:192228, trace:192337)
- card_reward: card_reward:take:armaments -> card_reward:skip (8x, high=0, complete=8, examples=trace:191608, trace:194985, trace:195141)
- route: route:choice:1 -> route:choice:2 (8x, high=8, complete=8, examples=trace:194415, trace:194416, trace:194962)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (6x, high=0, complete=6, examples=trace:191997, trace:192829, trace:193325)
- card_reward: card_reward:take:true_grit -> card_reward:skip (6x, high=0, complete=6, examples=trace:192156, trace:192273, trace:196429)

## Live Outcomes

- Matched outcomes included in gate: 621

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1795, 'category_counts': {'event': 339, 'route': 1101, 'card_reward': 277, 'shop': 78}, 'complete_category_counts': {'event': 339, 'route': 1044, 'card_reward': 277, 'shop': 78}, 'matched_outcomes': 621}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
