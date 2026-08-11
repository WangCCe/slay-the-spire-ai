## Context

The completed `noncombat-card-acceptance-objective-architecture-contract`
defines disjoint family and conditional heads for `card_reward`, canonical mean
family features, exact probability/entropy terms, and a float64 acceptance
coordinate. It deliberately selects no initialization, loss, optimizer, cohort,
or empirical authority.

The consumed cross-fitted experiment is immutable mechanism evidence. It
completed 512 trajectories and eight updates, retained zero victories, and
ended with `1,773/1,774` final-window card rewards having `take` as the unique
greedy family. Its cohort, checkpoints, runtime, registration, verifier, and
outcomes cannot serve as fresh or blind evidence. Earlier simulator-learning
control planes nevertheless establish useful source-only patterns for seed
exclusion, immutable registrations, write-ahead access accounting, checkpoint
closure, independent verification, and production isolation.

This change is planning only. It imports no Torch or native module, constructs
no environment, materializes no seed inventory, fits no model, and changes no
CommunicationMod or production checkpoint bytes.

## Goals / Non-Goals

**Goals:**

- Test whether the disjoint card-acceptance architecture can learn without
  reproducing greedy family collapse.
- Isolate that question by freezing route, shop, event, and every other
  non-card-reward decision policy.
- Select initialization, objective coefficients, optimizer, training schedule,
  canary gates, holdout endpoints, and evidence lifecycle before seed access.
- Compare one trained disjoint-head candidate against a matched trained
  shared-head control on fresh paired simulator seeds.
- Produce independently verifiable negative or positive evidence while keeping
  the candidate disabled outside the experiment.

**Non-Goals:**

- Reusing, resuming, repairing, or tuning any consumed empirical identity.
- Training route, shop, event, combat, or general noncombat policy behavior.
- Changing policy input, candidate projection, formal reward, cross-fitted
  baseline arithmetic, or native simulator mechanics.
- Loading a production model, starting Slay the Spire or CommunicationMod,
  changing live gameplay, running OPE, or claiming causal card value.
- Qualifying or promoting a checkpoint. Even a positive holdout result only
  makes a separate production-qualification proposal eligible.

## Decisions

### Add isolated successor modules without changing consumed runners

Implementation will add four source families:

1. `noncombat_card_acceptance_empirical_successor_experiment.py`, a
   standard-library control plane for immutable metadata, registration,
   authorization, lifecycle, publication, rollback observation, and CLI entry;
2. `noncombat_card_acceptance_empirical_successor_runtime.py`, the Torch/native
   runtime for initialization, rollout, cross-fitted objective construction,
   optimizer updates, canary, and holdout;
3. `noncombat_card_acceptance_empirical_successor_seed_inventory.py`, a
   standard-library historical exclusion scanner and fixed ascending selector;
4. `verify_noncombat_card_acceptance_empirical_successor.py`, an independent
   standard-library verifier that imports neither producer nor Torch/native
   runtime.

The runtime may reuse reviewed public APIs from the card-acceptance policy and
objective, state-conditioned ranker and input projection, candidate projection,
formal reward, simulator adapter, and cross-fitted advantage contract. It may
port small lifecycle algorithms with new tests, but it will not import private
helpers from or edit a consumed empirical runner. Every direct and transitive
behavioral dependency is included in the new source binding.

Before implementation edits, bind the reviewed pre-implementation Git tree and
publish a compact preservation manifest in its own independently reviewed,
committed, and pushed boundary. Its closed source-path array is exactly:

- `analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py`;
- `analysis_scripts/noncombat_cross_fitted_hierarchical_learning_runtime.py`;
- `analysis_scripts/verify_noncombat_cross_fitted_hierarchical_learning_experiment.py`;
- `analysis_scripts/noncombat_cross_fitted_hierarchical_learning_seed_inventory.py`; and
- `openspec/specs/noncombat-cross-fitted-hierarchical-learning-successor/spec.md`.

Its closed artifact-file array is exactly:

- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_registration.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_registration_review.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_request.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_request_review.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_standing_delegation_20260808.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_delegated_approval.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_delegated_approval_review.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_authorization.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_authorization_review.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_execution_preflight.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_postmortem.json`;
- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2_postmortem.md`; and
- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r5_closeout.json`.

Its closed artifact-root array is exactly:

- `reports/noncombat_cross_fitted_hierarchical_learning_successor_20260808_r2`;
- `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r5`; and
- `reports/noncombat_cross_fitted_empirical_successor_readiness_attempts/ffd9acc444258483d172529eccfe8ccb05c9bb9b`.

The manifest binds exact source hashes, canonical directory-inventory digests,
the two closed arrays, the pre-implementation tree, and its own digest. Source
qualification reobserves it after implementation and rejects any changed,
missing, extra, reordered, or newly imported consumed identity. This is a
preservation guard, not permission to reinterpret those bytes as fresh evidence.

Alternative: parameterize the consumed runner. Rejected because it changes or
couples a consumed source identity. Alternative: copy the entire prior runner.
Rejected because it would preserve unnecessary shared-policy and historical
execution complexity.

### Initialize matched candidate and control policies from one base state

With model seed `0`, construct one CPU float32
`StateConditionedCandidateRanker(HASH_DIM, DEFAULT_HIDDEN_DIM)`. Copy its exact
state dict into five storage-disjoint rankers:

- `candidate.card_policy.family_head`;
- `candidate.card_policy.conditional_ranker`;
- `candidate.frozen_noncard_ranker`;
- `control.shared_card_ranker`; and
- `control.frozen_noncard_ranker`.

Both arms begin from one canonical paired bootstrap. Candidate training updates
only its first two rankers. Control training uses its one shared card ranker to
produce both family logits over the same canonical mean family features and
conditional logits over candidates, so family and conditional components share
parameters only in the control. Both non-card rankers remain
`requires_grad=false`, are excluded from optimizers, and must remain
byte-identical to base and each other in every checkpoint. Thus all initial
function bytes, feature aggregation, objectives, and non-card behavior match;
the primary intervention is card-head parameter sharing.

Each arm samples card rewards family first and then candidate within family
with its own identically seeded checkpointed card generator. Each arm also has
an identically seeded separate non-card generator, so a card-family draw cannot
advance its non-card RNG stream. Frozen evaluation uses unique two-stage greedy
selection for card rewards and unique raw-score greedy selection for non-card
decisions. Any maximum tie fails closed; lexical or candidate order is never a
tie breaker.

Alternative: compare the candidate only with its untrained dual-head bootstrap.
Rejected because that tests whether training changed a new policy but does not
directly test the shared-parameter explanation. Alternative: evaluate against a
consumed checkpoint. Rejected because the old checkpoint is consumed evidence
and combines different architecture, cohort, and behavior.

### Train only the two card-reward heads with a four-component objective

Each arm update contains exactly 64 complete trajectories from the same ordered
training-seed slice. Separately for each arm, reuse the reviewed
four-fold, trajectory-disjoint 128-dimensional ridge baseline: 16 held-out
trajectories per fold, 48 fit trajectories, ridge coefficient `0.001`, CPU
float64 canonical arithmetic, clipped prediction range `[0, 3]`, and exact
unscaled advantage `return_to_go - clipped_held_out_prediction`. Formal return
uses the unchanged undiscounted reward contract. No post-baseline centering,
normalization, clipping, or learned scale is allowed.

For `M` card-reward decisions in a valid chunk, the exact components are:

```
card_reward_family_policy =
    -sum(selected_family_log_probability * advantage) / M
card_reward_conditional_policy =
    -sum(selected_conditional_log_probability * advantage) / M
family_entropy_regularizer = -0.01 * mean(family_entropy)
conditional_entropy_regularizer =
    -0.01 * mean(mean(per_family_conditional_entropies))
```

The full loss is their ordered sum with unit policy coefficients. A chunk with
no valid card reward is a terminal algorithm failure before an optimizer step.
The conditional entropy gives every explicit family equal weight within one
decision. Expected conditional entropy and joint entropy are retained as
diagnostics but excluded from loss because their family-probability weighting
would deliberately create cross-head entropy gradients and obscure the tested
separation.

Use one CPU `torch.optim.Adam` per arm: candidate Adam over its two card heads
and control Adam over its shared card ranker. Both use learning rate `0.001`,
betas `(0.9, 0.999)`, epsilon `1e-8`, zero weight decay, no AMSGrad, and no
alternate parameter groups. Separately per arm, independently differentiate
the four named components and separately supplied full loss, prove ordered
gradient reconstruction and the registered candidate-versus-control ownership,
apply one arm-local global norm ceiling `1.0`, install the resulting CPU float32
gradient, and retain the exact Adam transition for independent replay. No
coefficient, optimizer, clipping, or architecture term is caller-overridable.

Alternative: keep expected conditional entropy for continuity. Rejected because
the architecture contract proves it is cross-head. Alternative: add a learned
critic. Rejected because the existing cross-fitted baseline already isolates
the current architecture question with fewer interventions.

### Use a bounded fresh training schedule with an exact early collapse stop

After clean reviewed source publication, a separately authorized source-only
`build-inventory` operation may select `512` fresh unique paired training seeds
plus disjoint `128` canary and `512` holdout seeds by one canonical
ascending algorithm over a bound Git-tree exclusion inventory. Exclude every
historical used, reserved, diagnostic, canary, holdout, training, evaluation,
and failed-access seed, including previously untouched but reserved cohorts.
The inventory authorization enables only registered repository evidence reads,
seed discovery, and cohort materialization; native loading, environment seed
access, model loading, fitting, training, and evaluation remain false. Import,
request rendering, and pre-build request/authorization validation never discover
or select seeds. After a successful build, a distinct `verify-inventory`
operation under the same exact inventory authorization may read the materialized
inventory and the registered historical sources to reconstruct provenance,
exclusions, and selected values. It cannot select, replace, or materialize a
cohort and cannot import native, model, or environment runtime.

Training may execute at most 512 registered pairs in the same arm order: at
most eight paired chunks, 1,024 total training episode accesses, and at most
eight updates per arm (16 training optimizer steps total). If no early-collapse gate
fires, it must execute exactly all 512 pairs and eight updates per arm. There is
no epoch replay, checkpoint selection, or extension.

After each complete paired checkpoint, inspect the candidate's trailing four chunks. If they
contain at least 64 valid multi-family card rewards and every unique greedy
family is the same identity, publish a valid negative training-collapse verdict
before another seed, canary, or holdout access. Entropy, floor, victory,
baseline fit, control saturation, gradient cosine, and sampled family balance
do not stop or extend training.

The 512-pair scale matches the eight-chunk boundary where persistent greedy
concentration was established, while the matched control makes the new evidence
a direct architecture comparison rather than an extension of consumed data.
Alternative: repeat 1,024 seeds for four passes. Rejected because it spends
holdout-scale resources before establishing that disjoint heads differ from a
matched shared-head learner. Alternative: tune after an early collapse.
Rejected because that would consume the identity's evidentiary value.

### Make the 128-pair canary structural and protect the 512-pair holdout

Only after the exact `training_completed_without_family_saturation` verdict
proves 512 pairs, eight complete chunks, eight updates per arm, and no collapse
or failure may the system freeze and bind a new candidate checkpoint, trained
control checkpoint, candidate/control source manifests, candidate/control
configs, seed inventory, source commit, and exact candidate-disabled production
target. A collapse/failure checkpoint is evidence only and is ineligible for a
seal or canary. No post-training update is permitted.

One separately authorized canary uses 128 fresh paired seeds. Each seed runs
the candidate twice and the control twice; each arm's second execution must
reproduce its first decision and terminal payload exactly. Before either replay
environment is constructed, the first candidate and control outputs are
published to write-once, seed-ordered, hash-chained output commitments bound to
the sealed arm source/checkpoint/config hashes. Replay is judged only against
those immutable commitments; a first output cannot be replaced after replay.
Thus the canary
consumes at most 512 episodes but remains exactly 128 candidate-control pairs.
Candidate-arm card-reward evidence must satisfy all fixed architecture entry
gates:

- every counted decision has at least two explicit family identities;
- the valid multi-family selected-family denominator is at least 64 and its
  maximum selected-family rate is at most `0.95`;
- the unique-greedy-family denominator is at least 64 and its maximum family
  rate is at most `0.95`;
- every action is legal, every retained identity and probability recomputes,
  and all required outputs are finite;
- one cloned, canonical eligible decision performs the exact registered
  family-owned-only shadow Adam algorithm.

For the shadow gate, choose the first eligible candidate-arm decision in exact
`(seed, decision_index, decision_id)` order. Eligibility means a valid
multi-family card reward with finite terms and one selected legal action. Clone
the sealed candidate model and exact candidate Adam state, zero gradients with
`set_to_none=true`, and use the synthetic family-only loss
`-selected_family_log_probability - 0.01 * family_entropy`; its advantage is
fixed to unit one and it uses no conditional or cross-head term. Differentiate
in canonical candidate parameter order, apply the registered global norm clip
`1.0`, and replay exactly one Adam step with the candidate optimizer controls.
The gate requires a finite nonzero family gradient, at least one changed family
parameter, exact unchanged conditional parameter and Adam-state bytes, exact
unchanged conditional logits/probabilities/selected term at the same decision,
and independent replay of the changed family state. The shadow clone never
mutates either frozen arm or an environment. Canary floor and victory
differences are descriptive and are not gates. Any canary failure keeps the
candidate disabled, publishes a terminal negative result, and leaves all 512
holdout seeds unaccessed. Passing every canary gate only makes a separate exact
holdout request eligible.

The holdout runs candidate and control once on each of 512 untouched paired
seeds with both checkpoints/configs frozen. It reapplies legality, identity,
finite-output, and candidate concentration gates. The endpoint is the existing
formal-reward `floor_progress` channel: in ascending registered seed order, each
pair value is candidate `floor_progress` minus control `floor_progress`. Use a
fresh standard-library `random.Random(0)` and exactly 10,000 resamples; for each
resample, draw 512 indices with replacement by 512 consecutive `randrange(512)`
calls and store their arithmetic mean. Sort the means ascending and compute the
`0.025` and `0.975` quantiles by linear interpolation at position
`(10000 - 1) * p` between `floor(position)` and `ceil(position)`. A floor signal
requires the resulting lower endpoint to be strictly greater than zero.

Classify complete holdout evidence as:

- `victory_and_floor_signal` only when candidate victories are strictly greater
  than control victories and the paired-floor lower bound is greater than zero;
- `floor_only_signal` only when candidate and control victories are equal and
  the paired-floor lower bound is greater than zero;
- `inconclusive_signal` only when candidate victories are strictly greater and
  the paired-floor lower bound is not greater than zero, or candidate victories
  are strictly fewer and the paired-floor lower bound is greater than zero; or
- `no_learning_signal` for the remaining two cells: equal victories without a
  floor signal, or fewer candidate victories without a floor signal.

These predicates are evaluated in the stated order but are pairwise disjoint;
the verifier also reconstructs the full `victory comparison x floor signal`
truth table before accepting one class.

Only `victory_and_floor_signal` satisfies this experiment's preregistered
policy-quality evidence threshold. It still grants no loading, gameplay,
qualification, or promotion authority.

### Separate registration and authorization at every empirical boundary

Source implementation, seed inventory/registration, training request and
authorization, post-training candidate/control seal, canary request and
authorization, and holdout request and authorization are separate tracked and
pushed boundaries. The standard-library producer and independent verifier
reconstruct every canonical digest independently before the next boundary.

An exact inventory, training, canary, or holdout request may use a canonical delegated-
approval resolution only when a recorded solo-maintainer grant explicitly
covers this repository, request class, fixed exclusions, and revocation rule,
and has not been revoked. The resolution binds the exact reviewed request digest
and therefore its resource bounds, execution authority, and false downstream
authorities; it is not represented as verbatim human text. Proposal approval,
agent review, or an unbound permission cannot authorize execution.

The delegation manifest uses the existing canonical standing-delegation schema
and binds an external-human grant that predates and is outside the successor
request: verbatim grant text, grant timestamp, message/task IDs, source kind,
repository/request-class scope, exclusions, revocation rule, and self-digest.
Neither this change nor a request may create or modify its grant or retrofit
generated request terms into those immutable human-grant bytes.
Approval publication and every inventory, training, canary, or holdout launch
require a fresh authoritative current-conversation revocation observation with
checked-at time and latest observed human-message watermark. If the controller
cannot inspect that conversation state, or if a later explicit revocation is
observed, delegated approval is invalid. Human provenance and revocation remain
a procedural trust boundary; the verifier proves canonical binding, not human
identity.

Authorization publication uses one source-only chain validator over the exact
request, original request-review bytes, approval record, and authorization. This
closes the publication boundary before launch-time validation composes the later
runner observation and command envelope.

As an alternative to delegation, an exact external-human approval is valid only
after the exact request and its independent review are tracked and pushed. Its
canonical record binds the request digest, verbatim approval text, timestamp,
message/task IDs, source kind `external-human`, repository and request class,
requested scope, ceilings, exclusions, every false downstream authority, and a
self-digest. The approval must postdate and unambiguously approve that one
request; neither the producer nor verifier may generate or reinterpret it. It is
subject to the same fresh approval-time and launch-time current-conversation
revocation observations as delegated approval. Human identity and message truth
remain the same procedural trust boundary.

Control import, request render, and pre-build validation commands do not discover
seeds or import Torch/native modules. The separately authorized inventory
builder may read only its registered repository evidence and materialize seed
roles without native or environment access; post-build `verify-inventory` may
reconstruct those bytes but cannot select or materialize. Runtime import occurs only
after pushed-source, tracked-clean, registration, authorization, interpreter,
native bytes/provenance, production isolation, output-root, and lease checks
pass, including a fresh launch-time authority-revocation observation whenever a
delegated or exact external-human approval path is used. Candidate enablement exists only inside the authorized experiment arm;
CommunicationMod config and production checkpoint inventory are never changed.
The complete validated registration is captured once in an immutable private
process-local execution context and reused for journal, resource, checkpoint,
stage, and terminal operations; no per-seed path may rescan or deep-copy the
complete registration/source inventory.

Setup may be repeated before the first seed under the same identity. During
training, one manual same-identity continuation is permitted only from a
complete 64-seed paired checkpoint when no later arm debit exists; an interrupted
partial chunk is terminal and cannot be replayed. No continuation, resume,
retry, replacement, update, or tuning is permitted after canary start.
Lease ownership binds the actual native/runtime child process, not only a shell
wrapper. Monitoring may inspect liveness while that child is alive and may read
or reclaim the lease/output only after the bound process is proven dead.
Dead-owner terminalization keeps two launch observations deliberately separate:
one fresh pushed observation authorizes the terminalization command, while the
original pushed run observation reconstructs the immutable lifecycle context
named by the lease. The terminalizer must independently validate both authority
chains, require the same request, approval, and authorization, keep registration
opaque, and bind the original run-envelope digest before it may publish closure.
A mismatch before closure publication writes no recovery evidence and grants no
training retry.

### Bound resources and publish independently readable evidence

The complete logical execution is CPU-only at ascension 0 and is capped at:

- 1,024 paired training episode accesses and eight training optimizer updates
  per arm;
- 512 canary episode accesses for 128 pairs with exact replay of both arms;
- 1,024 holdout episode accesses for 512 pairs;
- 2,560 total environment episode accesses, 16 total training optimizer steps,
  and at most one separately charged isolated canary shadow optimizer step that
  cannot mutate either arm;
- 500 decisions per episode and 28,800 charged seconds;
- 64 MiB per managed artifact, 256 MiB total stored managed artifacts, and
  512 MiB total canonical uncompressed payload.

Every seed debit is write-ahead journaled. Complete training chunks have
write-once checkpoints; candidate/control sealing and canary/holdout stages have
separate immutable markers. Large rows and vectors use deterministic little-
endian binary payloads and gzip with `mtime=0`; canonical JSON contains bounded
metadata rather than unbounded decision arrays. The independent standard-
library verifier reconstructs source/config/checkpoint identities, seed roles,
access prefixes, fold and advantage arithmetic, loss rows, gradient ownership,
Adam transitions, control reproduction, concentration denominators, bootstrap
classification, rollback observations, and terminal manifests.

Crossing a legality, identity, evidence, byte, time, access, or publication
bound fails closed and preserves the immutable result. Bounds may be lowered
after source-only benchmarks; raising one requires proposal revision and renewed
review before registration.

The seed inventory scans only an explicit registered historical source set and
must exclude the candidate output, staging, sealed, scratch, attempt, and
temporary roots before traversal. It cannot recursively ingest artifacts it is
currently building. Every terminal path, including pre-checkpoint failure,
charges the final elapsed time and reconciles the actual access prefix before
publication.

### Keep rollback and downstream authority narrow

Before registration, rollback removes only additive uncommitted successor
files. After registration but before seed access, rollback cancels the candidate
and preserves the registration. After evidence-bearing start, rollback means:

- preserve every journal, checkpoint, failure witness, and terminal artifact;
- keep candidate enablement false outside the bound experiment;
- restore the experiment-local target binding to the exact registered control
  checkpoint/config and verify the registered production
  CommunicationMod/checkpoint inventories;
- publish no retry, replacement, tuning, loading, qualification, or promotion.

Every rollback-required failure terminal maps to exactly one of the architecture
contract's fixed rollback trigger classes using this precedence and closed
mapping:

- `authority`: grant, revocation, approval, authorization, or stage authority;
- `identity`: source, checkpoint, config, cohort, target, production, child,
  process, or lease identity;
- `legality`: candidate/action legality, schema, finiteness, objective support,
  or a zero-card-reward chunk;
- `preflight`: interpreter, native, isolation, output, dependency, or setup
  failure before the first debit;
- `canary`: registered training-family saturation or any canary gate/failure;
- `holdout`: any holdout gate, access, evaluation, or classification failure;
- `publication`: resource/time/access accounting, partial chunk, journal,
  evidence, byte bound, staging, checkpoint, terminal, or manifest failure not
  already classified above.

The mapping does not extend or rename the fixed trigger tuple. A complete
holdout's four evidence classes are normal closeout outcomes, not rollback
failure triggers; normal closeout still restores the exact control target, keeps
the candidate disabled, and verifies production isolation. Tests cover every
rollback-required failure path and reject an unmapped or multiply classified
failure terminal.

Every artifact distinguishes execution authority from downstream authority.
Training authorization enables only registered native loading, environment
construction, seed access, fitting, training, checkpointing, and publication.
Canary/holdout authorizations enable only their frozen evaluations. Formal RL,
causal, OPE, production model loading, gameplay, CommunicationMod,
qualification, and promotion remain false for every verdict.

## Risks / Trade-offs

- [The copied base initialization may itself prefer one family] -> Train a
  matched shared-head control from the same bytes, require both selected and
  greedy canary concentration gates, and retain a negative result without
  reinitializing.
- [Freezing non-card policy limits achievable wins] -> Accept the limitation;
  isolation is more valuable than attributing a first card-acceptance result to
  simultaneous route/shop changes.
- [Equal family weighting in conditional entropy changes prior objective scale]
  -> Bind it as the deliberate head-local intervention and retain expected/joint
  entropy only as diagnostics.
- [Cross-fitted prediction quality may remain weak] -> Keep all baseline
  diagnostics descriptive and never choose a fallback or normalize residuals.
- [A strict victory-plus-floor threshold may yield another negative result] ->
  Preserve floor-only and inconclusive evidence separately; do not weaken the
  threshold after seeing holdout.
- [The long CPU run may be interrupted] -> Checkpoint every 64 paired seeds
  (128 episode accesses) and
  allow only complete-boundary continuation before canary; never replay an
  ambiguous partial chunk.
- [Control reproduction adds canary cost] -> Cap it at one extra control
  episode per canary seed and use no holdout replay.
- [Evidence volume may exceed prior limits] -> Store bounded deterministic
  binary/gzip payloads, enforce ceilings before publication, and avoid recursive
  ingestion of generated candidate artifacts during seed inventory.
- [The repository test gate is already near its feedback limit] -> Use focused
  tests while implementing and run each configured commit/full gate only at its
  registered boundary without retrying for duration alone.

## Migration Plan

1. Strict-validate, independently review, commit, and push this planning change.
2. From the reviewed pre-implementation tree, publish and push the fixed closed
   preservation manifest before any implementation edit.
3. Add RED synthetic/control tests, then the four isolated source families;
   preserve all consumed files and empirical artifacts byte-for-byte.
4. Run focused tests, import-isolation checks, strict OpenSpec validation, one
   configured commit gate, and independent source/spec/authority review. Commit
   and push the source-only implementation.
5. Render, review, publish, and push the separate source-only inventory request
   and authorization; then build and independently verify one fresh exclusion
   inventory and all-false registration without native loading or environment
   seed access.
6. Render, review, and publish the exact training request plus a matching tracked
   authorization, using a valid standing-delegation resolution or exact external
   approval. Run at most one logical training identity.
7. Independently verify training closure, freeze candidate/control identities,
   then separately request and authorize the at-most-once canary.
8. If and only if canary passes, separately request and authorize the untouched
   at-most-once holdout. Otherwise preserve zero holdout access.
9. Independently verify terminal evidence, publish a bounded postmortem, sync
   and archive the change, and update project direction. Any production
   qualification remains a new proposal.

## Open Questions

- Exact seed values, source commit, native bytes/provenance, output roots, and
  candidate/control checkpoint hashes remain intentionally unresolved until
  their respective clean pushed registration or sealing boundary.
- Source-only benchmarks may lower storage or time ceilings before registration.
  No empirical result may change initialization, coefficient, optimizer,
  cohort, canary, holdout, bootstrap, verdict, or rollback terms inside the same
  identity.
