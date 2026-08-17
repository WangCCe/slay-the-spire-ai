# Second Parent On-Policy Replay Collection

## Decision

Accept the second replay as independent evidence for mixed-cohort offline
training. The 20-game collection completed naturally and stored all 3,255
transitions without truncation or optimizer updates.

## Zero-Update Verification

The terminal checkpoint has `episode=20`, `total_steps=3255`,
`learning_starts=100000`, an empty optimizer state, and null TD/total losses.
Its online and target tensors exactly equal the promoted parent and each other.
All 20 run seeds match the registered pool in order.

## Cross-Cohort Signal

The second cohort reproduces the first cohort's core policy mismatch:

| Metric | r1 | r2 |
| --- | ---: | ---: |
| Replay transitions | 3,856 | 3,255 |
| Parent positive-energy EndTurn share | 69.67% | 70.32% |
| Executed positive-energy EndTurn share | 2.66% | 2.34% |
| Positive-energy parent-EndTurn interventions | 2,002 | 1,674 |

The raw parent and effective guarded policy therefore disagree in the same
direction on two independently seeded state cohorts. Together they provide
7,111 transitions and 3,676 positive-energy intervention states, which is a
materially better training basis than selecting a margin weight from r1 alone.

## Runtime

The runs reached 424 total floors with ten Act 2 entries and five Act 2 boss
reaches. These outcomes are collection context only because the policy was
unchanged. There were no training-loss entries, expert actions, invalid actions,
nonzero RL failures, replay failures, tracebacks, critical errors, or post-start
CommunicationMod error growth. Production configuration was restored and all
experiment/game processes were closed.

## Next Step

Create one deterministic mixed replay checkpoint with a 512-row holdout from
each cohort. Run the existing Q-preserving, zero-TD pairwise EndTurn-margin
ablation against that 1,024-row stratified holdout. Any candidate must improve
the intervention margin across replicates while retaining parent agreement;
live evaluation still requires a new seed pool.
