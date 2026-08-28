## ADDED Requirements

### Requirement: Provenance-balanced parent anchor
The trainer SHALL optionally compute the parent-policy anchor as the equal aggregate of direct-row and override-row mean cross entropy while preserving frozen-parent labels on direct rows and executed-action labels on override rows. Existing callers MUST retain the current global-mean behavior unless the new option is explicitly enabled.

#### Scenario: Mixed provenance batch is balanced
- **WHEN** a training batch contains direct and override rows and provenance balancing is enabled
- **THEN** each stratum contributes one half of the aggregate anchor loss and separate counts and component losses are reported

#### Scenario: Existing caller does not enable balancing
- **WHEN** the trainer is constructed with its default anchor configuration
- **THEN** anchor loss and behavior remain compatible with the existing global-mean implementation

### Requirement: Direct-only parent top-action margin protection
The trainer SHALL optionally restrict parent top-action margin protection to direct provenance rows while preserving the existing all-row margin-guard mode for current callers.

#### Scenario: Direct-only guard sees mixed provenance
- **WHEN** the direct-only guard is enabled on a mixed batch
- **THEN** only direct rows with at least two legal actions and a positive finite parent margin contribute to guard loss and ranking-violation telemetry

#### Scenario: Override row changes parent action
- **WHEN** an override row prefers its executed label over the frozen parent's top action
- **THEN** the direct-only margin guard contributes no loss for that row

### Requirement: Fixed offline objective ablation
The system MUST validate the immutable R2 replay, frozen r16 parameters, existing R2 reference report, two-arm recipe, seeds, split, thresholds, and absent output before fitting. It SHALL execute exactly the registered balanced-only and balanced-plus-direct-margin arms with 64 updates each and SHALL publish deterministic arm hashes and telemetry.

#### Scenario: Registered ablation completes
- **WHEN** both fixed arms complete with finite objectives and exact serialization
- **THEN** the report compares each arm with the immutable global-anchor reference under the same stratified development metrics

#### Scenario: Binding or recipe differs
- **WHEN** an input hash, source binding, arm option, seed, split, update count, weight, cap, or threshold differs
- **THEN** the runner fails before publishing a final output directory

### Requirement: Objective-only selection authority
The ablation SHALL recommend at most one objective recipe only when an arm passes every fixed stratified gate. It MUST NOT grant candidate, holdout, gameplay, qualification, promotion, policy-quality, or production authority, and a selected recipe MUST use a newly collected replay before producing a final candidate.

#### Scenario: One or more arms pass
- **WHEN** at least one arm passes all fixed gates
- **THEN** the runner applies the preregistered direct-drift, override-uplift, and simplicity tie-break and emits only a new-corpus recipe recommendation

#### Scenario: No arm passes
- **WHEN** both arms fail one or more fixed gates
- **THEN** the runner recommends no recipe and directs the next investigation toward a residual or separate-head design
