# Non-Combat RL Decision Loop Readiness

This export evidence-presence gate does not authorize formal non-combat RL training or live-policy promotion.

## Summary

- Export evidence-presence gate: passed
- Samples: 1453
- Evidence-presence blocking reasons: none

## Sample Coverage

- Categories: card_reward=236, event=253, route=882, shop=82
- Evidence quality: complete=1409, partial=44

## Bottled Agreement

- Current/Bottled action-id matches: 1041/1453
- Oracle modes: native_bottled=1453

## Current-vs-Bottled Disagreements

- Action-id disagreements: 364/1453
- Complete high-confidence disagreements: 255
- By category: card_reward=162, event=7, route=186, shop=9

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (94x, high=94, complete=94, examples=trace:871057, trace:871058, trace:871064)
- route: route:choice:0 -> route:choice:1 (56x, high=56, complete=56, examples=trace:871069, trace:871070, trace:871347)
- route: route:choice:1 -> route:choice:2 (12x, high=12, complete=12, examples=trace:871001, trace:871002, trace:871432)
- route: route:choice:2 -> route:choice:0 (12x, high=12, complete=12, examples=trace:872878, trace:872879, trace:874555)
- card_reward: card_reward:take:anger -> card_reward:skip (9x, high=0, complete=9, examples=trace:871478, trace:872070, trace:872329)
- card_reward: card_reward:take:true_grit -> card_reward:skip (8x, high=0, complete=8, examples=trace:871290, trace:873415, trace:874705)
- card_reward: card_reward:take:headbutt -> card_reward:skip (7x, high=0, complete=7, examples=trace:873022, trace:873652, trace:874620)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (7x, high=0, complete=7, examples=trace:871761, trace:873475, trace:874175)
- card_reward: card_reward:take:clothesline -> card_reward:skip (6x, high=0, complete=6, examples=trace:872116, trace:873173, trace:873537)
- card_reward: card_reward:take:uppercut -> card_reward:skip (6x, high=0, complete=6, examples=trace:871017, trace:871085, trace:872741)
- route: route:choice:0 -> route:choice:2 (6x, high=6, complete=6, examples=trace:872397, trace:872398, trace:873363)
- card_reward: card_reward:take:carnage -> card_reward:skip (5x, high=0, complete=5, examples=trace:872307, trace:872889, trace:874658)

## Live Outcomes

- Matched decision rows: 488
- Unique non-null trajectory groups: 14
- Unique trajectory victories: 0

## Export Evidence-Presence Gate

- Audit-field presence: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Audit metrics: {'sample_count': 1453, 'category_counts': {'event': 253, 'route': 882, 'card_reward': 236, 'shop': 82}, 'complete_category_counts': {'event': 253, 'route': 838, 'card_reward': 236, 'shop': 82}, 'matched_outcomes': 488}
- Scope: Audit-field presence does not establish reward validity, off-policy evaluation (OPE) support, formal non-combat RL readiness, or live policy promotion.

## Readiness Boundaries

- Formal non-combat RL training: blocked
- Live policy promotion: blocked
- Off-policy evaluation: unsupported
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
