# Long-combat guard recovery r2

## Scope

- Source commit: `27766ff26061b9e2ae59abbd6016d489b1d48b3b`
- Seed: `0TP19MYO9CPA8`
- Mode: evaluation, epsilon `0.0`, one game, no training
- Checkpoint: `reports/combat_rl_parent_policy_anchor_smoke_20260815_r1/rl_combat_model_ep60_steps22620.pth`
- Checkpoint SHA-256: `8a60f45d2c1e5e32b2c1c95f8799cae99144d8fd4a070386e32a9be1e5b12b7d`
- Launch config: `reports/combat_rl_long_combat_guard_recovery_20260815_r1_launch_config.properties`
- Launch config SHA-256: `80d95673888f3987689915ec149fd7e62dcb42101241b29808c014900a532bfa`

## Result

The liveness recovery passed. The previously non-terminating Spheric Guardian
combat entered the long-combat guard at floor 19 turn 40. The guard emitted an
available attack on every turn from 41 through 47. The game then reached the
normal `GAME_OVER` path, wrote a new AI marker, and exited after its configured
single game.

- AI marker count: `15988 -> 15989`
- AI marker: `1786863147`
- Run record: `1786863143.run`
- Run record SHA-256: `bb7126130b5ae45ea3a2a7a245af3c32e4680c23ee2a91adc6d5f611f0c3f0b4`
- Floor reached: `19`
- Spheric Guardian combat turns: `47`
- Victory: `false`
- Killed by: `Spheric Guardian`
- RL failure count remained `0` before guard takeover.

Key timeline:

```text
14:52:10.154 turn=40 Bypassing RL
14:52:12.719 turn=41 Playing available attack
14:52:14.347 turn=42 Playing available attack
14:52:15.836 turn=43 Playing available attack
14:52:17.430 turn=44 Playing available attack
14:52:19.039 turn=45 Playing available attack
14:52:20.560 turn=46 Playing available attack
14:52:22.007 turn=47 Playing available attack
14:52:23.281 GAME_OVER current_hp=0/80
14:52:27.314 Max games reached (1); exiting
```

This is a liveness result only. It does not establish policy improvement,
qualification, promotion, or victory: the accumulated block was not removed
before the player died.

## Verification and cleanup

- Focused boundary regressions: `3 passed`
- Combat guard file: `174 passed in 4.95s`
- The first file run produced `173 passed, 1 error` because the pytest temp
  parent had been removed. After explicitly recreating the established system
  temp parent, the single permitted fresh-child rerun passed.
- CommunicationMod error-log growth contained batch bootstrap records and no
  new traceback in the inspected tail.
- Production config was restored to SHA-256
  `d4d1dd35fd53985796922e5915a8b4ab51373109d08addff2bdcdfebf01a00e4`.
- No Python or Java process remained after the run.

