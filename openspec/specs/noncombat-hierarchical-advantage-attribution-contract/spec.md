# noncombat-hierarchical-advantage-attribution-contract Specification

## Purpose

Define source-only trajectory-disjoint advantage provenance, exact shared-
parameter gradient component accounting, uniform clipping evidence, and the
minimum all-false observability boundary for any future empirical successor.

## Requirements

### Requirement: Advantage provenance is trajectory-disjoint
The contract SHALL group every supplied decision by stable trajectory and fold
identity. Every decision in one trajectory SHALL use one held-out fold, and the
complete set of trajectories assigned to that fold SHALL be disjoint from the
data-derived baseline-fit and scale-fit trajectory sets. Data-derived fit
identities SHALL be complete, unique, canonically ordered, nonempty, and
digest-bound. An explicit fixed-zero baseline and fixed-unit scale compatibility
mode SHALL carry no fit identities and SHALL NOT claim to reduce confounding.

#### Scenario: Cross-fitted provenance is valid
- **WHEN** every held-out fold is disjoint from the complete baseline and scale fit sets and every trajectory uses exactly one fold
- **THEN** the contract accepts the provenance and binds its canonical fold and fit-set digests

#### Scenario: One held-out trajectory leaks into fitting
- **WHEN** a target trajectory or any peer trajectory in its held-out fold appears in a baseline-fit or data-derived-scale-fit set
- **THEN** the contract rejects the complete batch before returning an advantage or attribution result

#### Scenario: One trajectory is split across folds
- **WHEN** decisions with the same trajectory identity reference different held-out folds
- **THEN** the contract rejects the batch rather than treating the decisions as independent samples

### Requirement: Advantage arithmetic uses only pre-decision control variates
Each accepted decision SHALL bind a finite raw return, finite baseline
prediction, positive finite scale, and pre-decision state-feature identity. The
contract SHALL compute exactly
`(raw_return - baseline_prediction) / scale` and SHALL NOT apply another
batch, fold, trajectory, or decision-level centering or normalization. A fixed
unit scale SHALL be explicit; every data-derived scale SHALL carry held-out
trajectory provenance.

#### Scenario: A held-out advantage is constructed
- **WHEN** a decision supplies valid trajectory-disjoint prediction and scale provenance
- **THEN** the returned advantage equals the exact registered residual-over-scale arithmetic and preserves the raw inputs and provenance

#### Scenario: Return and baseline shift together
- **WHEN** the same finite constant is added to a raw return and its supplied baseline prediction while scale and provenance remain unchanged
- **THEN** the computed advantage is unchanged

#### Scenario: Explicit zero baseline uses unit scale
- **WHEN** a valid record declares the compatibility baseline as exactly zero and the scale mode as fixed unit
- **THEN** the computed advantage equals the raw return without creating fit provenance

#### Scenario: Baseline input uses post-action information
- **WHEN** baseline feature provenance includes selected action or family, candidate scores, successor transition, reward, terminal outcome, or any later observation
- **THEN** the contract rejects the record before computing an advantage

#### Scenario: Scale is invalid or hidden
- **WHEN** scale is nonfinite, nonpositive, data-derived without disjoint fit provenance, or followed by an undeclared normalization
- **THEN** the contract fails closed rather than coercing or stabilizing the value

### Requirement: Named components reconstruct the shared-parameter gradient
The contract SHALL accept finite scalar components named
`card_reward_family_policy`, `card_reward_conditional_policy`, `other_policy`,
`family_entropy_regularizer`, and `conditional_entropy_regularizer` over one
uniquely named, ordered CPU float32 parameter set. The full scalar loss SHALL
be supplied separately and SHALL equal their sum. Its independently
differentiated full gradient SHALL match the elementwise sum of component
gradients under the frozen dtype-aware tolerance; a component-unused parameter
SHALL contribute an explicit aligned zero tensor.

#### Scenario: Shared gradients reconstruct
- **WHEN** all five connected scalar components and ordered parameters are valid
- **THEN** the ledger reports each aligned component vector, their complete sum, the independently differentiated full vector, norms, pairwise dot products and cosines, and bounded reconstruction residuals

#### Scenario: Components cancel through shared parameters
- **WHEN** two valid component vectors oppose one another on any shared parameter
- **THEN** the ledger preserves both signed vectors and their cancellation instead of reporting only absolute pressure or component norms

#### Scenario: Parameter or component identity drifts
- **WHEN** a component is missing, added, detached, nonfinite, mislabeled, or scalar-shape-invalid, the separately supplied full loss differs from the component sum, or a parameter name, order, shape, dtype, device, or finiteness check differs
- **THEN** the contract rejects the ledger without reordering, dropping, or imputing evidence

### Requirement: Uniform clipping preserves bounded gradient additivity
The contract SHALL use the fixed complete-gradient norm ceiling `1.0` and the
registered uniform global-norm clip semantics. It SHALL derive one clip factor
from the complete pre-clip gradient and apply that same factor to every
component, so clipped components reconstruct the clipped complete gradient. It
SHALL NOT accept optimizer state or a parameter delta, apply component-specific
clipping, or describe clipped gradients as Adam updates.

#### Scenario: Complete gradient exceeds the ceiling
- **WHEN** the pre-clip complete norm is greater than `1.0`
- **THEN** every component receives the same bounded clip factor and both pre-clip and post-clip reconstruction checks pass

#### Scenario: Complete gradient is already bounded
- **WHEN** the pre-clip complete norm is at most `1.0`
- **THEN** the clip factor is exactly one and no component vector changes

#### Scenario: Caller supplies optimizer attribution inputs
- **WHEN** a caller supplies optimizer state, a parameter delta, or a request to clip components independently
- **THEN** the contract rejects the request before publishing gradient attribution

### Requirement: Synthetic evidence exposes the row-local limitation
The capability SHALL render deterministic source-only evidence from fixed tiny
shared-ranker fixtures. It SHALL include one aligned fixture and one fixture in
which a card-reward row has positive direct family-logit pressure while the
complete shared-parameter direction has opposing pressure on a fixed probe
margin. No fixture SHALL load a checkpoint, empirical model, native module,
environment, or seed.

#### Scenario: Synthetic report is reproduced
- **WHEN** two fresh source-only processes render the fixed fixtures
- **THEN** canonical JSON and generated Markdown bytes are identical and all advantage, gradient, clipping, and limitation checks agree

#### Scenario: Direct and shared directions disagree
- **WHEN** the fixed opposing fixture is evaluated
- **THEN** the report preserves both signs and states that row-local logit pressure is insufficient to identify the full shared-parameter update

#### Scenario: Max-pooled family scores tie
- **WHEN** a fixed synthetic fixture ties the maximum score within or across families
- **THEN** gradient evidence preserves the checked-in max-pool tie semantics and stable component and parameter identity without using candidate order as an attribution tie-break

#### Scenario: Existing runtimes are imported
- **WHEN** the hierarchical control plane, runtime, ranker, policy input, agent, or production entry point is imported without explicitly importing this capability
- **THEN** the new attribution module is absent from the import graph and no synthetic evidence is constructed

### Requirement: Future observability grants no execution authority
Stable metadata SHALL define the minimum evidence for any future registration:
trajectory/fold and fit/scale manifests, pre-decision feature identity, raw
return and advantage arithmetic, ordered parameter metadata, raw component and
complete gradient vectors, clip factor and reconstruction residuals, and exact
source/objective/optimizer/verifier bindings. The current capability SHALL
accept no path, seed, cohort, checkpoint, environment factory, execution, or
optimizer-state input and SHALL keep model fitting, loading, native loading,
environment construction, seed access, replay, execution, training, gameplay,
formal RL, qualification, and promotion authority false.

#### Scenario: A future proposal references the contract
- **WHEN** a later change proposes a baseline or empirical successor
- **THEN** it must separately select and review the estimator, folds, bounds, raw evidence publication, cohort, and execution lifecycle rather than treating this contract as authorization

#### Scenario: Synthetic contract completes
- **WHEN** every source-only test and deterministic report check passes
- **THEN** the result establishes only an implementable observability contract and does not select a critic, coefficient, optimizer, architecture, checkpoint, seed, cohort, or policy change
