## Why

The source-bound Current bridge now passes its frozen four-row structural gate,
but its single authorized reused-seed check failed closed on `The Cleric`
because the resolver covers only `Liars Game`. Adding events one at a time from
that consumed trajectory would overfit the compatibility cohort and still leave
the full Current event surface unknown.

## What Changes

- Add a read-only, hash-bound static audit of the exact event branches and
  option-label semantics read by Current's `_choose_event_option` path.
- Bind every Current-relevant canonical event to the registered
  `sts_lightspeed` event identity, legal-action, display-label, and execution
  source cases, including phase-dependent or conditional gaps.
- Publish deterministic JSON and Markdown coverage artifacts that classify each
  event as source-complete, source-partial, or blocked and name the exact missing
  proof needed by a later adapter-contract change.
- Require complete accounting of Current aliases and label-sensitive branches,
  exact source identities, duplicate-free canonical mappings, artifact
  recomputation, and all execution or training authority remaining false.
- Do not extend the event resolver, alter Current policy, run native simulator
  episodes, retry seeds `2000..2003`, launch gameplay, fit a model, change
  reward, or authorize training or promotion.

Success means every statically discovered Current event branch is represented
exactly once in the canonical matrix and either has all four upstream source
bindings or an explicit blocker. The rollback boundary is removal of the audit
tool and artifacts; no runtime behavior or existing evidence is modified.

## Capabilities

### New Capabilities

- `noncombat-event-semantics-coverage-audit`: Defines deterministic,
  provenance-bound static coverage evidence for Current-relevant event-option
  semantics and its no-execution authority boundary.

### Modified Capabilities

None.

## Impact

- Adds one offline analysis script, focused parser and artifact tests, a
  hash-bound audit input, canonical report artifacts, and a project-direction
  update.
- Reads `spirecomm/ai/agent.py` and the external
  `D:\CLionProjects\sts_lightspeed` checkout without modifying either source
  behavior or the external checkout.
- Uses the r2 `event_option_semantics_event_unsupported: The Cleric` result only
  as the motivation and predecessor evidence boundary; it does not reopen or
  reinterpret that Stage 2 execution.
