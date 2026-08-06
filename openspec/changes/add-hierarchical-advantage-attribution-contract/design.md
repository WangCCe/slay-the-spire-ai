## Context

The terminal hierarchical successor normalized reward to go across every
decision in each 64-episode chunk and optimized one shared state/candidate MLP.
The completed read-only audit reconstructed 11,807 decisions and 3,559
multi-family card rewards. Direct row-local `take`-logit pressure was positive
in every chunk and terminal greedy margins grew, but the supported
effective-floor `17..33` band had nonpositive combined pressure. That audit
cannot determine whether a less trajectory-confounded advantage changes the
signal or how all decision rows combine through shared parameters.

The current diagnostic rows do not retain a cross-fitted baseline provenance
or named parameter-gradient components. Those facts cannot be recovered from
row-local score probabilities after the experiment. A future runtime must
produce them at update time, but no new runtime or experiment is authorized
until their source-only contract is explicit and synthetically tested.

## Goals / Non-Goals

**Goals:**

- Define an exact advantage record whose baseline and scale exclude the entire
  target trajectory and use only pre-decision state inputs.
- Define named loss-component gradients over one ordered shared parameter set
  and prove that they reconstruct the complete gradient.
- Preserve component additivity through the existing uniform global-norm clip
  while keeping every optimizer transform outside the attribution contract.
- Give a future registration a minimum raw evidence schema that a separate
  verifier can check without inferring provenance from aggregate metrics.
- Publish deterministic synthetic evidence and all-false authority without
  integrating the contract into an empirical or production path.

**Non-Goals:**

- Selecting or fitting a value model, critic architecture, feature schema,
  fold count, scale estimator, optimizer, coefficient, checkpoint, or cohort.
- Claiming that cross-fitting removes all trajectory confounding or turns an
  advantage into a causal card value.
- Decomposing Adam's nonlinear moment update into additive component updates.
- Loading a model or native module, constructing an environment, accessing a
  seed, training, replaying, qualifying, promoting, or starting the game.

## Decisions

### Add one generic source-only contract module

Add
`analysis_scripts/noncombat_hierarchical_advantage_attribution.py`. It may
import CPU Torch and Python standard-library modules, but it will not import
the experiment control plane, runtime, ranker, policy input, simulator adapter,
agent, or CommunicationMod. Existing modules will not import it. Its public
surface validates caller-supplied synthetic records, scalar loss components,
a separately supplied full scalar loss, and named parameters; it never opens a
checkpoint or data artifact.

Tests and a deterministic report will use a tiny locally constructed shared
ranker. This proves the algebra without making the checked-in production
ranker or a terminal checkpoint an implicit input.

Alternative: instrument the consumed runtime immediately. Rejected because it
would change a terminal source identity and silently turn design work into a
new empirical successor.

### Treat the complete trajectory as the cross-fitting unit

Each decision record binds one `trajectory_id`, one held-out `fold_id`, a
pre-decision feature identity, finite raw return, finite baseline prediction,
positive finite scale, and the complete baseline-fit and scale-fit trajectory
sets. Every decision from one trajectory must use one fold. The held-out
trajectory and every other trajectory in that fold must be absent from both
data-derived fit sets. Those fit sets are unique, sorted, nonempty, and bound
by canonical digest.

The contract computes only:

```
advantage = (raw_return - baseline_prediction) / scale
```

It does not center or normalize that result again. An explicit fixed-zero
baseline plus unit scale is the compatibility path and carries no fit set; it
reproduces raw returns but does not claim to reduce confounding. A
data-derived baseline or scale must carry held-out provenance. The baseline
feature identity must declare only a pre-action state projection. Selected
action/family, candidate scores, the successor transition, rewards, terminal
outcome, and any later observation are forbidden baseline inputs.

Cross-fitting is a leakage boundary, not proof of causal identification. The
return remains an outcome of the whole sampled trajectory, so every report and
metadata surface keeps causal authority false.

Alternative: center returns within each trajectory. Rejected because it can
erase the shared victory/floor signal and still does not estimate a
state-conditional control variate. Alternative: choose a critic here. Rejected
because the terminal audit does not identify an architecture or fitting rule.

### Decompose the shared gradient before optimizer semantics

The ledger accepts exactly these ordered conceptual components:

1. `card_reward_family_policy`
2. `card_reward_conditional_policy`
3. `other_policy`
4. `family_entropy_regularizer`
5. `conditional_entropy_regularizer`

Each component and the separately supplied full loss are finite scalars
connected to the same ordered, uniquely named CPU float32 parameter set. A
parameter unused by one component contributes an explicit zero tensor. The
supplied full loss must equal the component sum, and its independently
differentiated full gradient must match the elementwise sum of component
gradients under one fixed dtype-aware tolerance. Missing, duplicate,
reordered, nonfinite, detached, or shape-drifted evidence fails.

This taxonomy separates the card-reward family mechanism audited in the
terminal evidence while retaining its within-family and all non-card policy
competition. Entropy components arrive already signed and coefficient-weighted
by a future registered objective; this contract does not choose a coefficient.

Alternative: record only component norms. Rejected because norms cannot prove
gradient reconstruction or reveal cancellation through shared parameters.
Alternative: emit one gradient per decision. Rejected for this contract
because component vectors are the minimum bounded evidence; a future proposal
may register finer diagnostics separately.

### Preserve additivity only through uniform clipping

The contract reuses the existing gradient ceiling `1.0` and computes the one
uniform clip factor from the complete gradient norm. The same factor is applied
to every component vector, so clipped component vectors must still sum to the
clipped complete gradient. It reports norms, pairwise dot products and cosines,
and reconstruction residuals before and after clipping.

The contract stops at the uniformly clipped complete and component gradients.
It accepts no optimizer state or parameter delta. Adam's moment and square-root
transforms are nonlinear in the combined gradient and remain outside the
decomposition.

Alternative: clone Adam once per component and call each counterfactual delta a
contribution. Rejected because the resulting deltas depend on ordering and
counterfactual optimizer state and do not form a unique additive attribution.

### Make the row-local versus shared-gradient distinction synthetic

The deterministic design report includes a fixed two-decision shared-ranker
fixture. One card-reward row has positive direct family-logit pressure, while
the complete component gradient through shared parameters has an opposing
direction on a fixed probe margin because another row shares those parameters.
The report also includes an aligned case and fixed within-family and
across-family maximum-score ties that preserve the checked-in max-pool
semantics. This proves why the prior direct pressure is incomplete without
implying that any synthetic direction describes empirical policy quality.

### Freeze future registration observability, not execution

Stable metadata will define the minimum future evidence:

- trajectory/fold manifests and complete disjoint fit/scale provenance;
- pre-decision feature schema and per-row feature digest;
- raw return, baseline prediction, scale, and computed advantage;
- ordered parameter names, shapes, dtypes, and component taxonomy;
- raw component vectors, full gradient, clip factor, clipped vectors, and
  reconstruction residuals and bounded pairwise dot/cosine summaries; and
- exact source, objective, optimizer, and verifier identities.

The contract report itself contains only synthetic rows and all-false
authority. A later OpenSpec proposal must choose the baseline/folds and decide
whether to register this evidence for a new runtime. This change cannot be
reused as an execution authorization.

## Risks / Trade-offs

- [Cross-fitting can still leave outcome confounding] -> Name it only as a
  leakage-safe control-variate boundary and preserve every causal/OPE claim as
  false.
- [Component gradients can cancel] -> Publish vectors, dot products, cosines,
  and reconstruction residuals rather than norms alone.
- [Floating reductions can differ by order] -> Freeze parameter order, dtype,
  accumulation semantics, and one tolerance with extreme and cancellation
  fixtures.
- [Gradient vectors increase future artifact size] -> Require bounded
  component-level vectors, not per-decision vectors, and leave compression and
  empirical limits to the future registration.
- [Clipped gradients may be overinterpreted as optimizer updates] -> Expose no
  optimizer state or parameter delta and explicitly reject additive Adam and
  causal attribution.
- [Another contract can delay empirical learning] -> Keep implementation
  additive and synthetic, and make its terminal output directly enumerate the
  remaining baseline choices needed by the next experiment proposal.

## Migration Plan

1. Commit and push this reviewed planning identity before implementation.
2. Add RED synthetic provenance, arithmetic, gradient, clipping, drift, and
   import-isolation tests.
3. Implement only the additive source contract and deterministic report.
4. Run focused and repository gates once, obtain an independent review, update
   project direction, sync the capability, archive, and commit/push the scoped
   files.

Before the implementation commit, rollback deletes only the new uncommitted
files. After a pushed implementation, correction uses a revert or a separately
identified successor; it never edits consumed terminal evidence or production
configuration.

## Open Questions

- Which state-only baseline architecture, fold count, and fitting budget should
  a later empirical successor register?
- Should a future registration retain all component vectors or a preregistered
  bounded subset plus canonical vector digests?
- Which source-only evidence is sufficient before proposing that successor's
  first empirical cohort?
