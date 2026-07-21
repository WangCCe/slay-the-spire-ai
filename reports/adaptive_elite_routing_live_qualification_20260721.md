# Adaptive Elite Routing Live Qualification - 2026-07-21

## Status

**COMPLETE - NOT ELIGIBLE FOR LARGER VALIDATION.** The single bounded
ten-game Ironclad A0 adaptive cohort completed without a runtime or evidence
integrity failure, but it missed the elite-exposure, elite-fatality, average
floor, and Act 2 boss-reach gates. Conservative remains the live rollback
mode. This cohort must not be tuned and rerun as fresh qualification evidence.

## Qualified Source

- Qualified product source: `40bb9d8f9904f6764fc7160b46bafe0a8d7022f4`
- Launch HEAD: `d0578d23b8bcddd2581076adc7ddb6e92ae32752`
- The launch HEAD adds only qualification reports and task-ledger updates after
  the qualified product source.
- Branch: `codex/noncombat-ope-readiness`
- Production Python: `D:\anaconda\envs\stsai\python.exe`
- Agent: `combat_rl`, RL space `v2`, evaluation mode, A0
- Cohort size: exactly `10` completed games
- Elite route mode: `adaptive`

## Promotion Baselines

The preserved 2026-07-20 unpaired cohorts recorded:

| Mode | Runs | Wins | Average floor | Maximum floor | Act 2 boss reaches | Elite encounters | Elite-death runs |
|---|---:|---:|---:|---:|---:|---:|---:|
| conservative | 10 | 0 | 24.2 | 33 | 3 | 0 | 0 |
| aggressive | 10 | 0 | 18.9 | 31 | 0 | 9 | 5 |

This cohort is eligible for a larger validation only if it records at least
three elite encounters, no more than two elite-death runs, elite fatality ratio
at most 25 percent, average floor at least 24.2, at least three Act 2 boss
reaches, no runtime error, and no repeated causal A-class sim-divergence
cluster. A real `victory=true` run remains the outer objective.

## Prelaunch Baseline

- Baseline capture cutoff: Unix `1784650207`
- Target game/AI process count: `0`
- Ironclad autosave and backup: both absent
- Communication Mod config SHA-256:
  `D9D264340921D79BF10501DC210940DD404FA203B565865E3202A643B633CCF9`
- AI marker file: `15275` lines, `183300` bytes
- AI marker SHA-256:
  `CEF4353DC038E3DE9648258C0750F4936EC8E4CED974794ED64EACABA038E240`
- Latest AI marker: `1784557886`
- Latest Ironclad run: `1784557883.run`, floor `16`, `victory=false`,
  killed by `Hexaghost`, path `MM?M?R?MTRMRM$RBOSS`
- Existing `ai_debug.log` cutoff: `6828015` bytes
- `communication_mod_errors.log` cutoff: `1176013` bytes
- Cohort AI log: `ai_debug_adaptive_20260721.log`, absent / offset `0`
- Cohort decision trace: `ai_decision_trace_adaptive_20260721.jsonl`,
  absent / offset `0`
- Cohort sim-divergence trace:
  `sim_divergence_trace_adaptive_20260721.jsonl`, absent / offset `0`
- Checkpoint inventory: `208` files; metadata SHA-256
  `2310129F2D0589B088EF27DD30D17F11D03AF03BFD190B15F7E16BD1513AD1EF`;
  newest checkpoint timestamp `2026-06-03T18:44:50.0352542Z`

Baseline persistent Communication Mod command:

```properties
command="D\:/anaconda/envs/stsai/python.exe" "D\:/PycharmProjects/slay-the-spire-ai/scripts/run_training_batch.py" --eval --max-games 5 --phase conservative --restart-guidance --truncate-log-after-backup --decision-trace-path "D\:/SteamLibrary/steamapps/common/SlayTheSpire/ai_decision_trace_clean.jsonl" --sim-divergence-trace-path "D\:/SteamLibrary/steamapps/common/SlayTheSpire/sim_divergence_trace_clean.jsonl"
```

The wrapper has no `adaptive` phase. To avoid changing qualified source, the
temporary live command invokes `main.py` directly:

```text
D:\anaconda\envs\stsai\python.exe D:\PycharmProjects\slay-the-spire-ai\main.py --agent combat_rl --elite-route adaptive --max-games 10 --ascension 0 --rl-version v2 --eval
```

The game launch environment binds `STS_AI_LOG_FILE`,
`STS_DECISION_TRACE_FILE`, and `STS_SIM_DIVERGENCE_TRACE_FILE` to the three
fresh cohort-specific paths above. The exact baseline config must be restored
after completion or any failure.

## Execution

- ModTheSpire launch: `scripts\restart_sts_modded.ps1 -FreshRun`
- First game start: `2026-07-22 00:14:33 +08:00`
- Terminal boundary: `2026-07-22 00:30:46 +08:00`
- Terminal evidence: `Max games reached (10); exiting.`
- The Python process exited after the tenth marker and before an eleventh game.
- The remaining Java game process was stopped with
  `scripts\restart_sts_modded.ps1 -SkipLaunch`.
- The dedicated AI log reached the existing 10 MiB rotation boundary. The
  complete earlier segment was retained as
  `ai_debug_adaptive_20260721.log.1`; the active segment starts at the exact
  next log event.

## Cohort Runs

Each AI marker is unique and maps to exactly one `.run` file at marker minus
three seconds. All ten records are Ironclad A0 runs.

| Run id | AI marker | Floor | Victory | Final killer | `E` nodes | Path |
|---:|---:|---:|---|---|---:|---|
| `1784650652` | `1784650655` | 33 | false | Champ | 0 | `MM$?MRMMTMRMMMRBOSSM???MR$RTRMR?MRBOSS` |
| `1784650754` | `1784650757` | 16 | false | Hexaghost | 0 | `M???MRMRTM?MRMRBOSS` |
| `1784650802` | `1784650805` | 8 | false | Gremlin Gang | 0 | `MM?$MR?M` |
| `1784650867` | `1784650870` | 16 | false | Slime Boss | 0 | `MM?MM$M?T?MMR?RBOSS` |
| `1784650965` | `1784650968` | 22 | false | 3 Byrds | 0 | `MMMM?RM?T?R?RMRBOSSM???M` |
| `1784651020` | `1784651023` | 11 | false | 3 Sentries | 1 | `M$MMMRM?T?E` |
| `1784651097` | `1784651100` | 16 | false | The Guardian | 0 | `M$M??MMMTRMMM$RBOSS` |
| `1784651170` | `1784651173` | 16 | false | Slime Boss | 0 | `MM???MRMTRM$M$RBOSS` |
| `1784651250` | `1784651253` | 16 | false | Slime Boss | 0 | `MMM$MR$MTMMM?MRBOSS` |
| `1784651443` | `1784651446` | 31 | false | Shelled Parasite and Fungi | 0 | `M??MMR$MTMM$RMRBOSSM?M?MRMMT??$R?` |

The final `damage_taken` combat name matches `killed_by` in every run. The
only normalized final elite killer is `3 Sentries`, in run `1784651020`.

## Qualification Metrics

| Gate | Required | Observed | Result |
|---|---:|---:|---|
| Completed runs | exactly 10 | 10 | PASS |
| Elite encounters (`E`) | at least 3 | 1 | **FAIL** |
| Elite-death runs | at most 2 | 1 | PASS |
| Elite fatality ratio | at most 25% | `1 / 1 = 100%` | **FAIL** |
| Average floor | at least 24.2 | 18.5 | **FAIL** |
| Maximum floor | report only | 33 | n/a |
| Act 2 boss reaches | at least 3 | 1 | **FAIL** |
| Victories | report only | 0 | n/a |
| Runtime errors | none | 0 | PASS |
| Repeated causal A-class cluster | none | 0 | PASS |

The raw fatality ratio is reported even though the cohort also missed the
minimum exposure required to make that estimate useful. Adaptive underperformed
the preserved conservative cohort (`24.2` average floor and three Act 2 boss
reaches) and obtained much less elite exposure than the aggressive cohort
(`9` elite encounters).

## Route And Trace Evidence

The two retained AI log segments contain `346` structured
`[ADAPTIVE_ROUTE]` rows:

| Outcome / selection / reason | Rows |
|---|---:|
| success / conservative / `deck_not_ready` | 142 |
| success / conservative / `hp_below_absolute_floor` | 60 |
| success / conservative / `later_act_optional_elite` | 60 |
| success / conservative / `hp_below_relative_floor` | 52 |
| forced / conservative / `forced_elite_route` | 22 |
| candidate-generation fallback / conservative | 8 |
| success / aggressive / `optional_elite_allowed` | 2 |

The two aggressive records are repeated observations of the same run-1 floor-7
state. Later replanning backed away before the candidate's floor-14 elite, so
that run's realized path contains no `E`. The eight candidate-generation
failures occurred on repeated Act 2 floor-18 through floor-21 states in run
`1784650965`; every row contains a validated conservative fallback candidate,
and the run continued normally.

The dedicated sim-divergence trace contains one valid JSONL row and no malformed
rows:

| Normalized cluster key | Rows | Classification |
|---|---:|---|
| `EndTurnAction | end-turn/escape boundary | player | player.block` | 1 | isolated transition, no demonstrated causal mechanics or legality effect |

The row is a floor-20 Looter escape boundary where the oracle expected block
`0` and live state retained block `11`. It does not meet the repeated-cluster
definition. It is consistent with the preserved 2026-07-20 cohorts' isolated
end-of-combat block-clearing class and introduces no repeated A-class cluster.

## Integrity And Rollback

- AI log segment 1: `10,485,706` bytes, `111,379` lines, SHA-256
  `72F73E094C33883AE53F724C8FD48EA94482503FCCE503EBB4981210C9C6268A`.
- AI log segment 2: `2,751,552` bytes, `29,171` lines, SHA-256
  `E0388BCFB9D8992EC325E14F99076D5B7F5CFBDA7EAAB1B45AAE60DA7DD2A2FC`.
- Decision trace: `9,739,213` bytes, `2,768` non-empty valid JSONL rows,
  SHA-256
  `259A9C07F803C32D70CAF41EB062E4C354B09D5223D18CC462F71D260D9F899F`.
- Sim-divergence trace: `12,912` bytes, one valid JSONL row, SHA-256
  `1750070B506232F324ED1701F5AADDD638BA31D2D10FD9C78DF923ED1498FCFD`.
- AI logs contain zero `ERROR`, `CRITICAL`, traceback, unhandled-exception, or
  exception-marker rows. The Communication Mod error-log delta is `79` bytes
  and contains only the two normal database-load messages.
- Post-cohort marker file: `15,285` lines, `183,420` bytes, SHA-256
  `9C85CF77C2885F4EE17FA459CD538D040D77607A48EDCE99BABA9A5CFEC1021F`.
- The original Communication Mod file was restored byte-for-byte. Its final
  SHA-256 is the prelaunch value
  `D9D264340921D79BF10501DC210940DD404FA203B565865E3202A643B633CCF9`,
  and its command is the conservative five-game evaluation wrapper recorded
  above.
- Checkpoints remain `208` files and `1,356,047,034` bytes. The sorted
  `name|length|LastWriteTimeUtc.Ticks` metadata SHA-256 remains
  `2310129F2D0589B088EF27DD30D17F11D03AF03BFD190B15F7E16BD1513AD1EF`;
  the newest timestamp remains `2026-06-03T18:44:50.0352542Z`.
- No project Python, Slay the Spire Java, Ironclad autosave, or autosave backup
  remains after shutdown.

## Decision

Adaptive is **not eligible** for a larger validation. Keep conservative as the
persistent live mode. Do not tune thresholds and rerun this same cohort, do not
change the default route mode, and do not authorize training from this result.
No run advanced the outer `victory=true` objective.
