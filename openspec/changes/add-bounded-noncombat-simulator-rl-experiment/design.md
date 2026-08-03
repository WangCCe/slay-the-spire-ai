## Context

The frozen simulator smoke used a 1,024-dimensional hashed candidate view, a
linear `CandidateRanker`, and candidate-masked REINFORCE for 128 training
episodes. It passed legality, isolation, replay, and resource checks and
improved paired holdout floor, but produced no victories and used a reward whose
victory bonus did not strictly dominate complete-episode floor shaping.

The current adapter is API v3 and covers all four target categories with
explicit baseline-controlled non-target behavior and fail-closed event/shop
boundaries. Formal readiness still blocks policy-quality and promotion claims
because the Current baseline study is terminally blocked and live outcome
support is source-incomparable. This design does not change those facts. It
defines a lower-authority simulator experiment that can test learning without
being loadable by Communication Mod or production checkpoint discovery.

## Goals / Non-Goals

**Goals:**

- Run actual non-combat RL at materially larger scale than the smoke while
  retaining one fixed algorithm, model family, reward, and cohort contract.
- Make simulator terminal victory strictly primary over bounded floor shaping.
- Survive process or host interruption through exact, hash-chained,
  deterministic checkpoints without creating a second logical attempt.
- Keep train, canary, and holdout cohorts disjoint; access holdout only after a
  fixed canary gate; publish a terminal negative as readily as a positive.
- Verify artifacts independently without loading native code or replaying
  training.

**Non-Goals:**

- No Current, Bottled, SimpleAgent, live outcome, OPE, HP, gold, or heuristic
  value enters reward.
- No live gameplay, Communication Mod change, production checkpoint, formal-RL
  readiness update, policy-quality claim, causal claim, qualification, or
  promotion.
- No hyperparameter sweep, architecture search, PPO migration, teacher warm
  start, reward tuning, cohort replacement, or post-result retry.
- No modification or reinterpretation of the frozen simulator smoke, Current
  baseline study, outcome studies, or readiness artifacts.

## Decisions

### Reuse the linear candidate ranker and REINFORCE

The experiment uses the existing linear `CandidateRanker`, 1,024 hashed
features, Adam at `0.001`, discount `1.0`, model seed `0`, and candidate-masked
sampling. A new `candidate-masked-reinforce-experiment-v1` loop performs one
update per 64-episode chunk after standardizing return-to-go within that chunk.
Training covers four deterministic passes over 1,024 train seeds, for exactly
4,096 primary training episodes and 64 optimizer updates.

This keeps the smoke's demonstrated learning mechanism and changes only the
scale, current adapter contract, formal reward, and resumability needed for a
long experiment. PPO, actor-critic, a deeper model, and GPU training are
rejected here because they would add independent algorithm and capacity
questions before the scaled smoke hypothesis is tested.

The runner is CPU-only, sets PyTorch threads to one, enables deterministic
algorithms, and refuses CUDA tensors. The simulator dominates runtime; GPU use
would add reproducibility surface without meaningful benefit for a 1,024-weight
linear scorer.

### Introduce an API v3 feature contract without changing live code

Create `noncombat-simulator-policy-features-v2` as a source-bound projection of
validated API v3 snapshots and candidate records. It preserves decision state
and legal candidate identity while excluding seed, outcome, provenance,
baseline history, and terminal labels. Projection, ordering, hashing, and float
encoding are fixed and tested. The frozen v1 projector and smoke remain
unchanged.

Alternative: reuse the v1 label while feeding API v3 records. Rejected because
new event context and current adapter fields would silently change the feature
meaning under an old version name.

### Select strict scalar victory dominance

Each transition receives nonnegative capped floor advancement divided by 57.
A terminal simulator victory adds `2.0`; every other transition adds zero
victory reward. Since complete-episode floor progress is bounded by `1.0`, the
victory weight is strictly greater than all shaping and satisfies the formal
reward contract. Discount remains `1.0`.

Lexicographic policy optimization is rejected for this first experiment because
the existing single-head REINFORCE loop consumes scalar returns. Weight `2.0`
is the smallest simple registered value that proves strict dominance; it is not
tuned after execution.

### Use one exact disjoint cohort and conditional holdout

The registration binds these fixed A0 Ironclad seed ranges, subject to a
source-only inventory proving that no value appears in prior registered
simulator cohorts:

- train: `50000..51023` (1,024 seeds), four passes;
- canary: `51024..51151` (128 seeds);
- holdout: `51152..51663` (512 seeds).

Any prior registered collision blocks the proposal; the runner does not choose
another range. Seed order is ascending within each pass and no outcome-driven
shuffle or replacement occurs.

After training, frozen initialization and trained policy run once on the same
canary. Holdout remains untouched unless both policies are legal and terminal,
all four categories are covered, the registered unsupported rate is at most
10%, trained canary victories are not fewer than initialization, and the 95%
paired bootstrap lower bound for terminal-floor difference is above zero.

If canary passes, initialization and trained policy run once on holdout. The
learning-signal verdict requires trained holdout victories to exceed
initialization and the 95% paired floor-difference lower bound to exceed zero.
Victory counts/rates are always primary in the report. A valid run that misses
either learning gate remains a terminal negative.

### Treat only registered support blockers as conservative episode terminals

Exact adapter support-envelope blockers named in the registration retain the
episode at its last supported floor as a non-victory. They remain in training,
canary, holdout, unsupported-rate, victory, and floor denominators. Unknown
exceptions, illegal actions, duplicate candidates, source mutation, or
non-finite values block the entire experiment. No episode is retried or
replaced.

### Persist canonical hash-chained checkpoints

After every 64-episode optimizer update, write one canonical JSON checkpoint
containing model tensors, Adam tensors and counters, Python and PyTorch random
states, action-generator state, completed seed/pass/chunk coordinates,
accumulated bounded runtime, prior-checkpoint hash, registration hash, and
implementation identity. Tensor bytes use explicit dtype, shape, little-endian
contiguous bytes, and base64 encoding; no pickle or timestamp-bearing archive
format is authoritative.

A resume validates the full chain, exact source/runtime/native identities, the
started journal, single logical execution ID, next coordinate, and output
inventory before constructing an environment. It continues the same attempt
and cumulative 28,800-second wall budget. A second concurrent lease, changed
identity, missing checkpoint, or already terminal journal fails before rollout.

The first two primary chunks are independently replayed from initialization and
must reproduce checkpoint 2 byte-for-byte. Full 4,096-episode duplication is
rejected because it doubles cost without adding a distinct contract beyond the
checkpoint-prefix proof and deterministic source tests.

### Separate implementation, authorization, execution, and verification

Implementation and tests run with fake environments and no native module.
After they pass, a preregistration binds source commit, current API v3 adapter,
physical `sts_lightspeed` source and module, runtime, formal reward artifact,
feature/algorithm constants, cohorts, limits, expected artifacts, and all-false
authority. It is committed and pushed before a separate execution
authorization may set only `experiment_execution=true` for one logical run.

The runner publishes configuration, append-only journal, checkpoints,
trajectory summaries, canary/holdout rows when reached, metrics, model, report,
and manifest atomically under an experiment-specific directory outside live
checkpoint discovery. A standalone verifier recomputes identities, chain,
counts, gates, hashes, and verdict without importing native code or PyTorch.

## Risks / Trade-offs

- [Risk] The linear model may still produce zero victories. -> Mitigation: this
  is the registered hypothesis; publish `experiment_valid_without_learning_signal`
  rather than tune architecture or reward.
- [Risk] API v3 or simulator support blockers consume many episodes. ->
  Mitigation: retain exact registered blockers conservatively and stop before
  holdout if the fixed 10% canary ceiling fails.
- [Risk] Long execution is interrupted. -> Mitigation: canonical checkpoints,
  one logical execution journal, cumulative wall budget, and exact resume
  validation make interruption resumable without replacement.
- [Risk] Checkpoint serialization is subtly nondeterministic. -> Mitigation:
  explicit canonical tensor encoding, byte replay at chunk 2, and independent
  no-native verification.
- [Risk] Simulator gains are mistaken for live policy quality. -> Mitigation:
  separate artifact root and authority fields; formal readiness, Current
  baseline, outcome support, live loading, and promotion remain false for every
  verdict.
- [Trade-off] One fixed large run gives less algorithm insight than a sweep but
  preserves a falsifiable experiment and avoids selection on evaluation data.

## Migration Plan

1. Implement the v2 feature projector, formal reward adapter, chunked runner,
   checkpoint codec, journal, classifier, publisher, and standalone verifier
   with fake-environment regressions only.
2. Pass focused tests, the registered repository commit gate, strict OpenSpec,
   and a source-only review; commit and push implementation.
3. Build the exact preregistration and seed-inventory proof from pushed source;
   verify twice in fresh processes; commit and push it.
4. Create a separate one-shot execution authorization only after preflight
   proves exact identities, absent outputs, and no live/Communication Mod
   process or configuration mutation.
5. Execute or resume one logical experiment, independently verify the terminal
   artifacts, publish the result, update project direction without changing
   formal readiness, then sync and archive the change.

Rollback before execution removes the new source, tests, registration, and
specs. Rollback after a started execution preserves the journal and artifacts
as a terminal or interrupted result and removes only unconsumed integration
surfaces. It never deletes or rewrites prior evidence.

## Open Questions

None. Any algorithm, model, reward, cohort, threshold, support ceiling, or
resource change requires an OpenSpec amendment before execution, not an
operator override.
