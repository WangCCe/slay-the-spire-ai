# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1666
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=278, event=292, route=1000, shop=96
- Evidence quality: complete=1612, partial=54

## Bottled Agreement

- Current/Bottled action-id matches: 1165/1666
- Oracle modes: native_bottled=1666

## Current-vs-Bottled Disagreements

- Action-id disagreements: 444/1666
- Complete high-confidence disagreements: 313
- By category: card_reward=200, event=21, route=212, shop=11

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (90x, high=90, complete=90, examples=trace:192413, trace:192414, trace:192437)
- route: route:choice:0 -> route:choice:1 (72x, high=72, complete=72, examples=trace:192647, trace:192648, trace:192867)
- card_reward: card_reward:take:clothesline -> card_reward:skip (14x, high=0, complete=14, examples=trace:192644, trace:193173, trace:193301)
- route: route:choice:0 -> route:choice:2 (10x, high=10, complete=10, examples=trace:192698, trace:192699, trace:193488)
- route: route:choice:2 -> route:choice:0 (10x, high=10, complete=10, examples=trace:192822, trace:192823, trace:193286)
- event: event:choice:0 -> event:choice:1 (9x, high=9, complete=9, examples=trace:195099, trace:195288, trace:197088)
- event: event:choice:1 -> event:choice:0 (9x, high=9, complete=9, examples=trace:193063, trace:194144, trace:195292)
- card_reward: card_reward:take:anger -> card_reward:skip (8x, high=0, complete=8, examples=trace:192735, trace:194549, trace:194575)
- card_reward: card_reward:take:cleave -> card_reward:skip (7x, high=0, complete=7, examples=trace:193217, trace:193621, trace:195283)
- card_reward: card_reward:take:headbutt -> card_reward:skip (7x, high=0, complete=7, examples=trace:193591, trace:193974, trace:194290)
- card_reward: card_reward:take:armaments -> card_reward:skip (6x, high=0, complete=6, examples=trace:195111, trace:195242, trace:195684)
- route: route:choice:1 -> route:choice:2 (6x, high=6, complete=6, examples=trace:195889, trace:195890, trace:198911)

## Live Outcomes

- Matched outcomes included in gate: 491

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1666, 'category_counts': {'event': 292, 'route': 1000, 'card_reward': 278, 'shop': 96}, 'complete_category_counts': {'event': 292, 'route': 946, 'card_reward': 278, 'shop': 96}, 'matched_outcomes': 491}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
