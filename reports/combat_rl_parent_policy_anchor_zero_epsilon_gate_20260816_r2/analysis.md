# Combat RL parent-policy anchor zero-epsilon gate R2

## Decision

**Reject this gate for execution integrity. Do not start the parent arm and do
not retry this gate. Retain the promoted parent.**

## Candidate arm

The candidate completed 12 of 20 registered seeds. The completed floors were:

```text
16, 16, 16, 33, 29, 16, 16, 33, 28, 20, 33, 16
```

- Total floors: `272`
- Mean floor: `22.67`
- Median floor: `18`
- Act 2 entries: `6`
- Act 2 boss reaches: `3`
- Victories: `0`
- All 12 completed games produced run records.
- No long-combat guard activation occurred in the completed games.

These partial-arm metrics have no matched comparison or promotion authority.

## Integrity failure

The thirteenth seed, `2E047E2F7E9C4`, reached the map after floor 5 but did not
produce a run record. At `15:32:36`, a `ChooseMapNodeAction` remained queued on
`ScreenType.MAP` while CommunicationMod repeatedly reported
`game_is_ready=false`. The coordinator requested state every two seconds, but
the queue did not drain and no floor transition occurred through the stop at
approximately `15:35:41`.

The CommunicationMod error log did not grow after the arm's normal startup
records. Python and Java processes remained alive, and the AI log continued to
receive state updates. This is a live map-action liveness failure, not a model
load error or process crash.

Two screenshot attempts were not usable: the game window was covered by the
foreground Codex window, and both the matched-window and all-screens captures
contained Codex rather than game pixels. No visual claim is made.

## Gate handling

The preregistration requires a started arm failure to stop the gate. The
candidate arm was stopped without changing seeds, parameters, or checkpoints;
the parent arm was not started. The production CommunicationMod configuration
was restored to SHA-256
`d4d1dd35fd53985796922e5915a8b4ab51373109d08addff2bdcdfebf01a00e4`.
The three verified gate process IDs were terminated individually and no gate
process was left running.

The next task is a narrow regression and liveness repair for a queued map action
that remains blocked while `game_is_ready=false`. A later evaluation must use a
new gate registration and new seed pool.

