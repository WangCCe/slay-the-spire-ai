# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 447
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=62, event=86, route=272, shop=27
- Evidence quality: complete=431, partial=16

## Bottled Agreement

- Current/Bottled action-id matches: 326/447
- Oracle modes: native_bottled=447

## Current-vs-Bottled Disagreements

- Action-id disagreements: 105/447
- Complete high-confidence disagreements: 74
- By category: card_reward=48, event=1, route=51, shop=5

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (23x, high=23, complete=23, examples=trace:93, trace:94, trace:136)
- route: route:choice:0 -> route:choice:1 (16x, high=16, complete=16, examples=trace:153, trace:154, trace:388)
- card_reward: card_reward:take:cleave -> card_reward:skip (3x, high=0, complete=3, examples=trace:2, trace:105, trace:1313)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (3x, high=0, complete=3, examples=trace:600, trace:1503, trace:1795)
- card_reward: card_reward:take:true_grit -> card_reward:skip (3x, high=0, complete=3, examples=trace:38, trace:993, trace:1546)
- route: route:choice:0 -> route:choice:2 (3x, high=3, complete=3, examples=trace:1162, trace:1163, trace:1484)
- route: route:choice:1 -> route:choice:2 (3x, high=3, complete=3, examples=trace:1485, trace:1922, trace:1923)
- card_reward: card_reward:take:anger -> card_reward:skip (2x, high=0, complete=2, examples=trace:1449, trace:1572)
- card_reward: card_reward:take:armaments -> card_reward:skip (2x, high=0, complete=2, examples=trace:854, trace:1086)
- card_reward: card_reward:take:burning_pact -> card_reward:skip (2x, high=0, complete=2, examples=trace:763, trace:1524)
- card_reward: card_reward:take:combust -> card_reward:skip (2x, high=0, complete=2, examples=trace:199, trace:1810)
- card_reward: card_reward:take:headbutt -> card_reward:skip (2x, high=0, complete=2, examples=trace:967, trace:1299)

## Live Outcomes

- Matched outcomes included in gate: 220

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 447, 'category_counts': {'card_reward': 62, 'route': 272, 'event': 86, 'shop': 27}, 'complete_category_counts': {'card_reward': 62, 'route': 256, 'event': 86, 'shop': 27}, 'matched_outcomes': 220}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
