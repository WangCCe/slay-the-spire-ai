## ADDED Requirements

### Requirement: Immutable readiness registration
The system SHALL require one versioned registration that binds the source commit, analyzer implementation, fixed gate contract, and every consumed evidence file by repository-relative path, SHA-256 digest, byte size, and expected schema before a formal non-combat RL readiness audit can run.

#### Scenario: Registered evidence is exact
- **WHEN** every required path, byte identity, schema, embedded registration identity, and declared absence matches the registration
- **THEN** the analyzer SHALL evaluate exactly those frozen inputs under the registered gate contract

#### Scenario: Evidence or contract drifts
- **WHEN** a required file, hash, size, schema, embedded identity, declared absence, implementation identity, or gate value differs
- **THEN** the analyzer SHALL fail closed as `invalid_evidence` before issuing a readiness interpretation

### Requirement: Independent readiness domains
The analyzer SHALL evaluate state/action, reference isolation, formal reward, baseline policy, outcome support, and evaluation readiness as separate deterministic domains without averaging or allowing one domain to override another.

#### Scenario: State and action evidence closes
- **WHEN** frozen evidence has exact teacher reconstruction without adapter gaps, includes multi-candidate route and card-reward rows, and reports legal candidates across route, shop, event, and card reward
- **THEN** the state/action domain SHALL pass without claiming that the reconstructed teacher is a policy-quality target

#### Scenario: Formal reward evidence is absent
- **WHEN** only a simulator-smoke reward or a descriptive reward-readiness record is available and no separately tested formal reward contract is registered
- **THEN** the reward domain SHALL fail with an explicit formal-reward-contract prerequisite

#### Scenario: Baseline floor is not demonstrated
- **WHEN** a warm-start validation, independent rollout, final, or deterministic reproduction gate does not demonstrate the preregistered baseline policy floor
- **THEN** the baseline domain SHALL fail regardless of training loss, teacher agreement, or improvement over a weaker initialization

#### Scenario: Outcome support is not demonstrated
- **WHEN** evidence is source-incomparable, target-supported victories are below the registered minimum, or the registered feasibility pass probability is below its floor
- **THEN** the outcome-support domain SHALL fail without counting raw unsupported victories

#### Scenario: Evaluation isolation is preserved
- **WHEN** registered train and evaluation cohorts are disjoint, deterministic replays match, final-test access obeys its stop gate, frozen evaluation performs no update, and downstream authority remains false
- **THEN** the evaluation domain SHALL pass independently of policy quality

### Requirement: Auxiliary reference isolation
The audit SHALL preserve SimpleAgent, Current, and Bottled outputs only as explicitly bounded auxiliary references and SHALL NOT treat reference agreement, imitation accuracy, or teacher reconstruction as reward, policy-quality truth, or downstream authority.

#### Scenario: Teacher is source-faithful but policy-narrow
- **WHEN** the teacher audit reconstructs every registered target but reports failed suitability checks
- **THEN** the readiness matrix SHALL record source closure and teacher limitation separately
- **AND** it SHALL NOT create a blocker that asks for more imitation of that teacher

#### Scenario: Reference leaks into a quality gate
- **WHEN** a registration or consumed artifact grants a reference policy reward, policy-quality, training, live, OPE, qualification, or promotion authority
- **THEN** the audit SHALL classify the evidence as invalid

### Requirement: Fixed fail-closed verdict
The analyzer SHALL publish exactly one terminal verdict using fixed precedence: `invalid_evidence` for invalid or non-reproducible evidence, `not_ready_for_bounded_training_proposal` for valid evidence with any failed readiness domain, or `ready_for_bounded_training_proposal` only when every required domain passes.

#### Scenario: Valid evidence has unmet prerequisites
- **WHEN** evidence integrity passes and at least one required readiness domain fails
- **THEN** the analyzer SHALL emit `not_ready_for_bounded_training_proposal`
- **AND** it SHALL list deterministic prerequisites ordered by the registered domain order

#### Scenario: Every readiness domain passes
- **WHEN** evidence integrity and every required readiness domain pass
- **THEN** the analyzer SHALL emit `ready_for_bounded_training_proposal`
- **AND** it SHALL authorize only consideration of a separate reviewed bounded-training proposal

#### Scenario: Evidence integrity fails
- **WHEN** any registered identity, schema, structural, replay, or no-authority check fails
- **THEN** the analyzer SHALL emit `invalid_evidence` and no positive readiness flag

### Requirement: Hash-closed atomic publication
The audit SHALL atomically publish the validated configuration, evidence inventory, readiness matrix, machine-readable report, human-readable report, and artifact manifest, and SHALL support byte-identical strict recomputation from the same registered inputs.

#### Scenario: Canonical publication succeeds
- **WHEN** all inputs validate and the audit completes
- **THEN** every canonical artifact SHALL be present in the manifest with its SHA-256 digest and byte size
- **AND** a strict recomputation SHALL reproduce every canonical byte

#### Scenario: Publication or recomputation fails
- **WHEN** generation is interrupted, an output is incomplete, or recomputed bytes differ
- **THEN** the analyzer SHALL fail without partially replacing the last complete canonical directory

### Requirement: No execution or promotion authority
The audit SHALL remain read-only and SHALL keep gameplay, simulator rollout, native loading, model fitting, formal RL, OPE reinterpretation, qualification, live loading, and policy promotion authority false for every verdict.

#### Scenario: Positive readiness verdict is consumed
- **WHEN** a consumer reads `ready_for_bounded_training_proposal`
- **THEN** the only positive flag SHALL be bounded-training-proposal consideration
- **AND** actual training or evaluation execution SHALL still require a separate accepted OpenSpec change

#### Scenario: Canonical blocked evidence is audited
- **WHEN** the frozen current evidence lacks a formal reward contract, credible baseline floor, or demonstrated outcome support
- **THEN** the audit SHALL publish those gaps without running gameplay, simulator code, native modules, models, training, qualification, or promotion
