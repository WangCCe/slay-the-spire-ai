# noncombat-card-counterfactual-uplift-residual-audit Specification

## Purpose

Define fixed exposed-only uplift fitting, one bounded consumed audit, paired
read-only evaluation, and experiment/production isolation.

## Requirements

### Requirement: Fixed pre-audit model
The runner SHALL bind the completed cross-fit evidence and scorer datasets and
SHALL fit exactly one `shrinkage=3`, `strength=128` uplift model from all exposed
rows before constructing an audit environment. It MUST NOT update the entry
model or fit again after audit access.

#### Scenario: Audit access is about to begin
- **WHEN** all source, input, model, native, process, and isolation checks pass
- **THEN** the fixed uplift model already exists with a canonical identity and no audit return has influenced it

#### Scenario: Fixed configuration differs
- **WHEN** shrinkage, strength, fit rows, entry model, or model bytes differ
- **THEN** execution stops before audit environment construction

### Requirement: One bounded consumed audit
The runner SHALL collect only audit seeds `1024..1031`, at most two source
states per seed, at most 64 action branches, and at most one registered Courier
censor without replacement. It MUST require at least 12 complete source states.

#### Scenario: Audit support is valid
- **WHEN** collection completes within every registered limit
- **THEN** the runner persists the full canonical audit dataset and evaluates it once

#### Scenario: Audit support or blocker differs
- **WHEN** support is below 12 states, a nonregistered blocker occurs, or any branch/censor limit is exceeded
- **THEN** the runner fails without changing seeds, model, or configuration

### Requirement: Paired read-only audit gate
The runner SHALL compare frozen entry and fixed residual scores on identical
audit rows. Passing requires lower mean regret, nonincreasing maximum regret,
higher weighted pairwise accuracy, nondecreasing unique-best accuracy, and at
least one entry mistake corrected to a best action.

#### Scenario: Every audit gate passes
- **WHEN** all support, identity, immutability, and metric checks pass
- **THEN** the verdict authorizes only a separate fresh-evaluation proposal

#### Scenario: Any audit gate fails
- **WHEN** any fixed check fails
- **THEN** the verdict is not ready and no retry, tuning, refit, or alternate cohort is authorized

### Requirement: Native and production isolation
The audit SHALL bind and verify native bytes, CommunicationMod configuration,
and production checkpoint metadata. It MUST NOT start the game or
CommunicationMod, load a production checkpoint, or modify production state.

#### Scenario: Audit terminates
- **WHEN** a report is published
- **THEN** production isolation still matches, downstream authority is false, and all model/data artifacts remain experiment-local
