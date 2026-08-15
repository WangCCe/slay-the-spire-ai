# Combat RL expert-dominant replication R3

## Decision

**Approve one fresh matched 20+20 zero-epsilon live gate against the exact entry checkpoint. Do not promote before that gate.** R3 cleanly realized the intended expert-dominant behavior distribution and improved replay diagnostics while remaining finite and operationally stable.

## Training result

- 25 games completed in 48 minutes with 4,245 accepted transitions.
- The retained replay contains 4,096 of 5,810 source transitions; 1,714 new transitions arrived after the learning threshold.
- Optimizer step advanced from 2,679 to 3,108; epsilon fell from `0.887444` to `0.832268`.
- Whole-model relative L2 drift was `1.814%`; all online and target tensors were finite.
- Outcomes totaled 528 floors, mean `21.12`: 12 Act 2 entries, 4 Act 2 boss reaches, and 1 Act 3 entry. No victory occurred.

On the candidate's retained replay, candidate versus entry:

| Metric | Entry | Candidate |
| --- | ---: | ---: |
| Smooth-L1 TD loss | 4.5434 | 3.7514 |
| Median absolute TD error | 1.5003 | 0.9681 |
| 95th-percentile absolute TD error | 9.7564 | 8.5385 |
| Median valid-action Q margin | 0.2620 | 0.3853 |
| 5th-percentile Q margin | 0.0215 | 0.0288 |
| Executed-action greedy share | 33.96% | 30.86% |

Entry and candidate greedy actions agree on `53.05%` of retained replay states. Advantage-stream drift reached `14.73%`, so replay gains alone are not promotion evidence.

## Expert-action evidence

Retained logs cover `11:43:48` through completion, approximately the latter 22 of 25 games. They contain 2,231 successful expert selections, 926 probability skips, 2 mask rejections, and no failed or unencodable expert actions. Successful expert use was `70.62%`, above the preregistered 67% floor.

Both rejections targeted raw `monster_index=6`, beyond schema-2's five raw monster slots. No stale-target or no-longer-playable cached-card rejection remained.

## Integrity

- Exactly 25 markers and 25 matching run records were captured.
- No replay rejection, RL-agent failure, episode-close failure, checkpoint-save failure, or non-finite tensor was observed.
- CommunicationMod error-log growth was 557 bytes of expected launch messages.
- Original configuration and process state were restored.

## Next step

Use a new fixed 20-seed pool and evaluate R3 and the exact entry at epsilon zero. Require paired wins, total floors, and progression breadth to justify promotion; a tie or regression keeps the entry checkpoint.
