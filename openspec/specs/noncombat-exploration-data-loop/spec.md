# noncombat-exploration-data-loop Specification

## Purpose
Define a bounded, replayable known-propensity collection loop for safe non-combat abstention actions without authorizing formal RL, OPE, causal claims, or live promotion.

## Requirements

### Requirement: Explicit Bounded Exploration Configuration
The system SHALL keep non-combat exploration disabled unless a versioned experiment configuration is explicitly provided, and SHALL reject configurations outside the fixed safety envelope.

#### Scenario: Normal gameplay has no exploration configuration
- **WHEN** the live process starts without `STS_NONCOMBAT_EXPLORATION_CONFIG`
- **THEN** non-combat decisions SHALL follow the existing Current policy path without an exploration wrapper changing the selected action
- **AND** no exploration session artifact SHALL be created

#### Scenario: Unsafe configuration is rejected
- **WHEN** a configuration enables an executable category other than `shop` or `card_reward`, sets a category rate above 1,000 basis points, or sets a per-run budget above two attempts
- **THEN** startup SHALL fail with a specific configuration error
- **AND** the system SHALL NOT silently clamp or partially apply the configuration

### Requirement: Guarded Non-Combat Action Proposals
The system SHALL represent each considered decision as a uniquely identified Current action plus normalized alternatives whose legality and rollout mode are explicit.

#### Scenario: Eligible card reward exposes safe abstention
- **WHEN** the Current policy selects a mapped card and the reward screen can immediately skip
- **THEN** the proposal SHALL contain the Current card action and `card_reward:skip` with unique action IDs
- **AND** both candidates SHALL map to materializable legal actions

#### Scenario: Eligible shop decision exposes safe abstention
- **WHEN** the Current policy selects a mapped purchase or purge and the shop can immediately materialize a leave, cancel, or proceed command
- **THEN** the proposal SHALL contain the Current action and `shop:leave` with unique action IDs
- **AND** proposal construction SHALL NOT mutate purchase, purge, or leaving-shop state

#### Scenario: Unsupported decision remains Current-only
- **WHEN** the Current action is already abstention, cannot map uniquely, has no immediately legal abstention, or occurs in a transitional state
- **THEN** the controller SHALL return the unmodified Current action
- **AND** it SHALL record a specific ineligibility reason without claiming alternative-action support

#### Scenario: Selected arm owns action-specific side effects
- **WHEN** an executable card-reward or shop decision evaluates a Current callback that updates tracker, decision-history, shop-transition, or decision-trace state
- **THEN** the system SHALL evaluate those updates inside a reversible preview and restore the pre-callback state before sampling
- **AND** it SHALL commit only the selected arm's action-specific bookkeeping and final decision trace exactly once

### Requirement: Category Rollout Boundary
The system SHALL execute alternatives only for the explicitly supported first-stage categories and SHALL keep other categories shadow-only.

#### Scenario: Event and route proposals are shadow-only
- **WHEN** an event or route proposal is observed during an exploration session
- **THEN** the system MAY record its baseline and candidate diagnostics
- **AND** it SHALL NOT replace the Current event or route action

#### Scenario: Richer alternative is not executable
- **WHEN** a shop, card-reward, event, or route proposal contains an alternative other than the first-stage safe abstention action
- **THEN** the controller SHALL mark that alternative shadow-only
- **AND** it SHALL exclude it from the executable behavior distribution

### Requirement: Exact Replayable Behavior Distribution
The system SHALL compute and persist an exact behavior distribution and deterministic draw for every eligible exploration decision.

#### Scenario: Binary exploration distribution is valid
- **WHEN** an eligible proposal uses `epsilon_bps`
- **THEN** the alternative probability SHALL equal `epsilon_bps / 10000` and the Current probability SHALL equal the remainder
- **AND** the exact candidate probabilities SHALL sum to one

#### Scenario: Identical input replays identically
- **WHEN** the same schema, session ID, seed, trajectory session ID, decision index, state hash, ordered candidates, and configuration are replayed
- **THEN** the draw, selected action ID, selected-action probability, and distribution hash SHALL match exactly

#### Scenario: Invalid probability evidence fails closed
- **WHEN** candidate IDs are duplicated, the distribution is incomplete, the selected action is unavailable, or canonical replay inputs are missing
- **THEN** the system SHALL return the unmodified Current action
- **AND** it SHALL NOT emit a known behavior probability

#### Scenario: Coercible numeric values are not exact evidence
- **WHEN** a replay-critical decision index, draw, probability numerator or denominator, or alternative-budget field is encoded as a boolean, float, or numeric string
- **THEN** the validator SHALL reject the record instead of coercing the value to an integer
- **AND** the record SHALL NOT contribute known-propensity support

### Requirement: Persisted And Confirmed Exploration Actions
The system SHALL persist every eligible sampled mixture action before returning it and SHALL confirm its game transition before treating it as executed evidence.

#### Scenario: Proposal persistence fails
- **WHEN** the system cannot append the complete proposal record before returning the sampled Current or alternative action
- **THEN** it SHALL return the unmodified Current action
- **AND** it SHALL report the persistence failure without consuming a known-propensity sample

#### Scenario: Current arm is sampled
- **WHEN** an eligible mixture draw selects the Current action and the complete proposal record is persisted
- **THEN** the system SHALL return the Current action with its exact selected-action probability
- **AND** it SHALL retain the alternative's nonzero probability in the recorded distribution

#### Scenario: Alternative arm is sampled
- **WHEN** an eligible mixture draw selects the alternative and the complete proposal record is persisted
- **THEN** the system SHALL reserve one per-run alternative-attempt budget unit before returning the action
- **AND** a rejected or unresolved transition SHALL NOT release that unit for resampling

#### Scenario: Selected action is confirmed
- **WHEN** the subsequent game state uniquely matches the category-specific expected transition for the selected high-level action
- **THEN** the system SHALL append a confirmation referencing the stable decision ID
- **AND** the exporter MAY mark the sample as executed known-propensity evidence

#### Scenario: Selected action is not confirmed
- **WHEN** the subsequent state rejects, ambiguously applies, supersedes, or never resolves the selected action
- **THEN** the system SHALL preserve the attempted proposal and resolution status for diagnosis
- **AND** the exporter SHALL exclude it from executed known-propensity support

### Requirement: Exploration Session Provenance
The system SHALL freeze enough session and decision provenance to audit a bounded live experiment independently.

#### Scenario: Session starts
- **WHEN** a valid exploration configuration is activated
- **THEN** the system SHALL require a tracked-clean source tree and write a manifest containing the effective configuration and hash, source commit, clean-state evidence, Python executable, command, session ID, output paths, and pre-session isolation hashes
- **AND** it SHALL assign stable trajectory-session and decision identifiers before actions are sampled

#### Scenario: Qualification source is dirty
- **WHEN** tracked source changes are present at exploration-session startup
- **THEN** the system SHALL refuse to start a qualification batch
- **AND** it SHALL NOT create behavior records attributed only to the current commit

#### Scenario: Session outputs are replayed
- **WHEN** the offline validator reads the session manifest and append-only records
- **THEN** it SHALL verify configuration hashes, state hashes, candidate uniqueness, exact distributions, draws, selections, confirmations, and conservative run joins
- **AND** it SHALL list every exclusion or mismatch by reason

#### Scenario: CommunicationMod configuration is compared semantically
- **WHEN** the launcher rewrites Java Properties comments, ordering, or timestamp text without changing effective values
- **THEN** the isolation comparison SHALL preserve equivalence using Java continuation, escape, natural-line, and last-value-wins semantics
- **AND** any effective command or setting change SHALL produce a different semantic hash

### Requirement: Known-Propensity Data Qualification Gate
The system SHALL qualify only the structural and statistical support of the collected behavior data, separately from policy-quality or RL readiness.

#### Scenario: Bounded batch qualifies
- **WHEN** a fresh batch has at least 25 uniquely joined trajectories, all eligible executed decisions replay and confirm exactly, all selected actions are candidate-legal, and every executable category has at least five confirmed baseline and five confirmed alternative selections
- **THEN** the report SHALL set `known_propensity_exploration_data_ready` to true
- **AND** it SHALL report propensity coverage, support, outcome coverage, terminal-floor distribution, killed-by distribution, and victories

#### Scenario: Bounded batch lacks support
- **WHEN** any trajectory, replay, confirmation, legality, category-support, or isolation condition is not met
- **THEN** the report SHALL keep `known_propensity_exploration_data_ready` false
- **AND** it SHALL identify the blocking conditions without increasing exploration beyond the configured safety envelope

### Requirement: Live Isolation And Rollback
The system SHALL leave production gameplay configuration, combat checkpoints, and existing offline policy artifacts unchanged by the exploration experiment.

#### Scenario: Exploration session completes or fails
- **WHEN** the bounded session exits successfully or with an error
- **THEN** CommunicationMod configuration and combat checkpoint path, size, timestamp, and hash SHALL match the pre-session snapshot
- **AND** no pilot model SHALL be auto-loaded or rewritten

#### Scenario: Exploration is disabled after a session
- **WHEN** the explicit exploration configuration is removed
- **THEN** subsequent gameplay SHALL use the existing Current decision behavior
- **AND** retaining or deleting exploration-only records SHALL have no effect on live policy loading
