## ADDED Requirements

### Requirement: Published trust root and sealed gradients are immutable
The audit SHALL require the exact canonical 20260809 card-acceptance JSON and
Markdown, including their expected digests, schema, verdict, counts, source
identity, terminal-verification result, input bindings, limitations, and exact
all-false authority. It SHALL acquire and hold the inactive execution lease
while independently verifying and reading only the terminal, manifest,
checkpoint, and eight gzip chunk artifacts named by that trust root. It SHALL
bind every reused helper source and reject symlinks, reparse points, active or
malformed leases, untracked analytical inputs, byte drift, identity drift, or
structural drift.

#### Scenario: Exact trust root and source evidence are present
- **WHEN** the published reports and every named sealed artifact match all fixed identities and remain under the held inactive lease
- **THEN** the audit may reconstruct the recorded source-only gradient evidence

#### Scenario: One identity or authority differs
- **WHEN** any report, source, terminal, manifest, checkpoint, chunk, lease, digest, size, schema, count, verdict, limitation, or authority differs
- **THEN** the audit fails before analysis and does not substitute, repair, rediscover, or partially trust evidence

### Requirement: Recorded gradient components reconstruct exactly
For each of the eight ordered chunks, the audit SHALL decode the five bound
finite float64 component vectors and independently retained full vector using
standard-library code. It SHALL verify dtype, byte order, shape, component
order, data digest, scalar reconciliation, component-sum reconstruction,
registered clipping inputs and outputs, and the previously published norms,
dots, cosines, and clip factor within fixed arithmetic tolerance.

#### Scenario: One chunk reconstructs
- **WHEN** every vector, scalar, and clipping field is exact and finite
- **THEN** the audit retains the complete component vectors in memory for fixed counterfactual composition without publishing raw values

#### Scenario: Gradient evidence is malformed
- **WHEN** a vector is missing, nonfinite, misordered, wrongly typed, incorrectly shaped, digest-mismatched, scalar-inconsistent, or incompatible with the retained full gradient
- **THEN** the audit aborts publication without transforming that chunk

### Requirement: Fixed objective interventions are parameter-free
The audit SHALL compare exactly `recorded`, `family_policy_ablated`, and
`conditional_conflict_guarded` compositions. With `F` equal to card-reward
family-policy gradient, `C` equal to card-reward conditional-policy gradient,
and `R` equal to all remaining recorded components, `recorded` SHALL be
`F+C+R`, `family_policy_ablated` SHALL be `C+R`, and the guarded family
component SHALL equal `F-dot(F,C)/||C||^2*C` only when `dot(F,C)<0` and
`||C||>0`; otherwise it SHALL equal `F`. No coefficient, threshold, candidate,
or transform SHALL be fitted, searched, ranked, or selected from the evidence.

#### Scenario: Family and conditional components conflict
- **WHEN** `dot(F,C)` is negative and `C` has nonzero norm
- **THEN** the guarded family component is orthogonal to `C` within fixed arithmetic tolerance and all non-conflicting family directions are retained

#### Scenario: Family and conditional components do not conflict
- **WHEN** `dot(F,C)` is nonnegative and `C` has nonzero norm
- **THEN** the guarded family component is byte-for-byte identical to `F`

#### Scenario: Conditional support is degenerate
- **WHEN** `C` has zero norm in any chunk
- **THEN** no division or imputation occurs and that chunk is reported as unsupported for conflict projection

#### Scenario: Counterfactual summaries are emitted
- **WHEN** a fixed composition is valid
- **THEN** the audit reports raw and frozen-rule clipped norms, component retention, displacement from recorded, and dots and cosines against `F`, `C`, and the recorded full gradient
- **AND** full-gradient alignment remains descriptive and grants no policy or causal interpretation

### Requirement: Independent acceptance coordinate has synthetic invariants
The audit SHALL define a pure source-only synthetic distribution with an
acceptance-family logit independent of within-`take` conditional logits. In a
registered smooth fixture with at least two valid families, interior family
mass, and a nonzero finite translation producing distinct representable
masses, the acceptance translation SHALL change family mass while leaving all
within-`take` probabilities, ordering, entropy, and margins unchanged. In a
registered smooth fixture, a fixed nonzero finite zero-sum conditional
perturbation producing a representably distinct conditional distribution SHALL
change that distribution while preserving the acceptance logit and family mass. One-family fallback
SHALL have family mass one and an inactive acceptance coordinate. Analytical
derivatives SHALL match finite differences within fixed tolerance only at
smooth nontied points.

#### Scenario: Acceptance coordinate changes
- **WHEN** only the independent acceptance-family logit in the registered multi-family smooth fixture is translated by its fixed nonzero finite amount
- **THEN** take-family mass changes and every within-take conditional quantity remains unchanged

#### Scenario: Conditional coordinate changes
- **WHEN** only the registered fixed nonzero finite zero-sum within-take perturbation is applied at a smooth point and produces representably distinct probabilities
- **THEN** the conditional distribution changes while the acceptance logit and take-family mass remain unchanged

#### Scenario: Only one family exists
- **WHEN** every synthetic candidate belongs to one family
- **THEN** family mass is one, the acceptance coordinate is inactive, and an attempted acceptance translation changes neither family nor conditional quantities

#### Scenario: Max-pooled control changes its maximum take score
- **WHEN** a unique maximum take-candidate score is perturbed in the max-pooled control
- **THEN** the audit records that family mass and conditional choice can change together and does not label the control independent

#### Scenario: A max-pooled maximum is tied
- **WHEN** multiple take candidates share the maximum score
- **THEN** all tie identities remain explicit and the audit makes no unique derivative claim at the boundary

### Requirement: Bounded verdict and deterministic publication grant no authority
Identity or reconstruction failure SHALL prevent publication. After all gates
pass, the verdict SHALL be `insufficient_conditional_gradient_support` when any
chunk has zero conditional-policy norm,
`no_recorded_family_conditional_conflict` when every family/conditional dot is
nonnegative, and `bounded_conditional_conflict_guard_feasible` when at least one
chunk conflicts and every conflicting chunk is projected to zero while every
non-conflicting chunk is unchanged. The verdict SHALL select no intervention.
Two fresh isolated source-only processes using separate staging roots SHALL
produce byte-identical canonical JSON no larger than 1,048,576 bytes and
Markdown no larger than 65,536 bytes, with no raw vector or unrestricted
decision dump and an exact all-false authority map.

#### Scenario: Conflicting chunks are guarded exactly
- **WHEN** at least one chunk has a negative family/conditional dot and every transformation invariant passes
- **THEN** the verdict is `bounded_conditional_conflict_guard_feasible` without recommending an objective, architecture, coefficient, or successor

#### Scenario: Conditional support is absent
- **WHEN** any chunk has zero conditional-policy norm after exact reconstruction
- **THEN** the verdict is `insufficient_conditional_gradient_support`; the unsupported chunk remains unchanged and unprojected while valid chunks may retain deterministic summaries without imputation or threshold tuning

#### Scenario: Isolated publications agree
- **WHEN** the same pushed source and exact inputs are processed in two fresh isolated source-only processes
- **THEN** their canonical JSON and Markdown bytes are identical and publish complete identities, predicates, intervention summaries, limitations, and all-false authority

#### Scenario: A downstream run or policy claim is requested
- **WHEN** any result is cited to choose or change an objective, coefficient, architecture, ranker, checkpoint, experiment, evaluation, or live policy
- **THEN** the request remains blocked pending a separate reviewed proposal and any required execution authorization
- **AND** the audit grants no execution, replay, seed-access, fitting, training, evaluation, OPE, model-loading, native-loading, gameplay, CommunicationMod, formal-RL, qualification, promotion, policy-quality, or causal authority
