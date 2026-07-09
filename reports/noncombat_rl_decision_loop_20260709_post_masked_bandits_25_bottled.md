# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1438
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=223, event=284, route=856, shop=75
- Evidence quality: complete=1396, partial=42

## Bottled Agreement

- Current/Bottled action-id matches: 1021/1438
- Oracle modes: native_bottled=1438

## Current-vs-Bottled Disagreements

- Action-id disagreements: 371/1438
- Complete high-confidence disagreements: 265
- By category: card_reward=166, event=8, route=186, shop=11

### Top Disagreement Pairs

- route: route:choice:0 -> route:choice:1 (76x, high=76, complete=76, examples=trace:193628, trace:193629, trace:193906)
- route: route:choice:1 -> route:choice:0 (74x, high=74, complete=74, examples=trace:193350, trace:193351, trace:193422)
- route: route:choice:0 -> route:choice:2 (12x, high=12, complete=12, examples=trace:193330, trace:193331, trace:194750)
- card_reward: card_reward:take:anger -> card_reward:skip (9x, high=0, complete=9, examples=trace:193643, trace:194428, trace:195040)
- card_reward: card_reward:take:clothesline -> card_reward:skip (8x, high=0, complete=8, examples=trace:193766, trace:194818, trace:195404)
- card_reward: card_reward:take:armaments -> card_reward:skip (7x, high=0, complete=7, examples=trace:195191, trace:196363, trace:198228)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (6x, high=0, complete=6, examples=trace:194574, trace:195164, trace:196222)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (6x, high=0, complete=6, examples=trace:194156, trace:194261, trace:195121)
- card_reward: card_reward:take:uppercut -> card_reward:skip (6x, high=0, complete=6, examples=trace:193958, trace:194797, trace:196696)
- event: event:choice:0 -> event:choice:1 (6x, high=6, complete=6, examples=trace:195286, trace:196897, trace:198431)
- route: route:choice:1 -> route:choice:2 (6x, high=6, complete=6, examples=trace:193828, trace:193829, trace:195003)
- route: route:choice:2 -> route:choice:0 (6x, high=6, complete=6, examples=trace:195915, trace:195916, trace:197654)

## Live Outcomes

- Matched outcomes included in gate: 439

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1438, 'category_counts': {'event': 284, 'route': 856, 'card_reward': 223, 'shop': 75}, 'complete_category_counts': {'event': 284, 'route': 814, 'card_reward': 223, 'shop': 75}, 'matched_outcomes': 439}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
