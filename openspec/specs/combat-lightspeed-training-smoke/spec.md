# Combat LightSTS Training Smoke Specification

## Purpose

Define a bounded, source-bound combat RL training smoke in LightSTS that proves the simulator transition, optimizer, checkpoint, and held-out evaluation path without granting live-game or production authority.

## Requirements

### Requirement: Source-only transition generation
The system SHALL generate bounded RL v2 combat transitions from a fixed LightSTS seed cohort using a deterministic network-independent behavior policy and explicit native reward definition.

#### Scenario: Supported successor
- **WHEN** a legal simulator action moves between two supported states
- **THEN** the runner stores the current observation, action, reward, next observation, terminal flag, and both legal-action masks in the existing replay contract

#### Scenario: Terminal successor
- **WHEN** a legal action ends the simulator combat
- **THEN** the runner stores a terminal transition with a classified outcome and no fabricated next-state features

#### Scenario: Unsupported successor
- **WHEN** a legal action reaches `CARD_SELECT` or another unsupported native state
- **THEN** the runner excludes the pending transition, records the unsupported reason, and does not label the boundary terminal

### Requirement: Disposable CPU training
The system SHALL fit a fresh deterministic RL v2 network on CPU through the existing replay buffer and trainer without reading a production checkpoint.

#### Scenario: Optimizer smoke succeeds
- **WHEN** the registered transition cohort supplies enough accepted replay rows
- **THEN** training produces finite losses, at least one optimizer update, and a non-zero parameter delta from the initial network

#### Scenario: Simulator-only checkpoint
- **WHEN** the fitted candidate is saved
- **THEN** its metadata and path classify it as simulator-only and prevent it from satisfying production qualification or promotion inputs

### Requirement: Paired held-out simulator evaluation
The system SHALL evaluate the same deterministic network initialization before and after fitting on a fixed seed cohort disjoint from training.

#### Scenario: Evaluation completion
- **WHEN** both policies run on every held-out seed within the decision bound
- **THEN** the report includes paired outcomes, player HP, decision counts, unsupported reasons, and aggregate deltas

#### Scenario: No uplift
- **WHEN** the fitted policy does not improve the held-out simulator metrics
- **THEN** the technical smoke may still complete, but the report SHALL not claim policy improvement or authorize a larger run without a separate decision

### Requirement: Production isolation
The training smoke SHALL not start the game, load or write production checkpoints, or grant mechanics-equivalence, transfer, qualification, promotion, or live policy-quality authority.

#### Scenario: Report authority
- **WHEN** a smoke report is published
- **THEN** simulator fitting authority is scoped to the registered run and all production, gameplay, transfer, qualification, and promotion authority flags are false

#### Scenario: Production import isolation
- **WHEN** the normal CommunicationMod agent imports
- **THEN** neither the LightSTS native module nor the simulator training runner is imported
