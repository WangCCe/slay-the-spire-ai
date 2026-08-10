## Context

R5's build and dual verification are valid and pushed, but r5 is terminal
because registration planning crossed the protected predecessor-content
boundary. The frozen registration schema was specified in r3/r4 planning but
has no dedicated producer or standalone validator in current source. R6 must
recover registration without weakening r5's terminal state, rebuilding the
inventory, or scanning report roots.
The pushed r5 incident and archive commits are immutable prerequisites, not
merely narrative history; r6 cannot begin while r5 registration or parent-task
state differs from that terminal boundary.

## Goals / Non-Goals

**Goals:**

- Implement one pure producer builder/validator and one independent
  standard-library validator for the frozen registration schema.
- Implement a one-shot driver that claims its receipt, strict-parses and
  canonical-byte-compares every allowlisted input, accounts for one open each,
  and publishes exclusively without directory discovery.
- Require exact r5 inventory, build receipt, verification receipt/completion,
  and standalone-result agreement before the builder returns a registration.
- Render and review one canonical r6 registration through an explicit path
  allowlist and complete only parent task 6.2.
- Make broad root enumeration, predecessor paths, unknown fields, noncanonical
  bytes, and any true authority or operation value fail closed.

**Non-Goals:**

- Rebuilding or re-verifying r5; accessing r3/r4 inventory content; changing
  source discovery, exclusions, cohorts, or registration fields; creating a
  training request; loading native/model/environment/game state; training,
  evaluation, OPE, qualification, or promotion.

## Decisions

### Add pure mapping APIs instead of a path-discovering registration command

The producer module will expose `parse_canonical_mapping_bytes(...)`,
`build_inventory_registration(...)`, and
`validate_inventory_registration(...)`. The standalone module will expose its
own strict parser plus `verify_inventory_registration(...)`. The parsers reject
duplicate keys and require the original bytes to equal canonical
trailing-newline JSON before returning mappings. Builder and validators receive
those mappings and do no filesystem discovery. A bounded r6 driver may open
only the preregistered absolute allowlist and pass each raw input through the
strict parser before use.

This is preferred over another report-scanning CLI because registration needs
six known evidence objects, not discovery. It also makes path access reviewable
outside schema semantics and keeps unit tests small.

### Preserve the frozen v1 registration fields

R6 uses schema
`noncombat-card-acceptance-empirical-successor-registration-v1` and id
`noncombat-card-acceptance-empirical-successor-20260811-r6-registration-v1`.
The output retains the exact 16 fields frozen by r3/r4, including the build
receipt but not verification-only fields. Verification receipt/completion and
standalone agreement are required builder inputs and remain explicit review
prerequisites rather than silently extending the registration schema.

### Bind registration to historical r5 evidence without reviving r5

The registration's source, request, approval, authorization, launch, receipt,
output root, inventory, cohorts, and role digests come from the verified r5
artifact chain. Its identity is r6. R5 remains terminal, its own registration
path remains absent, and r6 does not claim a new build or verification.

### Make path authorization a closed allowlist

The r6 preflight freezes only these inputs: current r5 inventory, build started
receipt, verification started receipt, verification completion, standalone
verification result, and verification review. It also freezes the single r6
registration output and review paths. Directory enumeration, globbing, report
root search, predecessor paths, symlinks, duplicates, or any additional input
make the boundary NO-GO before input bytes are opened.

The preflight also binds r5 incident commit `de7cbc52e`, archive commit
`39e6864d8`, absent r5 registration, and unchecked parent 6.2/6.3. Drift in any
terminal prerequisite makes r6 NO-GO.

### Put path and publication enforcement in a dedicated driver

`noncombat_card_acceptance_empirical_successor_registration.py` owns the
one-shot lifecycle. It accepts one exact request-like allowlist mapping, rejects
unknown/additional/duplicate paths and symlinks, and never calls directory or
glob enumeration. The first driver process invocation consumes r6. Before any
input open it exclusively creates, writes, flushes, and fsyncs an immutable
started receipt. It then opens every input exactly once, verifies stable regular
file identity and registered hash/size, strict-parses canonical bytes, and
passes mappings to the pure APIs.

Focused tests monkeypatch directory enumeration to fail if called, account for
one input open, and cover symlink/additional-path rejection, existing or partial
receipt, exclusive output collision, short write, flush failure, and fsync
failure. Any process creation, receipt, parsing, validation, access, publication,
or accounting failure is terminal for r6 even when no input or output was
successfully opened.

The transport is frozen as one canonical request file with schema
`noncombat-card-acceptance-empirical-successor-registration-request-v1`.
Its exact fields are `schema_version`, `request_id`, `registration_id`,
`implementation_source_commit`, `inventory_source_commit`,
`preflight_sha256`, `input_bindings`, `receipt_path`, `output_path`,
`registration_schema_version`, `downstream_authority`, and `request_sha256`.
`input_bindings` has exactly six named entries, each containing absolute
canonical path, SHA-256, and size. The downstream map is exact and all false;
`request_sha256` covers every other field with trailing-newline canonical JSON.

The only process shape is the registered Windows interpreter with `-I`, the
fixed driver script, subcommand `publish-registration`, fixed repo root, and one
`--request` path. The request is a control input, not one of the six evidence
inputs, and is committed/pushed before launch. The driver never opens the
preflight itself; it validates the pushed preflight digest embedded in the
request. The immutable receipt binds request/preflight digests, all six input
identities, receipt/output paths, registration id/schema, both source commits,
and the observed exact CLI identity.

### Publish only after in-memory dual validation

After its immutable receipt, the driver builds and validates the registration
entirely in memory with both validators before opening the output path.
Publication then uses one exclusive create, canonical write, flush, and fsync
attempt. Existing output, interrupted write, flush/fsync failure, or any
post-create error preserves the bytes. Because the first driver invocation
already consumed r6, no pre- or post-publication failure permits reopening,
deletion, retry, repair, or replacement.

### Keep reviews text-only and path-bounded

Implementation review receives exact source/diff and test-evidence text only.
Registration review receives exact preflight, registration, validator result,
receipt, request, and access-accounting text only. Reviewers have no tool
permission and cannot search files or roots. Any reviewer access outside the
bounded text closes r6.

### Keep every authority false

The 15-key `authority` and 10-key `empirical_operations` maps are exact and all
false. Registration publication completes parent 6.2 only. Parent 6.3,
training request, approval, authorization, and execution remain absent.

## Risks / Trade-offs

- [Risk] Reusing r5 evidence is mistaken for reviving r5. -> Mitigation: use a
  distinct r6 registration id, preserve the r5 failure, and bind the review to
  the pushed r5 verification and terminal commits.
- [Risk] A pure mapping API cannot itself prove caller path discipline. ->
  Mitigation: implement and test a dedicated receipt-owning driver that rejects
  discovery/symlinks/additional paths, strict-parses raw bytes, and requires the
  observed one-open access set to equal the allowlist.
- [Risk] Verification evidence agrees but registration fields drift. ->
  Mitigation: producer and standalone validators independently reconstruct the
  exact field set, maps, cohorts, role digests, and self-digest.
- [Risk] Full pytest remains slow. -> Mitigation: require RED regressions and
  focused owning tests first; run the repository's registered gate only after
  the narrow implementation is stable, without repeating infrastructure-only
  failures.

## Migration Plan

1. Commit and push the reviewed r6 planning boundary.
2. Add RED registration tests, implement the pure producer/standalone APIs, run
   focused tests and the registered test gate, then commit and push source.
3. Publish and review an exact content-blind r6 path/evidence preflight.
4. From pushed tracked-clean HEAD, invoke the driver once; it claims its receipt,
   loads each allowlisted canonical r5 input once, strict-parses it, renders and
   dual-validates one registration in memory, then exclusively publishes it.
5. Commit/push the registration and parent 6.2 update, leave 6.3 unchanged,
   then archive r6 without creating downstream authority.

Before driver process creation, rollback removes only uncommitted r6 planning
or preflight artifacts. After process creation, preserve its receipt and every
complete or partial output; parsing, validation, access, process, publication,
or accounting failure denies reopening/deletion/retry/replacement and requires
another reviewed successor.

## Open Questions

None.
