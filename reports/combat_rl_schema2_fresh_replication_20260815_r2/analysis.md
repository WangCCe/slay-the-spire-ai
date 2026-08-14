# Combat RL Schema-2 Fresh Replication R2

## Result

The fresh 25-game replicate completed normally from the frozen schema-2 entry
checkpoint. It collected 3,640 accepted transitions and performed 278 Adam
updates after replay crossed 4,096 rows. The final checkpoint is finite and has
1.28% whole-model relative L2 drift from entry.

This is a viable candidate for a fresh matched zero-epsilon gate. It is not
promoted, and its exploratory training outcomes are not policy-quality evidence.

## Training

- Accepted transitions: `3,640` (`13,413 -> 17,053`)
- Replay at exit: newest `4,096` of `5,205` in-memory transitions
- Adam step: `2,679 -> 2,957` (+278)
- Epsilon: `0.887444 -> 0.838006`
- Episode: `15 -> 40`, aligned with `ep40_steps17053`
- Relative L2 drift: embeddings 0.25%, hidden 6.45%, value 4.56%, advantage
  9.62%, unused output layer 0%
- Target-to-online relative L2: 1.20%

Learning began at accepted step `15,944`. The target synchronized at step
`16,000` after 15 updates. Logged episode-average loss then moved
`5.4703 -> 5.1063 -> 5.0092 -> 4.8875 -> 4.4852`.

## Replication

On R2's retained replay, the frozen entry policy had Smooth-L1 TD loss `5.0104`,
R1 had `4.6353`, and R2 had `4.4975`. R1 and R2 greedy action indices agreed on
`76.44%` of R2 replay states; each agreed with entry on about `55%`.

R1 and R2 therefore learned a materially shared policy direction from
independent live replay, while retaining enough disagreement that a gameplay
gate is still required.

## Gameplay

The 25 exploratory games reached 496 total floors, mean 19.84 and median 16.
Seven entered Act 2, four reached an Act 2 boss, none entered Act 3, and none
won. R1 reached 498 total floors under the same training configuration. These
cohorts used different random seeds, high epsilon, expert mixing, and evolving
weights, so the similarity is operational context rather than a promotion test.

## Integrity

Replay rejection, RL-agent failure, episode-close failure, checkpoint-save
failure, and non-finite tensor counts were all zero. CommunicationMod's error
log grew only by the 557-byte startup wrapper/dependency message and did not
grow during gameplay. The max-game bound fired exactly once.

The original CommunicationMod configuration was restored byte-for-byte, and
the Python and ModTheSpire processes were closed after the batch.

## Next Step

Preregister a fresh seed pool and compare this candidate against the frozen
entry checkpoint with training and expert mixing disabled and epsilon fixed at
zero. Do not continue training R2 before that gate.
