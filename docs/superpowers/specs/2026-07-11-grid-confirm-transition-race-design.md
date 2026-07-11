# GRID Confirm Transition Race Design

## Status

Approved under the user's standing authorization on 2026-07-11 after the
second qualification batch exposed an A-class live command rejection.

## Problem

At 2026-07-11 23:13:17 CST, a shop purge opened a one-card GRID selection.
The agent selected a Strike, but a queued pre-selection GRID frame arrived
before the selection response. Because GRID selector commands and the terminal
optional confirm were fire-and-forget, the action queue drained on that stale
frame and invoked the agent again. The second callback selected the same card.

The first selection then raised the GRID confirm screen. The stale second
`ChooseAction` requested state, and the terminal optional action emitted a
confirm. A response to the state request still described GRID with confirm
available, so the empty queue invoked the agent a third time. Generic
availability handling returned `ProceedAction`, which mapped to a second
low-level confirm. CommunicationMod rejected that confirm after the first one
had closed the purge screen.

The rejection was represented by three propagation lines but one actual
command:

```text
Invalid command: confirm. Possible commands: [choose, potion, leave, key, click, wait, state]
```

## Root Cause

Commit `aa7a4856` made GRID-related `choose`, `click`, `key`, and confirm
commands non-blocking to remove a historical 10-second wait. That behavior
assumes the next received frame belongs to the command just sent. The current
coordinator can receive an already queued frame first, so readiness alone does
not establish command-response ordering.

CommunicationMod provides a narrower ordering primitive. Its input is a FIFO
queue, it executes at most one command per pre-update, and `wait 1` schedules a
state update after one frame. Therefore, a waiting `wait 1` sent after a GRID
selector produces a state that is ordered after that selector, even if an
older frame was already queued on the Python side.

The agent's generic `ProceedAction` is the final symptom, not the first cause.
The stale callback and duplicate selector already exist before that action is
created.

## Approaches Considered

### 1. Add GRID-specific protocol settle barriers

Serialize each GRID selector and follow it with a waiting `wait 1` barrier.
Serialize the terminal confirm and follow it with the same transition barrier.

Advantages:

- fixes both demonstrated stale-frame windows at the action source;
- uses CommunicationMod's FIFO and existing `wait` protocol instead of new
  shared lifecycle state;
- adds one frame rather than restoring the historical multi-second delay;
- preserves all non-GRID defaults and agent decision policy.

Risk:

- multi-card GRID selections add one settle frame per card;
- if CommunicationMod stops returning state entirely, progress depends on the
  coordinator's existing ready-wait state polling and timeout handling.

This is the selected approach.

### 2. Add a coordinator-level GRID in-flight state machine

Track selection and confirmation fingerprints across callbacks and suppress
callbacks until a selected-count or screen transition is observed.

This can tolerate an arbitrary number of stale frames, but it adds persistent
state, reset rules, timeout rules, and another screen-specific callback guard
to shared coordinator code. The demonstrated race has a smaller protocol-level
solution.

### 3. Guard generic GRID `ProceedAction`

Route GRID through `handle_screen()` before generic proceed handling or return
`StateAction` on confirm-only GRID frames.

This can avoid the final rejected confirm, but it does not prevent the stale
callback or duplicate card selection. It is a downstream symptom fix and is
not selected.

## Scope

In scope:

- GRID selector queue ordering for `choose`, `click`, and `key` transports;
- a one-frame response barrier after each GRID selector;
- GRID terminal confirm ordering and post-confirm transition settling;
- backward-compatible optional wait parameters on shared action classes;
- action-level and parsed-state coordinator regressions;
- focused and full pytest verification;
- a fresh no-training second qualification batch after review.

Out of scope:

- GRID card ranking, cardinality policy, or purge policy;
- HAND_SELECT ordering, which already has a separate qualified fix;
- generic `ProceedAction` mapping;
- coordinator-wide callback correlation or persistent in-flight state;
- CommunicationMod Java changes;
- route, shop, event, reward, RL state, reward, training, or tuning behavior.

## Design

Shared action classes gain optional serialization controls while preserving
their current defaults:

```text
WaitAction(timeout=1, requires_game_ready=False, wait_for_response=False)
ClickAction(target, requires_game_ready=False, wait_for_response=False)
ChooseAction(choice_index=0, name=None, wait_for_response=False)
```

`OptionalCardSelectConfirmAction` gains explicit response-wait and
post-confirm-settle options. Existing callers retain fire-and-forget behavior
unless they opt in.

For each selected GRID card, `CardSelectAction.execute()` queues:

1. the available selector transport (`ClickAction`, `ChooseAction`, or
   `KeyAction`) with `requires_game_ready=True` and
   `wait_for_response=True`;
2. `WaitAction(timeout=1, requires_game_ready=True,
   wait_for_response=True)` as a FIFO settle barrier.

After all selectors, it queues one `OptionalCardSelectConfirmAction` with:

```text
allow_stale_selection=True
requires_game_ready=True
wait_for_response=True
settle_after_confirm=True
```

The optional action still checks the current screen, `confirm_up`, and
available commands before sending. When it sends confirm, it appends a waiting
one-frame settle action. A stale post-selection frame is consumed before the
first barrier response; a stale post-confirm frame is consumed before the
transition barrier response. While either barrier remains queued, coordinator
callbacks stay deferred. The first callback after the queue drains therefore
uses a post-command state.

HAND_SELECT retains its existing key and optional-confirm ordering. All event,
shop, reward, map, and generic click/wait callers retain their existing action
defaults.

## Failure Handling

- If a selector response is delayed, the queued barrier cannot run until a
  frame marks the game ready. Existing ready-wait polling requests state on a
  timeout.
- Once the barrier command is sent, `wait_for_response=True` prevents the
  terminal confirm from running before the barrier response.
- If the fresh state no longer exposes confirm or has changed screens, the
  optional confirm remains a no-op and the deferred callback resumes normally.
- If confirmation succeeds but an older GRID frame is pending, the transition
  barrier suppresses a callback on that frame and requests a post-confirm
  state one frame later.
- Existing command-availability guards remain the final legality boundary.

## Testing

1. Replace the old GRID non-blocking queue assertion with transport-neutral
   assertions that every selector waits for readiness and response, every
   selector is followed by a waiting one-frame barrier, and terminal confirm
   is serialized.
2. Cover `choose`, positioned `click`, and `key` fallback selector paths.
3. Preserve explicit tests that default `ChooseAction`, `ClickAction`, and
   `WaitAction` behavior remains unchanged outside GRID.
4. Add a parsed-state coordinator regression reproducing both live stale
   frames. Assert one selector, one low-level confirm, no GRID callback after
   either stale frame, and the next callback only after the post-confirm
   transition state.
5. Run focused action/coordinator/GRID tests, then full pytest.
6. Run strict OPSX validation and independent review before live evaluation.

## Rollout

Commit the regression-backed ordering fix as one cohesive behavior change.
Do not resume qualification until focused tests, full pytest, strict OPSX
validation, and independent review pass. Then run a fresh 25-game no-training
Batch 2 retry from a new cutoff. Stop on any A-class command rejection,
uncaught gameplay exception, or repeated high-confidence mechanics cluster.
Promotion remains prohibited until that complete batch is independently
reviewed clean, giving two consecutive eligible 25-game batches.
