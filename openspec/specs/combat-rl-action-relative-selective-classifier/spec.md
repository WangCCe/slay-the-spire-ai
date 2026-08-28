# combat-rl-action-relative-selective-classifier Specification

## Purpose

Define the development-only pair classifier, calibration, source binding, and
fixed evidence gates used to evaluate selective card and potion interventions
relative to the production combat guard policy.

## Requirements

### Requirement: Supported pair-level return classes

The system SHALL classify each paired card or potion alternative relative to
the actual guard action as severe harm for advantage below `-0.5`, neutral for
advantage from `-0.5` inclusive to `0.5` exclusive, or beneficial for
advantage at least `0.5`.

#### Scenario: Supported alternatives are labeled

- **WHEN** a paired branch action is in card indices `0..59` or potion indices `60..89`
- **THEN** it receives exactly one class while preserving source-row, guard-action, candidate-action, return, and legality alignment

#### Scenario: Unsupported-only row is encountered

- **WHEN** a corpus row has no supported alternative after excluding EndTurn 90 and noncombat actions `91..132`
- **THEN** the system excludes that row from tensors and metadata together and reports the exclusion

### Requirement: Fixed selective classifier fit

The system SHALL fit one three-logit candidate classifier from frozen r16
latent state, guard identity, candidate identity, and legal action mask only on
seeds `262000..262191` with the registered deterministic recipe.

#### Scenario: Class-balanced fit executes

- **WHEN** every class and within-state beneficial-versus-nonbeneficial comparison has registered support
- **THEN** each update samples the registered count from every class and optimizes three-class cross entropy plus the fixed within-state ranking loss

#### Scenario: Fit provenance differs

- **WHEN** a fit row, class boundary, sample identity, source, parent, corpus, seed, architecture, optimizer, update budget, or loss binding differs
- **THEN** fitting or artifact loading fails before holdout access

### Requirement: Negative-class calibrated selection

The system SHALL compute candidate evidence as beneficial logit minus the
log-sum-exp of neutral and severe logits and SHALL derive one immutable
selection threshold from non-beneficial calibration pairs on seeds
`262192..262255`.

#### Scenario: Threshold is calibrated

- **WHEN** classifier fitting completes without accessing calibration rows
- **THEN** the threshold equals the finite-sample higher 95th percentile at rank `ceil((n + 1) * 0.95)` of non-beneficial calibration evidence

#### Scenario: Candidate clears the threshold

- **WHEN** the highest legal supported candidate evidence meets the calibrated threshold
- **THEN** the classifier selects that action and records logits, evidence, class prediction, threshold, guard identity, and constraints

#### Scenario: Candidate abstains

- **WHEN** every legal supported candidate evidence is below the calibrated threshold
- **THEN** the exact guard action is preserved

### Requirement: Source-bound selective artifact

The system SHALL bind classifier weights, frozen-parent identity, label
boundaries, fit and calibration seeds, row and sample identities, class
support, ranking support, calibrated threshold, recipe, telemetry, and
development-only authority in one artifact.

#### Scenario: Artifact roundtrip matches

- **WHEN** the artifact is loaded against exact registered bindings on CPU
- **THEN** class logits, evidence, selections, abstentions, and telemetry match exactly

#### Scenario: Artifact binding differs

- **WHEN** any source, parent, corpus, split, label, sample, classifier, threshold, recipe, or tensor binding differs
- **THEN** loading fails before evaluation or policy execution

### Requirement: Fixed offline and fresh-simulator decisions

The system SHALL load evaluation seeds `263000..263127` only after fitting and
calibration complete and SHALL apply all registered gates without sweep or
retry.

#### Scenario: Offline conditions pass

- **WHEN** interventions are at least 30, precision is at least 0.65, mean selected true advantage exceeds 0.18881003558635712, mean policy regret is below 3.1811342239379883, no selected advantage is below `-0.5`, and illegal and forbidden selections are zero
- **THEN** one separately registered fresh matched LightSTS gate may execute

#### Scenario: Offline condition fails

- **WHEN** any coverage, precision, value, regret, severe-harm, legality, provenance, or roundtrip condition fails
- **THEN** the recipe closes without LightSTS, retraining, seed replacement, threshold change, loss change, or sweep

#### Scenario: Fresh simulator conditions pass

- **WHEN** candidate-only victories are at least control-only victories, paired reward and HP deltas are non-negative, nonterminal exclusions are zero, interventions are positive, and forbidden interventions are zero
- **THEN** the candidate may be retained for a later separately registered real-game gate but not production loading or promotion

#### Scenario: Fresh simulator condition fails

- **WHEN** any registered fresh simulator condition fails
- **THEN** the recipe closes without retry, retraining, or parameter change

### Requirement: Optional direct item-semantic features

The development selective classifier SHALL optionally append direct candidate
and guard item embeddings, local card features, action family, and target
identity while preserving the existing feature contract when the option is
disabled.

#### Scenario: Item semantics are enabled

- **WHEN** a supported card or potion pair is scored with the item-semantic option enabled
- **THEN** candidate and guard slots map to their exact frozen item embedding, card-local features, family, and target without changing the frozen parent

#### Scenario: Existing artifact omits item semantics

- **WHEN** an existing selective-classifier artifact is loaded without the new config field
- **THEN** the option defaults to disabled and logits, evidence, selection, and abstention retain the original feature shape and behavior

### Requirement: Consumed-holdout development ablation

The system SHALL run at most one fixed item-semantic CPU ablation and SHALL
treat seeds `263000..263127` only as an already-consumed development
comparison.

#### Scenario: Fixed comparison passes

- **WHEN** interventions are at least 30, precision is at least `0.55`, severe harms are at most 5, mean selected advantage exceeds `0.17321939766407013`, mean regret is below `3.1967246532440186`, and integrity conditions pass
- **THEN** the result may justify a separately proposed fresh corpus but grants no evaluation, qualification, gameplay, or promotion authority

#### Scenario: Fixed comparison fails

- **WHEN** any registered comparison or integrity condition fails
- **THEN** the item-semantic recipe closes without retraining, tuning, native loading, fresh corpus generation, LightSTS execution, or gameplay
