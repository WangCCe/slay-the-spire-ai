## Context

RL v2 already stores executed actions, persists a per-transition `anchor_to_executed_action` boolean, and lets the parent-policy anchor use that executed action as its label. The live agent never sets the boolean: `commit_executed_action()` rewrites or creates a pending transition but `observe_next_state()` always calls `store_transition()` with the default false value.

This omission is material in deployment. The latest fresh 3,433-transition replay has zero override flags and only 35.97% frozen-parent/executed-action agreement. A separate matched live canary logs 401-403 energy-guard replacements per ten-game arm, plus fallback takeover actions that are emitted without a fresh RL proposal.

## Goals / Non-Goals

**Goals:**

- Preserve whether a stored action came directly from the RL proposal or from outer-policy replacement/takeover.
- Feed that provenance into the existing replay and parent-anchor override mechanism.
- Keep action masks, checkpoint compatibility, and CommunicationMod behavior unchanged.
- Produce fresh zero-update evidence that provenance is nonzero, legal, and consistent with retained runtime evidence.

**Non-Goals:**

- Changing energy, potion, lethal, or other combat guards.
- Training or promoting a candidate within this change.
- Reinterpreting historical all-false checkpoints.
- Adding a second replay schema or storing guard names in the tensor replay.

## Decisions

### Carry provenance on the pending transition

`PendingTransition` will gain an `anchor_to_executed_action` boolean. A direct RL proposal starts false. `observe_next_state()` will pass the value unchanged to `DQNTrainerV2.store_transition()`.

This uses the existing schema and training contract. Adding a parallel sidecar would make checkpoint/replay identity harder to validate and could drift from transition ordering.

### Derive the flag at the emitted-action boundary

`commit_executed_action()` is the only boundary that sees both the RL pending proposal and the action that the outer agent will emit:

- If an in-state pending proposal exists and its encoded action equals the emitted encoded action, retain false.
- If an in-state pending proposal exists and the encoded actions differ, update the stored action and set true.
- If no pending proposal exists and a legal combat action is emitted, create the pending transition with true. This represents potion preemption, fallback takeover, and other outer-policy actions without an RL proposal for that state.
- Preserve the current discard behavior for non-combat or unencodable actions and the current fail-closed behavior for stale pending transitions.

Comparing encoded action indices, rather than object identity or names, matches the replay action space and correctly includes card target differences.

### Keep provenance conservative and local

The boolean means only that the executed action must be authoritative for parent-anchor labeling. It does not claim that a guard action is globally optimal, identify which guard fired, or alter TD rewards. Guard-name telemetry remains in runtime logs.

### Validate collection before training

Unit regressions will exercise unchanged direct actions, changed same-state actions, no-proposal fallback actions, illegal actions, and stored replay flags. After focused tests and the qualified commit gate, a bounded zero-update production-r16 collection will retain checkpoint, decision trace, runtime logs, and run records. The report will reconcile marked rows with legal masks and outer-action evidence before any training proposal consumes them.

## Risks / Trade-offs

- [Fallback takeover may label heuristic actions that are locally safe but not globally optimal] -> The flag changes only optional parent-anchor labels; it grants no policy-quality claim, and training remains a separate evidence-gated change.
- [An action encoder mismatch could mark or store the wrong row] -> Reuse the current emitted-action legality check and test target-sensitive action indices.
- [Historical checkpoints remain all-false] -> Preserve schema-version compatibility and never infer provenance retroactively from state features.
- [Fresh gameplay costs time] -> Use a bounded zero-update cohort only after code gates pass; stop after the registered count and do not train during collection.

## Migration Plan

1. Add failing collection-path regressions.
2. Carry and persist the provenance flag with no action-selection changes.
3. Run focused RL transition tests and the qualified commit gate.
4. Collect and report one bounded fresh replay under production r16 with updates disabled.
5. Roll back by reverting the collection-side assignment; existing checkpoints remain readable and production checkpoint/configuration remain unchanged.

## Open Questions

None. Whether provenance-aware anchoring improves policy quality belongs to a later registered training experiment.
