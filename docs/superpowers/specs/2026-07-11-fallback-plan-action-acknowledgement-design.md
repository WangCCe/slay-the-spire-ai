# Fallback Plan Action Acknowledgement Design

## Status

Approved in principle on 2026-07-11. This design replaces the accumulated
lethal-only invalidation patches in Task 1 of
`investigate-lethal-detection-failure` with one generic cached-plan action
boundary.

## Problem

`OptimizedAgent.get_next_action_in_game()` currently returns an action from
`current_action_sequence` and advances `current_action_index` immediately.
`CombatRLAgent` can then replace that emitted action with a survival, pressure,
potion, wait, or legality guard action.

The fallback agent therefore records an action as consumed before the caller
has accepted it. A later cached action can be emitted even though its required
prefix never executed. Lethal provenance makes this unsafe because the later
action may bypass pressure guards, but the cursor defect applies to ordinary
cached plans as well.

The repeated review failures came from treating each replacement as a lethal
special case. The missing abstraction is acknowledgement of a consumed
fallback-plan action.

## Goals

- Preserve validated lethal provenance only when the emitted plan action is
  actually selected for execution.
- Invalidate the entire cached sequence whenever takeover returns a different
  action from the consumed planned action.
- Apply the same lifecycle rule to lethal and ordinary cached plans.
- Acquire the fallback action at most once per takeover decision.
- Keep lethal guard precedence after legality and immediate-death checks and
  before pressure, setup, and filler guards.
- Keep failure handling conservative across transient combat screens.

## Non-Goals

- Do not change planner scoring, lethal detection, combat weights, route
  policy, rewards, Bottled policy, or training behavior.
- Do not redesign all agent action APIs or add a general transaction system.
- Do not make `CombatRLAgent` inspect planner internals.
- Do not broaden the work beyond Ironclad fallback takeover behavior.

## Considered Approaches

### Generic acknowledgement boundary (selected)

Expose identity-based active-plan queries and rejection on `OptimizedAgent`.
After obtaining one fallback action, route every takeover result through a
single finalizer. The finalizer accepts the planned action or rejects the
cached sequence before returning a replacement.

This directly fixes the cursor ownership mismatch and covers lethal and
ordinary plans with one invariant.

### More lethal-only invalidation branches (rejected)

Add invalidation at each newly discovered lethal veto or replacement return.
This has already produced repeated gaps, duplicates lifecycle logic, and does
not protect ordinary cached sequences affected by the reordered fallback call.

### Non-consuming planner peek plus later commit (rejected)

Change `OptimizedAgent` to peek without advancing, then commit after the game
acknowledges execution. This is conceptually clean but changes the planner's
core sequencing protocol and requires broader state-transition work than the
current defect warrants.

## Interfaces

`OptimizedAgent` provides narrow identity-based methods:

```python
def is_active_plan_action(self, action: Action) -> bool: ...
def active_plan_kind_for_action(self, action: Action) -> Optional[str]: ...
def reject_active_plan_action(self, action: Action) -> bool: ...
```

- An action is active only when it is the exact object most recently emitted
  from the current cached sequence.
- `active_plan_kind_for_action()` currently returns `"lethal"` or `None`.
  Lifecycle logic must not infer plan membership from a non-null kind; ordinary
  cached actions are active plans with no special kind.
- `reject_active_plan_action()` clears sequence, index, signature, and plan
  kind only for the exact active action.
- Existing lethal-specific methods may remain as compatibility wrappers, but
  `CombatRLAgent` uses the generic contract.

`CombatRLAgent` uses one takeover finalizer with inputs equivalent to:

```python
def _finalize_takeover_action(
    self,
    emitted_action: Action,
    selected_action: Action,
    game: Game,
    *,
    accepted_plan_action: bool,
    active_plan: bool,
    plan_kind: Optional[str],
) -> Action: ...
```

The exact signature may follow local style, but the semantics are binding.

## Data Flow

1. Acquire exactly one fallback action.
2. Classify whether it is the active cached-plan action and record its plan
   kind before any guard can replace it.
3. Normalize and validate a lethal candidate without inventing a new target.
4. Reject immediate HP-cost or reactive-damage death.
5. Accept and return a safe active lethal prefix.
6. Otherwise run existing encounter, pressure, setup, filler, potion, wait,
   and legality guards.
7. Route the selected result through the finalizer.
8. If the selected result does not execute the emitted planned action, reject
   the whole cached sequence before returning it.

A normalized `PlayCardAction` can count as accepting the emitted action only
when it preserves the same card and the same still-live planned target. Generic
best-target repair is a replacement and therefore rejects the cached plan.

## Invariants

1. A takeover decision calls the fallback agent at most once.
2. Every emitted active-plan action is finalized exactly once.
3. The finalizer either accepts the planned action or rejects its entire cached
   continuation; there is no third normal state.
4. Any wait, end-turn, potion suppression, survival replacement, pressure
   replacement, legality repair, or other different action rejects the plan.
5. Ordinary non-plan actions do not call plan rejection.
6. Successful lethal pass-through does not reject or quarantine the plan.
7. Plan kind affects guard precedence only; plan lifecycle is generic.

## Failure Handling

The production fallback is `OptimizedAgent`, so generic rejection is expected
to succeed. Missing, false-returning, or throwing interfaces must not grant
lethal precedence.

When rejection fails for a confirmed active lethal action,
`CombatRLAgent` quarantines lethal precedence for the current combat epoch.
The epoch is:

```text
(bool(in_combat), floor, turn)
```

It is independent of `screen_type`, so same-turn `HAND_SELECT`, `GRID`, and
other transient screens do not clear quarantine. A turn change or combat exit
does clear it. Normal guards remain active while lethal precedence is
quarantined.

## Testing

- Keep the exact 3 HP Hemokinesis-plus-Headbutt live regression.
- Keep immediate HP-cost and Sharp Hide death controls.
- Keep stale target, early replacement, single fallback query, and ordinary
  pressure controls.
- Add an ordinary two-action cached plan whose first action is replaced;
  assert the second action is not emitted from the stale sequence.
- Add table-driven finalizer tests covering accepted planned action, normalized
  same action, wait, end turn, potion suppression, early survival replacement,
  late pressure replacement, and target repair.
- Add a failed lethal rejection regression that crosses `NONE -> HAND_SELECT ->
  NONE` in the same turn and remains quarantined.
- Prove quarantine clears on a new turn and combat exit.
- Run the three focused combat suites, full pytest, OPSX strict validation, and
  an independent task review before live evaluation.

## Rollout

Replace scattered lethal-only invalidation calls with the generic finalizer in
the existing Task 1 behavior commit. Do not start fresh qualification until the
task review reports both spec compliance and code quality approved. The live
gate remains two consecutive conservative 25-game eval batches with no
unresolved A-class mechanics or arbitration failure.
