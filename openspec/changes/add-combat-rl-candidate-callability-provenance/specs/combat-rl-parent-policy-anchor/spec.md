## MODIFIED Requirements

### Requirement: Backward-compatible anchor override replay state
The RL v2 replay buffer SHALL persist an optional per-transition executed-action anchor override and exact proposal action identity in schema v3. It SHALL preserve legacy replay behavior when either field is absent and SHALL expose proposal identity only through an explicit opt-in sampling contract.

#### Scenario: Version 3 replay round trip
- **WHEN** replay containing direct proposals, changed proposals, no-proposal takeover, and legacy-unknown rows is saved and loaded
- **THEN** each transition retains its original override value and exact proposal identity

#### Scenario: Version 2 replay load
- **WHEN** a version 2 replay has anchor override metadata but no proposal identity
- **THEN** every restored transition retains its override and receives legacy-unknown proposal identity

#### Scenario: Version 1 replay load
- **WHEN** a legacy version 1 replay has neither anchor override nor proposal identity
- **THEN** every restored transition has the override disabled and legacy-unknown proposal identity

#### Scenario: Existing caller compatibility
- **WHEN** a caller stores or samples a transition without requesting proposal identity
- **THEN** existing anchor behavior and the default sample field contract remain compatible

### Requirement: Live replay executed-action provenance
The RL v2 live collection path SHALL retain the pending RL proposal index when an emitted legal action is committed. It SHALL mark a stored combat transition to anchor to its executed action when that action differs from the pending proposal or when no proposal exists, and it SHALL persist direct, changed-proposal, and no-proposal identities separately without changing action selection.

#### Scenario: Direct RL action is emitted unchanged
- **WHEN** a pending RL proposal and the legal emitted combat action encode to the same action index
- **THEN** the stored transition retains that proposal and executed action with executed-action anchor override disabled

#### Scenario: Outer guard replaces the RL proposal
- **WHEN** a pending RL proposal exists and an outer guard emits a different legal encoded combat action for the same state
- **THEN** the stored transition retains the original proposal, stores the emitted action, and enables executed-action anchor override

#### Scenario: Fallback takeover emits without an RL proposal
- **WHEN** no pending RL proposal exists and the outer policy emits a legal encoded combat action
- **THEN** the stored transition records explicit no-proposal identity and enables executed-action anchor override

#### Scenario: Emitted action cannot form a legal combat transition
- **WHEN** the emitted action is non-combat, unencodable, or invalid under the current action mask
- **THEN** the collection path stores no provenance-marked transition for that action

#### Scenario: Provenance survives checkpoint round trip
- **WHEN** a live replay containing direct, changed-proposal, and no-proposal actions is saved and loaded
- **THEN** each transition retains its proposal identity and derived executed-action anchor override value
