## Why

R5 produced and pushed an exact compact inventory plus matching source-only and
standalone verification, but its registration boundary failed closed after a
broad schema search read protected r3/r4 inventory content. A distinct,
registration-only successor is needed to preserve that denial while recovering
the already-proven all-false registration through a path-allowlisted API.

## What Changes

- Add producer and independent standard-library validators for the frozen
  `noncombat-card-acceptance-empirical-successor-registration-v1` schema.
- Add a registration builder that accepts only explicitly supplied canonical r5
  inventory, build receipt, verification receipt/completion, and standalone
  result; it performs no path discovery or directory enumeration.
- Add strict raw-byte parsing at the allowlisted driver boundary so duplicate
  keys or bytes that differ from canonical trailing-newline JSON are rejected
  before mappings reach the builder.
- Add a dedicated one-shot registration driver that validates the exact
  allowlist without enumeration, claims an immutable receipt before input
  access, opens every input once, and exclusively publishes the validated
  registration.
- Freeze one canonical self-digested driver request and one exact CLI whose only
  caller-selected evidence path is that request. The request binds the pushed
  preflight, six input identities, receipt/output paths, registration identity,
  and source commits.
- Preregister r6 as a registration-only identity. It does not rebuild or
  reverify the inventory and does not grant seed, native, model, environment,
  gameplay, training, evaluation, OPE, qualification, promotion, or execution
  authority.
- Publish a canonical all-false registration only after producer and standalone
  validators agree exactly. Complete parent task 6.2 while leaving 6.3 and any
  training request incomplete.
- Fail r6 closed before publication on any unexpected path, field, digest,
  authority value, evidence mismatch, predecessor access, or worktree drift.
- Validate the registration fully in memory, then publish it through one
  exclusive create/write/flush/fsync attempt. Any created path or publication
  failure consumes r6 and forbids same-identity retry or replacement.

Live evidence is the pushed r5 verification commit `7ff1e9c89126dc5401dfbdb0ccc8b237673d152c`:
inventory file digest `8ffa0bf81ed66281cd48169928bc6133b4ec49d6b5b964eda7f86f3c8ae8a773`,
inventory semantic digest `deecb81010b76b4fbd197bef1eb732577481ae01591b9fa1a92b0428fe0526f3`,
source-only completion `fb5b688e1c882f9cddf088ef82239ccf2a617a1de99f6ef60dd10bc37dea8632`,
and standalone verification `50f19900c8367f47a2702a8544de44fe663f59ca28fc827de7d716addaa7917c`.
R5's fail-closed incident is pushed at `de7cbc52ec585b081b890d10783c28a43d9bdfb9`
and its terminal OpenSpec archive is pushed at
`39e6864d8a5ca7d7194d98624212edd0f9b5ca51`; the r5 registration is absent and
parent tasks 6.2/6.3 are unchecked before r6 begins.
Success is one canonical reviewed r6 registration with exact `512/128/512`
cohorts and closed all-false maps, with no r5 retry or downstream request.

Non-goals are inventory build/verification, report-root search, protected
r1-r4 or other non-allowlisted inventory access, source-discovery changes,
seed/cohort changes, gameplay,
training, tuning, evaluation, OPE, or policy promotion. Before registration
publication, rollback removes only uncommitted r6 planning/registration
artifacts before driver process creation. The first registration-driver process
invocation consumes r6. Its
receipt is exclusively created before input access. Any parsing, validation,
access, process, receipt, output, publication, or accounting failure preserves
complete or partial evidence and closes r6 without reopening, deletion, retry,
repair, or replacement under the same identity.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Add a distinct
  registration-only r6 recovery path over pushed r5 dual-verification evidence.
- `noncombat-card-acceptance-inventory-source-boundary`: Require an explicit
  evidence-path allowlist and reject report-root enumeration or predecessor
  access before r6 registration publication.

## Impact

Affected files are the card-acceptance seed-inventory producer, a dedicated
registration driver, independent verifier, focused tests, parent OpenSpec
tasks, and bounded r6 reports. No new
dependency, native module, checkpoint, CommunicationMod, or gameplay surface is
introduced.
