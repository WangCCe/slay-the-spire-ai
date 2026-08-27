## ADDED Requirements

### Requirement: Live replay executed-action provenance
The RL v2 live collection path SHALL mark a stored combat transition to anchor to its executed action when the emitted legal action differs from the pending RL proposal or when no RL proposal exists for that state. It SHALL leave the override disabled when the emitted action matches the pending RL proposal, and it SHALL persist the derived value through the existing replay checkpoint schema without changing action selection.

#### Scenario: Direct RL action is emitted unchanged
- **WHEN** a pending RL proposal and the legal emitted combat action encode to the same action index
- **THEN** the stored transition uses that action with executed-action anchor override disabled

#### Scenario: Outer guard replaces the RL proposal
- **WHEN** a pending RL proposal exists and an outer guard emits a different legal encoded combat action for the same state
- **THEN** the stored transition uses the emitted action with executed-action anchor override enabled

#### Scenario: Fallback takeover emits without an RL proposal
- **WHEN** no pending RL proposal exists and the outer policy emits a legal encoded combat action
- **THEN** the stored transition uses the emitted action with executed-action anchor override enabled

#### Scenario: Emitted action cannot form a legal combat transition
- **WHEN** the emitted action is non-combat, unencodable, or invalid under the current action mask
- **THEN** the collection path stores no provenance-marked transition for that action

#### Scenario: Provenance survives checkpoint round trip
- **WHEN** a live replay containing direct and outer-policy actions is saved and loaded
- **THEN** each transition retains its derived executed-action anchor override value
