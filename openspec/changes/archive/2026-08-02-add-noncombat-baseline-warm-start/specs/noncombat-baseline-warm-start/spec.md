## ADDED Requirements

### Requirement: Immutable Baseline Warm-Start Registration
The system SHALL require one checked-in registration that binds every source identity, implementation, model value, cohort, metric, threshold, exclusion, and resource limit before native demonstration collection can begin.

#### Scenario: Complete registration is accepted
- **WHEN** the input binds simulator, adapter, module, runtime, feature, model, optimizer, train, validation, final-test, bootstrap, threshold, prior-seed exclusion, and finite execution identities
- **THEN** the runner SHALL validate every bound value before constructing an environment for any registered seed
- **AND** every canonical artifact SHALL record the registration hash

#### Scenario: Registered identity or value drifts
- **WHEN** any bound source, module, implementation, runtime, model, optimizer, seed, metric, threshold, or limit differs
- **THEN** the study SHALL fail closed before registered collection
- **AND** it SHALL NOT substitute an alternate identity, cohort, configuration, or value

#### Scenario: Cohort isolation fails
- **WHEN** train, validation, or final-test seeds are duplicated, overlap each other, or overlap any registered prior fit, smoke, compatibility, or policy-validity cohort
- **THEN** registration validation SHALL fail
- **AND** no registered native rollout SHALL start

### Requirement: Native Baseline Demonstration Dataset
The runner SHALL collect deterministic baseline-following SimpleAgent demonstrations with complete legal candidate sets for route, shop, event, and card-reward decisions.

#### Scenario: Demonstration row is collected
- **WHEN** a baseline-following environment reaches a target decision
- **THEN** the row SHALL contain cohort, seed, decision index, category, canonical source state, complete ordered candidates, exactly mapped native target action, per-candidate policy views and hashes, and adapter provenance
- **AND** applying the target SHALL produce a legal successor or terminal outcome

#### Scenario: Demonstration collection repeats
- **WHEN** the same registered cohort is collected under identical identities
- **THEN** canonical rows, action sequences, successor summaries, and terminal outcomes SHALL match byte-for-byte
- **AND** measured timing SHALL be excluded from canonical identity

#### Scenario: Native target is invalid
- **WHEN** the target query mutates its source, maps to zero or multiple candidates, returns an unreported action, or produces a rejected transition
- **THEN** collection SHALL block with the exact seed and decision
- **AND** no fallback label or action SHALL be synthesized

### Requirement: Candidate-Masked Supervised Warm Start
The system SHALL train exactly one preregistered candidate-scoring model from native target actions using deterministic category-balanced supervised learning without reward or policy-gradient updates.

#### Scenario: Registered training executes
- **WHEN** the complete train demonstration dataset passes schema, provenance, legality, and category checks
- **THEN** the model SHALL initialize from the registered seed, score every reported candidate, optimize candidate-masked cross entropy under the registered fixed schedule, and remain CPU-only
- **AND** category losses SHALL receive equal aggregate weight regardless of row frequency

#### Scenario: Candidate action space is preserved
- **WHEN** the trained model selects an action
- **THEN** it SHALL score the complete current adapter candidate set and select only from that set
- **AND** the native teacher label SHALL NOT be hard-coded, filtered into the action set, or used as reward

#### Scenario: Training state is invalid or bounded
- **WHEN** a dataset, probability, loss, gradient, tensor, epoch, decision, episode, or wall-time bound is invalid or exceeded
- **THEN** training SHALL stop with an exact blocker
- **AND** no passing model artifact SHALL be published

### Requirement: Validation Is A Stop Gate Not A Selection Set
The v1 study SHALL evaluate one fixed model configuration on a preregistered validation cohort and SHALL NOT use validation or final-test observations for hyperparameter or model selection.

#### Scenario: Validation gate passes
- **WHEN** the frozen model satisfies every registered structural, action-fit, category, and rollout threshold on validation
- **THEN** its canonical model hash SHALL be frozen before final test
- **AND** the runner MAY proceed to the registered final-test cohort without changing any value

#### Scenario: Validation gate fails
- **WHEN** any registered validation threshold or structural check fails
- **THEN** the runner SHALL publish the validation result and leave all final-test seeds untouched
- **AND** it SHALL NOT train another model, alter a threshold, or use an alternate cohort under this change

### Requirement: Untouched Baseline Parity Evaluation
The runner SHALL evaluate teacher-state fit and independent rollout competence on the registered final-test cohort while treating paired candidate-minus-SimpleAgent terminal floor as the primary policy-floor evidence.

#### Scenario: Teacher-state fit is evaluated
- **WHEN** final-test baseline demonstrations are complete
- **THEN** the report SHALL include overall, macro-category, and per-category exact action agreement, cross entropy, row counts, and legality
- **AND** teacher-state fit SHALL NOT override a failed independent rollout gate

#### Scenario: Independent rollouts complete
- **WHEN** the frozen candidate and native SimpleAgent run in separate environments on each final-test seed
- **THEN** the artifacts SHALL record paired floors, outcomes, decision counts, category coverage, action sequences, and candidate legality
- **AND** neither policy SHALL update from final-test transitions

#### Scenario: Baseline non-inferiority is classified
- **WHEN** every paired final-test row is complete
- **THEN** the evaluator SHALL compute the preregistered deterministic confidence interval for mean candidate-minus-SimpleAgent terminal floor and compare it with the bound non-inferiority margin and mean-deficit limit
- **AND** baseline parity SHALL be demonstrated only when all registered teacher-fit and rollout gates pass

### Requirement: Deterministic Warm-Start Reproduction
The registered study SHALL run one primary execution and one identical replay from the same immutable registration.

#### Scenario: Primary and replay match
- **WHEN** both executions complete under identical identities
- **THEN** demonstration datasets, model tensors, selected actions, trajectories, metrics, report, and manifest SHALL match canonically
- **AND** timing SHALL remain only in a separate noncanonical journal

#### Scenario: Primary and replay differ
- **WHEN** any canonical field or managed artifact differs
- **THEN** the verdict SHALL be blocked and report the first exact difference
- **AND** no alternate retry SHALL be selected under this change

### Requirement: Atomic Artifacts And No Downstream Authority
The runner SHALL atomically publish hash-closed simulator-only evidence outside checkpoint and production-model discovery and SHALL grant no formal or live authority.

#### Scenario: Publication succeeds
- **WHEN** the primary execution, replay, and artifact validation complete
- **THEN** the managed set SHALL contain canonical demonstrations, model, trajectories, metrics, report, and manifest plus a separate execution journal
- **AND** the manifest SHALL mark formal RL, simulator RL training, live gameplay, live loading, live study, OPE, qualification, and promotion authority false

#### Scenario: Structural or quality gate fails
- **WHEN** provenance, isolation, determinism, legality, coverage, bounds, model immutability, validation, teacher fit, rollout non-inferiority, or reproduction fails
- **THEN** the report SHALL distinguish `blocked` from `baseline_floor_not_demonstrated`
- **AND** no tuning, formal RL proposal, live execution, or policy promotion SHALL be authorized by this result

#### Scenario: Baseline floor is demonstrated
- **WHEN** every structural, validation, teacher-fit, rollout, and reproduction gate passes
- **THEN** the result SHALL authorize only consideration of a separate bounded formal-RL proposal
- **AND** all training execution, live, OPE, qualification, and promotion authority flags SHALL remain false
