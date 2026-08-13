## Context

The expanded-corpus residual was selected entirely on train folds, persisted
before development access, and improved all fixed development metrics. Its
model bytes, configuration, development evidence, and the untouched audit
schedule are now tracked. The native corpus collector already enforces complete
action sets and registered Courier censor behavior.

## Goals / Non-Goals

**Goals:**

- Evaluate the exact frozen residual on independent reserved seeds.
- Preserve model-before-environment ordering and production isolation.
- Apply fixed development-equivalent gates without retries or tuning.

**Non-Goals:**

- Refit the residual, compare alternatives, or use audit results for selection.
- Start gameplay, load production models, or claim causal/policy quality.
- Replace censored seeds or access another cohort after failure.

## Decisions

### Load the frozen model without fitting

The audit runner restores the tracked residual model and r7 entry checkpoint,
verifies their exact bindings, and persists their identity before constructing
the native environment factory. No fitting function is called in preflight or
execution.

### Consume only the reserved audit cohort

Use seeds `80320..80383`, at most two states per seed, 512 branches, four
registered Courier censors, and a minimum of 110 complete states. No censored
seed is replaced. The charged-time limit is 3,600 seconds.

### Reuse the fixed development gate

Audit must reduce mean regret, not increase maximum regret, increase weighted
pairwise accuracy, not decrease unique-best accuracy, correct at least four
actions, and have no more worsened than corrected actions. Passing authorizes
only a separate fresh gameplay/evaluation proposal.

## Risks / Trade-offs

- [Audit has only 64 seeds] -> Require 110 complete states and multiple
  independent metrics; do not reuse the cohort.
- [Courier reduces support] -> Allow four registered censors and fail below the
  fixed state floor.
- [Native run is interruptible] -> Publish only after complete collection and
  fixed evaluation; infrastructure failures may rerun the unchanged schedule,
  while completed logical results are not retried.
