## Context

The r3 inventory builder completed source discovery and atomically published
`seed_inventory.json`, but the artifact was 2,675,460,894 bytes and remained
unverified after the CLI stdout failure. The v3 schema stores every discovered
seed occurrence as a five-field provenance row. Historical reports repeat seed
values in nested summaries, registrations, and ledgers, so row multiplicity
dominates the artifact even though selection uses only the sorted unique seed
set.

The source registry already binds every accepted source path, exact byte
SHA-256, byte size, format, document count, and row count. Verification already
rescans those exact source bytes. Retaining all row mappings in the inventory is
therefore redundant for cohort selection and independent reconstruction.

## Goals / Non-Goals

**Goals:**

- Publish a compact v4 inventory whose size scales with source count and unique
  excluded seeds instead of total repeated seed occurrences.
- Preserve exact historical-source identity, role discovery, exclusion, cohort
  selection, authority, receipt, and completion-envelope semantics.
- Independently prove that producer and verifier derive the same source
  registry, row counts, excluded seeds, cohorts, and digests.
- Reject publication before rename when canonical inventory bytes exceed 64 MiB.

**Non-Goals:**

- Reading, converting, verifying, deleting, or registering the terminal r3
  inventory.
- Discovering real seeds or materializing an r4 cohort during implementation or
  source-only qualification.
- Changing source inclusion, JSON traversal, semantic roles, ascending
  selection, cohort sizes, request/authorization schemas, or one-shot behavior.
- Loading native modules, models, checkpoints, Torch, or environments; fitting,
  training, evaluation, gameplay, CommunicationMod, or downstream authority.

## Decisions

### Replace inline rows with source-bound aggregate evidence

Increment `SEED_INVENTORY_SCHEMA_VERSION` to
`noncombat-card-acceptance-empirical-successor-seed-inventory-v4`. Its field set
is the v3 set with `rows` removed. Retain `row_count`; each source registry entry
continues to carry `document_count`, `row_count`, file SHA-256, size, path, and
format. Retain the complete sorted unique `excluded_seeds` array and its digest.

The source registry digest commits the ordered set of exact input bytes and
their per-source counts. The inventory digest commits that registry, total row
count, excluded set, cohorts, authority evidence, and all role digests. The
independent verifier rescans the bound bytes and compares all of those values,
so omitting path-level row duplication does not permit the producer to omit or
substitute a seed undetected.

Alternative: gzip the existing 2.675 GB JSON. Rejected because verification
would still inflate and retain the full row array, canonical digest work would
remain proportional to repeated occurrences, and compressed size would hide
rather than remove the redundant representation.

Alternative: retain only a `rows_sha256`. Rejected because exact source byte
hashes plus independently reconstructed counts and excluded seeds already bind
the behavior that affects selection. A row digest would preserve expensive
sorting solely to attest data that no downstream consumer uses.

### Accumulate counts and unique seeds without a global row list

Introduce an iterator over seed occurrences with the existing deterministic
mapping-key and list-index traversal. For each registered source, increment its
row count and add seeds to one set; do not append occurrence mappings to a
repository-wide list. Return the source registry, total row count, and sorted
unique excluded seeds.

Keep the current row-producing helper as a compatibility wrapper only if tests
or public imports require it; inventory build and verification must use the
streaming accumulator. Per-document JSON parsing and existing Git blob identity
checks remain unchanged in this change.

Alternative: change JSON/Git input parsing at the same time. Rejected because
it would broaden the behavioral surface beyond the observed publication and
verification bottleneck.

### Enforce a pre-publication canonical byte ceiling

Set `INVENTORY_MAX_BYTES = 64 * 1024 * 1024`. After validating the compact
mapping, encode canonical inventory bytes once, reject a payload larger than the
ceiling, and only then create the staging directory and write/flush/rename the
artifact. The function must not leave output or staging paths after a synthetic
pre-publication size rejection.

The existing completion envelope continues to bind actual file size and
streamed file SHA-256 and remains capped at 2,048 bytes. No completion schema
change is needed.

Alternative: rely on expected compactness without a hard bound. Rejected
because historical report growth could silently recreate the same operational
problem under a different source mix.

### Preserve terminal evidence and require a later distinct r4

The r3 receipt and 2.675 GB output remain terminal and unverified. This repair
does not access them and grants no post-build verification or registration.
After source implementation, tests, strict OpenSpec validation, independent
review, commit, and push, a separately proposed r4 may bind the new source
identity and its own request/approval/authorization/output roots.

## Risks / Trade-offs

- [Risk] A downstream reader expects inline `rows`. -> Mitigation: repository
  search and focused tests must prove only the inventory module/tests consume
  the unregistered v3 shape; v4 rejects unknown `rows` explicitly.
- [Risk] Aggregate evidence hides producer omission. -> Mitigation: the
  independent verifier rescans exact source bytes and compares ordered source
  identities, per-source and total counts, complete excluded seeds, and cohorts.
- [Risk] The compact artifact still exceeds 64 MiB. -> Mitigation: fail before
  publication; do not raise the bound or retry the same future identity.
- [Risk] Iterator traversal changes semantic role assignment. -> Mitigation:
  retain traversal order and role logic and add equivalence tests against the
  current row helper over nested mappings, lists, and cohort contexts.
- [Risk] Source parsing remains memory-heavy. -> Mitigation: keep that separate;
  this change removes the observed multi-gigabyte global row/canonical payload
  amplification without combining an unrelated parser rewrite.

## Migration Plan

1. Add RED tests for v4 exact fields, repeated-row compaction, traversal
   equivalence, independent reconstruction, and the 64 MiB publication gate.
2. Implement the occurrence iterator, aggregate registry builder, v4
   validation, compact build/verify comparison, and bounded publication.
3. Run focused inventory tests, owning successor tests, compile checks, strict
   OpenSpec validation, and one configured commit gate; independently review
   source/spec/authority behavior and resolve actionable findings.
4. Commit and push the source-only repair, sync/archive this change, and leave
   parent task 6.2 unchecked.
5. Consider a distinct r4 proposal bound to the pushed repair. No r4 authority
   or execution is created by this migration.

Rollback before a future started receipt reverts only this source-only repair.
No consumed evidence or empirical identity is modified.

## Open Questions

None.
