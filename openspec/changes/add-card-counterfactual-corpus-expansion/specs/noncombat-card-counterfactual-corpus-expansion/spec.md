## ADDED Requirements

### Requirement: Disjoint reserved seed schedule
The corpus SHALL reserve train seeds `80000..80255`, development seeds
`80256..80319`, and untouched audit seeds `80320..80383`. These sets MUST be
pairwise disjoint and MUST remain fixed in source, registration, and report.

#### Scenario: Corpus collection begins
- **WHEN** source, native, process, production-isolation, and schedule preflight passes
- **THEN** only train and development environments may be constructed and the audit range remains untouched

#### Scenario: Schedule differs
- **WHEN** a seed set overlaps, changes, is replaced, or is accessed outside its registered role
- **THEN** the runner fails without publishing a usable corpus

### Requirement: Bounded complete branch collection
The runner SHALL collect at most two complete card states per seed and four
counterfactual action branches per state. Train SHALL use at most 2,048 branches
and 16 registered Courier censors; development SHALL use at most 512 branches
and four registered Courier censors. Censored seeds MUST NOT be replaced.

#### Scenario: Registered Courier blocker occurs
- **WHEN** a seed reaches unsupported Courier restock semantics
- **THEN** the seed is recorded as censored, contributes no partial state, and collection continues only within the fixed censor bound

#### Scenario: Other blocker or limit occurs
- **WHEN** a nonregistered blocker, branch overflow, deadline, or censor overflow occurs
- **THEN** collection fails without changing seeds or limits

### Requirement: Canonical reusable datasets
The runner SHALL publish byte-round-trippable full train and development
partitions with every source identity, candidate, action return, state tensor,
candidate tensor, branch count, and censor. It MUST require at least 440 train
states and 110 development states.

#### Scenario: Both partitions satisfy support
- **WHEN** collection and canonical round-trip checks complete
- **THEN** both datasets are persisted with bound hashes and exact disjoint seed identities

#### Scenario: Support is insufficient
- **WHEN** either partition misses its fixed complete-state floor
- **THEN** the corpus verdict is not ready and no model training is authorized

### Requirement: Coverage diagnostics without model authority
The report SHALL summarize informative states, cards, action kinds, return
spreads, unseen development cards, branches, transitions, and censors. It MUST
keep training, evaluation, audit access, gameplay, policy-quality, and promotion
authority false.

#### Scenario: Corpus report is published
- **WHEN** both canonical datasets pass every fixed check
- **THEN** the verdict authorizes only a separate source-only training proposal and no policy claim
