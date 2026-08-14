## ADDED Requirements

### Requirement: Exact frozen model binding
The evaluator MUST load the committed state-conditioned shop model only when its
path, hash, architecture, feature width, and selected epoch match exactly.

#### Scenario: Model identity differs
- **WHEN** any bound model field or byte identity differs
- **THEN** evaluation stops before native environment or fresh seed access

### Requirement: One fresh shop cohort
The evaluator SHALL collect one fixed source-complete shop partition from seeds
`95428..95459` under frozen Current continuation.

#### Scenario: Support passes
- **WHEN** complete, informative, action-kind, and replay floors all pass
- **THEN** the frozen model and baselines may be evaluated

#### Scenario: Support fails
- **WHEN** any support floor fails
- **THEN** the run terminates without replacement seeds or retry

### Requirement: Robust untrained distribution gate
The evaluator SHALL compare trained weighted pairwise accuracy with the fixed
75th percentile of untrained model seeds `0..31`.

#### Scenario: Trained model clears robust baseline
- **WHEN** trained pairwise accuracy strictly exceeds the nearest-rank 75th percentile
- **THEN** the initialization-distribution check passes

### Requirement: Terminal fresh-evaluation verdict
The evaluator SHALL combine the robust initialization check with fixed Current
regret and correction guardrails.

#### Scenario: Every gate passes
- **WHEN** trained mean regret improves Current, maximum regret is non-inferior, at least one decision is corrected, corrections are not outnumbered by worsened decisions, and the robust initialization check passes
- **THEN** the verdict permits only a separate live-shadow proposal

#### Scenario: Any gate fails
- **WHEN** any fixed check fails
- **THEN** the verdict is terminal for the model and cohort without tuning or rerun

### Requirement: Evaluation isolation
The evaluator MUST NOT fit a model, access production checkpoints or protected
seed inventories, launch gameplay or CommunicationMod, or alter policy behavior.

#### Scenario: Fresh evaluation executes
- **WHEN** native outcomes and model scores are computed
- **THEN** canonical artifacts prove model-loading-only evaluation and false promotion authority
