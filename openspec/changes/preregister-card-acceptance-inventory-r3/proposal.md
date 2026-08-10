## Why

The r2 card-acceptance inventory identity terminated before authority
validation because its exact `python -I` script entrypoint could not import the
control module. That entrypoint is now repaired, regression-tested, reviewed,
and pushed, so the parent empirical-successor task still needs one distinct r3
identity to materialize and independently verify the fresh `512/128/512`
registration before any training request is eligible.

## What Changes

- Bind r3 to the pushed isolated-dispatch repair and require its exact
  side-effect-free `check-dispatch` command and canonical process binding before
  any r3 authority artifact is published.
- Create a new r3 source inventory, request id, output root, request, delegated
  approval, authorization, and launch observation; preserve every r1/r2
  artifact and identity as terminal evidence.
- Treat the durable request-bound started receipt, rather than mere process
  creation, as the one-shot inventory boundary. A pre-start failure does not
  itself consume r3 only after a bounded failure plus independent complete-
  side-effect review; any ambiguous effect or existing/partial receipt blocks
  or permanently consumes that request. The same request permits at most one
  reviewed pre-start reinvocation; a second pre-start failure closes r3.
- Run one logical r3 build start only after exact dispatch, source/path,
  authority, pushed/clean-tree, output/receipt absence, and focused test gates
  pass. Do not change source, path, request, cohort, thresholds, or authority in
  response to a started outcome.
- On success, run the distinct read-only verifier and publish one independently
  reviewed all-false registration containing exactly 512 training, 128 canary,
  and 512 holdout seeds. On terminal failure, publish one reviewed failure and
  grant no registration or downstream authority.
- Update parent task 6.2 only after successful independent reconstruction and
  registration. Task 6.3 and all training, native/model/environment, gameplay,
  CommunicationMod, evaluation, qualification, and promotion authority remain
  false.
- Live evidence is r2 terminal failure
  `d44f6d900c902d94af20fba365725e9cc46c423a3ab10cbcedf16747e80ec3fb`
  followed by pushed isolated-dispatch source `3dd915e7c`; success is a
  verified r3 inventory and all-false registration, not merely a passing
  dispatch check.
- Rollback before a started receipt removes only uncommitted r3 artifacts.
  After a receipt exists, rollback preserves all evidence and denies downstream
  authority; it never deletes, retries, resumes, repairs, or replaces the
  consumed identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Add the distinct r3
  inventory/verification/registration gate and align one-shot consumption with
  the durable started receipt.
- `noncombat-card-acceptance-inventory-source-boundary`: Require r3 path/source
  preflight to bind the pushed dispatch repair, both terminal predecessors,
  generated-root exclusions, and absent r3 output/staging/attempts/receipt
  paths before authority publication.

## Impact

The change is expected to add only source-only r3 OpenSpec and report artifacts
plus, on success, the new inventory and all-false registration. It reuses the
existing control plane, seed-inventory CLI, standing delegation, independent
verifier, and Windows production interpreter. It changes no gameplay policy,
simulator, RL objective, model/checkpoint, CommunicationMod configuration,
dependency, or test assertion.
