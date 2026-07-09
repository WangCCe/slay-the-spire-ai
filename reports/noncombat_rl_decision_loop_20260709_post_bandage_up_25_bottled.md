# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1675
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=273, event=292, route=1027, shop=83
- Evidence quality: complete=1620, partial=55

## Bottled Agreement

- Current/Bottled action-id matches: 1189/1675
- Oracle modes: native_bottled=1675

## Current-vs-Bottled Disagreements

- Action-id disagreements: 429/1675
- Complete high-confidence disagreements: 303
- By category: card_reward=199, event=10, route=210, shop=10

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (110x, high=110, complete=110, examples=trace:191913, trace:191914, trace:192591)
- route: route:choice:0 -> route:choice:1 (66x, high=66, complete=66, examples=trace:192788, trace:192789, trace:192862)
- route: route:choice:2 -> route:choice:0 (12x, high=12, complete=12, examples=trace:192180, trace:192181, trace:192715)
- card_reward: card_reward:take:anger -> card_reward:skip (11x, high=0, complete=11, examples=trace:193866, trace:194086, trace:194743)
- card_reward: card_reward:take:headbutt -> card_reward:skip (11x, high=0, complete=11, examples=trace:191950, trace:193138, trace:194565)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (10x, high=0, complete=10, examples=trace:193031, trace:194523, trace:194625)
- card_reward: card_reward:take:clothesline -> card_reward:skip (9x, high=0, complete=9, examples=trace:192064, trace:193010, trace:193447)
- card_reward: card_reward:take:true_grit -> card_reward:skip (9x, high=0, complete=9, examples=trace:192749, trace:192764, trace:193223)
- route: route:choice:1 -> route:choice:2 (8x, high=8, complete=8, examples=trace:195397, trace:195398, trace:195635)
- card_reward: card_reward:take:armaments -> card_reward:skip (6x, high=0, complete=6, examples=trace:192311, trace:192486, trace:194800)
- event: event:choice:0 -> event:choice:1 (6x, high=6, complete=6, examples=trace:192286, trace:195108, trace:196476)
- route: route:choice:0 -> route:choice:2 (6x, high=6, complete=6, examples=trace:192419, trace:192420, trace:196389)

## Live Outcomes

- Matched outcomes included in gate: 656

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1675, 'category_counts': {'event': 292, 'route': 1027, 'card_reward': 273, 'shop': 83}, 'complete_category_counts': {'event': 292, 'route': 972, 'card_reward': 273, 'shop': 83}, 'matched_outcomes': 656}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
