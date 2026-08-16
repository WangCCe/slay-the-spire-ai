# Ready-false map choice recovery r1

## Scope

- Source commit: `1289c9fff`
- Seed: `2E047E2F7E9C4`
- Mode: evaluation, epsilon `0.0`, one game, no training
- Checkpoint: anchored candidate
  `reports/combat_rl_parent_policy_anchor_smoke_20260815_r1/rl_combat_model_ep60_steps22620.pth`
- Launch config SHA-256:
  `fb6518a01aaf36f68e1ca72d74827dd15788044208fa53390f92e476acbcf296`

## Result

The same-seed liveness recovery passed. The run crossed the previous floor 5
map-stall boundary, continued to floor 31, reached a normal `GAME_OVER`, wrote a
new AI marker, and exited after the configured single game.

- AI marker count: `16001 -> 16002`
- Run record: `1786866527.run`
- Run record SHA-256:
  `97e0de81c638db5fc78101ac4d6cf1dad274ef213e3c1423b4753c4994c6213a`
- Floor reached: `31`
- Victory: `false`
- Killed by: `Centurion and Healer`
- Playtime: `164` seconds

The live run did not reproduce the exact ready-false timing. At the floor 5 map
choice, `game_is_ready=true`, the `ChooseMapNodeAction` drained normally, and
the next screen was the rest site. Therefore this run establishes same-seed
liveness recovery but does not independently exercise the new ready-false
branch.

The exact branch is covered by regressions:

- Ready-false MAP with `choose` available executes and drains the action.
- Ready-false MAP without `choose` remains queued.
- The existing ready-false EVENT behavior remains unchanged.
- Focused boundary result: `3 passed`.
- Deferred-state callback file: `28 passed`.

## Cleanup

The CommunicationMod error log grew only during normal batch startup and did
not grow during the run. The production config was restored to SHA-256
`d4d1dd35fd53985796922e5915a8b4ab51373109d08addff2bdcdfebf01a00e4`,
and the verified game process was stopped.

This recovery does not reopen the failed R2 matched gate and grants no model
promotion authority. Any later candidate-parent comparison requires a new seed
pool and registration.

