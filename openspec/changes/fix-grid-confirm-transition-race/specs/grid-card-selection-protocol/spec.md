## ADDED Requirements

### Requirement: GRID selectors execute across ordered state boundaries

The system SHALL execute each GRID card selector exactly once and SHALL obtain
a CommunicationMod state ordered after that selector before executing the next
selector or terminal confirmation.

#### Scenario: Stale frame is pending after a GRID choose selector
- **WHEN** a GRID card selection sends `choose` and a pre-selection state frame is received first
- **THEN** the system keeps the selection sequence in flight and obtains a post-selector state before confirmation or another agent callback
- **AND** it does not send the same selector a second time

#### Scenario: GRID click selector uses the same ordering contract
- **WHEN** GRID card positions select the `click` transport
- **THEN** the click requires readiness, waits for a response, and is followed by an ordered one-frame state boundary

#### Scenario: GRID key fallback uses the same ordering contract
- **WHEN** neither a positioned click nor choose transport is available for GRID selection
- **THEN** the key selector requires readiness, waits for a response, and is followed by an ordered one-frame state boundary

### Requirement: GRID confirmation settles before callbacks resume

The system SHALL send at most one low-level confirm for a GRID card-selection
sequence and SHALL obtain a state ordered after that confirm before allowing a
new agent callback.

#### Scenario: Stale GRID frame arrives after confirmation
- **WHEN** the optional GRID confirm is sent and a pre-transition GRID state frame is received first
- **THEN** the queued transition boundary suppresses an agent callback on that frame
- **AND** no second `ProceedAction` or low-level confirm is emitted from the stale frame

#### Scenario: Confirmation is no longer legal
- **WHEN** the ordered post-selector state has changed screens or does not expose a legal confirm
- **THEN** the optional confirm sends no command and normal callback processing resumes

### Requirement: Shared action defaults remain compatible

The system MUST preserve existing readiness and response-wait defaults for
shared choose, click, wait, and optional-confirm actions outside GRID card
selection.

#### Scenario: Non-GRID callers omit serialization options
- **WHEN** an existing caller constructs a shared action without the new optional arguments
- **THEN** its readiness and response-wait behavior matches the pre-change behavior

#### Scenario: HAND_SELECT selection remains unchanged
- **WHEN** `CardSelectAction` builds a HAND_SELECT sequence
- **THEN** its existing serialized key and terminal-confirm contract remains unchanged and no GRID settle action is inserted
