## ADDED Requirements
### Requirement: Periodic run archiving during training
The system SHALL archive older `.run` files after every 200 training games to keep the active run directory small.

#### Scenario: Archive after threshold
- **GIVEN** training mode is enabled
- **AND** the run count reaches a multiple of 200
- **WHEN** the game ends
- **THEN** the system SHALL move the oldest run files so only the newest 1000 remain in `runs/<CHARACTER>`
- **AND** the archive location SHALL be `runs_archive/<CHARACTER>`

#### Scenario: Skip when not in training
- **GIVEN** training mode is disabled
- **WHEN** a game ends
- **THEN** the system SHALL NOT archive run files
