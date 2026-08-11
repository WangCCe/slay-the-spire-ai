## ADDED Requirements

### Requirement: The successor is additive and source isolated
The capability SHALL add a new card-acceptance empirical control plane, Torch
runtime, seed-inventory utility, independent standard-library verifier, schemas,
tests, and reports without editing or importing private helpers from a consumed
empirical runner. Control-only import and commands SHALL NOT import Torch,
native adapter, gameplay, CommunicationMod, or environment modules. Every
direct and transitive behavioral dependency used at runtime SHALL be present in
the new source binding.

#### Scenario: Source-only control is imported
- **WHEN** registration, request, authorization, inventory, rollback-planning, or verification modules are imported, or request render/pre-build validation commands execute
- **THEN** no Torch/native module is imported, no environment is constructed, no seed is discovered or accessed, and no model is fitted or loaded

#### Scenario: A consumed empirical identity is proposed as fresh evidence
- **WHEN** a prior cohort, reserved seed, inventory, source registration, authorization, checkpoint, output root, runtime schema, verifier result, canary, holdout, or outcome is supplied as a new candidate or control identity
- **THEN** the capability rejects it before native loading or seed access

### Requirement: Consumed evidence is preserved byte for byte
Before implementation edits, the capability SHALL bind the reviewed
pre-implementation Git tree and publish a canonical preservation manifest in an
independently reviewed, committed, and pushed boundary. Its closed source-path
array SHALL contain exactly the consumed cross-fitted control plane, Torch
runtime, independent verifier, seed-inventory utility, and main successor spec
paths named in the design. Its closed artifact-file array SHALL contain exactly
the 20260808-r2 registration/review, request/review, standing delegation,
delegated approval/review, authorization/review, execution preflight,
JSON/Markdown postmortem, and r5 readiness closeout paths named in the design.
Its closed artifact-root array SHALL contain exactly the r2 execution root, r5
readiness publication root, and the source-keyed r5 readiness-attempt root bound
by the consumed registration. The manifest SHALL bind both closed arrays, exact
file SHA-256 identities, canonical directory-inventory digests, the baseline Git
tree, and its own digest. Source qualification SHALL reobserve the same arrays
and reject a changed, missing, extra, reordered, omitted, or newly importing
consumed identity. Preservation SHALL NOT make consumed bytes eligible as fresh
evidence.

#### Scenario: Source implementation preserves consumed identities
- **WHEN** source-only qualification reobserves every registered consumed path and the independently pushed baseline tree/manifest
- **THEN** file bytes, ordered directory inventories, counts, sizes, and digests exactly match the pre-edit manifest and consumed modules do not import the successor

#### Scenario: The preservation baseline is incomplete or late
- **WHEN** implementation edits predate the pushed manifest boundary or a consumed path/root is absent from either closed array
- **THEN** source qualification fails rather than absorbing the drift into a new baseline

#### Scenario: One consumed byte is mutated
- **WHEN** a synthetic preservation fixture changes, removes, adds, or reorders one consumed entry
- **THEN** preservation validation fails before registration eligibility

### Requirement: Composite initialization is deterministic and storage disjoint
With model seed `0`, the runtime SHALL construct exactly one CPU float32
`StateConditionedCandidateRanker(HASH_DIM, DEFAULT_HIDDEN_DIM)` base state and
copy every state-dict key and tensor byte into exactly five independent
rankers: `candidate.card_policy.family_head`,
`candidate.card_policy.conditional_ranker`,
`candidate.frozen_noncard_ranker`, `control.shared_card_ranker`, and
`control.frozen_noncard_ranker`. The control shared ranker SHALL produce both
family logits over the same canonical mean family features and conditional
logits over candidates. The destination key sets, shapes, dtypes, values, and
per-tensor SHA-256 identities SHALL equal the base mapping, while parameter
objects and storage SHALL be pairwise disjoint. The paired bootstrap SHALL bind
all five rankers and each arm's separate card/non-card generators under new
schemas and checkpoint identities.

#### Scenario: Bootstrap is reproduced
- **WHEN** two fresh runtimes use the registered model and generator seeds
- **THEN** their canonical paired checkpoint bytes and digest are exact and all five rankers match the base values without shared objects or storage

#### Scenario: One destination mapping drifts
- **WHEN** a key is absent, extra, renamed, reordered, reshaped, recast, changed in value, or shares parameter/storage identity with another head
- **THEN** bootstrap and checkpoint validation fail before an optimizer or environment is constructed

### Requirement: Both arms train only their card-reward parameters
The candidate optimizer SHALL contain all and only `family_head.*` and
`conditional_ranker.*` parameters in canonical name order. The control
optimizer SHALL contain all and only `shared_card_ranker.*` once, even though
both family and conditional terms differentiate through it. Both
`frozen_noncard_ranker` copies SHALL have `requires_grad=false`, SHALL be absent
from both optimizers, and SHALL remain byte-identical to bootstrap and each
other in every checkpoint, canary, holdout, and terminal artifact. Each arm
SHALL sample family then candidate with its own identically seeded checkpointed
card generator. Every other noncombat decision SHALL use that arm's frozen
ranker and separate identically seeded non-card generator.

#### Scenario: A card reward is sampled during training
- **WHEN** either arm reaches a valid card reward with one or more explicit families
- **THEN** that arm samples the sorted family distribution first, samples a candidate within that family second, and applies only the aligned legal action ID

#### Scenario: A non-card decision is reached
- **WHEN** either arm reaches route, shop, event, or another non-card-reward decision
- **THEN** only that arm's frozen non-card ranker and non-card generator select among legal candidates and no trainable card parameter or card generator is advanced

#### Scenario: Frozen behavior changes
- **WHEN** any frozen parameter byte, optimizer membership, generator ownership, candidate projection, or non-card selection rule differs
- **THEN** the current chunk or frozen evaluation fails closed and no subsequent seed is accessed

### Requirement: Frozen evaluation is deterministic and tie free
Candidate and control evaluation SHALL select a card reward by the unique
maximum family logit followed by the unique maximum conditional logit within
that family. Non-card evaluation SHALL select the unique maximum frozen-ranker
candidate score. Candidate order, family probability, joint probability, and
lexical order SHALL NOT break a maximum tie.

#### Scenario: Both greedy stages are unique
- **WHEN** one family and one candidate within it are unique maxima
- **THEN** the runtime applies exactly that legal action and retains both maximum sets and margins

#### Scenario: A maximum is tied
- **WHEN** either the family stage or selected-family conditional stage has more than one maximum identity
- **THEN** the evaluation fails before applying an action rather than selecting a tie member

### Requirement: Advantages are cross-fitted and unscaled
Every paired update SHALL contain exactly 64 complete trajectories per arm from
the same ordered training-seed slice. Each arm SHALL separately reuse the
registered four-fold, trajectory-disjoint baseline contract with 16 held-out
and 48 fit trajectories per fold, 128 pre-decision state features, ridge
coefficient `0.001`, CPU float64 canonical arithmetic, prediction clipping to
`[0, 3]`, and formal undiscounted return. Each policy weight SHALL equal exactly
`return_to_go - clipped_held_out_prediction` with no later centering,
normalization, standardization, learned scale, category transform, or clipping.

#### Scenario: A card-reward advantage is constructed
- **WHEN** its complete trajectory, fold, fit-set, feature, return, prediction, clipping, and decision provenance pass the cross-fitted contract
- **THEN** the selected family and conditional terms receive the same exact held-out residual advantage

#### Scenario: Post-decision data reaches the baseline
- **WHEN** selected action/family, score, reward, successor state, terminal outcome, seed, or another post-decision value appears in baseline features
- **THEN** the complete chunk is rejected before loss construction

### Requirement: The objective has four fixed head-owned components
For exactly `M` valid card-reward decisions in one arm's chunk, where `M > 0`,
that arm's full loss SHALL be the ordered sum of:

```
card_reward_family_policy =
    -sum(selected_family_log_probability * advantage) / M
card_reward_conditional_policy =
    -sum(selected_conditional_log_probability * advantage) / M
family_entropy_regularizer = -0.01 * mean(family_entropy)
conditional_entropy_regularizer =
    -0.01 * mean(mean(per_family_conditional_entropies))
```

Both arms SHALL use the same four component formulas and coefficients. The two
policy coefficients SHALL be one. The inner conditional entropy mean
SHALL weight every explicit family equally within one decision. Expected
conditional entropy and joint entropy SHALL remain diagnostic and SHALL NOT
enter the loss. No caller override is permitted.

#### Scenario: A valid chunk builds its loss
- **WHEN** every card-reward term and advantage is finite and identity aligned
- **THEN** all four connected scalar components appear in canonical order, reconstruct the separately supplied full loss, and preserve selected-family versus selected-conditional gradient ownership

#### Scenario: A chunk has no card reward
- **WHEN** 64 complete trajectories contain zero valid card-reward decisions
- **THEN** the identity terminates as an algorithm failure before an optimizer step rather than substituting a zero-loss update

#### Scenario: A cross-head entropy is added
- **WHEN** expected conditional entropy, joint entropy, family-probability weighting of conditional entropy, or another unregistered component reaches the loss
- **THEN** objective validation fails before gradient construction

### Requirement: Matched fixed Adam updates are independently replayable
The runtime SHALL use exactly one CPU `torch.optim.Adam` per arm: candidate over
both disjoint card heads and control over its shared card ranker. Each optimizer
SHALL have one parameter group with learning rate `0.001`, betas
`(0.9, 0.999)`, epsilon `1e-8`, zero weight decay, no AMSGrad, and no alternate
maximize, foreach, capturable, differentiable, or fused mode. Separately per
arm, the runtime SHALL independently differentiate the four components and
separately supplied full loss, prove ordered float64 gradient reconstruction
and registered ownership, compute one arm-local global norm clip factor at
ceiling `1.0`, install the canonical CPU float32 gradient, and retain complete
pre/post parameter and Adam state for standard-library replay.

#### Scenario: A valid update is applied
- **WHEN** both arms' scalar, gradient, ownership, finiteness, reconstruction, clipping, parameter-order, and optimizer checks pass
- **THEN** exactly one Adam step per arm consumes its installed gradient and the independent verifier reproduces both parameter and moment transitions within fixed reviewed tolerances

#### Scenario: A training control drifts
- **WHEN** model seed, architecture, parameter set/order, coefficient, optimizer option, gradient ceiling, reward, discount, or advantage arithmetic differs from registration
- **THEN** execution fails before the affected optimizer step and cannot tune or retry the identity

### Requirement: Fresh cohorts are selected once from an explicit inventory
After clean reviewed source publication, a separate exact tracked inventory
authorization SHALL permit only registered repository evidence reads, seed
discovery, and cohort materialization; native loading, environment seed access,
model loading, fitting, training, and evaluation SHALL remain false. Under that
authority, a standard-library `build-inventory` operation SHALL bind
one fixed Git tree, scan an explicit ordered historical source set, and exclude
every used, selected, reserved, diagnostic, failed-access, training, evaluation,
canary, and holdout seed. Candidate output, staging, sealed, scratch, attempt,
and temporary roots SHALL be excluded before traversal and SHALL NOT be
recursively ingested. One fixed ascending algorithm SHALL select exactly 512
unique training seeds, 128 canary seeds, and 512 holdout seeds with pairwise
disjoint roles and zero historical collisions.

Import, request rendering, and pre-build request/authorization validation SHALL
NOT scan historical inputs, discover seed values, or materialize a cohort.
Rendering or validating the inventory request/authorization SHALL NOT itself
grant the `build-inventory` operation. After a successful build, a distinct
`verify-inventory` operation under the same exact inventory authorization MAY
read the materialized inventory and registered historical source identities to
reconstruct provenance, exclusions, and selected values. It SHALL NOT select,
replace, or materialize a cohort or import native, model, environment, fitting,
training, or evaluation runtime.

#### Scenario: A fresh inventory is registered
- **WHEN** the exact inventory authorization validates, `build-inventory` publishes once, and the post-build independent `verify-inventory` operation scans the registered source identities
- **THEN** they reconstruct identical ordered provenance, exclusions, selected values, role digests, and whole-inventory SHA-256

#### Scenario: Pre-build validation attempts post-build verification
- **WHEN** an import, render, or pre-build validation command attempts to scan historical sources or read selected seed values
- **THEN** it fails before seed discovery because only separately authorized `build-inventory` and post-build `verify-inventory` have that source-only authority

#### Scenario: Inventory build lacks exact authority
- **WHEN** `build-inventory` is requested with only source publication, proposal approval, render/validate output, or an authority map that enables native/environment/model operations
- **THEN** seed discovery and cohort materialization are rejected

#### Scenario: An output root enters the inventory
- **WHEN** a candidate, staging, sealed, scratch, attempt, temporary, or recursively generated artifact path would be traversed
- **THEN** inventory construction fails before selection rather than admitting self-generated rows

### Requirement: Training is bounded and detects exact family collapse
Training SHALL execute at most 512 registered pairs in the same arm order, with
64 seeds per paired chunk, at most 1,024 training episode accesses, at most
eight updates per arm, and at most 16 total training optimizer steps. If no registered
early-collapse gate fires, it SHALL execute exactly all 512 pairs and eight
updates per arm. There SHALL be no epoch replay, checkpoint selection, or
extension. After each complete paired checkpoint, the runtime
SHALL inspect the candidate's trailing four complete chunks. If they contain at
least 64 valid multi-family card rewards and every unique greedy family has the
same identity, it SHALL publish
`experiment_stopped_during_training_for_family_saturation` before another seed,
canary, or holdout access. Control saturation and every other diagnostic SHALL
be retained but SHALL NOT stop, extend, or tune training.

#### Scenario: Training completes without exact collapse
- **WHEN** all eight registered paired chunks finish and no candidate four-chunk saturation predicate is true
- **THEN** terminal candidate and trained-control checkpoints become eligible for a separate candidate/control seal

#### Scenario: Fewer than four chunks are complete
- **WHEN** the candidate has fewer than four complete paired chunks
- **THEN** the saturation predicate is ineligible and cannot stop training

#### Scenario: Exact collapse is observed
- **WHEN** the first eligible trailing four-chunk window meets every denominator and singleton-family condition
- **THEN** training closes at its latest complete checkpoint with zero canary and holdout access and no replacement initialization or coefficient

### Requirement: Candidate and control are sealed before canary access
Only an independently verified exact
`training_completed_without_family_saturation` verdict proving 512 pairs, eight
complete chunks, eight updates per arm, and no collapse or failure may produce a
tracked source-only seal before canary access. The seal SHALL bind the source
commit; candidate and control source, checkpoint, and configuration SHA-256
identities; seed-inventory SHA-256; exact family/conditional/base mapping;
candidate-disabled default; exact experiment-local control target; production
CommunicationMod configuration; production checkpoint inventory; output root;
and rollback authority. Candidate and control SHALL remain frozen after sealing.
A collapse or failure checkpoint SHALL remain immutable evidence but SHALL NOT
be seal- or canary-eligible.

#### Scenario: A complete seal is published
- **WHEN** the exact no-collapse completion verdict, all 512 pairs, all eight complete chunks, all eight updates per arm, and both frozen trained-arm checkpoints independently verify
- **THEN** producer and verifier reconstruct every required binding and candidate remains disabled pending a separate exact canary authorization

#### Scenario: Collapse or failure evidence is offered for sealing
- **WHEN** training stopped for family saturation, ended in failure, completed fewer than 512 pairs or eight chunks, or lacks eight updates per arm
- **THEN** seal publication and canary eligibility are rejected while the checkpoint remains evidence only

#### Scenario: A sealed identity changes
- **WHEN** source, checkpoint, config, target, seed inventory, production inventory, or output binding differs after sealing
- **THEN** canary access is rejected and rollback keeps the candidate disabled

### Requirement: The at-most-once canary is structural
One separately authorized canary SHALL use exactly 128 registered paired seeds.
For every seed, candidate and control SHALL each execute twice from the exact
same seed and frozen arm; the second execution SHALL reproduce the first arm's
decision and terminal payload exactly. Before either replay environment is
constructed, each first-run candidate and control decision/terminal payload
SHALL be published to a write-once, seed-ordered, hash-chained output commitment
bound to the sealed arm source, checkpoint, and config hashes. Replay and
control reproduction SHALL be judged only against those registered commitment
bytes. A first output SHALL NOT be replaced, repaired, or rehashed after replay.
The canary SHALL therefore consume at most 512 environment episode accesses and
SHALL perform no update to either sealed arm.

Candidate-arm valid multi-family card rewards SHALL provide a selected-family
denominator of at least 64 and a unique-greedy-family denominator of at least
64. Every counted family set SHALL contain at least two identities. The maximum
selected-family rate and maximum unique-greedy-family rate SHALL each be no
greater than `0.95`. All actions SHALL be legal and every identity,
probability, score, tie set, and terminal SHALL verify.

The canary SHALL choose the first eligible candidate-arm decision in exact
`(seed, decision_index, decision_id)` order. Eligibility SHALL require a valid
multi-family card reward, finite terms, and one selected legal action. It SHALL
clone the sealed candidate model and exact candidate Adam state, zero gradients
with `set_to_none=true`, and build exactly
`-selected_family_log_probability - 0.01 * family_entropy`, using synthetic
unit advantage one and no conditional or cross-head term. It SHALL
differentiate canonical candidate parameters, apply the registered global norm
clip `1.0`, and replay exactly one candidate Adam step.

The shadow gate SHALL require a finite nonzero family gradient, at least one
changed family parameter, exact unchanged conditional parameter and Adam-state
bytes, exact unchanged conditional logits, probabilities, and selected term at
the same decision, and independent replay of the changed family state. The
shadow clone SHALL never replace or mutate a sealed arm or environment.

#### Scenario: Every canary gate passes
- **WHEN** both-arm exact replay, legality, control reproduction, both concentration gates, denominator/cardinality gates, and family-only shadow invariance all pass
- **THEN** and only then may a separate exact holdout request be published while both arms remain frozen

#### Scenario: One canary gate fails
- **WHEN** any registered identity, replay, legality, denominator, concentration, shadow, resource, publication, or authority gate fails
- **THEN** the canary identity terminates, candidate remains disabled, and all 512 holdout seeds remain unaccessed

### Requirement: The untouched holdout has preregistered outcome classes
After a passing canary and separate exact authorization, one at-most-once
holdout SHALL execute the frozen candidate and control once on each of exactly
512 untouched paired seeds, for at most 1,024 episode accesses. It SHALL reapply
legality, identity, finite-output, and candidate concentration gates. It SHALL
use the existing formal-reward `floor_progress` channel as its floor endpoint.
In ascending registered seed order, each paired difference SHALL be candidate
`floor_progress` minus control `floor_progress`. A fresh standard-library
`random.Random(0)` SHALL generate exactly 10,000 resamples in outer-resample,
inner-draw order; each resample SHALL make exactly 512 consecutive
`randrange(512)` calls with replacement and store their arithmetic mean. After
sorting the 10,000 means ascending, quantiles `p=0.025` and `p=0.975` SHALL use
linear interpolation at `(10000 - 1) * p` between the values at
`floor(position)` and `ceil(position)`. The paired-floor signal SHALL mean only
that the resulting lower endpoint is strictly greater than zero.

Only after all 512 pairs and every structural, concentration, resource,
bootstrap, and publication check pass SHALL the normal terminal outcome be
exactly one of:

- `victory_and_floor_signal` when candidate victories are strictly greater than
  control victories and the paired-floor lower bound is greater than zero;
- `floor_only_signal` when candidate and control victories are equal and the
  paired-floor lower bound is greater than zero;
- `inconclusive_signal` when candidate victories are strictly greater and the
  paired-floor lower bound is not greater than zero, or candidate victories are
  strictly fewer and the paired-floor lower bound is greater than zero; or
- `no_learning_signal` for the remaining two cells: equal victories without a
  floor signal, or fewer candidate victories without a floor signal.

The predicates SHALL be pairwise disjoint and exhaustive over the exact
three-way victory comparison and binary paired-floor signal. The verifier SHALL
reconstruct the complete six-cell truth table before accepting one class.

Only `victory_and_floor_signal` SHALL satisfy this experiment's preregistered
policy-quality evidence threshold. No class SHALL grant production loading,
gameplay, qualification, or promotion authority.

#### Scenario: Holdout is complete
- **WHEN** all 512 pairs and all structural, concentration, resource, bootstrap, and publication checks pass
- **THEN** the independent verifier reconstructs exactly one outcome class from raw registered pair evidence

#### Scenario: Holdout does not complete validly
- **WHEN** a structural, concentration, resource, bootstrap, access, or publication failure occurs before normal closeout
- **THEN** the run publishes its separately classified failure verdict and SHALL NOT publish any of the four evidence outcome classes

#### Scenario: Holdout is requested before canary passage
- **WHEN** canary is absent, incomplete, failed, changed, retried, resumed, or not independently verified
- **THEN** holdout environment construction and seed access are rejected

### Requirement: Empirical stages require separate exact tracked authority
Source implementation, inventory request/authorization, fresh registration,
training request/authorization,
post-training seal, canary request/authorization, and holdout
request/authorization SHALL be separate tracked and pushed boundaries. An exact
request MAY use a canonical delegated-approval resolution only when a recorded
solo-maintainer grant under the existing standing-delegation schema explicitly
covers this repository, request class, fixed exclusions, and revocation rule,
and has not been revoked. The grant SHALL predate and remain
outside the successor request and SHALL bind verbatim external-human grant
text, timestamp, message/task IDs, source kind, scope, exclusions, revocation
rule, and self-digest. This change, its producer, and its request SHALL NOT
create or modify the grant. The resolution SHALL bind the exact independently
reviewed request digest and thereby bind that request's resource bounds,
execution authority, and false downstream authorities. It SHALL NOT be
represented as verbatim external-human text.

Before authorization publication, one source-only validation operation SHALL
consume the exact request, original independent-review bytes, approval record,
and authorization record. It SHALL validate both approval modes, recompute the
review byte digest, and prove every request-review-approval-authorization link;
standalone validation of digest-shaped authorization fields is insufficient.

Approval publication and every inventory, training, canary, and holdout launch
SHALL require a fresh authoritative current-conversation revocation observation
binding checked-at time and the latest observed human-message watermark. If the
controller cannot inspect that conversation state, or a later explicit
revocation is observed, delegated approval and launch SHALL fail closed. The
independent verifier SHALL validate canonical provenance and observation
bindings while treating human identity and conversation truth as a declared
procedural trust boundary.

As an alternative to delegated approval, exact external-human approval SHALL be
valid only after the one exact request and its independent review are tracked and
pushed. Its canonical record SHALL bind the request digest, verbatim approval
text, timestamp, message/task IDs, source kind `external-human`, repository and
request class, requested scope, ceilings, exclusions, every false downstream
authority, and a self-digest. The message SHALL postdate and unambiguously
approve that request. The producer and verifier SHALL NOT generate, amend, or
reinterpret it. Approval publication and launch SHALL apply the same fresh
current-conversation watermark and later-revocation rules used by delegated
approval; human identity and conversation truth remain the same procedural trust
boundary.

#### Scenario: Standing delegation resolves an exact request
- **WHEN** canonical grant, scope, revocation state, registration, request, independent review, and digest bindings all validate
- **THEN** a tracked authorization may be published without requiring the maintainer to transcribe the generated tuple

#### Scenario: Authorization publication omits approval evidence
- **WHEN** an authorization has a valid self-digest but its review bytes or approval record are absent, changed, or do not bind the same request
- **THEN** publication validation rejects it before the authorization becomes a tracked execution boundary

#### Scenario: Delegation is revoked after authorization publication
- **WHEN** the fresh launch-time observation contains a later explicit human revocation than the bound grant or approval
- **THEN** the static authorization cannot start or resume inventory, training, canary, or holdout work

#### Scenario: Current revocation state is unavailable
- **WHEN** delegated or exact external-human authority is proposed but authoritative current-conversation state or its latest human-message watermark cannot be inspected
- **THEN** approval publication and launch are rejected pending restored authoritative observation and a valid exact approval path

#### Scenario: Exact external approval binds one request
- **WHEN** a post-request external-human message and its canonical record bind the exact pushed request/review, scope, ceilings, exclusions, false authorities, provenance, self-digest, and fresh non-revocation observation
- **THEN** a tracked authorization may be published for only that request

#### Scenario: External approval is broad, inferred, or stale
- **WHEN** human text predates the request, omits its exact binding, is generated or reinterpreted by the producer, exceeds scope, or has a later revocation
- **THEN** authorization publication and stage launch fail closed

#### Scenario: Authority is inferred from proposal approval
- **WHEN** only proposal approval, broad unbound permission, agent review, or an unpushed request exists
- **THEN** native loading, environment construction, seed access, fitting, training, canary, and holdout remain blocked

### Requirement: Execution lifecycle is fail closed and resource monotonic
Before runtime import, the producer SHALL validate pushed source, tracked-clean
state, exact registration and authorization, Windows interpreter, native bytes
and provenance, production isolation, absent or exactly reopenable output,
exclusive lease, stage authority, and a fresh launch-time revocation observation
when delegated or exact external-human authority is used. It SHALL capture one immutable private
execution context and reuse it without per-seed registration rescans or deep
copies. Every seed access SHALL be write-ahead journaled and every terminal path
SHALL charge final elapsed time and reconcile the exact access prefix.

Setup may repeat only before the first seed under the same identity. Before
canary, at most one manual training continuation SHALL be allowed from a
complete 64-seed paired checkpoint when no later arm debit exists. A partial
uncheckpointed chunk SHALL be terminal. After canary start, no continuation,
resume, retry, replacement, update, tuning, source change, threshold change, or
seed substitution SHALL be permitted. Lease ownership SHALL bind the true
runtime child process; active output may be read or reclaimed only after that
process is proven dead.

#### Scenario: Complete-boundary training continuation is valid
- **WHEN** the sole continuation restores both exact arm models, both optimizers, every arm generator, checkpoint coordinate, registration, authorization, fresh revocation observation, and resource prefix with no later debit
- **THEN** it continues at the next registered primary seed without replaying a completed or partial chunk

#### Scenario: A wrapper exits while its child is alive
- **WHEN** the shell or launcher process exits but the lease-bound runtime child remains alive
- **THEN** monitoring treats execution as active and does not read, reclaim, repair, resume, or replace its output

#### Scenario: Dead-owner terminalization uses a fresh command observation
- **WHEN** a pushed terminalization authority has a fresh non-revoked launch observation and binds a dead owner's original pushed run envelope
- **THEN** the fresh observation authorizes only the closure command, the original run observation reconstructs the lease-bound lifecycle identity, both chains require the same request, approval, and authorization, and registration remains opaque

#### Scenario: Terminalization cannot reconstruct the original run identity
- **WHEN** the bound original run envelope, launch observation, request, approval, authorization, lease, or failure prefix differs
- **THEN** terminalization fails before closure publication, performs no empirical access, and grants no training retry

#### Scenario: A terminal path omits elapsed charge
- **WHEN** failure occurs before the first checkpoint or in any later stage
- **THEN** terminal publication is invalid unless final charged time and exact access prefix are durably reconciled

### Requirement: Resource and publication bounds are fixed
The complete logical execution SHALL be CPU-only at ascension `0` and SHALL use
at most 1,024 paired training episode accesses, eight training optimizer updates
per arm, 16 total training optimizer steps, one separately charged isolated
canary shadow optimizer step that cannot mutate either sealed arm, 512 canary
accesses, 1,024 holdout accesses, 2,560 total environment episode accesses, 500
decisions per episode, and 28,800 charged seconds. Any one managed artifact
SHALL be no
larger than 64 MiB, all stored managed artifacts no larger than 256 MiB, and all
canonical uncompressed payload no larger than 512 MiB.

Managed evidence SHALL use deterministic canonical JSON plus bounded
little-endian binary/gzip payloads with `mtime=0`. Checkpoints and stage markers
SHALL be write once or byte identical. Terminal intent SHALL bind the complete
artifact prefix; terminal and manifest SHALL publish only after intent, with
manifest last. No unbounded decision rows or tensors may appear inline in
canonical report JSON.

#### Scenario: A resource bound would be crossed
- **WHEN** the next access, update, decision, elapsed charge, stored artifact, or canonical payload would exceed registration
- **THEN** execution stops before that operation and preserves one terminal resource failure without raising a bound or retrying

#### Scenario: Existing publication bytes drift
- **WHEN** a write-once path exists with different bytes, a staging sibling is ambiguous, or terminal order is incomplete
- **THEN** publication fails closed without overwriting, deleting, repairing, or replacing evidence

### Requirement: Rollback restores control targeting and verifies production
The registered rollback authority SHALL name the exact experiment-local target,
control checkpoint/config, production CommunicationMod configuration, production
checkpoint inventory, candidate-disabled value, and trigger classes
`authority`, `canary`, `holdout`, `identity`, `legality`, `preflight`, and
`publication`. On any trigger, rollback SHALL preserve immutable empirical
evidence, restore the experiment target binding to the exact control, keep
candidate enablement false, verify the production identities, and grant no
promotion authority. It SHALL NOT tune, replace, retry, resume after canary, or
rewrite a consumed result.

Every rollback-required failure terminal SHALL map to exactly one fixed trigger
class under this precedence and closed mapping:

- `authority`: grant, revocation, approval, authorization, or stage authority;
- `identity`: source, checkpoint, config, cohort, target, production, child,
  process, or lease identity;
- `legality`: candidate/action legality, schema, finiteness, objective support,
  or a zero-card-reward chunk;
- `preflight`: interpreter, native, isolation, output, dependency, or setup
  failure before the first debit;
- `canary`: registered training-family saturation or a canary gate/failure;
- `holdout`: a holdout gate, access, evaluation, or classification failure;
- `publication`: resource/time/access accounting, partial chunk, journal,
  evidence, byte bound, staging, checkpoint, terminal, or manifest failure not
  already classified above.

The mapping SHALL NOT extend or rename the fixed trigger tuple. An unmapped or
multiply classified rollback-required failure terminal SHALL invalidate
rollback and failure publication. The four complete holdout evidence classes
SHALL be normal closeout outcomes rather than rollback failure triggers. Normal
closeout SHALL still restore the exact experiment-local control target, keep the
candidate disabled, verify production isolation, and grant no downstream
authority.

#### Scenario: A registered gate fails
- **WHEN** any rollback trigger is observed and exact rollback authority validates
- **THEN** the control target is restored and verified, candidate is disabled, production identities are verified, and the failure remains immutable

#### Scenario: Every rollback-required failure path is classified
- **WHEN** training collapse, zero-card algorithm failure, resource/time failure, partial chunk, child/lease failure, canary failure, holdout failure, or publication failure reaches failure terminalization
- **THEN** the exact precedence assigns one and only one fixed rollback trigger before terminal publication

#### Scenario: A complete holdout closes normally
- **WHEN** the independent verifier reconstructs one of the four complete holdout evidence classes
- **THEN** normal closeout restores and verifies the control target and production isolation without manufacturing a rollback failure trigger

#### Scenario: Production inventory drift is external
- **WHEN** production configuration or checkpoint bytes differ even though the experiment never had authority to change them
- **THEN** rollback records terminal isolation failure and cannot silently manufacture or substitute production checkpoint bytes

### Requirement: Independent verification keeps downstream authority false
The independent verifier SHALL use only the Python standard library and SHALL
reconstruct source/config/checkpoint identities, seed roles and access prefixes,
initialization mapping, cross-fitted folds and advantages, four-component loss,
gradient ownership and Adam transitions, frozen non-card bytes, exact replay,
canary denominators/rates/shadow invariance, holdout bootstrap/classification,
resource accounting, rollback observation, isolation, terminal intent, and
manifest closure. Every registration and terminal SHALL keep formal RL, causal,
OPE, production model loading, gameplay, CommunicationMod, qualification, and
promotion authority false.

#### Scenario: Source-only implementation is complete
- **WHEN** focused synthetic, preservation, control, lifecycle, verifier, import-isolation, configured repository gates, strict OpenSpec validation, deterministic publication, and independent review pass
- **THEN** only the source implementation becomes eligible for a separate fresh all-false registration and no gameplay validation is required because production behavior is unchanged

#### Scenario: A terminal summary lacks raw support
- **WHEN** a checkpoint, denominator, rate, paired outcome, bootstrap bound, verdict, rollback, isolation, or authority claim cannot be reconstructed from bound raw evidence
- **THEN** independent verification rejects the bundle without inferring success from producer hashes or summaries
