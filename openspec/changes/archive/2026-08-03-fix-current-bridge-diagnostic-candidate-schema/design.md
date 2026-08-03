## Context

The one-shot Current bridge diagnostic failed before its first retained row
because `_run_replay()` compared the Current evaluation `action_type` with
`matches[0]["action_type"]`. `validate_candidates()` does not define or require
that candidate field. The production adapter candidate contract contains
`action_id`, `category`, `available`, `kind`, `label`, and `raw`; the focused
fake accidentally added `action_type` and masked the mismatch.

The registration, output, closeout, module, and seeds are consumed evidence.
They cannot be regenerated or used to justify a replacement attempt.

## Frozen Evidence

The pre-implementation check observed the same failed zero-row result recorded
by the archived closeout: status `failed`, reason
`diagnostic_execution_failed`, verdict `current_bridge_diagnostic_failed`, and
zero route, shop, event, or card-reward decisions.

| Evidence | Bytes | SHA-256 |
|---|---:|---|
| Registration | 6,971 | `351b0cf61f301ba4a3c48933b74a0dc70301d4d1ce1eaa6711161c6c61a7306a` |
| Artifact manifest | 1,620 | `649444f4b87877ebf2fcea7258ffa08484a94e7455d28f79e14c6ac30c90dbca` |
| Configuration | 8,040 | `3e3bd2fcc0d41fed22ef3124cf4e29c0feb44dd05eff8035f6b4ca02f1f2313a` |
| Execution journal | 938 | `9bb79654e4cba9d6fd287b666d01298d942c514c0901370e874a538ffdec2c90` |
| Metrics | 962 | `30a7ca88310a705f8a1e48a56a470448b8472a960d74330216ba168a0513d9db` |
| Generated report | 554 | `379a9e7802a5f5a18bcf7b3830eb803b9ea92c3bbd5f997113b3e51c30cbaaf9` |
| Trajectory rows | 1,132 | `75c0d84146c952454e98fbf4eb59d00da5ee8ec1de0765a216c0f91b996714d6` |
| Closeout | 5,310 | `006ffd7c3e3c662cc87fcd1f25550e3acc73ef61ca7912de533bc111ff0fed0f` |
| Native module | 4,225,024 | `7ac2c750fba6e38d4a023cab72a4d67f158fe7f88414058e5876cef5003fcb88` |

## Goals / Non-Goals

**Goals:**

- Make the fake candidate shape match the production validated contract.
- Remove only the invalid candidate-side `action_type` lookup.
- Keep unique legal action selection and non-empty Current evaluation
  `action_type` validation.
- Prove the consumed canonical artifact directory still recomputes with the
  no-native artifact verifier and remains byte-identical.

**Non-Goals:**

- Do not rerun, resume, repair, or replace the consumed registration.
- Do not load the native module, construct an environment, or consume a seed.
- Do not alter Current policy decisions, adapter schemas, bridge mapping,
  simulator behavior, baseline-floor contracts, outcome evidence, rewards,
  models, OPE, gameplay, or training.
- Do not reinterpret the failed verdict or claim a completed trajectory.

## Decisions

### Use the adapter validator as the only candidate field contract

The runner will continue to call `validate_candidates()` and identify the
selected action by unique `action_id`. It will not require evaluator-only
metadata from a candidate. The Current evaluation remains responsible for its
own non-empty string `action_type`, policy identity, input hashes, fallback,
tracker, and source-mutation fields.

Alternative considered: add `action_type` to the adapter candidate schema.
Rejected because it would expand every native candidate producer and historical
schema solely to satisfy a diagnostic-only comparison that is unnecessary for
action legality.

### Make the fake schema production-shaped

The shared fake candidate will remove its extra `action_type`. The former
wrong-type session regression will become a missing/non-string evaluation
metadata regression. A direct assertion will lock the exact fake candidate key
set so the fixture cannot silently grow evaluator-only fields again.

Alternative considered: retain the richer fake and add one isolated production
fixture. Rejected because every runner-path test should exercise the actual
candidate boundary.

### Preserve the consumed publication without current-source reinterpretation

The six canonical output files, registration, closeout, module, and archived
change remain unchanged. A focused test will load the committed registration
and run `verify_artifact_directory()` directly, proving byte-for-byte artifact
recomputation without native loading. The source-bound `verify_registered()`
preflight is not used after changing the implementation source because its old
registration intentionally binds the consumed implementation commit.

Alternative considered: weaken the consumed registration's implementation
binding so the current source could satisfy it. Rejected because that would
rewrite the meaning of preregistered evidence.

## Risks / Trade-offs

- [No candidate-side cross-check for `action_type`] -> Unique validated
  `action_id`, Current mapping, input hashes, and non-empty evaluation metadata
  remain enforced; the adapter never promised that candidate field.
- [Fake fixtures can drift again] -> Assert the exact production candidate key
  set in a focused regression.
- [Historical full preflight rejects successor source bytes] -> Preserve the
  old commit and registration; use the source-independent canonical artifact
  verifier for the consumed output and make no new execution claim.
- [A source fix is mistaken for retry authority] -> Keep all authority false,
  create no registration/output, and update project direction explicitly.

## Migration Plan

1. Freeze and recheck the consumed registration, output, closeout, and module
   hashes before editing source.
2. Add a red production-schema fixture regression.
3. Remove the single invalid comparison and retain evaluation metadata checks.
4. Run focused no-native tests, canonical artifact verification, compile and
   diff checks, the partitioned commit gate, and strict OpenSpec validation.
5. Update project direction, sync the modified requirement, archive, commit,
   and push without native execution.

Rollback is a source-and-test revert. No evidence migration is allowed.

## Open Questions

None. A later diagnostic registration is a separate decision and is not part
of this change.
