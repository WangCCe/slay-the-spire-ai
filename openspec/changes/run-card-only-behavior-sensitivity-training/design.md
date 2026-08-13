## Context

The r7 pilot proved that the candidate optimizer, cross-fitted baseline, and
checkpoint ownership path work. Four updates moved model parameters but changed
only one fixed-probe action and left the 64-seed aggregate outcome unchanged.
Each training chunk nevertheless reran a native control arm whose trajectory
was not used by the candidate baseline or optimizer.

The continuation must use only already-consumed development seeds, start from
the exact r7 `checkpoint_004`, preserve its Adam moments, and remain outside
production discovery. The native Windows module must load before torch because
the reverse order can make the DLL fail to resolve.

## Goals / Non-Goals

**Goals:**

- Convert the paired training chunk into a candidate-only collection without
  changing the candidate reward, cross-fitting, or optimizer objective.
- Execute 16 additional candidate steps within an eight-hour wall-clock bound.
- Measure whether the added steps produce stable greedy behavior changes and
  non-inferior supported development outcomes.
- Make complete-boundary resume practical after a host restart.

**Non-Goals:**

- No new seeds, protected cohort access, fresh evaluation, hyperparameter
  search, reward change, formal policy-quality claim, live gameplay, or
  production checkpoint loading.
- No attempt to improve route, shop, or event policy; native SimpleAgent remains
  responsible for every non-card action.
- No repeated run after a terminal result under this change.

## Decisions

### Train from candidate arm rollouts only

The empirical-successor runtime will accept a sequence of complete candidate
`ArmEpisodeRollout` objects anywhere the candidate-only cross-fitted update
currently accepts paired objects. A dedicated wrapper will run the candidate
card policy and native SimpleAgent for all non-card categories. It will not
construct or query a control environment during training.

This preserves the exact candidate decision sequence, return-to-go, four-fold
ridge baseline, card objective, and Adam update while reducing each training
chunk from 128 to 64 environment accesses. Keeping paired training was rejected
because the control trajectory is not an input to any candidate gradient.

### Continue from r7 instead of repeating its first four steps

The runner binds the committed r7 registration and `checkpoint_004` bytes,
restores the candidate model and Adam moments, and projects the same 175
validation rows for the fixed probe. It records the entry model hash and entry
predictions before any environment access. Chunk indices continue from 4
through 19; no step is replayed merely to reconstruct history.

Starting again from the warm checkpoint was rejected because it would spend
roughly one quarter of the new training budget reproducing already-observed
updates.

### Use complete-boundary resumability

Every completed chunk publishes a canonical checkpoint, collection summary,
and behavior summary before the next chunk. A resume journal binds the source
commit, registration, last complete checkpoint, and next chunk index.

If a process or host stops during a chunk, the runner may restore the complete
chunk-entry checkpoint and rerun that same registered 64-seed cohort. It may not
reuse partial gradients, skip or replace seeds, change the schedule, or alter a
parameter. This replaces the earlier blanket no-retry rule with deterministic
checkpoint-level recovery.

### Separate training from the terminal control comparison

After 16 successful updates, the runner collects one frozen native-control arm
and one frozen candidate arm for each of the 64 consumed seeds, then joins them
by seed. The corrected bounded Courier pair censoring contract applies to the
joined comparison. This spends 128 evaluation accesses once instead of 1,024
control accesses across training.

The proposal gate requires supported candidate mean floor and victories to be
non-inferior to control, fixed-probe take coverage in 5%-95%, and at least four
exact-action flips relative to the r7 entry checkpoint. Passing only authorizes
a separate fresh-evaluation proposal.

### Keep diagnostics cheap and fixed

After each optimizer step, the runner evaluates the 175 in-memory probe rows and
records exact-action flips, family flips, take rate, model SHA-256, and parameter
L2 distance from entry. These checks do not access an environment and do not
select a checkpoint. The terminal comparison always uses checkpoint 20 unless a
safety condition stops training first.

## Risks / Trade-offs

- **Repeated development seeds can overfit** -> Treat the result only as a
  behavior-sensitivity and proposal-readiness experiment; require a separate
  fresh cohort before any quality claim.
- **Removing per-chunk control loses paired trend data** -> Keep candidate
  training outcomes per chunk and run one complete terminal paired comparison.
- **Candidate support can drift** -> Retain the eight-pair Courier censor bound,
  56-trajectory floor, unknown-blocker failure, and exact seed reporting.
- **More steps can collapse the family boundary** -> Evaluate the fixed probe
  after every step and stop when take/non-take coverage leaves 5%-95%.
- **Host interruption can duplicate a partial chunk** -> Restore model,
  optimizer, and RNG from the chunk-entry checkpoint and publish no partial
  update or partial checkpoint.

## Migration Plan

1. Add candidate-arm normalization, rollout, baseline, and update regressions.
2. Add the source-bound continuation runner and complete-boundary resume tests.
3. Publish one registration and execute the bounded continuation.
4. Publish the terminal comparison and verdict outside production discovery.
5. Keep native SimpleAgent as rollback regardless of verdict.

## Open Questions

None. The fixed schedule and gates are intentionally decided before execution.
