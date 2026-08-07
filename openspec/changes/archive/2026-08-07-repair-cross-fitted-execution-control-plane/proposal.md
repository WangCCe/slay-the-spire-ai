## Why

The consumed cross-fitted successor reached its 14,400-second deadline after
only 11 completed accesses because each access repeatedly revalidated and
hashed a 63 MB registration; one source-only identity validation measured
56.016 seconds versus 0.530 seconds to parse the JSON. Its valid post-start
failure also retained `charged_seconds=0.0`, and producer closeout took about
2,228 seconds from failure witness to manifest, so another experiment would
repeat known control-plane defects rather than test the learning mechanism.

## What Changes

- Validate the immutable registration, execution identity, output root, and
  digest once into a typed in-process context after authorization/source
  preflight, then reuse that context through access journals, resources,
  checkpoints, failure handling, and terminal publication.
- Preserve durable journal, schedule, lease, hash-chain, byte, and independent
  verification checks while proving no full-registration work occurs per seed
  or nested terminal helper.
- Charge elapsed time on every post-start terminal path, including
  non-infrastructure failures before the first checkpoint, before freezing the
  terminal intent.
- Reuse the validated context and terminal intent during producer closeout so
  intent, terminal, and manifest publication do not recursively revalidate the
  complete registration.
- Harden Windows execution supervision: wrapper completion is not process exit;
  active output remains unreadable until the true Python child exits and its
  lease is no longer locked.
- Add RED structural, accounting, recovery, corruption, and source-only
  performance regressions. Success is bounded validation count and a valid
  synthetic terminal bundle, not a new native run or policy result.

No consumed registration, authorization, terminal artifact, seed identity, or
model is changed. Non-goals are simulator tuning, estimator/reward/architecture
changes, native loading, empirical seed access, another mechanism experiment,
policy-quality evaluation, formal RL, gameplay, CommunicationMod,
qualification, or promotion. Before a new source commit, rollback removes only
this additive change and code/test edits. After publication, rollback reverts
the source commit; it never mutates or retries the consumed execution.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-cross-fitted-hierarchical-learning-successor`: Require one
  validated execution context, seed-count-independent registration validation,
  complete elapsed-time accounting on terminal failure, bounded producer
  closeout, and true-child liveness before output inspection.

## Impact

- Updates the cross-fitted control plane and independent verifier under
  `analysis_scripts/`, their focused tests, source bindings, execution
  documentation, and project direction.
- Keeps the Torch runtime algorithm, native adapter, registration/cohort,
  learning controls, terminal schemas, agent behavior, `main.py`,
  CommunicationMod configuration, and production checkpoints unchanged.
- Requires a fresh future source identity and registration before any later
  evidence-bearing execution; this change itself grants no execution authority.
