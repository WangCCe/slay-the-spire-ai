# Combat RL parent-policy anchor zero-epsilon gate R3

## Decision

**Reject this gate for execution integrity. Do not start the parent arm and do
not retry this gate. Retain the promoted parent.**

## Candidate arm

The candidate produced six run records from the first six registered seeds
before terminalization failed on game 6. Their floors were:

```text
16, 24, 16, 21, 28, 16
```

- Total floors: `121`
- Mean floor: `20.17`
- Median floor: `18.5`
- Act 2 entries: `3`
- Act 2 boss reaches: `0`
- Victories: `0`

These partial-arm metrics have no matched comparison or promotion authority.

## Integrity failure

The sixth seed, `32E285F92FD74`, reached `GAME_OVER` on floor 16 after dying to
The Guardian. The run record was written, but after `ProceedAction` sent
`proceed`, CommunicationMod reported `game_is_ready=false` while still exposing
`proceed`, `wait`, and `state`. The queued ready-required `WaitAction` could not
execute. State polls produced no transition, and the coordinator stopped the
batch after ten timeouts at `16:05:38`.

The failure is a terminal-screen liveness defect, not a model load or disk-space
error. The CommunicationMod error log did not grow beyond startup output, and C:
had `52.72 GB` free during postmortem.

## Gate handling

The preregistration requires a started arm failure to stop the gate. The parent
arm was not started, and the candidate was not resumed. The verified Slay the
Spire process was stopped individually. The production CommunicationMod
configuration was restored to SHA-256
`d4d1dd35fd53985796922e5915a8b4ab51373109d08addff2bdcdfebf01a00e4`.

The next task is a narrow regression and repair that lets the post-`proceed`
wait execute on `GAME_OVER` while `game_is_ready=false`. A later matched
evaluation must use a new registration and a fresh seed pool.
