# Trainable Baseline Qualification Batch 1

## Batch Identity
- Commit: `40a92d0e13d510c89288f8392f4690adca46d269`
- Cutoff: `1783768251` (2026-07-11 19:10:51 CST)
- Mode: conservative eval, requested 25 games, no training
- Completion: failed at 1/25 new AI-marked runs; `Max games reached (25); exiting.` was absent

## Run Outcomes
- Victories: 0 of 1 completed fresh run
- Average floor: 16.0 across the one completed fresh run
- Maximum floor: 16
- Act 1 boss reach: 1
- Act 2 reach: 0
- Top death clusters: The Guardian (1)
- Fresh run: `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783768375.run` (AI marker `1783768378`, floor 16, `victory=false`, killed by The Guardian)
- Missing sample: 24 required fresh run records were not produced. The 25-run combat-failure diagnostic therefore mixed this run with 24 historical runs and is not used as Batch 1 outcome evidence.

## Execution Correctness
- Invalid commands: 0
- New gameplay exceptions: 39 failed attempts escaped `Coordinator.play_one_game` and were caught by the outer batch loop, all with `Wrong number of cards selected (provided 3, need 1)`
- CommunicationMod error-log exceptions attributable to the cutoff: 0
- Validated lethal prefix pass-throughs: 4
- Plan acknowledgements logged: 0
- Plan rejections: 0
- Lethal rejection quarantines: 0
- Completion marker: 0

## Raw Evidence Classification
- **A - GRID card-selection cardinality:** On the second live run, the floor 17 `TreasureRoomBoss` Astrolabe GRID required three cards total. After two cards were already selected, one selection remained, but the fallback repeatedly returned `CardSelectAction` with `['Shockwave', 'Fiend Fire', 'Shrug It Off']`; `CardSelectAction.execute` rejected the action before command emission because three cards were supplied when one remained. The unchanged GRID state then caused 39 failed attempts (`Game #2` through `Game #40`) while only one AI-marked run existed. This is a trace-supported legality failure that prevents run completion.
- **C - lethal pass-throughs:** Four `plan_kind=lethal decision=pass_through` actions (Flex, Anger, Strike, and Bash) were accepted, drained from the queue, and advanced the game state. No rejection or quarantine evidence accompanied them.
- **C - sim divergence:** The cutoff-bounded summary read 22,389 rows, skipped all 22,389 as pre-cutoff, and found 0 fresh events. There are no fresh high-impact divergence rows to classify.
- **C - command protocol:** No invalid-command log entry was present.

## Sim Divergence
- Fresh events: 0
- High-impact clusters: none in the sim-divergence trace
- Unresolved A-class clusters: 1 (GRID card-selection cardinality)

## Qualification Decision
- Batch status: failed
- Reason: a causally demonstrated A-class legality failure prevented the second run from leaving the boss-reward GRID and made the required 25-run completion impossible.
- Next action: add a focused regression for a partially completed Astrolabe GRID and fix the selector to honor the remaining card count before rerunning Batch 1. Do not start Batch 2.
