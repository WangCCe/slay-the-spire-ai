## ADDED Requirements

### Requirement: Frozen-parent end-turn margin guard
The simulator trainer SHALL optionally preserve the frozen parent's clipped positive selected-non-end-turn-versus-end-turn Q margin on legal replay states.

#### Scenario: Eligible replay row
- **WHEN** end turn is legal and the frozen parent's masked greedy action is not end turn
- **THEN** the guard computes a hinge loss against the parent's positive selected-action-versus-end-turn margin clipped by the registered cap

#### Scenario: Ineligible replay row
- **WHEN** end turn is illegal or the frozen parent selects end turn
- **THEN** the row contributes neither loss nor eligibility count to the guard

#### Scenario: Zero eligible rows
- **WHEN** a replay batch contains no eligible guard rows
- **THEN** the guard returns a finite differentiable zero and reports zero eligible rows and zero ranking violations

### Requirement: Guard configuration compatibility
The simulator trainer SHALL keep the end-turn margin guard disabled by default and SHALL require an immutable warm-start parent for positive guard weight.

#### Scenario: Default-off compatibility
- **WHEN** guard weight is `0.0`
- **THEN** existing initialization, optimization, checkpoint, and report behavior remains unchanged

#### Scenario: Invalid guard configuration
- **WHEN** weight or cap is non-finite, weight is negative, or a positive weight has no positive cap or valid warm-start parent
- **THEN** the runner fails before trajectory collection or model fitting

### Requirement: Guard evidence binding
The simulator-only report and checkpoint SHALL bind the guard configuration and objective evidence without granting production authority.

#### Scenario: Guarded optimization completes
- **WHEN** a positive-weight guarded run completes optimizer updates
- **THEN** the report records finite guard losses, positive aggregate eligibility, ranking-violation counts, weight, cap, and frozen-parent parameter identity

#### Scenario: Simulator-only authority
- **WHEN** a guarded candidate is published
- **THEN** it remains production-incompatible and grants no gameplay, transfer, qualification, promotion, or live policy-quality authority

### Requirement: Bounded fresh-seed decision gate
The first guarded successor SHALL use preregistered fresh disjoint training and evaluation seeds and SHALL stop before production or gameplay unless its matched LightSTS outcome gates pass.

#### Scenario: Outcome gate misses
- **WHEN** the guarded successor misses any registered matched aggregate or battle-stratum guardrail
- **THEN** production r16 remains authoritative and no packaging or gameplay is authorized

#### Scenario: Outcome gate passes
- **WHEN** all registered technical and matched LightSTS outcome guardrails pass
- **THEN** the report may authorize a separately registered confirmation but SHALL NOT itself authorize production packaging or gameplay
