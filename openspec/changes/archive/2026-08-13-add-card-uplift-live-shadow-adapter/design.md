## Context

The simulator candidate is frozen and has positive independent whole-run
evidence. Live `Game` objects expose the run, deck, offer, relic, potion, and map
surfaces needed for scoring, but not every simulator-internal enum or history
field. The first live step must therefore measure adapter behavior without
allowing the shadow result to own an action.

## Goals / Non-Goals

**Goals:**

- Load exact tracked r7 and residual bytes only under explicit configuration.
- Produce deterministic current-versus-shadow rows for ordinary three-card
  non-combat rewards.
- Preserve the exact Current action object under success, ineligibility, and
  every failure.
- Return to fresh gameplay quickly with a small, inspectable cohort.

**Non-Goals:**

- Claim that live best-effort features equal native simulator features.
- Select a card, explore, train, tune, or update any checkpoint.
- Use live outcomes to reinterpret the completed simulator evaluation.

## Decisions

### Wrap the final callback

An opt-in runtime wraps the callback after any existing exploration wrapper, so
it observes the action that CommunicationMod will receive. The wrapper calls
Current exactly once, records shadow evidence afterward, and returns the same
object by identity.

### Bind configuration and frozen bytes

`STS_CARD_UPLIFT_SHADOW_CONFIG` names one canonical JSON config containing the
source commit, source bindings, entry/residual bindings, output path, and false
authority map. Startup rejects drift before gameplay. The batch wrapper exposes
one option that sets this environment variable for the child.

### Label the projection boundary honestly

The projector mirrors the API-v3 card schema from live fields and records
`live-best-effort-v1`. Known simulator-only or estimated fields are listed in
each row. Unsupported rewards, including bowl, generated combat choices, and
non-three-card offers, are recorded as ineligible and never scored.

### Fail open after Current owns the action

Initialization errors fail startup when the user explicitly requested shadow
mode. Per-decision projection, scoring, or persistence errors emit logging and
return Current unchanged. No shadow exception crosses the callback boundary.

## Risks / Trade-offs

- [Feature distribution differs from simulator] -> Record the projection
  version and known shifts; use rows only to decide whether a canary proposal is
  justified.
- [Shadow latency delays gameplay] -> Load once, score only eligible card
  rewards on CPU, and report per-row latency.
- [Persistence fails] -> Log the failure and preserve Current action ownership.
- [Repeated state callbacks duplicate rows] -> Bind each row to run, floor,
  decision ordinal, offer hash, and final action; suppress exact duplicate keys.
