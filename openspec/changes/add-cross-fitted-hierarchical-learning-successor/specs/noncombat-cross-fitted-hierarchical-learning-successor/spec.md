## ADDED Requirements

### Requirement: The successor is additive and source-isolated
The capability SHALL use a new control-plane module, Torch runtime module,
independent verifier module, and source-only historical seed-inventory utility.
It SHALL preserve every consumed hierarchical
runner, registration, authorization, checkpoint, terminal artifact, and seed
identity unchanged. The control plane and verifier SHALL remain standard-
library importable without importing Torch, loading a native module,
constructing an environment, or accessing a seed. The runtime SHALL reuse only
bound public low-level policy, simulator, reward, hierarchy, and attribution
APIs and SHALL NOT import private helpers from a consumed experiment.
Every directly or transitively reused behavioral source SHALL be included in
the registered source inventory. Execution SHALL reject pre-imported Torch or
native modules, load and verify the registered native bytes and build
provenance first, and import the bound Torch runtime only after source, runtime,
native, pushed-commit, isolation, output-root, lease, and authorization checks
all pass.

#### Scenario: A control-only command is invoked
- **WHEN** registration inspection, source verification, terminal verification, or help is invoked with Torch and the native adapter unavailable
- **THEN** the command completes or reports a source-level validation error without importing either dependency

#### Scenario: A consumed input changes
- **WHEN** any bound consumed source or empirical artifact differs from its registered path, bytes, size, or digest
- **THEN** the successor fails closed before native loading, environment construction, seed access, baseline fitting, or training

#### Scenario: Runtime work is requested without exact authority
- **WHEN** a caller requests native loading, environment construction, seed access, model fitting, or an optimizer step without a matching pushed registration and exact authorization
- **THEN** the control plane rejects the request without lazily importing the runtime

#### Scenario: Registration and authorization advance the pushed branch
- **WHEN** the all-false registration and later exact authorization are committed after the registered implementation commit
- **THEN** source-only preflight requires the implementation commit to be an ancestor of the tracked-clean `origin/master` HEAD, requires the current tree to contain the exact canonical registration and authorization blobs, and requires every registered source byte to remain unchanged before any dependency is loaded

### Requirement: Baseline features contain only bounded pre-decision state
For every retained decision, the runtime SHALL obtain the validated exact-API-
v3 1,024-dimensional CPU float32 state tensor from the public state-conditioned
policy-input boundary and SHALL fold it to 128 dimensions by summing source
indices modulo 128 in ascending source-index order with float32 arithmetic. It
SHALL retain the canonical sparse float32 vector with unique increasing indices
and no signed or unsigned zero, plus its identity. Candidate features, selected
action or family, policy scores,
successor state, reward, return, terminal outcome, seed identity, and later
observations SHALL NOT enter the baseline feature vector.

#### Scenario: A valid decision is projected
- **WHEN** one nonterminal exact-API-v3 snapshot and its complete legal candidates are projected
- **THEN** the baseline receives one finite 128-dimensional state-only vector whose values equal the registered modulo-folding arithmetic and whose payload and source metadata are digest-bound

#### Scenario: Candidate order or identity changes
- **WHEN** only the legal candidate order or candidate-local fields change while the validated pre-decision state remains identical
- **THEN** the baseline feature bytes and digest remain identical

#### Scenario: A prohibited field reaches baseline input
- **WHEN** selected action, selected family, score, transition, reward, return, terminal label, seed, or any post-decision value is included in baseline feature provenance
- **THEN** the chunk is rejected before a baseline prediction or policy loss is returned

#### Scenario: State projection is malformed
- **WHEN** the source state tensor has the wrong API identity, shape, device, dtype, or a nonfinite value
- **THEN** the runtime fails closed rather than coercing, dropping, or replacing the input

### Requirement: Every advantage uses a deterministic trajectory-disjoint ridge fit
Each complete update SHALL contain exactly 64 nonempty registered trajectories
and SHALL assign their ascending integer seed values to four folds by `position
mod 4`, with exactly 16 trajectories per fold. For each held-out
fold, the baseline SHALL fit all and only decisions from the other 48 complete
trajectories. It SHALL use one unpenalized intercept, 128 state coefficients,
trajectory-balanced row weights `1 / (48 * trajectory_decision_count)`, fixed
ridge coefficient `0.001`, CPU float64 weighted normal equations, and the
registered Cholesky solve. Every feature, target, and weight SHALL be converted
to float64 before any multiplication or accumulation, and accumulation SHALL
follow canonical trajectory, decision, and sparse-feature order. It SHALL use
no float32 sufficient statistics, alternate estimator, solver, jitter,
hyperparameter, fallback, or data-derived scale.
For every normal-equation coordinate `r_j = (A beta - b)_j`, independent
verification SHALL require
`abs(r_j) <= 1e-9 + 1e-9 * max(abs(b_j), sum_k abs(A_jk * beta_k))` using the
registered float64 canonical order. Registration SHALL NOT alter these
`atol=1e-9` and `rtol=1e-9` ridge residual terms. Held-out predictions SHALL
use `math.fsum(float(beta_j) * float(x_j) for j in 0..128)` and reproduce their
stored pre-clip float64 bytes exactly.

#### Scenario: Four valid folds are fitted
- **WHEN** a complete 64-trajectory chunk has at least one decision in every trajectory
- **THEN** every trajectory occurs in exactly one 16-trajectory held-out fold, every fold model binds the complete other 48 trajectory identities, and all held-out decisions receive exactly one prediction

#### Scenario: A trajectory leaks into its baseline
- **WHEN** any held-out trajectory appears in its baseline fit rows or any non-held-out trajectory is absent, duplicated, or reordered relative to the canonical complete fit identity
- **THEN** the advantage-attribution boundary rejects the complete chunk before loss construction

#### Scenario: Ridge arithmetic is reproduced
- **WHEN** the independent verifier consumes retained state features, returns, trajectory counts, weights, and coefficients
- **THEN** it reconstructs the registered weighted normal equations and accepts only finite coefficients whose every coordinate satisfies the fixed absolute-plus-scaled ridge residual rule and whose held-out prediction bytes reproduce exactly

#### Scenario: A ridge residual crosses its fixed boundary
- **WHEN** a fixed synthetic coefficient produces one coordinate immediately within or immediately beyond the registered `1e-9 + 1e-9 * scale` bound
- **THEN** the verifier accepts the within-bound fixture, rejects the beyond-bound fixture, and cannot substitute another scale or tolerance

#### Scenario: The baseline predicts outside the formal range
- **WHEN** a finite held-out linear prediction is below zero or above three
- **THEN** the runtime retains the unclipped value and clip diagnostic but uses exactly its `[0, 3]` clipped value as the baseline prediction

#### Scenario: Baseline fit quality is poor
- **WHEN** held-out ridge MSE exceeds the zero or fit-mean descriptive comparator
- **THEN** the runtime records the result and continues under the same estimator without fallback, tuning, cancellation, seed replacement, or retry

#### Scenario: The registered solve is invalid
- **WHEN** a trajectory is empty, a return is outside `[0, 3]`, a matrix or coefficient is nonfinite, Cholesky fails, or coefficient provenance cannot be verified
- **THEN** the chunk terminates without an optimizer update and no alternate numeric path is attempted

### Requirement: The update uses only held-out residual advantages
For decision `d`, the capability SHALL compute undiscounted formal return-to-go
`G_d` and exactly `G_d - clipped_held_out_prediction_d` with fixed unit scale.
It SHALL apply no later batch, fold, trajectory, category, or decision-level
centering, normalization, standardization, or clipping. Across all `N`
decisions, the full loss SHALL be the exact sum of the registered
`card_reward_family_policy`, `card_reward_conditional_policy`, `other_policy`,
`family_entropy_regularizer`, and `conditional_entropy_regularizer` components.

#### Scenario: A held-out decision enters the loss
- **WHEN** its fold and fit provenance, raw return, prediction, pre-decision feature identity, and fixed-unit scale are valid
- **THEN** its policy weight equals the exact held-out residual and the retained arithmetic agrees with the checked-in advantage contract

#### Scenario: Card-reward and other decisions are split
- **WHEN** one chunk contains card-reward and non-card decisions
- **THEN** card-reward family and conditional log-probability losses appear only in their separately named components, every non-card joint log-probability loss appears only in `other_policy`, and all three use denominator `N`

#### Scenario: One policy subset is empty
- **WHEN** a chunk has no decision for one of the policy subsets
- **THEN** its named component is a finite graph-connected scalar zero and all five component identities remain present in canonical order

#### Scenario: A second normalization is introduced
- **WHEN** a caller supplies a centered, standardized, learned-scale, clipped, or otherwise transformed residual after the registered advantage arithmetic
- **THEN** the runtime rejects the loss before gradient construction

#### Scenario: Preserved learning controls drift
- **WHEN** ranker architecture, model seed, action sampling, reward, discount, Adam terms, entropy coefficients, or gradient ceiling differs from the immutable registration
- **THEN** the execution fails before the affected optimizer update

### Requirement: Raw shared gradients govern the actual optimizer step
Before each optimizer step, the runtime SHALL invoke the checked-in advantage-
attribution ledger over the exact five scalar components, separately supplied
full loss, and unique ordered CPU float32 parameters. It SHALL retain all five
raw float64 component vectors, the independently differentiated complete
vector, norms, pairwise metrics, reconstruction residuals, and one global clip
factor at ceiling `1.0`. It SHALL install the clipped complete vector into the
model gradients in registered parameter order before calling Adam. The
float64-ledger-factor then float32-install path SHALL be registered as a second
numeric intervention and SHALL retain a no-step comparison against the consumed
Torch float32 clipping path on the same complete vector. Ordered pre/post model
parameters and Adam step, first moment, and second moment SHALL permit a
standard-library replay under fixed `atol=5e-7` and `rtol=5e-6`. Optimizer state
and parameter deltas SHALL prove only step integrity and SHALL NOT be attributed
to loss components.

#### Scenario: A valid chunk is updated
- **WHEN** all five components and the separately supplied full loss pass the attribution contract
- **THEN** raw component vectors reconstruct the independent complete vector, one ledger factor clips the complete vector and every component, the installed CPU float32 gradient equals the registered cast of that clipped vector, and the retained pre/post state replays exactly one Adam update within the fixed tolerances

#### Scenario: The consumed clipping path differs numerically
- **WHEN** applying consumed Torch float32 clipping to the same complete gradient differs from the ledger-derived installed gradient
- **THEN** both results and their maximum absolute and relative difference remain descriptive evidence and the runtime neither hides the second intervention nor tunes, cancels, or retries the update

#### Scenario: Shared component pressure cancels
- **WHEN** two component vectors oppose each other on shared parameters
- **THEN** the retained signed vectors, dot products, cosines, complete vector, and cancellation remain visible without absolute-value aggregation

#### Scenario: Parameter or gradient evidence drifts
- **WHEN** a parameter name, identity, order, shape, dtype, device, component, scalar loss, vector length, finiteness check, reconstruction, clip factor, installed gradient, Adam step, moment, or pre/post parameter transition differs
- **THEN** pre-step drift blocks the update and post-step drift makes the chunk terminally invalid rather than repairing or dropping evidence

#### Scenario: Adam did not consume the installed gradient
- **WHEN** independent replay shows a missing step, wrong gradient, wrong moment, or incompatible post-step parameter under the registered optimizer and tolerances
- **THEN** terminal verification rejects the chunk without describing optimizer state as component attribution

### Requirement: Every chunk retains a same-batch legacy objective gradient
The runtime SHALL call the consumed public `normalize_returns` and
`build_reinforce_loss` functions over the exact same chunk returns and selected
policy terms, including float32 conversion, mean, population
`std(unbiased=False)`, strict `std > 1e-12`, `std + 1e-8`, and the all-zero
low-variance branch. It SHALL differentiate one complete legacy-objective
vector with the unchanged entropy terms at the same observed pre-update
parameters, retain its raw vector and implied clip factor, and SHALL NOT apply
it to the optimizer or infer the trajectory or outcome a legacy learner would
have experienced.

#### Scenario: Both objective gradients are available
- **WHEN** a chunk passes advantage and attribution validation
- **THEN** the evidence reports the cross-fitted and legacy-objective complete vectors, norms, dot product, difference norm, and cosine when both norms are nonzero from the same rows and observed successor parameters

#### Scenario: Legacy normalization is near its variance threshold
- **WHEN** fixed returns produce population standard deviation below, exactly at, or above `1e-12`
- **THEN** the diagnostic bytes and vector agree with the consumed public implementation and use its exact branch without an alternate accumulation or tolerance

#### Scenario: One objective gradient is zero
- **WHEN** either complete gradient has zero norm
- **THEN** the raw vector and norm remain retained, cosine is explicitly undefined, and no substitute metric or pass/fail interpretation is introduced

#### Scenario: A second policy execution is requested
- **WHEN** a caller attempts to run the legacy optimizer, consume another seed, or infer a legacy trajectory outcome from the gradient diagnostic
- **THEN** the successor rejects the request because the vector is same-batch legacy-objective direction evidence only, chunk zero merely shares seeded initialization, and later chunks already reflect successor updates

### Requirement: Raw evidence is bounded, durable, and independently readable
Every completed chunk SHALL publish fold, fit, feature, return, baseline,
advantage, action-family, scalar loss, gradient, clipping-path, installed-
gradient, pre/post model and Adam state, resource, and checkpoint evidence in
canonical JSON and fixed little-endian binary payloads.
Compressed payloads SHALL use deterministic gzip metadata and bind both
canonical uncompressed and stored bytes. The registration SHALL cap retained
decisions at `32,768`, one managed artifact at `64 MiB`, total stored managed
artifacts at `192 MiB`, and total canonical uncompressed payloads at `256 MiB`.
Before every primary or replay seed reaches the environment factory, the runner
SHALL flush an append-only access record with monotonic ordinal, chunk, exact
seed, attempt ordinal, and debited status; completion SHALL append its terminal
status without rewriting the prefix.

#### Scenario: A completed chunk is published
- **WHEN** baseline validation and one optimizer update complete
- **THEN** its diagnostic rows, sparse state features, four fitted models, five component vectors, complete and legacy-objective vectors, both clipping paths, raw installed gradient, pre/post model and Adam states, checkpoint, and resource prefix are durably published and closed by exact inventory digests

#### Scenario: Evidence is independently parsed
- **WHEN** the standard-library verifier reads a terminal payload
- **THEN** it reconstructs binary value order, fold and fit completeness, baseline equations and predictions, advantage and scalar-loss arithmetic, gradient sums and norms, both clipping paths, installed-gradient casting, legacy-objective comparison, and Adam transition without importing the control plane, runtime, Torch, or native simulator

#### Scenario: An incomplete chunk is interrupted
- **WHEN** a process exits after debiting one or more seeds but before publishing a complete chunk
- **THEN** every attempted seed and ordinal remains in the terminal access journal, any same-identity replay appends new records, and the verifier reconciles the exact primary and replay accesses against monotonic resource use

#### Scenario: Publication bytes drift
- **WHEN** gzip metadata, dtype, endian, shape, offset, row order, byte count, digest, managed inventory, or a temporary publication differs from its binding
- **THEN** terminal verification fails closed without rewriting the artifact

#### Scenario: A decision or byte ceiling would be exceeded
- **WHEN** collecting or publishing another row, vector, checkpoint, or artifact would cross a registered ceiling
- **THEN** the runtime stops before another optimizer update and preserves one terminal resource failure under the same identity

#### Scenario: Checkpoint envelope publication is interrupted
- **WHEN** one chunk's evidence and exact journal/resource coordinate are durable but its checkpoint envelope is absent
- **THEN** a later invocation may reconstruct exactly that one envelope from the immutable prefix and duplicated opaque runtime-checkpoint binding without another seed access or optimizer update, while every ambiguous or inconsistent prefix fails closed

#### Scenario: Terminal publication is interrupted
- **WHEN** the immutable terminal intent or intent plus terminal document is durable but the manifest is absent
- **THEN** a later invocation completes only the uniquely missing byte-identical terminal publication before dependency loading and does not reopen training

### Requirement: The empirical mechanism study is fresh and narrowly bounded
A later immutable registration SHALL select exactly 512 unique fresh scheduled
training seeds by one deterministic ascending exclusion algorithm from one
clean pushed source tree. It SHALL divide them into eight ordered chunks of 64,
permit at most eight optimizer updates, 500 decisions per episode, 32,768
retained decisions, 576 total environment episode accesses including one
incomplete-chunk replay reserve, CPU-only execution at ascension `0`, and
14,400 charged seconds. It SHALL bind the loaded native module and build
provenance, the exact pushed `origin/master` commit, the CommunicationMod
configuration, and the complete inert production-checkpoint tree. Preflight
and terminal closeout SHALL independently reobserve those identities.
It SHALL define no canary, holdout, teacher, checkpoint-selection, or frozen-
policy evaluation cohort and SHALL exclude every historical used, reserved,
diagnostic, canary, holdout, and previously untouched holdout seed.

#### Scenario: A fresh registration is built
- **WHEN** the implementation is clean, independently reviewed, committed, and pushed
- **THEN** the inventory binds the fixed pushed source tree, all transitive behavioral sources, native provenance, ascension zero, isolation identity, and complete historical exclusions, selects exactly 512 otherwise-unused seeds, and grants no native, seed, fitting, training, gameplay, or promotion authority

#### Scenario: A runtime seed or resource term drifts
- **WHEN** seed order, chunk membership, fold assignment, native module, CPU mode, episode/update/decision/byte/time ceiling, output root, or source identity differs from registration
- **THEN** execution fails before the divergent resource is used

#### Scenario: Four chunks reach exact family saturation
- **WHEN** a trailing four-complete-chunk window contains at least 64 multi-family `card_reward` or `shop` decisions and every one has the same singleton raw-score maximum family
- **THEN** the runner publishes `experiment_stopped_during_training_for_family_saturation` at the exact last-checkpoint journal coordinate before another seed or chunk and accesses no evaluation cohort

#### Scenario: Eight chunks complete without exact saturation
- **WHEN** all 512 scheduled trajectories and eight optimizer updates complete within every structural and resource bound
- **THEN** the runner publishes `experiment_completed_with_cross_fitted_mechanism_evidence` regardless of baseline fit, gradient cosine, floor, or victory

#### Scenario: Evaluation is requested
- **WHEN** a caller requests canary, holdout, teacher, frozen-policy, production-checkpoint, or gameplay evaluation under this identity
- **THEN** the successor rejects it without accessing the requested environment or seed

### Requirement: Registration, human approval, authorization, and execution are separate irreversible stages
Planning, source implementation, fresh inventory and all-false registration,
read-only exact execution request, explicit external human approval, tracked
authorization, one evidence-bearing execution, and terminal closeout SHALL be
separate boundaries. The execution request SHALL bind the pushed registration,
native identity, exact cohort/resources/output/retry terms, and false downstream
authorities. An authorization SHALL bind the canonical request digest and the
verbatim external approval text, time, and available task provenance; neither
an agent-authored review nor broad standing permission SHALL substitute for
approval of that exact request. A durable
first-seed journal marker SHALL distinguish pre-start setup from empirical
execution. A manual pre-start re-entry SHALL preserve the exact registration,
authorization, source-bound static documents, native identity, cohort,
controls, and output root and SHALL NOT consume the post-start resume. It SHALL
not automatically loop or substitute any term. After the marker, algorithm or
evidence failure SHALL be terminal, while at most one infrastructure
interruption MAY resume only the same identity and replay only its incomplete
registered chunk.

#### Scenario: An exact request has only agent review
- **WHEN** the registration and execution request are valid but no separate human message explicitly approves that exact digest and bounds
- **THEN** no authorization may be published and native loading, environment construction, seed access, fitting, and training remain rejected

#### Scenario: The human approves a different request
- **WHEN** recorded approval text, request digest, cohort, resource term, output root, retry rule, or false authority differs from the authorization candidate
- **THEN** the authorization is invalid and execution remains blocked

#### Scenario: Exact external approval is bound
- **WHEN** a separate human message explicitly approves the reviewed canonical request and its exact bounds
- **THEN** a tracked authorization may bind that request and verbatim approval without treating the human identity as a cryptographic claim

#### Scenario: Setup fails before seed access
- **WHEN** native loading, isolation, source, output-root, or process setup fails and the durable first-seed marker is absent
- **THEN** a later manual invocation may reopen only the exact source-bound static setup inventory or initialized zero-debit bootstrap with identical registration, authorization, source, native module, cohort, controls, and output root, without consuming the post-start resume

#### Scenario: A setup re-entry would change a term or loop automatically
- **WHEN** setup retry proposes a different module, seed, cohort, parameter, output root, or automatic retry cycle
- **THEN** the control plane rejects it before dependency loading or environment access

#### Scenario: Infrastructure interrupts one incomplete chunk
- **WHEN** the first post-start infrastructure interruption leaves a valid bootstrap or complete checkpoint and sufficient registered access/time budget
- **THEN** the same identity may restore exact model, optimizer, Python RNG, Torch generator, and chunk coordinates and replay only that incomplete chunk while retaining all previously debited resources

#### Scenario: A chunk has all episode terminals but no checkpoint
- **WHEN** infrastructure interrupts after all 64 registered episode accesses finish but before that chunk's complete checkpoint is durably published
- **THEN** the checkpoint coordinate still defines the chunk as incomplete and the sole resume may replay exactly that chunk without treating its access-only prefix as a complete update

#### Scenario: Infrastructure interrupts at a complete checkpoint boundary
- **WHEN** infrastructure interrupts after a complete checkpoint and before the next registered seed is debited
- **THEN** the sole resume restores that checkpoint and continues the next primary chunk without replaying a completed chunk or substituting a seed

#### Scenario: A second resume or evidence-driven retry is requested
- **WHEN** a second post-start resume, replacement identity, seed substitution, source change, estimator change, threshold change, tuning, or algorithm retry is requested
- **THEN** the request is rejected and the existing identity remains terminal

#### Scenario: The permitted resume is itself interrupted
- **WHEN** an infrastructure interruption occurs after the one post-start resume has been consumed
- **THEN** the runner charges the durable resource prefix, publishes one typed infrastructure failure, closes the identity as `experiment_failed_after_seed_access`, and grants no further resume

#### Scenario: Post-execution isolation differs
- **WHEN** the persisted post-isolation observation differs from the registered CommunicationMod or production-checkpoint identity
- **THEN** the runner preserves the observation and any typed failure witness but publishes no terminal intent, terminal, or manifest, and independent verification cannot classify the root as a valid bundle

#### Scenario: Active output is monitored
- **WHEN** the execution process is alive and holds its exclusive output lease
- **THEN** monitoring is limited to process liveness and does not read or mutate files below the active output root

#### Scenario: One stale lease is reclaimed for resume
- **WHEN** the sole permitted same-identity infrastructure resume proves that the recorded owner process is dead and validates the exact bootstrap, journal, resource prefix, complete checkpoints, and absence of an ambiguous temporary publication
- **THEN** it may atomically reclaim only that identity's stale lease before replaying the incomplete chunk

#### Scenario: Preexisting output cannot be reconstructed
- **WHEN** an output root, lease, journal, artifact, or temporary publication is unrelated, live, ambiguous, or differs from an exact source-bound setup, zero-debit bootstrap, checkpoint-publication recovery, terminal-publication recovery, or same-identity-resume inventory
- **THEN** the control plane fails closed without deleting, repairing, or replacing it

#### Scenario: Checkpoint and resource coordinates differ
- **WHEN** an incomplete chunk consumed episode accesses after the latest complete checkpoint
- **THEN** access-journal records, resource debits, and charged seconds remain monotonic, the checkpoint coordinate remains at the latest complete update, and resume cannot reclaim the consumed budget

### Requirement: Independent verification grants only mechanism evidence
After process exit, the standard-library verifier SHALL reobserve bound source
and pre/post isolation state, close the exact managed inventory, verify the external-
approval binding, every scheduled or replayed seed access, every Adam state
transition, and every complete chunk, and classify only valid completion,
valid family saturation, pre-start blocking, or preserved post-start failure.
No result SHALL establish policy quality, formal RL readiness, target-supported
outcomes, production loading, gameplay value, qualification, or promotion.

#### Scenario: A complete terminal bundle is valid
- **WHEN** all source, registration, external approval, authorization, access journal, resource, fold, baseline, advantage, gradient, Adam transition, checkpoint, artifact, isolation, and manifest checks pass
- **THEN** the verifier accepts exactly the registered completion or family-saturation verdict and keeps every downstream authority false

#### Scenario: A terminal claim lacks raw evidence
- **WHEN** a summary metric or verdict cannot be reconstructed from retained registered rows and payloads
- **THEN** the verifier rejects the bundle rather than trusting the producer's claim

#### Scenario: Mechanism evidence appears favorable
- **WHEN** baseline fit improves, cross-fitted and legacy gradients differ, exact family saturation is absent, floor rises, or a victory occurs
- **THEN** the report records the observation but authorizes only a later read-only audit and not another experiment, formal training, model loading, gameplay, qualification, or promotion

#### Scenario: A success verdict contains access after its last checkpoint
- **WHEN** a completion or family-saturation terminal journal advances beyond `checkpoint_count * 64` primary positions or retains a resume candidate after the last checkpoint
- **THEN** independent verification rejects the bundle even if its manifest and aggregate resource count are internally rehashed

#### Scenario: Source-only implementation completes
- **WHEN** synthetic leakage, fold, float64 ridge, advantage, gradient, dual-clipping, threshold-neighborhood legacy normalization, optimizer-installation and Adam replay, binary, access-journal, human-approval, lifecycle, resume, and verifier tests pass under the reviewed source identity
- **THEN** the capability becomes eligible only for a separate fresh inventory and all-false registration, with no empirical authority implied by the tests
