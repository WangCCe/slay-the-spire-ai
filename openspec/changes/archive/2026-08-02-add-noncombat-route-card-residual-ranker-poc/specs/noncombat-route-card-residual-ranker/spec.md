## ADDED Requirements

### Requirement: Bound train-only evidence and lineage
The POC SHALL consume only the hash-bound canonical warm-start train input and
SHALL bind the completed structured-ranker negative result as immutable
lineage. Validation rows, final-test rows, native simulator state, live state,
outcomes, rewards, prior predictions, and prior metrics MUST NOT contribute to
feature construction, fitting, thresholds, selection, or result metrics.

#### Scenario: Registered evidence is loaded
- **WHEN** the runner receives the exact registered train input, manifest,
  implementation, runtime, and lineage artifacts
- **THEN** it SHALL validate every identity before feature construction
- **AND** it SHALL retain exactly the registered seeds and complete legal
  candidate sets

#### Scenario: Unregistered evidence reaches the model boundary
- **WHEN** an identity differs or a non-train cohort, native result, live result,
  outcome, reward, prior prediction, or prior metric is supplied as model input
- **THEN** the POC SHALL fail closed before fitting

### Requirement: Shared frozen legacy base
Each fold SHALL train exactly one registered legacy base on its fit seeds and
SHALL freeze and share that exact model between the control and residual
candidate. A seed and all of its decisions MUST remain entirely on one side of
the fold, and singleton decisions MUST remain excluded from fitting and
competence metrics.

#### Scenario: A fold is evaluated
- **WHEN** the legacy base completes its registered fit schedule
- **THEN** the control and candidate SHALL receive byte-identical base model
  parameters and base logits for every held-out row
- **AND** neither evaluation path SHALL update the base parameters

#### Scenario: Fold or row isolation is violated
- **WHEN** fit and held-out seeds overlap, candidates receive different rows,
  a singleton contributes to loss or competence metrics, or a base parameter
  changes after freezing
- **THEN** the POC SHALL fail closed

### Requirement: Bounded route and card residual
The sole candidate SHALL add the registered zero-initialized, category-specific
structured residual to frozen legacy logits only for route and card-reward
decisions. It SHALL score every legal candidate in adapter order, preserve the
registered first-max tie rule, and keep every residual correction within the
registered magnitude bound.

#### Scenario: Route or card reward is scored
- **WHEN** a valid multi-candidate route or card-reward row is evaluated
- **THEN** each candidate logit SHALL equal its frozen legacy logit plus the
  registered bounded structured residual
- **AND** the output SHALL contain one finite score and probability for every
  original candidate

#### Scenario: Residual integrity is violated
- **WHEN** a residual changes an event/shop row, exceeds its bound, filters or
  reorders candidates, depends on excluded evidence, or produces a non-finite
  value
- **THEN** the POC SHALL fail closed

### Requirement: Exact event and shop delegation
The residual candidate SHALL delegate event and shop decisions directly to the
shared frozen legacy base. Candidate ids, logits, probabilities, selected
action, target probability, and tie behavior MUST be byte-identical to the
control on every such held-out row.

#### Scenario: Event or shop is evaluated
- **WHEN** the paired evaluator scores a valid event or shop row
- **THEN** it SHALL record exact control/candidate equality for all delegated
  outputs
- **AND** the row SHALL contribute unchanged to aggregate metrics

#### Scenario: Delegated output differs
- **WHEN** any event or shop control/candidate output differs
- **THEN** the execution SHALL be classified `blocked`
- **AND** no model SHALL be selected

### Requirement: Materialized paired terminal gate
The evaluator SHALL publish aggregate, per-category, and per-fold agreement and
cross-entropy metrics for control and candidate, paired deltas, delegation
proofs, residual diagnostics, and every registered threshold result. It SHALL
apply exactly the preregistered terminal gate without reconstructing a required
check from another artifact or changing a threshold after execution.

#### Scenario: Candidate passes every registered check
- **WHEN** replay, delegation, structural, resource, residual-bound, aggregate,
  category, and every-fold checks all pass
- **THEN** the verdict SHALL be `route_card_residual_selected`
- **AND** the result SHALL authorize only a separate fresh-study proposal

#### Scenario: Candidate misses an implementation-fit threshold
- **WHEN** the execution is valid and reproducible but any agreement or
  cross-entropy threshold fails
- **THEN** the verdict SHALL be `poc_valid_without_route_card_residual`
- **AND** no model SHALL be selected or alternate POC attempted on this corpus

#### Scenario: Required metric is absent
- **WHEN** an aggregate, category, per-fold, delegation, residual, replay,
  coverage, or resource check cannot be materialized
- **THEN** the verdict SHALL be `blocked`

### Requirement: Deterministic bounded no-authority publication
One bounded primary execution and one identical replay SHALL atomically publish
hash-closed configuration, folds, training histories, models, predictions,
metrics, verdict report, manifest, and one noncanonical timing journal. The
manifest SHALL close the exact managed inventory, and every downstream
authority flag SHALL be false.

#### Scenario: Primary execution and replay complete
- **WHEN** both registered executions finish within their row, candidate, fit,
  residual, and wall-time bounds
- **THEN** every canonical identity and verdict SHALL match exactly
- **AND** the selected all-train model SHALL exist only after a passing gate

#### Scenario: Result is inspected for downstream use
- **WHEN** a consumer reads any published result
- **THEN** native evidence collection, simulator rollout, live gameplay, live
  loading, DAgger, formal RL, OPE reinterpretation, qualification, policy
  promotion, and policy-quality authority SHALL all be false
