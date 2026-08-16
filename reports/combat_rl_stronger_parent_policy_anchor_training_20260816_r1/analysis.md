# Stronger parent-policy anchor training R1

## Decision

**Retain the promoted parent and do not run a fresh gate for this candidate.**
The training run was complete and improved replay TD fit, but parent/candidate
greedy agreement was `86.57%`, below the preregistered `88%` minimum.

## Training result

The fixed `0.5` parent-policy anchor completed exactly 20 games, accepted 3,622
transitions, and performed 905 optimizer updates. The final checkpoint is
finite, retains 4,096 transitions from 7,718 source transitions, and stores an
anchor state tensor-for-tensor identical to the promoted parent's online policy.

On the successor replay, SmoothL1 decreased from `4.0084` for the parent to
`3.3605` for the successor. The successor's p95 absolute TD error improved from
`11.9444` to `8.7940`, while p50 worsened from `1.3438` to `1.5811`. Whole-model
relative L2 drift was `2.20%`.

The last anchor loss was finite and positive at `0.4207`. Across 37 periodic
samples it ranged from `0.3640` to `0.6776`, with mean `0.4977`.

## Training cohort

The consumed R4 cohort produced 471 total floors, mean `23.55`, eight Act 2
entries, six Act 2 boss reaches, two Act 3 entries, and no victory. These
outcomes have training-context authority only.

The full rotated log set contains 2,133 selected expert actions and 846 mix
skips, a `71.6%` successful expert share. No masked, unencodable, failed, or
replay-rejected transition was recorded, and all stored executed actions remain
valid under their masks.

## Integrity

Exactly 20 run records and markers completed. The final checkpoint is
`rl_combat_model_ep60_steps22202.pth` with SHA-256
`7fa9064280e45470b26bc9d4ccbec91db16b9198b57fa8eefb68d2a35d634fd8`.
CommunicationMod error growth was the expected 1,014-byte launch record. The
production configuration was restored to SHA-256
`d4d1dd35fd53985796922e5915a8b4ab51373109d08addff2bdcdfebf01a00e4`,
and no game or Python process remains.

The next iteration should restart from the promoted parent with a `1.0` anchor,
not continue this failed-threshold candidate. A later evaluation must use a
fresh seed pool.
