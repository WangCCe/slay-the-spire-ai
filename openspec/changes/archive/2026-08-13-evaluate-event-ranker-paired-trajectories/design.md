## Context

The event ranker replicated lower one-step regret on fresh counterfactual
sources, but repeated event overrides can interact across a run and change which
later states are visited. A paired trajectory test is the shortest evidence path
from local ranking quality to whole-policy value.

## Goals / Non-Goals

**Goals:**

- Compare pure Current and Current plus the exact event overlay from identical
  fresh simulator seeds.
- Measure terminal victory, floor, strict return, and override exposure.
- Decide whether simulator-only policy integration is justified.

**Non-Goals:**

- Model fitting, threshold calibration, policy-gradient training, or OPE.
- Gameplay, CommunicationMod, production loading, or promotion.
- Route, shop, card-reward, or combat policy changes.

## Decisions

### Fixed paired cohort

Use seeds `94600..94727`, disjoint from all event POC, training, development,
and fresh source-shadow cohorts. Construct a new environment and Current session
for each arm. Require at least 112 complete pairs, 96 pairs with an eligible
event decision, and 64 pairs with at least one actual event override. Allow at
most 16 pairs censored only by registered continuation support boundaries.

### Exact event overlay

At every target decision, ask the persistent Current session for its legal
action. For multi-option event states only, project the exact state/candidate
features, score the bound model, and apply its stored confidence threshold
against Current. All other states execute Current unchanged. Record both the
Current proposal and executed action for every event decision.

### Fixed terminal-value gates

Use strict terminal return `2*victory + floor/57`. Integration readiness requires
selected mean return to improve Current, selected victory count and mean floor to
be noninferior, no pair where Current wins and selected loses, at least one
improved pair, and improved pairs not fewer than worsened pairs. Support and
event-exposure floors must also pass. These gates are evaluated once after all
complete pairs; no seed replacement or tuning follows.

## Risks / Trade-offs

- [Deterministic paired outcomes remain high variance] -> Pair identical seeds
  and bind both terminal outcomes and action traces.
- [Current agent state diverges when an event action is overridden] -> Still call
  Current at every event before overlay selection so its episode-local screen
  handling advances consistently.
- [Unsupported downstream state affects one arm] -> Exclude the entire pair and
  record the exact registered blocker; unknown failures remain fatal.
- [Aggregate gains hide lost wins] -> Require zero paired Current-win to
  selected-loss regressions in addition to aggregate victory noninferiority.

## Migration Plan

Add one offline runner, tests, and report. No production migration occurs.
Rollback removes those files.

## Open Questions

If paired value passes, the next change must define a simulator policy bundle
and live shadow-only integration boundary before the ranker can affect gameplay.
