## Context

The closed r2 simulator experiment demonstrated a broad paired floor increase
over seeded initialization, but produced zero victories, selected every
observed card reward, and used a linear scorer whose shared state contribution
cancelled from relative candidate scores. The repository now has a source-only
state-conditioned MLP ranker, an exact API v3 separate state/candidate input
boundary, and canonical anti-collapse diagnostics, but no experiment integrates
them.

The final Current comparator attempt is consumed and invalid; SimpleAgent and
Bottled are auxiliary-only. Formal readiness remains blocked by policy-quality
baseline and source-comparable target-supported outcomes. This change answers
only an earlier question: can a state-conditioned policy learn under fixed
simulator controls without repeating r2's deterministic capacity defect or
action-family collapse?

The experiment runs only in Windows production Python on CPU with the bound
native simulator. It must not contact CommunicationMod, load production
checkpoints, or mutate gameplay behavior.

## Goals / Non-Goals

**Goals:**

- Add a new runner without changing the source-bound r2 implementation.
- Integrate exact API v3 separate state/candidate tensors with
  `StateConditionedCandidateRanker`.
- Train and evaluate against a frozen seeded initialization control under the
  existing formal victory-primary reward.
- Make state usage and action-family collapse first-class preregistered gates.
- Preserve deterministic replay, conservative support accounting, fresh
  cohort isolation, bounded execution, resumable checkpoints, atomic
  publication, and independent verification.
- Publish simulator architecture evidence with explicit floor-only and victory
  signal distinctions.

**Non-Goals:**

- Establish a credible policy-quality baseline or formal-RL readiness.
- Reopen Current, r2, any retired qualification, or the blocked outcome study.
- Use SimpleAgent, Bottled, Current, teacher agreement, OPE, or live outcomes in
  policy input, reward, action selection, or pass gates.
- Launch Slay the Spire or CommunicationMod, load a production model, or
  qualify or promote a policy.
- Tune after seeing canary or holdout results.

## Decisions

### Add a successor runner instead of editing r2

Create
`analysis_scripts/noncombat_state_conditioned_simulator_learning_experiment.py`
and a standard-library verifier. The successor may reuse immutable adapter,
reward, canonicalization, bootstrap, and Windows native-load helpers where
their contracts match, but it owns its model runtime, rollout, checkpoint,
diagnostic, gate, and artifact schemas.

This preserves r2's source identity and verifier while avoiding a broad common
engine refactor before the new boundary is proven. Some narrow duplication is
accepted because empirical provenance is more important than reducing lines in
this change.

Alternative: refactor r2 into a generic experiment engine. Rejected because it
would alter historical evidence dependencies and combine migration risk with a
new empirical design.

### Use seeded initialization as an experimental control only

The model seed, architecture, initialization state, optimizer state, and action
generator state are fixed before training. Evaluation compares the frozen
initial state with the frozen terminal state on identical fresh seeds.

The control answers whether the registered update process changed outcomes. It
does not answer whether the initial or trained policy is good. No reference
policy enters a primary or secondary pass gate.

Alternative: replace Current with SimpleAgent or Bottled. Rejected because
their evidence-bounded roles prohibit policy-quality use.

### Preserve state and candidate channels through scoring

Every target decision is validated and projected by
`project_state_conditioned_policy_input`. The ranker receives one state vector
and the complete candidate matrix separately. Candidate masks are represented
only by the validated candidate set; candidates cannot be added, dropped, or
reordered outside the recorded order.

The experiment records canonical scored-decision rows through
`build_policy_diagnostic_row`. Checkpoints bind architecture metadata, feature
metadata, model tensors, optimizer tensors, random generator states, and exact
training coordinates.

### Add bounded exploration and anti-collapse evidence

Training uses CPU candidate-masked REINFORCE with the formal scalar reward,
Adam, normalized returns, a fixed entropy term, and a fixed gradient-norm
ceiling. Every numeric value is frozen in the pushed registration; there is no
runtime override. Evaluation is greedy and update-free.

The entropy term is included because r2's terminal policy saturated to one
card-reward family. It is an algorithm control, not a reward channel. The
gradient ceiling bounds the larger MLP update surface.

Diagnostics summarize, by cohort and category:

- candidate and selected-kind counts and rates;
- single-candidate and multi-candidate decision counts;
- exact single-kind saturation where alternatives were available;
- finite raw score-margin distributions; and
- relative-score changes between actual state and a registered zero-state
  counterfactual using the same candidates and model.

The canary cannot pass when a registered card-reward or shop anti-collapse
gate fails, or when empirical relative scores show no state-conditioned effect.
Route and event categories are reported but are not forced to have multiple
action kinds when their candidate schema exposes only one kind.

Alternative: report collapse only after holdout. Rejected because it would
spend the held-out cohort on an already invalid policy family.

### Keep victory and floor verdicts distinct

The formal reward remains terminal victory weight `2.0` plus bounded
nonnegative floor progress of at most `1.0` per episode. The experiment reports
three valid terminal classes:

- `experiment_valid_with_victory_signal` when every structural, behavior, and
  paired floor gate passes and trained holdout victories exceed initialization;
- `experiment_valid_with_floor_only_signal` when structural, behavior, and
  paired floor gates pass without a victory increase; and
- `experiment_valid_without_learning_signal` for any other structurally valid
  complete holdout result.

A floor-only result establishes only bounded simulator learning evidence. Even
a victory signal does not establish live value, formal readiness, or promotion.

### Freeze cohorts only after source-only implementation

Implementation and focused tests use synthetic environments and explicit test
seeds. They load no native module and materialize no empirical cohort.

After the implementation commit is pushed, a source-only inventory scans
tracked registrations and canonical artifacts, excludes every historical,
consumed, reserved, train, canary, holdout, compatibility, and diagnostic seed,
then applies one fixed ascending search algorithm. The registration binds the
materialized train, canary, and holdout cohorts, all thresholds, runtime and
native identities, resource limits, output inventory, and all-false downstream
authority.

### Preserve a one-attempt Windows lifecycle

Preparation and verification before a started journal are repeatable and may
not import native code, construct an environment, or access an empirical seed.
Execution requires a separately tracked authorization bound to the pushed
registration.

After start, any failure consumes the logical identity. No retry, resume under
a replacement identity, seed replacement, tuning, threshold change, or
in-place repair is allowed. Resumption, if the registration explicitly permits
it, can only continue the same nonterminal logical identity from the last
complete checkpoint and unchanged controls.

While the process is alive, operators and monitors inspect process liveness
only and do not read files under the active output root. Artifacts are inspected
after process exit to avoid Windows atomic-replace sharing conflicts.

## Risks / Trade-offs

- [Simulator floor shaping again dominates without victories] -> Publish a
  distinct floor-only verdict and keep formal/live authority false.
- [Entropy prevents exact collapse but masks poor decisions] -> Retain raw
  selected-kind rates, score margins, victories, floors, and fixed gates; do
  not treat entropy itself as success.
- [Zero-state counterfactual is out of distribution] -> Use it only to prove
  the model's relative logits depend on the state channel, not as a quality
  metric.
- [New runner duplicates historical logic] -> Reuse only small immutable
  helpers, bind every imported source hash, and keep schemas/versioning local.
- [MLP training exceeds the resource bound] -> Freeze episode, wall-time, and
  checkpoint limits before execution and fail closed at the exact coordinate.
- [A successful simulator result creates pressure for live use] -> Every
  artifact repeats the independent baseline-quality and outcome-support
  blockers and grants no model-loading or promotion authority.

## Migration Plan

1. Commit this audit and OpenSpec planning change without native loading.
2. Add source-only runner/verifier regressions and preserve all historical
   source and artifacts byte-for-byte.
3. Run focused tests, the repository commit gate, strict OpenSpec validation,
   and independent source/authority review; commit and push implementation.
4. Generate and review a fresh deterministic seed inventory and all-false
   registration; commit and push without starting execution.
5. Publish a tracked exact authorization under the user's standing approval,
   execute one logical experiment, verify after process exit, and preserve the
   terminal result.
6. Refresh simulator-learning interpretation and project direction without
   changing formal readiness or the outcome-study gate.

Rollback is deletion of uncommitted additive source before registration. Once
a registration is pushed it is immutable; once execution starts, rollback
means stop, preserve evidence, and close the logical identity rather than
rerun.

## Open Questions

- Exact fresh seed ranges, episode counts, entropy coefficient, gradient
  ceiling, anti-collapse thresholds, and wall-time limits remain to be frozen
  during source-only registration design after implementation benchmarks.
- Whether a later floor-only result justifies another algorithm proposal is a
  post-closeout decision and is not answered by this change.
