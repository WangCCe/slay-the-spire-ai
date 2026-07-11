# Trainable Baseline Qualification Batch 2 Retry 1

## Batch Identity

- Candidate: `f321cb05a40c808d3abfba8b977dfe8988b8ee47`.
- Cutoff: `1783787478` (2026-07-12 00:31:18 CST); marker baseline: 14,746.
- Config identity: `D:\anaconda\envs\stsai\python.exe` runs `scripts/run_training_batch.py --eval --max-games 25 --phase conservative --restart-guidance --truncate-log-after-backup --decision-trace-path D:/SteamLibrary/steamapps/common/SlayTheSpire/ai_decision_trace_clean.jsonl --sim-divergence-trace-path D:/SteamLibrary/steamapps/common/SlayTheSpire/sim_divergence_trace_clean.jsonl`. The live command contains no `--train` argument.
- Completion evidence: 25 markers (14,746 to 14,771), 25 unique post-cutoff Ironclad records, and exactly one `Max games reached (25); exiting.` marker. The wrapper and game PIDs exiting naturally is an operator observation; the durable completion evidence is the completion marker plus the post-run error-log lifecycle through post-analysis.
- This was an eval-only batch. Active `checkpoints/` creations or modifications after the cutoff: 0; newly trained checkpoints: 0. The startup archival step created two expected backup copies at 00:33:58 under `checkpoints_archive\training_batches`; these are archival copies, not trained checkpoints.

## Preserved Baselines And Raw Scope

- Prior-report SHA-256 values: `batch1.md` `22F0AA10A899EBBF94DBA6D10D27F3D5906F6C2C77DB7BA3D63D04B0E1EE9730`; `batch1_retry1.md` `609F42A15DD6037B365ECA815A04CBE2724A0A13AB93B9D2D98DD24821060D32`; eligible `batch1_retry2.md` `DABED49A496492D1D4CA5552B5C6137F1934D8A608C6C34B3423C915EB636A18`; failed `batch2.md` `9DAADD776DE264AED5AFA48B348272EA464254EEE45E93FDD305FCE28A0F860D`.
- Pre-launch sizes: active debug 9,553,901 bytes; `.1` 10,485,739; `.2` 10,485,710; error log 1,134,601; decision trace 2,024,715,217; sim trace 151,380,928.
- Final fresh raw set only: `ai_debug.log` 9,894,921 bytes, `.1` 10,485,702, and `.2` 10,485,712 (30,866,335 bytes total); error log 1,136,853 bytes; decision trace 2,048,908,436 bytes; sim trace 151,551,920 bytes. Stale debug rotations `.3` through `.5` were excluded.
- The error log has exactly five post-baseline lines (lines 8,753-8,757): maintenance, post-analysis, and restart guidance only. It has no post-baseline `Traceback`, exception, invalid-command, or card-count error.

## Marker-To-Run Pairing And Outcomes

Each post-baseline marker has one unique post-cutoff `.run` file. The save-to-marker delta is three seconds except pair 8, which is four seconds.

| # | AI marker | Run record | Floor | Victory | Killed by |
|---|---:|---|---:|---|---|
| 1 | 1783787730 | `1783787727.run` | 16 | false | Hexaghost |
| 2 | 1783787811 | `1783787808.run` | 16 | false | Slime Boss |
| 3 | 1783788037 | `1783788034.run` | 33 | false | Automaton |
| 4 | 1783788110 | `1783788107.run` | 16 | false | Slime Boss |
| 5 | 1783788224 | `1783788221.run` | 22 | false | Chosen and Byrds |
| 6 | 1783788322 | `1783788319.run` | 16 | false | Hexaghost |
| 7 | 1783788515 | `1783788512.run` | 30 | false | Sentry and Sphere |
| 8 | 1783788571 | `1783788567.run` | 11 | false | Gremlin Nob |
| 9 | 1783788656 | `1783788653.run` | 16 | false | Hexaghost |
| 10 | 1783788750 | `1783788747.run` | 16 | false | Hexaghost |
| 11 | 1783788811 | `1783788808.run` | 11 | false | Gremlin Gang |
| 12 | 1783788937 | `1783788934.run` | 25 | false | Shelled Parasite and Fungi |
| 13 | 1783789061 | `1783789058.run` | 18 | false | Spheric Guardian |
| 14 | 1783789111 | `1783789108.run` | 7 | false | 3 Sentries |
| 15 | 1783789189 | `1783789186.run` | 16 | false | Slime Boss |
| 16 | 1783789263 | `1783789260.run` | 16 | false | Hexaghost |
| 17 | 1783789394 | `1783789391.run` | 22 | false | Centurion and Healer |
| 18 | 1783789450 | `1783789447.run` | 16 | false | The Guardian |
| 19 | 1783789654 | `1783789651.run` | 29 | false | Sentry and Sphere |
| 20 | 1783789793 | `1783789790.run` | 22 | false | Centurion and Healer |
| 21 | 1783789845 | `1783789842.run` | 16 | false | Slime Boss |
| 22 | 1783789912 | `1783789909.run` | 11 | false | Gremlin Gang |
| 23 | 1783789978 | `1783789975.run` | 16 | false | Hexaghost |
| 24 | 1783790047 | `1783790044.run` | 16 | false | Hexaghost |
| 25 | 1783790134 | `1783790131.run` | 16 | false | The Guardian |

The batch has 0/25 victories, average floor 17.96, maximum floor 33, 21 Act 1 boss reaches, and 8 Act 2 reaches. The first-Ironclad-victory objective remains unmet.

## Command-Legality And Ordering Audit

- The decision trace was streamed line-by-line. It has exactly 6,898 post-cutoff rows: 42 `ScreenType.HAND_SELECT` `CardSelectAction` rows, 120 `ScreenType.GRID` `CardSelectAction` rows, and 586 `ProceedAction` rows, all with command `proceed`.
- No trace row has action command `confirm`; no `ProceedAction` occurs on either HAND_SELECT or GRID. The 42 low-level HAND_SELECT confirmations are therefore not trace-level `ProceedAction` emissions.
- HAND_SELECT: 44 card-key sends and 42 terminal-confirm sends. Every confirm diagnostic has `confirm` in the available-command list, follows a new card-key send, and has no duplicate-confirm ordering violation. There are no HAND_SELECT `ProceedAction` trace rows.
- GRID: 120 `CardSelectAction` returns. 119 returned `1/1`; one legitimate boss-reward screen returned `3/3`. All 120 returns were followed by an initial queue depth exactly `2 * selected-card-count`, proving a selector plus one-frame barrier per selected card; there were zero queue/cardinality mismatches. The `3/3` sequence started at queue depth six and remained callback-deferred while selected count advanced 0 -> 1 -> 2 before transition.
- GRID terminal confirmation: the 120 GRID returns partition into 93 legal serialized optional-confirm sends and 27 explicit skips. The one `3/3` case skipped after transition to CHEST. GRID `ProceedAction` rows: 0; rejected GRID confirms: 0. Thus no GRID `ProceedAction`/confirm race occurred.
- Across the three fresh debug segments: invalid commands 0; tracebacks 0; uncaught exceptions 0; `Wrong number of cards selected` 0; stuck signatures 0; cardinality signatures 0.
- Lethal path audit: 89 `plan_kind=lethal decision=pass_through` rows. Fresh logs contain 0 lethal veto, `[PLAN_ACK]`, rejection-failure, or quarantine diagnostics, and no pass-through row is paired with a command rejection or exception. Successful internal rejection calls are not logged and therefore cannot be counted exactly.

## Sim-Divergence Audit

`analysis_scripts/summarize_sim_divergence_trace.py --trace D:\SteamLibrary\steamapps\common\SlayTheSpire\sim_divergence_trace_clean.jsonl --since-unix 1783787478` streamed 22,437 rows, skipped 22,425 pre-cutoff rows, found 12 fresh events, and found no malformed rows.

| # | Floor / turn | Reason and action | Diff keys | Class |
|---|---|---|---|---|
| 1 | 8 / 4 | player-state, EndTurnAction | `player.block` | C |
| 2 | 4 / 4 | player-state, EndTurnAction | `player.block` | C |
| 3 | 19 / 4 | player-state, EndTurnAction | `player.block` | C |
| 4 | 33 / 2 | monster-state, EndTurnAction | `monsters[2].hp` | B |
| 5 | 11 / 3 | monster-state, Burning Pact | `monsters[0].gone`, `monsters[0].hp`, `monsters[1].hp` | B |
| 6 | 11 / 3 | monster-state, CardSelectAction | `monsters[0].gone`, `monsters[0].hp`, `monsters[1].hp` | B |
| 7 | 21 / 2 | player-state, EndTurnAction | `player.current_hp` | C |
| 8 | 7 / 12 | monster-state, EndTurnAction | `monsters[2].hp` | B |
| 9 | 18 / 4 | player-state, EndTurnAction | `player.block` | C |
| 10 | 28 / 9 | monster-state, EndTurnAction | `monsters[1].hp` | B |
| 11 | 14 / 4 | player-state, Headbutt+ | `player.energy` | C |
| 12 | 14 / 4 | player-state, CardSelectAction | `player.energy` | C |

- A-class: none. No event has demonstrated causal linkage to an invalid command, exception, selector-cardinality failure, or repeatable live mechanics impact.
- B-class: five isolated monster-state boundary rows. The floor-11 pair is the same state boundary observed across a play/select transition, not two demonstrated impacts.
- C-class: seven player block, HP, or energy timing rows. These are observation-boundary differences only; the floor-14 energy pair is likewise one boundary seen by two adjacent actions.

## Final Promotion Decision And Task State

Independent raw-evidence review approved the corrected evidence snapshot with SHA-256 `B1EBBC88C062883C488799179E42287EB8AE0193D2C081DAD408FD1386DAAA3F` and explicitly authorized final promotion. This completed no-training retry is eligible: it has all 25 unique marker/run pairs, one completion marker, zero gated command/exception/cardinality failures, and no demonstrated A-class sim-divergence cluster.

Eligible Batch 1 retry 2 and this Batch 2 retry 1 form **two consecutive clean 25-game batches**. The trainable behavior baseline is promoted and frozen at candidate `f321cb05a40c808d3abfba8b977dfe8988b8ee47`. No training has been started, and the first-Ironclad-victory objective remains unmet at 0/25 for this batch.

The separate lethal-investigation task 5.5 and GRID-fix tasks 4.5-4.7 are complete. The reviewed evidence and promotion task-state changes were committed as `cbc0853e`. Neither change is archived as part of this retry.
