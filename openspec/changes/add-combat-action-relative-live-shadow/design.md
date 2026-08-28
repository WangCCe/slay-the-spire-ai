## Context

The action-relative scorer is explicitly post-guard: it predicts alternatives
relative to the card action selected after the parent proposes wasteful
`EndTurn`. In the real agent, the RL proposal is produced before outer safety
guards, while the exact guard-processed action is available only through
`commit_executed_action`. Running the scorer during the initial proposal would
therefore substitute the parent action for the required guard baseline and
invalidate the experiment.

The existing latent-gated live shadow already provides source-bound
registration, behavior-neutral proposal/commit attribution, bounded JSONL,
transient wait handling, runtime failure isolation, and launcher environment
wiring. The new runtime can reuse those lifecycle patterns but must defer
inference and publish post-guard-specific telemetry.

## Goals / Non-Goals

**Goals:**

- Observe the exact encoded state, legal action mask, parent proposal, and final
  guard-processed action from one production-r16 decision.
- Run candidate inference only for real `parent=90, executed!=90` opportunities
  and apply the EndTurn constraint before selection.
- Prove behavior neutrality, source binding, artifact identity, callability,
  legality, safety, bounded latency, and trace consistency on real game states.
- Produce one read-only readiness result from at most five games and 512
  committed decisions.

**Non-Goals:**

- Replace the production action, fit or tune any model, change guards, alter
  rewards, claim policy quality, or promote the artifact.
- Expand the batch, retry it, or change readiness thresholds after observing
  the trace.
- Reuse the pre-guard latent candidate runtime as if its timing were equivalent.

## Decisions

### Defer inference until execution commit

The RL agent SHALL call the new runtime at proposal time only to cache encoded
state, mask, game identity, and parent action. The existing final-action callback
SHALL provide the executed action. Only then may the runtime identify a guard
replacement and score alternatives relative to the executed guard action.

Alternative considered: infer at proposal time with parent action as baseline.
Rejected because the scorer was trained relative to the guard action, not raw
`EndTurn`, and the resulting telemetry would answer a different question.

### Count all committed decisions and report eligible support separately

Each committed policy decision SHALL consume one of 512 budget slots and emit
one event. Ineligible events record a fixed support reason without loading the
scorer path; eligible events record candidate inference. Readiness requires at
least 100 eligible events, so insufficient natural support fails closed without
extending the game count.

Alternative considered: count only eligible events. Rejected because the shadow
could remain enabled indefinitely and its denominator could not be audited.

### Preserve exact legal mask and enforce EndTurn before maximization

Eligible inference SHALL use the proposal's exact encoded state and legal mask,
the executed action as guard, and an alternative mask containing legal
non-guard actions except action 90. No allowed alternative or a prediction below
threshold produces a candidate abstention; neither outcome changes execution.

Alternative considered: canonicalize live actions through LightSTS helpers.
Rejected because those helpers consume simulator state rather than the real
CommunicationMod game object. Exact action support is published for later
identity-divergence analysis instead of silently mapping it.

### Keep the new runtime mutually exclusive with existing live candidates

The launcher and RL agent SHALL reject simultaneous action-relative shadow,
latent-gated shadow, or latent-gated candidate registrations. The registration
binds source, artifact, parent checkpoint and state, corpus identities, trace,
budget, and readiness thresholds before startup.

Alternative considered: run both shadows together. Rejected because shared
pending commit attribution and latency would be ambiguous.

## Risks / Trade-offs

- [Five games may not yield 100 guard replacements] -> Report insufficient
  support and stop; do not enlarge the cohort post-hoc.
- [Exact live action slots differ from canonical simulator representatives] ->
  Publish legal indices, selected identity, and support telemetry for a later
  divergence decision.
- [Shadow inference raises after production action is chosen] -> Record one
  error if possible, disable the shadow, and preserve production execution.
- [Game restart or transient wait interrupts a pending event] -> Discard waits
  without budget consumption and emit explicit lifecycle evidence for other
  interruptions.

## Migration Plan

Implement and test the runtime, agent and launcher integration, and summarizer.
Commit a source-only version, then commit one registration binding the retained
artifact and production r16. Temporarily add the shadow registration argument to
the existing five-game CommunicationMod command, launch one fresh batch, restore
the prior config after terminalization, and publish the trace and summary.
Rollback removes the environment option and runtime and restores the exact
pre-run config; no checkpoint changes are involved.

## Open Questions

If readiness passes, a separate change must decide whether the first action
authority experiment should be replay-based confirmation or a small matched
live takeover gate. This shadow does not answer policy-quality questions.
