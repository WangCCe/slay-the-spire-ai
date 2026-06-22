# 2026-06-22 Post-Reward-Fix Pre-IronWave 50-Game Eval Triage

## Batch

- Mode: no-training fresh eval
- Cutoff: 1782082768
- Runs: 50
- Victories: 0
- Best floor: 47
- Average floor: 22.5

## Outcome Triage

- Act 1 boss deaths: 22/50
  - The Guardian: 11
  - Slime Boss: 8
  - Hexaghost: 3
- Act 2 boss deaths: 12/50
  - Automaton: 8
  - Collector: 4
- Act 2 hallway deaths:
  - 3 Cultists: 3
  - Snake Plant: 2
  - Sentry and Sphere: 2
  - Exordium Wildlife: 2
  - Other one-offs: 3 Byrds, 4 Shapes, Blue Slaver, Centurion and Healer, Cultist and Chosen, Shelled Parasite and Fungi, Spheric Guardian

## Decision Loop

- Samples: 3706
- Categories: card_reward=584, event=684, route=2262, shop=176
- Complete samples: 3582
- Matched outcomes: 447
- Promotion gate: allowed
- Formal non-combat RL training: still blocked by guard

This report was generated with `--trace-tail 100000`; older 2026-06-22 post-shopfix reports used the shorter default tail and have lower sample counts, so coverage counts are not directly comparable.

## Mismatch Stability

Compared against `reports/noncombat_rl_decision_samples_20260622_post_shopfix_50_eval.jsonl`:

- Stable high-confidence mismatches: 11
- Policy-ready stable mismatches: 5
- Stable policy candidates:
  - `shop:buy_potion:block_potion -> shop:leave` (candidate=7)
  - `card_reward:skip -> card_reward:take:twin_strike` (candidate=3)
  - `card_reward:take:anger -> card_reward:take:flame_barrier` (candidate=1)
  - `card_reward:take:iron_wave -> card_reward:take:twin_strike` (candidate=1)
  - `card_reward:take:shrug_it_off -> card_reward:take:twin_strike` (candidate=1)
- Route mismatches remain diagnostic-only.

## Read

The already-fixed `card_reward:take:iron_wave -> card_reward:take:twin_strike` case was present in this batch and is now covered by `c69508bc`. The broader batch is still not healthy: no wins, Act 1 boss deaths remain high, and later failures concentrate around Automaton and Collector. Combat logs also show combat RL repeatedly returning low-value potion or end-turn actions in Act 2 boss fights, with guards doing most of the salvage work.

## Next Action

Run a fresh post-IronWave-fix eval batch from cutoff `1782088549`. If Act 1 boss deaths remain high, audit card rewards around skipped or underpicked early damage before making route changes. If Act 1 stabilizes but Automaton/Collector remain dominant, pivot to combat decision traces for Act 2 bosses rather than expanding non-combat RL training.
