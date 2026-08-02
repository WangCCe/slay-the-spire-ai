## MODIFIED Requirements

### Requirement: Formal Non-Combat RL Training Guard
The system SHALL prevent formal non-combat RL training from being treated as ready until the decision loop is fully defined and verified. It SHALL allow a bounded offline supervised policy-learning pilot only when that pilot remains isolated from live gameplay, reward optimization, and policy promotion. A credible simulator baseline floor SHALL be necessary but not sufficient for a later formal-RL proposal.

#### Scenario: Combat RL smoke remains allowed
- **WHEN** a developer runs a small combat RL smoke training or dry-run command
- **THEN** the report may use it as training-pipeline health evidence without marking formal non-combat RL training as ready

#### Scenario: Non-combat training remains blocked before readiness
- **WHEN** the state schema, action schema, reward definition, or evaluation gate lacks tests and report support
- **THEN** the system reports formal non-combat RL training as blocked

#### Scenario: Supervised pilot does not unlock formal RL
- **WHEN** an offline Current-imitation or Bottled-auxiliary pilot trains and evaluates successfully
- **THEN** the system SHALL continue to report formal non-combat RL and live-policy promotion as blocked
- **AND** the pilot result SHALL be treated only as training-pipeline and representation evidence

#### Scenario: Baseline warm start lacks a credible floor
- **WHEN** a baseline-anchored warm-start study is blocked or fails its preregistered untouched rollout gate
- **THEN** formal non-combat RL SHALL remain blocked on baseline-policy readiness
- **AND** a positive training loss or teacher-agreement result SHALL NOT override that blocker

#### Scenario: Baseline warm start demonstrates a credible floor
- **WHEN** a baseline-anchored warm-start study passes its structural, untouched action-fit, rollout non-inferiority, and reproduction gates
- **THEN** the result MAY support a separate proposal for bounded formal non-combat RL
- **AND** it SHALL NOT itself authorize training, live loading, qualification, or promotion

### Requirement: Simulator Transitions Remain Separate Evidence
The non-combat decision loop SHALL distinguish simulator-generated transitions, demonstrations, rewards, returns, models, baseline comparisons, and evaluation metrics from live trace samples, known-propensity exploration evidence, and matched `.run` outcomes.

#### Scenario: Simulator transition is exported
- **WHEN** the offline adapter exports a route, shop, event, or card-reward transition
- **THEN** the row SHALL use a separate versioned schema and `source_type=sts_lightspeed_simulation`
- **AND** it SHALL preserve simulator and baseline provenance without claiming a live outcome join

#### Scenario: Simulator data enters readiness reporting
- **WHEN** a readiness report includes simulator transition counts or returns
- **THEN** it SHALL report them in a separate evidence class
- **AND** they SHALL NOT increase live known-propensity coverage, live OPE overlap, target-supported victory counts, or promotion evidence

#### Scenario: Simulator data trains a bounded smoke
- **WHEN** a reviewed bounded smoke derives rewards, returns, model updates, or holdout metrics from simulator transitions
- **THEN** every artifact SHALL retain simulator-only source and reward provenance
- **AND** it SHALL NOT be joined into live outcome, OPE, qualification, or promotion evidence

#### Scenario: Frozen simulator policies are compared
- **WHEN** a reviewed policy-validity study compares a frozen simulator policy with same-schema baselines
- **THEN** baseline deltas, confidence intervals, floors, and victories SHALL remain simulator-only evidence
- **AND** they SHALL NOT authorize formal training, increase live evidence coverage, or satisfy a live promotion gate

#### Scenario: Native demonstrations train a warm start
- **WHEN** a reviewed baseline-warm-start study derives supervised labels, model updates, action-fit metrics, or rollout comparisons from native SimpleAgent demonstrations
- **THEN** every artifact SHALL retain simulator-only source, teacher, cohort, and model provenance
- **AND** it SHALL NOT treat the teacher as reward, increase live evidence coverage, or satisfy a live promotion gate

#### Scenario: Future training combines evidence classes
- **WHEN** a future proposal seeks to train on both live and simulator data
- **THEN** it MUST separately define dataset weighting, simulator-divergence controls, reward semantics, and real-game holdout evaluation
- **AND** the adapter POC, bounded simulator smoke, policy-validity study, or baseline warm start alone SHALL NOT satisfy that approval gate
