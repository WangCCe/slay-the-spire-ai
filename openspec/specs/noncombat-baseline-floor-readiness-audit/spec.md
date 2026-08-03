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
The audit SHALL publish one deterministic planning verdict using fixed precedence and SHALL name one exact next prerequisite.

#### Scenario: Current structural closure is absent
- **WHEN** frozen Current own-trajectory compatibility has no completed deterministic row under the current supported adapter boundary
- **THEN** the verdict SHALL be `diagnostic_smoke_required`
- **AND** the next prerequisite SHALL be a separately reviewed reused-development-seed Current bridge smoke with structural-only authority

#### Scenario: Structural closure exists but the floor contract is incomplete
- **WHEN** Current structural closure is demonstrated but comparison controls, numeric absolute and paired gates, unsupported-rate ceiling, replay, bootstrap, stop, or untouched holdout terms remain unfixed
- **THEN** the verdict SHALL be `baseline_floor_contract_required`
- **AND** no fresh baseline-floor cohort SHALL be selected or executed

#### Scenario: Candidate and evidence contract are complete
- **WHEN** Current structural closure is demonstrated and candidate role, conservative unsupported handling, comparison controls, numeric absolute and paired gates, replay, bootstrap, stop, and untouched holdout contracts are all fixed
- **THEN** the verdict MAY be `ready_for_baseline_floor_preregistration`
- **AND** it SHALL authorize only consideration of a separate baseline-floor proposal

#### Scenario: No eligible candidate remains
- **WHEN** every non-teacher candidate is invalid, structurally incompatible, or lacks a conservative evaluable episode contract
- **THEN** the verdict SHALL be `no_viable_baseline_candidate`
- **AND** formal non-combat RL SHALL remain blocked

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
