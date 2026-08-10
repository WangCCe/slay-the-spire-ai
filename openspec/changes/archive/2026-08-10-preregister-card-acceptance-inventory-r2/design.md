## Context

The r1 request bound source commit `5cbc6960` and made its sole inventory call
after later authority commits. That call failed on a tracked readiness staging
artifact and is permanently terminal. The source-boundary repair was reviewed,
archived, and pushed as `cc7fde4602ea7be414700330784733f56083bed2`.
The parent successor change still requires task 6.2 to produce a verified fresh
inventory and an all-false empirical registration before training can even be
requested.

The existing seed-inventory module already permits a pushed ancestor source
commit while requiring current `HEAD == origin/master`, a tracked-clean tree,
and an exact current source-inventory digest. It also separates authorized
`build-inventory` from read-only post-build verification. However, a failure
before output staging leaves no durable marker, so the same authorization can
technically invoke `build-inventory` again. No new runner or algorithm is
required, but one-shot enforcement must become persistent before r2.

## Goals / Non-Goals

**Goals:**

- Establish r2 as a distinct identity whose predecessor, source, output, and
  authority chain are reviewable before execution.
- Make a started build request durably non-retryable before historical blob
  reads or seed discovery.
- Detect path/source/authority drift before blob reads or seed discovery.
- Permit one build call only, followed by verification and registration only
  on success.
- Preserve a terminal failure without retry or downstream authority.

**Non-Goals:**

- Retrying, resuming, repairing in place, or replacing r1.
- Changing source classification, seed parsing, seed order, cohort sizes,
  thresholds, model architecture, training, or evaluation.
- Loading native modules, Torch, models, checkpoints, environment runtime,
  gameplay, or CommunicationMod.
- Granting training, canary, holdout, qualification, or promotion authority.

## Decisions

### Fix the r2 request and output identity before source publication

The request id is
`noncombat-card-acceptance-empirical-successor-20260810-r2-inventory-request-v1`,
and the output root is
`reports/noncombat_card_acceptance_empirical_successor_20260810_r2`.
Request, approval, authorization, launch, failure, inventory, verification, and
registration artifacts use the same r2 stem and remain separate from r1.

The exact source commit is the clean pushed implementation commit containing
the started-receipt guard and this reviewed change. It must descend from
`cc7fde4602ea7be414700330784733f56083bed2` and is recorded by the source-only
preflight before any authority artifact is rendered.

Alternative: bind source directly to `cc7fde460`. Rejected because that commit
lacks durable one-shot enforcement. Alternative: point r2 at the final
authority commit. Rejected because the request cannot bind a commit containing
itself. The existing pushed-ancestor rule was hardened for this publication
sequence.

### Persist a request-bound started receipt before source discovery

The seed-inventory module derives an attempts root beside the output:
`<output_root>_attempts/<request_sha256>/started.json`. After full authority,
source-inventory, pushed-ancestry, tracked-clean, and output-absence validation,
but before `_build_source_registry_and_rows`, it creates the parent and writes a
canonical request/authorization/launch/source binding with exclusive `xb`
creation, flush, and file `fsync`. Existing receipt bytes are never removed,
rewritten, or treated as permission to continue.

The attempts root is already excluded by the generated-root source boundary.
A second invocation with the same request sees the receipt and fails before
historical path or blob discovery. A crash before exclusive receipt creation is
pre-start; any exception or crash after creation consumes the identity. A
successful output keeps the receipt as execution evidence.

Alternative: rely on output/staging existence. Rejected because the r1 failure
occurred before both. Alternative: write the receipt inside staging. Rejected
because staging may not exist at source-parse failures and is coupled to output
publication cleanup.

### Add a path-only preflight before authority publication

The preflight uses the existing standard-library source inventory and tracked
Git tree. It records current pushed/clean state, exact pushed receipt-hardening
source commit and repair ancestry,
r1 evidence digests and terminal status, absence of the r2 output/staging roots,
candidate path count/hash, excluded roots and kinds, and exact exclusion of the
offending readiness root. It does not read candidate blobs or seed values.

Any unsupported path, ambiguous generated-root kind, r1 evidence drift,
source-inventory drift, existing r2 output, or unpushed/dirty tracked state is a
pre-start NO-GO. No threshold or path substitution is allowed after review.

Alternative: run build and rely on fail-closed parsing. Rejected because r1
already showed that a cheap path boundary can prevent consuming an identity on
known source-shape problems.

### Reuse control-plane behavior, not r1 authority artifacts

The r2 request, request review, delegated approval, approval review,
authorization, authorization review, and launch observation are newly rendered
and digest-bound. The preserved standing external-human grant may be referenced
only through the existing exact item/text/time/task binding. r1 request,
approval, authorization, and launch artifacts remain evidence and cannot
authorize r2.

Publication uses logical boundaries: preflight and request/review; delegated
approval/review; authorization/review; then a fresh launch observation after
all preceding commits are pushed. Every authority map remains false except the
existing source-only repository read, seed discovery, and cohort
materialization permissions required by `build-inventory`.

### Treat the sole build invocation as the irreversible boundary

Before invocation, validate fresh revocation state, source ancestry/inventory,
tracked cleanliness, output and receipt absence, preflight digest, and all r2
authority artifacts. Call `build-inventory` once. Receipt creation is the
durable started boundary. A failure writes and reviews one
terminal r2 failure and creates no registration. A success permits one distinct
`verify-inventory` reconstruction; matching reconstruction then permits the
existing all-false registration for exactly 512 training, 128 canary, and 512
holdout seeds.

No failure permits retry, resume, seed/path/source replacement, threshold
change, or tuning. Verification does not select or publish cohorts.

## Risks / Trade-offs

- [Risk] Another malformed ordinary source can terminate r2. -> Mitigation:
  path-only preflight catches generated and unsupported shapes, while strict
  ordinary parsing intentionally remains fail closed.
- [Risk] Receipt I/O fails or a process crashes while writing. -> Mitigation:
  exclusive creation consumes no identity before file creation; any existing or
  partial receipt blocks all later invocations and is preserved for review.
- [Risk] Documentation commits advance HEAD past the source commit. ->
  Mitigation: require the fixed repair commit to remain an ancestor while
  current HEAD equals pushed `origin/master` and the source inventory remains
  exact.
- [Risk] r2 is mistaken for training approval. -> Mitigation: registration and
  every downstream authority remain false; task 6.3 requires a later training
  request and review.
- [Risk] Standing delegation reuse is mistaken for r1 replay. -> Mitigation:
  preserve only the exact human grant and require fresh r2 request-bound
  approval, observation, and authorization digests.

## Migration Plan

1. Add RED coverage for a mid-build failure followed by a rejected second call,
   implement the receipt guard, run focused source-only verification, and push
   the clean implementation commit.
2. Produce and independently review the source-only path preflight that fixes
   that pushed commit as r2 source.
3. Render, validate, commit, and push r2 request/authority artifacts in their
   defined boundaries.
4. Recheck launch state and invoke r2 build at most once.
5. On success, independently verify and publish the all-false registration. On
   failure, preserve a reviewed terminal report and stop.
6. Update parent task 6.2 only after successful verification/registration;
   otherwise record r2 terminal without checking it.

Before invocation, rollback removes only uncommitted r2 artifacts. After
invocation, rollback is evidence preservation and downstream denial, never
deletion or retry.

## Open Questions

None.
