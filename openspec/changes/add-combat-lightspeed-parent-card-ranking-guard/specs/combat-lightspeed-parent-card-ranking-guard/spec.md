## ADDED Requirements

### Requirement: Frozen-parent legal-card ranking guard
The simulator trainer SHALL optionally preserve the frozen parent's clipped positive best-legal-card-versus-best-alternative-card Q margin on replay states.

#### Scenario: Eligible replay row
- **WHEN** at least two card-play actions are legal and the frozen parent's best card action has a finite positive margin over its next-best legal card action
- **THEN** the guard computes a hinge loss requiring the candidate to preserve that margin up to the registered cap

#### Scenario: Candidate ranking violation
- **WHEN** the candidate ranks another legal card action above the frozen parent's best legal card action on an eligible row
- **THEN** the guard counts one ranking violation

#### Scenario: Ineligible replay row
- **WHEN** fewer than two card-play actions are legal or the frozen parent's best-card margin is non-positive or non-finite
- **THEN** the row contributes neither loss nor eligibility count

#### Scenario: Zero eligible rows
- **WHEN** a replay batch contains no eligible rows
- **THEN** the guard returns a finite differentiable zero and reports zero eligible rows and zero ranking violations

### Requirement: Card-ranking guard configuration compatibility
The simulator trainer SHALL keep the card-ranking guard disabled by default and SHALL require an immutable warm-start parent for positive guard weight.

#### Scenario: Default-off compatibility
- **WHEN** card-ranking guard weight is `0.0`
- **THEN** existing initialization, optimization, checkpoint, and report behavior remains unchanged apart from additive default-valued schema fields

#### Scenario: Invalid guard configuration
- **WHEN** weight or cap is non-finite, weight is negative, or a positive weight has no positive cap or valid warm-start parent
- **THEN** the runner fails before trajectory collection or model fitting

### Requirement: Card-ranking guard evidence binding
The simulator-only report and checkpoint SHALL bind card-ranking guard configuration and objective evidence without granting production authority.

#### Scenario: Guarded optimization completes
- **WHEN** a positive-weight guarded run completes optimizer updates
- **THEN** the report records finite losses, positive aggregate eligibility, ranking-violation counts, weight, cap, and frozen-parent identity

#### Scenario: Simulator-only authority
- **WHEN** a card-ranking guarded candidate is published
- **THEN** it remains production-incompatible and grants no gameplay, transfer, qualification, promotion, or live policy-quality authority

### Requirement: Guard-aware objective ablation gate
The first card-ranking guarded candidate SHALL be evaluated against the frozen production parent and prior guarded control under the same deployment guard proxy before fresh or live work.

#### Scenario: Material guard-aware improvement absent
- **WHEN** the candidate does not materially improve preregistered reward, HP, victory, and battle-stratum metrics over both controls
- **THEN** production r16 remains authoritative and no fresh confirmation, packaging, or gameplay is authorized

#### Scenario: Material guard-aware improvement present
- **WHEN** all technical and guard-aware outcome gates pass
- **THEN** the evidence may authorize one separately registered fresh frozen comparison but SHALL NOT authorize packaging or gameplay
