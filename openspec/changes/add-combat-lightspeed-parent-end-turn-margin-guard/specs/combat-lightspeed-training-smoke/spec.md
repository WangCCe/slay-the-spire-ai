## ADDED Requirements

### Requirement: Optional parent end-turn margin objective
The system SHALL optionally add a registered frozen-parent end-turn margin objective to simulator-only warm-start training while preserving all prior defaults.

#### Scenario: Guard disabled
- **WHEN** parent end-turn margin guard weight is `0.0`
- **THEN** replay optimization and objective reporting preserve prior behavior

#### Scenario: Guard enabled
- **WHEN** finite positive guard weight and cap are supplied with a valid simulator-only warm-start checkpoint
- **THEN** the runner initializes one immutable parent anchor and reports separate total, TD, parent-policy anchor, and end-turn margin guard objectives

#### Scenario: Guarded successor checkpoint
- **WHEN** guarded fitting publishes a simulator-only checkpoint
- **THEN** its source binding includes parent checkpoint identity, parent parameter identity, guard weight, and guard cap
