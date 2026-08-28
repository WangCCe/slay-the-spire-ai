## MODIFIED Requirements

### Requirement: Fixed downstream eligibility gate
The system SHALL permit only a separately registered fresh holdout when all preregistered technical, fit, materiality, direct-policy stability, override-label uplift, provenance, and serialization checks pass. It MUST NOT grant gameplay, qualification, promotion, or production authority. After a failed candidate fit, the candidate pipeline MUST stop on that corpus; the system SHALL permit reuse only through a separate, finite, preregistered objective-design ablation that grants no candidate or downstream authority.

#### Scenario: Every stratified development condition passes
- **WHEN** validation TD loss improves, overall parent disagreement is at least 5%, direct parent disagreement is at most 10%, override executed-label agreement improves by at least 0.10 absolute, positive-energy End Turn count increases by at most two, both validation provenance strata are nonempty, and all integrity checks pass
- **THEN** the frozen candidate hash is eligible only for a separate fresh holdout

#### Scenario: Any stratified development condition fails
- **WHEN** one or more fixed conditions fail
- **THEN** production r16 remains authoritative and no alternate candidate recipe is fitted on the same corpus

#### Scenario: Separate bounded objective-design ablation is registered
- **WHEN** a later change freezes a finite arm matrix, immutable inputs, deterministic seeds, technical metrics, and no-authority boundary before reusing the failed development corpus
- **THEN** the system may emit only an objective recipe recommendation and MUST require a newly collected replay before fitting a final candidate

#### Scenario: Same-corpus reuse is adaptive or grants candidate authority
- **WHEN** a reuse attempt changes arms after observing results or claims candidate, holdout, gameplay, qualification, promotion, policy-quality, or production authority
- **THEN** the system rejects the attempt
