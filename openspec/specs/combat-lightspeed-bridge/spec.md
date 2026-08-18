# Combat LightSTS Bridge Specification

## Purpose

Define the offline-only native combat stepping, RL v2 mapping, calibration,
and production-isolation contract for the LightSTS bridge.

## Requirements

### Requirement: Offline native combat environment
The system SHALL provide an opt-in native `sts_lightspeed` combat environment that can reset from an Ironclad seed, clone the current state, return a canonical snapshot, enumerate legal actions, apply one legal action, and report terminal or unsupported boundaries.

#### Scenario: Deterministic reset
- **WHEN** two environments reset with the same seed, ascension, and source identity
- **THEN** their canonical first supported combat snapshots and legal actions are identical

#### Scenario: Clone isolation
- **WHEN** a legal action is applied to one clone
- **THEN** the source environment and a separate clone retain their original canonical state

#### Scenario: Unsupported combat substate
- **WHEN** native execution reaches a combat input state not covered by the POC
- **THEN** the environment reports a stable unsupported reason and does not fabricate a legal RL v2 action

### Requirement: Bounded auxiliary combat card-selection settlement
The native combat environment SHALL deterministically settle implemented and natively enumerable `CARD_SELECT` states after an RL-visible legal action without changing the RL v2 observation or action dimensions.

#### Scenario: Enumerable card selection
- **WHEN** a legal combat action enters an allowlisted `CARD_SELECT` task with at least one valid native action
- **THEN** the environment applies the deterministic auxiliary native policy until it reaches player-normal input, a terminal outcome, another unsupported input state, or the settlement bound

#### Scenario: Settlement evidence
- **WHEN** one or more auxiliary card-selection actions are applied
- **THEN** the next status and snapshot report the ordered task identities and auxiliary action count while the RL-visible decision count increases only for the originating combat action

#### Scenario: Unsafe card selection
- **WHEN** a card-selection task is unimplemented, not allowlisted, has no enumerable action, makes no progress, or exceeds the settlement bound
- **THEN** the environment reports a stable unsupported reason and does not fabricate an RL v2 action or terminal outcome

#### Scenario: Deterministic clone successor
- **WHEN** the same legal action enters card selection on two clones of one source state
- **THEN** both clones produce identical settlement evidence, canonical successor state, and legal actions without mutating the source environment

#### Scenario: RL action-space isolation
- **WHEN** the bridge maps a successor after auxiliary settlement
- **THEN** it still returns 328 continuous features and a 133-element action mask containing only the existing card, potion, End Turn, and non-combat indices

### Requirement: Exact RL v2 mapping contract
The Python bridge SHALL map every supported native snapshot into the existing RL v2 observation components and a 133-element legal-action mask without loading a model.

#### Scenario: Supported player-normal state
- **WHEN** the native environment reports a supported player-normal combat snapshot
- **THEN** the bridge returns 328 continuous features, 10 card IDs, 5 potion IDs, 40 relic IDs, and a 133-element boolean mask

#### Scenario: Native action correspondence
- **WHEN** the native environment enumerates a playable card, usable potion, or End Turn
- **THEN** exactly the corresponding RL v2 action index is enabled in the mask

#### Scenario: Unknown identity
- **WHEN** a required simulator card, potion, relic, power, or intent identity cannot be mapped explicitly
- **THEN** the bridge rejects the state with a classified mapping error instead of silently substituting a production feature value

### Requirement: Bounded source-only calibration
The system SHALL provide a deterministic calibration runner that exercises a fixed bounded seed cohort, records source identities, and reports mapping and clone/replay evidence without accessing gameplay or training state.

#### Scenario: Calibration completion
- **WHEN** the registered seed and decision bounds complete without a native or mapping failure
- **THEN** the report includes supported-state count, action-family coverage, deterministic successor checks, terminal outcomes, unsupported counts by reason, and artifact hashes

#### Scenario: Calibration failure
- **WHEN** source identity, clone isolation, successor determinism, shape, or action correspondence fails
- **THEN** the run terminates with a non-ready verdict and preserves the failure evidence

### Requirement: Production isolation
The bridge SHALL remain outside CommunicationMod and SHALL grant no training, model-loading, gameplay, qualification, promotion, OPE, or mechanics-equivalence authority.

#### Scenario: Import isolation
- **WHEN** the production agent starts normally
- **THEN** neither the combat LightSTS native module nor its Python calibration package is imported

#### Scenario: Report authority
- **WHEN** a calibration report is published
- **THEN** all training, model-loading, gameplay, qualification, promotion, OPE, policy-quality, and mechanics-equivalence authority flags are false
