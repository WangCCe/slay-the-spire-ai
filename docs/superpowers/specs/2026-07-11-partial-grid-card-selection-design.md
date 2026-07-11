# Partial GRID Card Selection Design

## Status

Approved under the user's standing authorization on 2026-07-11 after the
first fallback-plan qualification batch exposed an A-class legality loop.

## Evidence

At floor 17 after choosing Astrolabe, the GRID required three cards total.
The first `CardSelectAction` correctly requested three cards. CommunicationMod
then emitted intermediate states with one and two cards already selected while
the queued clicks drained.

On the state with `num_cards=3` and `selected_cards=2`, `SimpleAgent` again
returned three cards because it sliced the sorted candidates by the total
required count. `CardSelectAction.execute()` correctly calculated that one
selection remained and raised:

```text
Wrong number of cards selected (provided 3, need 1)
```

The unchanged screen caused 39 retries and prevented the bounded batch from
producing its second run.

## Goals

- Select exactly the number of cards still required by a GRID screen.
- Exclude cards already selected in an intermediate GRID state.
- Preserve upgrade, purge, transform, remove, and neutral-grid ranking policy.
- Keep `CardSelectAction` cardinality validation strict.
- Cover reconstructed card objects and duplicate cards safely.

## Non-Goals

- Do not change event, relic, card, route, combat, or RL policy.
- Do not suppress or truncate invalid actions in `CardSelectAction.execute()`.
- Do not change coordinator callback timing or queue draining.
- Do not generalize this fix to unrelated screen protocols.

## Considered Approaches

### Agent-side remaining selection (selected)

Compute `remaining = total_required - len(selected_cards)`, remove already
selected cards from the candidate multiset, retain the existing ranking, and
return exactly `remaining` cards.

This fixes the producer at the point where total and remaining cardinality
were confused. It remains correct whether the callback arrives before any
selection, after a partial selection, or when selection is complete.

### Action-side truncation (rejected)

Silently truncate `CardSelectAction.cards` to the remaining count. This hides
caller bugs and may choose an already selected or lower-priority card because
the action lacks policy context.

### Coordinator callback suppression (rejected)

Delay all GRID callbacks until queued selections finish. Partial callbacks are
legitimate and can occur after state changes or lost clicks; every screen
handler must remain correct when resumed from an intermediate state.

## Card Identity

`GridSelectScreen.from_json()` reconstructs `cards` and `selected_cards`
separately, so Python object identity is insufficient.

Match selected cards as a multiset using:

1. UUID when present;
2. otherwise canonical card identity plus upgrade count.

Remove one available-card occurrence per selected-card occurrence. This keeps
duplicate Defends or Strikes distinguishable by multiplicity without removing
every equivalent copy.

## Data Flow

1. Read `num_cards` as the total required count.
2. Read the reconstructed `selected_cards` list.
3. Compute `remaining = max(0, total - selected_count)`.
4. If `remaining == 0`, use the existing confirm/proceed behavior.
5. Remove selected-card occurrences from `screen.cards` by the stable multiset
   key.
6. Apply the existing upgrade/removal/neutral sorting policy to the remaining
   candidates.
7. Return `CardSelectAction(sorted_candidates[:remaining])`.

## Error Handling

- Invalid or negative `num_cards` coerces to zero through the existing numeric
  helper.
- If selected count exceeds total, remaining clamps to zero.
- If fewer unselected cards exist than required, log the inconsistent state
  and return `StateAction()` to request a refresh; do not invent duplicates or
  construct an action that strict cardinality validation will reject.
- Preserve `any_number` behavior and current confirmation handling.

## Testing

- Reproduce the live state with three total, two reconstructed selected cards,
  and one remaining unselected card. Assert one-card action output.
- Use distinct objects with matching UUIDs to prove reconstructed-card
  exclusion.
- Cover duplicate cards without UUIDs and assert multiset removal removes only
  the selected occurrence.
- Keep existing neutral, purge, transform, upgrade, and HAND_SELECT tests green.
- Run focused screen/action tests, full pytest, strict OPSX validation, and an
  independent task review.
- Restart Batch 1 from a new cutoff only after the fix is approved.

## Rollout

Implement as a separate OPSX change and cohesive commit. Preserve the failed
Batch 1 report as audit evidence. After approval, create a new Batch 1 retry
report rather than rewriting the failed attempt, then require the original
two consecutive clean 25-game batches.
