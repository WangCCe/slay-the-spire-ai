## Why

The failed second baseline-qualification batch contains a live A-class GRID
command-legality failure: one stale selection frame caused a duplicate card
selection, and one stale post-confirm frame caused `ProceedAction` to emit a
second `confirm` after the purge screen had closed. The failure must be fixed
before another 25-game no-training qualification batch can count toward
promotion.

## What Changes

- Serialize GRID `choose`, `click`, and `key` selector transports and place a
  one-frame CommunicationMod FIFO settle barrier after each selection.
- Serialize the optional GRID confirm and place a one-frame transition barrier
  after a sent confirm so stale GRID frames cannot trigger a second callback.
- Preserve the default behavior of shared action classes outside GRID and keep
  HAND_SELECT's already-qualified ordering unchanged.
- Add action-contract and parsed-state coordinator regressions for the exact
  stale-selection and stale-confirm sequence.
- Require focused pytest, full pytest, strict OpenSpec validation, independent
  review, and a fresh 25-game no-training Batch 2 retry before promotion.
- Success metric: the regression emits exactly one selector and one low-level
  confirm, and the fresh retry has zero invalid commands, uncaught gameplay
  exceptions, GRID cardinality failures, or demonstrated A-class mechanics
  clusters.
- Non-goals: no card-ranking, shop, event, route, reward, combat policy, RL
  state/action/reward, training, tuning, CommunicationMod Java, or generic
  coordinator callback-state changes.
- Rollback boundary: revert the GRID-specific serialization arguments and
  settle barriers as one behavior commit; optional action parameters retain
  backward-compatible defaults so unrelated callers do not require rollback.

## Capabilities

### New Capabilities

- `grid-card-selection-protocol`: Defines ordered GRID selector and confirm
  execution across stale CommunicationMod state frames.

### Modified Capabilities

None.

## Impact

- Affected Python code: `spirecomm/communication/action.py` only for behavior;
  coordinator code is exercised but does not gain persistent state.
- Affected tests: GRID action queue contracts and deferred parsed-state
  callback integration tests.
- Runtime impact: one CommunicationMod frame after each GRID selector and one
  after a sent GRID confirm; no new dependency or public breaking change.
- Operational impact: qualification remains blocked at one consecutive clean
  batch until the fix is independently reviewed and the complete Batch 2 retry
  passes.
