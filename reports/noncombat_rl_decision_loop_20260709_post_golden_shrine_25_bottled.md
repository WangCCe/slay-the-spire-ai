# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 381
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=62, event=66, route=236, shop=17
- Evidence quality: complete=365, partial=16

## Bottled Agreement

- Current/Bottled action-id matches: 283/381
- Oracle modes: native_bottled=381

## Current-vs-Bottled Disagreements

- Action-id disagreements: 80/381
- Complete high-confidence disagreements: 54
- By category: card_reward=43, event=1, route=34, shop=2

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (16x, high=16, complete=16, examples=trace:4, trace:5, trace:168)
- route: route:choice:0 -> route:choice:1 (10x, high=10, complete=10, examples=trace:708, trace:709, trace:818)
- card_reward: card_reward:take:anger -> card_reward:skip (7x, high=0, complete=7, examples=trace:571, trace:776, trace:1385)
- card_reward: card_reward:take:headbutt -> card_reward:bowl (2x, high=0, complete=2, examples=trace:1092, trace:1126)
- card_reward: card_reward:take:uppercut -> card_reward:skip (2x, high=0, complete=2, examples=trace:609, trace:728)
- card_reward: card_reward:take:whirlwind -> card_reward:skip (2x, high=0, complete=2, examples=trace:367, trace:1899)
- route: route:choice:1 -> route:choice:2 (2x, high=2, complete=2, examples=trace:306, trace:307)
- route: route:choice:1 -> route:choice:3 (2x, high=2, complete=2, examples=trace:1484, trace:1485)
- route: route:choice:2 -> route:choice:0 (2x, high=2, complete=2, examples=trace:1268, trace:1269)
- route: route:choice:2 -> route:choice:1 (2x, high=2, complete=2, examples=trace:925, trace:926)
- card_reward: card_reward:skip -> card_reward:take:perfected_strike (1x, high=1, complete=1, examples=trace:525)
- card_reward: card_reward:skip -> card_reward:take:twin_strike (1x, high=1, complete=1, examples=trace:1220)

## Live Outcomes

- Matched outcomes included in gate: 198

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 381, 'category_counts': {'route': 236, 'card_reward': 62, 'event': 66, 'shop': 17}, 'complete_category_counts': {'route': 220, 'card_reward': 62, 'event': 66, 'shop': 17}, 'matched_outcomes': 198}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
