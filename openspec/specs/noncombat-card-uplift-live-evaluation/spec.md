# noncombat-card-uplift-live-evaluation Specification

## Purpose

Define a bounded, source-bound live evaluation mode for frozen card-uplift
candidates, including intervention safety, evidence publication, and exact
rollback requirements.

## Requirements

### Requirement: Explicit bounded live-evaluation configuration
The system SHALL enable card-uplift live evaluation only from a canonical,
source-bound configuration with a game ceiling from 1 through 25. Shadow,
canary, and live-evaluation modes MUST be mutually exclusive.

#### Scenario: Live evaluation is not configured
- **WHEN** ordinary gameplay starts without the live-evaluation environment variable
- **THEN** the new mode remains inert and Current behavior is unchanged

#### Scenario: A configuration conflicts or drifts
- **WHEN** another card-uplift mode is configured or a source, model, authority, path, schema, or game-ceiling binding differs
- **THEN** startup fails before CommunicationMod gameplay begins

### Requirement: Existing intervention safety boundary is reused
The live evaluation SHALL substitute only uniquely mapped actions for supported
ordinary card rewards and MUST preserve Current for ineligible decisions. Any
runtime error MUST disable all later substitutions in the cohort.

#### Scenario: Eligible candidate action differs
- **WHEN** projection and scoring succeed and the frozen candidate differs from Current
- **THEN** the uniquely mapped live card or skip action is returned and recorded

#### Scenario: A decision is unsupported or fails
- **WHEN** the card reward is ineligible or projection, scoring, persistence, or action construction fails
- **THEN** Current is returned, with errors additionally disabling later substitutions

### Requirement: Bounded outcome and operational evidence
The evaluation SHALL publish canonical decision rows and fresh Ironclad run
records for no more than the configured game ceiling. The report MUST include
victories, floors, death reasons, substitutions, errors, invalid actions,
latency, bindings, and production-isolation status.

#### Scenario: Evaluation completes safely with a victory
- **WHEN** the cohort has at least one `victory=true`, zero runtime or invalid-action errors, intact bindings, and maximum latency at most 200 ms
- **THEN** the result is ready for a separate policy-promotion decision

#### Scenario: Evaluation has no victory or fails an operational gate
- **WHEN** no run wins or any hard operational gate fails
- **THEN** the report remains descriptive and grants no promotion or policy-quality authority

### Requirement: Exact rollback after evaluation
The evaluation MUST leave production checkpoints unchanged and restore the
pre-evaluation CommunicationMod configuration byte-for-byte.

#### Scenario: Cohort terminates
- **WHEN** the game ceiling is reached or execution stops because of failure
- **THEN** Current is restored before another ordinary gameplay batch can start
