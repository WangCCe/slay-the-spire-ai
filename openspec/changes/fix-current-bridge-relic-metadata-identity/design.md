## Context

`MetadataCatalog.relic` currently uses the upstream display name only to prove
that a record exists in the Communication Mod metadata index, then constructs a
typed `Relic` from the native stable ID and display name. The complete static
surface audit compared the clean upstream `relicEnumNames[]` and `relicNames[]`
arrays at simulator commit `7476a81954020087da31d41d16fddf475746ec2d`
with the same frozen metadata consumed by r2.

Of 180 non-invalid upstream relics, 163 names match directly. Fifteen valid
identities differ only in punctuation, possessives, spacing, or the canonical
singular `Philosopher's Stone`. `CIRCLET` and `RED_CIRCLET` are exact upstream
fallbacks used when rare or boss relic pools are empty, but the exporter omits
both. Separately, every one of the 370 upstream base card display names exists
in metadata, so card identity needs no repair.

## Goals / Non-Goals

**Goals:**

- Hydrate all 15 proven relic aliases with canonical Communication Mod names.
- Hydrate the two exact simulator fallback relics despite their audited metadata
  absence.
- Preserve stable native ID, source slot, counter, price, source bytes, and all
  163 direct-name behaviors.
- Reject any name drift, unknown ID, absent canonical alias target, or new
  metadata exemption before Current executes.

**Non-Goals:**

- Generic punctuation removal, possessive repair, compact-ID matching, fuzzy
  matching, modded relic support, or card changes.
- Adding synthetic metadata records for Circlet variants.
- Changing the native adapter, simulator, consumed diagnostics, Current policy,
  actions, models, rewards, evaluation, or training.
- Rerunning a diagnostic, preparing r3, accessing a seed, or launching gameplay.

## Decisions

### Use one closed identity table

Define one module-level mapping from each of the 17 stable native IDs to its
exact expected upstream display name and either its canonical metadata name or
`None` for an audited exemption. The stable ID is the primary selector, but it
never authorizes a changed native name.

This keeps all exceptions reviewable in one place. A generic name normalizer
was rejected because the canonical differences are not mechanically uniform
and could merge unrelated future or modded relics.

### Validate mapped IDs before direct lookup

If a stable ID is in the table, first require the exact expected upstream name
case-insensitively. This prevents a mapped ID carrying another valid metadata
name from bypassing the contract through the direct-name path.

For 15 aliases, require the canonical metadata entry and hydrate with its exact
metadata name. For `CIRCLET` and `RED_CIRCLET`, require their expected native
name and allow only those IDs to proceed when the direct metadata entry is
absent. If a future exporter adds those exact entries, use its exact casing.

### Preserve the existing direct path

IDs outside the table continue to require the incoming display name in the
case-insensitive metadata index and retain the incoming hydrated name. This
avoids behavior changes for all 163 direct matches.

### Exercise catalog and screen boundaries

Parametrized tests cover every alias and exemption, exact direct matching,
mapped-ID direct-name bypass attempts, unknown IDs, missing canonical targets,
wrong exemption names, and shop hydration with source-slot/price/non-mutation
checks.

## Risks / Trade-offs

- [Another upstream relic is added or renamed] -> fail closed and require a
  new source-bound audit and regression.
- [Exporter later adds Circlet metadata] -> accept only the exact audited ID and
  name and use the metadata spelling without expanding exemptions.
- [Canonicalizing alias names changes Current observations] -> this is the
  intended Communication Mod-compatible representation; stable IDs and source
  records remain unchanged and regressions cover both.
- [The exception list becomes maintenance burden] -> retain the complete static
  audit identity and avoid sharing the table until another proven consumer
  needs it.

## Migration Plan

Commit and push the validated planning artifacts, add red regressions and the
audit report, implement the single table and relic lookup branch, then run
focused/adjacent tests, `py_compile`, the partitioned commit gate, and strict
OpenSpec validation. Rollback removes that table, branch, tests, report, and
spec delta. No runtime, data, model, registration, or native migration exists.

## Open Questions

None. The full upstream and metadata identity sets and both fallback call sites
are statically proven for this bounded change.
