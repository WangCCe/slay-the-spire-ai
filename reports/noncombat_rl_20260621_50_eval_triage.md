# 2026-06-21 Non-Combat Eval And Outcome Triage

## Batch

- Launch: `run_training_batch.py --eval --max-games 50 --phase conservative`
- Window: `since-unix 1782048500`
- Runs: 50
- Victories: 0
- Best floor reached: 33

## Decision Loop Readiness

- Promotion status: allowed
- Samples: 364
- Categories: card_reward=63, event=65, route=228, shop=8
- Evidence quality: complete=352, partial=12
- Matched live outcomes included in gate: 171
- Formal non-combat RL training: still blocked by guard

## Cross-Batch Stability

- Baseline: `reports/noncombat_rl_decision_samples.jsonl`
- Candidate: `reports/noncombat_rl_decision_samples_20260621_50_eval.jsonl`
- Stable high-confidence mismatches: 5
- Policy-ready stable mismatches: 2

Stable policy candidates:

- `shop:leave -> shop:buy_card:perfected_strike` with baseline=1, candidate=1
- `card_reward:take:carnage -> card_reward:take:twin_strike` with baseline=1, candidate=1

Route diagnostics remain noisy:

- `route:choice:1 -> route:choice:0` with baseline=24, candidate=22
- `route:choice:0 -> route:choice:1` with baseline=12, candidate=16
- `route:choice:2 -> route:choice:0` with baseline=2, candidate=2

## Outcome Triage

Top deaths:

- Slime Boss: 9
- The Guardian: 8
- Hexaghost: 7
- Centurion and Healer: 5
- Champ: 4
- 3 Cultists: 3
- Collector: 2
- Cultist and Chosen: 2
- Exordium Wildlife: 2

## Decision

Do not change gameplay policy from the non-combat mismatch evidence alone. The two policy-ready stable mismatches are only one sample in each batch, while 24/50 runs died at Act 1 bosses and another 5 died to Centurion and Healer.

Next work should switch from non-combat mismatch fixes to outcome-driven failure audit, starting with Act 1 boss readiness: inspect Slime Boss, Guardian, and Hexaghost losses for deck damage/block shape, route risk, rest/upgrade choices, and combat damage taken before proposing a fix.
