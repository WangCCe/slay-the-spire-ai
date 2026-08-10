## Why

The terminal r3 build published a 2,675,460,894-byte inventory because it
inlined every repeated provenance row even though source bytes, per-source row
counts, and the unique excluded-seed set already determine cohort selection.
The repaired CLI no longer writes that payload to stdout, but a fresh r4 would
still duplicate the oversized JSON and require the verifier to parse and copy it.

## What Changes

- Replace the unverified v3 inventory shape with a v4 compact shape that omits
  inline provenance `rows` and binds exact source bytes, per-source document and
  row counts, total row count, sorted unique excluded seeds, and their canonical
  digests.
- Build the excluded-seed set and row counts incrementally while parsing each
  registered source, without retaining one global list of provenance row
  mappings or deep-copying it into publication.
- Make verification independently rescan the closed source registry and compare
  source identities, counts, excluded seeds, cohorts, role digests, and the
  whole inventory digest without materializing a second provenance-row list.
- Add a fixed 64 MiB canonical inventory ceiling checked before publication and
  carried in the bounded CLI completion envelope through its existing file size
  field. Exceeding the ceiling fails closed rather than publishing an oversized
  artifact.
- Keep historical source discovery, role classification, ascending
  `512/128/512` selection, request/authorization/receipt semantics, generated
  root exclusions, and direct/CLI API authority unchanged.
- Preserve the r3 2.675 GB output and receipt as terminal unverified evidence;
  this change never reads, converts, deletes, verifies, or registers them.
- Success is synthetic and fixture-backed proof that repeated-row volume no
  longer controls artifact size, compact build/verify reconstruct identically,
  and all existing authority and exclusion regressions pass. No real seed
  discovery or cohort materialization is part of this repair.
- Native/model loading, environments, fitting, training, evaluation, gameplay,
  CommunicationMod, qualification, promotion, r4 execution, and parent task 6.2
  remain out of scope.
- Rollback before any future r4 starts is removal of this additive source change
  and its tests. No consumed artifact or empirical identity is modified.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Replace inline provenance
  rows with independently reconstructed compact inventory evidence and enforce
  a fixed canonical inventory byte ceiling before publication.

## Impact

The implementation changes only the standard-library card-acceptance seed
inventory module, its focused tests, and the corresponding specification. It
adds no dependency and changes no runtime policy, simulator, model/checkpoint,
CommunicationMod configuration, or gameplay behavior.
