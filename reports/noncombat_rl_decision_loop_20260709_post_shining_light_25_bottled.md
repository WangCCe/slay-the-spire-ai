# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1583
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=220, event=338, route=944, shop=81
- Evidence quality: complete=1537, partial=46

## Bottled Agreement

- Current/Bottled action-id matches: 1141/1583
- Oracle modes: native_bottled=1583

## Current-vs-Bottled Disagreements

- Action-id disagreements: 389/1583
- Complete high-confidence disagreements: 288
- By category: card_reward=148, event=20, route=216, shop=5

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (111x, high=111, complete=111, examples=trace:193154, trace:193155, trace:193426)
- route: route:choice:0 -> route:choice:1 (70x, high=70, complete=70, examples=trace:193177, trace:193178, trace:193183)
- card_reward: card_reward:take:anger -> card_reward:skip (11x, high=0, complete=11, examples=trace:193461, trace:194234, trace:194933)
- card_reward: card_reward:take:armaments -> card_reward:skip (9x, high=0, complete=9, examples=trace:193118, trace:193502, trace:193598)
- event: event:choice:0 -> event:choice:1 (9x, high=9, complete=9, examples=trace:195012, trace:195350, trace:195681)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (8x, high=0, complete=8, examples=trace:193135, trace:193416, trace:193898)
- event: event:choice:1 -> event:choice:0 (8x, high=8, complete=8, examples=trace:193248, trace:193929, trace:194314)
- route: route:choice:0 -> route:choice:2 (8x, high=8, complete=8, examples=trace:193697, trace:193698, trace:196344)
- card_reward: card_reward:take:clothesline -> card_reward:skip (6x, high=0, complete=6, examples=trace:193367, trace:193667, trace:194526)
- card_reward: card_reward:take:headbutt -> card_reward:skip (6x, high=0, complete=6, examples=trace:194027, trace:195221, trace:195244)
- card_reward: card_reward:take:true_grit -> card_reward:skip (6x, high=0, complete=6, examples=trace:193346, trace:194366, trace:195261)
- route: route:choice:1 -> route:choice:2 (6x, high=6, complete=6, examples=trace:194236, trace:194237, trace:194723)

## Live Outcomes

- Matched outcomes included in gate: 580

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1583, 'category_counts': {'event': 338, 'card_reward': 220, 'route': 944, 'shop': 81}, 'complete_category_counts': {'event': 338, 'card_reward': 220, 'route': 898, 'shop': 81}, 'matched_outcomes': 580}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
