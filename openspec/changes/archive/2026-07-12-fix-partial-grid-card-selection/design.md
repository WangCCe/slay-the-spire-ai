## Context

`SimpleAgent.handle_screen()` treats `GridSelectScreen.num_cards` as the number
to select on every callback. CommunicationMod can legitimately deliver an
intermediate GRID state while queued selections drain, and
`selected_cards` is reconstructed separately from `cards` on every JSON state.

The failed qualification state had `num_cards=3` and two already selected
cards. Returning three more cards violated the strict remaining-card check in
`CardSelectAction.execute()` and repeated without changing game state.

## Goals / Non-Goals

**Goals:**

- Select exactly the remaining required GRID cardinality.
- Exclude already selected reconstructed cards without collapsing duplicates.
- Preserve current ranking for upgrade, purge, transform, remove, and neutral
  grids.
- Keep invalid action cardinality visible at the action boundary.

**Non-Goals:**

- Coordinator callback or queue changes.
- Action-side truncation.
- HAND_SELECT, gameplay policy, RL, route, reward, or training changes.

## Decisions

### Compute remaining cardinality in the producer

The GRID handler SHALL compute:

```text
remaining = max(0, total_required - selected_count)
```

and slice the ranked unselected candidates by `remaining`. The action layer
keeps exact-cardinality validation unchanged.

Action-side truncation was rejected because it would hide producer defects and
lacks the ranking context needed to choose the correct remaining card.

### Exclude selected cards as a multiset

Selected and available card objects do not share Python identity after JSON
parsing. Match one selected occurrence to one available occurrence by UUID
when present, otherwise by canonical card identity plus upgrade count.

Multiset consumption preserves unselected duplicate Strikes or Defends rather
than removing every equivalent card.

### Preserve partial callbacks

The coordinator remains free to call the agent from intermediate GRID states.
Suppressing callbacks was rejected because partial states are legitimate after
state changes or lost queued clicks.

## Risks / Trade-offs

- **Risk:** Card JSON lacks UUIDs for duplicate cards. **Mitigation:** canonical
  identity plus upgrade count removes only the number of selected occurrences.
- **Risk:** Fewer unselected cards exist than the remaining count.
  **Mitigation:** log the inconsistent state and return `StateAction()` instead
  of constructing an action strict validation will reject.
- **Risk:** Ranking changes accidentally alter non-partial selection policy.
  **Mitigation:** filter before applying the existing sort branches and retain
  focused upgrade/removal/neutral regressions.

## Migration Plan

1. Add the exact three-total, two-selected regression and duplicate fallback
   identity control.
2. Implement remaining-count and multiset filtering in `SimpleAgent` only.
3. Run focused screen/action tests, full pytest, strict OPSX validation, and
   independent review.
4. Commit one GRID-selection behavior fix.
5. Restart the original Batch 1 qualification from a new cutoff and write a
   retry report; preserve the failed attempt report.

Rollback is the single behavior commit. No stored data or configuration
migration is required.

## Open Questions

None. The raw log establishes total, selected, and remaining counts directly.
