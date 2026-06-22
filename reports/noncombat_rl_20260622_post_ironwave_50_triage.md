# 2026-06-22 Post-IronWave 50-Game Eval Triage

## Batch

- Mode: no-training fresh eval
- Cutoff: `1782088549`
- Observed runs at or after cutoff: 51
- Victories: 0
- Best floor: 50
- Average floor: 22.8
- Wrapper/main Python exited after the batch; only the game window remained running.

## Outcome Triage

- Act 1 boss deaths: 18/51
  - Hexaghost: 7
  - The Guardian: 6
  - Slime Boss: 5
- Early deaths before Act 1 boss: 3/51
  - Gremlin Gang, Gremlin Nob, 3 Sentries
- Act 2 boss deaths: 7/51
  - Collector: 3
  - Automaton: 2
  - Champ: 2
- Act 2 hallway deaths:
  - Chosen and Byrds: 3
  - Shelled Parasite and Fungi: 3
  - 3 Cultists: 3
  - Sentry and Sphere: 3
  - Centurion and Healer: 2
  - 3 Byrds: 2
  - Other one-offs: Snecko, Book of Stabbing, Cultist and Chosen, Chosen, Shell Parasite
- Act 3 deaths: 2/51
  - Time Eater: 1
  - 4 Shapes: 1

## Decision Loop

- Samples: 3600
- Categories: card_reward=542, event=645, route=2203, shop=210
- Complete samples: 3484
- Matched outcomes: 621
- Promotion gate: allowed
- Formal non-combat RL training: still blocked by guard

This report was generated with `--trace-tail 100000`. The comparison baseline `reports/noncombat_rl_decision_samples_20260622_post_shopfix_50_eval.jsonl` used the shorter default trace tail, so coverage counts are not directly comparable.

## Mismatch Stability

Compared against `reports/noncombat_rl_decision_samples_20260622_post_shopfix_50_eval.jsonl`:

- Stable high-confidence mismatches: 13
- Policy-ready stable mismatches: 6
- Stable policy candidates:
  - `shop:buy_potion:block_potion -> shop:leave` (candidate=7)
  - `card_reward:skip -> card_reward:take:twin_strike` (candidate=5)
  - `card_reward:take:armaments -> card_reward:take:twin_strike` (candidate=3)
  - `card_reward:take:shrug_it_off -> card_reward:take:twin_strike` (candidate=2)
  - `card_reward:take:uppercut -> card_reward:take:pommel_strike` (candidate=2)
  - `card_reward:take:power_through -> card_reward:take:perfected_strike` (candidate=1)
- Route mismatches remain diagnostic-only.

## Read

The prior `card_reward:take:iron_wave -> card_reward:take:twin_strike` mismatch is absent from this full post-IronWave batch, supporting the `c69508bc` fix direction. The batch still did not reach a win and remains bottlenecked mostly by Act 1 boss combat plus Act 2 hallway/boss fights.

The clearest small noncombat fix from this batch was `card_reward:take:armaments -> card_reward:take:twin_strike`: three Act 1 samples, including a floor 5 Hexaghost run where current policy took first Armaments over Twin Strike with thin frontload. A regression now covers that trace shape and the reward guard now prefers Twin Strike over first Armaments only when Act 1 frontload is thin and Twin Strike is offered.

`potions_floor_usage` should not be treated as reliable failure evidence for these CommunicationMod runs. Live logs showed `PotionAction` reaching reward/follow-up states, while run records still left `potions_floor_usage` empty, likely because CommunicationMod manually calls `selectedPotion.use(...)` and `destroyPotion(...)` instead of the vanilla run-history path.

## Next Action

Run a fresh post-first-Armaments-guard no-training eval. If Act 1 boss deaths remain high, pivot to combat traces for Guardian/Hexaghost/Slime Boss rather than adding broader Bottled-style reward alignment. Keep shop Block Potion and route mismatches as diagnostics until they show direct outcome leverage.
