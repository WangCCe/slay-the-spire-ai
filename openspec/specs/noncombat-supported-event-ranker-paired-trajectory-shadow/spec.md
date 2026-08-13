# noncombat-supported-event-ranker-paired-trajectory-shadow Specification

## Purpose
TBD - created by archiving change evaluate-supported-event-ranker-paired-trajectories. Update Purpose after archive.
## Requirements
### Requirement: Bound training support
The experiment SHALL verify the training dataset against the model's artifact
manifest and derive canonical support signatures from observed executable event
candidate semantics.

#### Scenario: Training dataset is valid
- **WHEN** the dataset bytes match their manifest binding and canonical codec round trip
- **THEN** the experiment records the support signature count, event identities, and support digest

#### Scenario: Training dataset binding differs
- **WHEN** the dataset is absent, noncanonical, or differs from its manifest binding
- **THEN** the experiment stops before trajectory or model inference

### Requirement: Supported event-only overlay
The selected arm SHALL invoke the frozen event ranker only for multi-option event
candidate signatures present in the bound training support set.

#### Scenario: Event signature is supported
- **WHEN** the current event candidate signature is in training support
- **THEN** the selected arm applies the stored model and threshold and records the proposal and any override

#### Scenario: Event signature is unsupported
- **WHEN** the current event candidate signature is absent from training support
- **THEN** the selected arm executes Current unchanged and records an explicit support fallback

#### Scenario: State is outside event overlay scope
- **WHEN** the state is route, shop, card reward, or a single-option event
- **THEN** the selected arm executes Current unchanged without model inference

### Requirement: Fresh paired trajectory evaluation
The experiment SHALL run pure Current and supported-overlay arms from separate
environments initialized with each identical fixed fresh seed.

#### Scenario: Pair completes
- **WHEN** both arms reach supported terminal outcomes
- **THEN** the experiment records action traces, support decisions, terminal outcomes, and paired deltas

#### Scenario: Pair reaches registered unsupported continuation
- **WHEN** either arm reaches a registered simulator or Current support boundary
- **THEN** the experiment excludes the pair and records the exact censor reason within the fixed limit

### Requirement: Fixed integration verdict
The experiment SHALL decide readiness from predeclared complete-pair, event and
support exposure, override, fallback-accounting, victory, floor, return, and
paired-regression gates.

#### Scenario: Supported overlay passes
- **WHEN** all fixed support and terminal-value gates pass
- **THEN** the verdict permits only a separate simulator policy-bundle proposal

#### Scenario: Any gate fails
- **WHEN** any fixed support or terminal-value gate is unmet
- **THEN** the verdict ends the frozen event-ranker integration path without rerun or tuning

### Requirement: Reproducible offline isolation
The experiment MUST bind source, model, training dataset, support digest, native
adapter, Current bridge, seeds, traces, metrics, and artifacts while keeping all
gameplay and training authority false.

#### Scenario: Experiment executes
- **WHEN** the fixed paired cohort is evaluated
- **THEN** the experiment performs no fitting, gameplay, CommunicationMod, production checkpoint access, qualification, or promotion

