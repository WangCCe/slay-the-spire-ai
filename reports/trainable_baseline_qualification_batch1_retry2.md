# Trainable Baseline Qualification Batch 1 Retry 2

## Batch Identity
- Candidate: `cba66c5dd7de53fda9de12ebd5f23769fd4f155d` (`docs: approve hand select confirmation fix`); reviewed behavior commit: `1501ebf4`.
- Cutoff: `1783776731` (2026-07-11 21:32:11 CST); marker baseline: 14,706.
- Config identity: `D:\anaconda\envs\stsai\python.exe` runs `scripts/run_training_batch.py --eval --max-games 25 --phase conservative --restart-guidance --truncate-log-after-backup --decision-trace-path D:/SteamLibrary/steamapps/common/SlayTheSpire/ai_decision_trace_clean.jsonl --sim-divergence-trace-path D:/SteamLibrary/steamapps/common/SlayTheSpire/sim_divergence_trace_clean.jsonl`. No `--train` argument was present.
- Launch: one `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_sts_modded.ps1 -FreshRun` invocation at 21:33 CST. The helper stopped one prior ModTheSpire Java process and moved both Ironclad autosaves before launch.
- Completion: 25 new markers (14,706 to 14,731), 25 paired Ironclad records, and exactly one `Max games reached (25); exiting.` marker.

## Preserved Baselines
- Prior report `reports/trainable_baseline_qualification_batch1.md`: SHA-256 `22F0AA10A899EBBF94DBA6D10D27F3D5906F6C2C77DB7BA3D63D04B0E1EE9730`.
- Prior report `reports/trainable_baseline_qualification_batch1_retry1.md`: SHA-256 `609F42A15DD6037B365ECA815A04CBE2724A0A13AB93B9D2D98DD24821060D32`.
- Pre-launch sizes: `ai_debug.log` 9,524,304 bytes, `ai_debug.log.1` 10,485,648 bytes, `communication_mod_errors.log` 1,130,854 bytes, decision trace 1,983,868,946 bytes, sim-divergence trace 150,982,140 bytes.
- Fresh debug evidence comprises active `ai_debug.log` plus `.1`, `.2`, and `.3`: 4 segments, 31,774,190 bytes. The error-log delta is 18 wrapper lifecycle lines only; it contains no gameplay exception or command rejection.

## Run Outcomes
- Victories: 0 of 25. Average floor: 18.96. Maximum floor: 33. Act 1 boss reach: 23. Act 2 reach: 7.
- Death clusters: The Guardian 10; Slime Boss 4; Gremlin Gang, Hexaghost, and Automaton 2 each; 3 Cultists, Champ, 3 Byrds, Masked Bandits, and Collector 1 each.
- Marker-to-run timestamps consistently differ by 3-4 seconds because exporter save time precedes AI marker time; each pairing is unique and within five seconds.

| # | AI marker | Run record | Floor | Victory | Killed by |
|---|---:|---|---:|---|---|
| 1 | 1783776933 | `1783776929.run` | 16 | false | The Guardian |
| 2 | 1783777128 | `1783777124.run` | 31 | false | 3 Cultists |
| 3 | 1783777211 | `1783777207.run` | 16 | false | The Guardian |
| 4 | 1783777283 | `1783777279.run` | 16 | false | The Guardian |
| 5 | 1783777381 | `1783777377.run` | 16 | false | Slime Boss |
| 6 | 1783777552 | `1783777548.run` | 33 | false | Champ |
| 7 | 1783777626 | `1783777622.run` | 16 | false | The Guardian |
| 8 | 1783777733 | `1783777730.run` | 16 | false | The Guardian |
| 9 | 1783777795 | `1783777792.run` | 10 | false | Gremlin Gang |
| 10 | 1783777875 | `1783777872.run` | 16 | false | Hexaghost |
| 11 | 1783778051 | `1783778047.run` | 33 | false | Automaton |
| 12 | 1783778096 | `1783778092.run` | 7 | false | Gremlin Gang |
| 13 | 1783778208 | `1783778204.run` | 18 | false | 3 Byrds |
| 14 | 1783778308 | `1783778304.run` | 16 | false | The Guardian |
| 15 | 1783778389 | `1783778385.run` | 16 | false | Slime Boss |
| 16 | 1783778514 | `1783778510.run` | 20 | false | Masked Bandits |
| 17 | 1783778607 | `1783778603.run` | 16 | false | Slime Boss |
| 18 | 1783778698 | `1783778694.run` | 16 | false | The Guardian |
| 19 | 1783778794 | `1783778790.run` | 16 | false | The Guardian |
| 20 | 1783778906 | `1783778903.run` | 16 | false | Hexaghost |
| 21 | 1783778984 | `1783778981.run` | 16 | false | The Guardian |
| 22 | 1783779163 | `1783779159.run` | 33 | false | Collector |
| 23 | 1783779357 | `1783779354.run` | 33 | false | Automaton |
| 24 | 1783779449 | `1783779445.run` | 16 | false | Slime Boss |
| 25 | 1783779560 | `1783779557.run` | 16 | false | The Guardian |

## Execution Correctness
- Invalid commands: 0. `Wrong number of cards selected`: 0. New uncaught gameplay exceptions: 0. CommunicationMod error-log gameplay exceptions: 0.
- Decision trace: 7,136 cutoff-bounded rows: 33 `ScreenType.HAND_SELECT` `CardSelectAction` rows and 152 GRID rows (150 `CardSelectAction` and 2 accepted `ProceedAction`).
- HAND_SELECT: 35 card-key actions and 33 terminal confirms. Every confirmation was emitted only after a new key action and with `confirm` in the available command list; no duplicate-confirm sequence or HAND_SELECT `ProceedAction` row occurred. The 33 `Sending card-select confirm with stale selection state` diagnostics are availability-guarded terminal confirmations, not rejected commands.
- GRID: 150 logged selector returns, all exactly `1/1 remaining`; zero remaining-count mismatches and zero cardinality exceptions.
- Lethal acknowledgement evidence: 86 `plan_kind=lethal decision=pass_through` rows; 0 `[PLAN_ACK]`, plan-reject, or plan-quarantine rows. The pass-through actions advanced normally and produced no command-legality or exception evidence.

## Sim Divergence
- The cutoff summary read 22,416 rows, skipped 22,397 pre-cutoff rows, found 19 fresh events, and found no malformed rows.
- **A-class:** none.
- **B-class:** 6 localized state rows: five monster-state rows (intent, gone/hp, or split-hp boundaries) and one slime-split state row. None was paired with a command rejection, exception, or repeatable live impact.
- **C-class:** 13 player-state rows (block or energy boundary timing). The repeated floor-16 block rows are observation-boundary noise, not a high-impact command or mechanics cluster.
- No repeated high-impact sim-divergence cluster was demonstrated.

## Qualification Decision
- Batch 1 retry 2 is **qualified** for the three repaired live-validation surfaces: full 25-game conservative evaluation completed with zero gated HAND_SELECT duplicate/legality failures, GRID cardinality failures, invalid commands, and uncaught gameplay exceptions.
- This qualification does not establish the separate first-Ironclad-victory objective: this batch produced 0 victories. Per task scope, no Batch 2 or training run was started.
