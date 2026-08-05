## Context

The consumed state-conditioned experiment completed 64 training chunks and
stopped before holdout because the terminal greedy canary policy selected only
the `take` action family for card rewards. Its retained `training_rows.json`
contains pre-update decision scores and stochastic selections for every chunk;
each checkpoint contains the corresponding post-update model and optimizer
state; terminal diagnostics contain frozen initial and trained canary rows.

The bundle does not retain the initial model tensors, only their SHA-256. It
also cannot supply a counterfactual reward, alternate optimizer, or replay
without violating the consumed-experiment boundary. The audit must therefore
locate and characterize the observed transition while keeping causal claims
strictly out of scope.

## Goals / Non-Goals

**Goals:**

- Validate and identity-bind the exact allowed terminal artifacts before using
  them.
- Reconstruct deterministic per-decision candidate probabilities from recorded
  scores and summarize selection, score, multiplicity, entropy, and outcome
  trajectories by training chunk.
- Align each chunk with its post-update checkpoint and report finite parameter
  movement from checkpoint 2 onward.
- Identify exact first-observed and earliest-persistent saturation boundaries,
  compare training with initial/trained canary diagnostics, and distinguish
  direct observations from bounded interpretations and unresolved causal
  hypotheses.
- Publish canonical JSON plus Markdown derived only from that JSON.

**Non-Goals:**

- Reading empirical holdout rows, replaying any seed, loading native code or
  PyTorch, constructing a simulator, or invoking gameplay or CommunicationMod.
- Training, fitting, ablation, hyperparameter or threshold selection, model or
  checkpoint selection, reward redesign, or policy promotion.
- Recovering the absent initial tensors or claiming that descriptive
  correlation proves a root cause.
- Authorizing a successor experiment or changing formal-RL readiness.

## Decisions

### Use an explicit artifact allowlist

The audit reads only `artifact_manifest.json`, `training_rows.json`,
`diagnostics.json`, `metrics.json`, `final_model.json`, `evaluation.json`, and
contiguous `checkpoints/checkpoint_*.json` files. It verifies bytes and SHA-256
values against the terminal manifest and rejects symlinks, schema drift,
nonterminal or non-canary-stop evidence, checkpoint gaps, and inconsistent
row/chunk coordinates. The evaluation container is accepted only when its
holdout wrapper says `accessed=false` and contains no evaluation object; the
audit consumes only the canary branches. It never opens registration cohorts,
native bindings, seed inventories, or any empirical holdout row. Terminal
diagnostics must independently state that holdout was not accessed and contain
no holdout policy diagnostics.

This is narrower than importing the experiment verifier. The verifier remains
the terminal-bundle authority, while the audit stays standard-library-only and
has no code path capable of constructing experiment runtime objects.

### Analyze action families as well as individual candidates

For every card-reward decision with both `take` and `skip`, the audit preserves
candidate multiplicity, selected kind, greedy kind, best-take minus best-skip
score margin, stable softmax family probability mass, candidate entropy, kind
entropy, and take-family probability excess over its candidate-count share.
This exposes the distinction between entropy over card candidates and diversity
between `take` and `skip`. Other categories receive the same generic
selection/probability summaries as descriptive controls, without inventing
cross-category equivalence.

Recorded scores are treated as the source of truth. Softmax is reconstructed in
the standard library using max subtraction; it is descriptive and is not
represented as bitwise Torch replay.

### Define boundaries without tuning a numeric threshold

The report uses exact predicates rather than a learned or selected cutoff:

- an observed-selection saturation chunk has eligible card decisions and no
  selected non-`take` kind;
- a greedy saturation chunk has eligible card decisions and every best-scored
  candidate belongs to `take` with a strictly positive best-take/skip margin;
- an earliest persistent boundary is the first chunk for which the same exact
  predicate remains true through the final chunk.

The audit also reports the complete series, so a first occurrence is never
misrepresented as persistent behavior. No canary gate is changed or reused as
an analysis tuning target.

### Keep pre-update rows and post-update checkpoints explicit

Chunk `n` decision rows were generated before optimizer update `n + 1`; its
checkpoint is the state after that update. The report records this relationship
and computes model L2 norm plus consecutive checkpoint delta norm. Because the
initial tensors are absent, checkpoint 1 has no parameter delta and the report
must not estimate one. The final model must byte-decode to the same tensor state
as checkpoint 64.

### Grade claims by evidence type

The JSON separates `observations`, `bounded_interpretations`,
`unresolved_hypotheses`, and `prohibited_claims`. Structural candidate-family
multiplicity, reconstructed probability mass, observed selections, exact score
margins, entropy trajectories, outcomes, and parameter deltas are observations.
Their consistency with candidate-space multiplicity or weak action-family
diversity is a bounded interpretation. Reward causality, optimizer causality,
and the effect of any proposed correction remain unresolved without a separately
approved ablation.

### Publish atomically and canonically

The script builds the complete result in memory, serializes canonical JSON, and
derives Markdown from that normalized result. It writes only the two explicit
output paths, refuses paths inside the source bundle, and uses temporary files
plus replacement. It emits no wall-clock timestamp, so identical source bytes
and arguments produce identical outputs.

## Risks / Trade-offs

- **The 126 MB training artifact requires substantial memory** -> Load it once,
  discard no source ordering, avoid duplicate normalized row copies, and keep
  production execution outside the test gate.
- **Standard-library softmax differs slightly from Torch float32** -> Treat it
  as a deterministic reconstruction from published scores, retain raw aggregate
  score margins, and avoid bit-exact replay claims.
- **Stochastic training selections can briefly look saturated by chance** ->
  report probability mass and greedy margins alongside selection counts and
  distinguish first occurrence from persistent suffix.
- **No initial tensor delta is available** -> publish the gap and begin
  consecutive movement at checkpoint 2; never regenerate weights from a seed.
- **Descriptive patterns may invite causal overreach** -> encode claim classes
  in the machine-readable result and keep successor authorization false.

## Migration Plan

1. Add synthetic RED tests for strict inputs, probability/multiplicity
   calculations, saturation boundaries, parameter decoding, and deterministic
   output.
2. Implement the standard-library audit and focused GREEN verification.
3. Run it once against the already tracked terminal bundle and independently
   inspect the report.
4. Run strict OpenSpec validation and the repository commit gate, then sync and
   archive the completed change.

Rollback removes only this additive analysis capability and its reports; the
consumed experiment and its terminal verdict remain unchanged.

## Open Questions

None. Any intervention or causal ablation is intentionally deferred until this
audit is complete and separately reviewed.
