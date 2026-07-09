# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 1705
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=260, event=302, route=1045, shop=98
- Evidence quality: complete=1646, partial=59

## Bottled Agreement

- Current/Bottled action-id matches: 1232/1705
- Oracle modes: native_bottled=1705

## Current-vs-Bottled Disagreements

- Action-id disagreements: 411/1705
- Complete high-confidence disagreements: 281
- By category: card_reward=187, event=6, route=208, shop=10

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (94x, high=94, complete=94, examples=trace:191941, trace:191942, trace:192297)
- route: route:choice:0 -> route:choice:1 (78x, high=78, complete=78, examples=trace:192165, trace:192166, trace:192302)
- card_reward: card_reward:take:clothesline -> card_reward:skip (16x, high=0, complete=16, examples=trace:193768, trace:194036, trace:194605)
- card_reward: card_reward:take:anger -> card_reward:skip (15x, high=0, complete=15, examples=trace:193336, trace:193803, trace:193843)
- route: route:choice:2 -> route:choice:0 (14x, high=14, complete=14, examples=trace:191866, trace:191867, trace:194164)
- card_reward: card_reward:take:true_grit -> card_reward:skip (8x, high=0, complete=8, examples=trace:191908, trace:193785, trace:193934)
- card_reward: card_reward:take:armaments -> card_reward:skip (7x, high=0, complete=7, examples=trace:194328, trace:194738, trace:196716)
- route: route:choice:0 -> route:choice:2 (6x, high=6, complete=6, examples=trace:193523, trace:193524, trace:197218)
- card_reward: card_reward:take:heavy_blade -> card_reward:skip (5x, high=0, complete=5, examples=trace:197269, trace:197286, trace:198190)
- card_reward: card_reward:take:hemokinesis -> card_reward:skip (5x, high=0, complete=5, examples=trace:192527, trace:195404, trace:198212)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (5x, high=0, complete=5, examples=trace:191968, trace:194414, trace:196068)
- event: event:choice:0 -> event:choice:1 (5x, high=5, complete=5, examples=trace:193497, trace:195300, trace:195501)

## Live Outcomes

- Matched outcomes included in gate: 547

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 1705, 'category_counts': {'event': 302, 'route': 1045, 'card_reward': 260, 'shop': 98}, 'complete_category_counts': {'event': 302, 'route': 986, 'card_reward': 260, 'shop': 98}, 'matched_outcomes': 547}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
