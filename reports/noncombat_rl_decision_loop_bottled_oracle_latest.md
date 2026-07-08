# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: blocked
- Samples: 382
- Blocking reasons: matched_live_outcomes_missing

## Sample Coverage

- Categories: card_reward=52, event=82, route=228, shop=20
- Evidence quality: complete=368, partial=14

## Bottled Agreement

- Current/Bottled action-id matches: 296/382
- Oracle modes: native_bottled=382

## Current-vs-Bottled Disagreements

- Action-id disagreements: 71/382
- Complete high-confidence disagreements: 47
- By category: card_reward=36, event=4, route=28, shop=3

### Top Disagreement Pairs

- route: route:choice:0 -> route:choice:1 (12x, high=12, complete=12, examples=trace:1, trace:2, trace:873)
- route: route:choice:1 -> route:choice:0 (6x, high=6, complete=6, examples=trace:463, trace:464, trace:774)
- route: route:choice:0 -> route:choice:2 (4x, high=4, complete=4, examples=trace:583, trace:584, trace:1469)
- route: route:choice:2 -> route:choice:0 (4x, high=4, complete=4, examples=trace:820, trace:821, trace:1790)
- card_reward: card_reward:take:headbutt -> card_reward:skip (3x, high=0, complete=3, examples=trace:1494, trace:1779, trace:1809)
- card_reward: card_reward:take:anger -> card_reward:skip (2x, high=0, complete=2, examples=trace:1128, trace:1832)
- card_reward: card_reward:take:clothesline -> card_reward:skip (2x, high=0, complete=2, examples=trace:841, trace:1407)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (2x, high=0, complete=2, examples=trace:1263, trace:1750)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (2x, high=0, complete=2, examples=trace:359, trace:535)
- card_reward: card_reward:take:pommel_strike -> card_reward:take:thunderclap (2x, high=2, complete=2, examples=trace:460, trace:478)
- card_reward: card_reward:take:true_grit -> card_reward:skip (2x, high=0, complete=2, examples=trace:501, trace:1386)
- card_reward: card_reward:take:wild_strike -> card_reward:skip (2x, high=0, complete=2, examples=trace:718, trace:743)

## Live Outcomes

- Matched outcomes included in gate: 0

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'missing'}
- Metrics: {'sample_count': 382, 'category_counts': {'route': 228, 'event': 82, 'card_reward': 52, 'shop': 20}, 'complete_category_counts': {'route': 214, 'event': 82, 'card_reward': 52, 'shop': 20}, 'matched_outcomes': 0}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
