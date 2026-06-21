# 2026-06-22 Post-Shop-Fix 50-Game Eval Triage

## Batch

- Mode: no-training fresh eval
- Cutoff: 1782061718
- Runs: 50
- Victories: 0
- Best floor: 33
- Average floor: 21.5
- Average playtime: 99s

## Decision Loop

- Samples: 408
- Categories: card_reward=64, event=71, route=249, shop=24
- Complete samples: 394
- Matched outcomes: 198
- Promotion gate: allowed
- Formal non-combat RL training: still blocked by guard

## Mismatch Stability

Compared against `reports/noncombat_rl_decision_samples_20260621_postfix_50_eval.jsonl`:

- Stable high-confidence mismatches: 4
- Policy-ready stable mismatches: 0
- Stable mismatches are now route diagnostics only:
  - `route:choice:1 -> route:choice:0`
  - `route:choice:0 -> route:choice:1`
  - `route:choice:1 -> route:choice:2`
  - `route:choice:2 -> route:choice:3`

The shop `Perfected Strike` cluster no longer appears as a stable policy-ready mismatch after `eef1e60f`.

## Outcome Triage

- Act 1 boss deaths: 25/50
  - Hexaghost: 9
  - Slime Boss: 8
  - The Guardian: 8
- Act 2/3 deaths:
  - Sentry and Sphere: 5
  - Centurion and Healer: 4
  - Snake Plant: 3
  - Collector: 3
  - Champ: 3
  - Automaton: 2
  - Other one-offs: 3 Cultists, Red Slaver, Gremlin Leader, Cultist and Chosen, Shelled Parasite and Fungi

## Read

The shop fix cleaned up the repeated non-combat policy mismatch, but this batch did not improve the outer objective: no victory and best floor regressed from the prior post-fix best floor 47 to 33. Treat that as noisy but not solved. With no policy-ready non-combat mismatch left, the next high-value loop should pivot to Act 1 boss and Act 2 entry audits rather than route policy changes, because route mismatches remain diagnostic-only and heavily attribution-noisy.

## Next Action

Audit repeated Act 1 boss losses from this batch, starting with Hexaghost and Guardian, then Slime Boss. Look for concrete combat/deck-readiness bugs before changing route policy. If the boss audit does not produce an A-class fix, move to Act 2 entry fights, especially Sentry and Sphere plus Centurion and Healer.
