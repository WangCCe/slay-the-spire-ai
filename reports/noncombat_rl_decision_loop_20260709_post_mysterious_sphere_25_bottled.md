# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1677
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=251, event=315, route=1006, shop=105
- Evidence quality: complete=1621, partial=56

## Bottled Agreement

- Current/Bottled action-id matches: 1207/1677
- Oracle modes: native_bottled=1677

## Current-vs-Bottled Disagreements

- Action-id disagreements: 410/1677
- Complete high-confidence disagreements: 282
- By category: card_reward=183, event=6, route=210, shop=11

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (102x, high=102, complete=102, examples=trace:191719, trace:191720, trace:192870)
- route: route:choice:0 -> route:choice:1 (62x, high=62, complete=62, examples=trace:192225, trace:192226, trace:192358)
- route: route:choice:0 -> route:choice:2 (14x, high=14, complete=14, examples=trace:191762, trace:191763, trace:193587)
- card_reward: card_reward:take:anger -> card_reward:skip (12x, high=0, complete=12, examples=trace:193119, trace:193688, trace:195295)
- card_reward: card_reward:take:clothesline -> card_reward:skip (10x, high=0, complete=10, examples=trace:191822, trace:192917, trace:193139)
- route: route:choice:2 -> route:choice:0 (10x, high=10, complete=10, examples=trace:193238, trace:193239, trace:194209)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (8x, high=0, complete=8, examples=trace:191944, trace:192418, trace:192498)
- route: route:choice:1 -> route:choice:2 (8x, high=8, complete=8, examples=trace:195281, trace:195282, trace:195841)
- card_reward: card_reward:take:headbutt -> card_reward:skip (6x, high=0, complete=6, examples=trace:191797, trace:191961, trace:192784)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (6x, high=0, complete=6, examples=trace:193600, trace:193971, trace:197440)
- route: route:choice:2 -> route:choice:1 (6x, high=6, complete=6, examples=trace:195520, trace:195521, trace:196640)
- card_reward: card_reward:take:corruption -> card_reward:skip (5x, high=0, complete=5, examples=trace:194795, trace:195186, trace:195514)

## Live Outcomes

- Matched outcomes included in gate: 674

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1677, 'category_counts': {'event': 315, 'route': 1006, 'card_reward': 251, 'shop': 105}, 'complete_category_counts': {'event': 315, 'route': 950, 'card_reward': 251, 'shop': 105}, 'matched_outcomes': 674}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
