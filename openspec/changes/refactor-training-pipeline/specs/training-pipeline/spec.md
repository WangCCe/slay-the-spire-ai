## ADDED Requirements

### Requirement: Bounded Training Batches
The system SHALL provide a training orchestration workflow that runs live Communication Mod training in bounded batches instead of unbounded sessions.

#### Scenario: Run a bounded batch
- **WHEN** the user starts a training batch with a maximum game count
- **THEN** the orchestrator runs no more than that number of games
- **AND** it writes a batch summary with run count, average floor, win rate, and top death causes

#### Scenario: Preserve production Python path
- **WHEN** the orchestrator launches live Slay the Spire training on Windows
- **THEN** it uses the configured Windows Python environment for Communication Mod gameplay
- **AND** it does not use the WSL development Python path for live gameplay

### Requirement: Curriculum Route Scheduling
The system SHALL support curriculum configuration for map-route risk during RL training.

#### Scenario: Conservative startup phase
- **WHEN** no curriculum phase is explicitly selected
- **THEN** the training batch defaults to conservative Act 1 elite routing
- **AND** the batch summary records the selected route mode

#### Scenario: Progress to higher route risk
- **WHEN** recent evaluation metrics meet configured promotion thresholds
- **THEN** the curriculum MAY advance from conservative to mixed or aggressive routing
- **AND** the promotion decision is recorded with the metrics that justified it

### Requirement: Live Session Stability Controls
The system SHALL provide maintenance hooks that reduce slowdown during long live-game training sessions.

#### Scenario: Maintain run directory size
- **WHEN** a batch completes or reaches a configured maintenance interval
- **THEN** the system archives older run records according to the configured retention policy
- **AND** keeps the active `runs/<CHARACTER>` directory below the configured limit when possible

#### Scenario: Preserve logs and checkpoints
- **WHEN** maintenance runs between batches
- **THEN** the system preserves recent logs and checkpoint files before cleanup or rotation
- **AND** reports any maintenance failures without deleting unverified files

### Requirement: Offline Dataset Extraction
The system SHALL extract reusable offline training and evaluation artifacts from Slay the Spire run records and AI logs.

#### Scenario: Extract episode summaries
- **WHEN** the extractor processes `.run` files
- **THEN** it writes episode-level records containing seed or filename, victory, floor reached, path, deck size, relic count, score, playtime, and death cause

#### Scenario: Extract decision traces
- **WHEN** the extractor processes AI debug logs containing decision/action details
- **THEN** it writes decision-level records linked to the corresponding run when a link can be inferred
- **AND** it reports records that cannot be linked instead of discarding them silently

### Requirement: Checkpoint Promotion Evaluation
The system SHALL evaluate checkpoints with gameplay metrics before treating them as promoted training baselines.

#### Scenario: Evaluate a candidate checkpoint
- **WHEN** a candidate checkpoint is evaluated on a fixed seed pool
- **THEN** the evaluator reports average floor, win rate, boss reach rate, elite death rate, and action failure rate
- **AND** saves the evaluation summary next to checkpoint metadata

#### Scenario: Reject plateaued checkpoint
- **WHEN** a checkpoint fails configured promotion thresholds
- **THEN** the system marks it as not promoted
- **AND** preserves it as a normal checkpoint without overwriting the last promoted checkpoint
