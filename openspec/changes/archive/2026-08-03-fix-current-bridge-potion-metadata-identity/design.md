## Context

The native adapter serializes potions with an enum-style stable `id` and an
upstream display `name`. `MetadataCatalog` indexes the Communication Mod export
only by metadata display name, then `MetadataCatalog.potion` requires the native
name to be present before constructing the typed `Potion`.

The r2 diagnostic first reached `ELIXIR_POTION` / `Elixir Potion`, while the
frozen metadata calls the potion `Elixir`. A read-only comparison of every
non-empty upstream potion found two additional differences:
`FAIRY_POTION` / `Fairy Potion` / `Fairy in a Bottle` and
`GAMBLERS_BREW` / `Gamblers Brew` / `Gambler's Brew`. The other 39 upstream
display names match metadata case-insensitively.

The bridge must remain a strict Communication Mod hydration boundary. The
repair cannot alter the native adapter, the consumed diagnostic, or Current's
decision logic, and it cannot infer arbitrary aliases.

## Goals / Non-Goals

**Goals:**

- Hydrate the three complete, statically proven potion identities.
- Expose the canonical metadata name to the typed `Potion` so existing potion
  effect metadata remains correct.
- Preserve native stable ID, source slot, price, input bytes, and all exact-name
  behavior.
- Reject every unregistered or inconsistent identity before Current executes.

**Non-Goals:**

- Broad suffix removal, punctuation normalization, fuzzy matching, or modded
  potion support.
- Rebuilding the native module or changing native serialization.
- Rerunning r2, preparing r3, accessing any seed, gameplay, policy tuning,
  fitting, OPE, reward work, formal RL, or training.

## Decisions

### Use a closed stable-ID mapping

Define one module-level mapping from each allowed native ID to the exact
expected native display name and canonical metadata name. The alias branch is
eligible only when the direct case-insensitive metadata lookup fails.

This uses all available identity evidence and keeps the accepted surface
auditable. Broad normalization was rejected because it can silently merge
future base-game or modded names. A display-name-only alias map was rejected
because it discards the stable native ID already present in every snapshot.

### Guard both sides of every mapping

For a mapped ID, require the incoming display name to case-insensitively equal
the registered native name and require the canonical metadata record to exist.
Otherwise preserve the existing `potion_metadata_missing` blocker. Do not use a
mapped ID as permission to accept a new upstream display name.

### Canonicalize only aliased hydrated names

Exact-name matches continue constructing `Potion` with the incoming name. An
alias match constructs it with the metadata record's canonical name while
retaining the native ID, source slot, and price. This supplies correct existing
effect metadata for Elixir and Fairy without changing the 40 compatible paths.
The source snapshot and candidate records remain untouched.

### Test the catalog boundary directly and through screen hydration

Parametrized red regressions cover all three valid aliases, wrong native name
for a mapped ID, unknown ID/name, missing canonical metadata, and exact-name
compatibility. At least one shop hydration regression proves source-slot and
price preservation through the screen boundary.

## Risks / Trade-offs

- [Upstream adds another naming difference] -> fail closed and require a new
  audited mapping entry with a regression.
- [A known upstream display name changes] -> fail closed instead of silently
  accepting drift.
- [Metadata omits or renames a canonical entry] -> fail closed before Current
  executes.
- [The mapping becomes duplicated elsewhere] -> keep it private to the bridge
  until another proven consumer requires a shared contract.

## Migration Plan

Land the closed mapping after red regressions, run focused and adjacent bridge
tests, then run the partitioned commit gate and strict OpenSpec validation.
Rollback removes the mapping, its one lookup branch, tests, report, and spec
delta. No data, model, native module, registration, or runtime migration exists.

## Open Questions

None. The complete base-game mismatch set and both identity sources are already
known for this bounded repair.
