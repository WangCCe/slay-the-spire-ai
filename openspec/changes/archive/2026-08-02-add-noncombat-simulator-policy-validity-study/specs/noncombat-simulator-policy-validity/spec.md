## ADDED Requirements

### Requirement: Immutable Policy Validity Registration
The system SHALL require one checked-in registration that binds every frozen input, identity, cohort, metric, and resource limit before a simulator policy-validity study can execute.

#### Scenario: Complete registration is accepted
- **WHEN** the study input binds the canonical smoke registration, model, trajectories, manifest, refreshed adapter fit, simulator and adapter build identities, evaluator implementation, runtime, excluded baselines, exact policy order, compatibility seeds, fresh seeds, bootstrap settings, and finite limits
- **THEN** the evaluator SHALL validate every identity before constructing a fresh-cohort environment
- **AND** every canonical artifact SHALL record the registration hash

#### Scenario: Registered input or identity drifts
- **WHEN** any bound source, module, model, artifact, runtime, policy, seed, metric, threshold, or limit differs from the registration
- **THEN** the study SHALL fail closed before fresh evaluation
- **AND** it SHALL NOT substitute another model, cohort, or value

#### Scenario: Fresh cohort is not fresh
- **WHEN** a fresh seed is duplicated or overlaps any registered fit, training, smoke-holdout, or compatibility seed
- **THEN** registration validation SHALL fail
- **AND** no fresh policy rollout SHALL start

### Requirement: Frozen Candidate And Replication Policies
The evaluator SHALL compare the canonical smoke-trained ranker and its exact seeded initialization without updating, selecting, or rewriting either policy.

#### Scenario: Frozen trained model loads
- **WHEN** the canonical model artifact passes its registered schema and hash checks
- **THEN** the evaluator SHALL reconstruct exactly its registered architecture and tensor values on CPU
- **AND** its canonical model hash SHALL remain unchanged before and after all rollouts

#### Scenario: Seeded initialization is reconstructed
- **WHEN** the replication policy is created
- **THEN** it SHALL use the registered architecture, input dimension, model seed, runtime settings, and feature version from the smoke
- **AND** its canonical model hash SHALL remain unchanged before and after all rollouts

#### Scenario: Evaluation attempts to train or select
- **WHEN** a code path enables gradients, optimizer updates, checkpoint discovery, model selection, or alternate-policy fallback
- **THEN** the evaluator SHALL block before fresh rollout
- **AND** no modified model artifact SHALL be published

### Requirement: Published Smoke Compatibility Gate
The evaluator SHALL prove exact frozen-policy compatibility with published smoke trajectories before evaluating untouched seeds.

#### Scenario: Compatibility subset matches
- **WHEN** the initial and trained policies replay registered smoke-holdout compatibility seeds under the refreshed adapter
- **THEN** every policy-input hash and selected action id SHALL equal the corresponding published smoke trajectory
- **AND** those replayed outcomes SHALL be excluded from policy-validity metrics

#### Scenario: Compatibility subset differs
- **WHEN** any policy-input hash, action id, model hash, candidate identity, or terminal sequence differs from the bound smoke evidence
- **THEN** the study SHALL report the first exact mismatch and block
- **AND** it SHALL NOT evaluate a fresh seed or redefine the frozen model

### Requirement: Three-Policy Fresh-Cohort Evaluation
The system SHALL evaluate the frozen trained ranker, exact seeded initialization, and native SimpleAgent target policy greedily in independent environments on the same registered fresh seeds.

#### Scenario: Fresh evaluation completes
- **WHEN** all three policies run the registered cohort
- **THEN** the artifacts SHALL contain one terminal row per policy and seed with floor, outcome, decision count, category coverage, selected actions, policy-input or native-action provenance, and legality
- **AND** no policy SHALL update from any transition

#### Scenario: Native baseline acts
- **WHEN** the SimpleAgent baseline reaches a target decision on its own baseline-following trajectory
- **THEN** it SHALL select exactly the adapter candidate returned by the native baseline query
- **AND** zero, duplicate, unreported, or rejected selections SHALL block the study

#### Scenario: Resource bound would be exceeded
- **WHEN** an episode, decision, policy-episode, total-episode, or wall-time limit would be exceeded
- **THEN** the execution SHALL stop with an exact bound blocker
- **AND** it SHALL NOT publish a structurally valid verdict

### Requirement: Pre-Registered Paired Baseline Signal
The evaluator SHALL treat trained-versus-SimpleAgent paired terminal-floor difference as its sole primary quality estimand and trained-versus-initial difference as secondary replication evidence.

#### Scenario: Primary baseline signal is calculated
- **WHEN** all registered paired terminal rows are complete
- **THEN** the evaluator SHALL compute the registered deterministic percentile-bootstrap confidence interval for mean trained-minus-SimpleAgent terminal floor
- **AND** baseline signal SHALL be demonstrated only when the interval lower bound is greater than zero

#### Scenario: Mean improvement lacks confidence
- **WHEN** the trained-minus-SimpleAgent mean is positive but the registered interval lower bound is not greater than zero
- **THEN** the quality verdict SHALL state that baseline signal was not demonstrated
- **AND** the evaluator SHALL NOT tune, extend, or rerun another cohort under this change

#### Scenario: Replication control is favorable
- **WHEN** trained terminal floor exceeds the seeded initialization with a positive confidence-interval lower bound
- **THEN** the result SHALL be reported as secondary smoke-signal replication only
- **AND** it SHALL NOT replace or override the SimpleAgent primary gate

#### Scenario: Victory observations are reported
- **WHEN** terminal outcomes are summarized
- **THEN** per-policy victory counts and paired victory differences SHALL be separate from the floor gate
- **AND** zero trained victories SHALL remain an explicit limitation regardless of floor signal

### Requirement: Deterministic Policy Validity Reproduction
The registered study SHALL run once for publication and once with identical input for canonical reproduction.

#### Scenario: Same-input reproduction matches
- **WHEN** primary and replay executions use the same registered identities and input
- **THEN** policy trajectories, paired metrics, model hashes, manifest content, and report bytes SHALL match exactly
- **AND** measured timing SHALL be excluded from canonical comparison

#### Scenario: Same-input reproduction differs
- **WHEN** any canonical field or artifact differs
- **THEN** structural validity SHALL be blocked
- **AND** the first differing artifact and field SHALL be reported

### Requirement: Fail-Closed Verdict And Offline Authority
The study SHALL classify structural validity separately from baseline signal and SHALL grant no training, live, OPE, qualification, or promotion authority.

#### Scenario: Structure passes and baseline signal passes
- **WHEN** all structural checks and the primary lower-bound gate pass
- **THEN** the verdict SHALL record a valid study with baseline-relevant simulator floor signal
- **AND** only a separately reviewed offline proposal MAY use that result

#### Scenario: Structure passes without baseline signal
- **WHEN** all structural checks pass but the primary lower-bound gate does not
- **THEN** the verdict SHALL record a valid study without demonstrated baseline signal
- **AND** no alternative cohort, model, metric, or retry SHALL be selected under this change

#### Scenario: Structural prerequisite fails
- **WHEN** provenance, compatibility, seed isolation, legality, terminal completion, aggregate category coverage, bounds, model immutability, or reproduction fails
- **THEN** the verdict SHALL be `blocked`
- **AND** all downstream authority flags SHALL remain false

### Requirement: Atomic Simulator-Only Artifacts
The evaluator SHALL publish hash-closed canonical artifacts only to an explicit offline report directory outside model and checkpoint discovery.

#### Scenario: Publication succeeds
- **WHEN** primary execution, reproduction, and artifact validation complete
- **THEN** the system SHALL atomically publish canonical trajectories, metrics, report, and manifest plus a separate noncanonical execution journal
- **AND** the manifest SHALL mark formal RL, simulator training, live gameplay, live loading, live study, OPE, qualification, and promotion authority false

#### Scenario: Publication fails
- **WHEN** any artifact write, hash, replacement, or manifest validation fails
- **THEN** the prior complete managed artifact set SHALL remain byte-identical
- **AND** no partial policy-validity artifact SHALL enter model discovery
