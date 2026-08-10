## Context

r1 is terminal after reading an excluded generated root. r2 is terminal after
its isolated script entrypoint failed before receipt creation. r3 is terminal
after its durable receipt was written and a 2,675,460,894-byte v3 inventory was
published but the CLI failed while writing the full mapping to stdout. The r3
artifact remains published and unverified; no verifier or registration was
permitted.

The source now contains three separately reviewed repairs: bounded build/verify
CLI completion, compact aggregate inventory schema v4 with a 64 MiB canonical
ceiling, and v4 support in the standalone successor verifier. The final source
boundary `710599ec6c2a9f7964da1e43084d2d577dffb7b3` is pushed on `master`, the
relevant full gate passed 5,773 tests with 18 skipped, and the compact repair is
archived in OpenSpec. Parent task 6.2 remains incomplete.

## Goals / Non-Goals

**Goals:**

- Preregister one distinct r4 source-only inventory identity bound to the
  pushed compact-v4 source.
- Preserve r1/r2/r3 as terminal and make the r3 artifact content inaccessible
  to r4 planning, preflight, verification, and registration.
- Prove dispatch, source/path, compact-schema, authority, and write-surface
  readiness before a logical r4 build start.
- Build and independently reconstruct one bounded v4 inventory with fixed
  `512/128/512` cohorts, then publish an all-false registration.
- Complete parent task 6.2 only after registration review.

**Non-Goals:**

- Reading, hashing, parsing, validating, converting, deleting, relocating, or
  registering the terminal r3 inventory.
- Editing inventory selection semantics, historical role discovery, cohort
  counts, policy code, simulator behavior, RL objectives, or thresholds.
- Loading native modules, Torch, models, checkpoints, or environments.
- Training, canary, holdout, evaluation, OPE, gameplay, CommunicationMod,
  qualification, promotion, or parent task 6.3.
- Treating a dispatch check, build exit, CLI completion envelope, or compact
  file size alone as verified inventory evidence.

## Decisions

### Freeze a distinct compact-v4 source identity

r4 source is fixed at
`710599ec6c2a9f7964da1e43084d2d577dffb7b3`. Planning and report commits may
advance HEAD, but every execution boundary must be pushed, tracked-clean, and a
descendant of that source while reproducing its exact script/control/verifier
identities.

The source/path boundary must prove all of the following before request
publication:

- exact production interpreter, repository cwd, `-I`, script path, and
  deterministic `check-dispatch` bytes;
- compact schema
  `noncombat-card-acceptance-empirical-successor-seed-inventory-v4`;
- canonical inventory ceiling 64 MiB and CLI completion ceiling 2,048 bytes;
- exact tracked terminal receipts/failures/reviews/postmortems for r1/r2/r3;
- exclusion of every predecessor output and generated root from r4 source
  candidates;
- absence of r4 output, staging, attempt, receipt, verification, and
  registration paths.

The r3 output may be observed only as an excluded absolute path whose
preservation is required. Its content identity comes only from already tracked
terminal evidence; r4 must not open, stream, hash, canonicalize, or verify the
file. Binding the predecessor by rereading it was rejected because that would
turn terminal unverified bytes into new evidence.

### Reuse the durable receipt state machine

r4 uses the existing request-bound exclusive `started.json` receipt as the
logical one-shot boundary. An empty, partial, invalid, or complete receipt
consumes the identity. A pre-receipt process failure is not an automatic retry:
it first requires the existing bounded pre-start failure and independent
complete-side-effect review. Only one unchanged ordinal-two reinvocation may be
authorized after an external-only repair and fresh reviewed revocation
observation. A second pre-start failure or any ambiguity closes r4.

No new retry mechanism is introduced. Any failure after receipt creation,
including source scanning, compact validation, byte-ceiling enforcement,
publication, completion rendering, or verification, is terminal. Source,
paths, request, cohorts, resource ceilings, thresholds, and authority cannot be
changed in response to the outcome.

### Keep authority stages separate but use the standing delegation path

Reuse only the immutable external-human standing grant. Create fresh r4
request-bound delegated approval, authorization, approval-time revocation
observation, and launch-time revocation observation. Predecessor request,
approval, authorization, launch, receipt, or output artifacts cannot authorize
r4.

Publication boundaries are:

1. planning only;
2. dispatch observation/review, source inventory, path preflight/review, and
   request/review;
3. delegated approval/review and authorization/review;
4. fresh launch observation/review;
5. pre-start gate and no-write recheck;
6. one logical build, distinct verification, and terminal result.

Every r4 authority map permits only repository evidence reading, historical
seed discovery, cohort materialization, compact inventory publication, and the
separately authorized source-only reconstruction needed by that stage. Native,
model, environment, fitting, training, evaluation, gameplay, CommunicationMod,
formal RL, OPE, qualification, promotion, and downstream execution remain
false.

### Freeze paths, limits, and registration before seed access

Use output root
`D:/PycharmProjects/slay-the-spire-ai/reports/noncombat_card_acceptance_empirical_successor_20260810_r4`
and request id
`noncombat-card-acceptance-empirical-successor-20260810-r4-inventory-request-v1`.
The request fixes `max_materialized_seeds=1152`, ascending `512/128/512`
selection, 64 MiB canonical inventory bytes, 2,048-byte completion bytes, and a
3,600-second outer observer. The observer grants no runtime or downstream
authority.

The registration is frozen as schema
`noncombat-card-acceptance-empirical-successor-registration-v1` with identity
`noncombat-card-acceptance-empirical-successor-20260810-r4-registration-v1`.
It retains the existing exact top-level fields, cohort/role mapping, fifteen-key
authority map, ten-key empirical-operation map, canonical trailing-newline
self-digest rule, and all-false values. No outcome-dependent field may be added.

### Register only source-reconstructed compact evidence

Build success means a closed canonical v4 file plus valid bounded CLI completion
and immutable receipt. It grants verification authority only through a
distinct request/authorization/launch boundary. Source-only verification must
rescan the exact registered Git bytes and reproduce source identities,
per-source document and occurrence counts, total row count, sorted unique
exclusions, fixed cohorts, role digests, authority bindings, and whole digest.
The standalone successor verifier then validates the exact compact structure
without repository-read authority.

Only agreement between those boundaries permits one all-false registration.
Any mismatch leaves parent task 6.2 unchecked and closes r4 without training
authority.

## Risks / Trade-offs

- [Risk] r4 accidentally treats the large r3 output as source evidence. ->
  Mitigation: bind only tracked terminal evidence and excluded path identity;
  forbid all content access and include the predecessor root in path preflight.
- [Risk] compact output still exceeds 64 MiB. -> Mitigation: fail before staging
  or publication; do not raise, split, compress, or tune the ceiling.
- [Risk] bounded CLI output is mistaken for independent verification. ->
  Mitigation: require a distinct source-rescanning verifier and standalone
  structural verifier before registration.
- [Risk] report commits advance HEAD beyond the fixed source. -> Mitigation:
  require pushed tracked-clean ancestry and exact source module digests at each
  boundary rather than equality to the original source commit.
- [Risk] approval machinery dominates the experiment. -> Mitigation: reuse the
  established standing-delegation schemas and stages; add no new authorization
  type or verifier framework.
- [Risk] a successful registration is mistaken for training approval. ->
  Mitigation: all authority maps remain false and parent task 6.3 stays
  incomplete.

## Migration Plan

1. Strict-validate and independently review this planning-only change, then
   commit and push it without r4 authority artifacts.
2. Reproduce exact isolated dispatch and render/review the source inventory,
   path preflight, request, and their bounded reviews without seed values or r3
   artifact content; commit and push that boundary.
3. Resolve the standing grant to the exact request, render/review authorization,
   and push the authority boundary.
4. Capture and review a fresh launch-time revocation observation, then push it.
5. Produce/review/push the pre-start gate and perform a separate no-write
   pushed-clean/absence/process recheck.
6. Invoke one logical r4 build. On pre-start failure, apply only the established
   bounded one-time reinvocation rule; on post-receipt failure, close terminal.
7. On build success, run distinct source-only and standalone verification. Only
   exact reconstruction may publish the all-false registration and complete
   parent task 6.2.
8. Publish a bounded closeout, sync specs, archive r4, strict-validate, and push.

Before receipt creation, rollback removes only additive uncommitted r4
artifacts. After receipt creation, rollback preserves immutable evidence and
denies downstream authority.

## Open Questions

None.
