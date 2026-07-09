# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 407
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=60, event=61, route=254, shop=32
- Evidence quality: complete=393, partial=14

## Bottled Agreement

- Current/Bottled action-id matches: 280/407
- Oracle modes: native_bottled=407

## Current-vs-Bottled Disagreements

- Action-id disagreements: 111/407
- Complete high-confidence disagreements: 85
- By category: card_reward=45, event=3, route=58, shop=5

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (28x, high=28, complete=28, examples=trace:58, trace:59, trace:67)
- route: route:choice:0 -> route:choice:1 (18x, high=18, complete=18, examples=trace:20, trace:21, trace:91)
- route: route:choice:0 -> route:choice:2 (4x, high=4, complete=4, examples=trace:1638, trace:1639, trace:1654)
- card_reward: card_reward:take:anger -> card_reward:skip (3x, high=0, complete=3, examples=trace:223, trace:1502, trace:1815)
- card_reward: card_reward:take:headbutt -> card_reward:skip (3x, high=0, complete=3, examples=trace:55, trace:1403, trace:1711)
- event: event:choice:0 -> event:choice:1 (3x, high=3, complete=3, examples=trace:476, trace:941, trace:945)
- card_reward: card_reward:take:cleave -> card_reward:skip (2x, high=0, complete=2, examples=trace:759, trace:1625)
- card_reward: card_reward:take:flex -> card_reward:skip (2x, high=0, complete=2, examples=trace:121, trace:1938)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (2x, high=0, complete=2, examples=trace:166, trace:1776)
- card_reward: card_reward:take:sever_soul -> card_reward:skip (2x, high=0, complete=2, examples=trace:17, trace:1924)
- card_reward: card_reward:take:true_grit -> card_reward:skip (2x, high=0, complete=2, examples=trace:192, trace:978)
- route: route:choice:0 -> route:choice:3 (2x, high=2, complete=2, examples=trace:1762, trace:1763)

## Live Outcomes

- Matched outcomes included in gate: 176

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 407, 'category_counts': {'event': 61, 'route': 254, 'card_reward': 60, 'shop': 32}, 'complete_category_counts': {'event': 61, 'route': 240, 'card_reward': 60, 'shop': 32}, 'matched_outcomes': 176}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
