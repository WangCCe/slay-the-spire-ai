# Post Shop Frontload 47-Run Triage

Batch start: `2026-06-22 13:35:40`

## Batch Outcome

- Recorded runs: 47
- Wins: 0
- Best floor: 37
- Average floor: 20.9
- Top deaths: The Guardian 13, Automaton 6, Slime Boss 6, Hexaghost 4
- Act 1 boss deaths: 23/47
- Runtime note: `ai_debug.log` reported `Max games reached (50); exiting`, but
  `runs/ai_games.txt` and `.run` files only provided 47 current-batch records.
  This triage uses the verifiable `.run` records.

## Non-Combat Sample Report

- Report: `reports/noncombat_rl_decision_loop_post_shop_frontload_47.md`
- Samples: 3182
- Coverage: card_reward=490, event=587, route=1924, shop=181
- Complete samples: 3072
- Matched outcomes: 718
- Promotion status: allowed

## Shop Fix Verification

The prior shop bug did not recur in the new trace:

- Shop `Block Potion` buys after this fix: 5
- Cases where `Block Potion` was bought while `Carnage`, `Twin Strike`, or
  `Clothesline` was still affordable: 0

## Stable Mismatch Triage

Compared against `reports/noncombat_rl_decision_samples_20260622_post_shopfix_50_eval.jsonl`.

Policy-ready repeated mismatches:

- `shop:buy_potion:block_potion -> shop:leave`: baseline=1, candidate=4
- `card_reward:skip -> card_reward:take:twin_strike`: baseline=1, candidate=3
- `card_reward:take:armaments -> card_reward:take:pommel_strike`: baseline=1, candidate=3
- `card_reward:take:shrug_it_off -> card_reward:take:twin_strike`: baseline=1, candidate=2

Run-record audit of the 23 Act 1 boss deaths found 4 clear pre-boss choices where
`Armaments`, `Shrug It Off`, or `SKIP` displaced `Pommel Strike` or `Twin Strike`.

## Fix Candidate

Repeated evidence supports one narrow card-reward fix:

- Before Act 1 boss, with frontload count still below 5, prefer `Pommel Strike`
  over the first `Armaments` when both are offered.
- Keep existing deck strategy and evaluator gates intact.
- Do not add a new `Shrug It Off` rule yet: the direct regression shape already
  passes under current scoring, so more evidence is needed before changing it.

## Verification

- Red regression:
  `test_act1_reward_prefers_pommel_strike_over_first_armaments_when_frontload_is_thin`
- Adjacent guard:
  `test_act1_reward_prefers_twin_strike_over_shrug_when_frontload_is_thin`
- Full card reward guard file: 100 passed
- Full pytest: 2163 passed
