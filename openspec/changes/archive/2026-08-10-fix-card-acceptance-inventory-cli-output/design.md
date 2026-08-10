## Context

r3 proved that the inventory operation can finish validation and atomic
publication while the CLI still fails afterward. `main()` currently serializes
the full mapping returned by `build_inventory` or `verify_inventory` to stdout;
the r3 mapping was 2.675 GB. The durable file is already the canonical carrier
for that data, so duplicating it on stdout adds no evidence and makes process
completion depend on pipe and shell behavior.

The repair must not alter the frozen `check-dispatch` bytes, direct Python API
return values, inventory schema/content, receipt timing, historical scan,
cohort selection, verifier reconstruction, or any downstream authority. r3 is
terminal and cannot be used to test the repair by retry or verification.

## Goals / Non-Goals

**Goals:**

- Make `build-inventory` and `verify-inventory` CLI output constant-size with
  respect to inventory rows, exclusions, and cohorts.
- Emit enough canonical identity to let an outer observer confirm which closed
  output and receipt completed without reading the inventory from stdout.
- Fail closed if the output, receipt, request, or returned artifact identities
  disagree after an operation returns.
- Preserve exact `check-dispatch` output and all direct API behavior.

**Non-Goals:**

- Do not verify, register, delete, move, or reuse r3 output.
- Do not optimize the inventory's 2.675 GB durable representation or historical
  scan performance in this change.
- Do not create r4 authority, load native/model/runtime state, construct an
  environment, train, evaluate, qualify, promote, or launch gameplay.

## Decisions

### 1. Emit a canonical completion envelope, not a truncated artifact

`main()` will keep returning the full artifact from the direct operation, but
for `build-inventory` and `verify-inventory` it will pass that mapping to a new
completion builder and serialize only the builder result. The envelope has a
frozen schema version
`noncombat-card-acceptance-empirical-successor-inventory-cli-completion-v1`
and exactly these fourteen fields: `schema_version`, `operation`, `status`,
`request_sha256`, `output_path`, `inventory_path`, `inventory_size_bytes`,
`inventory_file_sha256`, `inventory_sha256`,
`inventory_launch_observation_sha256`,
`operation_launch_observation_sha256`, `receipt_path`, `receipt_sha256`, and
`completion_sha256`. The only operation/status pairs are
`build-inventory`/`published` and `verify-inventory`/`verified`. The inventory
launch is the build launch bound by the artifact and receipt; the operation
launch is the current build or verification authority. They are equal for a
build and may differ for a separately authorized verification.

`completion_sha256` is the production canonical SHA-256 of the exact other
thirteen fields, excluding `completion_sha256` itself. Paths are resolved absolute
paths rendered with forward slashes. The encoded envelope includes the
production canonical trailing newline.

Truncating or streaming the full artifact was rejected. Truncation is not a
valid JSON identity, while streaming still duplicates multi-gigabyte durable
state and leaves the observer coupled to inventory size.

### 2. Revalidate small durable identities after the operation returns

The builder will require a closed output directory containing only
`seed_inventory.json`, no staging root, a regular non-symlink inventory file,
and a canonical regular non-symlink started receipt. It will validate the
receipt's stable file identity, exact field set, and self-digest, then require its request,
authorization, launch, and source identities to match the request and returned
artifact. It will open the inventory once, stream it through SHA-256 with a
fixed-size buffer, and compare pre-read file identity, post-read file identity,
and final path identity before publishing completion. The envelope binds both
that `inventory_file_sha256` and the artifact's already validated semantic
`inventory_sha256`. For verification, receipt launch validation uses the
artifact's inventory/build launch while the envelope separately binds the fresh
operation launch that authorized verification.

Relying only on the returned mapping was rejected because an observer could
receive a completion for a substituted path or receipt after unexpected drift.
Re-parsing or reconstructing the large file was rejected because independent
semantic verification belongs to `verify-inventory`; a single constant-memory
byte hash is the minimal sufficient completion identity. The hash does not
claim registration or semantic validity.

### 3. Freeze a hard encoded-size limit

The canonical encoded envelope must not exceed 2,048 bytes. The builder checks
this before stdout write and fails closed if future fields or path growth cross
the bound. Tests will use an operation result containing a large ignored value
to prove stdout size depends only on the selected identity fields.

### 4. Preserve dispatch output as a separate branch

The `check-dispatch` branch and `canonical_json_bytes(artifact)` call remain
unchanged. Its exact bytes are already bound into predecessor evidence and are
small. Only the common build/verify branch changes to emit the envelope.

## Risks / Trade-offs

- [A completion envelope could hide a malformed durable artifact] -> The build
  validates before publication and the verifier independently reconstructs the
  file; the envelope stream-binds observed bytes but claims only operation
  completion and identity, never registration or policy validity.
- [The large file changes during completion hashing] -> Compare regular-file
  identity and size before/after the stream and against the final path stat;
  fail closed without stdout on any mismatch.
- [Receipt revalidation could introduce a new post-publication failure] -> Use
  the same stable regular-file checks, canonical primitives, and exact known
  receipt schema, cover success and tamper cases, and keep failure
  terminal/fail-closed.
- [Future long paths could exceed the bound] -> Enforce the explicit 2,048-byte
  maximum and fail before writing any partial completion output.
- [Changing stdout could break callers that consumed full artifacts] -> The
  only registered CLI consumers are observers; direct Python APIs retain full
  mappings, and the durable file remains the full canonical source.

## Migration Plan

1. Add RED tests for bounded build/verify output, exact completion fields,
   tampered receipt/output rejection, direct API preservation, and unchanged
   dispatch bytes.
2. Implement the completion schema, receipt/output validation, single streaming
   byte hash, and bounded serialization path without touching inventory
   construction.
3. Run focused CLI nodes, the complete owning pytest file, compile/import
   checks, strict OpenSpec, and independent review.
4. Commit and push the repair as a source boundary. Only a later distinct
   proposal may preregister r4.

Rollback reverts this code/test/spec change only. The r3 receipt, terminal
reports, postmortem, and unverified local output remain immutable.

## Open Questions

None.
