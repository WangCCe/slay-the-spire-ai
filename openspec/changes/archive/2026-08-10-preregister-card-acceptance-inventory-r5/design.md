## Context

R4 proved the compact builder works: it published a 249,500-byte v4 inventory
covering 805 sources and 11,775,420 seed occurrences with fixed
`512/128/512` cohorts. R4 nevertheless became terminal because a review command
invoked the old verification entrypoint before distinct verification authority
and launch artifacts existed. No r4 verification or registration was accepted.

The pushed source at `525c302df2d54cf06c756a9dc55fbae4ed9cb8b0`
now rejects that command shape at argparse, requires canonical build plus
verification authority files, creates a verification-specific immutable
receipt before evidence access, emits a bounded flushed completion, and keeps
build CLI compatibility. Static review is text-only, owning tests passed 265,
the full gate passed 5,803 with 18 skipped, and the hardening change is archived.

## Goals / Non-Goals

**Goals:**

- Preregister one distinct r5 build and verification authority chain against
  the pushed hardened source.
- Build at most one compact v4 inventory without predecessor-content access.
- Track and push exact build output, receipt, and completion before deriving
  verification prerequisites.
- Run one hardened source-only verification with its own one-shot receipt,
  then require standalone verifier agreement.
- Publish one all-false registration and complete parent task 6.2 only on exact
  agreement.

**Non-Goals:**

- Retrying or resuming r5 after any process invocation failure.
- Reading, hashing, parsing, converting, deleting, or registering r3 or r4
  unverified inventory content.
- Changing source discovery, seed roles, cohort selection, schemas, ceilings,
  gameplay policy, simulator behavior, RL objectives, or thresholds.
- Native/model/checkpoint/environment loading, training, canary, holdout,
  evaluation, OPE, gameplay, CommunicationMod, qualification, promotion, parent
  task 6.3, or any downstream authority.

## Decisions

### Bind one new identity to the pushed hardened source

Use source commit `525c302df2d54cf06c756a9dc55fbae4ed9cb8b0`,
output root
`D:/PycharmProjects/slay-the-spire-ai/reports/noncombat_card_acceptance_empirical_successor_20260811_r5`,
inventory request id
`noncombat-card-acceptance-empirical-successor-20260811-r5-inventory-request-v1`,
verification request id
`noncombat-card-acceptance-empirical-successor-20260811-r5-inventory-verification-request-v1`,
and registration id
`noncombat-card-acceptance-empirical-successor-20260811-r5-registration-v1`.
Planning/report commits may advance HEAD only while it remains pushed,
tracked-clean, and an exact source-compatible descendant.

The path preflight binds tracked terminal r1-r4 evidence and the absolute
excluded predecessor roots, but it does not open predecessor inventory bytes.
Every r5 output, staging, attempt, build receipt, verification receipt, and
registration path must be absent before its owning authority is published.

### Use no reinvocation path

R5 permits one process invocation for build and one for verification. The
existing implementation may describe a bounded pre-receipt reinvocation as a
general option, but this identity deliberately does not preregister or exercise
it. Any process failure, missing completion, unexpected child, ambiguous access,
or receipt state closes that operation without retry, altered launch, changed
path, raised ceiling, tuning, or substitution. A future attempt requires a new
OpenSpec successor identity.

This is stricter and simpler than r4. It avoids conditional authorization whose
main practical effect was to enlarge the control surface.

### Separate build publication from verification authority

Build uses only the existing inventory stage and exact build request,
authorization, delegated approval, and launch. Its command is invoked directly
under a bounded outer observer, never by a reviewer. On success, canonical
inventory bytes, build receipt, completion, and bounded review are tracked,
committed, and pushed.

Only then may the six verification prerequisites be frozen:

- inventory request digest;
- inventory authorization digest;
- build launch digest from the canonical build receipt;
- build receipt digest;
- inventory file digest;
- inventory semantic digest.

Verification gets a separate `inventory-verification` request, standing-
delegation approval, authorization, and fresh launch. The exact CLI supplies
the build request/authorization plus those four verification artifacts. Build
approval and launch files are not caller-selected verification arguments.

### Keep every review non-executable

Independent planning, authority, completion, and terminal reviews receive
canonical artifact text and recorded hashes only. Reviewers are explicitly
forbidden from invoking tools, commands, tests, inventory operations, or
verification. Execution occurs only in the main controlled task after the
corresponding pushed authority boundary.

### Register only after both reconstructions agree

The source-only verifier must reproduce the compact source registry, counts,
exclusions, cohorts, role digests, authority evidence, and whole digest. The
standalone verifier must independently accept the same v4 structure without
repository authority. Only exact agreement may publish the frozen all-false
registration. Build or verification completion alone grants no registration or
training authority.

## Risks / Trade-offs

- [Risk] A transient pre-receipt failure consumes schedule time without a
  retry. -> Mitigation: run exact source-only preflight and owning tests first;
  require a new identity rather than conditional reuse if launch still fails.
- [Risk] A reviewer repeats the r4 side effect. -> Mitigation: send text only,
  prohibit tools, and omit executable commands from review material.
- [Risk] Tracked build bytes advance HEAD after the fixed source. -> Mitigation:
  verification validates pushed ancestry plus exact source inventory and binds
  the already pushed build digests.
- [Risk] Predecessor inventories are accidentally treated as evidence. ->
  Mitigation: use only tracked terminal metadata and excluded path existence;
  never read or hash predecessor content.
- [Risk] Registration is mistaken for training approval. -> Mitigation: retain
  all-false authority/operation maps and leave parent task 6.3 incomplete.

## Migration Plan

1. Strict-validate and text-only review this planning change, then commit and
   push it.
2. Render/review/push build dispatch, source/path preflight, and the inventory
   request.
3. After that push, resolve/review/push delegated approval and authorization;
   after the second push, recheck revocation and capture/review/push fresh
   launch.
4. Recheck pushed cleanliness, process absence, exact command identity, tests,
   and all r5 absence conditions; invoke build once.
5. On build success, preserve/review/commit/push inventory, receipt, and
   completion. On any failure, publish terminal evidence and close r5.
6. Derive/review/push the separate verification request. After that push,
   resolve/review/push delegated approval and authorization; after the second
   push, recheck revocation and capture/review/push fresh verification launch.
7. Recheck the exact verification boundary and invoke verification once.
8. On exact source-only and standalone verification, publish/review/push the
   all-false registration and complete parent 6.2. Otherwise close terminal.
9. Publish closeout, sync specs, archive r5, strict-validate globally, and push.

Before any build or verification process is created, rollback removes only
uncommitted r5 artifacts. After process creation, rollback preserves invocation,
failure, receipt, and output evidence even when no receipt was written, closes
the failed identity, and denies registration and downstream authority.

## Open Questions

None.
