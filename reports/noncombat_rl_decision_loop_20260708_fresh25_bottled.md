# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1688
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=244, event=295, route=1034, shop=115
- Evidence quality: complete=1629, partial=59

## Bottled Agreement

- Current/Bottled action-id matches: 1172/1688
- Oracle modes: native_bottled=1688

## Current-vs-Bottled Disagreements

- Action-id disagreements: 447/1688
- Complete high-confidence disagreements: 340
- By category: card_reward=178, event=35, route=215, shop=19

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (130x, high=130, complete=130, examples=trace:192233, trace:192234, trace:192247)
- route: route:choice:0 -> route:choice:1 (48x, high=48, complete=48, examples=trace:192287, trace:192288, trace:192321)
- event: event:choice:0 -> event:choice:1 (21x, high=21, complete=21, examples=trace:192253, trace:192289, trace:193259)
- card_reward: card_reward:take:clothesline -> card_reward:skip (11x, high=0, complete=11, examples=trace:192912, trace:193008, trace:195250)
- card_reward: card_reward:take:anger -> card_reward:skip (9x, high=0, complete=9, examples=trace:192422, trace:192506, trace:193516)
- event: event:choice:1 -> event:choice:0 (9x, high=9, complete=9, examples=trace:192965, trace:193026, trace:193412)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (8x, high=0, complete=8, examples=trace:192311, trace:193288, trace:194591)
- route: route:choice:2 -> route:choice:1 (8x, high=8, complete=8, examples=trace:193237, trace:193238, trace:193773)
- route: route:choice:1 -> route:choice:2 (7x, high=7, complete=7, examples=trace:195318, trace:195319, trace:195320)
- card_reward: card_reward:take:headbutt -> card_reward:skip (6x, high=0, complete=6, examples=trace:194028, trace:194267, trace:195365)
- route: route:choice:2 -> route:choice:0 (6x, high=6, complete=6, examples=trace:195789, trace:195790, trace:198433)
- card_reward: card_reward:take:armaments -> card_reward:skip (5x, high=0, complete=5, examples=trace:192722, trace:194184, trace:198450)

## Live Outcomes

- Matched outcomes included in gate: 638

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1688, 'category_counts': {'event': 295, 'route': 1034, 'card_reward': 244, 'shop': 115}, 'complete_category_counts': {'event': 295, 'route': 975, 'card_reward': 244, 'shop': 115}, 'matched_outcomes': 638}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
