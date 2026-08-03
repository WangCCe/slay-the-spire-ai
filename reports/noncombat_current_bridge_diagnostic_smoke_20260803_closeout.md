# Current Bridge Diagnostic Smoke Closeout

Date: 2026-08-03

## Decision

The single registered reused-development-seed attempt finalized as
`current_bridge_diagnostic_failed`. It stopped during the first decision of the
first replay before retaining any row. The exact failure was
`diagnostic_execution_failed` with `KeyError('action_type')`.

This is a diagnostic-runner contract defect, not evidence of Current policy
quality, simulator mechanics, Courier support behavior, or a baseline floor.
The runner required `candidate["action_type"]`, while the validated native
candidate schema provides `action_id`, `category`, `available`, `kind`,
`label`, and `raw`. The fake candidate used by the focused regression included
the extra field and therefore did not expose the mismatch before publication.

The registered attempt is consumed. It will not be repaired, resumed, replaced,
or rerun. A source fix cannot reinterpret this result or supply a completed
Current own-trajectory row.

## Registered Identity

- Planning commit: `2bb0d0e53074daad1bf01254cffaa23c4f24210b`.
- Frozen pre-implementation commit: `6d8080340`.
- Runner implementation commit: `3ca13828d047939517462a980072ccaee4e7182d`.
- Preregistration publication commit: `d2d78228818e051d230d2a2934f015c7fa103323`.
- Final pushed preflight commit and attempted identity:
  `b3da176bc6dab63d3e245b9d4159190b7077eab8`.
- Registration: 6,971 bytes, SHA-256
  `351b0cf61f301ba4a3c48933b74a0dc70301d4d1ce1eaa6711161c6c61a7306a`.
- Native module: 4,225,024 bytes, SHA-256
  `7ac2c750fba6e38d4a023cab72a4d67f158fe7f88414058e5876cef5003fcb88`.
- Fixed reused seeds: `[7000, 7100, 2000, 10]`.
- Registered controls: two replays per seed, at most 500 target decisions per
  replay, and a 600-second whole-run deadline.

No module was rebuilt. Identity-only preparation loaded API/build identity and
constructed no environment. The one execution used the frozen module and
registered MinGW runtime directory.

## Observed Result

- Status: `failed`.
- Verdict: `current_bridge_diagnostic_failed`.
- First reason: `diagnostic_execution_failed`.
- Detail: `{"message": "'action_type'", "type": "KeyError"}`.
- Retained rows: 0.
- Terminal rows: 0.
- Declared support rows: 0.
- Route decisions: 0.
- Shop decisions: 0.
- Event decisions: 0.
- Card-reward decisions: 0.

The finalized journal binds result SHA-256
`7f60a0d1022ce1259ae388694a0d652c52ee8dbcafea9a9d8231ddf6e5cc96de`.
The canonical artifact inventory is:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `artifact_manifest.json` | 1,620 | `649444f4b87877ebf2fcea7258ffa08484a94e7455d28f79e14c6ac30c90dbca` |
| `configuration.json` | 8,040 | `3e3bd2fcc0d41fed22ef3124cf4e29c0feb44dd05eff8035f6b4ca02f1f2313a` |
| `execution_journal.json` | 938 | `9bb79654e4cba9d6fd287b666d01298d942c514c0901370e874a538ffdec2c90` |
| `metrics.json` | 962 | `30a7ca88310a705f8a1e48a56a470448b8472a960d74330216ba168a0513d9db` |
| `report.md` | 554 | `379a9e7802a5f5a18bcf7b3830eb803b9ea92c3bbd5f997113b3e51c30cbaaf9` |
| `trajectory_rows.json` | 1,132 | `75c0d84146c952454e98fbf4eb59d00da5ee8ec1de0765a216c0f91b996714d6` |

The no-native verifier recomputed the publication byte-for-byte and reproduced
the failed verdict.

## Readiness And Authority

No baseline-floor readiness refresh is permitted from this result. The eight
floor-contract checks remain false:

- `comparison_controls_fixed`
- `absolute_quality_gate_fixed`
- `paired_quality_gate_fixed`
- `unsupported_rate_ceiling_fixed`
- `replay_contract_fixed`
- `bootstrap_contract_fixed`
- `stop_rules_fixed`
- `untouched_holdout_fixed`

The independent target-supported-outcome blocker also remains unchanged: the
frozen evidence has zero deterministic-Current-supported victories.

Every registered authority remains false:

- `baseline_floor_authorized = false`
- `formal_rl_authorized = false`
- `fresh_evidence_authorized = false`
- `gameplay_authorized = false`
- `model_fitting_authorized = false`
- `ope_authorized = false`
- `policy_loading_authorized = false`
- `promotion_authorized = false`
- `qualification_authorized = false`
- `reward_authorized = false`
- `target_supported_outcome_authorized = false`
- `training_authorized = false`

## Verification And Handoff

Before preregistration, the focused bridge/adapter suite passed with
`152 passed, 5 skipped`; the partitioned commit gate passed with
`3550 passed, 11 skipped` in 228.18 seconds and 231.34 seconds total. The
registration and all evidence bindings then passed no-environment validation.

After the attempt, a fresh-process no-native verifier reproduced the failed
verdict with `native_loaded = false`. The same adjacent focused suite passed
with `152 passed, 5 skipped` in 5.99 seconds. `py_compile` and
`git diff --check` passed, and strict global OpenSpec validation returned
`61 passed, 0 failed`. No raw unpartitioned full pytest, gameplay, fresh seed,
model fitting, reward change, OPE, or training ran.

The immediate handoff is the exact runner defect above. A separate narrow
OpenSpec may add a production-schema regression and remove the invalid
candidate-field assumption without executing native environments or seeds.
Any later diagnostic attempt requires a separate preregistration and explicit
anti-retry justification; it is not authorized by this closeout.
