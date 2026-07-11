## Context

The 2026-07-11 Batch 2 qualification attempt produced one live rejected
`confirm` during a shop purge GRID. GRID selection commands are currently
fire-and-forget. A pre-selection frame drained the queue and caused the same
card to be selected twice; a later pre-transition frame caused generic
`ProceedAction` handling to emit a second confirm after the first confirm had
closed the screen.

CommunicationMod consumes a FIFO command queue, executes at most one command
per pre-update, and makes `wait 1` publish a state after one frame. The Python
coordinator already defers callbacks while actions remain queued and polls
state while a ready-required action is blocked. Production gameplay must keep
using the Windows Python environment, and the fix must not change policy or
start training.

## Goals / Non-Goals

**Goals:**

- Establish a post-selector state boundary before GRID confirmation.
- Establish a post-confirm transition boundary before another agent callback.
- Cover `choose`, positioned `click`, and `key` GRID selector transports.
- Preserve shared action defaults outside GRID and preserve HAND_SELECT
  ordering.
- Prove the exact stale-frame sequence with a parsed-state coordinator test.

**Non-Goals:**

- Change GRID card ranking, cardinality, purge, shop, route, event, reward, or
  combat policy.
- Change generic coordinator callback correlation or `ProceedAction` mapping.
- Change CommunicationMod Java code.
- Change RL spaces, rewards, checkpoints, training, or tuning.

## Decisions

### Use one-frame FIFO settle barriers

Each GRID selector will require readiness, send with response waiting enabled,
and be followed by `WaitAction(timeout=1)` that also requires readiness and
waits for its response. The wait command is queued after the selector in
CommunicationMod, so its response is ordered after the selector even when the
Python input queue already contains an older frame.

The optional GRID confirm will require readiness and wait for a response. When
it sends confirm, it will append the same waiting one-frame action. A stale
post-confirm GRID frame therefore services the queued barrier instead of
invoking the agent; the barrier response supplies the post-confirm state.

This is preferred over a coordinator in-flight state machine because it fixes
the demonstrated ordering defect without persistent shared state or reset
rules. It is preferred over an agent-side `ProceedAction` guard because that
guard would leave duplicate card selection intact.

### Add backward-compatible action options

`WaitAction` will accept optional `requires_game_ready` and
`wait_for_response` arguments. `ClickAction` will accept the same arguments,
and `ChooseAction` will accept optional `wait_for_response`. All defaults will
match current behavior. `OptionalCardSelectConfirmAction` will accept explicit
response-wait and post-confirm-settle options, also disabled by default.

Only the GRID branch in `CardSelectAction` opts into these controls. No public
caller is forced to change.

### Keep coordinator behavior unchanged

The existing queue and deferred-callback rules are sufficient once a barrier
stays queued across each ordering boundary. The coordinator will be exercised
by the integration regression but will not gain a GRID fingerprint, in-flight
flag, or new callback special case.

## Risks / Trade-offs

- [One extra frame per GRID selector and confirm] -> Keep barriers at exactly
  one frame and restrict them to GRID card selection.
- [A selector never produces a normal response] -> The barrier remains
  ready-blocked and existing coordinator state polling requests a fresh state.
- [Shared action defaults regress unrelated screens] -> Add explicit default
  contract tests and pass serialization arguments only from GRID.
- [A stale frame still appears after confirm] -> Keep a post-confirm barrier in
  the action queue and reproduce that exact frame in the coordinator test.
- [The fix masks a policy issue] -> Do not change card choice or
  `ProceedAction`; validate only command count, order, and legality.

## Migration Plan

1. Add red action-contract and parsed-state race regressions.
2. Implement the optional action parameters and GRID-only queue ordering.
3. Run focused tests, full pytest, strict OpenSpec validation, and independent
   review.
4. Run a fresh 25-game no-training Batch 2 retry from a new cutoff.
5. Promote only if the complete retry is independently reviewed clean and the
   existing Batch 1 remains eligible.

Rollback is one cohesive behavior commit: remove the GRID serialization
arguments and barriers. Backward-compatible defaults mean unrelated callers
do not require migration or rollback edits.

## Open Questions

None. The live trace, Python queue behavior, and local CommunicationMod FIFO
implementation provide enough evidence for the bounded fix.
