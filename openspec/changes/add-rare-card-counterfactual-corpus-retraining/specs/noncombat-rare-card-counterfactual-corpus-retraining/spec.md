## ADDED Requirements

### Requirement: Fixed targeted source eligibility
The collector SHALL branch only ordinary `card_reward` states containing at
least one legal take action whose card ID is in the fixed 16-card Ironclad rare
set. It SHALL otherwise advance the root trajectory with the registered native
baseline and MUST preserve the existing collector behavior when no target set
is supplied.

#### Scenario: Rare-card reward is reached
- **WHEN** a nonterminal ordinary card reward contains a target rare card and the per-seed state limit is not exhausted
- **THEN** every legal take and skip action is evaluated from the immutable source state

#### Scenario: Ordinary reward has no target card
- **WHEN** a card reward contains no target rare card
- **THEN** the root trajectory advances without consuming branch budget or source-state quota

### Requirement: Disjoint bounded targeted partitions
The runner SHALL collect train seeds `92000..92255` and development seeds
`92256..92319`, reserve audit seeds `92320..92383` without access, collect at
most two target states per seed, and enforce branch ceilings of 2,048 train and
512 development actions. It SHALL allow only the registered Courier blocker,
with at most 16 train and 4 development censored seeds and no replacement.

#### Scenario: Targeted collection passes
- **WHEN** train has at least 250 complete states, development has at least 60 complete states, and both contain all 16 target IDs within fixed limits
- **THEN** canonical partition datasets and exact collection diagnostics are published

#### Scenario: Collection support or boundary fails
- **WHEN** coverage is insufficient or a seed, deadline, branch, censor, native, process, or production-isolation boundary differs
- **THEN** the study reports not ready without replacing seeds, changing limits, or modifying the current model

### Requirement: Frozen-entry merged-corpus residual training
The runner SHALL verify and merge the existing large train/development rows
with their corresponding targeted rows, reject duplicate source hashes or
cross-partition seed overlap, keep the r7 entry checkpoint byte-identical, and
select and fit the fixed card-uplift residual family using merged train rows
only.

#### Scenario: Residual fitting begins
- **WHEN** both source corpora and all lineage bindings pass before development access
- **THEN** seed-level train cross-fitting selects one fixed residual configuration and persists canonical model bytes

#### Scenario: Corpus lineage differs
- **WHEN** a dataset, source hash, schedule, checkpoint, or partition identity differs
- **THEN** fitting stops and no development or audit result is claimed

### Requirement: One-shot rare-card development gate
The runner SHALL restore the fitted residual before reading development rows
and evaluate development exactly once. It SHALL report overall and rare-only
regret, ranking, correction, and best-take-versus-skip diagnostics, and all 16
target IDs MUST have train and development support.

#### Scenario: Development gate passes
- **WHEN** the fixed overall gates pass, rare-only mean regret decreases, rare-only pairwise accuracy does not decrease, and best-take-to-skip errors do not increase
- **THEN** the verdict authorizes only a separate fresh simulator/live-shadow evaluation proposal

#### Scenario: Development gate fails
- **WHEN** any fixed gate fails
- **THEN** the residual is not ready and no retry, tuning, audit access, gameplay action authority, or promotion is authorized

### Requirement: Isolated no-authority execution
The study SHALL bind source, native, prior corpus, entry checkpoint, production
checkpoint metadata, and output paths before execution. Training authority
applies only to the registered residual fit; gameplay, CommunicationMod,
production loading, formal RL, audit, policy-quality, qualification, and
promotion authority SHALL remain false.

#### Scenario: Study completes
- **WHEN** collection and residual fitting finish with production bindings unchanged
- **THEN** canonical datasets, model, metrics, report, and manifest artifacts are published without modifying production state
