## ADDED Requirements
### Requirement: Back up latest checkpoint at training start
When training mode is enabled, the system SHALL copy the latest checkpoint to a backup location before training begins.

#### Scenario: Backup available checkpoint
- **GIVEN** training mode is enabled
- **AND** a checkpoint exists in `checkpoints/`
- **WHEN** the agent starts
- **THEN** the system SHALL copy the latest checkpoint into a backup directory outside `checkpoints/`
- **AND** the backup filename SHALL be unique to avoid overwriting previous backups

#### Scenario: No checkpoint to back up
- **GIVEN** training mode is enabled
- **AND** no checkpoint exists in `checkpoints/`
- **WHEN** the agent starts
- **THEN** the system SHALL skip backup and log a warning
