# Current Baseline Evidence Study Closeout

Date: 2026-08-04

## Decision

The preregistered one-shot study is terminally `study_blocked`. The exact
blocking reason is `card_metadata_cost_invalid` with detail `Injury`. The
canary is incomplete, the holdout was not accessed, no baseline floor is
demonstrated, and formal non-combat RL remains `no_go`.

This result is not retryable. The retained rows are partial structural
evidence only; their floors, category coverage, and paired difference cannot
be used to pass the registered canary or any downstream readiness gate.

## Execution Identity

- Preregistration commit:
  `720f41b07c6d92a35fc7c6620ad62bad8771ce49`
- Registration SHA-256:
  `e84411234821397b462530398722f1f6b5174198754348b1c40bbb6f6d651085`
- Execution-authorization commit:
  `bc380f0a62ce195ad4874042735b41e2ca4203cd`
- Execution-authorization SHA-256:
  `75d19d3631079540465c08c3d6bd44b8ff84d05f6a335c4584d750cbbd9f3b11`
- Artifact-manifest SHA-256:
  `31ad6171c3926e0ca23173824163e168b88698f20dd604355b007eb45d636e4e`
- Exact command:
  `D:\anaconda\envs\stsai\python.exe analysis_scripts/noncombat_current_baseline_evidence_study.py execute`

The command ran once. It did not retry, replace a seed, change a threshold,
or access a holdout seed.

## Retained Canary Evidence

The artifact set retains 18 replay-identical policy rows for the first nine
fixed canary seeds, `11000..11008`. Each row represents two identical fresh
environment executions. The registered canary required 32 policy rows across
all seeds `11000..11015`, so no canary classification or bootstrap result
exists.

| Policy | Rows | Floor sum | Mean floor | Range | Victories | Declared support rows |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Current | 9 | 132 | 132/9 (14.666666666667) | 7..33 | 0 | 1 |
| First candidate | 9 | 94 | 94/9 (10.444444444444) | 6..25 | 0 | 0 |

The nine paired floor differences are
`[0, 8, 8, -3, 1, 3, 10, 10, 1]`, with partial mean `38/9`
(`4.222222222222`). These values are descriptive only.

| Policy | Card reward | Event | Route | Shop |
| --- | ---: | ---: | ---: | ---: |
| Current | 70 | 18 | 130 | 25 |
| First candidate | 59 | 10 | 93 | 17 |

All 18 retained outcomes are `player_loss`. Current seed `11003` is the one
exact declared-support row: it is retained as a non-victory at floor 9 with
`unsupported_shop_courier_restock_semantics`.

## Blocking Boundary

The terminal journal records `card_metadata_cost_invalid` and `Injury`. The
registered external metadata entry names `Injury` as a Curse with an empty
cost string, while the frozen bridge accepts integers, `X`, `UNPLAYABLE`, or
`-`. This is a read-only diagnosis of the observed bridge boundary. It does
not alter the result, authorize a repair in place, or reopen the cohort.

## Verification

The fresh-process command
`D:\anaconda\envs\stsai\python.exe -B analysis_scripts/noncombat_current_baseline_evidence_study.py verify`
returned `study_blocked` with `verified_without_native_loading=true`.
It reconstructed the fixed seven-file artifact inventory from the
registration, terminal journal, and retained rows. The manifest binds:

- `execution_journal.json`: 1,072 bytes,
  SHA-256 `f8d6b771bc9be0ff16241d2d18505f2082836fcc9e340415aa974bbbd1f4951d`
- `metrics.json`: 911 bytes,
  SHA-256 `e53e12558232b6b97f1c78c60a7917fe77d5287cd8764dfd1ef4ed7c1d9cb76b`
- `trajectory_rows.json`: 219,839 bytes,
  SHA-256 `14e5b886737e18e1e0b1bcfe9e43e24864047635939991e90792b0793c75c04d`
- `report.md`: 275 bytes,
  SHA-256 `48ede3984dd265eea09c656ccfe2815d90216b3cf08d0ae943b8c71245638ed2`

`bootstrap_draws.json` is canonically present with `status=not_run`; canary
and holdout metrics are null.

The closeout verification also passed:

- Focused Current-study, baseline-readiness, and formal-readiness suites:
  `76 passed in 26.64s`.
- Registered partitioned `commit` gate: `3664 passed, 11 skipped in 265.22s`;
  total gate time `268.28s`.
- Pre-archive strict OpenSpec validation: `63 passed, 0 failed`.

An earlier sandboxed focused invocation failed only because pytest could not
access its external basetemp (`WinError 5`); it is not represented as a test
result. The identical focused selection then passed in a new explicitly
writable local basetemp.

## Authority

The terminal journal, metrics, and manifest keep every authority flag false.
In particular, the study grants no baseline-floor, target-supported-outcome,
formal-RL, training, model-fitting, gameplay, OPE, qualification, policy-load,
or promotion authority.

## Handoff

Preserve the registration, authorization, journal, rows, metrics, report,
bootstrap placeholder, configuration, and manifest byte-for-byte. Do not
retry the study, prepare replacement seeds, reinterpret partial rows as a
canary, or tune around the blocker. A separate read-only readiness refresh
records the unchanged formal-RL decision. The completed change is synced to
the main specs and archived at
`openspec/changes/archive/2026-08-03-add-post-repair-current-baseline-evidence-study`.
