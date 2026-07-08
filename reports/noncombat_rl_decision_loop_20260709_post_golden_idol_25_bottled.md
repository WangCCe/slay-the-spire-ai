# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1839
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=270, event=342, route=1112, shop=115
- Evidence quality: complete=1775, partial=64

## Bottled Agreement

- Current/Bottled action-id matches: 1316/1839
- Oracle modes: native_bottled=1839

## Current-vs-Bottled Disagreements

- Action-id disagreements: 455/1839
- Complete high-confidence disagreements: 328
- By category: card_reward=191, event=18, route=225, shop=21

### Top Disagreement Pairs

- route: route:choice:0 -> route:choice:1 (103x, high=103, complete=103, examples=trace:191528, trace:191529, trace:191577)
- route: route:choice:1 -> route:choice:0 (87x, high=87, complete=87, examples=trace:192116, trace:192117, trace:192503)
- event: event:choice:0 -> event:choice:1 (15x, high=15, complete=15, examples=trace:191601, trace:192319, trace:193306)
- card_reward: card_reward:take:headbutt -> card_reward:skip (13x, high=0, complete=13, examples=trace:191868, trace:193919, trace:193941)
- card_reward: card_reward:take:clothesline -> card_reward:skip (10x, high=0, complete=10, examples=trace:192359, trace:193568, trace:194438)
- route: route:choice:1 -> route:choice:2 (10x, high=10, complete=10, examples=trace:191511, trace:191512, trace:192495)
- card_reward: card_reward:take:anger -> card_reward:skip (9x, high=0, complete=9, examples=trace:191574, trace:192770, trace:193142)
- route: route:choice:0 -> route:choice:2 (8x, high=8, complete=8, examples=trace:193124, trace:193125, trace:194213)
- card_reward: card_reward:take:armaments -> card_reward:skip (7x, high=0, complete=7, examples=trace:192691, trace:193631, trace:195208)
- card_reward: card_reward:take:uppercut -> card_reward:skip (7x, high=0, complete=7, examples=trace:191768, trace:192171, trace:195267)
- card_reward: card_reward:take:cleave -> card_reward:skip (6x, high=0, complete=6, examples=trace:192596, trace:194519, trace:195343)
- card_reward: card_reward:take:havoc -> card_reward:skip (6x, high=0, complete=6, examples=trace:194550, trace:195490, trace:195714)

## Live Outcomes

- Matched outcomes included in gate: 604

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1839, 'category_counts': {'event': 342, 'route': 1112, 'card_reward': 270, 'shop': 115}, 'complete_category_counts': {'event': 342, 'route': 1048, 'card_reward': 270, 'shop': 115}, 'matched_outcomes': 604}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
