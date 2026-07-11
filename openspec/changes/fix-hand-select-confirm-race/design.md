## Context

The failed Batch 1 retry captured a two-card HAND_SELECT sequence in which the
terminal optional confirm executed before the last key response. That response
then triggered a second callback and duplicate confirm. The queue already
serializes every HAND_SELECT key with `requires_game_ready=True` and
`wait_for_response=True`; only the terminal confirm bypasses that boundary.

CommunicationMod remains the command-legality authority. Production gameplay
uses Windows Python, and validation must use fresh run records plus the active
and rotated logs and traces.

## Goals / Non-Goals

**Goals:**

- keep at most one HAND_SELECT state-changing command awaiting its response;
- execute the terminal confirm only after the final key response;
- prevent a stale final-key response from causing a second agent callback or
  duplicate confirm;
- preserve GRID behavior and all selection policies.

**Non-Goals:**

- adding generic coordinator in-flight state;
- changing GRID timing, card ranking, cardinality, `ProceedAction`, RL, or
  non-combat policy;
- changing CommunicationMod or production configuration.

## Decisions

### Require ready for the terminal HAND_SELECT confirm

`CardSelectAction` will construct its optional confirm with
`requires_game_ready=True` for HAND_SELECT and retain `False` for GRID. The
final key response therefore arrives while the confirm remains queued. The
coordinator defers the callback, executes one confirm against the updated
state, and invalidates that deferred callback through its existing sent-message
counter.

This restores the ordering removed by `ae01dcd0` without changing shared
coordinator state. Current ready-wait state polling handles a delayed key
response.

### Keep optional command checks as the legality boundary

The optional action still checks screen type, available commands, and confirm
state at execution. If the screen changed or confirm disappeared, it remains a
no-op and normal callback processing resumes.

### Test the real interleaving

The coordinator regression will model two keys and the state response between
the final key and confirm. It will assert that no early confirm or callback is
possible, then that exactly one confirm is sent after readiness. Existing GRID
tests will prove its non-blocking contract remains unchanged.

## Risks / Trade-offs

- [A HAND_SELECT key sends no response] -> Existing ready-wait polling requests
  fresh state; live qualification checks for a new stall.
- [A historical reason for `ae01dcd0` recurs] -> Focused tests plus a fresh
  25-game retry cover multiple hand-selection sources before promotion.
- [The fix masks a broader callback race] -> Scope remains at the proven
  ordering defect; a coordinator state machine requires separate repeated
  evidence.

## Migration Plan

1. Add the failing interleaving regression and update the queue contract.
2. Restore HAND_SELECT-only ready serialization.
3. Run focused tests, full pytest, strict OPSX validation, and independent
   review.
4. Run a fresh conservative 25-game no-training retry from a new cutoff.

Rollback is the single behavior commit. Failed qualification reports remain
preserved as audit evidence.

## Open Questions

None. The live trace, current queue contract, and CommunicationMod command
availability establish the required ordering.
