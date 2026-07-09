# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1656
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=238, event=302, route=1025, shop=91
- Evidence quality: complete=1603, partial=53

## Bottled Agreement

- Current/Bottled action-id matches: 1209/1656
- Oracle modes: native_bottled=1656

## Current-vs-Bottled Disagreements

- Action-id disagreements: 391/1656
- Complete high-confidence disagreements: 275
- By category: card_reward=166, event=11, route=205, shop=9

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (117x, high=117, complete=117, examples=trace:192037, trace:192038, trace:192052)
- route: route:choice:0 -> route:choice:1 (58x, high=58, complete=58, examples=trace:191978, trace:191979, trace:192280)
- route: route:choice:2 -> route:choice:0 (14x, high=14, complete=14, examples=trace:193344, trace:193345, trace:194101)
- card_reward: card_reward:take:carnage -> card_reward:skip (9x, high=0, complete=9, examples=trace:193434, trace:193708, trace:193794)
- card_reward: card_reward:take:headbutt -> card_reward:skip (9x, high=0, complete=9, examples=trace:192029, trace:192498, trace:192640)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (8x, high=0, complete=8, examples=trace:193080, trace:194535, trace:194622)
- event: event:choice:0 -> event:choice:1 (7x, high=7, complete=7, examples=trace:192758, trace:194777, trace:195127)
- card_reward: card_reward:take:anger -> card_reward:skip (6x, high=0, complete=6, examples=trace:192080, trace:192753, trace:192787)
- card_reward: card_reward:take:armaments -> card_reward:skip (6x, high=0, complete=6, examples=trace:195234, trace:196287, trace:196863)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (6x, high=0, complete=6, examples=trace:192243, trace:194011, trace:194857)
- card_reward: card_reward:take:uppercut -> card_reward:skip (6x, high=0, complete=6, examples=trace:194211, trace:195015, trace:198053)
- route: route:choice:1 -> route:choice:2 (6x, high=6, complete=6, examples=trace:195967, trace:195968, trace:196072)

## Live Outcomes

- Matched outcomes included in gate: 517

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1656, 'category_counts': {'event': 302, 'route': 1025, 'card_reward': 238, 'shop': 91}, 'complete_category_counts': {'event': 302, 'route': 972, 'card_reward': 238, 'shop': 91}, 'matched_outcomes': 517}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
