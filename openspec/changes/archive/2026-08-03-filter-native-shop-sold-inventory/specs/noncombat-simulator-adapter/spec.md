## MODIFIED Requirements

### Requirement: Deterministic Non-Combat Environment API
The adapter SHALL expose deterministic Ironclad reset, deep clone, canonical snapshot, legal-action enumeration, action execution, native SimpleAgent target-action query, and terminal outcome through JSON-compatible values. Native shop snapshots SHALL expose the same visible inventory boundary as Communication Mod while preserving simulator source-slot identity.

#### Scenario: Same seed resets identically
- **WHEN** two environments reset with the same seed and ascension under the same bound identities
- **THEN** their canonical snapshots and legal actions SHALL be byte-equivalent at every corresponding policy decision

#### Scenario: Clone branches are isolated
- **WHEN** an environment is cloned at a target decision and an action executes on only one branch, including an action that enters a new Act
- **THEN** the untouched branch snapshot and map SHALL remain unchanged
- **AND** the changed branch SHALL return a legal successor or terminal outcome

#### Scenario: Reported candidates execute legally
- **WHEN** the adapter reports legal candidates at a target decision
- **THEN** every candidate SHALL execute successfully on a fresh clone of that decision state
- **AND** no unreported action SHALL be accepted as a target-category action

#### Scenario: Upstream screen field lacks current semantics
- **WHEN** an upstream screen-info field is uninitialized, stale, or not defined for the current target screen
- **THEN** the adapter SHALL omit it or emit an explicit canonical unavailable value
- **AND** process memory contents SHALL NOT enter snapshots or policy features

#### Scenario: Native baseline target action is queried
- **WHEN** a baseline-following environment reaches a route, shop, event, or card-reward decision
- **THEN** the adapter SHALL map the corresponding upstream SimpleAgent decision to exactly one currently reported candidate
- **AND** repeated queries SHALL leave source snapshot and candidate bytes unchanged

#### Scenario: Native baseline continuation is broken
- **WHEN** an environment previously applies a target action different from its queried SimpleAgent action
- **THEN** a later native-baseline query on that trajectory SHALL fail closed
- **AND** the adapter SHALL NOT present a stale route path as a counterfactual baseline action

#### Scenario: Native shop snapshot is emitted
- **WHEN** fixed shop slots contain a sold `price == -1` entry, a nonnegative unaffordable entry, or a nonnegative Courier replacement
- **THEN** the snapshot SHALL omit exactly the sold entry and SHALL retain every nonnegative visible entry with its original fixed `slot`
- **AND** legal candidate ids SHALL continue to map to original fixed slots rather than compact visible-list positions

#### Scenario: Native shop inventory has an invalid negative price
- **WHEN** a card, relic, or potion source slot has a price below `-1`
- **THEN** snapshot generation SHALL fail with the affected inventory kind and source slot
- **AND** it SHALL NOT reinterpret the invalid value as a sold item or pass it to policy hydration
