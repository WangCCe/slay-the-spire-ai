## Why

The independent r3 LightSTS training replication kept held-out reward and HP deltas positive, but its only two candidate non-victories were high-HP `CARD_SELECT` exclusions on seeds `50252` and `50254`. The same boundary also excluded 27 training trajectories, so repeating training before resolving it would spend compute on censored outcomes rather than improve the policy evidence.

## What Changes

- Settle natively enumerable combat `CARD_SELECT` states through a deterministic, bounded auxiliary LightSTS policy after an RL-visible combat action.
- Record settlement count and task identity so reports can distinguish auxiliary resolution from an ordinary player-normal successor.
- Leave unenumerable, unimplemented, or over-bound card-selection states explicitly unsupported.
- Keep the RL v2 133-action contract unchanged; card selection remains outside the learned combat action surface.
- Build and validate the changed adapter in a new immutable native build directory, preserving the existing v1 module and reports.
- Run one new-cohort simulator replication only after focused settlement, clone-isolation, and unsupported-boundary regressions pass.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-lightspeed-bridge`: Add bounded deterministic settlement and auditable evidence for enumerable native combat card-selection states.

## Impact

The change affects `simulator_adapters/sts_lightspeed/combat_adapter.cpp`, the Python combat bridge, focused native tests, and simulator-only reports. It does not start Slay the Spire or CommunicationMod, alter production checkpoints, expand the RL action space, or claim simulator/game equivalence. Success requires deterministic successor equality across clones, preserved unsupported behavior for unsafe tasks, zero `CARD_SELECT` exclusions on a fresh bounded replication, and source-bound report artifacts. Rollback is selecting the prior immutable v1 module and reverting this adapter-only change; no production state needs migration.
