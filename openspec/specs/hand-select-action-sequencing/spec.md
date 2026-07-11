# hand-select-action-sequencing Specification

## Purpose
Define ordered HAND_SELECT card selection and optional confirmation behavior.

## Requirements

### Requirement: HAND_SELECT keys and confirmation are serialized
The action system SHALL wait for the response to the final HAND_SELECT card-key
command before executing the terminal confirmation.

#### Scenario: Multiple cards are selected
- **WHEN** a HAND_SELECT action queues two or more card-key commands and a terminal confirmation
- **THEN** every card-key command SHALL wait for game readiness before the next queued action executes
- **AND** the terminal confirmation SHALL NOT execute before the final card-key response marks the game ready

#### Scenario: Final key response enables confirmation
- **WHEN** the final card-key response reports HAND_SELECT with confirmation available
- **THEN** the queued terminal confirmation SHALL execute exactly once against that updated state

### Requirement: Final-key acknowledgement does not trigger a duplicate decision
The coordinator SHALL defer the agent callback for a final HAND_SELECT card-key
response while the terminal confirmation remains queued.

#### Scenario: Stale HAND_SELECT response arrives before terminal confirmation
- **WHEN** a final card-key response still reports HAND_SELECT and a terminal confirmation is queued
- **THEN** the coordinator SHALL execute the queued confirmation before invoking another agent decision
- **AND** the final-key response SHALL NOT cause a second confirmation decision

#### Scenario: Confirmation closes the screen
- **WHEN** the queued terminal confirmation is sent and the next state leaves HAND_SELECT
- **THEN** the system SHALL NOT emit another HAND_SELECT confirmation from the prior key response

### Requirement: Optional confirmation fails safely on changed state
The terminal optional confirmation SHALL emit no command if its execution state
does not expose a legal HAND_SELECT confirmation.

#### Scenario: Screen changes before confirmation
- **WHEN** the queued terminal confirmation executes after the screen has left HAND_SELECT
- **THEN** it SHALL emit no `confirm` command

#### Scenario: Confirmation is unavailable
- **WHEN** the queued terminal confirmation executes on HAND_SELECT without `confirm` in the available commands
- **THEN** it SHALL emit no `confirm` command
