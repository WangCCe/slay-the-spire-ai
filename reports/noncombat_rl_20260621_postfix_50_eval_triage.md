# 2026-06-21 Post-Fix 50-Game Eval Triage

## Batch

- Mode: no-training fresh eval
- Cutoff: 1782055300
- Runs: 50
- Victories: 0
- Best floor: 47
- Previous 50-game best floor: 33

## Outcome Summary

- Act 1 boss deaths remain the largest bottleneck: 26/50 post-fix runs.
- Slime Boss deaths improved from 9 to 5 after the Act 1 Perfected Strike reward fix.
- Guardian deaths increased from 8 to 11 and Hexaghost deaths increased from 7 to 10.
- Act 2/3 progress improved at the tail: one run reached floor 47, one reached floor 44, and multiple runs reached floor 33.

## Post-Fix Decision Loop

- Samples: 420
- Categories: shop=27, route=256, card_reward=68, event=69
- Complete samples: 406
- Matched outcomes: 260
- Promotion gate: allowed
- Formal non-combat RL training: still blocked by guard

## Stable Mismatch Triage

The stable policy-ready mismatches after comparing the pre-fix and post-fix 50-game batches are:

- `shop:purge:strike -> shop:buy_card:perfected_strike` with total 4 observations.
- `shop:leave -> shop:buy_card:perfected_strike` with total 3 observations.
- `card_reward:take:anger -> card_reward:take:dropkick` with total 2 observations.

The shop Perfected Strike cluster is the strongest next candidate because it repeats across both batches and matches a concrete code path: the shop currently prioritizes paid purge before card purchase, and card purchase normally requires preserving purge budget. That can make the agent remove a Strike before buying an affordable early Perfected Strike, then leave the shop without the scaling attack.

## Next Action

Add a regression for early Act 1 shops where the deck has high Strike-name density and an affordable Perfected Strike. The expected behavior is to buy the first supported Perfected Strike before spending gold on purge. Keep the fix narrow and reuse the existing Ironclad deck strategy gate rather than adding a separate shop-only card model.
