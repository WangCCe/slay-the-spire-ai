## MODIFIED Requirements

### Requirement: Offline native combat environment
The system SHALL provide an opt-in native `sts_lightspeed` combat environment that can reset from an Ironclad seed, ascension, and zero-based battle index; deterministically resolve every earlier run state with the declared native baseline; clone the current state; return a canonical snapshot; enumerate legal actions; apply one legal action; and report terminal, unsupported, or initialization boundaries.

#### Scenario: Deterministic indexed reset
- **WHEN** two environments reset with the same seed, ascension, battle index, and source identity
- **THEN** their canonical requested combat snapshots and legal actions are identical

#### Scenario: First-combat compatibility
- **WHEN** an environment resets with battle index zero
- **THEN** it reaches the same first supported combat semantics as the prior first-combat-only adapter

#### Scenario: Baseline-forward progression
- **WHEN** an environment resets with a reachable positive battle index
- **THEN** the native baseline resolves all earlier out-of-combat states and combats, writes each prior result back to the run state, and starts the RL-visible episode at exactly the requested battle with decision count zero

#### Scenario: Indexed reset evidence
- **WHEN** a requested combat is reached
- **THEN** status and snapshot evidence report the requested and reached battle index together with the target act, floor, encounter, deck size, relic count, and player HP

#### Scenario: Unreachable indexed reset
- **WHEN** the baseline loses, the run terminates, an unsupported state occurs, no progress is made, or an advancement bound is exhausted before the requested combat
- **THEN** initialization fails with a stable classified reason and does not substitute a different combat or seed

#### Scenario: Clone isolation
- **WHEN** a legal action is applied to one clone
- **THEN** the source environment and a separate clone retain their original canonical state

#### Scenario: Unsupported combat substate
- **WHEN** native execution reaches a combat input state not covered by the bridge
- **THEN** the environment reports a stable unsupported reason and does not fabricate a legal RL v2 action

### Requirement: Bounded source-only calibration
The system SHALL provide a deterministic calibration runner that exercises a fixed bounded cohort of registered `(seed, ascension, battle_index)` profiles, records source and baseline identities, and reports mapping, clone/replay, progression-coverage, and initialization-failure evidence without accessing gameplay or training state.

#### Scenario: Calibration completion
- **WHEN** the registered profile and decision bounds complete without a native or mapping integrity failure
- **THEN** the report includes supported-state count, action-family coverage, deterministic successor checks, terminal outcomes, unsupported counts, initialization failures by reason, encounter and act coverage, floor range, deck-size range, relic-count range, HP range, and artifact hashes

#### Scenario: Later-battle coverage gate
- **WHEN** expanded-surface training is considered
- **THEN** a source-bound calibration report demonstrates reached positive battle indices and materially broader encounter or progression-state coverage than the first-combat cohort

#### Scenario: Calibration failure
- **WHEN** source identity, indexed reset identity, clone isolation, successor determinism, shape, action correspondence, or profile accounting fails
- **THEN** the run terminates with a non-ready verdict and preserves the failure evidence
