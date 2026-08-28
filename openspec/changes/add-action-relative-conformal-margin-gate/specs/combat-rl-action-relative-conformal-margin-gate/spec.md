## ADDED Requirements

### Requirement: Seed-disjoint internal calibration split

The system SHALL assign training-corpus rows to fixed fit seeds
`262000..262191` or calibration seeds `262192..262255`, SHALL preserve tensor and
metadata alignment, and SHALL exclude every calibration row from bootstrap and
optimizer access.

#### Scenario: Split validates
- **WHEN** every retained training row has one registered seed and the fit and calibration seed sets are disjoint
- **THEN** the system publishes row, pair, seed, and action-family support for both partitions before fitting

#### Scenario: Split identity or support differs
- **WHEN** a row is outside the registered seed sets, partitions overlap, tensor alignment changes, or either calibration action family has fewer than 100 pairs
- **THEN** the recipe closes before fitting or holdout access

### Requirement: Fixed action-family conformal correction

The system SHALL compute raw ensemble score as member mean minus one sample
standard deviation and SHALL subtract a fixed 90% one-sided finite-sample
conformal correction separately for card actions `0..59` and potion actions
`60..89`.

#### Scenario: Family correction is calibrated
- **WHEN** all five members finish fitting on fit rows
- **THEN** each family correction is the higher order statistic at rank `ceil((n + 1) * 0.9)` of calibration `raw_score - true_advantage`, clamped to at least zero

#### Scenario: Candidate is scored
- **WHEN** a supported allowed card or potion alternative is evaluated
- **THEN** its calibrated lower margin equals raw ensemble score minus the immutable registered family correction

#### Scenario: Unsupported family is encountered
- **WHEN** an alternative is outside card actions `0..59` and potion actions `60..89`
- **THEN** it cannot be a conformal intervention

### Requirement: Calibrated abstaining selection

The system SHALL rank supported allowed alternatives by calibrated lower margin
and SHALL intervene only when the maximum margin is at least 0.5.

#### Scenario: Calibrated margin clears threshold
- **WHEN** the maximum allowed calibrated lower margin is at least 0.5
- **THEN** the policy selects that alternative and records raw mean, sample standard deviation, family correction, calibrated margin, and constraints

#### Scenario: Calibrated margin abstains
- **WHEN** every allowed calibrated lower margin is below 0.5
- **THEN** the exact guard action is preserved

### Requirement: Source-bound conformal artifact

The system SHALL bind the refitted five-member ensemble, fit/calibration seed
sets, partition identities, action-family support, conformal alpha, family
corrections, parent and corpus hashes, recipe, telemetry, and development-only
authority in one artifact.

#### Scenario: Artifact roundtrip matches
- **WHEN** the artifact is loaded against exact registered bindings
- **THEN** raw statistics, calibrated margins, selections, and abstentions match exactly on CPU

#### Scenario: Binding differs
- **WHEN** any source, parent, corpus, split, member, bootstrap, correction, family, recipe, or tensor binding differs
- **THEN** loading fails before evaluation or policy execution

### Requirement: Fixed holdout and fresh-simulator decisions

The system SHALL load the existing evaluation corpus only after fit and
calibration complete and SHALL apply all registered conditions without sweep or
retry.

#### Scenario: Offline conditions pass
- **WHEN** interventions are at least 30, precision is at least 0.65, mean selected true advantage exceeds 0.12269661575555801, mean policy regret is below 3.2472479343414307, no selected true advantage is below `-0.5`, and illegal and forbidden selections are zero
- **THEN** the recipe may enter one separately registered fresh matched LightSTS gate

#### Scenario: Offline condition fails
- **WHEN** any support, calibration, coverage, precision, value, regret, tail-safety, legality, or provenance condition fails
- **THEN** the recipe closes without LightSTS, retraining, seed replacement, alpha change, family change, threshold change, or sweep

#### Scenario: Registered execution fails before holdout evaluation
- **WHEN** a deterministic runner-contract defect stops the registered execution before any holdout metric is computed
- **THEN** the system preserves the failed registration and failure evidence, SHALL NOT rerun it, and MAY execute one replacement registration bound to a tested source repair with unchanged inputs, recipe, seed partitions, alpha, threshold, and gates

#### Scenario: Fresh simulator conditions pass
- **WHEN** the separately registered fresh gate has candidate-only victories at least control-only victories, non-negative paired reward and HP deltas, zero excluded nonterminal profiles, positive interventions, and zero forbidden interventions
- **THEN** the candidate may be retained for a later separately registered real-game gate but not production loading or promotion

#### Scenario: Fresh simulator condition fails
- **WHEN** any registered fresh simulator condition fails
- **THEN** the recipe closes without retry, retraining, or parameter change
