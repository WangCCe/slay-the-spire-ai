# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 430
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=64, event=66, route=270, shop=30
- Evidence quality: complete=413, partial=17

## Bottled Agreement

- Current/Bottled action-id matches: 298/430
- Oracle modes: native_bottled=430

## Current-vs-Bottled Disagreements

- Action-id disagreements: 115/430
- Complete high-confidence disagreements: 81
- By category: card_reward=50, event=1, route=59, shop=5

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (36x, high=36, complete=36, examples=trace:328, trace:329, trace:343)
- route: route:choice:0 -> route:choice:2 (7x, high=7, complete=7, examples=trace:581, trace:1469, trace:1470)
- route: route:choice:0 -> route:choice:1 (6x, high=6, complete=6, examples=trace:324, trace:325, trace:369)
- card_reward: card_reward:take:clothesline -> card_reward:skip (4x, high=0, complete=4, examples=trace:439, trace:992, trace:1041)
- card_reward: card_reward:take:disarm -> card_reward:skip (4x, high=0, complete=4, examples=trace:651, trace:775, trace:1419)
- route: route:choice:2 -> route:choice:0 (4x, high=4, complete=4, examples=trace:633, trace:634, trace:1215)
- card_reward: card_reward:take:armaments -> card_reward:skip (3x, high=0, complete=3, examples=trace:630, trace:1910, trace:1938)
- card_reward: card_reward:take:cleave -> card_reward:skip (3x, high=0, complete=3, examples=trace:298, trace:851, trace:1142)
- card_reward: card_reward:take:headbutt -> card_reward:skip (3x, high=0, complete=3, examples=trace:18, trace:552, trace:1543)
- card_reward: card_reward:take:sever_soul -> card_reward:skip (3x, high=0, complete=3, examples=trace:1290, trace:1642, trace:1787)
- route: route:choice:1 -> route:choice:2 (3x, high=3, complete=3, examples=trace:580, trace:1575, trace:1576)
- route: route:choice:1 -> route:choice:3 (3x, high=3, complete=3, examples=trace:514, trace:515, trace:516)

## Live Outcomes

- Matched outcomes included in gate: 156

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 430, 'category_counts': {'card_reward': 64, 'route': 270, 'event': 66, 'shop': 30}, 'complete_category_counts': {'card_reward': 64, 'route': 253, 'event': 66, 'shop': 30}, 'matched_outcomes': 156}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
