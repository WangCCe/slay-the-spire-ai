## Context

Shop is the only major non-combat decision category without action-level
outcome collection. The bound A0 native adapter now excludes known-invalid
Courier states and impossible potion purchases, so the remaining subset can be
measured without pretending full shop compatibility.

## Goals / Non-Goals

**Goals:** collect deterministic branch returns for legal actions at supported
shop states and make a fixed learning-signal go/no-go decision.

**Non-Goals:** model fitting, policy comparison, full Courier support, A16
pricing, gameplay, training, or promotion.

## Decisions

### Reuse frozen Current continuation

At each first supported shop per seed, clone the environment once per legal
candidate, apply that action, then let the existing Current bridge own all
later choices. This measures action-level opportunity while holding continuation
constant and reuses the established strict primary return `2*victory+floor/57`.

### Preserve the complete shop action domain

Store candidate kind, label, price/raw payload, Current action, and every branch
trace. Do not collapse purchases into buy/leave because cards, relics, potions,
purge, and leave have distinct costs and downstream effects. The learning gate
requires at least four observed kinds.

### Fail closed on simulator boundaries

Registered Courier support blockers censor the source state. Any unknown
blocker, missing candidate outcome, repeated source identity, nondeterministic
replay, deadline violation, or active game process aborts the collection.

### Use one fixed fresh cohort

Run seeds `95000..95063` once, at most one shop source per seed, 512 action
branches, 32 censors, and 7200 charged seconds. Signal viability requires 24
complete sources, 12 informative sources, four kinds, and eight exact replays.
No threshold changes or retry follow outcome access.

## Risks / Trade-offs

- [Few runs reach a supported shop] -> Use 64 seeds but keep one state per seed.
- [Large inventories consume branch budget] -> Stop at 512 branches and report
  budget exhaustion rather than sampling actions.
- [Current continuation re-enters Courier] -> Censor the entire source to keep
  every action row complete and comparable.
- [Supported subset is mistaken for full shop semantics] -> Bind A0 and report
  Courier/A16 exclusions in every artifact.

## Migration Plan

Implement focused pure-collection tests, commit and bind the runner, execute the
cohort once, and archive the result. A pass permits a separate source-only
ranking change; a failure retains Current.

## Open Questions

None. Cohort, limits, reward, censor policy, and gates are fixed.
