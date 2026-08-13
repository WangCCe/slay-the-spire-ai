## ADDED Requirements

### Requirement: Shared trajectories are published as a bounded lossless replay
The experiment SHALL collect exactly one 64-seed candidate-only consumed cohort
and SHALL publish supported trajectories as canonical JSON in deterministic gzip.

#### Scenario: Replay publication succeeds
- **WHEN** 56 to 64 trajectories remain after bounded known censoring
- **THEN** the artifact records ordered decisions, CPU float32 state and candidate features, candidate metadata, selected actions, rewards, terminal metadata, and post-collection generator states
- **AND** stored bytes are at most 64 MiB and canonical bytes are at most 512 MiB

#### Scenario: Replay publication cannot validate
- **WHEN** support, size, canonical encoding, deterministic gzip, tensor validation, or round-trip identity fails
- **THEN** no optimizer step starts
- **AND** no seed is replaced or recollected under the same experiment identity

### Requirement: Optimizer branches consume only decoded replay data
Both optimizer branches SHALL restore checkpoint `004` and SHALL construct their
baseline and policy terms only after reading and validating the replay from disk.

#### Scenario: Replay is decoded
- **WHEN** stored and uncompressed bindings validate
- **THEN** decoded episode identities, order, categories, selected actions, features, rewards, and generator states exactly reproduce the encoded source values
- **AND** native environment objects and live rollout objects are released before branch updates

### Requirement: Full-model branch reproduces historical state
Branch A SHALL apply the current full-model Adam update and SHALL match the bound
historical checkpoint `005` bootstrap and optimizer state exactly.

#### Scenario: Full reproduction succeeds
- **WHEN** branch A completes one replayed update
- **THEN** model parameters, guarded models, generators, and Adam state equal historical checkpoint `005`
- **AND** scorer-only evidence may be interpreted

#### Scenario: Full reproduction fails
- **WHEN** any branch A bootstrap or optimizer byte differs
- **THEN** the verdict is `scorer_optimizer_ablation_reproduction_failed`
- **AND** no scorer mechanism or continuation claim is made

### Requirement: Scorer-only Adam is an exact state slice
Branch B SHALL optimize only the two scorer modules with the registered Adam
options and their corresponding checkpoint `004` moments.

#### Scenario: Scorer-only update completes
- **WHEN** scorer parameter names, order, shapes, dtypes, ownership, and Adam moments validate
- **THEN** exactly one scorer-only optimizer step is applied
- **AND** every hidden and guarded-model byte remains equal to checkpoint `004`

#### Scenario: Optimizer slice differs
- **WHEN** a scorer state is missing, reordered, incompatible, or includes a hidden parameter
- **THEN** both branches restore checkpoint `004`
- **AND** no partial branch artifact is published

### Requirement: Retained function movement gates progression
The runner SHALL compare entry, full-model, and scorer-only policies on the fixed
175-row probe and SHALL deny all downstream execution authority.

#### Scenario: Scorer-only retains material movement
- **WHEN** full reproduction and isolation pass, neither branch collapses, full-model mean joint total variation from entry is positive, scorer-only retains at least 80 percent of that value, and hidden bytes remain exact
- **THEN** the verdict is `ready_to_propose_four_step_scorer_optimizer_ablation`
- **AND** no four-step run starts under this change

#### Scenario: Scorer-only does not retain material movement
- **WHEN** validity checks pass but retained mean joint total variation is below 80 percent
- **THEN** the verdict is `scorer_only_optimizer_not_ready`
- **AND** the same one-step cohort is not recollected or tuned
