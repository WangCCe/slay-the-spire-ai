## Context

The completed simulator-training smoke proved a deterministic training and
artifact pipeline, but its final ranker averaged floor 14.5625 on the registered
policy-validity cohort while native SimpleAgent averaged 19.96875. The paired
trained-minus-baseline interval `[-7.875, -2.921875]` rules out using the smoke
as a credible starting policy for formal RL.

Adapter API v2 can query the native SimpleAgent target action and advance a
baseline-following trajectory without mutating query inputs. That API is
sufficient to collect supervised route, shop, event, and card-reward examples,
but it deliberately fails closed after a counterfactual target action. The
design must therefore distinguish teacher-state imitation from independent
candidate-policy rollouts and use the latter as the primary competence check.

## Goals / Non-Goals

**Goals:**

- Prove whether the simulator feature/action representation can learn a useful
  approximation of native SimpleAgent under one bounded supervised protocol.
- Preserve full legal candidate sets and train a scorer, not a table of forced
  teacher actions.
- Freeze train, validation, and final test cohorts before native collection;
  keep every previously observed fit, smoke, and policy-validity seed excluded.
- Gate final test access on deterministic structural checks and a registered
  validation threshold, then publish one final execution and one exact replay.
- Produce enough evidence to decide whether a later bounded formal-RL proposal
  has a credible baseline starting floor.

**Non-Goals:**

- No formal RL, reward optimization, DAgger, online learning, live gameplay,
  CommunicationMod use, checkpoint discovery, or production model loading.
- No claim that SimpleAgent is optimal, live-compatible, reward truth, or a
  permanent target.
- No Current or Bottled training labels until their simulator state/action
  bridges are separately validated.
- No hyperparameter search, post-test tuning, alternate cohort, or retry under
  this change.

## Decisions

### 1. Keep the runner separate from historical studies

Add `analysis_scripts/noncombat_simulator_baseline_warm_start.py`. It may import
stable feature, canonicalization, bootstrap, native-loading, and artifact
helpers from the smoke and policy-validity modules, but it will not rewrite
their registrations, models, artifacts, or verdicts. This keeps the new
supervised objective from changing the meaning of historical evidence.

An all-new script is preferred over adding a mode to the smoke runner because
the smoke uses simulator return and REINFORCE, while this change uses teacher
actions and candidate-masked cross entropy. A shared command would make reward
and authority boundaries harder to audit.

### 2. Freeze one three-cohort study before collection

The registration binds exact adapter/simulator/build/runtime identities,
implementation hashes, feature and model versions, one model seed, one fixed
optimizer schedule, train/validation/test seeds, all prior excluded seeds,
bootstrap settings, thresholds, and resource limits. All three cohorts are
unique and mutually disjoint.

The v1 study has exactly one model configuration. Validation is a stop gate,
not a selection set: failure publishes a reproducible validation result and
leaves final test seeds untouched. Passing validation freezes the model before
the final test. No value may be changed after any registered seed is observed.

Pure fixtures and the already observed adapter fit seeds may establish only
schema, legality, determinism, and implementation fit. They cannot contribute
to quality metrics or choose study values.

### 3. Collect baseline-following demonstrations with complete candidates

For each registered demonstration seed, reset an independent environment and
follow native SimpleAgent at every target decision. Each canonical row records:

- cohort, seed, decision index, category, and adapter provenance;
- canonical source snapshot and the complete ordered candidate set;
- target action id returned by the native query and proof it maps exactly once;
- policy-view bytes and hashes for every candidate; and
- successor/terminal summary and sequence hashes.

Repeated collection must be byte-identical. Query mutation, zero or duplicate
target matches, rejected actions, unsupported terminal outcomes, missing
category coverage, or resource exhaustion blocks the study.

Storing complete candidates rather than only the teacher action keeps negative
examples auditable and lets the learned scorer retain the original action
space. The teacher action never becomes a reward field.

### 4. Train one deterministic candidate-masked MLP

Use the existing leakage-controlled `noncombat-simulator-policy-features-v1`
projection and a new `candidate-ranker-mlp-v1`: one fixed-width ReLU hidden
layer followed by one scalar score per candidate, with no dropout or recurrent
state. Initialize on CPU from the registered seed.

At each decision, softmax only over the complete reported candidates and apply
cross entropy to the native target index. Aggregate per-decision losses into
equal-weight category means before averaging categories so frequent categories
cannot silently erase shop, event, or route supervision. Use one fixed Adam
schedule, deterministic row ordering, finite-gradient checks, and hard epoch,
decision, and wall-time bounds.

The MLP is preferred over the smoke's linear scorer because SimpleAgent contains
state-dependent thresholds and interactions that a purely additive scorer may
not represent. The model remains intentionally small; this stage tests a
usable warm start, not model scaling.

### 5. Separate teacher fit from rollout competence

Validation and final test each compute two evidence classes:

1. Teacher-state fit: overall and per-category exact action agreement, macro
   category agreement, cross entropy, and candidate legality on independent
   baseline-following demonstrations.
2. Rollout competence: paired terminal floors and outcomes from independent
   frozen-model and native-SimpleAgent environments on the same seeds.

The registration binds a minimum teacher-fit threshold and a paired floor
non-inferiority contract before collection. The primary final quality gate is
the registered lower confidence bound for candidate-minus-SimpleAgent terminal
floor together with its maximum tolerated mean deficit. Teacher agreement is a
required representation check but cannot override failed rollout competence.
Victory counts remain descriptive because the previous cohort produced no
victories.

Exact numeric margins and cohort sizes are frozen only after the implementation
fit report exposes row counts, category balance, runtime, and deterministic
behavior without touching registered study seeds. This is a preregistration
decision, not a result-dependent adjustment.

### 6. Reproduce the whole bounded execution

One primary execution collects demonstrations, trains, applies the validation
stop gate, and conditionally evaluates final test. One identical replay starts
from a fresh process-equivalent state and must reproduce canonical datasets,
model tensors, action sequences, metrics, report, and manifest. Measured timing
is written only to a noncanonical journal.

Canonical outputs are atomically published under an explicit report directory
outside checkpoint/model discovery. The manifest closes every managed file and
sets formal RL, simulator RL training, live gameplay, live loading, live study,
OPE, qualification, and promotion authority false.

## Risks / Trade-offs

- **Baseline-state covariate shift** -> Teacher fit may look strong while the
  candidate drifts during rollout. Keep paired independent rollout floor as the
  primary gate and report first divergence diagnostics.
- **SimpleAgent limitations are inherited** -> Treat labels as temporary
  auxiliary supervision and preserve all actions; the goal is a competence
  floor, not policy optimality.
- **Category imbalance distorts training** -> Require all four categories and
  use category-balanced loss plus per-category metrics.
- **A non-inferiority margin can be too permissive** -> Bind both confidence
  bound and mean-deficit limits with written rationale before collection; do
  not revise them after observation.
- **External native identity is dirty or drifts** -> Reuse physical-source and
  module hashing, bind the accepted dirty identity explicitly, and fail closed
  before registered seeds.
- **Deterministic replay doubles native cost** -> Keep fixed finite cohorts and
  wall-time limits; do not replace replay with a weaker spot check.

## Migration Plan

1. Implement and test pure registration, dataset, loss, metric, and artifact
   contracts using synthetic fixtures.
2. Add opt-in native collection tests and a bounded implementation-fit report
   using only already observed fit seeds.
3. Review the fit evidence, choose and commit exact study cohorts, thresholds,
   and limits without collecting them.
4. Run repository gates and isolation checks, then execute the registration at
   most once plus its identical replay.
5. Publish the positive, negative, or blocked result without tuning.

Rollback removes only the new offline runner, tests, registration, reports,
docs, and optional build output. No live configuration, checkpoint, prior
artifact, external simulator source, or production agent path changes.

## Open Questions

- Exact train/validation/test counts and numerical action-fit/non-inferiority
  margins remain a fit-review decision and MUST be committed before any study
  seed is collected.
- The final registration must decide whether the replay shares one process or
  uses two explicit subprocess invocations; canonical expectations are the same,
  but fresh subprocesses provide stronger runtime-isolation evidence.
