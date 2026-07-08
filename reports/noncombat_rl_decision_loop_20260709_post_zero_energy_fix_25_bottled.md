# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1642
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=248, event=284, route=1012, shop=98
- Evidence quality: complete=1588, partial=54

## Bottled Agreement

- Current/Bottled action-id matches: 1161/1642
- Oracle modes: native_bottled=1642

## Current-vs-Bottled Disagreements

- Action-id disagreements: 424/1642
- Complete high-confidence disagreements: 299
- By category: card_reward=194, event=11, route=202, shop=17

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (94x, high=94, complete=94, examples=trace:192386, trace:192518, trace:192519)
- route: route:choice:0 -> route:choice:1 (72x, high=72, complete=72, examples=trace:192013, trace:192014, trace:192096)
- card_reward: card_reward:take:anger -> card_reward:skip (10x, high=0, complete=10, examples=trace:192187, trace:192728, trace:193947)
- card_reward: card_reward:take:clothesline -> card_reward:skip (10x, high=0, complete=10, examples=trace:192448, trace:193014, trace:193247)
- route: route:choice:1 -> route:choice:2 (10x, high=10, complete=10, examples=trace:193145, trace:193146, trace:193210)
- card_reward: card_reward:take:armaments -> card_reward:skip (8x, high=0, complete=8, examples=trace:192106, trace:192914, trace:193914)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (8x, high=0, complete=8, examples=trace:193747, trace:194828, trace:195378)
- route: route:choice:2 -> route:choice:0 (8x, high=8, complete=8, examples=trace:193761, trace:193762, trace:197594)
- route: route:choice:2 -> route:choice:1 (8x, high=8, complete=8, examples=trace:193037, trace:193038, trace:193672)
- event: event:choice:0 -> event:choice:1 (7x, high=7, complete=7, examples=trace:192675, trace:193698, trace:196689)
- card_reward: card_reward:take:hemokinesis -> card_reward:skip (6x, high=0, complete=6, examples=trace:192093, trace:196041, trace:196477)
- card_reward: card_reward:take:immolate -> card_reward:skip (6x, high=0, complete=6, examples=trace:196241, trace:196608, trace:197866)

## Live Outcomes

- Matched outcomes included in gate: 609

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1642, 'category_counts': {'event': 284, 'card_reward': 248, 'route': 1012, 'shop': 98}, 'complete_category_counts': {'event': 284, 'card_reward': 248, 'route': 958, 'shop': 98}, 'matched_outcomes': 609}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
