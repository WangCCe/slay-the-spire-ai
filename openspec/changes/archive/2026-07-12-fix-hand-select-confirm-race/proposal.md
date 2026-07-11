## Why

The first qualification retry produced a fresh A-class command-legality
failure: HAND_SELECT sent `confirm` before the final card-key response, then a
stale HAND_SELECT callback emitted a duplicate `confirm` after the screen had
closed. CommunicationMod rejected the duplicate command, so baseline
qualification cannot continue on the current action ordering.

## What Changes

- Serialize the terminal HAND_SELECT confirmation after the final card-key
  response.
- Keep GRID confirmation timing unchanged.
- Add action-queue and coordinator regressions for the observed stale-response
  sequence.
- Preserve existing card ranking, cardinality, command mapping, coordinator
  callback policy, RL, and non-combat decision behavior.
- Restart the conservative no-training Batch 1 qualification from a fresh
  cutoff only after focused, full-suite, strict OPSX, and independent review
  gates pass.

Success means HAND_SELECT emits no confirmation before the final key response,
emits at most one legal confirmation afterward, and does not invoke an agent
callback from the stale final-key response. The fresh qualification retry must
contain zero invalid commands attributable to this race.

Non-goals are a generic coordinator in-flight state machine, changes to GRID,
HAND_SELECT policy retuning, `ProceedAction` remapping, RL training, and route,
shop, event, or reward changes.

The rollback boundary is one cohesive HAND_SELECT queue-ordering commit. Both
failed qualification reports remain unchanged audit evidence except for
reviewed factual corrections.

## Capabilities

### New Capabilities

- `hand-select-action-sequencing`: Ordered card-key and terminal-confirm
  execution for CommunicationMod HAND_SELECT screens.

### Modified Capabilities

None.

## Impact

- Affected code: `spirecomm/communication/action.py` HAND_SELECT action queue
  construction.
- Affected tests: card-select confirmation guards and coordinator deferred
  callback sequencing.
- Live validation: a new Batch 1 retry report, fresh `.run` records,
  `ai_debug.log`, `communication_mod_errors.log`, and decision/sim-divergence
  traces.
- No public API, dependency, configuration, model, reward, training, or policy
  change.
