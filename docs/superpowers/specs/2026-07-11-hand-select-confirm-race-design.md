# HAND_SELECT Confirm Race Design

## Status

Approved under the user's standing authorization on 2026-07-11 after the
first qualification retry exposed an A-class command-legality failure.

## Problem

At 2026-07-11 20:38:53 CST, a hand-selection action queued two card-key
commands followed by `OptionalCardSelectConfirmAction`. Each key command waited
for a CommunicationMod response, but the optional confirm did not require the
game to be ready. The coordinator therefore sent `confirm` immediately after
the final key command and before that key's response arrived.

The final key response still described `HAND_SELECT` with `confirm` available.
Because the action queue was empty, that stale response triggered a second
agent callback. The fallback returned `ProceedAction`, which emitted a second
`confirm` after the first confirm had already closed the screen. CommunicationMod
rejected the duplicate command because the live commands were then
`[end, key, click, wait, state]`.

The same ordering also causes benign stale callbacks in successful Gambler's
Brew selections. Those callbacks can enqueue extra card keys after the hand
selection has already closed, even when they happen not to produce an error.

## Root Cause

`CardSelectAction` already serializes HAND_SELECT card keys:

```text
KeyAction(requires_game_ready=True, wait_for_response=True)
```

However, commit `ae01dcd0` removed the ready requirement from the terminal
optional confirm. This permits the final two commands to overlap:

```text
send final key
send confirm before final-key response
receive stale final-key HAND_SELECT response
run agent callback again
```

The agent's later `ProceedAction` is not the source of the first duplicate. It
is a consequence of the stale callback created by the overlapping commands.

## Approaches Considered

### 1. Serialize the HAND_SELECT confirm after the final key response

Set the terminal `OptionalCardSelectConfirmAction` to require game readiness
for HAND_SELECT only. GRID retains its current behavior.

Advantages:

- fixes the command ordering at its source;
- restores one outstanding state-changing command at a time;
- matches successful single-card HAND_SELECT traces;
- changes one action-queue contract without adding persistent state.

Risk:

- if a HAND_SELECT key produces no response, confirmation waits for the
  coordinator's existing ready-wait state poll rather than firing immediately.

This is the selected approach.

### 2. Add a coordinator-level confirm-in-flight state machine

Suppress callbacks while a card-selection confirm remains in flight.

This can defend against more races, but it adds new lifecycle state and screen
transition rules to shared coordinator code. The observed race does not require
that broader change.

### 3. Make stale HAND_SELECT callbacks request state

Return `StateAction` instead of `ProceedAction` when no cards remain or confirm
is not legal.

This avoids the observed rejected command but does not prevent the stale
callback, overlapping confirm, or extra post-close key actions. It treats a
downstream symptom rather than the ordering defect.

## Scope

In scope:

- HAND_SELECT `CardSelectAction` queue ordering;
- the ready requirement of the terminal optional confirm;
- action-level and coordinator-level regressions for the live race;
- focused and full pytest verification;
- a fresh no-training qualification retry.

Out of scope:

- GRID confirmation behavior;
- HAND_SELECT card ranking or selection cardinality policy;
- `ProceedAction` command mapping;
- generic coordinator callback suppression;
- RL state, action, reward, or training behavior;
- route, shop, event, or reward policy.

## Design

When `CardSelectAction.execute()` builds a HAND_SELECT sequence, it queues:

1. one `KeyAction` per selected card, each requiring ready and waiting for a
   response;
2. one `OptionalCardSelectConfirmAction` with
   `requires_game_ready=True` and `allow_stale_selection=True`.

For GRID, the optional confirm continues to use
`requires_game_ready=False` because GRID choices have separate response and
fallback behavior.

After the final HAND_SELECT key is sent, the optional confirm remains queued
and cannot execute. The final-key state response marks the game ready while the
queue is non-empty, so the coordinator defers the agent callback. It then
executes exactly one optional confirm against the updated state. Sending that
confirm changes the deferred callback message count, preventing the deferred
callback from running against the key response. The next callback comes from
the post-confirm state.

No new coordinator flag or action type is introduced.

## Failure Handling

- If the final key response is delayed, the existing ready-wait state poll
  requests a fresh state.
- If the updated state no longer exposes `confirm`, the optional action remains
  a no-op and the deferred callback can run normally.
- If the screen changes before confirmation, the existing optional-confirm
  screen guard skips the command.
- Existing command-availability checks remain the final legality boundary.

## Testing

1. Update the queue-contract test to require readiness for the HAND_SELECT
   optional confirm while preserving ready waits on every key.
2. Add a coordinator regression that reproduces the live sequence: two queued
   keys, a state response after the first key, and a stale HAND_SELECT response
   after the final key. Assert that no confirm is emitted before the final-key
   response, exactly one confirm is emitted afterward, and no agent callback is
   invoked from that response.
3. Preserve GRID tests proving its optional confirm remains non-blocking.
4. Run focused action/coordinator/HAND_SELECT tests, then full pytest.
5. Run strict OPSX validation and independent review before live evaluation.

## Rollout

Commit the regression-backed behavior fix as one cohesive change. Restart
Batch 1 from a new cutoff only after focused tests, full pytest, strict OPSX
validation, and independent review pass. Stop the retry on any new A-class
command-legality or uncaught gameplay failure; do not start Batch 2 until one
complete 25-game Batch 1 is clean.
