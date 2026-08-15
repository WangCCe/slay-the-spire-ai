# Combat RL expert-dominant replication R2

## Decision

**Do not give this checkpoint a live gate.** The 25-game batch completed cleanly and its replay diagnostics improved over the entry checkpoint, but the available latter-run logs contain 356 rejected expert `PlayCardAction` values. R2 therefore did not realize the intended expert-dominant behavior distribution.

## Training result

- 25 games completed in 44 minutes with 3,481 accepted transitions.
- Optimizer step advanced from 2,679 to 2,917; epsilon fell from `0.887444` to `0.839526`.
- Whole-model relative L2 drift was `1.251%`; all online and target tensors were finite.
- Outcomes totaled 509 floors, mean `20.36`: 9 Act 2 entries, 4 Act 2 boss reaches, and 1 Act 3 entry. No victory occurred.

On the candidate's retained replay, Smooth-L1 loss fell from `5.1685` to `4.6645`, median absolute TD error fell from `1.5430` to `1.0992`, and median valid-action margin rose from `0.2494` to `0.2818`. The 5th-percentile margin was essentially flat (`0.0211` to `0.0210`).

## Expert-action evidence

Log rotation retained `10:06:44` through batch completion, covering the latter roughly 21 of 25 games. In that window there were 1,298 successful expert selections, 689 probability skips, and 356 mask rejections; no expert call failed or was unencodable. The attempted expert share was `70.59%`, but only `55.40%` of observed source events successfully used the expert.

Context showed that UUID card relocation exposed stale target metadata on cached actions: current non-target cards were encoded into target slots and rejected by the action mask. Commit `d957a595d66636a6b6e68cc7a3c458012c284f8b` normalizes non-target cards to target slot zero and adds failure-only diagnostic fields.

## Integrity

- Exactly 25 markers and 25 matching run records were captured.
- The final schema-2 checkpoint round-tripped with replay and optimizer state.
- No replay rejection, RL-agent failure, episode-close failure, checkpoint-save failure, or non-finite tensor was observed.
- CommunicationMod error-log growth was 557 bytes of expected launch messages.
- The original CommunicationMod configuration was restored and all game/Python processes were closed.

## Next step

Use the five-game target-normalization smoke to validate the repair. Do not reuse R2 as a promotion candidate.
