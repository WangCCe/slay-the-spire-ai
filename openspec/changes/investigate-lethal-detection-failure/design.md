## Context

`IroncladCombatPlanner.plan_turn()` calls `CombatEndingDetector` before normal planning and returns a non-empty lethal sequence when one is proven. `OptimizedAgent` caches and emits that sequence, but caches no plan kind. `CombatRLAgent` receives only the next fallback action.

The HP-loss pressure guard introduced in commit `139ddb4b` asks whether playing an HP-loss card would leave the player unable to survive current end-turn incoming damage. That check is correct for ordinary filler actions. It is incorrect for the first action of a validated lethal sequence because the incoming damage will not occur when the sequence completes.

The later single-card lethal guard cannot handle this case because the fresh failure involved two living monsters and a two-card sequence.

## Goals

- Preserve lethal intent across the planner, fallback agent, and takeover guard boundary.
- Bypass end-turn pressure heuristics only for an active validated lethal prefix.
- Preserve immediate self-death and action-legality vetoes.
- Keep the change small enough to validate with the exact live state.

## Non-Goals

- Recompute lethal independently inside `CombatRLAgent`.
- Treat aggregate damage estimates as validated plans.
- Reorder unrelated non-combat or reward policy.
- Refactor all combat guards into a new framework.

## Root Cause

The failing path is:

```text
CombatEndingDetector proves lethal
  -> IroncladCombatPlanner returns [Hemokinesis, Headbutt]
  -> OptimizedAgent caches the sequence and returns Hemokinesis
  -> plan provenance is lost at the fallback-agent boundary
  -> CombatRLAgent evaluates Hemokinesis as generic HP-loss filler
  -> end-turn pressure check returns unsafe
  -> EndTurnAction replaces the lethal prefix
  -> player dies
```

The root cause is missing semantic provenance, not insufficient damage scoring or an inaccurate low-HP threshold.

## Decisions

### Carry plan kind with the cached sequence

`IroncladCombatPlanner` SHALL expose whether its most recent non-empty plan came from the validated lethal branch. `OptimizedAgent` SHALL cache that plan kind with `current_action_sequence` and clear it whenever the sequence is cleared, invalidated, replanned, or reset for a new turn.

The fallback agent SHALL expose a narrow query that tells `CombatRLAgent` whether the action just returned is part of the active validated lethal plan. `CombatRLAgent` SHALL not inspect planner internals directly or run a second approximate lethal calculation.

### Apply hard vetoes before lethal preservation

Before a lethal prefix is passed through, the current action must be normalized and executable. It remains blocked when its immediate HP cost or known reactive damage kills the player before the action resolves safely.

Low HP and projected end-turn incoming damage are not hard vetoes. They are pressure heuristics and SHALL yield to a safe lethal prefix.

### Acknowledge every consumed cached-plan action

`OptimizedAgent` SHALL expose identity-based membership, plan-kind, and
rejection for the action most recently emitted from its cached sequence.
`CombatRLAgent` SHALL acquire fallback once and finalize the emitted action
exactly once. Returning the same validated planned action accepts it; returning
any wait, end turn, potion suppression, repaired target, survival action,
pressure action, or other replacement rejects and clears the entire cached
continuation.

Plan kind affects lethal guard precedence only. Plan rejection applies to both
ordinary and lethal cached sequences. A normalized lethal action counts as the
same action only when it preserves the planned card and still-live target.

### Emit arbitration evidence

Logs SHALL distinguish:

- validated lethal prefix passed through;
- lethal prefix rejected by action legality;
- lethal prefix rejected by immediate self-death;
- ordinary HP-loss action rejected by end-turn pressure.

## Guard Order

For takeover fallback actions:

1. normalize and validate the current action;
2. reject immediate self-death;
3. pass through an active safe lethal prefix;
4. apply encounter-specific survival guards;
5. apply HP-loss pressure, setup, and filler guards;
6. execute a legal fallback or end the turn.

## Error Handling

- Missing or stale plan metadata defaults to normal guard behavior.
- A mismatch between the returned action and the cached lethal sequence disables the bypass and logs a diagnostic.
- Exceptions in provenance checks do not send an unvalidated action; they fall back to existing guard behavior.

## Testing

- Reproduce the fresh Large Slime state with 3 HP, 2 energy, two monsters, and a lethal Hemokinesis-plus-Headbutt sequence. Expected first action: Hemokinesis with a valid target, not `EndTurnAction`.
- Prove an HP-cost action that immediately kills the player remains blocked.
- Prove a Guardian Sharp Hide action that kills the player before safe resolution remains blocked.
- Prove a non-lethal HP-loss filler that exposes lethal end-turn damage remains blocked.
- Prove plan kind clears on replan, stale sequence, combat end, and turn reset.
- Run focused tests, full pytest, and a fresh 25-game no-training evaluation.

## Rollout

Commit the regression-backed fix as one behavior class. If the fresh batch contains another A-class guard-arbitration failure, address it separately and restart baseline qualification. Do not broaden this change based only on B/C-class policy noise.
