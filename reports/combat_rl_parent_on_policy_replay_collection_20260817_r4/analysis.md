# Fourth Parent On-Policy Replay Collection

## Decision

Accept r4 as complete fresh replay evidence and advance the frozen r7
single-step SGD candidate to a bounded matched live gate. This is not promotion
authority and the production checkpoint remains unchanged.

## Collection

All 20 registered seed indices ran in order and completed naturally. The parent
policy produced 4,576 transitions with no optimizer state, optimizer steps,
training losses, expert actions, invalid actions, RL failures, tracebacks, or
post-start CommunicationMod error growth. Online and target tensors remained
exactly equal to the promoted parent.

The cohort reached 498 total floors: 12 Act 2 entries, seven Act 2 Boss reaches,
and one Act 3 run that died to Donu and Deca on floor 50. There were no wins.

## Replay Integrity

The terminal checkpoint's 4,096-transition serialization limit omitted the
first 480 of 4,576 source transitions. The complete replay was reconstructed
from the untruncated `ep16_steps4000` prefix and terminal suffix. Their 3,520
overlapping transitions matched exactly across all 13 replay tensor fields;
576 terminal rows were appended to produce an untruncated 4,576-row artifact.

## Candidate Confirmation

On the complete untouched r4 replay:

| Metric | Parent | Candidate |
| --- | ---: | ---: |
| one-step SmoothL1 | 3.609213 | 3.604594 |
| parent action agreement | 1.000000 | 0.999126 |
| off-target disagreement | 0.000000 | 0.001654 |
| positive-energy EndTurn share | 0.631579 | 0.631579 |

The candidate improves the registered outcome metric while changing only four
off-target decisions in 4,576 states. Its relative L2 distance from the parent
is `1.4983e-6`. All frozen replay gate conditions passed.

## Next Step

Run a small matched live gate using a new seed pool, with the frozen candidate
and promoted parent on identical seeds. Keep the production configuration on
the parent until the paired floor/depth and runtime checks pass; do not retune
the candidate using r4.
