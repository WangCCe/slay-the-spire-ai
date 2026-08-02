## ADDED Requirements

### Requirement: Train-only evidence isolation
The POC SHALL derive and consume one canonical train-only dataset from the
preserved baseline warm-start demonstrations. It SHALL bind the source artifact
and manifest identities, require exactly the registered train seeds and native
teacher policy, validate every retained row, and SHALL NOT use validation or
final-test rows in features, fitting, selection, thresholds, or metrics.

#### Scenario: Registered train evidence is prepared
- **WHEN** the preparation command receives the hash-matching preserved warm-start artifact and manifest
- **THEN** it SHALL publish a canonical dataset containing only the registered train cohort and its source identities
- **AND** each retained target SHALL map exactly once to its complete legal candidate set

#### Scenario: Non-train evidence reaches the model boundary
- **WHEN** a model or evaluation input contains a validation seed, final-test seed, unregistered seed, or non-train cohort field
- **THEN** the POC SHALL fail closed before feature construction or fitting

### Requirement: Structured permutation-invariant candidate features
The POC SHALL provide a versioned structured feature projection for route,
card-reward, shop, and event candidates. State collection summaries SHALL be
independent of irrelevant list order, category features SHALL be relative to
the candidate being scored, and the projection SHALL exclude teacher,
successor, terminal outcome, reward, baseline history, seed identity, and other
post-action leakage.

#### Scenario: State collections are reordered
- **WHEN** semantically identical deck, relic, potion, or map-node collections are presented in a different source order
- **THEN** every candidate SHALL receive byte-identical structured features and scores

#### Scenario: Category-relative context is available
- **WHEN** a valid route, card-reward, shop, or event row is projected
- **THEN** its feature record SHALL include the registered category-specific state, candidate, and interaction summaries
- **AND** all numeric values SHALL be finite and all categorical hashing SHALL be deterministic

#### Scenario: Leakage is inserted
- **WHEN** teacher labels, successor state, terminal floor, outcome, reward, seed identity, or baseline action history differ while the legal decision state is otherwise identical
- **THEN** the structured policy features and scores SHALL remain unchanged

### Requirement: Complete candidate preservation and category-specific ranking
The structured ranker SHALL score every legal candidate in original adapter
order using one registered category-specific head for the current decision. It
SHALL neither filter candidates nor use a teacher fallback, and its selected
action SHALL always be a member of the reported set.

#### Scenario: A multi-candidate decision is scored
- **WHEN** the ranker receives a valid decision and complete legal candidate list
- **THEN** it SHALL emit one finite score and probability per candidate in the original order
- **AND** it SHALL select exactly one reported action id using the registered deterministic tie rule

#### Scenario: Candidate integrity is violated
- **WHEN** a candidate is missing, duplicated, unavailable, in the wrong category, or cannot be projected
- **THEN** the ranker SHALL fail closed instead of repairing, dropping, or replacing the action set

### Requirement: Seed-grouped train-only comparison
The POC SHALL compare exactly the registered legacy control and structured
candidate under deterministic seed-grouped folds. All decisions from one seed
MUST remain on one side of each fold, both candidates SHALL receive the same
eligible rows and registered training schedule, and only rows with at least two
legal candidates SHALL contribute gradients or competence metrics.

#### Scenario: Cross-validation folds are built
- **WHEN** the registered train seeds are partitioned
- **THEN** the fold assignment SHALL be deterministic, exhaustive, mutually exclusive, and reproducible
- **AND** no seed or decision SHALL occur in both fit and held-out rows for a fold

#### Scenario: Singleton decisions are encountered
- **WHEN** a row has exactly one legal candidate
- **THEN** it SHALL be counted and checked separately for schema and legality
- **AND** it SHALL NOT contribute to optimization loss, agreement, cross entropy, macro agreement, or candidate selection

### Requirement: Multi-candidate implementation-fit verdict
The evaluator SHALL report aggregate, per-category, per-fold, and paired
held-out metrics for real multi-candidate decisions. It SHALL apply only the
registered gate, distinguish a valid negative result from a blocked execution,
and SHALL NOT reinterpret the verdict as simulator rollout or policy-quality
evidence.

#### Scenario: Structured candidate satisfies the fixed gate
- **WHEN** deterministic replay and all structural checks pass and every registered multi-candidate delta, non-regression, cross-entropy, coverage, and resource threshold passes
- **THEN** the verdict SHALL be `structured_candidate_selected`
- **AND** the result SHALL authorize only a separate fresh-study preregistration

#### Scenario: Structured candidate misses a competence threshold
- **WHEN** the execution is valid and reproducible but one or more registered selection thresholds fail
- **THEN** the verdict SHALL be `poc_valid_without_structured_candidate`
- **AND** the POC SHALL stop without an alternate model, schedule, fold assignment, or retry

#### Scenario: Evidence integrity fails
- **WHEN** an identity, cohort, candidate, fold, finite-value, determinism, resource, or artifact contract fails
- **THEN** the verdict SHALL be `blocked`
- **AND** no candidate SHALL be selected

### Requirement: Bounded deterministic no-authority artifacts
The POC SHALL atomically publish hash-closed configuration, train-input
identity, fold assignment, candidate models, held-out predictions, metrics,
verdict report, and manifest from one bounded execution and one identical
replay. Timing SHALL remain noncanonical, and every downstream authority flag
SHALL be false.

#### Scenario: Primary execution and replay complete
- **WHEN** both registered executions finish within their bounds
- **THEN** all canonical dataset, fold, model, prediction, metric, report, and manifest identities SHALL match exactly
- **AND** the manifest SHALL close the exact managed inventory

#### Scenario: Result is inspected for downstream use
- **WHEN** any consumer reads the POC manifest or report
- **THEN** simulator rollout, new native evidence, live gameplay, live loading, DAgger, formal RL, qualification, OPE reinterpretation, and promotion authority SHALL all be false
- **AND** no production checkpoint or policy-discovery path SHALL include the POC model
