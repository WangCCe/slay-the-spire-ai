# Combat RL expert-dominant replication R1

## Decision

**Do not give this checkpoint a live gate. Repeat the same training recipe after the expert-action UUID relocation fix.** The batch completed successfully and produced encouraging replay metrics, but 39 intended expert actions were rejected because stale `card_index` values overrode resolvable card UUIDs.

## Training result

- 25 games completed in 47 minutes with 3,811 accepted transitions.
- The retained replay contains 4,096 of 5,376 source transitions; 1,280 new transitions arrived after the learning threshold.
- Optimizer step advanced from 2,679 to 3,000, and epsilon fell from `0.887444` to `0.836372`.
- All online and target tensors are finite. Whole-model relative L2 drift from entry is `1.562%`.
- Training outcomes totaled 516 floors, mean `20.64`, with 9 Act 2 entries and 4 Act 2 boss reaches. No run reached Act 3 or victory.

## Replay evidence

On the candidate's retained replay, candidate versus entry:

| Metric | Entry | Candidate |
| --- | ---: | ---: |
| Smooth-L1 TD loss | 4.8591 | 4.1980 |
| Median absolute TD error | 1.5864 | 1.1135 |
| 95th-percentile absolute TD error | 11.1887 | 10.3054 |
| Median valid-action Q margin | 0.2472 | 0.4036 |
| 5th-percentile Q margin | 0.0199 | 0.0341 |
| Executed-action greedy share | 37.04% | 32.84% |

Entry and candidate greedy actions agree on `57.15%` of replay states. The larger margin and lower TD errors are encouraging, but the candidate drifted more than R1-R3, especially in the advantage stream (`12.23%`).

## Expert-action defect

The training log contains 314 expert-source decisions: 170 successful expert selections, 105 probability skips, and 39 mask rejections. Every failure was `Expert action masked out` for a `PlayCardAction`; no expert call failed or was unencodable.

The encoder trusted `PlayCardAction.card_index` before looking up the attached card UUID in the current hand. When heuristic planning changed hand position, a stale index encoded a different card slot and failed the current action mask. Focused regression reproduced `slot 0` instead of the UUID-bound `slot 1`. Commit `f7d31c3a96f271b48153f1f8690320a4bfdc868e` now relocates UUID-bound cards before considering the explicit index; the complete RL v2 action-space test file passes (`40 passed`).

The attempted expert share was `67%`, close to the configured 70%, but only `54%` of source events successfully used the expert. Because rejected expert actions fell back to epsilon-greedy behavior, this batch did not cleanly realize the intended behavior distribution.

## Integrity

- Exactly 25 new AI markers and 25 matching run records were captured.
- The final checkpoint round-tripped with schema-2 training state, replay, optimizer, episode, epsilon, and total steps.
- No replay rejection, episode-close failure, checkpoint-save failure, RL failure, NaN, or non-finite tensor was observed.
- CommunicationMod error-log growth was 557 bytes of expected wrapper/dependency messages.
- CommunicationMod configuration was restored to SHA-256 `b42093ae...03c1`, and no related Python or game process remained after the batch.

## Next step

Run one fresh 25-game R2 from the same entry checkpoint with the same `expert_mix_prob=0.70` and no other parameter changes, now including the UUID relocation fix. Require zero UUID/index-related expert mask rejections before considering a fresh matched live gate.
