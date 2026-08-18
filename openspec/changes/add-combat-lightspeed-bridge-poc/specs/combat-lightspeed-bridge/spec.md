## ADDED Requirements

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
