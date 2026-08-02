## ADDED Requirements

### Requirement: Audited Generic Event Enrichment
For new code-level sessions, the bridge SHALL enrich a native event without inline option semantics through the reachable-surface successor resolver, while preserving source snapshot and candidate bytes and retaining historical registration validation by schema.

#### Scenario: A generic native event is hydrated
- **WHEN** the event is in the audited generic set and its candidates satisfy the successor contract
- **THEN** the bridge SHALL hydrate contiguous Current options, call Current with the registered event identity, and reverse-map the selected Current position to the exact simulator choice index
- **AND** diagnostics SHALL record upstream and Current event ids, event data, semantic source, Current position, simulator choice index, and selected action id

#### Scenario: An explicit native event is hydrated
- **WHEN** the event is covered by an explicit static, phased, or dynamic rule
- **THEN** the bridge SHALL use the explicit successor rule and preserve its stronger checks
- **AND** generic enrichment SHALL NOT shadow or relax that rule

#### Scenario: Event enrichment cannot prove its source
- **WHEN** the event is outside the explicit and generic sets or any identity, candidate, mutation, mapping, or Current-handling proof fails
- **THEN** the bridge SHALL stop before issuing a simulator action
- **AND** it SHALL NOT fall back to candidate position zero merely because Current's present default would select it

### Requirement: Successor Bridge Has Structural-Only Authority
The reachable-surface bridge extension SHALL establish only code-level observation and action-mapping behavior and SHALL grant no native execution or policy-quality authority.

#### Scenario: All source-only bridge regressions pass
- **WHEN** explicit, generic, sparse-index, phase, dynamic-context, mutation, unknown-event, and historical-isolation tests pass
- **THEN** the extension MAY be recorded as ready for a separate compatibility preregistration
- **AND** gameplay, baseline-floor, outcome, reward, model, OPE, formal-RL, training, qualification, loading, and promotion authority SHALL remain false
