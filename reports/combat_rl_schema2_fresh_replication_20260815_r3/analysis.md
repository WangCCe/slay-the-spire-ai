# Combat RL schema-2 fresh replication R3

## Result

The third independent 25-game replicate completed from the same frozen schema-2 entry checkpoint. It collected 3,613 accepted transitions and performed 271 Adam updates after replay crossed 4,096 rows. The final checkpoint is finite and has 1.30% whole-model relative L2 drift from entry.

This is a valid candidate for a fresh matched zero-epsilon gate. It is not promoted, and its exploratory training outcomes are not policy-quality evidence.

## Training

- Accepted transitions: `3,613` (`13,413 -> 17,026`)
- Replay at exit: newest `4,096` of `5,178` in-memory transitions
- Adam step: `2,679 -> 2,950` (+271)
- Epsilon: `0.887444 -> 0.838272`
- Episode: `15 -> 40`, aligned with `ep40_steps17026`
- Relative L2 drift: embeddings 0.27%, hidden 6.61%, value 4.93%, advantage 9.47%, unused output layer 0%
- Target-to-online relative L2: 1.22%

The nonzero episode-average losses were `5.3493 -> 4.8369 -> 4.5287 -> 4.4331 -> 4.4840 -> 4.6015 -> 4.6615`. The late rise is a cohort summary, not enough to select an earlier checkpoint; the final replay comparison remains favorable.

## Replication

On R3's retained replay, Smooth-L1 TD loss was `5.0677` for entry, `4.7172` for R1, `4.6811` for R2, and `4.5532` for R3. All three trained checkpoints therefore improve over entry on replay collected independently by R3.

R1/R2 greedy actions agreed on 76.88% of R3 replay states. R3 agreed with R1 on 70.21% and R2 on 70.51%; each trained checkpoint agreed with entry on 53-58%. The three replicates share a learned direction but retain meaningful policy variance, which is why a live gate remains necessary.

## Gameplay

The exploratory cohort reached 508 total floors, mean 20.32 and median 16. Nine games entered Act 2, three reached an Act 2 boss, none entered Act 3, and none won. R1 and R2 reached 498 and 496 total training floors under the same recipe. Because seeds, exploration, expert mixing, and weights all varied, these totals are operational context only.

## Integrity

Replay rejection, RL-agent failure, episode-close failure, checkpoint-save failure, and non-finite tensor counts were all zero. CommunicationMod's error log grew by only the expected 557-byte wrapper/dependency message during the successful batch, and the max-game bound fired exactly once.

One pre-start attempt failed before any episode or environment initialization because the wrapper rejected a redundant `--train` argument. Removing that wrapper-only token did not change training semantics: a direct dry-run showed the corrected wrapper still emits `--train` for `main.py`. The repair was committed before the successful batch.

The original CommunicationMod configuration was restored byte-for-byte, and the Python and ModTheSpire processes were closed after training.

## Next step

Preregister a fresh seed pool and compare R3 against the frozen entry checkpoint at epsilon zero, with training and expert mixing disabled. Apply the same conjunctive gate used for R2. Do not continue or promote R3 before that result.
