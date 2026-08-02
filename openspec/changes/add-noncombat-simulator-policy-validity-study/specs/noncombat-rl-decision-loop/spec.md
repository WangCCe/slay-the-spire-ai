## MODIFIED Requirements

### Requirement: Simulator Transitions Remain Separate Evidence
The non-combat decision loop SHALL distinguish simulator-generated transitions, rewards, returns, models, baseline comparisons, and evaluation metrics from live trace samples, known-propensity exploration evidence, and matched `.run` outcomes.

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

#### Scenario: Future training combines evidence classes
- **WHEN** a future proposal seeks to train on both live and simulator data
- **THEN** it MUST separately define dataset weighting, simulator-divergence controls, reward semantics, and real-game holdout evaluation
- **AND** the adapter POC, bounded simulator smoke, or policy-validity study alone SHALL NOT satisfy that approval gate
