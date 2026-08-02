## Context

The current offline bridge has a version-1 event resolver that supports only
`Liars Game`. It emits `choice_index` equal to the simulator `GameAction` index,
hydrates that value into `EventOption.choice_index`, and later matches the
Current `ChooseAction.choice_index` directly to candidate `raw.idx1`. Current,
however, chooses a zero-based position in the visible enabled option list. The
integers differ whenever simulator legal indices are sparse: Cleric Leave can be
simulator index 2 at Current position 0, and Cursed Tome phases expose indices 2,
3, or 4 as a single visible position 0.

The immutable total observation contract provides exact identities and labels
for 25 events and 47 Current aliases. It defines 23 static rules, five explicit
Cursed Tome phases, Mindbloom hydration normalization, and an N'loth dynamic
schema. `sts_lightspeed` stores the two N'loth offers in
`GameContext.info.relicIdx0/relicIdx1`; the current native snapshot exports the
player relic list but not those indices. The implementation must preserve
historical v2 evidence while ensuring newly built modules expose sufficient v3
context.

This is offline structural tooling. Communication Mod gameplay does not import
the native adapter or bridge, and this change must not alter `OptimizedAgent`.

## Goals / Non-Goals

**Goals:**

- Export exact N'loth offered-relic records from the native source state.
- Resolve every contract event from hash-checked canonical rules and exact
  simulator provenance, with named dynamic handling and no generic fallback.
- Carry Current position and simulator choice index as distinct coordinates
  from resolution through hydration and action mapping.
- Preserve source snapshot, candidates, provenance, and contract bytes.
- Keep historical v2 snapshot validation available for immutable evidence while
  requiring v3 context for N'loth resolution.
- Prove the implementation through synthetic/frozen focused regressions and the
  repository commit gate without running a native cohort.

**Non-Goals:**

- Reconstruct complete UI prose or event effects not read by Current.
- Change Current event policy, candidate legality, upstream simulator behavior,
  Communication Mod, reward, model, training, or promotion logic.
- Re-run consumed seeds `2000..2003`, create fresh simulator evidence, or claim
  bridge compatibility from unit tests.
- Modify the external `sts_lightspeed` checkout or rewrite historical reports.

## Decisions

### Version new native output while retaining historical readers

The C++ adapter and `ADAPTER_API_VERSION` advance to
`sts-lightspeed-noncombat-adapter-v3`. `load_native_module` requires exactly v3
for a newly loaded module. Python snapshot and provenance validators retain an
explicit allow-list for historical v2 (and existing provenance v1) records so
old registrations remain inspectable; they do not silently upgrade their
identity.

For an N'loth event, `appendDecisionContext` emits exactly two
`offered_relics` records. Each contains `simulator_choice_index`, `relic_slot`,
`relic_id`, and `relic_name`, sourced directly from `relicIdx0/relicIdx1` and
the corresponding `gc_.relics.relics` entries. Other events do not receive this
field. The resolver independently checks count, distinct slots, bounds, and
slot/id/name equality against `state.relics`.

Alternative considered: infer offers in Python from relic order or candidate
labels. Rejected because the offer slots are shuffled simulator state and cannot
be reconstructed from either source.

Alternative considered: retain API v2. Rejected because the native snapshot
shape gains decision-relevant data; the build interface should identify that
change even though historical readers remain explicit.

### Consume the canonical contract artifact, not a duplicate registry

The event resolver loads
`reports/noncombat_event_option_observation_contract_20260802/contract.json`
from a fixed repository-relative path on each resolution, rejects duplicate
JSON keys, verifies its registered SHA-256 and schema/count invariants, and then
selects exactly one rule by upstream event id and event name. The resolver
identity records the contract path/hash, simulator source identity, schema, and
coverage counts. Contract bytes are checked before snapshot resolution so a
cached prior rule cannot mask drift.

The resolver implements the contract's small runtime projection locally:
static index labels, the Cursed Tome phase table, N'loth offered-relic labels,
and Current event-id normalization. It emits an observation containing
`current_event_id` and ordered rows with `current_position`,
`simulator_choice_index`, `label`, and `text`. `text` equals the non-empty label
because the contract intentionally covers Current-observable labels rather than
complete UI prose; Current prefers `label` whenever it is present.

Alternative considered: import the audit validator's global registry. Rejected
because runtime resolution should consume the published contract bytes that the
proposal names, not an independent in-memory table with a separate drift path.

Alternative considered: parse `ConsoleSimulator` output at runtime. Rejected
because it is not an API, does not solve dynamic state binding, and would weaken
the reviewed contract boundary.

### Normalize every event observation to two coordinates

Resolved semantics use a version-2 record:

```
{
  "choice_index": <current_position>,
  "current_position": <current_position>,
  "simulator_choice_index": <raw.idx1>,
  "label": <contract label>,
  "text": <contract label>
}
```

`choice_index` remains as the Communication Mod-compatible hydration field but
must equal `current_position`. Positions must be exactly `0..n-1`; simulator
indices must be strictly increasing, unique, and exactly equal to the legal
candidate set. The bridge hydrates `EventOption.choice_index` from the Current
position. After Current returns `ChooseAction(position)`, the bridge selects the
observation row at that position and uniquely matches the candidate using its
simulator index.

Alternative considered: attach simulator indices to the Current action object
with a monkey patch. Rejected because the policy returns a generic
`ChooseAction` and the validated observation already provides the stable
mapping without changing production classes.

### Bound legacy inline semantics to the only unambiguous case

Inline version-2 rows with both coordinates are validated identically to
resolver output and remain authoritative. Legacy inline rows containing only
`choice_index`, `label`, and `text` are accepted only when candidate simulator
indices are exactly contiguous `0..n-1` and legacy choice indices match that
same sequence. The bridge normalizes them in its deep copy before hydration.
Sparse, reordered, duplicate, partial, or extra legacy rows fail closed.

Alternative considered: interpret a legacy `choice_index` as either coordinate
based on which candidate happens to match. Rejected because equal-looking rows
can silently select the wrong simulator action.

### Keep implementation evidence separate from compatibility evidence

This change runs focused tests, strict OpenSpec validation, and the repository
commit gate. It may use existing frozen JSON rows as test fixtures but does not
load a native module, construct an environment, run a seed, or publish a bridge
successor report. Project direction records the implementation as complete but
leaves compatibility and baseline-floor readiness blocked. A later change must
bind the new module, resolver, bridge, contract, and cohort before execution.

## Risks / Trade-offs

- [The contract file drifts after import] -> Hash and parse the exact file on
  every resolution; do not retain a rule cache across calls.
- [Historical v2 acceptance becomes an implicit upgrade] -> Preserve the
  snapshot's declared API version and require N'loth-specific v3 context rather
  than inserting defaults.
- [N'loth slots point at changed relic records] -> Validate slot, id, name,
  uniqueness, and candidate indices together before producing labels.
- [Current position is again confused with simulator index] -> Require both
  fields in normalized rows and use only position for hydration and only the
  mapped simulator index for candidate lookup.
- [Incomplete UI text changes Current behavior] -> Set a non-empty label and
  matching text, test that Current label selection is unchanged, and make no
  claim about full prose.
- [Unit tests are mistaken for native compatibility] -> Keep every execution
  authority false and require a later preregistered cohort.

## Migration Plan

1. Add red Python/C++ source-surface regressions for API v3, N'loth context,
   total resolution, dynamic states, identity normalization, and sparse mapping.
2. Implement the native snapshot extension and Python validation compatibility.
3. Replace the narrow resolver and normalize bridge enrichment/hydration/action
   mapping without changing Current policy.
4. Run focused tests, strict OpenSpec validation, and the repository commit gate.
5. Update project direction, sync specs, archive, commit, and push without native
   execution.

Rollback reverts the v3 adapter source, resolver, bridge integration, focused
tests, and this change. The v2 native module and every historical registration,
report, and total-contract artifact remain untouched.

## Open Questions

None. Any compatibility execution remains a separate preregistration decision.
