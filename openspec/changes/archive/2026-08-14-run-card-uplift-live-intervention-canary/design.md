## Context

The existing opt-in live shadow runtime already validates source/model bindings,
projects eligible live card rewards, scores the frozen uplift model, and emits
canonical rows. It deliberately never changes actions. The shadow evidence now
supports a narrow operational canary, not a policy-quality claim.

## Goals / Non-Goals

**Goals:**

- Execute the frozen candidate on a bounded number of eligible card rewards.
- Preserve an exact Current fallback for ineligible states and all failures.
- Make every substitution and rollback condition observable.
- Finish the canary in three fresh games and restore ordinary configuration.

**Non-Goals:**

- Training, exploration, model or threshold tuning, causal inference, policy
  promotion, or qualification.
- Changing combat, route, shop, event, default gameplay, or checkpoints.

## Decisions

### Add a separate explicit canary configuration

Use `STS_CARD_UPLIFT_CANARY_CONFIG` with a distinct schema and authority that
permits only card-reward action selection. Shadow and canary configuration are
mutually exclusive at startup. The canary binds the same entry checkpoint,
residual model, source files, output path, and fixed maximum of three games.

This keeps ordinary and shadow execution unchanged and makes accidental
intervention impossible without a dedicated command-line option.

### Reuse scoring and projection but add an exact action mapper

The canary calls the existing projection and score path after Current proposes
an action. If the candidate differs, map the selected action id back to exactly
one offered card or the legal skip action. Refuse Singing Bowl, generated combat
choices, non-three-card rewards, non-skippable rewards, unseen actions, and any
ambiguous mapping.

Alternatives rejected: editing the agent card heuristic mixes model deployment
with production policy; parsing action ids without checking the live offer can
create invalid commands.

### Fail closed for the remainder of the run

An ineligible decision falls back only for that decision. Any projection,
scoring, binding, or action-construction exception records an error, disables
all later substitutions, and returns Current. The wrapper never suppresses the
underlying agent action.

### Treat the canary as operational evidence

Success requires exactly three fresh runs, at least eight substitutions, zero
invalid actions, zero runtime errors, canonical unique rows, intact bindings,
and maximum scoring latency at most 200 ms. Floors and victories are descriptive
only. Passing allows a separate policy-value experiment; failing restores
Current without retry or tuning.

## Risks / Trade-offs

- [Live projection differs from simulator state] -> Retain known-shift metadata,
  strict eligibility, and immediate Current fallback.
- [Candidate selects an invalid offer] -> Construct actions only from the live
  screen object after unique action-id matching.
- [A callback exception stalls gameplay] -> Catch it at the wrapper boundary,
  disable canary intervention, log the error, and return Current.
- [Three runs are too noisy for quality] -> Make no quality claim; measure only
  operational safety and evidence volume.

## Migration Plan

Implement and test the opt-in runtime, commit and bind it, create one canary
configuration, run three fresh games with Windows Python, collect rows and run
records, restore the prior CommunicationMod command, and archive the result.
Rollback is removal of the canary option/config followed by the normal restart.

## Open Questions

None. Model, limits, success metrics, fallback, and rollback are fixed before
the live run.
