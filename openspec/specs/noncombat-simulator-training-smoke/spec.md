# noncombat-simulator-training-smoke Specification

## Purpose

Define one provenance-bound, deterministic, offline-only simulator training
smoke and its strict separation from formal training, live use, and promotion.

## Requirements

### Requirement: Immutable Simulator Smoke Registration
The system SHALL require one checked-in registration that binds every input and limit before a simulator-training smoke can execute.

#### Scenario: Complete registration is accepted
- **WHEN** the smoke input binds the adapter fit input and report, physical simulator source, submodules, adapter source and commit, native module, runtime/build identities, feature and algorithm versions, reward constants, optimizer values, exact train and holdout seeds, bootstrap settings, and resource bounds
- **THEN** the runner SHALL validate every bound identity before constructing an environment
- **AND** it SHALL record the registration hash in every published artifact

#### Scenario: Registered identity or value drifts
- **WHEN** a source, module, dependency, artifact, algorithm, feature, reward, optimizer, seed, evaluation, or limit value differs from the registration
- **THEN** the runner SHALL fail closed before training
- **AND** it SHALL NOT reuse a prior fit or smoke verdict

#### Scenario: Train and holdout seeds overlap
- **WHEN** any seed appears in both registered cohorts or either cohort contains duplicates
- **THEN** registration validation SHALL fail
- **AND** no rollout SHALL start

### Requirement: Leakage-Controlled Candidate Policy
The smoke policy SHALL score only adapter-reported candidates from a versioned simulator feature view that excludes direct seed, terminal, and provenance leakage.

#### Scenario: Policy features are projected
- **WHEN** a simulator state and candidate are converted to model features
- **THEN** the projection SHALL remove seed, outcome, provenance, baseline history, and terminal-label fields
- **AND** identical retained state/candidate values SHALL produce identical feature bytes

#### Scenario: Policy selects an action
- **WHEN** the policy acts at a route, shop, event, or card-reward decision
- **THEN** its probability distribution SHALL contain exactly the unique adapter-reported candidates
- **AND** the selected action SHALL be legal in that state

#### Scenario: Candidate set is ambiguous or unsupported
- **WHEN** candidate identities are empty, duplicated, changed after scoring, or rejected by a fresh environment clone
- **THEN** the episode and smoke SHALL fail closed
- **AND** the runner SHALL NOT synthesize a fallback action

### Requirement: Training-Only Progress Return
The smoke SHALL use only the registered simulator floor-progress and terminal-victory reward, and SHALL keep that reward separate from every live evidence contract.

#### Scenario: Transition reward is computed
- **WHEN** a simulator transition advances from one target decision to the next or terminates
- **THEN** reward SHALL equal non-negative floor advancement capped at floor 57 and divided by 57, plus one only for a simulator terminal victory
- **AND** return-to-go SHALL use discount 1.0

#### Scenario: Auxiliary evidence is available
- **WHEN** Current labels, Bottled labels, live outcomes, behavior propensities, HP, gold, deck heuristics, or OPE values are present elsewhere
- **THEN** none of those values SHALL enter the smoke reward
- **AND** the report SHALL label its return as simulator-training-only

### Requirement: Bounded Candidate-Masked Policy Gradient
The system SHALL expose a closed CPU-only REINFORCE smoke with fixed architecture and optimizer behavior rather than a general formal-training entry point.

#### Scenario: Registered training executes
- **WHEN** the smoke runs with its accepted registration
- **THEN** it SHALL initialize the registered candidate ranker from the registered model seed, sample only legal candidates, compute standardized return-to-go per pass, and perform the registered finite Adam updates
- **AND** it SHALL NOT load a Current, Bottled, live, or production checkpoint

#### Scenario: Hard bound is reached
- **WHEN** an episode, update, total-episode, or wall-time bound would be exceeded
- **THEN** the smoke SHALL stop with a bound blocker
- **AND** it SHALL NOT publish a passing structural verdict

#### Scenario: Numerical training state is invalid
- **WHEN** a probability, return, loss, gradient, or model tensor is non-finite
- **THEN** training SHALL stop and report the exact numerical blocker

### Requirement: Frozen Paired Holdout Evaluation
The system SHALL compare the frozen initial and trained greedy policies on the same disjoint, untouched holdout seeds without selecting or rerunning a favorable cohort.

#### Scenario: Holdout evaluation completes
- **WHEN** both policies finish the registered holdout cohort
- **THEN** the report SHALL record paired per-seed terminal floors, outcomes, decision counts, category coverage, candidate legality, and differences
- **AND** neither policy SHALL update from holdout transitions

#### Scenario: Holdout signal is calculated
- **WHEN** paired holdout rows are complete
- **THEN** the evaluator SHALL compute the registered deterministic percentile-bootstrap confidence interval for mean paired terminal-floor improvement
- **AND** it SHALL classify quality as `holdout_signal` only when the lower bound is greater than zero

#### Scenario: Positive mean lacks confidence
- **WHEN** mean paired improvement is positive but the registered confidence-interval lower bound is not greater than zero
- **THEN** the quality verdict SHALL be `quality_not_demonstrated`
- **AND** the runner SHALL NOT tune or rerun within this change

### Requirement: Deterministic Smoke Reproduction
The published smoke SHALL be reproduced once from the identical registration before its structural pipeline can be classified as demonstrated.

#### Scenario: Native module and PyTorch initialize on Windows
- **WHEN** the smoke CLI starts with the registered native module and MinGW DLL directory
- **THEN** it SHALL load and validate the native adapter before importing PyTorch
- **AND** a fresh-process integration check SHALL prove both runtimes coexist

#### Scenario: Same-input replay matches
- **WHEN** primary and replay executions use the same registered environment and runtime identities
- **THEN** canonical model tensors, selected actions, metrics, manifests, and report bytes SHALL match exactly
- **AND** noncanonical measured timing SHALL be excluded from the byte-identity comparison

#### Scenario: Same-input replay differs
- **WHEN** any canonical training or evaluation artifact differs
- **THEN** the structural verdict SHALL be `blocked`
- **AND** the differing artifact and field SHALL be reported

### Requirement: Fail-Closed Verdict And Authority
The smoke SHALL publish structural and quality verdicts separately and SHALL grant no formal, live, OPE, qualification, or promotion authority.

#### Scenario: Structural checks pass without quality signal
- **WHEN** provenance, bounds, legality, four-category coverage, terminal outcomes, seed isolation, atomic publication, and deterministic replay pass but the holdout signal gate does not
- **THEN** the verdict SHALL be `pipeline_demonstrated_quality_not_demonstrated`
- **AND** every downstream authority flag SHALL remain false

#### Scenario: Structural checks and quality signal pass
- **WHEN** every structural check passes and the registered holdout signal gate passes
- **THEN** the verdict SHALL be `pipeline_demonstrated_with_holdout_signal`
- **AND** only a separate reviewed proposal for the next offline phase MAY be considered

#### Scenario: Structural prerequisite fails
- **WHEN** any required structural check fails
- **THEN** the verdict SHALL be `blocked`
- **AND** no alternate parameter, cohort, or retry SHALL be selected under this change

### Requirement: Offline Atomic Artifact Isolation
The smoke SHALL publish hash-closed artifacts only to an explicit offline directory outside production checkpoint and model discovery.

#### Scenario: Publication succeeds
- **WHEN** a primary execution and reproduction pass their required checks
- **THEN** the system SHALL atomically publish the canonical model, trajectory summary, metrics, report, and manifest
- **AND** the manifest SHALL mark formal RL, live loading, gameplay, OPE, qualification, and promotion authority false

#### Scenario: Publication fails
- **WHEN** any artifact write, hash, replacement, or manifest validation fails
- **THEN** the complete prior managed artifact set SHALL remain byte-identical
- **AND** no temporary or partially published model SHALL enter live discovery

### Requirement: Canonical Smoke Model Is A Frozen Evaluation Candidate
The completed simulator-training smoke SHALL permit its canonical final model and exact seeded initialization to be consumed only as immutable inputs to a separately reviewed offline policy-validity study.

#### Scenario: Policy-validity study binds the smoke
- **WHEN** an accepted policy-validity registration references the smoke model
- **THEN** it SHALL bind the smoke registration, model, trajectories, manifest, implementation identity, feature version, model seed, and canonical hashes
- **AND** it SHALL validate exact published action and policy-input compatibility before new evaluation

#### Scenario: Prior smoke holdout is replayed for compatibility
- **WHEN** a bounded subset of smoke holdout seeds verifies adapter and policy identity
- **THEN** those rows SHALL be used only as a byte-exact compatibility gate
- **AND** their outcomes SHALL NOT enter policy selection, a new quality estimate, or promotion evidence

#### Scenario: Frozen candidate would change
- **WHEN** loading, feature projection, adapter semantics, or evaluation would alter the canonical model or its published compatible actions
- **THEN** the policy-validity study SHALL block before fresh seeds
- **AND** it SHALL NOT retrain, translate, or repair the frozen model in place
