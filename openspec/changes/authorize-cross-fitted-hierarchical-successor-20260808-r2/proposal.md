## Why

The exact 20260808-r2 execution request is pushed and remains non-authorizing.
The maintainer has already granted an auditable solo-repository standing
delegation, so the next boundary is to resolve that grant to the exact request
and publish a separately tracked authorization without requiring another
manually transcribed digest tuple.

## What Changes

- Publish one canonical standing-delegation v1 manifest preserving the exact
  external-human grant, timestamp, message ID, task ID, closed scope,
  exclusions, revocation rule, and self-digest.
- After checking that no later explicit human revocation exists, resolve that
  manifest to request SHA-256
  `6257a36c6573c8c412bb8727736e81b063dd0c7076f1ea5b41a70d4a08206c2e`
  as one canonical delegated-approval v2 and deterministic review.
- Commit and push the approval stage before deriving one canonical tracked
  authorization v1 and a separate deterministic review.
- Keep the registered output root absent and stop after authorization. Do not
  load native or model code, construct an environment, access a seed, fit,
  train, evaluate, run gameplay, or invoke CommunicationMod.
- Success means that exact delegation, approval, and authorization artifacts
  independently validate against the pushed registration and request, are
  published in the required order, and leave execution unstarted.
- Before each publication commit, rollback removes only additive untracked
  artifacts from that stage. After push, preserve published bytes; any defect
  requires a new approval or authorization identity rather than mutation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-cross-fitted-hierarchical-learning-successor`: bind the exact
  20260808-r2 request to the existing solo-maintainer standing-delegation
  contract and publish approval and authorization as separate irreversible
  lifecycle stages.

## Impact

- Additive standing-delegation, delegated-approval, authorization, and review
  artifacts under `reports/`.
- Existing source-only producer and independent standard-library validation
  paths; no implementation or test-source edit is expected.
- One delta requirement, project-direction update, and archived OpenSpec
  change. The long repository commit gate and gameplay validation are not
  applicable to evidence-only artifacts.
