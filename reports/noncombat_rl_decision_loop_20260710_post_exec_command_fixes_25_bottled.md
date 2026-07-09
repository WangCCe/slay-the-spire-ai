# Non-Combat RL Decision Loop Readiness

## Summary

- Promotion status: allowed
- Samples: 373
- Blocking reasons: none

## Sample Coverage

- Categories: card_reward=70, event=61, route=224, shop=18
- Evidence quality: complete=363, partial=10

## Bottled Agreement

- Current/Bottled action-id matches: 256/373
- Oracle modes: native_bottled=373

## Current-vs-Bottled Disagreements

- Action-id disagreements: 106/373
- Complete high-confidence disagreements: 67
- By category: card_reward=53, event=2, route=48, shop=3

### Top Disagreement Pairs

- route: route:choice:0 -> route:choice:1 (22x, high=22, complete=22, examples=trace:50, trace:51, trace:181)
- route: route:choice:1 -> route:choice:0 (20x, high=20, complete=20, examples=trace:262, trace:263, trace:479)
- card_reward: card_reward:take:iron_wave -> card_reward:skip (3x, high=0, complete=3, examples=trace:801, trace:1396, trace:1419)
- card_reward: card_reward:take:spot_weakness -> card_reward:skip (3x, high=0, complete=3, examples=trace:518, trace:1315, trace:1886)
- card_reward: card_reward:take:whirlwind -> card_reward:skip (3x, high=0, complete=3, examples=trace:156, trace:174, trace:1113)
- card_reward: card_reward:take:anger -> card_reward:skip (2x, high=0, complete=2, examples=trace:94, trace:1176)
- card_reward: card_reward:take:anger -> card_reward:take:twin_strike (2x, high=2, complete=2, examples=trace:551, trace:1512)
- card_reward: card_reward:take:carnage -> card_reward:skip (2x, high=0, complete=2, examples=trace:818, trace:1086)
- card_reward: card_reward:take:cleave -> card_reward:skip (2x, high=0, complete=2, examples=trace:1779, trace:1844)
- card_reward: card_reward:take:flex -> card_reward:skip (2x, high=0, complete=2, examples=trace:638, trace:1956)
- card_reward: card_reward:take:headbutt -> card_reward:bowl (2x, high=0, complete=2, examples=trace:254, trace:396)
- card_reward: card_reward:take:headbutt -> card_reward:skip (2x, high=0, complete=2, examples=trace:189, trace:1978)

## Live Outcomes

- Matched outcomes included in gate: 216

## Reward readiness

- Status: present

## Promotion Gate

- Readiness: {'state': 'present', 'action': 'present', 'reward': 'present', 'evaluation': 'present'}
- Metrics: {'sample_count': 373, 'category_counts': {'card_reward': 70, 'route': 224, 'event': 61, 'shop': 18}, 'complete_category_counts': {'card_reward': 70, 'route': 214, 'event': 61, 'shop': 18}, 'matched_outcomes': 216}

## Training Guard

- Formal non-combat RL training: blocked
- Guard: not_started_by_this_change

## Combat RL Smoke

- Command: `"D:\anaconda\envs\stsai\python.exe" scripts\run_training_batch.py --python "D:\anaconda\envs\stsai\python.exe" --game-dir "D:\SteamLibrary\steamapps\common\SlayTheSpire" --agent combat_rl --eval --max-games 1 --dry-run`
