## MODIFIED Requirements

### Requirement: Simulator POC Has No Training Authority
Simulator adapter readiness SHALL authorize only separately reviewed bounded simulator smoke, policy-validity, or baseline-warm-start work and SHALL NOT authorize formal training or live use.

#### Scenario: POC report passes
- **WHEN** a fit report returns `adapter_poc_ready`
- **THEN** live study launch, formal RL training, OPE reinterpretation, live policy loading, and promotion authority SHALL all remain false

#### Scenario: Reviewed bounded smoke executes
- **WHEN** an accepted simulator-training-smoke change invokes the adapter against its exact registered identities
- **THEN** the adapter MAY run only within that change's registered cohorts and resource bounds
- **AND** formal RL, live gameplay, live loading, OPE, qualification, and promotion authority SHALL remain false

#### Scenario: Reviewed policy-validity study executes
- **WHEN** an accepted simulator-policy-validity change invokes the adapter against its exact registered identities
- **THEN** the adapter MAY run only frozen policies within that change's registered compatibility and fresh-evaluation bounds
- **AND** training, live gameplay, live loading, OPE, qualification, and promotion authority SHALL remain false

#### Scenario: Reviewed baseline warm start executes
- **WHEN** an accepted baseline-warm-start change invokes the adapter against its exact registered identities
- **THEN** the adapter MAY collect native demonstrations, train one bounded supervised candidate ranker, and evaluate frozen policies only within that change's registered cohorts and limits
- **AND** formal RL, simulator RL training, live gameplay, live loading, OPE, qualification, and promotion authority SHALL remain false

#### Scenario: Bottled labels are attached
- **WHEN** Bottled labels are compared with simulator transitions
- **THEN** they SHALL remain auxiliary annotations
- **AND** they SHALL NOT become direct reward, terminal truth, or simulator correctness evidence
