## MODIFIED Requirements

### Requirement: Exact snapshot hydration without mutation
The bridge SHALL validate and hydrate the minimum Communication Mod-compatible game and screen object graph required by the exact Current non-combat decision path, and it SHALL NOT mutate source snapshots or candidate records.

#### Scenario: A frozen row is hydrated
- **WHEN** every decision-relevant field is available from the registered snapshot or metadata source
- **THEN** the bridge SHALL create typed route, shop, event, or card-reward state with stable source-slot identity
- **AND** canonical hashes of the input snapshot and candidates SHALL remain unchanged after evaluation

#### Scenario: A decision-relevant field is absent
- **WHEN** Current can read a field whose exact value cannot be reconstructed from registered evidence
- **THEN** the row SHALL fail closed with a field-specific reason
- **AND** the bridge SHALL NOT insert a heuristic value that can affect the selected action

#### Scenario: A native shop has consumed card removal
- **WHEN** a validated shop snapshot reports `remove_cost == -1` and its legal candidate set contains no `remove_card` action
- **THEN** the bridge SHALL hydrate removal as unavailable with a policy-inert nonnegative typed cost
- **AND** it SHALL preserve the source snapshot and candidates byte-for-byte

#### Scenario: A shop remove-cost sentinel is inconsistent
- **WHEN** `remove_cost == -1` is paired with a legal `remove_card` candidate, or the reported cost is below `-1`, missing, boolean, or non-integer
- **THEN** the bridge SHALL fail with a field-specific structural blocker before Current executes
- **AND** it SHALL NOT infer removal availability or replace an unproven negative value
