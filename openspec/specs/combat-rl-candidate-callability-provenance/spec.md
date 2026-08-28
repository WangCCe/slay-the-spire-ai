# combat-rl-candidate-callability-provenance Specification

## Purpose

Define exact RL proposal identity, candidate-decision SMDP construction, fresh
callability-complete replay collection, and fixed development-fit authority.

## Requirements

### Requirement: Exact candidate-callability identity
The live RL v2 collection path SHALL persist the exact pending RL proposal index for every emitted legal combat transition. It MUST use explicit no-proposal and legacy-unknown sentinels and MUST classify every known row as direct unchanged proposal, changed same-state proposal, or no-proposal takeover without changing the emitted action.

#### Scenario: Proposal is emitted unchanged
- **WHEN** a legal emitted action equals the pending RL proposal
- **THEN** replay stores the proposal index, the executed action, and a disabled executed-action override

#### Scenario: Proposal is replaced
- **WHEN** a legal emitted action differs from the pending RL proposal for the same state
- **THEN** replay retains the original proposal index, stores the emitted action, and enables the executed-action override

#### Scenario: Wrapper emits without a proposal
- **WHEN** a legal combat action is emitted while no pending RL proposal exists
- **THEN** replay stores the no-proposal sentinel and enables the executed-action override

#### Scenario: Caller provenance is unavailable
- **WHEN** a caller stores a transition without exact proposal identity
- **THEN** replay stores the legacy-unknown sentinel rather than inferring a callability class

### Requirement: Compatible and validated replay schema
Replay schema v3 SHALL persist exact proposed action indices while preserving schema-v1 and schema-v2 loading and the existing default sampling contract. Every known proposal MUST be legal under the stored action mask and MUST be consistent with the executed action and override flag.

#### Scenario: Schema-v3 replay round trip
- **WHEN** replay containing direct, changed-proposal, no-proposal, and unknown rows is saved and loaded
- **THEN** every executed action, proposal index, override value, order, and tensor dtype is preserved exactly

#### Scenario: Legacy replay is loaded
- **WHEN** a schema-v1 or schema-v2 replay without proposal indices is loaded
- **THEN** every restored proposal index is legacy unknown and existing executed-action override semantics remain unchanged

#### Scenario: Known proposal identity is inconsistent
- **WHEN** a nonnegative proposal is illegal, an unchanged proposal has override enabled, a changed proposal has override disabled, or a no-proposal row has override disabled
- **THEN** validation fails before publishing or fitting from the replay

#### Scenario: Existing sampler is used
- **WHEN** a caller samples replay without explicitly requesting proposal identity
- **THEN** the returned fields remain compatible with the existing trainer contract

### Requirement: Candidate-decision SMDP construction
The offline builder SHALL convert terminal-delimited source replay into candidate-decision spans. It MUST start only from proposal-bearing rows, aggregate discounted rewards across subsequent no-proposal takeover rows, and bootstrap only from the next proposal-bearing state or a terminal boundary.

#### Scenario: Proposal enters a takeover span
- **WHEN** a proposal-bearing row is followed by one or more no-proposal rows before the next proposal
- **THEN** the builder emits one candidate-decision sample with accumulated discounted reward, source span length, and bootstrap multiplier `gamma ** span_length`

#### Scenario: Immediate successor has not settled
- **WHEN** the last source row's stored `next_*` snapshot differs from the next proposal-bearing row after game effects settle
- **THEN** the nonterminal span bootstraps from the next proposal-bearing row's current state and action mask and reports the settled boundary

#### Scenario: Takeover reaches terminal
- **WHEN** no later proposal occurs before the source combat terminates
- **THEN** the span includes all remaining takeover rewards and has no bootstrap value

#### Scenario: Combat starts under wrapper control
- **WHEN** one or more no-proposal rows precede the first proposal in a combat
- **THEN** those rows are reported as uncontrolled prefix and are not attributed to a later candidate decision

#### Scenario: Unknown or unreconciled source row exists
- **WHEN** any source row has legacy-unknown proposal identity or cannot be assigned exactly once to a span, prefix, or terminal boundary
- **THEN** SMDP construction fails before fitting

### Requirement: Fresh callability-complete collection
The registered production-r16 cohort MUST preserve zero optimizer updates, exact seed order, trace and inventory identity, legal executed and proposed actions, complete callability classes, and nonempty direct and changed-proposal candidate strata before fitting.

#### Scenario: Fresh cohort passes
- **WHEN** all registered games complete and every collection, parity, legality, callability, and boundary check passes with no unknown rows
- **THEN** the immutable schema-v3 checkpoint may be consumed only by the registered callability-filtered fit

#### Scenario: Fresh cohort fails
- **WHEN** any registered game, hash, seed, trace, inventory, optimizer, legality, proposal reconciliation, class coverage, or boundary check fails
- **THEN** the cohort remains diagnostic-only and no candidate is fitted

### Requirement: Fixed callability-filtered development fit
The registered runner SHALL execute exactly one 64-update CPU fit over candidate-decision spans using the frozen recipe, batches containing exactly 64 direct and 64 changed-proposal spans sampled without replacement within each stratum, balanced direct/changed parent anchor, direct-only top-action margin guard, variable bootstrap multiplier, and terminal-combat split. No no-proposal or unknown row may be sampled as an independent candidate decision.

#### Scenario: Registered fit completes
- **WHEN** every immutable binding and pre-fit gate passes
- **THEN** the report binds optimizer batches, source spans, callability strata, losses, policy metrics, checkpoint hashes, and authority to the registered recipe and replay

#### Scenario: Optimizer samples an ineligible row
- **WHEN** any independent optimizer or evaluation row is no-proposal, legacy unknown, outside its source combat, or uses a fixed one-step bootstrap through takeover
- **THEN** fitting fails before publishing a final result

### Requirement: Callability-filtered authority gate
The result SHALL grant at most eligibility for a separately registered fresh holdout when every fixed technical gate passes. It MUST NOT authorize gameplay, qualification, promotion, policy quality, production loading, or another fit on the same corpus.

#### Scenario: Every gate passes
- **WHEN** validation SMDP TD improves, overall disagreement is at least 5%, direct disagreement is at most 10%, changed-proposal executed-label agreement improves by at least 0.10 absolute, positive-energy End Turn increase is at most two, both validation strata are nonempty, and all integrity checks pass
- **THEN** the frozen candidate is eligible only for a separate fresh holdout

#### Scenario: Any gate fails
- **WHEN** one or more fixed conditions fail
- **THEN** production r16 remains authoritative, the corpus is closed to further fitting, and the next architecture investigation is residual or separate head
