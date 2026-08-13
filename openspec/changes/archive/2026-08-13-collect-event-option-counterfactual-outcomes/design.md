## Context

The simulator exposes cloneable event decisions and the reachable-event resolver maps all 48 supported event targets into Current-policy option positions. The prior route experiment also established a working frozen Current-policy continuation across off-baseline branches. What remains unknown is whether event options have enough deterministic terminal-return separation to support supervised ranking or RL credit.

## Goals / Non-Goals

**Goals:**

- Collect complete returns for every legal option at multi-option event sources.
- Preserve event id, semantics source, Current action, option candidates, terminal outcome, and return spread.
- Replay the first forced option for the first 16 complete sources and require exact outcome identity.
- Issue a simple viable/not-viable result without fitting a model.

**Non-Goals:**

- No model fitting, tuning, held-out evaluation, formal RL, gameplay, CommunicationMod, or production checkpoint access.
- No claim that one fixed Current continuation estimates arbitrary future-policy value.
- No permanent seed-consumption rule for implementation failures; this is an evidence collector, not a promotion gate.

## Decisions

1. **Generalize Current continuation by source category.** Rename the route-specific evaluator internally to accept any target category and retain the route wrapper for compatibility.
2. **Use fresh seeds `94000..94063`.** Follow native root trajectories to locate up to two multi-option event sources per seed, force all options, and continue each branch with a fresh Current session.
3. **Use compact semantic rows rather than hashed policy features.** This POC needs human-readable event/action/outcome evidence, not training tensors.
4. **Use fixed viability floors.** Require 64 complete sources, 32 informative sources, 8 distinct event ids, and 16 exact branch replays. Report all observed counts even on no-go.
5. **Write artifacts only after collection completes.** Failures leave no partial canonical output; after a code repair, the same POC may restart because no result-driven tuning or holdout access has occurred.

## Risks / Trade-offs

- **Rare event support may miss the count floor** -> Report observed event ids and stop without lowering the gate.
- **Current continuation may hit unsupported shop Courier states** -> Censor the source with the registered reason and enforce a bounded censor count.
- **Terminal return is high variance** -> This POC asks only whether deterministic within-state option separation exists; policy quality requires a later disjoint study.
- **Event semantics can be dynamic** -> Store resolver source and event observation for every source, and fail closed on mapping errors.

## Migration Plan

Add the generic continuation helper, event collector, tests, and one report. Rollback removes those additions; production behavior is unchanged.

## Open Questions

If the POC passes, the next change must decide between a simple event-option ranker and direct policy-gradient training. This change does not make that decision.
