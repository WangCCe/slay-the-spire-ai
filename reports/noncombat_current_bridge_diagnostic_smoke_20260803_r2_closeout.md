# Current Bridge Diagnostic Smoke R2 Closeout

Date: 2026-08-03

## Decision

The separately registered r2 successor finalized as
`current_bridge_diagnostic_failed`. It stopped before retaining a decision row
because the Current bridge rejected the native potion display name
`Elixir Potion` as absent from the frozen Communication Mod metadata catalog.

This is a deterministic metadata-identity boundary, not evidence of Current
policy quality, simulator mechanics, a baseline floor, or RL readiness. The
native adapter emits both the stable enum identity `ELIXIR_POTION` and the
upstream display name `Elixir Potion`; the bridge ignores the enum identity for
metadata validation and requires an exact case-insensitive display-name match.
The frozen base-game metadata entry is named `Elixir`.

The registered attempt is consumed. It will not be retried, repaired in place,
or used to prepare r3. A later source fix cannot reinterpret this result or
supply a completed Current own-trajectory row.

## Registered Identity

- Anti-retry decision commit:
  `6d9673f3e1369700afac801677d3d592fd6f66aa`.
- Planning commit: `7a0fefcc120d325349c8c60e7560d8ecd790f5fd`.
- Frozen r2 lineage commit:
  `78c73f6709247116e4dba67c6347f2f4e017fe7d`.
- Profile implementation commit:
  `fe9f861aa945618187291e04b595d69914135200`.
- Preregistration commit:
  `91e18b8eac7498b22366bee9898461411b1e3701`.
- Final pushed authorization and attempted identity:
  `a9ecb7d66dafa9bf7ddc1d01bc0e2f896d856d91`.
- Registration: 6,977 bytes, SHA-256
  `71e156bfcb2d8b6932fbf8e1f50c1705023098ae91485e5967304bb866874934`.
- Preimplementation lineage: 5,603 bytes, SHA-256
  `aabbc0e007f2f44f05c1f529ce03ada57c715fe257237fa2c830a6f2035ed9c9`.
- Preflight: 3,341 bytes, SHA-256
  `9853adcae89f8ca4982dd6764525b66164ae8aaf6d84098bf28e83be6ead6a27`.
- Execution authorization: 2,000 bytes, SHA-256
  `d81a44b1f4c93467ccace8636604c90e5d4e29d776e89b8084518abf8f4b4525`.
- Native module: 4,225,024 bytes, SHA-256
  `7ac2c750fba6e38d4a023cab72a4d67f158fe7f88414058e5876cef5003fcb88`.
- Fixed reused seeds: `[7000, 7100, 2000, 10]`.
- Registered controls: two replays per seed, at most 500 target decisions per
  replay, and a 600-second whole-run deadline.

The one execution used the pushed registration, bound Windows Python, frozen
module, simulator and metadata identities, and registered MinGW runtime. It had
no runtime override.

## Observed Result

- Status: `failed`.
- Verdict: `current_bridge_diagnostic_failed`.
- Reason: `potion_metadata_missing`.
- Detail: `Elixir Potion`.
- Retained rows: 0.
- Terminal rows: 0.
- Declared support rows: 0.
- Route decisions: 0.
- Shop decisions: 0.
- Event decisions: 0.
- Card-reward decisions: 0.

The finalized journal binds result SHA-256
`b969c26b106455320d03408a1d427a3ea20fa6f2f3b65e977aa8dc3de31e3285`.
The canonical artifact inventory is:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `artifact_manifest.json` | 1,620 | `7f6da7c27b73db15be1470c702ed6ff3bef24ba6952528c33b49c5248fcf3e8b` |
| `configuration.json` | 8,046 | `2102e422e7cd8d1825e7fb16687f917b6e0ab44a2f41b5a469ea026831b78dfb` |
| `execution_journal.json` | 938 | `5b57c8fe7b2b45d70b1ccbe1498f0bc9b8875f9799a44291220eae5a0f7fa4da` |
| `metrics.json` | 958 | `4fb2a2607487df9c9ac09f7d214f9b936e4d1879c31f6a5ee0dcd58b13462ee1` |
| `report.md` | 550 | `fb426fb2655cb0dfecc7d6170d6f485a39190fe3fbb6a9570d75157808c99ba0` |
| `trajectory_rows.json` | 1,077 | `40158f052f260dd51d0b14880f61a1265fad92af5de48ee99223f5b7538fa493` |

A fresh-process no-native verifier reproduced the failed verdict and every
canonical artifact byte with `native_loaded = false`.

## Root-Cause Boundary

A read-only static comparison of all 43 upstream non-empty potion display names
against the frozen base-game metadata found exactly three unmatched pairs:

| Stable native ID | Native display name | Metadata name |
|---|---|---|
| `ELIXIR_POTION` | `Elixir Potion` | `Elixir` |
| `FAIRY_POTION` | `Fairy Potion` | `Fairy in a Bottle` |
| `GAMBLERS_BREW` | `Gamblers Brew` | `Gambler's Brew` |

Only the first pair was reached by r2. The other two are static compatibility
findings, not observed r2 failures. Exact matching succeeds for the other 40
upstream potion display names.

Any repair belongs to a separate OpenSpec change. It should key a closed alias
table by stable native ID and verify the expected native and metadata names,
rather than remove suffixes or broadly normalize punctuation. It must add red
regressions for all three aliases and preserve fail-closed behavior for unknown
IDs or mismatched names. It grants no diagnostic execution, fresh evidence,
gameplay, OPE, model, reward, formal-RL, training, qualification, loading, or
promotion authority.

## Readiness And Handoff

The Current structural baseline remains undemonstrated. No baseline-floor or
target-supported-outcome readiness state changes, and every registered
downstream authority remains false.

Before preregistration, the focused implementation suite passed with
`150 passed, 5 skipped`; the partitioned commit gate passed with
`3573 passed, 11 skipped` in 239.77 seconds and 242.89 seconds total. The r2
registration and preflight then passed their source-bound checks without
constructing an environment.

After the attempt, the canonical no-native verifier passed in a fresh process.
The focused suite also recomputed the consumed v1 artifact directory
byte-for-byte without native loading. The old v1 source-bound CLI correctly
rejects the newer implementation with `implementation_source_hash_mismatch`;
that fail-closed result proves v1 is not reusable and is distinct from the
historical artifact recomputation.

The immediate next step is the separate offline potion metadata compatibility
repair described above. Do not rerun r2, prepare r3, access a fresh cohort,
launch gameplay, or start training from this result.
