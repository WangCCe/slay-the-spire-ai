# Trainable Baseline Qualification Batch 2

## Batch Identity
- Status: **failed and stopped**. This was not a 25-game qualification result.
- Candidate: `70947284f937ffbb68da7055efa6975d43add0e2` (`docs: record hand select qualification retry`); reviewed behavior commit: `1501ebf4`.
- Cutoff: `1783781240` (2026-07-11 22:47:20 CST); marker baseline: 14,731, last prior marker `1783779560`; completion-marker baseline: 1 historical `Max games reached (25); exiting.` entry.
- Config re-read before launch: `D:\anaconda\envs\stsai\python.exe` runs `scripts/run_training_batch.py --eval --max-games 25 --phase conservative --restart-guidance --truncate-log-after-backup --decision-trace-path D:/SteamLibrary/steamapps/common/SlayTheSpire/ai_decision_trace_clean.jsonl --sim-divergence-trace-path D:/SteamLibrary/steamapps/common/SlayTheSpire/sim_divergence_trace_clean.jsonl`. It contains no `--train` argument.
- Launch: exactly one `powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_sts_modded.ps1 -FreshRun` invocation. The helper stopped one previous ModTheSpire Java process, found no Ironclad autosaves, and launched ModTheSpire. The batch wrapper recorded its fresh log backup at 22:48:14 CST.
- Monitoring: 50-second marker/debug/error polls. The invalid command occurred at 23:13:17 CST and was visible to the monitor at 23:13:19. Gameplay nevertheless continued through the affected run, started game 16, and logged its final action at 23:14:09. The later process stop used wrapper PID `40464` and game-agent PID `34728`; those PIDs and their post-stop absence are operational observations, while the durable logs only prove the continued timeline and abrupt final tail.

## Preserved Baselines
- `reports/trainable_baseline_qualification_batch1.md`: SHA-256 `22F0AA10A899EBBF94DBA6D10D27F3D5906F6C2C77DB7BA3D63D04B0E1EE9730`.
- `reports/trainable_baseline_qualification_batch1_retry1.md`: SHA-256 `609F42A15DD6037B365ECA815A04CBE2724A0A13AB93B9D2D98DD24821060D32`.
- Eligible Batch 1 input, `reports/trainable_baseline_qualification_batch1_retry2.md`: SHA-256 `DABED49A496492D1D4CA5552B5C6137F1934D8A608C6C34B3423C915EB636A18`.
- Pre-launch logs: `ai_debug.log` 317,028 bytes; `.1` 10,485,710; `.2` 10,485,756; `.3` 10,485,696; `.4` 10,485,648; `.5` 10,485,694; `communication_mod_errors.log` 1,133,106 bytes.
- Pre-launch traces: decision 2,008,479,339 bytes; sim-divergence 151,219,926 bytes.
- Fresh debug evidence is one rotated segment, `ai_debug.log.1` (10,485,739 bytes), plus active `ai_debug.log` (9,553,901 bytes): 20,039,640 bytes total. Earlier `.2` through `.5` are pre-cutoff. The CommunicationMod error delta is 1,495 bytes / 13 wrapper-startup lines only.
- Final traces: decision 2,024,715,217 bytes; sim-divergence 151,380,928 bytes.

## Stop Condition And Containment
- One rejected command occurred at 23:13:17 CST, represented by three propagating debug lines, not three separate commands: `CALLBACK_CHECK last_error`, `CombatRLAgent error`, and `Game error` at `ai_debug.log:93698-93700`.
- Causal sequence: after a stale queued `ChooseAction` requested state, GRID reported `cards=18`, `selected=0`, `num_cards=1`, `confirm_up=True`, `for_purge=True`, and initial commands `[potion, confirm, cancel, key, click, wait, state]`. The callback returned `ProceedAction`; its queued `confirm` executed after CommunicationMod had transitioned to `[choose, potion, leave, key, click, wait, state]`, so it was rejected and the screen became `SHOP_SCREEN`.
- Regression cluster: **GRID/ProceedAction confirm transition race**. This is A-class because the command was actually rejected by the live game; it is not a sim-only observation mismatch.
- After the rejection, the agent continued for about 52 seconds: the affected run reached `GAME_OVER` at 23:13:41, marker 14,746 was written, game 16 started at 23:13:44, and the active log ended during floor 6 at 23:14:09. The operator then issued `Stop-Process -Id 34728,40464 -Force` and observed both production Python processes absent while ModTheSpire remained running. The exact stop instant and historical PID state are not independently reconstructable from the preserved logs.

## Run Outcomes
- Stop count: 15 new AI markers (14,731 to 14,746), 15 unique paired Ironclad run records, 0 new completion markers, and 0 victories. The process continued into an unpaired 16th run before being terminated prior to 25 games.
- Marker-to-run save timestamps differ by 3-4 seconds; every pairing is unique.

| # | AI marker | Run record | Floor | Victory | Killed by |
|---|---:|---|---:|---|---|
| 1 | 1783781393 | `1783781390.run` | 16 | false | The Guardian |
| 2 | 1783781493 | `1783781490.run` | 20 | false | Shell Parasite |
| 3 | 1783781578 | `1783781575.run` | 16 | false | Hexaghost |
| 4 | 1783781702 | `1783781699.run` | 22 | false | Shelled Parasite and Fungi |
| 5 | 1783781891 | `1783781888.run` | 33 | false | Automaton |
| 6 | 1783781954 | `1783781951.run` | 16 | false | The Guardian |
| 7 | 1783782020 | `1783782017.run` | 16 | false | Hexaghost |
| 8 | 1783782256 | `1783782253.run` | 50 | false | Awakened One |
| 9 | 1783782301 | `1783782297.run` | 10 | false | Exordium Thugs |
| 10 | 1783782385 | `1783782381.run` | 16 | false | Slime Boss |
| 11 | 1783782466 | `1783782463.run` | 16 | false | Slime Boss |
| 12 | 1783782587 | `1783782584.run` | 33 | false | Automaton |
| 13 | 1783782687 | `1783782684.run` | 16 | false | The Guardian |
| 14 | 1783782745 | `1783782742.run` | 16 | false | The Guardian |
| 15 | 1783782824 | `1783782821.run` | 16 | false | The Guardian |

## Execution And Screen Evidence
- Invalid commands: **1 rejected command**, with 3 debug-log propagations. `Wrong number of cards selected`: 0. New uncaught gameplay exceptions: 0. CommunicationMod error-log gameplay exceptions: 0.
- Decision trace: 4,547 cutoff-bounded rows. Screens include 26 `HAND_SELECT` and 98 `GRID` rows. The trace records no action whose command field is `confirm`; its sole GRID `ProceedAction` row captures `confirm` in `available_commands`, and `ProceedAction.execute()` subsequently maps that action to the low-level `confirm` rejected in the debug log.
- HAND_SELECT: 30 key actions and 26 terminal confirmation diagnostics. All 26 diagnostics had `confirm` available; sampled sequences show key action before the terminal confirmation. There was no HAND_SELECT invalid command.
- GRID: 97 selector returns, all exactly `1/1 remaining`; zero selector cardinality mismatches. The separate 98th GRID trace row is the `ProceedAction` captured while `confirm` was available; action execution then emitted the rejected low-level `confirm` across the screen transition.
- Lethal acknowledgement: 43 `plan_kind=lethal decision=pass_through` rows; 0 `[PLAN_ACK]`, plan-reject, or plan-quarantine rows. This evidence is not the failing surface.

## Sim Divergence
- Cutoff summary: 22,425 lines read; 22,416 pre-cutoff rows skipped; 9 fresh events; 0 malformed rows.
- **A-class sim cluster:** none. The A-class operational failure is the live GRID command rejection above.
- **B-class:** 5 localized monster-state mismatches (four `monsters[2].hp`, one `monsters[0].intent`) across floors 18, 33, 42, 47, and 50; no repeated high-impact causal cluster was established.
- **C-class:** 4 player-state timing rows (two `player.block`, two `player.current_hp`) on floors 16 and 33.

## Two-Batch Promotion
- Batch 1 status: clean, using independently reviewed `batch1_retry2.md` only.
- Batch 2 status: failed: GRID/ProceedAction confirm transition race.
- Consecutive clean batches: `1`.
- Trainable baseline promoted: **no**.
- Frozen baseline commit: not created.
- First-Ironclad-victory status: not achieved in this partial batch (0 of 15); no training was started.

## OPSX State And Next Action
- `openspec instructions apply --change investigate-lethal-detection-failure --json` was `ready` with 28/29 tasks complete before the launch. Task 5.5 remains unchecked and will not be modified for this failed batch.
- The failure is preserved for a separate investigation/fix change. This qualification change is not archived here.

## Commands
```powershell
openspec instructions apply --change investigate-lethal-detection-failure --json
Get-Content C:\Users\20571\AppData\Local\ModTheSpire\CommunicationMod\config.properties
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\restart_sts_modded.ps1 -FreshRun
D:\anaconda\envs\stsai\python.exe analysis_scripts\summarize_sim_divergence_trace.py --trace D:\SteamLibrary\steamapps\common\SlayTheSpire\sim_divergence_trace_clean.jsonl --since-unix 1783781240
Stop-Process -Id 34728,40464 -Force
```
