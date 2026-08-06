## Context

The hierarchical simulator-learning successor is immutable terminal evidence.
It stopped after 512 training episodes and eight optimizer updates because the
last four chunks contained 1,847 multi-family card rewards whose unique
raw-score maximum family was always `take`. Family entropy remained near
`ln(2)`, sampled `take` and `skip` stayed near balanced, and the mean take
margin widened from 0.0165 to 0.0959. Read-only inspection also found that
sampled `take` rows had higher mean normalized return than sampled `skip` rows
in every chunk, but those repeated trajectory associations do not identify a
causal card value or the complete shared-parameter gradient.

The audit must explain exactly what pressure the registered objective applied
at the family-logit boundary, where that pressure is heterogeneous, and what
the evidence cannot establish. It must operate on the tracked 42.6 MB canonical
training-row payload and terminal metadata without opening a new empirical
identity.

## Goals / Non-Goals

**Goals:**

- Bind the exact inactive, verified terminal bundle and additive audit source.
- Reconstruct registered reward-to-go, float32 normalization, and chunk
  objective summaries with standard-library arithmetic.
- Compute direct policy, family-entropy, and expected-conditional-entropy
  pressure on the take family logit.
- Report fixed decision, trajectory, propensity, margin, and seed-cluster
  strata without adaptive slicing.
- Produce one deterministic bounded verdict and canonical source/input-bound
  report.

**Non-Goals:**

- Replaying or accessing any training, canary, holdout, or replacement seed.
- Importing Torch, loading the native adapter or any model, constructing an
  environment, fitting a baseline, or selecting a checkpoint.
- Estimating policy value, a treatment effect, OPE, causal card value, or the
  complete model-parameter gradient.
- Changing reward, return normalization, entropy coefficients, optimizer,
  architecture, deterministic action selection, or experiment gates.
- Authorizing another experiment, gameplay, policy loading, qualification,
  formal RL, or promotion.

## Decisions

### Use one standalone standard-library audit module

Add
`analysis_scripts/audit_hierarchical_card_reward_credit_assignment.py` with no
imports from the runner, runtime, Torch, native adapter, agent, or
CommunicationMod. It may use only Python standard-library APIs, including
`contextlib`, `gzip`, `hashlib`, `json`, `math`, `os`, `pathlib`, `statistics`,
`struct`, `subprocess`, and the platform lock module. Tests must prove import
isolation before and after report construction.

Alternative: extend the terminal verifier. Rejected because verifier acceptance
and analytical interpretation are different trust roles; changing acceptance
logic to carry optional analysis would enlarge the terminal verification
surface.

### Bind bytes before parsing analytical content

The audit first validates the tracked postmortem and terminal manifest, then
hashes every required source artifact and confirms that the output lease is
inactive. It verifies the gzip stored hash and canonical decompressed hash
before JSON parsing. Checkpoint envelopes are hash-bound through the manifest;
the audit does not parse model or optimizer tensors because training rows and
chunk summaries contain all registered analytical fields.

The audit source is not trusted through a self-reported digest alone. Before
analysis, its worktree bytes must match the exact `HEAD` blob at the fixed
source path; the report records the commit, Git blob identity, and SHA-256. The
implementation source and tests are therefore reviewed, committed, and pushed
before the two fresh publication processes. The audit fails if the source is
untracked or differs from `HEAD`.

The sole permitted untracked control file is the existing
`.execution.lease`. It is not analytical evidence and is never added to the
terminal manifest. The audit first acquires the same non-blocking exclusive file
lock used by the accepted verifier, then validates the locked bytes and holds
the lock across terminal snapshotting and analysis. A missing, malformed,
mismatched, or locked lease fails closed; the audit never modifies its bytes.

Alternative: trust the postmortem's copied metrics. Rejected because the audit
must fail if the underlying rows or terminal identity drift.

### Reconstruct the exact registered return arithmetic

Rows remain in registered chunk/seed/decision order. For each episode, scan
rewards backward with discount 1.0 using finite Python binary64 addition, then
cast each completed return once to IEEE float32. Mean is float32 of
`float32(math.fsum(float32(values))) / N`, followed by another float32 cast.
Population variance casts each subtraction, square, fsum, and division to
float32; standard deviation casts the square root to float32. If standard
deviation is greater than `1e-12`, normalization casts the subtraction,
`standard_deviation + float32(1e-8)`, division, and result as the accepted
verifier does; otherwise every normalized return is zero.
Reconstructed loss components must match each chunk summary under the terminal
verifier tolerance.

Alternative: consume the chunk's reported normalized mean and standard
deviation. Rejected because those aggregates cannot independently bind each
decision's advantage or pressure.

### Report direct take-logit update pressure, not a full gradient

For normalized return `A`, take selection indicator `I`, take probability `p`,
family entropy `H_family`, take-family conditional entropy `h_take`, expected
conditional entropy `H_cond`, and total chunk decision count `N`, the negative
gradient of the registered chunk-mean loss with respect to the row-local take
family logit is:

`[A * (I - p) - 0.01 * p * (log(p) + H_family) + 0.01 * p * (h_take - H_cond)] / N`.

The report reconstructs `h_take` from the recorded within-take conditional
probabilities, verifies `H_cond` from every family's conditional entropy and
probability, and separates policy, family-entropy, and expected-conditional-
entropy terms before summing them. Positive combined pressure means the direct
coordinate contribution of gradient descent raises the take family logit. The
factorized family and conditional logits share underlying scorer parameters;
therefore this coordinate derivative is neither the full model-parameter
update nor a causal mechanism by itself.

Alternative: reconstruct model parameter gradients from checkpoints. Rejected
because that requires Torch/runtime loading and would still not remove
trajectory confounding.

### Freeze descriptive strata before implementation

Use only the spec's chunk, effective-floor, card-reward ordinal, take-propensity,
and score-margin bands. Pre-decision effective floor is the cumulative prior
recorded floor-progress reward times 57. Card-reward ordinal is counted within
seed before the current decision. A stratum is supported only with at least 64
rows and at least 16 selections each for take and skip. Every sparse stratum is
retained and labeled; bands are never merged after seeing a result.

The minimum descriptive-evidence gate is fixed: the complete eligible set must
contain at least 64 rows and at least 16 recorded selections each for `take`
and `skip`, and each of the effective-floor, ordinal, take-propensity, and
family-margin dimensions must contain at least one supported band. Chunk rows
remain mandatory alignment checks but do not count as non-chunk heterogeneity
strata. The terminal window is exactly chunks 4 through 7, and its mean
take-family margin "grows" only when each adjacent chunk mean is strictly
larger than its predecessor.

One seed-cluster row reports each seed's eligible count, take/skip counts,
pressure sum, and reward-to-go means. No p-value, confidence interval,
bootstrap, inverse-propensity estimate, or effective policy value is produced.

Alternative: search for the strongest explanatory partition. Rejected because
adaptive partitions would turn a bounded diagnostic into post-hoc threshold
tuning.

### Use a four-way bounded verdict

Input, identity, order, or arithmetic reconstruction failure aborts publication
without analytical metrics or a verdict. For a fully valid reconstruction,
verdict precedence is:

1. `insufficient_overlap_or_evidence` when the fixed minimum descriptive-
   evidence gate is not met.
2. `direct_take_pressure_not_aligned` if any chunk has nonpositive aggregate
   combined pressure or terminal-window mean margin does not grow.
3. `direct_take_pressure_aligned_but_stratum_heterogeneous` if aggregate
   alignment holds but any supported non-chunk fixed stratum has nonpositive
   pressure.
4. `direct_take_pressure_consistently_aligned` otherwise.

The verdict classifies recorded objective alignment only. All downstream
authority remains false regardless of class.

### Publish canonical JSON plus a generated Markdown summary

The JSON report is the source of truth and includes exact input/source
bindings, reconstruction checks, counts, strata, seed-cluster summaries,
verdict, limitations, and all-false authority. The Markdown report is generated
from that validated structure. Two fresh source-only processes must produce
byte-identical outputs.

## Risks / Trade-offs

- [Direct logit pressure omits shared-parameter coupling] -> Name the quantity
  explicitly, keep conditional and full-gradient claims false, and preserve the
  limitation in every verdict.
- [Reward-to-go is trajectory-confounded] -> Publish fixed floor/timing/
  propensity strata and seed clusters, but prohibit causal, OPE, and
  independent-row inference.
- [Post-hoc audit can overfit its questions] -> Freeze all formulas, bands,
  support thresholds, and verdict precedence in this change before coding.
- [Large canonical rows can create memory pressure] -> Hash compressed and
  decompressed bytes first, cap accepted canonical size to the bound artifact,
  parse once, and avoid loading checkpoint tensor JSON.
- [Float reduction can drift from the registered runtime] -> Reuse the fixed
  standard-library float32 semantics, add RED fixtures from the terminal
  verifier repair, and reconcile every chunk objective before analysis.
- [A plausible finding may trigger premature training] -> Keep all authority
  false and require a separate OpenSpec proposal with fresh evidence boundaries.

## Migration Plan

1. Bind the tracked terminal files and publish a source-only preimplementation
   record with all authority false.
2. Add RED arithmetic, pressure, strata, mutation, determinism, and import-
   isolation tests.
3. Implement the additive audit, turn the focused boundary green, then review,
   commit, and push the implementation identity.
4. Run the audit twice in fresh processes, require byte-identical reports, and
   review the bounded interpretation.
5. Publish reports, update project direction, sync the new capability, archive
   this change, run applicable gates, and commit/push only scoped files.

Before the implementation commit, rollback removes only uncommitted additive
audit files. After that commit but before canonical publication, rollback uses
an explicit revert or superseding commit; it never rewrites pushed history.
After publication, never edit the consumed evidence or silently replace the
report; a correction uses a separately named revision with explicit
supersession.

## Open Questions

Whether a later algorithm should introduce a learned value baseline,
within-trajectory centering, different credit horizon, or another objective is
deliberately unresolved. This audit may narrow that proposal question but
cannot select or authorize an intervention.
