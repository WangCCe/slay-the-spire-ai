# combat-rl-provenance-aware-successor Specification

## Purpose

Define deterministic, evidence-gated full-network combat RL successor fitting
from parity-qualified replay with executed-action provenance.

## Requirements

### Requirement: Immutable parity-qualified training input
The system MUST accept only the preregistered zero-update parity checkpoint with the expected SHA-256, transition count, compatible RL v2 metadata, empty optimizer state, equal parent and target parameters, legal stored actions, and nonzero executed-action overrides.

#### Scenario: Qualified checkpoint is supplied
- **WHEN** every bound checkpoint identity and replay invariant matches
- **THEN** the runner may construct the deterministic development split before fitting

#### Scenario: Input identity or invariant differs
- **WHEN** the checkpoint hash, transition count, metadata, optimizer state, parameter equality, action legality, or override coverage differs
- **THEN** the runner fails before creating a final output directory

### Requirement: Recipe-before-corpus parity collection
The system MUST freeze the optimizer recipe, split rule, provenance-stratified eligibility thresholds, seed-generation rule, and production-r16 collection behavior before collecting a new training replay. The new replay MUST pass zero-update, trace, inventory, boundary, action legality, provenance reconciliation, and direct eval-parent parity checks before fitting.

#### Scenario: Registered fresh cohort passes
- **WHEN** exactly the registered games complete on the registered seeds and every parity check passes
- **THEN** the immutable replay hash may be bound as training-only input for the registered recipe

#### Scenario: Collection or parity check fails
- **WHEN** game count, seed order, zero-update state, trace binding, inventory identity, boundary integrity, action legality, provenance reconciliation, or direct eval-parent agreement fails
- **THEN** the cohort remains diagnostic-only and no candidate is fitted

### Requirement: Deterministic bounded full-network fitting
The system SHALL split complete terminal-delimited combats with the registered split seed and SHALL fit all online-network parameters with the registered CPU seed, learning rate, batch size, frozen target, frozen parent anchor, parent anchor weight, and exact optimizer-update budget.

#### Scenario: Registered recipe is executed twice on equivalent temporary inputs
- **WHEN** the same checkpoint and registered configuration are supplied
- **THEN** split indices, objective summaries, candidate parameters, and candidate hash are identical

#### Scenario: Training update budget is incomplete
- **WHEN** fewer or more than the registered optimizer updates complete or any loss is non-finite
- **THEN** the result is ineligible for a fresh holdout

### Requirement: Provenance-aware parent anchor labels
The system SHALL use the stored executed action as the parent-policy anchor label on every sampled override row and the frozen parent's mask-aware greedy action on every sampled direct row.

#### Scenario: Mixed provenance batch is sampled
- **WHEN** an optimizer batch contains direct and executed-action override transitions
- **THEN** anchor telemetry reports the sampled override count and each row uses its required label source

#### Scenario: Override action is invalid
- **WHEN** any executed-action override is invalid under its stored action mask
- **THEN** fitting fails before applying an optimizer update

### Requirement: Partitioned development evidence
The system SHALL report parent and candidate one-step TD loss, greedy action disagreement, provenance-aware anchor-label agreement, positive-energy End Turn behavior, parameter movement, and objective telemetry separately for fitting and validation partitions, including direct and override validation strata.

#### Scenario: Bounded fitting completes
- **WHEN** all registered optimizer updates finish
- **THEN** the report binds every metric to the input hash, split indices, recipe, candidate hash, and development-only authority

### Requirement: Fixed downstream eligibility gate
The system SHALL permit only a separately registered fresh holdout when all preregistered technical, fit, materiality, direct-policy stability, override-label uplift, provenance, and serialization checks pass. It MUST NOT grant gameplay, qualification, promotion, or production authority.

#### Scenario: Every stratified development condition passes
- **WHEN** validation TD loss improves, overall parent disagreement is at least 5%, direct parent disagreement is at most 10%, override executed-label agreement improves by at least 0.10 absolute, positive-energy End Turn count increases by at most two, both validation provenance strata are nonempty, and all integrity checks pass
- **THEN** the frozen candidate hash is eligible only for a separate fresh holdout

#### Scenario: Any stratified development condition fails
- **WHEN** one or more fixed conditions fail
- **THEN** production r16 remains authoritative and no alternate recipe is fitted on the same corpus
