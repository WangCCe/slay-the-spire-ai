# combat-rl-action-relative-uncertainty-ensemble Specification

## Purpose

Define deterministic bootstrap fitting, uncertainty-aware abstention,
source-bound artifacts, and fixed evidence gates for a development-only
action-relative combat candidate.

## Requirements

### Requirement: Deterministic bootstrap ensemble fit

The system SHALL fit exactly five independent action-relative scorer heads over
registered with-replacement bootstrap samples of the expanded training pairs,
SHALL keep one shared parent frozen, and SHALL publish member seeds, bootstrap
hashes, losses, scorer hashes, and parent-freeze evidence.

#### Scenario: Registered fit completes
- **WHEN** the committed parent, corpora, source hashes, member seeds, recipe, and update budget validate
- **THEN** each member fits once on its deterministic bootstrap and the parent parameter hash remains unchanged

#### Scenario: Bootstrap or recipe differs
- **WHEN** a member seed, bootstrap identity, fit parameter, source binding, or corpus binding differs from the registration
- **THEN** validation fails and no development artifact is published

### Requirement: Lower-confidence abstaining selection

The system SHALL score each supported allowed alternative with every ensemble
member, SHALL define its policy score as member mean minus one unbiased sample
standard deviation, and SHALL intervene only when the maximum policy score is
at least 0.5 return units.

#### Scenario: Confident alternative clears the gate
- **WHEN** the maximum allowed lower-confidence score is at least 0.5
- **THEN** the policy selects that alternative and records its member mean, sample standard deviation, lower-confidence score, and active constraints

#### Scenario: Disagreement or low mean closes the gate
- **WHEN** every allowed lower-confidence score is below 0.5
- **THEN** the policy preserves the exact guard action and records an abstention

#### Scenario: Forbidden action scores highest
- **WHEN** a forbidden action has the highest unconstrained lower-confidence score
- **THEN** the action is removed before maximization and cannot be selected

### Requirement: Source-bound ensemble artifact

The system SHALL serialize a development-only ensemble artifact containing the
single frozen-parent identity, five ordered member scorer states and hashes,
member and bootstrap identities, fixed confidence rule, corpus identities,
recipe, telemetry, and non-production authority.

#### Scenario: Artifact roundtrip matches
- **WHEN** the artifact is loaded against the exact parent, corpora, metadata, and recipe
- **THEN** member predictions, uncertainty statistics, lower-confidence scores, and selected actions match the pre-save ensemble exactly on CPU

#### Scenario: Artifact binding differs
- **WHEN** any parent, corpus, member, bootstrap, schema, recipe, or tensor binding differs
- **THEN** loading fails before evaluation or policy execution

### Requirement: Fixed untouched-holdout decision

The system SHALL keep the registered evaluation corpus out of fitting and rule
selection and SHALL compare the ensemble against the committed prior
single-residual holdout metrics using fixed conditions.

#### Scenario: Offline conditions pass
- **WHEN** the ensemble makes at least 30 interventions, intervention precision is at least 0.65, mean selected true advantage exceeds 0.12269661575555801, mean policy regret is below 3.2472479343414307, and illegal and forbidden selection counts are zero
- **THEN** the recipe may enter one separately registered fresh LightSTS gate

#### Scenario: Any offline condition fails
- **WHEN** any registered provenance, coverage, precision, value, regret, legality, or safety condition fails
- **THEN** the system closes the recipe without fitting another member, changing a threshold or confidence multiplier, or running a fresh simulator gate

### Requirement: At-most-once fresh simulator decision

The system SHALL run at most one seed-disjoint matched LightSTS comparison only
after offline conditions pass and SHALL keep the result development-only.

#### Scenario: Fresh simulator conditions pass
- **WHEN** candidate-only victories are at least control-only victories, paired mean reward and HP deltas are non-negative, no nonterminal profile is excluded, at least one intervention occurs, and no forbidden intervention occurs
- **THEN** the candidate may be retained for separately registered real-game validation but is not authorized for production loading or promotion

#### Scenario: Fresh simulator condition fails
- **WHEN** any registered fresh simulator condition fails
- **THEN** the recipe closes without retry, seed replacement, retraining, or parameter sweep
