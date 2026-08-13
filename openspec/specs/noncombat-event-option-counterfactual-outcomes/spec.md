# noncombat-event-option-counterfactual-outcomes Specification

## Purpose
TBD - created by archiving change collect-event-option-counterfactual-outcomes. Update Purpose after archive.
## Requirements
### Requirement: Complete event option branches
The collector SHALL force every legal option at each eligible multi-option event source from an immutable clone and SHALL use a fresh frozen Current-policy continuation for each branch.

#### Scenario: Complete event source
- **WHEN** every legal event option reaches a supported terminal outcome
- **THEN** the collector records one source row containing event semantics, Current action, candidate outcomes, and return spread

#### Scenario: Unsupported branch
- **WHEN** any option branch reaches a registered unsupported simulator boundary
- **THEN** the collector excludes the incomplete source, records the reason, and continues within the censor limit

### Requirement: Deterministic branch replay
The collector SHALL replay the first option branch for the first 16 complete sources and SHALL compare the full outcome identity.

#### Scenario: Replay matches
- **WHEN** a replayed option produces the same action sequence, terminal state, return, and transition count
- **THEN** the source contributes to the replay pass count

#### Scenario: Replay differs
- **WHEN** any replay identity field differs
- **THEN** the terminal verdict is not viable

### Requirement: Event signal viability
The collector SHALL classify event counterfactual signal as viable only when support, outcome separation, event diversity, and deterministic replay floors all pass.

#### Scenario: Viability gate passes
- **WHEN** there are at least 64 complete sources, 32 informative sources, 8 distinct event ids, and 16 exact replays
- **THEN** the report permits a separate event-learning proposal

#### Scenario: Viability gate fails
- **WHEN** any fixed floor is unmet
- **THEN** the report records a no-go without fitting or selecting a model

### Requirement: Offline isolation
The collector MUST NOT launch gameplay or CommunicationMod, load or modify production checkpoints, fit a model, or alter policy behavior.

#### Scenario: POC execution
- **WHEN** the collector runs
- **THEN** it records source/native/bridge identities, fixed seeds, resource use, and all-false downstream authority
