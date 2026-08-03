## MODIFIED Requirements

### Requirement: Fixed Baseline-Floor Planning Verdict
The audit SHALL publish one deterministic planning verdict using fixed
precedence and SHALL name one exact next prerequisite without authorizing
execution.

#### Scenario: Current structural closure is absent before post-r2 closeout
- **WHEN** frozen Current own-trajectory compatibility has no completed row and
  the separately reviewed r2 successor has not reached its terminal closeout
- **THEN** the verdict SHALL be `diagnostic_smoke_required`
- **AND** the next prerequisite SHALL remain the already reviewed reused-seed
  structural diagnostic path

#### Scenario: Both diagnostics are consumed and static repairs are closed
- **WHEN** v1 and r2 are immutable zero-row failures, r3 is prohibited, their
  independent candidate-schema and closed item-identity repairs pass, and no
  Current policy-quality row exists
- **THEN** the verdict MAY be
  `post_repair_baseline_evidence_contract_required`
- **AND** only one integrated canary-plus-holdout study contract MAY be proposed
  without reviving or replacing either diagnostic

#### Scenario: Integrated study contract is complete but unexecuted
- **WHEN** candidate role, conservative unsupported handling, fixed weak
  control, numeric canary and holdout gates, replay, bootstrap, stop, cohort
  isolation, untouched holdout, limits, publication, and separate execution
  approval are all fixed
- **THEN** the verdict MAY be
  `ready_for_post_repair_baseline_evidence_preregistration`
- **AND** native loading, environment construction, seed access, and execution
  SHALL remain unauthorized

#### Scenario: Current structural closure exists but the floor contract is incomplete
- **WHEN** Current structural closure is demonstrated through earlier evidence
  but comparison controls, numeric absolute and paired gates,
  unsupported-rate ceiling, replay, bootstrap, stop, or untouched holdout terms
  remain unfixed
- **THEN** the verdict SHALL be `baseline_floor_contract_required`
- **AND** no fresh baseline-floor cohort SHALL be selected or executed

#### Scenario: Candidate and evidence contract are complete
- **WHEN** Current structural closure is demonstrated and candidate role,
  conservative unsupported handling, comparison controls, numeric absolute and
  paired gates, replay, bootstrap, stop, and untouched holdout contracts are all
  fixed
- **THEN** the verdict MAY be `ready_for_baseline_floor_preregistration`
- **AND** it SHALL authorize only consideration of a separate baseline-floor
  proposal

#### Scenario: No eligible candidate remains
- **WHEN** every non-teacher candidate is invalid, structurally incompatible,
  or lacks a conservative evaluable episode contract
- **THEN** the verdict SHALL be `no_viable_baseline_candidate`
- **AND** formal non-combat RL SHALL remain blocked

## ADDED Requirements

### Requirement: Integrated Post-Repair Result Interpretation
The audit SHALL treat the registered integrated study as both structural and
floor evidence only when its immutable canary and holdout contracts were
followed, and SHALL NOT infer success from partial or supported-only rows.

#### Scenario: Integrated study demonstrates a floor
- **WHEN** the canonical result is `study_valid_with_baseline_floor`, every
  selected row is retained, replay and bootstrap identities match, and every
  absolute, paired, support, coverage, and publication gate passes
- **THEN** a later read-only refresh MAY mark Current structural closure and the
  baseline-floor contract demonstrated
- **AND** outcome support and formal training SHALL remain independently blocked

#### Scenario: Integrated study does not demonstrate a floor
- **WHEN** the study stops at canary, is blocked, is interrupted, is invalid, or
  returns `study_valid_without_baseline_floor`
- **THEN** the audit SHALL preserve the exact negative result and keep the
  baseline policy domain blocked
- **AND** it SHALL NOT recommend r3, replacement seeds, threshold changes, or a
  same-question retry
