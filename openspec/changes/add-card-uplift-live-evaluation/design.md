## Context

The frozen card-uplift model already passed offline, independent simulator,
live shadow, and repaired intervention-canary gates. The existing canary
configuration deliberately hard-codes three games, so it cannot provide a
useful live victory/floor sample without repeated configuration identities.

## Goals / Non-Goals

**Goals:**

- Run one source-bound candidate-owned cohort of 1 to 25 fresh games.
- Reuse the tested card eligibility, action mapping, fallback, logging, and
  two-thread inference path.
- Preserve exact rollback and publish run/decision evidence.

**Non-Goals:**

- Training, exploration, model selection, causal paired claims, promotion, or
  production checkpoint changes.
- Extending the supported card-reward boundary.

## Decisions

1. Add a third explicit configuration schema and environment variable for live
   evaluation instead of weakening the three-game canary contract. This keeps
   historical canary evidence replayable and makes mutually exclusive startup
   validation explicit.
2. Reuse `CardUpliftCanaryRuntime` behavior through a small evaluation subclass;
   only the validated game ceiling and row schema differ. Duplicating scoring
   or action mapping would create unnecessary drift.
3. Accept a registered `maximum_games` from 1 through 25. The first execution
   will use 10 games; a later 25-game cohort requires a new output identity and
   fresh runs, not mutation or resume of the first cohort.
4. Treat at least one real `victory=true` as the policy-outcome success signal.
   Zero errors, legal actions, intact bindings, maximum latency at most 200 ms,
   and exact configuration restoration remain hard operational gates.

## Risks / Trade-offs

- [Unpaired live outcomes are noisy] -> Report them descriptively and do not
  claim causal superiority over Current.
- [Candidate harms a run] -> Bound the cohort, retain strict per-decision
  fallback, and restore Current after completion.
- [A runtime failure recurs] -> Disable later substitutions immediately and
  classify the cohort as an operational no-go.
- [Long batches obscure failures] -> Start with 10 games and monitor decision
  rows, logs, and `.run` files while the process is active.

## Migration Plan

Add and test the opt-in mode, commit it, generate a source-bound configuration,
save the existing CommunicationMod configuration, run the bounded cohort, and
restore the saved bytes. With the environment variable absent, ordinary startup
and Current behavior remain unchanged.

## Open Questions

None for the first 10-game cohort.
