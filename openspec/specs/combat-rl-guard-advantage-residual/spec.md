# combat-rl-guard-advantage-residual Specification

## Purpose

Define source-bound offline evidence and safety contracts for learning and
evaluating a development-only combat residual relative to the guarded baseline.

## Requirements

### Requirement: Source-bound guard-intervention corpus

The system SHALL generate a bounded LightSTS corpus from a fixed native module,
frozen parent checkpoint, item metadata, seed partitions, and recipe. It SHALL
retain only supported states where the raw parent proposes `EndTurn`, the
deployment guard proxy selects a legal card action, and a distinct legal
alternative action exists.

#### Scenario: Eligible state is retained
- **WHEN** a source-bound profile reaches a supported state where the frozen parent `EndTurn` is replaced by the guard and another legal action exists
- **THEN** the system records the encoded state, raw parent action, guarded baseline action, canonical alternatives, seed, profile, encounter, and provenance

#### Scenario: Ineligible state is skipped
- **WHEN** the parent does not propose `EndTurn`, the guard does not replace it, or no distinct legal alternative exists
- **THEN** the system excludes the state from advantage labeling and increments an explicit reason counter

### Requirement: Paired action return labels

The system SHALL clone one common environment per canonical eligible first
action, execute that action, continue every branch with the same frozen guarded
policy for the fixed horizon or until terminal, and calculate discounted return
using the existing native reward definition.

#### Scenario: Complete paired state is labeled
- **WHEN** all cloned branches remain supported and settle within the registered bound
- **THEN** the system records each branch return, the guard-relative advantage, the deterministic best target action, and whether advantage meets the fixed positive margin

#### Scenario: One branch is unsupported
- **WHEN** any required branch becomes unsupported, fails settlement, or exceeds the registered decision bound
- **THEN** the system excludes the entire paired state and reports the exclusion reason without using a partial label

### Requirement: Behavior-equivalent action canonicalization

The system SHALL treat actions using duplicate card or potion slots as one
behavior only when encoded item identity, card features, and target agree. It
SHALL use deterministic RL action index ordering to break remaining return
ties.

#### Scenario: Duplicate Strike slots agree
- **WHEN** two legal actions play encoded-identical `Strike` copies at the same target with equal card features
- **THEN** the system evaluates and counts them as one canonical behavior

#### Scenario: Upgrade or target differs
- **WHEN** item identity, encoded card features, or target differs
- **THEN** the system preserves the actions as distinct alternatives

### Requirement: Corpus sufficiency gate

The system MUST stop before fitting unless train and seed-disjoint evaluation
partitions both contain positive and negative labels, the training partition
contains at least 100 positive states, and positive training targets cover at
least three distinct canonical action identities.

#### Scenario: Corpus is sufficient
- **WHEN** every fixed coverage condition passes
- **THEN** the system may fit exactly the registered development residual recipe

#### Scenario: Corpus is insufficient
- **WHEN** any fixed coverage condition fails
- **THEN** the system publishes a no-go report and MUST NOT lower the margin, change seeds, extend the horizon, fit a model, or start gameplay in this change

### Requirement: Post-guard abstaining residual

The system SHALL keep the parent frozen and fit a development-only residual
whose inputs include frozen parent features, the guarded baseline action, and
the legal action mask. The residual SHALL default to the guarded action unless
its fixed hard gate opens, and its selected alternative SHALL be legal.

#### Scenario: Gate remains closed
- **WHEN** the residual gate probability is below the registered threshold
- **THEN** the selected action exactly preserves the guarded baseline action

#### Scenario: Gate opens
- **WHEN** the residual gate opens on a supported state
- **THEN** the system selects a legal canonical alternative and records guard action, residual action, score, advantage label, and final action

### Requirement: Fresh simulator policy gate

The system SHALL evaluate the frozen residual and guarded baseline on identical
fresh LightSTS seeds and profiles. It SHALL publish candidate-only and
control-only victories, paired reward and player-HP deltas, intervention count,
support exclusions, and all fixed gate results.

#### Scenario: Candidate passes every policy condition
- **WHEN** candidate-only victories are at least control-only victories, mean reward and mean HP deltas are non-negative, no nonterminal profiles are excluded, and at least one residual intervention occurs
- **THEN** the system may retain the recipe for a separately registered offline follow-up but SHALL NOT authorize gameplay, qualification, promotion, or production loading

#### Scenario: Candidate fails a policy condition
- **WHEN** any fixed policy condition fails
- **THEN** the system closes the recipe without a seed, horizon, threshold, architecture, or optimizer sweep and leaves production r16 unchanged

### Requirement: Offline authority boundary

The POC SHALL run on CPU without starting Slay the Spire or CommunicationMod,
loading a production checkpoint, writing a production checkpoint, or changing
live policy routing.

#### Scenario: POC completes or fails
- **WHEN** the corpus, fit, or evaluation terminates
- **THEN** every artifact records development-only authority and production r16 remains authoritative
