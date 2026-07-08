# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1585
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=229, event=276, route=994, shop=86
- Evidence quality: complete=1528, partial=57

## Bottled Agreement

- Current/Bottled action-id matches: 1102/1585
- Oracle modes: native_bottled=1585

## Current-vs-Bottled Disagreements

- Action-id disagreements: 423/1585
- Complete high-confidence disagreements: 312
- By category: card_reward=169, event=22, route=219, shop=13

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (110x, high=110, complete=110, examples=trace:192723, trace:192724, trace:192913)
- route: route:choice:0 -> route:choice:1 (58x, high=58, complete=58, examples=trace:192878, trace:192879, trace:193256)
- route: route:choice:1 -> route:choice:2 (12x, high=12, complete=12, examples=trace:193445, trace:193446, trace:194164)
- route: route:choice:2 -> route:choice:1 (12x, high=12, complete=12, examples=trace:192595, trace:192596, trace:194941)
- card_reward: card_reward:take:uppercut -> card_reward:skip (10x, high=0, complete=10, examples=trace:194652, trace:195626, trace:196180)
- route: route:choice:2 -> route:choice:0 (10x, high=10, complete=10, examples=trace:193626, trace:193627, trace:193877)
- event: event:choice:1 -> event:choice:0 (8x, high=8, complete=8, examples=trace:193250, trace:193485, trace:195649)
- route: route:choice:0 -> route:choice:2 (8x, high=8, complete=8, examples=trace:194339, trace:194340, trace:194851)
- card_reward: card_reward:take:headbutt -> card_reward:skip (7x, high=0, complete=7, examples=trace:193893, trace:194437, trace:196373)
- card_reward: card_reward:take:true_grit -> card_reward:skip (7x, high=0, complete=7, examples=trace:192893, trace:193327, trace:193827)
- event: event:choice:0 -> event:choice:2 (7x, high=7, complete=7, examples=trace:193258, trace:194166, trace:194327)
- card_reward: card_reward:take:anger -> card_reward:skip (6x, high=0, complete=6, examples=trace:192606, trace:192835, trace:193226)

## Live Outcomes

- Matched outcomes included in gate: 734

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1585, 'category_counts': {'event': 276, 'route': 994, 'card_reward': 229, 'shop': 86}, 'complete_category_counts': {'event': 276, 'route': 937, 'card_reward': 229, 'shop': 86}, 'matched_outcomes': 734}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
