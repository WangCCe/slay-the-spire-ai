# Non-Combat Baseline-Floor Readiness Audit Specification

## Purpose

Define the immutable evidence, candidate-role isolation, conservative
unsupported-episode treatment, deterministic verdict, and no-authority boundary
for deciding whether a non-teacher baseline-floor study may be preregistered.

## Requirements

### Requirement: Immutable Baseline-Floor Readiness Evidence
The audit SHALL consume only a versioned registration that binds every decision-bearing readiness, baseline, bridge, compatibility, support-envelope, reward, and outcome-feasibility input by repository-relative path, SHA-256 digest, byte size, and expected identity.

#### Scenario: Registered evidence is exact
- **WHEN** every registered path, hash, size, schema or declared identity, and required absence matches
- **THEN** the audit SHALL evaluate exactly that frozen evidence
- **AND** it SHALL NOT discover additional reports by directory scan

#### Scenario: Evidence or implementation drifts
- **WHEN** a registered byte, identity, analyzer source, or expected no-authority field differs
- **THEN** the audit SHALL fail as `invalid_evidence`
- **AND** it SHALL publish no baseline-floor readiness claim

### Requirement: Non-Teacher Candidate Role Isolation
The audit SHALL classify candidate and reference policies by fixed role before evaluating baseline-floor eligibility, and SHALL NOT substitute imitation agreement or auxiliary-reference quality for a non-teacher floor.

#### Scenario: Current remains the only eligible candidate
- **WHEN** Current has exact frozen-row bridge compatibility but lacks a completed own-trajectory structural result under the current adapter surface
- **THEN** the audit SHALL classify Current as the only eligible non-teacher candidate with structural closure still required
- **AND** it SHALL NOT claim a demonstrated baseline floor

#### Scenario: Auxiliary and negative policies are inventoried
- **WHEN** SimpleAgent, Bottled, seeded initialization, imitation, structured-ranker, or residual-policy evidence is registered
- **THEN** SimpleAgent and Bottled SHALL remain auxiliary and the learned or seeded policies SHALL remain negative evidence or weak controls
- **AND** none SHALL become policy-quality truth, reward, or a credible baseline merely through agreement, loss, or relative improvement

### Requirement: Conservative Unsupported-Episode Contract
The audit SHALL require every future baseline-floor study to retain all selected episodes and apply a preregistered conservative disposition to exact support-envelope blockers.

#### Scenario: An episode reaches a declared support blocker
- **WHEN** a selected trajectory stops at an exact registered unsupported reason before terminal outcome
- **THEN** the episode SHALL remain in the denominator as a non-victory with its registered conservative floor value
- **AND** paired and aggregate pass metrics SHALL include it

#### Scenario: Unsupported rows are reported
- **WHEN** one or more selected episodes are unsupported
- **THEN** the study SHALL report exact reasons, counts, rates, seeds, and both conservative and supported-only diagnostics
- **AND** only the conservative metrics plus a preregistered unsupported-rate ceiling MAY affect a positive floor verdict

#### Scenario: A caller attempts survivor-only evaluation
- **WHEN** unsupported episodes are dropped, replaced, retried, or excluded from a headline pass metric
- **THEN** the audit SHALL reject the proposed evidence contract
- **AND** it SHALL NOT authorize a fresh cohort

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
- **AND** it SHALL authorize only consideration of a separate baseline-floor proposal

#### Scenario: No eligible candidate remains
- **WHEN** every non-teacher candidate is invalid, structurally incompatible, or lacks a conservative evaluable episode contract
- **THEN** the verdict SHALL be `no_viable_baseline_candidate`
- **AND** formal non-combat RL SHALL remain blocked

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

### Requirement: Canonical Planning Publication
The audit SHALL render one compact JSON result and one Markdown report deterministically and SHALL support byte-identical strict regeneration from the same registration.

#### Scenario: Publication succeeds
- **WHEN** all registered evidence validates and classification completes
- **THEN** JSON and Markdown SHALL report evidence identities, candidate roles, blockers, unsupported-episode requirements, verdict, next prerequisite, and authority flags
- **AND** strict regeneration SHALL reproduce both files byte-for-byte

#### Scenario: Publication fails
- **WHEN** validation, classification, rendering, or strict byte comparison fails
- **THEN** neither output SHALL be treated as a readiness result

### Requirement: Planning Audit Has No Execution Authority
The audit SHALL remain offline and read-only and SHALL keep native loading, simulator environment construction, seed selection, gameplay, model fitting, reward, OPE, formal-RL, training, qualification, loading, and promotion authority false for every verdict.

#### Scenario: Diagnostic smoke is recommended
- **WHEN** the verdict is `diagnostic_smoke_required`
- **THEN** the audit SHALL NOT itself load the module or execute reused seeds
- **AND** the smoke SHALL require a separate accepted OpenSpec change

#### Scenario: Baseline preregistration is considered
- **WHEN** a later audit returns `ready_for_baseline_floor_preregistration`
- **THEN** actual compatibility, evaluation, training, gameplay, or promotion SHALL remain unauthorized
- **AND** the independent target-supported-outcome blocker SHALL remain unchanged
