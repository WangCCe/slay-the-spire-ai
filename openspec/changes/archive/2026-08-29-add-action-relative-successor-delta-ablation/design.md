## Context

The completed real-context-weighted action-relative fit aligned the simulator
rows to the bound real replay distribution but still failed broadly on fresh
evaluation. It selected 2,004 interventions, including 481 severe harms, and
its weighted mean selected advantage was `-0.00194955`. A read-only postmortem
found severe harms across floors, HP bands, evidence margins, and card and
potion families. Even evidence margin at least 6 reached only `0.458`
precision. Current-state context, action identity, and fixed item semantics do
not expose what each proposed first action causes.

The existing native corpus runner already clones a source environment and
rolls out every supported first action against a canonical guard. It computes
the first transition's before/after snapshots and reward but currently retains
only discounted branch return and terminal status. This change extends that
development-only evidence path without changing production r16, the runtime
policy, the action space, or CommunicationMod.

The bound native module is
`.sts_lightspeed_combat_guard_advantage_20260828_r1_build/sts_lightspeed_combat_adapter.cp310-win_amd64.pyd`
with SHA-256
`195678b7fc6bf69815f3d2971404afb8ce72fb666700edf4203383429caf1009`.
The simulator-only r16 parent has SHA-256
`ce2ae34f82b3f457fb35e87d429c397204c42d0f742d3ac8952d91b69119b83b`.
The items export has SHA-256
`e23784ea8ed3092e3bfa9918240e162a9cbcb837badfb53c612eb0d83cc811dc`.

## Goals / Non-Goals

**Goals:**

- Collect an immutable paired corpus that preserves source-state identity,
  paired continuation returns, and the first transition caused by every guard
  and candidate branch.
- Compare one current-state control with one successor-delta candidate on the
  same rows, context weights, labels, optimizer, updates, sampling plans,
  calibration rule, and fresh evaluation.
- Determine whether action-relative successor information produces a material
  safety and value signal before any policy execution is considered.
- Preserve explicit source, seed, fit/calibration/fresh, native-module, and
  development-only authority boundaries.

**Non-Goals:**

- Tuning evidence thresholds, item vetoes, reward coefficients, labels,
  optimizer settings, architecture width, update count, seed ranges, or gates
  after observing results.
- Importing arbitrary real states into LightSTS, claiming exact simulator
  equivalence, or changing native combat mechanics.
- Starting Slay the Spire or CommunicationMod, online training, loading or
  writing the production checkpoint, qualification, promotion, or deployment.
- Optimizing the full test gate inside this change. Gate performance is a
  separate maintenance boundary after this experiment closes.

## Decisions

### Collect pair-level first-successor evidence

For each retained source state, the collector executes the canonical guard and
every supported candidate in independent cloned environments. It records the
source mapped tensors once and one pair record per candidate. Each pair stores
guard and candidate action identities, total continuation returns, first-step
immediate rewards, first-step successor mapped tensors when available, and an
explicit first-step disposition.

Terminal first steps use zero-filled mapped tensors only together with an
explicit terminal disposition and terminal outcome. They are never interpreted
as ordinary zero states. Unsupported or excluded first successors remove the
pair and increment a named exclusion count; they do not silently fall back to
the source state.

Alternative: modify `BranchResult` globally and rewrite the existing corpus
format. Rejected because historical corpora and registrations are immutable.
The new runner may reuse pure helpers, but it publishes a new schema and leaves
the old collector contract unchanged.

### Use three disjoint preregistered seed partitions

Fit uses seeds `275000..275767`, calibration uses `275768..276023`, and fresh
evaluation uses `277000..277255`. Every partition uses battle indices
`0,3,6,9,10` and retains at most two source states per initialized profile.
Seed sets must be disjoint, and no fresh tensor or metadata file may be loaded
until both arms and their thresholds are frozen.

The collector first runs a tiny source-only smoke using a fixed subset to prove
schema, deterministic branch identity, terminal encoding, and roundtrip. Smoke
rows are excluded from the formal corpus and cannot select a model or alter the
registered recipe.

Alternative: reuse the previously consumed 10,688-row fresh corpus. Rejected
because it does not contain successor tensors and its policy metrics have
already been observed.

### Reapply the existing context-support contract before fitting

The new source states are evaluated against the same bound r14/r15 real replay
target using the existing exact context cells. Coverage, effective sample size,
maximum-weight concentration, floor coverage, weighted balance, legality,
provenance, and seed isolation retain their current thresholds. Any failed
condition closes the experiment before optimizer construction.

Context weight belongs to the source state. Classification pair weight is the
source weight divided by supported candidate-pair count and then normalized
within class. Ranking weight is the source weight divided by ranking-pair count
and then normalized globally. This prevents states with more legal actions
from receiving extra mass.

Alternative: fit first and report context support descriptively. Rejected
because a representation result outside the real-context support contract
would not answer the deployment-relevant question.

### Compare a current-state control with one successor-delta arm

Both arms reuse the frozen parent encoder and the fixed item-semantic
three-class head width. The control consumes source-state latent plus guard and
candidate item semantics. The successor arm adds only:

- frozen candidate-successor latent minus frozen guard-successor latent;
- candidate immediate reward minus guard immediate reward; and
- candidate and guard disposition/outcome features.

The frozen parent encoder has no gradients and is hash-checked before and after
both fits. Both arms use the same labels, Adam `0.001`, 4,096 updates, 128
samples per class per update, 128 ranking pairs per update, ranking coefficient
`0.5`, random seeds, weighted higher 95th-percentile calibration, and offline
gates. The arms have separate deterministic sample-plan hashes but derive them
from the same row identities and weights.

Alternative: concatenate both full successor latents or add multi-step branch
trajectories. Rejected because the delta is the narrowest action-relative test,
while wider or multi-step representations confound information gain with a
large architecture change.

### Separate hard authority from descriptive representation signal

The successor arm passes only with at least 30 raw interventions, weighted
precision at least `0.65`, weighted mean selected advantage above
`0.18881003558635712`, weighted regret below `3.1811342239379883`, and zero raw
severe, illegal, or forbidden selections. A pass grants only authority to
propose a separately registered fresh matched LightSTS policy gate.

If the successor arm does not hard-pass, it may still report a descriptive
signal when weighted precision improves by at least `0.10`, weighted mean
selected advantage improves by at least `0.10`, and raw severe-harm rate falls
by at least 50% relative to the paired control. That verdict grants no policy,
gameplay, training, qualification, or promotion authority.

Alternative: promote the better arm whenever it beats the control. Rejected
because relative improvement can still leave an unsafe policy.

### Fail closed after metric access

Source-only registrations bind code, native bytes, parent, items, real replay
target, seed partitions, schema, recipe, paths, resource limits, and authority
before formal collection or fitting. Pre-start validation may stop without
consuming an execution. Once fresh policy metrics are accessed, no retry,
threshold change, seed substitution, path substitution, or tuning is allowed
under this change.

A deterministic implementation failure before any fresh policy metric may be
handled only by a new corrective successor that binds a committed failure
report and changes no evidence or recipe field. It is a new execution, not a
retry. No more than one corrective successor is allowed.

## Risks / Trade-offs

- [Risk] First-step successor features may encode simulator artifacts rather
  than real causal effects. -> Treat a pass as authority for a fresh matched
  LightSTS gate only, never as deployment or gameplay evidence.
- [Risk] Zero tensors for terminal states can be confused with valid states.
  -> Require explicit disposition/outcome features and regression tests that
  terminal encoding cannot equal an ordinary successor record.
- [Risk] Pair collection increases native execution and artifact size. -> Cap
  profiles, battle indices, retained states, stored bytes, and wall time in the
  registration; publish exclusion and completeness counts.
- [Risk] The same frozen encoder may not represent successor distinctions well.
  -> Report the descriptive ablation result and stop; a new encoder or
  multi-step representation requires a new change.
- [Risk] A broad implementation could inflate engineering overhead. -> Reuse
  existing mapping, context weighting, fit, and evaluation helpers; run focused
  tests during iteration and exactly one timed full gate at the cohesive source
  boundary.

## Migration Plan

1. Commit and strictly validate this OpenSpec change.
2. Add focused regressions for first-successor capture, disposition encoding,
   pair identity, corpus determinism, split isolation, and paired arm inputs.
3. Implement the development-only collector and ablation runner, then run a
   fixed source-only smoke and focused tests.
4. Commit source-only registrations for the formal corpus and paired fit.
5. Collect the registered corpus, verify support, and stop before fitting if
   support fails.
6. Fit both arms once, freeze thresholds, load fresh evaluation once, publish
   the hard decision and descriptive comparison, and run exactly one timed full
   commit gate.
7. Sync and archive the change, push master, then begin a separate read-only
   full-gate timing audit.

Rollback is non-use of all development-only artifacts. Production r16, live
runtime, CommunicationMod configuration, and existing registered corpora stay
unchanged.

## Open Questions

None. A change to representation beyond the registered one-step delta,
collection cohort, context support contract, fixed fit recipe, or decision
thresholds requires a new OpenSpec change.
