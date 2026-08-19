## Why

The card-only ranking guard improved guard-aware reward and HP but failed material and victory gates, while its in-batch ranking violations increased. It also leaves the key deployment boundary unprotected: a frozen-parent raw EndTurn can be valuable because the production wrapper replaces it with a strong fallback, but a candidate card action bypasses that guard.

## What Changes

- Add an optional frozen-parent top-legal-action margin guard, disabled by default.
- Preserve a clipped positive margin between the parent's raw best legal action and its best legal alternative, regardless of whether that action is EndTurn, a card, or a potion.
- Bind loss, eligibility, violation, weight, and cap evidence in simulator reports and checkpoints.
- Run one preregistered fresh training/evaluation cohort with guard-aware evaluation and compare the candidate against r16 plus prior guarded candidates.
- Success means materially positive guard-aware reward and HP with non-worse victory splits and stable battle strata. Rollback is weight `0.0`; production r16 remains unchanged.

## Capabilities

### New Capabilities

- `combat-lightspeed-parent-top-action-margin-guard`: Defines the optional frozen-parent top-legal-action margin constraint and fresh simulator gate.

### Modified Capabilities


## Impact

- Affects RL v2 trainer, LightSTS smoke configuration/report/checkpoint binding, and focused tests.
- Adds no runtime dependency, action mapping, native adapter, CommunicationMod, or production behavior change.
- No packaging or gameplay is authorized by this change.
