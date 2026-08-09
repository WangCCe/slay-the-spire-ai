## Why

The sole `20260810-r1` inventory build is terminal after exposing a generated
source-root gap, and the reviewed repair is now pushed at `cc7fde460`. Review
of the proposed successor also found that one-shot execution is not durably
enforced before publication. Task 6.2 still needs a fresh exclusion inventory,
so progress requires both a request-bound started receipt and a distinct,
pre-registered identity that cannot reuse or reinterpret r1.

## What Changes

- Add a request-bound atomic started receipt before historical blob reads or
  seed discovery; any later invocation of the same request must fail before
  source discovery, even when the first invocation failed before publication.
- Commit and push the receipt hardening as the exact r2 source commit, with
  `cc7fde460` preserved as its required repair ancestor.
- Pre-register `20260810-r2` against that pushed source commit, a distinct
  request id, and a distinct repository-local output root.
- Require a source-only path and authority preflight before publication of the
  r2 request, proving the repair commit is pushed, the r1 evidence is immutable,
  the r2 output is absent, and generated roots are excluded before blob access.
- Publish and review fresh r2 request, delegated approval, authorization, and
  launch observation artifacts. No r1 request, approval, authorization, or
  launch artifact is reused; the preserved standing human grant may be
  referenced only through its existing exact binding.
- Permit at most one r2 `build-inventory` invocation. Any started failure is
  terminal; success alone permits a distinct read-only `verify-inventory` and
  an all-false `512/128/512` empirical registration.
- Keep native loading, environment construction, model loading, training,
  evaluation, gameplay, CommunicationMod, qualification, and promotion out of
  scope.

Live evidence is the pushed r1 failure/review, the exact unclassified readiness
staging path, the archived source-boundary repair, focused `4 passed`, complete
seed-inventory `17 passed`, the repair's independent no-findings review, the r2
proposal review's started-receipt P1, and global strict OpenSpec `82 passed`.
Success is one independently reconstructed inventory with 512 training, 128
canary, and 512 holdout seeds plus an all-false registration; failure is a
preserved terminal report with no registration.

Rollback before r2 starts removes only uncommitted r2 planning or authority
artifacts. After a started invocation, rollback preserves all r2 evidence and
never retries, replaces, tunes, or changes the consumed identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Define how task 6.2 may use
  one distinct r2 inventory identity after terminal r1 without gaining training
  or downstream execution authority.
- `noncombat-card-acceptance-inventory-source-boundary`: Add the reviewed
  future-identity preflight and immutable predecessor boundary required before
  a new inventory build can become eligible.

## Impact

The change affects only OpenSpec records, request-bound one-shot enforcement in
the existing seed-inventory control plane, focused synthetic tests, source-only
request/review tooling, and bounded repository reports. It does not change seed selection,
cohort counts, algorithms, thresholds, simulator mechanics, production policy,
checkpoints, CommunicationMod configuration, or gameplay.
