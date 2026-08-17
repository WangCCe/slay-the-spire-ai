# Promoted-parent replay collection r6

## Decision

Accept r6 as a complete fresh replay confirmation cohort and allow the frozen
r8 candidate to enter one bounded matched live gate.

All 20 registered parent-policy games completed naturally and produced `3595`
transitions. The replay is below the checkpoint storage limit and is complete;
no reconstruction was required.

## Candidate confirmation

On r6, the current parent one-step SmoothL1 was `4.143240` and the frozen r8
candidate improved it to `4.138884`. Candidate-parent action agreement was
`99.9722%`; only one of `1679` off-target states changed action, for a
disagreement share of `0.0596%`.

This confirmation used the already frozen alpha-0.25 checkpoint. It did not fit
a model, select an interpolation, or write a checkpoint.

## Collection integrity

The terminal checkpoint contains all `3595` source transitions. Online and
target networks remain exactly equal to the promoted parent, optimizer state is
empty, optimizer step is zero, and recorded losses are null. Runtime logs show
no training, expert action, invalid action, RL failure, replay failure,
fallback, traceback, critical error, or post-start CommunicationMod error
growth.

The cohort reached `460` total floors, with 11 Act 2 entries and six Act 2 boss
reaches. No run entered Act 3 or achieved victory.

## Next step

Run one small fresh matched live gate against the promoted parent. The effect is
even smaller than the first promoted SGD step, so an all-tied result should
retain the parent rather than promote an observationally indistinguishable
checkpoint.
