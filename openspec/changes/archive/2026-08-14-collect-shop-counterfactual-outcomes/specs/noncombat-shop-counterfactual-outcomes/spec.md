## ADDED Requirements

### Requirement: Complete supported shop branches
The collector SHALL evaluate every legal candidate at each selected supported
A0 shop state under frozen Current-policy continuation.

#### Scenario: Shop state is supported
- **WHEN** a non-Courier shop exposes multiple legal actions
- **THEN** the corpus records the source, Current action, candidates, and one complete outcome per candidate

#### Scenario: Shop state is unsupported
- **WHEN** the native support envelope reports a registered blocker
- **THEN** the source is censored with its exact reason and contributes no partial row

### Requirement: Deterministic bounded evidence
The collector MUST use the fixed `95000..95063` cohort and fixed resource limits
and MUST prove deterministic replay on eight complete sources.

#### Scenario: Replay matches
- **WHEN** the first action branch of a replay source is evaluated twice
- **THEN** both traces match exactly

#### Scenario: Unknown failure occurs
- **WHEN** an unknown blocker, replay difference, active game process, deadline violation, or incomplete branch occurs
- **THEN** execution aborts without retry or replacement seed

### Requirement: Fixed learning-signal verdict
The collector SHALL authorize only a separate source-only learning proposal
when all preregistered coverage and signal floors pass.

#### Scenario: Signal gate passes
- **WHEN** at least 24 sources are complete, 12 are informative, four action kinds are represented, and eight replays match
- **THEN** the report marks shop signal viable for a separate learning proposal

#### Scenario: Signal gate fails
- **WHEN** any preregistered floor is unmet
- **THEN** Current remains the rollback and no training, retry, tuning, qualification, or promotion is authorized

### Requirement: Offline isolation
The collector MUST NOT access production checkpoints, CommunicationMod,
gameplay, protected seed inventories, models, or training operations.

#### Scenario: Collection executes
- **WHEN** the native outcome cohort runs
- **THEN** operations and authority fields prove source-only model-free isolation
