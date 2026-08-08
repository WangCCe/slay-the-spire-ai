# noncombat-cross-fitted-baseline-support-audit Specification

## Purpose
Define the immutable source-only audit that reconstructs cross-fitted baseline
support and card-reward take-family pressure from the sealed 20260808-r2
hierarchical-learning evidence without granting downstream execution authority.

## Requirements
### Requirement: Immutable verified r2 evidence and pushed audit source
The audit SHALL consume only the tracked terminal bundle and closeout for
`noncombat-cross-fitted-hierarchical-learning-successor-20260808-r2` as
published by commit `7f2f08878e08d9276425f2fb99a97cf095361c9e`. Before analysis it SHALL run the
standard-library independent terminal verifier, acquire and retain a
non-blocking exclusive lock on the exact inactive execution lease, and while
locked revalidate the terminal, manifest, registration, authorization,
complete artifact inventory, checkpoint/evidence chain, isolation identity,
and closeout bindings. The audit source and test bytes SHALL match one explicit
pushed source commit whose HEAD and origin/master identities agree.

#### Scenario: Exact source and terminal evidence pass
- **WHEN** the pushed audit source, verifier result, inactive lease, terminal
  identity, manifest, every managed artifact, and r2 closeout all match their
  fixed bytes and digests
- **THEN** the audit may stream the already recorded chunk evidence without
  loading Torch, native code, a model, an environment, or any seed outcome

#### Scenario: Source, lease, or evidence differs
- **WHEN** source identity, Git ancestry, lease liveness or identity, terminal
  self-digest, manifest closure, artifact size or digest, checkpoint chain,
  isolation evidence, or closeout binding differs
- **THEN** the audit fails before analytical publication and does not repair,
  copy, substitute, or mutate any consumed artifact

### Requirement: Exact cross-fitted baseline reconstruction
For every recorded decision the audit SHALL validate chunk, trajectory,
decision, fold, fit-trajectory, held-out-trajectory, feature, raw return,
unclipped prediction, clipped prediction, clipping indicator, residual, and
advantage relationships against the independently verified evidence. Each
chunk SHALL contain exactly four trajectory-disjoint folds with 48 fit and 16
held-out trajectories per fold. The audit SHALL preserve lower and upper
clipping separately and SHALL NOT refit a baseline or change the registered
`[0,3]` prediction bounds.

#### Scenario: Cross-fitted rows reconcile
- **WHEN** all eight chunks reproduce the registered folds, predictions,
  clipping, residuals, advantages, and checkpoint summaries
- **THEN** the audit emits exact aggregate counts and residual summaries without
  fitting, imputing, coercing, or dropping a row

#### Scenario: A baseline relationship drifts
- **WHEN** a held-out trajectory appears in its fit set, a fold has the wrong
  support, a prediction or advantage identity differs, or a clipping indicator
  disagrees with the fixed bounds
- **THEN** the audit rejects the evidence rather than recomputing a nearby
  baseline or accepting an approximate row

### Requirement: Fixed baseline-support strata
The audit SHALL report count, clipping count and rate, raw-return mean,
prediction mean, residual RMSE, advantage mean and sign counts, selected-family
counts, and greedy-family counts by chunk, fold, category, clipping status,
selected family, advantage sign, pre-decision effective-floor bands `<17`,
`17..33`, and `>=34`, and card-reward ordinals `first`, `second`, and `later`.
A binary clipped/unclipped comparison SHALL be supported only when it contains
at least 64 rows and at least 16 rows on each side. A selected `take`/`skip`
comparison SHALL additionally require at least 16 rows from each selected
family. Sparse strata SHALL retain exact counts and remain insufficient without
merging bands or changing thresholds.

#### Scenario: A fixed stratum has support
- **WHEN** a preregistered stratum meets every applicable total, clipping-side,
  and selected-family minimum
- **THEN** the report marks it supported and emits both sides separately with
  no independent-row confidence or causal claim

#### Scenario: A fixed stratum is sparse
- **WHEN** any applicable support minimum is absent
- **THEN** the report marks the stratum insufficient, preserves raw counts, and
  does not merge, extrapolate, or tune a boundary

### Requirement: Cross-fitted card-reward pressure and saturation reconciliation
For each multi-family card-reward decision, the audit SHALL reconstruct the
direct take-family logit update pressure using its recorded cross-fitted
advantage, selected family, family probability, family entropy, take-family
conditional entropy, expected conditional entropy, registered entropy
coefficients, and total chunk decision count. Positive pressure SHALL mean that
gradient descent directly raises the row-local `take` family logit before
shared-parameter effects. Aggregate scalar policy components SHALL reconcile
with the stored chunk ledger, while stored full-gradient vectors and their
legacy comparison remain a separate verified diagnostic.

The audit SHALL also reconstruct the registered final-window saturation
predicate, report all greedy-family counts, and preserve the exact coordinate
and family of every non-`take` exception. It SHALL NOT change the predicate or
interpret one exception as robust policy diversity.

#### Scenario: Direct pressure and full gradient reconcile
- **WHEN** all card-reward policy terms and chunk gradient ledgers are exact
- **THEN** the report publishes direct pressure by fixed support strata and the
  separately recorded full-gradient comparison without claiming equivalence

#### Scenario: Final-window near saturation is exact
- **WHEN** the registered final four chunks contain 1,773 greedy `take` rows and
  one different greedy-family row among 1,774 multi-family decisions
- **THEN** the audit records both `stop=false` under the immutable predicate and
  the exact 1,773/1 descriptive concentration without changing a threshold

### Requirement: Bounded descriptive verdict
After exact reconstruction, the audit SHALL emit exactly one of
`take_pressure_persists_on_supported_unclipped_rows`,
`take_pressure_concentrated_in_clipped_rows`,
`take_pressure_not_consistently_aligned`, or
`insufficient_support_or_evidence`. The verdict SHALL depend only on fixed
clipped/unclipped support, direct take-logit pressure signs, and final-window
chunk consistency. It SHALL make no policy-quality, causal, OPE, formal-RL,
target-supported-outcome, or promotion claim.

#### Scenario: Pressure persists beyond clipping
- **WHEN** clipped and unclipped comparisons are supported, both have positive
  aggregate direct take pressure, and every supported final-window unclipped
  chunk has positive pressure
- **THEN** the verdict is
  `take_pressure_persists_on_supported_unclipped_rows`

#### Scenario: Pressure is concentrated in clipped rows
- **WHEN** the clipped comparison is supported and positive while the supported
  unclipped comparison is nonpositive
- **THEN** the verdict is `take_pressure_concentrated_in_clipped_rows`

#### Scenario: Pressure is not consistently aligned
- **WHEN** applicable supported aggregates have another nonuniform sign pattern
  or a supported final-window unclipped chunk is nonpositive
- **THEN** the verdict is `take_pressure_not_consistently_aligned`

#### Scenario: Required support is absent
- **WHEN** exact reconstruction passes but a required clipped/unclipped or
  take/skip support minimum is absent
- **THEN** the verdict is `insufficient_support_or_evidence`

### Requirement: Deterministic source-only publication with all authority false
The audit SHALL publish one compact canonical JSON report and one Markdown
summary from a pushed source identity. Two fresh isolated source-only processes
using separate staging paths SHALL produce byte-identical outputs. The report
SHALL bind exact source and input identities, verifier results, reconstruction
counts, fixed strata, verdict inputs, limitations, and an all-false authority
map. It SHALL contain no raw model state or unrestricted decision dump.

#### Scenario: Publication succeeds
- **WHEN** source/input verification, reconstruction, support, pressure,
  saturation, determinism, and import-isolation gates all pass
- **THEN** the byte-identical reports may be published without modifying the r2
  bundle or granting execution, training, replay, evaluation, OPE, native/model
  loading, gameplay, CommunicationMod, qualification, or promotion authority

#### Scenario: A downstream action is requested
- **WHEN** any audit result is cited as direct authority for an algorithm
  change, new cohort, experiment, checkpoint, evaluation, live policy, or
  formal-RL claim
- **THEN** the request remains blocked pending a separate reviewed proposal and
  any required fresh authorization
