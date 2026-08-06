## Context

The consumed state-conditioned simulator experiment used one flat candidate
softmax, one selected-candidate log probability, and one candidate-entropy
term. It completed `4,096` training episodes and improved paired canary floor,
but its raw-score greedy policy selected `take` for all `1,458` trained
card-reward decisions. The retained trajectory shows persistent greedy `take`
saturation beginning at chunk `2`; the read-only audit separates structural
candidate-count pressure from later score amplification without claiming
intervention causality.

Three additive capabilities now define the intervention without touching the
experiment: action-family distribution, frozen-score counterfactual audit, and
hierarchical objective terms. Candidate `kind` is the validated family;
max-pooled family logits remove equal-score family mass dependence on family
cardinality; and the selected joint log probability is exactly the sum of its
family and conditional terms.

The old experiment, verifier, tests, registration, authorization, checkpoints,
terminal artifacts, and unvisited holdout identities are consumed evidence.
Moving helpers out of those files or making them import a new common module
would change their source binding. The successor therefore needs a new
identity and schemas while reusing only stable low-level public APIs.

This change is source-only planning. It does not load Torch through a control
command, load native code, construct a simulator environment, materialize a
cohort, access a seed, fit a model, or start the game.

## Goals / Non-Goals

**Goals:**

- Isolate one intended learning intervention: hierarchical family/candidate
  sampling and its corresponding factorized policy objective.
- Freeze separate family and expected-conditional entropy terms while retaining
  the previous scalar coefficient as a controlled starting point.
- Preserve raw-score deterministic evaluation and fail closed on ambiguity.
- Detect exact persistent family collapse before spending the full training
  budget, then protect holdout behind a family-aware canary.
- Give the successor its own bounded control plane, runtime, schemas,
  verifier, source identity, cohort identity, and terminal evidence.
- Make pre-start retry, evidence-bearing execution, checkpoint resume, and
  terminal consumption explicit rather than treating every setup failure as an
  empirical attempt.

**Non-Goals:**

- Editing, importing private functions from, rerunning, resuming, tuning, or
  reinterpreting the consumed state-conditioned experiment.
- Changing model architecture, policy input, reward channels, optimizer,
  learning rate, gradient ceiling, return normalization, or production policy.
- Choosing Current, Bottled, SimpleAgent, or any teacher as policy-quality
  truth or training supervision.
- Establishing formal RL readiness, live value, policy quality,
  target-supported outcomes, qualification, loading, promotion, or victory.
- Launching Slay the Spire or CommunicationMod.

## Decisions

### Use three additive successor modules

The implementation will add:

1. `analysis_scripts/noncombat_hierarchical_simulator_learning_experiment.py`
   as the standard-library control plane for contracts, source binding, seed
   inventory, registration, authorization, lease/journal/checkpoint control,
   artifact publication, and CLI commands;
2. `analysis_scripts/noncombat_hierarchical_simulator_learning_runtime.py` for
   Torch model/runtime state, rollout, hierarchical sampling, loss, training,
   diagnostics, and frozen evaluation; and
3. `analysis_scripts/verify_noncombat_hierarchical_simulator_learning_experiment.py`
   as an independent standard-library terminal verifier that imports neither
   the control plane nor the Torch runtime.

Control-only commands must remain importable when Torch and the native adapter
are unavailable. The runtime is imported only after exact authorization,
source/runtime/native/isolation validation, and lease acquisition.

The new runtime directly reuses public state-conditioned ranker/input,
simulator-adapter, formal-reward, action-family distribution, and hierarchical
objective APIs. Generic behavior seen in old private helpers may be ported in
small successor-owned functions with focused tests; private imports and a bulk
copy of the old runner are forbidden. Every imported source is included in the
new implementation binding.

Alternative: refactor the consumed runner into a shared framework. Rejected
because even a behavior-preserving import edit would invalidate its source
identity. Alternative: copy and patch the full runner. Rejected because it
would duplicate more than six thousand tightly coupled lines and obscure the
actual intervention.

### Sample family first, then candidate within family

For aligned score `z_i` and candidate family `g(i)`, reuse the checked-in
distribution:

```
m_g = max(z_i for i in g)
p(g) = softmax(m)_g
p(i | g) = softmax(z within g)_i
p(i) = p(g(i)) * p(i | g(i))
```

At each training decision, one CPU Torch generator samples a family from
sorted family order, then samples a candidate from the original-order members
of that family. Both calls occur in that order, including one-family or
one-candidate cases, and the generator state is checkpointed. The selected
candidate is then passed by stable `action_id` to
`build_hierarchical_policy_terms`; metadata drift or family/candidate mismatch
fails before applying an action.

Two-stage sampling is chosen over one flat multinomial on the joint candidate
probabilities because the experimental intervention is family-first behavior
and its random-consumption semantics must be visible and replayable. Both have
the same marginal candidate probabilities, but they do not have the same RNG
trajectory.

Event and route currently have one family. Their family log probability and
family entropy remain exactly zero, while their conditional sampling,
conditional log probability, and conditional entropy remain active.

### Freeze a split objective with equal initial coefficients

The source contract fixes:

```
family_entropy_coefficient = 0.01
conditional_entropy_coefficient = 0.01
joint_log_probability = family_log_probability + conditional_log_probability
policy_loss = -mean(joint_log_probability * normalized_return)
loss = policy_loss
       - 0.01 * mean(family_entropy)
       - 0.01 * mean(expected_conditional_entropy)
```

The two coefficient fields are independently validated, checkpointed,
reported, and immutable even though both initial values are `0.01`. Equal
values intentionally preserve the old numeric entropy multiplier because
`H_joint = H_family + H_conditional` under the new distribution. They do not
claim equal entropy magnitude or gradient versus the old flat distribution;
the changed factorization and sampling remain the intended intervention. No
joint-entropy term is added a second time.

The runtime keeps CPU float32 ranker scores and the checked-in finite CPU
float64 distribution/objective terms. Gradients must reach the float32 model
parameters and remain finite before and after the unchanged `1.0` norm clip.

Alternative: increase family entropy relative to conditional entropy. Rejected
because the retained audit does not identify a numeric coefficient causal
effect. Any unequal coefficient or later tuning requires a new proposal.

### Preserve the remaining learning controls

The successor retains the existing state-conditioned ranker architecture,
model seed `0`, learning rate `0.001`, Adam betas `(0.9, 0.999)`, epsilon
`1e-8`, zero weight decay, no AMSGrad, discount `1.0`, normalized returns,
gradient ceiling `1.0`, exact API v3 state/candidate projection, candidate
order, and formal scalar reward:

```
2.0 * terminal_victory + bounded_floor_progress
```

The formal reward is computed from the checked-in reward-channel API and is
not a policy-quality claim. Initial model bytes, terminal model bytes,
optimizer state, Python RNG state, Torch action-generator state, exact chunk
coordinate, and cumulative resource use are checkpointed.

### Keep deterministic evaluation score-based and tie-free

Training samples from the hierarchical distribution. Frozen canary and holdout
evaluation select only the unique maximum raw candidate score, equivalently
the maximum family score followed by the maximum score within that family.
Joint-probability argmax is never an evaluation API because the counterfactual
audit shows it changes many card-reward and shop choices.

If the objective contract returns more than one maximum action ID, evaluation
fails closed before applying an action. Input order, lexical order, and family
probability cannot silently break the tie. Every evaluation episode is replayed
once from a fresh environment, and initial/trained policies use identical
registered seeds without updates.

### Add trajectory and canary anti-collapse gates

Each training decision records family membership, sampled family/action,
family and conditional probabilities, all three entropy terms, raw-score
maximum action and family sets, score margins, state effect, chunk, pass, and
legal candidate identity. Chunk summaries report category/family opportunities
and selection rates without treating entropy as success. A tie wholly within
one family has a singleton maximum-family set; a tie across families prevents
that decision from counting as single-family saturation.

After each complete chunk, the control plane evaluates a trailing four-chunk
window. If the raw-score maximum-family set equals the same singleton family
for exactly `100%` of at least `64` multi-family decisions in either
`card_reward` or `shop`, the experiment publishes
`experiment_stopped_during_training_for_family_saturation` before the next
chunk. It does not evaluate canary or holdout. Exact saturation and four
durable chunks are chosen because the consumed run was persistently saturated
from chunk `2`; a weaker probability threshold would introduce unsupported
tuning.

After complete training, trained canary diagnostics must, independently for
`card_reward` and `shop`:

- contain at least `32` raw-score multi-family decisions;
- select at least two distinct raw-score greedy families; and
- keep the largest selected-family rate at or below `0.95`.

The canary also retains exact replay, legality, four-category coverage,
unsupported-rate ceiling `0.10`, state-effect minimum absolute relative-score
change `1e-8`, at least `4` multi-candidate state-effect decisions, nonzero
state-effect rate at least `0.25`, at least one relative-order change, trained
victory noninferiority, and a positive paired-floor lower bound from `10,000`
bootstrap resamples at `95%` confidence with seed `0`. Event and route
one-family decisions are reported but exempt from multi-family requirements.
Any structural, support, state-effect, family, victory, or paired-floor canary
failure stops before holdout and preserves every holdout seed as unaccessed.

### Use fresh cohorts with the previous holdout excluded

Source-only tests use explicit synthetic seeds and environments. After the
implementation commit is clean, reviewed, committed, and pushed, a tracked
standard-library inventory scans one fixed Git tree. It excludes every seed
appearing under a seed-bearing field in historical registrations, artifacts,
diagnostics, reservations, training, canary, evaluation, and holdout records.
It also explicitly binds and excludes prior untouched holdout `71152..71663`.

One deterministic ascending algorithm then selects `1,024` unique train seeds,
`128` canary seeds, and `512` holdout seeds. Training repeats the train cohort
for four fixed passes in the same order. Caller-supplied seeds, alternate
search starts, and runtime overrides are rejected. Exact seed values are not
materialized by this planning change.

### Bound resources and artifacts no higher than the consumed run

The registration fixes `64` episodes per update, `64` maximum optimizer
updates, `4,096` training episodes, `2,560` evaluation/replay episodes,
`6,656` total episodes, `500` decisions per episode, CPU-only execution, and
`28,800` charged seconds. Holdout episodes count against the total even when
never reached. The evaluation ceiling is exactly four executions per seed
(initial plus replay and trained plus replay) across `128 + 512` seeds. Source
implementation benchmarks may lower a bound but may not raise one without
updating and re-reviewing this proposal.

Every completed chunk has one durable checkpoint. Training rows may be stored
as a deterministic compressed artifact, but the manifest must bind both the
canonical uncompressed bytes and stored bytes. Production checkpoint inventory
and CommunicationMod configuration are snapshotted before and after execution
and must remain unchanged.

Logical training state and consumed resources use separate durability rules.
Model, optimizer, Python RNG, Torch generator, completed-chunk coordinates, and
gradients roll back to the latest complete checkpoint when an incomplete chunk
fails. Training/evaluation episode counts and charged seconds never roll back:
each episode is durably debited in a leased `resource_use.json` prefix before
its seed reaches the environment factory, and elapsed time is merged after each
bounded phase. A checkpoint may therefore report more consumed training
episodes than its completed-episode coordinate. Checkpoint publication first
advances the resource prefix, then publishes the checkpoint idempotently. Any
negative or interrupted terminal result reconstructs the model from the latest
complete checkpoint, or from a write-once `bootstrap_runtime.json` published
before the evidence marker when no checkpoint exists, before merging the
durable resource prefix. The bootstrap binds the exact seeded initial model,
optimizer, Python RNG, Torch generator, and zero coordinates so a later process
cannot silently reinitialize a different terminal model. Both control plane and
independent verifier require its frozen canonical runtime digest. The bootstrap
and evidence marker are mandatory members of every terminal inventory. It never
publishes an uncheckpointed in-memory update.

Every nonzero resource prefix requires the same-identity evidence marker. A
crash-left `.resource_use.json.tmp` is reconciled only while holding the output
lease: the control plane may promote only the exact deterministic successor
revision, advancing by the newly debited episode count or by one for a wall-only
advance, or discard an equal or stale prefix. It fails closed on every other
relation, and terminal publication and verification reject every unreconciled
temporary file.
Before restoring any checkpoint state, the control plane also verifies that
every chunk contains the exact registered training-seed slice in order.

### Separate setup retries from evidence-bearing execution

Registration, source-only verification, and pre-start validation are
repeatable and access no native module, environment, or empirical seed. A
native-load or process-isolation failure before the first seed access may
publish a pre-start attempt record and retry under the same immutable
registration and authorization; it is not empirical evidence.

The evidence-bearing logical identity starts with a durable, flushed
write-ahead journal record immediately before the first registered seed is
passed to an environment factory. Pre-seed retry is permitted only when the
control plane and verifier prove that this marker is absent. After that
boundary:

- algorithm, validation, legality, support, or gate failure is terminal;
- source, runtime, native bytes, cohorts, thresholds, coefficients, and limits
  cannot change;
- an infrastructure interruption may resume only the same identity from the
  last complete checkpoint, with the unchanged generator state and controls;
  an incomplete chunk is deterministically replayed as part of that identity;
  and
- no replacement identity, seed, checkpoint selection, or tuning is allowed.

This avoids consuming an experiment merely because setup failed while still
preventing evidence-driven retries. While an execution process is alive,
monitoring is limited to process liveness and does not read the active output
root, avoiding the prior Windows sharing-conflict failure mode.

### Keep verdicts bounded and downstream authority false

A training-collapse or canary stop is a valid negative experiment result. A
complete holdout is classified separately as a victory signal, floor-only
signal, or no learning signal. Positive floor requires the preregistered paired
trained-minus-initial floor confidence interval to have a lower bound greater
than zero while all structural, support, family, state-effect, and victory-
noninferiority gates pass. The same card-reward/shop family thresholds are
reapplied to trained holdout diagnostics. Victory signal additionally requires
more trained than initial holdout victories.

No verdict establishes policy quality, formal RL readiness, target-supported
outcomes, live value, loading, qualification, gameplay, or promotion. Those
downstream authorities remain false in every artifact. The exact execution
authorization enables only the preregistered execution, native-loading,
environment, seed-access, and model-fitting/training fields; it grants none of
the downstream authorities.

## Risks / Trade-offs

- [Equal entropy coefficients may not prevent family collapse] -> Treat the
  hierarchy itself as the intervention, retain the exact early/canary gates,
  and preserve a negative result without coefficient tuning.
- [Max pooling gives sparse family-logit gradients] -> Reuse the tested `amax`
  semantics, retain conditional gradients, and make no quality claim before a
  fresh registered result.
- [Two RNG draws change trajectories beyond the marginal distribution] ->
  Declare the order explicitly, checkpoint the generator, and require exact
  synthetic and checkpoint-resume replay.
- [An exact early stop could prevent later recovery] -> Require four complete
  chunks and at least 64 multi-family decisions; classify the stop narrowly as
  family saturation rather than general algorithm failure.
- [A new control plane duplicates proven lifecycle concepts] -> Keep the old
  evidence files untouched, split control/runtime/verifier, port only required
  semantics, and require independent source/authority review before
  registration.
- [Floor shaping again produces no victory] -> Keep victory separate, report
  floor-only evidence as simulator learning only, and leave formal RL false.
- [The source/test surface becomes another iteration bottleneck] -> Run focused
  successor/dependency tests during implementation and invoke the repository
  commit gate once at the commit boundary, recording its five-minute feedback
  result without rerunning solely for duration.

## Migration Plan

1. Review, strict-validate, commit, and push this proposal without source,
   native, cohort, seed, or execution work.
2. Add RED tests and the three additive successor modules; keep every consumed
   experiment byte unchanged and use only synthetic environments/seeds.
3. Run focused tests, import-isolation checks, strict OpenSpec validation, one
   repository commit gate, and independent code/spec/authority review; commit
   and push the source-only implementation.
4. From that clean pushed commit, build and independently verify the fresh seed
   inventory and immutable all-false registration; commit and push without
   native loading or seed access.
5. Publish a separately reviewed exact authorization bound to the pushed
   registration. Pre-start failures remain source/setup evidence only.
6. Execute at most one evidence-bearing logical identity, using only
   same-identity checkpoint resume after infrastructure interruption. Protect
   holdout behind the training and canary gates.
7. After process exit, independently verify and preserve the terminal bundle,
   publish a bounded postmortem, sync/archive the change, and update project
   direction without granting downstream authority.

Before registration, rollback deletes only uncommitted additive successor
files. After registration, rollback means cancel before seed access or preserve
the immutable evidence-bearing identity; it never means changing a registered
term or rerunning under replacement evidence.

## Open Questions

- The exact fresh seed values and native-module identity remain intentionally
  unresolved until the clean pushed implementation is inventoried. Their
  selection algorithms and upper resource bounds are already fixed here.
- Source-only benchmarks may justify lowering episode or wall-time ceilings.
  Raising a ceiling, changing a coefficient, changing a family definition, or
  changing an anti-collapse threshold requires proposal revision and renewed
  review before registration.
