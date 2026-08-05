# Final Current Baseline Replication Closeout

Date: 2026-08-05 (Asia/Shanghai)

## Decision

The unique final Current baseline replication is consumed and invalid. It
completed and passed the 16-pair canary, accessed five holdout pairs, then
failed before a 43rd row was retained. Terminal publication independently
failed with `PermissionError: [WinError 5] Access is denied` while atomically
replacing `execution_journal.json`.

The output therefore has no canonical terminal metrics, report, or manifest.
It does not demonstrate a Current baseline floor. Current is no longer eligible
for another baseline attempt, and formal non-combat RL remains `no_go`.

## Lifecycle

- Preregistration commit:
  `b60b6b94acda5ca1ed480f199f702cdde8a52a3b`
- Authorization commit:
  `886c8375c49bd8566969a74db663d5cd10b31201`
- Registration SHA-256:
  `8a2a3948eb3e604b0aebb2296fa15c40dac7efb4005d2245e5f4d5c6c6043a46`
- The durable started journal existed before native loading.
- The runner exited `1`; no retry, resume, seed replacement, repair, or
  threshold change was performed.
- The preserved journal remains in `started` state. Its zero row count and
  `holdout_accessed=false` fields are pre-execution state, superseded only for
  descriptive reconstruction by the bound 42-row partial trajectory file.

## Canary

All 32 policy rows for seeds `60000..60015` validate in registered order and
retain complete hashes and replay identity.

- Result: `canary_passed`
- Current mean floor: `25.0625`
- Control mean floor: `14.1875`
- Paired mean Current-minus-control floor: `10.875`
- Current category counts: route 392, shop 57, event 87, card reward 191
- Declared support rows: 0 for both policies
- Victories: 0 for both policies
- Every registered canary check passed.

## Partial Holdout

Only the five complete pairs for seeds `60016..60020` are retained. These rows
are descriptive and cannot enter the 64-pair holdout gate or bootstrap.

- Current mean floor: `20.2`
- Control mean floor: `13.4`
- Paired mean floor difference: `6.8`
- Current floors: 16, 16, 31, 16, 22
- Declared support rows: 0 for both policies
- Victories: 0 for both policies
- Next unobserved registered boundary: seed `60021`, Current policy
- Bootstrap status: `not_run`

The partial values do not authorize a floor claim, tuning, or another run.

## Publication Failure

The output directory contains exactly four files:

| File | Size | SHA-256 |
| --- | ---: | --- |
| `bootstrap_draws.json` | 481 | `a6b21110bad3d3838ce34053fd59946943d19213bf788a93a13b6c83736859a3` |
| `configuration.json` | 11,886 | `0ec4818495e1e5552a597c1815bd3037a926443ed6a810257f88c34c4fdb1a07` |
| `execution_journal.json` | 950 | `d2e17578fa4c7c37280bd52ff60cf017ae6b5d6cd6bb412bf367d799ba4c103d` |
| `trajectory_rows.json` | 742,770 | `0e2c770a413e793d50ad3a4e670bcc988e1bc216ff4eacf672cb4b49668ac166` |

The source-only verifier returned `artifact_inventory_mismatch`; canonical
`metrics.json`, `report.md`, and `artifact_manifest.json` are absent. The
empty bootstrap placeholder and configuration were written before journal
replacement failed. No temporary file survived cleanup.

An execution boundary occurred before row 43, but its exact reason and detail
were not durably published before the later atomic-journal failure. The run
also overlapped with read-only monitoring of files under the atomic output
root. That overlap is recorded as a possible source of transient Windows file
locking, but causal attribution is unresolved.

## Operational Rule

For future one-attempt Windows executions, do not read any file under an
actively written atomic output root. Monitor only process liveness until exit,
then inspect artifacts. This prevents observational reads from becoming a
plausible file-sharing confounder.

## Authority

All gameplay, native, seed, fresh-evidence, reward, OPE, model fitting, formal
RL, training, qualification, loading, promotion, and target-supported-outcome
authority is false after closeout. Target-supported outcomes remain an
independent blocker with zero source-comparable supported victories.
