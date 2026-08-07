## Context

The consumed hierarchical simulator-learning successor preserved stochastic
family exploration but stopped after 512 episodes and eight updates because
all 1,847 card-reward multi-family decisions in its final four chunks had
`take` as the unique raw-score maximum family. Its direct credit-assignment
audit found positive aggregate take pressure but negative pressure in the
supported effective-floor `17..33` stratum. That audit could not identify the
complete shared-parameter update because the ranker shares parameters across
categories and decisions.

The source-only hierarchical advantage-attribution contract now validates
trajectory-disjoint residual advantages, five named loss components, the
independently differentiated complete gradient, and one aggregate-first clip
factor. It deliberately selects no estimator, fold construction, empirical
cohort, or execution lifecycle. This change selects those missing terms for a
small mechanism study. It is not another policy-quality experiment.

The consumed hierarchical source, registration, checkpoints, terminal bundle,
and all prior seed identities are immutable evidence. This planning change
does not import Torch, load the native simulator, construct an environment,
materialize a cohort, access a seed, fit a baseline, or update a model.

## Goals / Non-Goals

**Goals:**

- Replace decision-batch return normalization with a cross-fitted pre-decision
  state-value residual while holding the existing policy and reward controls
  fixed.
- Prove that every empirical advantage is predicted by a model fitted on
  complete, disjoint trajectories and that no post-action field reaches the
  baseline.
- Preserve all five raw shared-parameter gradient components, the complete
  gradient, the installed clipped gradient, the resulting Adam state
  transition, and a same-batch legacy-objective gradient diagnostic before
  each optimizer step.
- Bound the first execution to the same 512 scheduled trajectories at which
  the consumed successor established persistent family saturation.
- Produce an independently verifiable terminal mechanism bundle without using
  predictive fit, gradient direction, floor, or victory to select or tune an
  algorithm.

**Non-Goals:**

- Editing, importing private helpers from, rerunning, resuming, or
  reinterpreting the consumed hierarchical experiment.
- Changing the state-conditioned ranker, candidate policy input, hierarchical
  action distribution, formal reward, Adam parameters, entropy coefficients,
  model seed, discount, or gradient ceiling.
- Learning a scale, tuning ridge strength or feature width, selecting a model,
  or falling back when the baseline predicts poorly.
- Running canary or holdout evaluation, establishing policy quality, comparing
  against a teacher, making a causal or OPE claim, or declaring formal RL
  ready.
- Loading a production checkpoint, starting Slay the Spire or CommunicationMod,
  qualifying a policy, or promoting gameplay behavior.

## Decisions

### Add three isolated execution modules and one seed-inventory utility

The implementation will add:

1. `analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py`
   as a standard-library control plane for immutable terms, source binding,
   inventory, registration, authorization, lease/journal/resource control,
   checkpoint publication, terminal publication, and CLI commands;
2. `analysis_scripts/noncombat_cross_fitted_hierarchical_learning_runtime.py`
   for Torch model state, rollout, baseline fitting, objective construction,
   gradient evidence, optimizer updates, and family diagnostics; and
3. `analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py`
   as an independent standard-library verifier that imports neither the
   control plane nor the runtime; and
4. `analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_inventory.py`
   as a standard-library historical-exclusion scanner and deterministic fresh-
   schedule validator used only at the later registration boundary.

Control-only commands remain importable without Torch or the native adapter.
The runtime is imported only after authorization, source, runtime, native,
isolation, output-root, and lease checks pass. The new runtime reuses public
APIs from the simulator adapter, formal reward, policy input, state-conditioned
ranker, hierarchical distribution/objective, candidate feature projection, and
advantage-attribution modules. For the diagnostic only, it calls the consumed
hierarchical runtime's public `normalize_returns` and `build_reinforce_loss`
functions so the legacy objective arithmetic is source-identical rather than
reimplemented. It imports no private function from a consumed learning runner,
and every directly or transitively reused behavioral source file is included in
the new source binding. Execution rejects a pre-imported Torch or native module,
loads and verifies the registered native bytes and build provenance first, and
only then imports the bound runtime and compares its complete immutable metadata
to the registration.

Alternative: patch the consumed runner. Rejected because that would alter
consumed evidence. Alternative: copy its complete control plane and runtime.
Rejected because it would hide the intended intervention inside duplicated
code. Only small lifecycle semantics with new tests may be ported.

### Derive a fixed 128-dimensional state-only feature vector

For each nonterminal exact-API-v3 decision, the runtime obtains the checked-in
1,024-dimensional CPU float32 `state_features` tensor from
`project_state_conditioned_policy_input`. It ignores the candidate tensor and
folds the state tensor deterministically, adding source indices in ascending
order with float32 arithmetic:

```
baseline_state[j] = sum(state_features[i] for i where i mod 128 == j)
```

Because 128 divides 1,024, this is equivalent to applying the same stable hash
projection directly at width 128 while reusing the public leakage-controlled
policy-input boundary. The baseline vector is independent of candidate order
and identity. Its feature identity binds the source policy-input metadata,
folding rule, shape, dtype, canonical sparse `(index, float32 value)` payload,
and SHA-256 digest. Sparse indices are unique and strictly increasing; exact
zeros, including negative zero, are omitted. The candidate set is used only to
validate and construct the
existing pre-decision policy input; selected action/family, scores, successor
state, reward, return, terminal outcome, seed, and later observations are not
baseline features.

Width 128 is an engineering bound, not a selected hyperparameter: it keeps each
exact solve at 129 coefficients and each retained feature payload bounded while
preserving the established state hash. Width 1,024 was rejected because 32
exact fold solves and their independent verification would dominate this small
mechanism study. Hand-selected fields were rejected because they would add a
new semantic feature-design question.

### Fit one deterministic four-fold ridge baseline per update

Each update starts from exactly 64 complete trajectories generated by one
frozen pre-update policy. Sort their registered integer seed values in ascending
numeric order, assign fold `position mod 4`, and require exactly 16 nonempty
trajectories in every fold.
All decisions in one trajectory remain in that fold. For each held-out fold,
fit on every decision from all and only the other 48 trajectories; the complete
fit-trajectory list is unique, ordered, and digest-bound.

For fit trajectory `t` with `n_t` decisions, each row has weight
`1 / (48 * n_t)`. With an intercept prepended to the 128 state values, solve:

```
min_beta sum_t [1 / (48 * n_t)] * sum_d (G_td - x_td beta)^2
         + 0.001 * sum_{j=1..128} beta_j^2
```

`G_td` is the undiscounted formal return-to-go and must be finite in `[0, 3]`.
The intercept is not penalized. Before any weight, product, or accumulation,
the runtime converts each exact float32 feature value, float64 target, and
float64 trajectory weight to float64. It then constructs the weighted normal
equations with float64 multiply-adds in canonical trajectory, decision, and
sparse-feature order and uses CPU float64 Cholesky factorization and solve. A
failed or nonfinite factorization blocks the chunk. No float32 sufficient-
statistic accumulation, pseudoinverse, jitter, alternate solver, or coefficient
change is allowed.

The independent verifier reconstructs `A`, `beta`, and `b` and checks every
normal-equation coordinate `r_j = (A beta - b)_j` against the immutable rule:

```
abs(r_j) <= 1e-9
            + 1e-9 * max(abs(b_j), sum_k abs(A_jk * beta_k))
```

Both products and the absolute scale sum use the registered float64 canonical
order. These `atol=1e-9` and `rtol=1e-9` values apply only to ridge KKT
residuals and cannot be changed by registration. Held-out predictions use the
registered `math.fsum(float(beta_j) * float(x_j) for j in 0..128)` dot product
and must reproduce their stored float64 bytes exactly before range clipping.

Held-out predictions use canonical float64 dot-product order and are clipped to
`[0, 3]`. The registered advantage is exactly:

```
advantage = raw_return_to_go - clipped_held_out_prediction
```

The scale is fixed at one and has no fit identities. The prediction is detached
and is the same for every candidate at the decision. The checked-in advantage
contract validates all fold, fit-set, feature, return, prediction, scale, and
arithmetic provenance before a loss is built.

Ridge coefficient `0.001`, four folds, trajectory-balanced weights, clipping,
and unit scale are frozen design controls. Per-fold held-out MSE and MAE,
prediction clip counts, a zero predictor, and the same-weighted fit-trajectory
mean predictor are descriptive diagnostics only. No metric can select a
fallback, cancel an update, alter a coefficient, or generate a retry.

Alternative: a learned neural critic. Rejected because its optimizer, schedule,
and initialization would add several unconstrained interventions. Alternative:
a fold-mean constant baseline. Rejected because it cannot test whether existing
pre-decision state information reduces trajectory confounding. Alternative:
learned standard-deviation scaling. Rejected because it adds fit provenance and
another unstable control before the baseline itself is understood.

### Use held-out policy weights while freezing high-level controls

For all `N` selected decisions in one chunk, the new scalar components are:

```
card_reward_family_policy =
    -sum(card_reward family_log_probability * advantage) / N
card_reward_conditional_policy =
    -sum(card_reward conditional_log_probability * advantage) / N
other_policy =
    -sum(non-card joint_log_probability * advantage) / N
family_entropy_regularizer = -0.01 * mean(family_entropy)
conditional_entropy_regularizer =
    -0.01 * mean(expected_conditional_entropy)
```

Empty policy subsets produce a graph-connected scalar zero so all five named
components remain present. Their sum is the separately supplied full loss.
The ranker, model seed `0`, family-first then conditional sampling, action
generator, formal reward, discount `1.0`, Adam learning rate `0.001`, betas
`(0.9, 0.999)`, epsilon `1e-8`, zero weight decay, no AMSGrad, separate entropy
coefficients `0.01`, and gradient norm ceiling `1.0` remain fixed.

The new update performs no additional batch, fold, trajectory, category, or
decision centering or normalization after the cross-fitted advantage. The
legacy-objective diagnostic does not approximate the old normalization: it
calls the consumed public `normalize_returns` implementation, including its
float32 conversion, `mean`, population `std(unbiased=False)`, strict
`std > 1e-12` branch, `std + 1e-8` divisor, and all-zero low-variance branch,
then calls the consumed public loss builder. Source tests cover values below,
at, and above the threshold.

### Install the validated complete gradient and retain a legacy diagnostic

Before every optimizer step, call the checked-in gradient ledger with the five
components, separately supplied full loss, and exact named parameter order.
Retain all five float64 component vectors, their independently differentiated
float64 complete vector, pairwise metrics, reconstruction residuals, norm, and
one aggregate-first clip factor. Segment the ledger's clipped complete vector
in parameter order, cast each segment to CPU float32, install those values as
the model parameter gradients, retain the installed vector, and only then call
Adam.

This ledger-derived float64 norm/factor followed by float32 installation is a
registered secondary numeric intervention. It is not claimed to be bitwise
identical to the consumed runtime, which called Torch global clipping on
float32 `.grad` tensors. On the same new complete gradient, the runtime also
computes the consumed Torch clipping result without stepping it and retains the
maximum absolute and relative difference from the installed ledger result.
That difference is descriptive and cannot tune, cancel, or retry an update.

For step-integrity evidence, each chunk retains ordered pre-step and post-step
model parameters plus Adam `step`, `exp_avg`, and `exp_avg_sq` tensors in the
same little-endian representation as the installed gradient. The independent
verifier replays the fixed Adam transition and rejects a wrong installed
gradient, missing step, wrong moment, or incompatible parameter transition
under fixed `atol=5e-7` and `rtol=5e-6` float32 tolerances. It binds the consumed
Adam options, resolved CPU execution mode, and Torch version and applies the
registered bias-corrected Adam equations in parameter order. This replay proves
optimizer
application integrity only. Optimizer state and parameter deltas never enter
the advantage-attribution ledger and are never described as loss-component
attribution. Authenticity of autograd vectors rests on the bound reviewed
source, scalar-row reconstruction, the checked-in independently differentiated
ledger, and source-only gradient tests rather than an adversarial re-execution
of Torch by the standard-library verifier.

On the same selected actions, returns, and pre-update computation graph, also
construct the consumed normalized-return objective with the unchanged entropy
terms and differentiate one complete legacy-objective vector. Do not step it.
Retain its raw norm, implied global clip factor, dot product, cosine when
defined, and difference norm against the cross-fitted complete gradient. These
are continuous descriptive evidence; no cosine, norm, or sign is a pass/fail
gate.

Alternative: run a second policy under the legacy update. Rejected because it
would double seed use and introduce different sampled actions and trajectories.
The retained vector is only a same-batch legacy-objective gradient diagnostic
at parameters and actions observed under this successor. Only chunk zero shares
the registered seeded parameter initialization; later chunks already reflect
cross-fitted updates. No chunk represents the parameters, trajectory, or
outcome a legacy learner would have experienced.

### Publish bounded raw evidence in independently readable formats

Each completed chunk publishes canonical diagnostic JSON plus deterministic
gzip payloads with `mtime=0`. Sidecar metadata binds schema, row/vector order,
dtype, shape, byte offsets, canonical uncompressed SHA-256 and byte size, and
stored SHA-256 and byte size.

The retained evidence includes:

- exact chunk seed order, fold membership, complete fit identities, decision
  order, rewards, return-to-go values, baseline predictions, advantages, and
  fixed-unit scale provenance;
- canonical sparse baseline-state float32 features, four float64 coefficient
  vectors, fit weights, normal-equation identities and residuals, held-out
  predictions, and descriptive baseline diagnostics;
- candidate/family identities, selected family/action terms, raw scores,
  probabilities, entropy terms, and the existing family-saturation fields;
- five raw component gradient vectors, the independent complete vector, the
  legacy-objective complete vector, scalar loss reconstruction, both ledger and
  consumed Torch clip diagnostics, exact parameter names/shapes/dtypes, the raw
  installed clipped float32 vector, and pre/post model and Adam state vectors;
  and
- write-once bootstrap state, a flushed per-access `(ordinal, chunk, seed,
  attempt, status)` journal, resource prefixes, complete-chunk checkpoints,
  terminal model/checkpoint identity, isolation snapshots, registration,
  authorization, human-approval binding, report, and closed manifest.

Float32 feature and installed-gradient values and float64 gradient values use a
fixed little-endian binary representation. The independent verifier parses
them with the Python standard library. It reconstructs fold completeness,
normal equations, coefficient residuals, predictions, advantages, gradient
component sums, norms, clip arithmetic, installed-gradient casts, and
legacy-objective metrics. It also replays each Adam state transition and checks
every primary and replay seed access against the durable journal rather than
trusting summary claims.

The registration caps retained decisions at `32,768`, any one managed artifact
at `64 MiB`, all stored managed artifacts at `192 MiB`, and their canonical
uncompressed payloads at `256 MiB`. Crossing a byte or decision bound stops
before another optimizer update and preserves the terminal failure. Timing is
reported but noncanonical.

### Run one 512-trajectory mechanism study without evaluation cohorts

A later registration fixes eight chunks of 64 unique scheduled training
trajectories, at most eight optimizer updates, at most 500 decisions per
episode, and at most 32,768 retained decisions. There is no canary, holdout,
teacher, checkpoint selection, or frozen-policy rollout. The execution is CPU
only at ascension `0`, may load only its bound native simulator module and build
provenance, may not load a production checkpoint, and has 14,400 charged
seconds. Registration also binds the exact CommunicationMod configuration and
complete inert production-checkpoint tree. Source-only preflight reobserves the
pushed `origin/master` commit, tracked-clean source bytes, runtime identity,
native bytes, and isolation identity before native loading. Because
registration and authorization are later tracked boundaries, the registered
implementation commit is required to be an ancestor of the current pushed
HEAD rather than equal to it. The current Git tree must contain the exact
canonical registration and authorization blobs, while the complete registered
source inventory must still match byte for byte. Terminal closeout reobserves
isolation before accepting any verdict.

The existing exact anti-collapse rule remains unchanged. After each complete
chunk, inspect the trailing four chunks. If at least 64 multi-family decisions
in either `card_reward` or `shop` all have the same singleton raw-score maximum
family, publish
`experiment_stopped_during_training_for_family_saturation` before the next
chunk. Baseline fit and gradient diagnostics never stop training. Completion of
all eight updates publishes
`experiment_completed_with_cross_fitted_mechanism_evidence` regardless of
floor, victory, baseline MSE, or gradient cosine.

The 512-trajectory limit matches the point at which the consumed experiment's
registered saturation gate fired. Extending directly to another 4,096-episode
quality study was rejected because this successor first needs to show that its
credit-assignment mechanism changes observable shared-gradient behavior and
does not immediately reproduce the same saturation.

### Select one fresh cohort only after clean source publication

Source implementation and tests use explicit synthetic seeds and environments.
After that source is independently reviewed, committed, and pushed, a tracked
standard-library inventory scans one fixed Git tree and excludes every seed
under seed-bearing fields in historical registrations, authorizations,
reservations, diagnostics, reports, checkpoints, training, evaluation, canary,
and holdout evidence. Previously unvisited holdouts remain excluded.
Every extracted provenance row is ordered by `(seed, source path, document
index, JSON path, role)` before hashing so the producer and independent
verifier share one explicit canonical identity.

One fixed ascending algorithm selects exactly 512 unique training seeds. Sort
them canonically for chunk and fold assignment. Exact values, native-module
identity, source commit, and output root are materialized only in the later
all-false registration. That registration additionally binds ascension `0`,
native build provenance, the pushed remote ref, and pre-execution isolation.
Caller-supplied seeds, alternate search starts, or runtime overrides fail
closed.

### Require explicit external approval for exact execution

After the pushed registration is independently verified, the implementation
may render a read-only execution request that repeats its canonical digest,
native identity, exact seed and resource bounds, output root, retry/resume rule,
and false downstream authorities. Rendering or reviewing that request grants no
authority. The process must stop until the human operator explicitly approves
that exact request in a separate message.

Only after that external approval may a tracked authorization be materialized.
It binds the canonical request digest plus the verbatim approval text, approval
timestamp, and conversation/task provenance available to the operator. The
independent verifier can prove that the authorization matches the request and
recorded approval; human identity remains a procedural trust boundary rather
than a cryptographic claim. A broad standing permission, this proposal's
approval, or an agent-authored review is not the exact execution approval.

### Permit setup retry and one bounded same-identity resume

Registration, source-only verification, inventory, and pre-start validation do
not load native code or access a seed. After source-only checks and lease
acquisition, the runner publishes six canonical registration, request,
approval, authorization, preflight, and pre-isolation documents before loading
the registered native module. If dependency loading fails, a later manual
invocation may reclaim only that exact source-bound setup inventory under the
same registration and authorization. A fully initialized bootstrap with a
zero-debit journal and zero resource ledger is likewise reopenable without
consuming the post-start resume. Neither case triggers an automatic retry loop,
changes a module, seed, cohort, or control, or accesses an environment.

Immediately before the first registered seed reaches the environment factory,
the runner durably flushes the evidence-bearing start marker. After that point,
algorithm, legality, schema, finiteness, resource, or evidence failure is
terminal. One infrastructure interruption may resume the same identity from
the latest complete checkpoint and replay only its incomplete registered chunk
with unchanged model, optimizer, Python RNG, Torch generator, source, native
module, seeds, controls, and output root. No second post-start resume is
allowed.

The schedule contains 512 unique trajectories; the resource ledger permits at
most 576 environment episode accesses, reserving one complete 64-episode chunk
for that same-identity replay. Debited episode accesses and charged seconds
never roll back. Before each seed reaches the environment factory, the runner
flushes one append-only access record containing the monotonic access ordinal,
scheduled chunk and seed, primary-or-resume attempt ordinal, and debited status;
episode completion appends the corresponding terminal status without rewriting
the prefix. An interruption therefore retains every partial-chunk access even
when no diagnostic row completed. A checkpoint coordinate may be lower than
consumed resources. Checkpoint publication advances resource use first and
model state second, and terminal reconstruction uses only the latest complete
checkpoint or the write-once seeded bootstrap when no chunk completed.
Chunk evidence duplicates the exact opaque runtime-checkpoint binding held by
its checkpoint envelope. If evidence and its reconciled journal/resource
coordinate are durable but the envelope write is interrupted, a later manual
invocation may reconstruct exactly that one missing envelope without another
environment access or optimizer update. Any non-unique or inconsistent prefix
fails closed.

The output lease is exclusive. While the execution process is alive,
monitoring reads process liveness only and does not inspect the active output
root. Initial execution requires an absent output root. A pre-start retry may
reopen only the exact source-bound setup inventory or initialized zero-debit
boundary with no first-seed marker. The one permitted post-start resume may
reclaim only its exact lease after independently proving the recorded owner
process is dead and validating the registered bootstrap, journal, resource
prefix, complete checkpoints, and absence of an ambiguous temporary
publication. Every unrelated or unreconstructable preexisting lease, journal,
artifact, temporary publication, or output root fails closed.

The interruption coordinate is the latest durably published complete
checkpoint, not merely the number of episode terminal records. If all 64
episode accesses of a chunk completed but its checkpoint did not, that chunk is
still incomplete and is the sole replay candidate. If interruption occurs after
a complete checkpoint and before the next registered seed, resume restores that
checkpoint and continues the next primary chunk without replaying a completed
chunk or consuming an extra seed. Both cases consume the one post-start resume
allowance and retain all charged resources.

Terminal publication first writes an immutable intent over the exact artifact
prefix, then the terminal document, then the manifest. If interrupted after the
intent or terminal write, a later invocation completes only the uniquely
missing byte-identical document before dependency loading. It does not reopen
training or consume another seed.

If the persisted post-isolation observation differs from registration, the
runner preserves that observation and any typed failure witness but does not
publish terminal intent, terminal, or manifest. Such a root is deliberately
not a structurally valid bundle and cannot be reopened. If the sole post-start
resume is itself interrupted, the runner instead charges its final resources
and closes a typed infrastructure failure under the consumed identity; it does
not expose a second resume.

### Keep every verdict and downstream authority narrow

The independent verifier classifies only:

- structurally valid completion with cross-fitted mechanism evidence;
- structurally valid early family-saturation evidence;
- a pre-start blocked attempt with no seed access; or
- a terminal post-start integrity, algorithm, infrastructure, or resource
  failure preserved under the same identity.

It does not convert baseline fit, gradient disagreement, absence of saturation,
floor, or victory into policy quality or formal RL readiness. Every registration
and terminal artifact keeps formal RL, policy quality, model loading, gameplay,
CommunicationMod, qualification, and promotion authority false. Only a later
read-only audit may decide whether the mechanism evidence warrants a separate
full policy-quality successor proposal.

## Risks / Trade-offs

- [The hashed linear baseline may predict poorly] -> Preserve its negative
  evidence and fixed controls; never tune or replace it inside this identity.
- [Hash folding increases collisions] -> Bind every raw folded feature and use
  width 128 only for this bounded mechanism question, not as a production
  critic choice.
- [A baseline fitted on only 48 trajectories may have high variance] -> Keep
  complete trajectory-disjoint folds, fixed unit scale, and per-fold diagnostics
  without claiming variance reduction when the evidence does not support it.
- [Prediction clipping biases the fitted value estimate] -> Fit coefficients on
  raw bounded returns, retain unclipped and clipped predictions plus clip counts,
  and state that clipping is a numerical range guard rather than a quality gate.
- [The extra gradient evidence increases runtime and artifact size] -> Cap
  decisions and bytes, use deterministic compressed binary payloads, and stop at
  eight updates.
- [A same-batch legacy-objective gradient is not a legacy learner trajectory]
  -> Describe it only as an objective-direction diagnostic at observed
  successor parameters and actions, and call out that only chunk zero shares
  seeded initialization.
- [Ledger clipping is a second numeric intervention] -> Register it explicitly,
  retain the consumed Torch clipping diagnostic on the same vector, and never
  attribute an observed difference solely to the baseline.
- [A self-consistent gradient payload could still be fabricated] -> Bind the
  reviewed source and scalar rows, use the independently differentiated ledger,
  cover the path with source-only tests, and independently replay the actual
  Adam transition without claiming adversarial autograd verification.
- [The exact saturation rule may stop a policy that could later recover] ->
  Preserve the consumed four-chunk rule for comparability and classify the
  result narrowly as repeated family saturation.
- [A Windows interruption may consume seeds twice] -> Permit only one
  same-identity incomplete-chunk replay, debit every access durably, and never
  substitute a seed or evidence identity.
- [An operator could delete the complete output root and attempt to reuse the
  authorization] -> Treat deletion or renaming after publication as prohibited
  destruction of immutable evidence. The local lifecycle assumes preservation
  of its bound output root; a deletion-resistant redemption service would be a
  new external trust boundary and requires a separate proposal rather than a
  second local marker that the same operator could also delete.
- [The repository commit gate already exceeds its feedback target] -> Use
  focused tests during implementation, invoke the commit gate once at the
  source commit boundary, and leave duration optimization to its separate
  maintenance lane.

## Migration Plan

1. Strict-validate, independently review, commit, and push this planning change
   without implementation, Torch/native loading, cohort creation, or seed
   access.
2. Add RED synthetic and lifecycle tests, then the three execution modules and
   source-only seed-inventory utility. Preserve all consumed files and
   empirical artifacts byte-for-byte.
3. Run focused successor/dependency tests, import-isolation checks, strict
   OpenSpec validation, one repository commit gate, and independent code/spec/
   authority review. Commit and push the source-only implementation.
4. From that clean pushed commit, generate and independently verify the fresh
   exclusion inventory and immutable all-false registration. Commit and push
   without loading native code or accessing an empirical seed.
5. Render and independently review the exact execution request, then stop for a
   separate explicit human approval of that exact digest and bounds.
6. After that approval, publish its bound authorization and run at most one
   evidence-bearing identity, with only the one bounded same-identity
   infrastructure resume described above.
7. After process exit, independently verify and preserve the terminal bundle,
   publish a read-only postmortem, sync/archive the change, and update project
   direction. Any later policy-quality study requires a new proposal.

Before registration, rollback deletes only additive uncommitted successor
files. After registration, rollback means cancel before seed access. After the
start marker, rollback means preserve the immutable terminal evidence; it never
means changing a term, source, cohort, seed, threshold, or model and rerunning.

## Open Questions

- Exact fresh seed values, native-module bytes, source commit, and output root
  remain intentionally unresolved until the implementation is clean, reviewed,
  committed, and pushed.
- Source-only size and timing benchmarks may lower the registered byte,
  decision, episode-access, or wall-time ceilings. Raising a ceiling or changing
  the feature width, ridge coefficient, fold assignment, baseline solver,
  advantage arithmetic, stop rule, or lifecycle requires proposal revision and
  renewed review before registration.
