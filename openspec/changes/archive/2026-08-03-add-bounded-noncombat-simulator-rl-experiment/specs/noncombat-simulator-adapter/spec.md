## ADDED Requirements

### Requirement: Reviewed Bounded RL Experiment Adapter Access
The API v3 simulator adapter SHALL serve a bounded non-combat RL experiment only
under an accepted experiment registration and execution authorization that bind
the exact adapter, native module, physical simulator source, cohorts, support
envelope, and resource limits.

#### Scenario: An authorized experiment constructs an environment
- **WHEN** the exact pushed registration and one-shot execution authorization
  pass before rollout
- **THEN** the adapter MAY construct only registered A0 Ironclad environments
  in the registered train, canary, holdout, or checkpoint-prefix role
- **AND** existing deterministic transitions, candidate legality, API v3 event
  semantics, native shop support, and baseline-controlled screens SHALL remain
  unchanged

#### Scenario: An experiment request exceeds its registration
- **WHEN** a caller requests another seed, role, ascension, module, source,
  support approximation, environment override, or terminal replacement
- **THEN** the adapter SHALL reject the request before returning policy-consumable
  evidence
- **AND** it SHALL NOT substitute SimpleAgent, Current, Bottled, or another
  candidate

#### Scenario: Experiment adapter evidence is published
- **WHEN** the registered experiment reaches a terminal result
- **THEN** adapter rows MAY support only that simulator experiment's legality,
  reward, learning-signal, and reproducibility classifications
- **AND** formal RL, live gameplay, target-supported outcomes, OPE, loading,
  qualification, and promotion authority SHALL remain false
