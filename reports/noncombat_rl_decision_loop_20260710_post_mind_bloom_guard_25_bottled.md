# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 412
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=59, event=75, route=260, shop=18
- Evidence quality: complete=396, partial=16

## Bottled Agreement

- Current/Bottled action-id matches: 299/412
- Oracle modes: native_bottled=412

## Current-vs-Bottled Disagreements

- Action-id disagreements: 96/412
- Complete high-confidence disagreements: 69
- By category: card_reward=45, event=3, route=46, shop=2

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (24x, high=24, complete=24, examples=trace:60, trace:61, trace:98)
- route: route:choice:0 -> route:choice:1 (14x, high=14, complete=14, examples=trace:390, trace:391, trace:467)
- card_reward: card_reward:take:anger -> card_reward:skip (5x, high=0, complete=5, examples=trace:114, trace:291, trace:504)
- route: route:choice:0 -> route:choice:2 (4x, high=4, complete=4, examples=trace:347, trace:348, trace:1420)
- route: route:choice:2 -> route:choice:0 (4x, high=4, complete=4, examples=trace:277, trace:278, trace:934)
- event: event:choice:0 -> event:choice:1 (3x, high=3, complete=3, examples=trace:760, trace:1724, trace:1728)
- card_reward: card_reward:take:disarm -> card_reward:skip (2x, high=0, complete=2, examples=trace:429, trace:1438)
- card_reward: card_reward:take:havoc -> card_reward:skip (2x, high=0, complete=2, examples=trace:538, trace:1710)
- card_reward: card_reward:take:headbutt -> card_reward:skip (2x, high=0, complete=2, examples=trace:932, trace:1577)
- card_reward: card_reward:take:hemokinesis -> card_reward:skip (2x, high=0, complete=2, examples=trace:950, trace:1870)
- card_reward: card_reward:skip -> card_reward:take:dropkick (1x, high=1, complete=1, examples=trace:1941)
- card_reward: card_reward:skip -> card_reward:take:perfected_strike (1x, high=1, complete=1, examples=trace:1298)

## Live Outcomes

- Matched outcomes included in gate: 232

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 412, 'category_counts': {'route': 260, 'card_reward': 59, 'event': 75, 'shop': 18}, 'complete_category_counts': {'route': 244, 'card_reward': 59, 'event': 75, 'shop': 18}, 'matched_outcomes': 232}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
