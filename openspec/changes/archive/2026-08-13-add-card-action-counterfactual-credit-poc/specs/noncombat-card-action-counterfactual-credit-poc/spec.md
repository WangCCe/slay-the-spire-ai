## ADDED Requirements

### Requirement: Source-preserving card action evaluation
The evaluator SHALL compare every legal candidate at an eligible card-reward
state by cloning one canonical source environment independently for each action.
It MUST reject a state if branch evaluation mutates the source environment or if
a forced action cannot be validated against the source candidates.

#### Scenario: Every legal action uses the same source
- **WHEN** an eligible card-reward state has multiple legal candidates
- **THEN** the evaluator applies each candidate to a distinct clone of the same canonical source and leaves the source environment unchanged

#### Scenario: Source mutation is detected
- **WHEN** the canonical source differs after any branch evaluation
- **THEN** the evaluator fails the POC instead of publishing comparable action returns

### Requirement: Fixed native continuation and formal rewards
After each forced card action, the evaluator SHALL use the native SimpleAgent
for every remaining decision until terminal and SHALL derive accumulated return
only from validated transitions under the existing formal reward contract. It
MUST NOT load a learned model or update any policy or baseline.

#### Scenario: Branch reaches terminal
- **WHEN** a forced card action is accepted
- **THEN** all downstream actions come from the native SimpleAgent and the branch return is the sum of formal transition rewards through terminal

#### Scenario: Unsupported native transition occurs
- **WHEN** any branch cannot produce or validate a required native transition
- **THEN** the evaluator fails closed without substituting another continuation policy

### Requirement: Bounded consumed-seed evidence
The empirical POC MUST use only consumed development seeds `1000..1007`, MUST
evaluate at most the first two eligible card-reward states per seed, and MUST
execute no more than 64 action branches. It MUST NOT replace seeds, expand the
cohort, or change bounds after execution begins.

#### Scenario: Branch budget would be exceeded
- **WHEN** evaluating every legal action at the next source state would exceed 64 total branches
- **THEN** the evaluator stops before that source and records the fixed budget boundary

#### Scenario: Seed produces more than two eligible states
- **WHEN** a consumed development seed reaches a third card-reward state
- **THEN** the evaluator advances without evaluating that state

### Requirement: Exact fixed-branch replay
The evaluator SHALL repeat one preregistered eligible branch from the identical
source clone and MUST require exact equality of the initial validated
transition, terminal summary, accumulated reward, and native action sequence.

#### Scenario: Fixed branch reproduces exactly
- **WHEN** the repeated branch has identical transition, terminal, reward, and action-sequence evidence
- **THEN** the report marks the determinism gate as passed

#### Scenario: Fixed branch drifts
- **WHEN** any required repeated-branch field differs
- **THEN** the report marks the POC failed and grants no downstream authority

### Requirement: Preregistered viability verdict
The POC SHALL report complete source-state count and, for each state, return
spread and unique-best status. It SHALL declare action-level counterfactual
credit viable only if at least eight source states are complete, at least four
complete states have nonzero return spread and one unique best action, and the
determinism gate passes.

#### Scenario: All viability gates pass
- **WHEN** the complete-state, informative-state, unique-best, determinism, and isolation gates all meet their fixed thresholds
- **THEN** the report declares the credit signal viable only for a later training-integration proposal

#### Scenario: Any viability gate fails
- **WHEN** any fixed viability or isolation gate is not met
- **THEN** the report declares the POC not ready and forbids training, tuning, cohort expansion, qualification, promotion, and policy-quality claims

### Requirement: Production isolation and compact reporting
The runner SHALL bind and compare production checkpoint and CommunicationMod
metadata before and after execution, SHALL reject protected seed access, and
SHALL publish compact source/action/return evidence without full simulator
snapshots. All model-fitting, training, evaluation, OPE, gameplay, qualification,
promotion, and policy-quality authority fields MUST remain false.

#### Scenario: POC completes without production mutation
- **WHEN** execution ends and production bindings match their pre-run values
- **THEN** the report includes compact hashes, action returns, gate results, and false downstream authority

#### Scenario: Production binding changes
- **WHEN** a production checkpoint or CommunicationMod binding differs after execution
- **THEN** the runner fails isolation and grants no downstream authority
