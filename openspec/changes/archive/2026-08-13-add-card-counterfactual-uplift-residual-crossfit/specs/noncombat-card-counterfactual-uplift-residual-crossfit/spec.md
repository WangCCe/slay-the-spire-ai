## ADDED Requirements

### Requirement: Immutable source-only inputs
The POC SHALL consume only the canonical scorer-pilot train/development datasets
and the tracked r7 entry checkpoint. It MUST bind their hashes and source
identities before fitting and MUST NOT load native code or access audit seeds.

#### Scenario: Input identity differs
- **WHEN** a dataset, checkpoint, row identity, seed schedule, or source binding differs
- **THEN** execution stops before fitting or scoring a residual

### Requirement: Frozen-entry card uplift residual
The POC SHALL keep every entry model tensor byte-identical and SHALL fit card
uplift only from fit-seed `take_return - skip_return` values. It SHALL compose
scores as frozen entry joint log probability plus the selected smoothed uplift
strength, with zero skip uplift and the fit-only global prior for unseen cards.

#### Scenario: Held-out row is scored
- **WHEN** the POC scores a row whose seed was excluded from uplift fitting
- **THEN** it returns one finite composed score per legal action in original order without mutating the entry model

#### Scenario: Held-out card is unseen
- **WHEN** a take action's card id does not occur in the fit seeds
- **THEN** its uplift equals the fit-only global smoothed prior and no held-out return contributes to it

### Requirement: Nested seed-grouped selection
The POC SHALL use four sorted round-robin outer seed folds and three sorted
round-robin inner seed folds. It SHALL select among exactly the 12 registered
shrinkage/strength configurations using only inner cross-fitted metrics and the
registered lexicographic rule, then evaluate the selected fit once on the outer
held-out fold.

#### Scenario: Configuration is selected
- **WHEN** all inner predictions for one outer fold are materialized
- **THEN** exactly one registered configuration is selected deterministically without using the outer held-out returns

#### Scenario: Seed isolation is violated
- **WHEN** any seed contributes to fitting or inner selection for a prediction on that seed
- **THEN** the POC fails before publishing a verdict

### Requirement: Materialized cross-fitted gate
The POC SHALL compare aggregate and per-fold outer-held-out residual predictions
with frozen entry predictions on identical rows. A positive verdict requires
lower aggregate mean regret, nonincreasing aggregate maximum regret, higher
weighted pairwise accuracy, nondecreasing unique-best accuracy, at least two
corrected entry mistakes, no fold maximum-regret increase, and at least three
folds with nonincreasing mean regret.

#### Scenario: Every gate passes
- **WHEN** all aggregate, correction, isolation, determinism, and fold-safety checks pass
- **THEN** the verdict authorizes only a separate consumed-audit proposal

#### Scenario: Any gate fails
- **WHEN** any registered gate fails
- **THEN** the verdict is not ready and the method is not retried or tuned on this corpus

### Requirement: Canonical no-authority publication
The POC SHALL publish canonical configuration, folds, outer predictions,
metrics, and report artifacts. Native loading, audit access, gameplay, model
loading, qualification, promotion, and policy-quality authority MUST remain
false.

#### Scenario: Publication completes
- **WHEN** the source-only POC terminates normally
- **THEN** canonical artifacts reproduce the verdict and contain no deployable or production-loaded model
