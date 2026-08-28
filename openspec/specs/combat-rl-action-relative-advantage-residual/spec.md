# combat-rl-action-relative-advantage-residual Specification

## Purpose

Define source-bound training, abstention, safety, artifact, and evaluation
contracts for a development-only post-guard action-relative advantage scorer.

## Requirements

### Requirement: Complete action-relative corpus expansion

The system SHALL expand every retained guard-advantage corpus row into one
development example for each supported non-guard branch and SHALL preserve the
state tensors, guard identity, candidate identity, legal-action context, raw
branch return, guard return, and relative advantage.

#### Scenario: Corpus row has multiple alternatives
- **WHEN** a retained row contains the guarded branch and three supported legal alternatives
- **THEN** the action-relative dataset contains three examples with distinct candidate identities and exact branch-minus-guard targets

#### Scenario: Corpus branch is inconsistent
- **WHEN** a branch identity is illegal, outside the registered action space, duplicates the guard, or has a non-finite return
- **THEN** validation fails before fitting and no artifact is written

### Requirement: Frozen action-relative advantage scorer

The system SHALL keep the parent frozen and fit one shared development-only
scorer from frozen parent latent state, guard identity, candidate identity, and
legal-action context to the registered scaled relative-advantage target.

#### Scenario: Scorer evaluates supported alternatives
- **WHEN** a batch contains one state with multiple supported alternatives
- **THEN** the scorer returns one finite scalar predicted advantage per alternative without changing any parent parameter

#### Scenario: Fixed fit completes
- **WHEN** the registered corpus, source hashes, recipe, seed, and update budget validate
- **THEN** the system fits exactly one artifact and publishes loss, held-out value, ranking, selection, support, and parent-freeze evidence

### Requirement: Calibrated abstaining selection

The system SHALL score every supported allowed alternative, select the maximum
predicted relative advantage, and execute it only when it reaches the
registered return-unit threshold. Otherwise the system SHALL preserve the
exact guarded action.

#### Scenario: Best predicted alternative clears threshold
- **WHEN** at least one supported allowed alternative has predicted advantage at or above the registered threshold
- **THEN** the policy executes the highest-scoring legal alternative and records its predicted advantage, true advantage when available, and active constraints

#### Scenario: No alternative clears threshold
- **WHEN** every supported allowed alternative is below the registered threshold
- **THEN** the policy executes the exact guarded action and records a threshold abstention

#### Scenario: EndTurn safety boundary applies
- **WHEN** the scorer is invoked after the wasteful-EndTurn guard and action 90 is registered as forbidden
- **THEN** action 90 is removed before maximization and cannot be a residual intervention

### Requirement: Source-bound development artifact

The system SHALL serialize the scorer with its schema, frozen-parent identity,
corpus identities, architecture, target transform, threshold, recipe, fit
telemetry, and development-only authority, and SHALL reject incomplete or
mismatched artifacts.

#### Scenario: Artifact roundtrip matches
- **WHEN** a valid artifact is loaded against the exact parent and corpus hashes
- **THEN** held-out predictions and selected actions match the pre-save artifact exactly on CPU

#### Scenario: Artifact binding differs
- **WHEN** parent, corpus, schema, recipe, or tensor structure differs from the registered artifact
- **THEN** loading fails before evaluation or policy execution

### Requirement: Fixed offline and fresh simulator decision

The system SHALL apply the registered offline integrity conditions before at
most one seed-disjoint matched LightSTS comparison with guarded control and
SHALL publish all fixed conditions and decision authority.

#### Scenario: Offline integrity fails
- **WHEN** held-out selection is empty, mean selected true advantage is negative, or any illegal or forbidden selection occurs
- **THEN** the system closes the recipe without a fresh simulator run or parameter sweep

#### Scenario: Fresh policy gate passes
- **WHEN** candidate-only victories are at least control-only victories, mean paired reward and HP deltas are non-negative, no nonterminal profiles are excluded, and at least one constrained intervention occurs
- **THEN** the system may retain the recipe for separately registered real-game validation but SHALL NOT authorize production loading or promotion

#### Scenario: Fresh policy gate fails
- **WHEN** any registered fresh policy condition fails
- **THEN** the system closes the recipe without changing the scorer, threshold, seeds, horizon, training recipe, or safety constraint
