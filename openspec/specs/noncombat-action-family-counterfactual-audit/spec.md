# noncombat-action-family-counterfactual-audit Specification

## Purpose

Define a strict read-only audit that binds frozen non-combat scored rows to a
terminal collapse audit, measures flat versus max-pooled action-family
counterfactuals, separates stochastic and deterministic semantics, and grants
no training or runtime authority.

## Requirements

### Requirement: Terminal audit trust root
The system SHALL consume an explicitly supplied canonical terminal collapse
audit and SHALL require its expected schema, terminal status and verdict,
unaccessed holdout state, and exact all-false authority before opening scored
row artifacts.

#### Scenario: Valid terminal trust root
- **WHEN** the supplied collapse audit has the expected terminal identity and all authority fields are false
- **THEN** the system permits validation of the two scored-row artifacts named by that audit

#### Scenario: Trust-root drift
- **WHEN** schema, status, verdict, holdout state, canonical encoding, or authority differs from the required terminal boundary
- **THEN** the system fails without publishing either output

### Requirement: Exact scored-row source binding
The system SHALL open only `training_rows.json` and `evaluation.json` beneath
the explicit source root and SHALL verify their exact relative paths, byte
sizes, SHA-256 digests, canonical JSON encoding, and non-symlink containment
against the source identities recorded by the terminal audit.

#### Scenario: Exact source identities
- **WHEN** both artifacts exactly match their terminal-audit identities and remain within the non-symlink source root
- **THEN** the system accepts them as the complete counterfactual input set

#### Scenario: Source identity or containment mismatch
- **WHEN** an artifact is missing, modified, noncanonical, symlinked, outside the source root, or does not match its recorded size and digest
- **THEN** the system fails without publication and does not inspect an alternate artifact

### Requirement: Frozen diagnostic-row validation
The system SHALL validate training, initial-canary, and trained-canary decision
rows for expected category counts, nonempty unique candidate action identities,
candidate `kind`, selected-action membership, score coverage, finite score
values, and exact reconciliation with the terminal audit. It MUST require the
evaluation holdout wrapper to state `accessed=false` and `episode_count=0`.

#### Scenario: Valid frozen diagnostics
- **WHEN** all diagnostic rows and aggregate counts reconcile with the terminal audit
- **THEN** the system analyzes exactly those rows grouped by phase and category

#### Scenario: Invalid row or holdout access
- **WHEN** a row is malformed, identities or scores are misaligned, counts drift, or the holdout wrapper indicates access
- **THEN** the system fails closed without publishing results or reading holdout rows

### Requirement: Checked-in family distribution semantics
The system SHALL apply the checked-in
`build_action_family_distribution` implementation to CPU float32 row scores and
SHALL require its expected max-family aggregation, float64 distribution,
entropy decomposition, candidate and family identity fields, and exact
all-false authority metadata. Ordinary float64 candidate softmax SHALL be used
only as the flat descriptive control.

#### Scenario: Distribution metadata and invariants match
- **WHEN** the checked-in helper has the expected metadata and each row satisfies probability normalization and entropy decomposition
- **THEN** the system records flat and hierarchical metrics for that row

#### Scenario: Helper or mathematical drift
- **WHEN** helper metadata, probability normalization, one-family fallback, or entropy decomposition differs from the required behavior
- **THEN** the system fails without substituting another implementation

### Requirement: Counterfactual metrics distinguish semantics
For each phase and category, the system SHALL report row and family counts,
flat and hierarchical family mass, family, conditional and joint entropy,
one-family and multi-family opportunity counts, raw-score tie counts, raw-score
argmax versus joint-probability-argmax transitions, and two-stage score-argmax
equivalence outside ties.

#### Scenario: Multi-family decision
- **WHEN** a row contains more than one candidate family
- **THEN** the report separately records family-mass reallocation and any joint-probability argmax transition

#### Scenario: Single-family decision
- **WHEN** a row contains exactly one candidate family
- **THEN** the report proves zero family entropy and exact fallback to ordinary within-family softmax

#### Scenario: Score tie
- **WHEN** more than one candidate shares the maximum raw score
- **THEN** the report counts the tie and excludes it from deterministic two-stage equivalence claims

### Requirement: Deterministic bounded publication
The system SHALL publish canonical JSON and deterministic Markdown only to two
explicit output paths outside the source root. It SHALL stage both payloads and
atomically replace each file only after all validation succeeds. On a handled
replacement failure it SHALL restore any already-replaced destination; if that
rollback also fails, it SHALL preserve the recovery backup and report the
incomplete rollback. It SHALL NOT claim that two independent paths form a
crash-atomic transaction. Both reports SHALL state that the audit provides no
training, model-loading, native-loading, seed-access, experiment, qualification,
promotion, gameplay, or formal-RL authority.

#### Scenario: Repeated valid audit
- **WHEN** the same exact inputs and implementation are audited twice
- **THEN** the JSON and Markdown outputs are byte-identical

#### Scenario: Failure before publication
- **WHEN** validation or analysis fails at any point
- **THEN** neither destination is partially replaced and no authority is granted

#### Scenario: Handled replacement failure
- **WHEN** one destination was replaced and a later replacement raises an error
- **THEN** the system restores the earlier destination or preserves its recovery backup if rollback itself fails
