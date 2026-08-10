## Context

`verify-inventory` currently reuses the inventory build stage request,
authorization, approval, and a caller-supplied launch observation. Production
validation proves those artifacts are internally valid, but it does not prove
that a distinct verification operation was requested and authorized. The r4
request tried to add that distinction in report-only JSON; a commit-review
tool ignored the outer files and successfully reached the production verifier
entrypoint with the old CLI shape.

The control module already provides canonical stage requests,
authorizations, delegated/external approval validation, fresh launch
observations, exact authority maps, and fixed prerequisite/resource maps. The
standing delegation is scoped to that stage-request schema, so extending the
existing stage model is narrower and more enforceable than inventing another
parallel approval framework.

## Goals / Non-Goals

**Goals:**

- Make a distinct reviewed verification stage mandatory in production code.
- Reject the r4 escaped command shape before inventory or historical evidence
  access.
- Persist one immutable verification execution receipt before reconstruction.
- Preserve build CLI behavior and bounded output.
- Provide focused and full-suite evidence without running a real r4/r5
  verifier or granting registration authority.

**Non-Goals:**

- Recovering, accepting, or rerunning r4 verification.
- Creating an r5 request, inventory, verification, or registration.
- Changing source selection, seed role semantics, compact schema v4, cohort
  counts, gameplay policy, simulator behavior, RL objectives, or thresholds.
- Loading native modules, Torch runtime, models, checkpoints, environments, or
  CommunicationMod; training, evaluation, OPE, qualification, or promotion.

## Decisions

### Add an `inventory-verification` control-plane stage

Extend the existing stage request/authorization machinery with
`inventory-verification`. Its execution authority enables only repository
evidence reading and historical seed discovery; cohort materialization and all
native/model/environment/training/evaluation/downstream authority remain
false. Its prerequisites bind the exact build request, build authorization,
build launch, build receipt, inventory file, and inventory semantic digests.
Its fixed resources bind the 64 MiB inventory and 2,048-byte completion
ceilings without granting execution capacity.

This keeps verification under the existing canonical stage-request schema and
standing-delegation scope. A custom report-only request was rejected because
the CLI could ignore it, which is the failure this change must prevent.

### Give verification an explicit CLI contract

Keep `build-inventory` arguments unchanged. `verify-inventory` receives
explicit build request/authorization paths plus a distinct verification
request, verification authorization, verification approval record, and fresh
verification launch observation. The parser rejects the legacy four-argument
verification command before calling any operation function.

The verifier first validates both authority chains, exact prerequisites,
pushed tracked-clean ancestry, source identities, output path, schemas, and
ceilings. It does not trust caller-selected digests from the inventory.

### Claim verification once before evidence reconstruction

After all authority/source validation and before opening the inventory or
registered historical Git blobs, create the request-bound verification
`started.json` with exclusive `xb`, then write, flush, and fsync canonical
bytes. Any path existence consumes the verification identity, including an
empty, partial, invalid, or complete receipt. A post-receipt failure is
terminal and cannot be retried or repaired in place.

The receipt binds verification request/authorization/launch, build
request/authorization/launch/receipt, inventory file/semantic digests, fixed
source identity, and its own canonical digest. Source-qualification Git reads
needed to validate pushed ancestry may precede the receipt; inventory and
historical candidate evidence may not.

### Use a distinct bounded verification completion

Build continues emitting the existing inventory CLI completion v1.
Verification emits a separate constant-size completion schema that binds the
build inventory and receipt plus the verification request, authorization,
launch, and execution receipt. It must remain at or below 2,048 bytes and must
not serialize source rows, excluded seeds, or cohorts.

This avoids weakening the existing fourteen-field build contract or hiding
the new operation identity in a field that previously meant the build
receipt.

### Prove the boundary with synthetic fixtures only

Tests use temporary Git repositories and compact fixtures. Required RED/GREEN
coverage includes the exact escaped r4 command shape, missing or substituted
verification artifacts, authority broadening, prerequisite drift, access-order
spies, empty/partial/valid receipt collisions, interruption during receipt
write, post-receipt failure, duplicate invocation, exact reconstruction, and
both CLI completion envelopes. No tracked r4/r3 inventory is executed by the
test or review process.

## Risks / Trade-offs

- [Risk] Adding a stage changes shared control-plane maps and tests. -> Keep the
  new stage source-only, add exact disjoint-map regressions, and run the full
  suite because the module is shared by later training stages.
- [Risk] A receipt can make a test fixture terminal after an assertion fails.
  -> Use per-test temporary roots and assert receipt timing directly.
- [Risk] Review tooling may execute command text again. -> Planning and review
  artifacts contain no eligible real command; independent review is explicitly
  static, while production tests use only temporary repositories.
- [Risk] Separate completion schemas add branching. -> Leave build untouched
  and isolate verification completion construction in one validated helper.
- [Risk] Source qualification before receipt is mistaken for reconstruction.
  -> Tests distinguish Git ancestry/source-module identity reads from inventory
  and registered historical blob access.

## Migration Plan

1. Publish and review this planning-only change.
2. Add RED tests for stage identity, legacy CLI rejection, pre-access ordering,
   receipt semantics, exact success, and bounded completion.
3. Implement the control-plane stage and seed-inventory verification boundary
   with no report or experiment execution.
4. Run focused tests, static review, the repository full test gate, and strict
   OpenSpec validation; commit and push one hardening boundary.
5. Sync the modified specification and archive this change.
6. Only a later separately proposed r5 may consume the new production contract.

Rollback before any external verification receipt removes the source/test
change normally. Any receipt created by a future authorized experiment remains
immutable and requires a new identity after failure.

## Open Questions

None.
