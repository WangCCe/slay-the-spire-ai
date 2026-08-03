## Context

`MetadataCatalog.card()` resolves card name, type, rarity, and cost from the
registered StSExporter `items.json`. The current cost parser maps `X` to `-1`,
maps literal `UNPLAYABLE` or `-` to SpireComm `-2`, and parses integers. The
frozen exporter instead represents 20 native unplayable card identities with
an empty cost and a leading `Unplayable.` description, so all 20 currently fail
with `card_metadata_cost_invalid`.

The terminal Current baseline study encountered this boundary through an
`INJURY` added to the run deck. That study and its canary are consumed and
cannot be retried. This change is an offline implementation repair for future
bridge use only.

## Goals / Non-Goals

**Goals:**

- Hydrate exactly the audited 20 stable native IDs from their exact empty-cost,
  explicitly unplayable metadata representation to SpireComm cost `-2`.
- Preserve integer and `X` cost behavior and source non-mutation.
- Fail closed on every identity or metadata drift and on every other empty-cost
  card, including the three Wish option identities.
- Cover the complete positive table, reverse boundaries, upgraded source
  records, and production-shaped `Injury` deck hydration with red-first tests.

**Non-Goals:**

- No generic empty-cost, type-based, description-only, fuzzy-name, or
  punctuation normalization.
- No native adapter or simulator source change, native loading, environment,
  seed, gameplay, Current policy, reward, model, OPE, or training work.
- No retry, replacement, continuation, or reinterpretation of the terminal
  baseline study.

## Decisions

### Use one closed stable-ID table

Add one module-level mapping keyed by the exact 20 native enum-style IDs. Each
entry binds expected native display name and metadata type. A listed ID takes
the closed validation path before generic cost parsing, so a changed name,
type, cost, or description cannot bypass the contract through a newly valid
generic value.

The closed IDs are the 13 audited Curses, four Status cards, and three
cross-color unplayable Skills. The mapping includes all audited identities
rather than only `INJURY`, preventing the same known representation defect from
moving to another reachable Curse or Prismatic Shard reward.

Alternative: map every empty cost to `-2`. Rejected because six Wish option
records have empty cost without declaring themselves unplayable.

Alternative: map empty cost by `CURSE` or `STATUS` type. Rejected because
`PRIDE` and `SLIMED` are numeric-cost counterexamples and because it would omit
the audited unplayable Skills.

Alternative: trust only the leading description text. Rejected because display
text alone is not a stable identity boundary and could authorize an unknown
future card.

### Validate exact metadata shape before assigning cost

For a listed ID, require the exact expected source name, the matching metadata
name already selected by the existing catalog, the expected metadata type,
`cost == ""` after exact string retrieval, and a description beginning exactly
with `Unplayable.`. Only then assign cost `-2`. Rarity, upgrades, misc, price,
slot, color disambiguation, and all existing typed construction continue
through the current path.

The three upgradable unplayable Skills use their base native name plus the
existing `upgrade_count`; no `+`-name inference or second metadata lookup is
added.

Alternative: treat a future `UNPLAYABLE` value as equivalent for listed IDs.
Rejected for this source-bound repair because the audited metadata hash and
empty representation are part of the evidence. Future metadata drift should
fail closed and receive a separate review.

### Use SpireComm unplayable cost `-2`

The bridge hydrates Communication Mod-compatible `Card` objects. Its existing
literal unplayable path already uses `-2`, matching the policy-side
representation. The simulator's internal `-3` distinction for Curses is not a
Communication Mod card-cost contract and must not leak into the bridge.

### Keep reverse regressions independent of the mapping

Tests define the expected 20-entry table explicitly, then exercise each entry
through `MetadataCatalog.card()`. Separate tests cover wrong source name,
changed metadata type, non-empty cost, missing `Unplayable.`, an unknown ID,
the three Wish IDs, numeric Status/Curse controls, `X`, upgrades, and source
non-mutation. A production-shaped `hydrate_game()` test places `INJURY` in the
deck at a target decision.

## Risks / Trade-offs

- [Risk] The English description field changes while semantics remain valid.
  -> Mitigation: fail closed because this repair is bound to the audited
  exporter identity; do not broaden matching silently.
- [Risk] A listed ID with changed metadata could use the generic path.
  -> Mitigation: dispatch listed IDs through closed validation before generic
  cost parsing.
- [Risk] The constant duplicates upstream facts. -> Mitigation: keep one small
  table and an exhaustive expected-table regression; avoid a generic parser or
  new data model.
- [Risk] The repair is mistaken for permission to rerun the study. ->
  Mitigation: keep all authority false in proposal, spec, tests, closeout, and
  project direction; execute no native or empirical command.

## Migration Plan

1. Add exhaustive red regressions and record the expected failure class.
2. Implement the closed table and minimal cost-resolution branch.
3. Run focused bridge, study-verifier, adapter, and metadata tests; run
   `py_compile`, strict OpenSpec validation, and the registered commit gate.
4. Update project direction only to record the offline repair. Sync and archive
   this change, then commit and push one cohesive compatibility fix.

Rollback removes the table, branch, regressions, synced requirement, and
repair closeout. It preserves the cost-domain audit and every terminal study
artifact byte-for-byte.

## Open Questions

None. Any request to broaden the identity set, accept another cost
representation, load native code, access a seed, or prepare empirical evidence
requires a separate proposal.
