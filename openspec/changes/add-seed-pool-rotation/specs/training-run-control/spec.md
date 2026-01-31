## ADDED Requirements
### Requirement: Seed pool rotation for training
The system SHALL allow training runs to rotate through a provided list of seeds on a per-game basis.

#### Scenario: Rotate seeds across consecutive games
- **WHEN** the user supplies a seed pool file and starts training
- **THEN** each new game uses the next seed from the pool

### Requirement: Bounded training runs
The system SHALL allow limiting the number of games in a training session.

#### Scenario: Stop after N games
- **WHEN** the user sets a maximum game count
- **THEN** the process exits after N games are completed
