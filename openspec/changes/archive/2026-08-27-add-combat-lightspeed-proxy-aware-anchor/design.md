## Context

Deployment-consistent LightSTS collection can replace a frozen parent's raw `EndTurn` with a legal card through the registered guard proxy. Replay correctly stores the card that the simulator executed, but the parent-policy anchor later recomputes the frozen parent's raw greedy action and labels that row as `EndTurn`. This creates contradictory supervision precisely on the rows where deployment behavior differs from the raw parent.

The previous no-anchor ablation regressed materially, so removing conservative anchoring is not supported. The change instead needs row-level provenance that survives replay balancing, buffer sampling, and checkpoint round trips without changing existing callers or production behavior.

## Goals / Non-Goals

**Goals:**

- Represent confirmed guard replacements as explicit transition provenance.
- Opt in to executed-action anchor labels only for confirmed replacement rows.
- Preserve frozen-parent greedy labels for parent, epsilon, uniform, and forced-EndTurn rows.
- Preserve existing behavior when the new mode or metadata is absent.
- Load legacy replay checkpoints with all override flags disabled.
- Bind the selected mode and observed override count in simulator-only evidence.

**Non-Goals:**

- Changing encounter identity, rewards, TD targets, replay balancing, guard rules, or action selection.
- Loading a production checkpoint into CommunicationMod, running gameplay, packaging, qualification, or promotion.
- Authorizing a training experiment from implementation tests alone.

## Decisions

### Use an explicit label mode plus per-row provenance

The runner will expose `parent_anchor_label_mode` with default `frozen-parent-greedy-v1` and opt-in `guard-replacement-executed-action-v1`. `ReplayTransition` will retain `guard_proxy_replaced: bool = False`, and replay insertion will derive `anchor_to_executed_action` only when both the opt-in mode is active and the row records an actual replacement.

This separates experiment configuration from observed provenance. A single global switch is insufficient because only a subset of guarded-parent rows are replacements, while inferring replacement from positive energy or executed action would also misclassify exploration rows.

### Store the resolved override in replay schema v2

`ReplayBufferV2` will append an optional boolean `anchor_to_executed_action` field to each transition. New state dictionaries will use schema version 2 and persist this tensor. Version 1 state dictionaries will remain loadable by synthesizing an all-false tensor, preserving historical checkpoint semantics.

Storing the resolved flag keeps the trainer independent of LightSTS guard implementation details and makes sampled labels reproducible after checkpoint resume.

### Select mixed anchor targets at training time

The trainer will continue to compute the frozen parent's mask-aware greedy action for every anchored batch. It will then use the sampled executed action only where `anchor_to_executed_action` is true, and the frozen-parent action everywhere else. Anchor parameters remain frozen and receive no optimizer updates.

This retains the conservative anchor on ordinary and exploratory rows while removing the direct label conflict on confirmed deployment proxy rows.

### Fail invalid opt-in configurations before collection

The proxy-aware mode will require guarded-parent behavior, a positive parent anchor weight, a warm-start parent, and the registered guard proxy. Unknown modes or incompatible combinations will fail before trajectory collection. Default mode remains valid for all existing paths.

### Report configuration and observed usage

Runner reports and checkpoint source bindings will include the label mode and the number of sampled override labels used by training updates. This is technical evidence only; it grants no gameplay or promotion authority.

## Risks / Trade-offs

- [Replay tuple expansion can break positional callers] -> Append the field, update all local unpacking, keep `add` and `store_transition` defaults, and cover v1/v2 round trips with focused regressions.
- [A false provenance flag silently preserves contradictory labels] -> Derive it directly from the collection branch's guard replacement telemetry and test parent, epsilon, forced-EndTurn, and replacement rows separately.
- [An invalid executed action could bypass the parent mask] -> Require every override action to be valid under the stored action mask and fail the update if the invariant is violated.
- [Override telemetry can be confused with unique replay rows] -> Report sampled override-label usage separately from collected replacement-row counts.
- [Positive simulator evidence may be overinterpreted] -> Keep reports production-incompatible and require a separately registered fresh experiment before any downstream gate.

## Migration Plan

1. Add RED regressions for provenance, mixed labels, legacy replay loading, and default behavior.
2. Introduce the optional fields and schema-v2 serialization with v1 compatibility.
3. Add runner mode validation, provenance propagation, and report telemetry.
4. Run focused RL v2 and LightSTS tests plus strict OpenSpec validation.
5. Roll back by selecting `frozen-parent-greedy-v1`; old callers and v1 checkpoints remain all-false.

## Open Questions

None for implementation. Any simulator comparison requires a new immutable registration after this change is complete.
