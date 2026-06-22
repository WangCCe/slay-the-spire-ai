# Post First Armaments Guard 50-Run Triage

Cutoff: `1782097502`

## Batch Outcome

- Runs: 50
- Wins: 0
- Best floor: 38
- Average floor: 21.0
- Top deaths: Hexaghost 13, The Guardian 8, Slime Boss 4, Collector 4
- Act 1 boss deaths: 25/50

The prior Act 1 `Armaments` over `Twin Strike` regression stayed fixed in the target
window. The only remaining same-label occurrence was a floor 21 Act 2 pick, outside
the repaired early-frontload guard.

## Non-Combat Sample Report

- Report: `reports/noncombat_rl_decision_loop_post_first_armaments_50.md`
- Samples: 3355
- Coverage: card_reward=500, event=610, route=2061, shop=184
- Complete samples: 3240
- Matched outcomes: 518
- Promotion status: allowed

## Stable Mismatch Triage

Compared against `reports/noncombat_rl_decision_samples_20260622_post_shopfix_50_eval.jsonl`.

Policy-ready repeated mismatches:

- `shop:buy_potion:block_potion -> shop:leave`: baseline=1, candidate=5
- Card reward singletons: each baseline=1, candidate=1

The card reward singletons are not enough for another reward-policy patch. The shop
cluster is repeated and matches the current failure shape: early Act 1 decks are
dying to bosses and some shops spend remaining post-purge gold on Block Potion
while affordable frontload cards are still available.

## Fix Candidate

Trace evidence from `unix_time=1782099577`:

- Floor 4 shop, after paid purge: gold 70, hp 71/80
- Affordable cards still available: `Carnage` price 69, `Twin Strike` price 26
- Potion available: `Block Potion` price 48
- Current action: buy `Block Potion`
- Follow-up state: gold 22, no affordable frontload purchase possible, then leave

Root cause: post-purge card buying only allowed `Offering`, `Battle Trance`, and
`Shockwave`, so Act 1 frontload cards were skipped before potion buying ran.

Implemented minimal fix: allow `Carnage`, `Twin Strike`, and `Clothesline` as
post-purge shop card priorities. Existing deck-strategy and price checks still
gate the final purchase.

## Verification

- Red regression:
  `tests/test_shop_screen_guards.py::test_shop_screen_buys_act1_frontload_after_purge_before_block_potion`
- Focused adjacent checks:
  `test_shop_screen_skips_fire_potion_after_purge_when_no_priority_purchase_is_available`
  and `test_shop_screen_skips_strength_potion_when_no_priority_purchase_is_available`
- Full shop guard file: 25 passed
- Full pytest: 2161 passed
