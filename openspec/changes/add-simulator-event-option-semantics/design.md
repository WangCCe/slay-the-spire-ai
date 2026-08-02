## Context

The frozen Current-policy bridge registration binds an immutable 320 MB
demonstration file, four exact row hashes, the adapter and simulator provenance,
the bridge implementation commit and source digest, and all execution settings.
Its route, card-reward, and shop rows pass; the `Liars Game` event row fails
before Current executes because the adapter snapshot has only event identity and
legal action indices.

The audited `sts_lightspeed` checkout has no standalone event-semantics API.
For `Event::THE_SSSSSERPENT`, however, four source surfaces agree: the stable
event id is `Liars Game`, legal indices are `0` and `1`, the console labels are
`Agree` and `Disagree`, and `chooseEventOption` implements accept-gold-and-Doubt
versus no-op departure. This is sufficient for one narrow source-bound contract,
not for a claim that every simulator event is semantically covered.

## Goals / Non-Goals

**Goals:**

- Resolve exact `Liars Game` option semantics from immutable snapshot fields and
  candidates without editing the frozen evidence.
- Keep the resolver in the offline adapter layer and make unsupported event
  identities, phases, candidate sets, or provenance fail closed.
- Preserve input snapshot and candidate bytes while invoking the exact Current
  policy path.
- Re-evaluate the same four Stage 1 rows under a successor registration that
  proves all decision/evaluation settings except implementation and semantics
  identity are unchanged.
- Conditionally run the already-declared reused-seed Stage 2 compatibility check
  only after a fully passing Stage 1 result.

**Non-Goals:**

- A complete semantic catalogue for all `sts_lightspeed` events.
- Modifying native simulator behavior, Current event policy, live gameplay, or
  Communication Mod configuration.
- Fresh simulator evidence, gameplay batches, model fitting, reward tuning,
  formal RL training, baseline-floor claims, or promotion.
- Rewriting the 320 MB frozen demonstrations or presenting derived rows as the
  original source evidence.

## Decisions

### Add one versioned Python adapter-layer resolver

`noncombat_simulator_adapter.py` will expose a pure resolver whose input is a
validated event snapshot, legal candidates, and a registered simulator source
identity. Version 1 supports only `event_id == "Liars Game"`, `event_data == 0`,
and the exact candidate indices `{0, 1}`. It returns ordered semantic records:
`Agree` with the ascension-dependent gold/Doubt effect and `Disagree` with the
no-op effect.

The source contract will record the upstream enum, event id, legal-index source,
display-label source, execution source, simulator commit, and simulator source
digest. Resolution rejects identity drift before returning semantics.

Alternative considered: duplicate the entire console event switch in the C++
adapter. Rejected because it creates broad unverified coverage and still cannot
retroactively enrich the immutable frozen snapshot.

Alternative considered: use `option 0` and `option 1`. Rejected because those
labels are not semantic and Current intentionally reads option text.

### Enrich a deep copy at the bridge boundary

The bridge will first validate and hash the original snapshot and candidates,
then ask the adapter resolver for semantics only when an event snapshot lacks
`option_semantics`. The returned semantics are inserted into a deep copy passed
to hydration. Existing valid inline semantics remain authoritative; the
resolver will not overwrite them. Resolver absence or failure is reported as a
field-specific structural blocker.

Alternative considered: change `OptimizedAgent` to choose these rows by index.
Rejected because that changes production policy behavior and weakens the exact
Current-path claim.

### Use a successor registration, not an in-place recomputation claim

The original registration cannot be strictly recomputed by changed code because
it binds implementation commit and source digest. A v2 successor registration
will bind the predecessor registration file/hash, predecessor canonical output
manifest/hash, semantic contract identity, new implementation identity, and new
output directory. Before row execution it will compare a fixed immutable field
set: frozen demonstration binding, all Stage 1 rows and hashes, category
minimums, replay count, Current configuration, authority values, metadata,
runtime, prior-seed evidence, and Stage 2 seeds/limits. Only implementation,
semantic-contract, predecessor, schema, and output identities may differ.

Alternative considered: edit the original registration or report directory.
Rejected because it would destroy the valid negative result and its audit trail.

### Keep Stage 2 conditional and single-use

Stage 1 recomputes only the same four frozen rows. If and only if its verdict is
`frozen_bridge_structurally_compatible`, the change may execute one compatibility
run using the already-registered seeds `2000..2003`. Stage 2 remains structural:
it checks legal deterministic own-trajectory execution and cannot update policy
quality or RL readiness.

## Risks / Trade-offs

- [The narrow resolver is mistaken for full event support] -> Encode supported
  event ids and phases explicitly, report coverage, and fail every other absent
  semantic state closed.
- [Upstream dirty-source provenance is ambiguous] -> Match both the registered
  simulator parent commit and full compiled-source SHA-256, not commit alone.
- [Derived semantics mutate frozen evidence] -> Deep-copy before enrichment and
  compare canonical source hashes before and after every replay.
- [A successor silently changes the cohort] -> Validate immutable registration
  fields before evaluating any row and publish their comparison in the report.
- [A Stage 1 pass is interpreted as policy quality] -> Keep all authority flags
  false and preserve the separate baseline-floor gate.

## Migration Plan

1. Add red regressions for exact source identity, labels, dynamic text, candidate
   coverage, unsupported states, non-mutation, and successor comparison.
2. Implement the adapter resolver and bridge enrichment without native or
   gameplay changes.
3. Create and hash the successor registration; run focused tests and the commit
   gate.
4. Recompute the four frozen Stage 1 rows into a new output directory.
5. If Stage 1 passes, execute the one authorized reused-seed Stage 2 check;
   otherwise stop and preserve the blocker.
6. Sync and archive the change after reports and project direction are updated.

Rollback deletes the resolver, bridge integration, successor registration,
tests, and successor reports. The predecessor registration and negative report
remain untouched.

## Open Questions

None for the bounded `Liars Game` contract. Any additional event requires a
separate evidence-backed coverage extension rather than implicit fallback.
