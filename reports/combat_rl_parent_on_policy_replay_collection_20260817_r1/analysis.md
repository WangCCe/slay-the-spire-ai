# Parent on-policy replay collection

## Decision

Accept the 3,856-transition checkpoint as immutable fresh replay evidence for
offline training design. It has no promotion authority and did not update the
policy.

The registered run requested 20 games, but episode 19 ended at 3,856
transitions, only 240 below `learning_starts=4096`. Because the largest
observed episode added 419 transitions, the process was stopped before episode
20 could trigger the first optimizer step. This is an intentional safety
termination, not a runtime failure.

## Zero-update verification

The terminal checkpoint stores 3,856 replay rows and `total_steps=3856`.
Online and target tensors exactly equal the promoted parent, optimizer state is
empty with step zero, epsilon is zero, and both TD and total loss remain null.
The runtime log contains no training update, expert action, invalid action,
replay failure, traceback, or critical error. CommunicationMod's error file did
not grow after startup.

## Policy evidence

The fresh replay exposes a large difference between the raw network and the
effective gameplay policy. On 2,967 positive-energy states, the parent network
greedily selects EndTurn 2,067 times (`69.67%`), while the recorded executed
action is EndTurn only 79 times (`2.66%`). There are 2,002 positive-energy
states where an EndTurn selected by the parent is replaced by a non-EndTurn
action. Overall raw-parent versus executed-action agreement is `34.52%`.

The older truncated replay showed the same effective low-EndTurn behavior but
a lower raw-parent EndTurn share (`60.76%`). That cohort sensitivity explains
why optimizing the aggregate old-replay EndTurn rate did not transfer reliably
to fresh matched games.

## Outcomes

The 19 complete runs reached 476 total floors, mean `25.05`, with 14 Act 2
entries, five Act 2 boss reaches, one Act 3 entry, and no victory. These are
collection context only because there is no candidate policy comparison.

## Next step

Use this immutable replay for bounded offline pairwise margin training: only on
positive-energy intervention states, require the recorded executed action to
outrank EndTurn while retaining a frozen parent anchor. Compare held-out margin
coverage, executed-action agreement, parent agreement, and TD error before any
live candidate training.
