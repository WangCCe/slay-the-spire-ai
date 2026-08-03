## Why

The consumed Current bridge diagnostic finalized with zero rows because the
runner read `candidate["action_type"]`, although the production adapter
candidate contract does not expose that field. The focused fake candidate did
expose it, so the regression suite failed to represent the live native schema.

## What Changes

- Make diagnostic fake candidates match the validated production adapter
  schema exactly and add a regression proving that no candidate-side
  `action_type` is required.
- Remove the invalid candidate-field comparison while retaining validation of
  the non-empty Current evaluation `action_type`, unique legal `action_id`,
  input hashes, event mapping, and transition identity.
- Preserve the consumed registration, finalized failed artifacts, closeout,
  seeds, module, and verdict byte-for-byte.
- Run only no-native unit and verifier checks. Do not create a replacement
  registration, construct an environment, consume a seed, refresh readiness,
  or start gameplay, OPE, model fitting, reward work, or training.

Success means production-shaped fake candidates without `action_type` pass the
deterministic runner contract, a missing or non-string evaluation `action_type`
still fails closed, archived artifacts remain unchanged, and the consumed
attempt remains a failed non-retryable result. The rollback boundary is this
source-and-test fix; reverting it must require no evidence rewrite.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-current-bridge-diagnostic-smoke`: Require the runner to consume
  only fields guaranteed by the validated adapter candidate schema and keep
  evaluator-only action metadata separate.

## Impact

The change is limited to the Current bridge diagnostic runner, its focused
tests, the existing capability spec, and closeout direction. It changes no
gameplay policy, bridge evaluator, adapter schema, simulator module, historical
artifact, model, reward, or training path.
