## ADDED Requirements

### Requirement: Versioned Policy-Learning Dataset
The system SHALL build a versioned offline policy-learning dataset from canonical non-combat decision samples and SHALL preserve the source sample, candidate actions, label provenance, trajectory group, and input hashes needed to reproduce it.

#### Scenario: Eligible sample enters the dataset
- **WHEN** a complete decision sample has a unique trajectory group, behavior-policy provenance, available candidate actions, and a target label mapped to one candidate
- **THEN** the builder SHALL include it in the appropriate label-mode dataset
- **AND** the manifest SHALL record its source and schema version

#### Scenario: Unsupported sample remains auditable
- **WHEN** a sample lacks an unambiguous trajectory group, behavior provenance, candidates, or mapped target label
- **THEN** the builder SHALL exclude it from train/evaluation rows
- **AND** it SHALL count the exclusion by reason in the support report

### Requirement: Leakage-Free Trajectory Splits
The system SHALL assign complete trajectories, not individual decision rows, to deterministic train, validation, and test splits.

#### Scenario: No trajectory crosses splits
- **WHEN** a split manifest is generated
- **THEN** every `trajectory_group_id` SHALL appear in exactly one split
- **AND** all decisions from that trajectory SHALL use the same split

#### Scenario: Split generation is reproducible
- **WHEN** identical inputs, configuration, and split seed are processed twice
- **THEN** the ordered group assignments and split-manifest hash SHALL be identical

### Requirement: Action-Masked Candidate Ranker
The system SHALL train and evaluate a bounded offline model that scores only the normalized available candidates in each sample.

#### Scenario: Prediction is candidate-legal
- **WHEN** the model predicts an action for a sample
- **THEN** the predicted action id SHALL belong to that sample's available candidate set
- **AND** the evaluation report SHALL show 100 percent candidate legality

#### Scenario: Unmapped target is not trained
- **WHEN** a Current or Bottled target does not map to an available candidate
- **THEN** the trainer SHALL exclude that row rather than create a global fallback class
- **AND** the report SHALL count it as a target-mapping exclusion

### Requirement: Current And Bottled Label Isolation
The system SHALL train Current-imitation and Bottled-auxiliary modes as separate experiments with separate artifacts, counts, metrics, and limitations.

#### Scenario: Current imitation uses behavior labels
- **WHEN** Current-imitation mode builds its targets
- **THEN** it SHALL use only the action selected by the recorded behavior policy
- **AND** it SHALL NOT substitute a Bottled label or run outcome

#### Scenario: Bottled auxiliary uses qualified oracle labels
- **WHEN** Bottled-auxiliary mode builds its targets
- **THEN** it SHALL use only mapped native Bottled labels that satisfy the configured evidence and confidence gates
- **AND** it SHALL NOT treat the label as reward or policy-promotion truth

### Requirement: Reproducible Bounded Training
The system SHALL make the pilot reproducible and bounded through explicit seeds, deterministic input ordering, CPU-compatible execution, bounded epochs, and versioned configuration.

#### Scenario: Identical pilot run reproduces metrics
- **WHEN** the same dataset, split manifest, model configuration, and seed are run in the same supported environment
- **THEN** predictions and reported metrics SHALL match within the declared numerical tolerance

#### Scenario: Training cannot run unbounded
- **WHEN** the trainer starts
- **THEN** it SHALL require finite epoch and output-directory settings
- **AND** it SHALL record the effective bounds in the artifact manifest

### Requirement: Offline Evaluation And Support Gate
The system SHALL compare pilot models with trivial and reference baselines and SHALL separate structural pipeline readiness from policy or RL readiness.

#### Scenario: Report contains held-out evidence
- **WHEN** a pilot experiment completes
- **THEN** the report SHALL include train, validation, and test trajectory counts; per-category coverage; target-mapping coverage; candidate legality; top-1 agreement; loss; calibration; and baseline comparisons
- **AND** all held-out metrics SHALL be computed only from held-out trajectory groups

#### Scenario: Insufficient trajectory support blocks claims
- **WHEN** fewer than 10 eligible trajectory groups exist, any required split is empty, or a category lacks two train groups and one held-out group
- **THEN** the support gate SHALL mark the affected experiment or category blocked
- **AND** it SHALL still emit a diagnostic report without claiming learned-policy quality

#### Scenario: Off-policy evaluation is unsupported
- **WHEN** behavior action probabilities are unknown or the logged data lacks alternative-action support
- **THEN** the report SHALL mark off-policy evaluation unsupported
- **AND** it SHALL NOT report causal outcome uplift

### Requirement: Offline Artifact Isolation
The system SHALL keep policy-learning code and artifacts outside live gameplay and existing checkpoint discovery paths.

#### Scenario: Pilot leaves live behavior unchanged
- **WHEN** dataset building, training, or evaluation succeeds or fails
- **THEN** it SHALL NOT modify CommunicationMod configuration, live policy code paths, launcher defaults, or production checkpoints

#### Scenario: Pilot artifact is not promotion-ready
- **WHEN** a pilot model artifact is written
- **THEN** its manifest SHALL mark live-policy promotion and formal non-combat RL readiness false
- **AND** no live agent SHALL auto-load it
