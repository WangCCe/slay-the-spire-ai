## ADDED Requirements
### Requirement: Restore trainer state in training mode
When training mode is enabled, the system SHALL restore trainer state from checkpoints, including optimizer state, epsilon, and step counters.

#### Scenario: Restore trainer checkpoint
- **GIVEN** training mode is enabled
- **AND** a compatible checkpoint is available
- **WHEN** the agent starts
- **THEN** the trainer SHALL load the checkpoint state and resume with the saved epsilon and optimizer state

#### Scenario: Fall back to weights-only loading
- **GIVEN** training mode is enabled
- **AND** the checkpoint does not include trainer state
- **WHEN** the agent starts
- **THEN** the system SHALL load weights only and continue with default trainer state
