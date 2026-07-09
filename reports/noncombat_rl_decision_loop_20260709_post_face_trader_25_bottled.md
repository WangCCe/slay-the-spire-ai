# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 365
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=57, event=63, route=226, shop=19
- Evidence quality: complete=351, partial=14

## Bottled Agreement

- Current/Bottled action-id matches: 277/365
- Oracle modes: native_bottled=365

## Current-vs-Bottled Disagreements

- Action-id disagreements: 74/365
- Complete high-confidence disagreements: 57
- By category: card_reward=33, route=40, shop=1

### Top Disagreement Pairs

- route: route:choice:1 -> route:choice:0 (20x, high=20, complete=20, examples=trace:150, trace:151, trace:177)
- route: route:choice:0 -> route:choice:1 (8x, high=8, complete=8, examples=trace:159, trace:160, trace:1011)
- route: route:choice:2 -> route:choice:0 (6x, high=6, complete=6, examples=trace:155, trace:156, trace:389)
- card_reward: card_reward:take:anger -> card_reward:skip (2x, high=0, complete=2, examples=trace:1215, trace:1820)
- card_reward: card_reward:take:cleave -> card_reward:skip (2x, high=0, complete=2, examples=trace:497, trace:807)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (2x, high=0, complete=2, examples=trace:548, trace:1875)
- card_reward: card_reward:take:true_grit -> card_reward:skip (2x, high=0, complete=2, examples=trace:1244, trace:1429)
- route: route:choice:0 -> route:choice:2 (2x, high=2, complete=2, examples=trace:1823, trace:1824)
- route: route:choice:0 -> route:choice:4 (2x, high=2, complete=2, examples=trace:683, trace:684)
- route: route:choice:2 -> route:choice:1 (2x, high=2, complete=2, examples=trace:448, trace:449)
- card_reward: card_reward:take:anger -> card_reward:take:twin_strike (1x, high=1, complete=1, examples=trace:1268)
- card_reward: card_reward:take:armaments -> card_reward:skip (1x, high=0, complete=1, examples=trace:202)

## Live Outcomes

- Matched outcomes included in gate: 229

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 365, 'category_counts': {'route': 226, 'event': 63, 'card_reward': 57, 'shop': 19}, 'complete_category_counts': {'event': 63, 'card_reward': 57, 'route': 212, 'shop': 19}, 'matched_outcomes': 229}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
