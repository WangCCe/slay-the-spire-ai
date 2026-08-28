## Context

The action-relative residual is evaluated only when the production parent
proposes EndTurn and an outer `CombatRLAgent` guard replaces it with a legal
non-EndTurn action. Shadow mode can observe that guard action at the existing
final-action callback, but the callback currently occurs after the outer guard
pipeline and therefore cannot grant authority without an explicit late
takeover boundary.

The qualified artifact is bound to production r16, its two corpora, and a CPU
mirror of the frozen parent. Its five-game CPU shadow produced 241 eligible
events and 66 intervention intents with zero runtime errors and 7.244ms p95
latency. The next evidence must exercise candidate actions in real gameplay
without turning a development adapter into a production checkpoint.

## Goals / Non-Goals

**Goals:**

- Add explicit eval-only action-relative candidate authority at the final guard
  boundary while preserving the production parent and ordinary parent arm.
- Fail closed to the completed guard action on registration, inference,
  decoding, legality, safety-veto, tracing, or commit failure.
- Record parent, guard, candidate, veto, selected, and final actions so late
  takeover and later guard/final mismatches are independently auditable.
- Run one fixed ten-pair candidate-vs-r16 live gate and restore the production
  CommunicationMod configuration exactly after each arm.

**Non-Goals:**

- Training, fitting, threshold changes, alternate artifacts, or same-cohort
  tuning.
- Refactoring the full `CombatRLAgent` guard pipeline or weakening existing
  safety behavior for ordinary gameplay.
- Automatic checkpoint promotion or a statistically powered win-rate claim.

## Decisions

### Candidate mode has a distinct registration and environment variable

Add `STS_COMBAT_RL_ACTION_RELATIVE_CANDIDATE_REGISTRATION` and a matching
batch-wrapper argument. The registration binds `mode=candidate`, source files,
the already qualified artifact and corpus identities, production checkpoint
and state, CPU inference, trace path, finite decision budget, and the fixed
late-safety-policy version. Agent startup rejects any combination of latent
shadow, latent candidate, action-relative shadow, or action-relative candidate
runtimes.

Historical schema-v1/v2 shadow registrations remain unchanged. Candidate mode
uses its own exact schema rather than assigning meaning to unused shadow
readiness fields.

### Late takeover is split into propose, safety veto, and commit

The action-relative runtime continues to cache the raw parent proposal. At the
final-action boundary, candidate mode encodes the completed guard action and
computes the same constrained alternative used by shadow mode. The outer
`CombatRLAgent` decodes that proposal, applies a source-fixed veto, and either
selects the candidate or retains the guard before the ordinary final commit.

The fixed veto rejects non-card actions, invalid or unplayable cards,
self-lethal and unsafe HP-loss cards, and any proposal for which the existing
mandatory lethal, survival, boss-pressure, or action-specific guard predicates
would retain or replace the proposal. Veto is not configurable in the live
registration. Refactoring the entire guard pipeline into a reusable second
pass was considered but rejected because its blast radius is much larger than
this bounded evaluation.

### Candidate telemetry extends the qualified shadow evidence

Each committed decision records the original parent, completed guard,
candidate and advantage, safety-policy version and veto reason, selected
action, takeover-applied flag, final action, latency, and all existing identity
and legality fields. Transient waits do not consume the decision budget.
Runtime or trace failures disable candidate authority and invalidate the arm;
gameplay may continue under the guard action only to preserve recoverability.

### The first matched gate reuses the established ten-pair canary

Freeze ten fresh Ironclad A0 seeds and run the candidate arm first, then
production r16 in identical order, both with conservative routing, eval mode,
epsilon zero, and training disabled. The candidate qualifies only when paired
floor wins exceed losses, at least one pair differs, aggregate floors and Act
2/Act 2 boss/Act 3/victory progression are non-worse, at least one safe
takeover occurs, both arms complete, and all identity, legality, error, seed,
and restoration checks pass. Passing permits only a separate promotion
decision.

## Risks / Trade-offs

- [Late takeover can bypass an outer guard] -> Reapply a fixed source-bound
  safety veto at the final boundary and retain the guard on any uncertainty.
- [The veto can suppress useful candidate intents] -> Record veto reasons and
  treat this as conservative canary evidence, not as the artifact's maximum
  possible effect.
- [Ten pairs have low statistical power] -> Require strict paired
  non-regression and use the result only as a promotion go/no-go input.
- [Sequential arms can drift] -> Freeze seed order and launch configs, preserve
  complete runtime evidence, and restore/verify production config between arms.

## Migration Plan

1. Add RED registration, mutual-exclusion, late-proposal, veto, trace, and
   wrapper-environment tests.
2. Implement the candidate runtime and fixed safety veto; run focused tests and
   one timed commit gate at the source boundary.
3. Commit and push source, then freeze the source-bound candidate registration,
   ten fresh seeds, candidate/parent launch configs, and scoring rules.
4. Run candidate and parent arms once, restore production after each, reconcile
   evidence, and publish the fixed decision.
5. Roll back by omitting the candidate registration and restoring the saved
   production config; no checkpoint or artifact is modified.

## Open Questions

None. A passing gate still requires a separate explicit promotion decision.
