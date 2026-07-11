# Trainable Baseline Qualification Batch 1 Retry 1

## Batch Identity
- Commit: `36c294dde0d6308a33f509a550ef57f846e7d8d0`
- Cutoff: `1783772162` (2026-07-11 20:16:02 CST)
- Mode: conservative eval, requested 25 games, no training
- Completion: failed at 10/25 new AI-marked runs; `Max games reached (25); exiting.` was absent

## GRID Regression
- Partial GRID callbacks: 0 observed
- GRID callbacks: 91 successful selections across the active and rotated fresh logs (90 selected 1/1 remaining card; one selected 2/2 remaining cards)
- GRID cardinality exceptions: 0
- Evidence: one transient state reported `selected=1, num_cards=2`, but its callback was correctly deferred while the second queued selection executed. No partial-GRID callback occurred, and the exact two-selected/one-remaining Astrolabe case did not replay. Every observed callback selected exactly its logged remaining count.

## Run Outcomes
- Victories: 0 of 10 completed fresh runs
- Average floor: 21.7
- Maximum floor: 33
- Act 1 boss reach: 9
- Act 2 reach: 7
- Top death clusters: Snake Plant (2), Snecko (2), Slavers (1), Automaton (1), Slime Boss (1), 3 Sentries (1), Centurion and Healer (1), The Guardian (1)

| # | AI marker | Run path | Floor | Victory | Killed by |
|---|---:|---|---:|---|---|
| 1 | 1783772347 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783772344.run` | 22 | false | Snake Plant |
| 2 | 1783772518 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783772515.run` | 25 | false | Slavers |
| 3 | 1783772678 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783772675.run` | 33 | false | Automaton |
| 4 | 1783772751 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783772748.run` | 16 | false | Slime Boss |
| 5 | 1783772924 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783772921.run` | 21 | false | Snecko |
| 6 | 1783773035 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783773032.run` | 23 | false | Snecko |
| 7 | 1783773113 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783773110.run` | 13 | false | 3 Sentries |
| 8 | 1783773252 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783773249.run` | 27 | false | Snake Plant |
| 9 | 1783773430 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783773427.run` | 21 | false | Centurion and Healer |
| 10 | 1783773510 | `D:\SteamLibrary\steamapps\common\SlayTheSpire\runs\IRONCLAD\1783773507.run` | 16 | false | The Guardian |

Runs 11 through 25 and their AI markers do not exist because the retry stopped at the first causally demonstrated A-class failure. The required 25-run combat-failure diagnostic therefore mixed these 10 runs with 15 historical runs and is excluded from retry outcome metrics.

## Execution Correctness
- Invalid commands: 1 command rejection (3 log occurrences for callback, agent error, and game error)
- New uncaught gameplay exceptions: 0
- Lethal pass-throughs: 56 across the active and rotated fresh logs
- Plan rejections: 0
- Lethal quarantines: 0
- `[PLAN_ACK]` rows: 0
- Completion markers: 0

At 2026-07-11 20:38:53 CST on floor 7, turn 3, the fallback returned `ProceedAction` while `screen=ScreenType.HAND_SELECT`. That emitted `confirm`, but CommunicationMod allowed only `[end, key, click, wait, state]` and rejected it as `Invalid command: confirm`. The queue recovered and gameplay continued, but a command-legality rejection violates the qualification gate.

## Sim Divergence
- Fresh events: 8 (22,397 rows read, 22,389 skipped before cutoff, 0 malformed)
- High-impact clusters: none; no fresh trace row established a deterministic A-class mechanics failure
- B-class raw rows: two `Iron Wave`/`Juggernaut` random-target rows and two Gremlin/Thorns/block-order rows
- C-class raw rows: two Looter escape/block-retention boundaries, one Bronze Automaton summon-order row, and one Distilled Chaos multi-card potion row
- Unresolved A-class clusters: 0 in sim divergence; 1 overall from command legality

## Qualification Decision
- Retry status: failed
- Reason: one causally demonstrated A-class `HAND_SELECT`/`ProceedAction` command-legality cluster occurred before 25 runs and the completion marker.
- Next action: add a focused regression for HAND_SELECT fallback confirmation and fix the selector before restarting Batch 1. Do not start the second consecutive batch.
