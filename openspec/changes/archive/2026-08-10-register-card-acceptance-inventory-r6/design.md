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
  canonical-byte-compares all six JSON evidence inputs, accounts for one open
  each, and publishes
  exclusively without directory discovery.
- Require exact r5 inventory, build receipt, verification receipt/completion,
  hash-pinned historical standalone evidence, and a fresh exact five-field
  standard-library reconstruction before the builder returns a registration.
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
one-shot lifecycle. Its exact CLI supplies a separately reviewed expected
request SHA-256 and receipt path. It exclusively publishes the immutable
invocation receipt before reading or resolving the request path. It then
accepts one exact request-like allowlist mapping, rejects
unknown/additional/duplicate paths and symlinks, and never calls directory or
glob enumeration. The first driver process invocation consumes r6. The
receipt's expected request digest transitively binds the preflight, all six
input identities, output path, source commits, and downstream denial before
the request control input is opened. It then opens the request and every
evidence input exactly once, verifies stable regular
file identity and registered hash/size, strict-parses all six canonical JSON
inputs, reruns the independent
standard-library inventory reconstruction in-process, and passes that fresh
exact five-field result with the four authority/inventory mappings to the
producer. The historical standalone wrapper remains an exact hash-pinned,
reviewed prerequisite but does not self-authorize registration construction.

The receipt writer keeps its exclusive `x+b` handle open, fsyncs and reads back
the canonical bytes through that same handle. Receipt, request validation,
evidence access, validation, and publication are one private lifecycle with
function-local state; no independently callable start or publication stage
exists. Production `main()` derives isolation from `sys.flags.isolated` and the
trusted root from the driver module, while test-only injection remains behind
the private complete-lifecycle helper rather than exported publication APIs.

Focused tests monkeypatch directory enumeration to fail if called, account for
one request open and one open per evidence input, and cover self-digested
request substitution, malformed request, wrong root, missing isolated mode,
symlink/alias/additional-path rejection, existing or partial receipt, exclusive
output collision, short write, flush failure, and fsync failure. Any process
creation, receipt, parsing, validation, access, publication, or accounting
failure is terminal for r6 even when no evidence or output was opened.
One synthetic end-to-end test uses the real inventory builder, fresh standalone
inventory reconstruction, producer registration builder/validator, final
independent registration validator, receipt lifecycle, and exclusive output;
stubbed driver tests remain only for isolated failure injection.

The transport is frozen as one canonical request file with schema
`noncombat-card-acceptance-empirical-successor-registration-request-v1`.
Its exact fields are `schema_version`, `request_id`, `registration_id`,
`implementation_source_commit`, `inventory_source_commit`,
`preflight_sha256`, `input_bindings`, `receipt_path`, `output_path`,
`registration_schema_version`, `downstream_authority`, and `request_sha256`.
`input_bindings` has exactly six named entries, each containing absolute
canonical path, SHA-256, size, and `content_kind`. All six entries use
`canonical_json`, including the canonical JSON verification review. The
downstream map is exact and all false;
`request_sha256` covers every other field with trailing-newline canonical JSON.

The only process shape is the registered Windows interpreter with `-I`, the
fixed driver script, subcommand `publish-registration`, fixed repo root,
`--request`, `--expected-request-sha256`, and `--receipt-path`. The request is a
control input, not one of the six evidence inputs, and is committed/pushed
before launch. The driver never opens the preflight itself. Before request
access, the immutable receipt binds the exact command, receipt path,
registration identity/schema, and expected request digest; that digest
transitively binds the preflight digest, all six input identities, output path,
both source commits, and downstream denial. After receipt publication, the
driver requires the request self-digest and bytes to equal the separately
reviewed expected digest.

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
   loads each allowlisted r5 input once, strict-parses all six JSON inputs,
   renders and dual-validates one
   registration in memory, then exclusively publishes it.
5. Commit/push the registration and parent 6.2 update, leave 6.3 unchanged,
   then archive r6 without creating downstream authority.

Before driver process creation, rollback removes only uncommitted r6 planning
or preflight artifacts. After process creation, preserve its receipt and every
complete or partial output; parsing, validation, access, process, publication,
or accounting failure denies reopening/deletion/retry/replacement and requires
another reviewed successor.

## Open Questions

None.
