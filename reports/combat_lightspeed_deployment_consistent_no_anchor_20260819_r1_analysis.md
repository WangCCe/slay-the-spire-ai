# Deployment-Consistent Anchor Ablation

## Verdict

Retain production r16. Removing the raw-parent cross-entropy anchor made the guarded one-step candidate materially worse. The frozen three-way comparison completed without technical blockers, but neither trained candidate earned promotion authority.

## Training Evidence

The no-anchor run retained 53,088 complete-trajectory transitions, balanced them to 73,052 replay rows, and completed 256 optimizer updates. Parameter L2 movement was `1.0896` and mean TD loss was `2.5356`. Collection recorded 47,614 parent branches, 5,394 exploration branches, and 22,121 guard replacements.

## Fresh Parent Gate

Across 875 matched terminal profiles, no-anchor minus r16 was reward `-0.6199`, HP `-0.2549`, and candidate-only versus parent-only victories `20:28`. Battle reward deltas were `-0.1480`, `-0.8074`, `+0.3344`, and `-2.3838` for battle indices 0, 3, 6, and 9.

## Anchor Diagnostic

On the same fresh cohort, anchored one-step minus r16 was reward `+0.1719`, HP `-0.3520`, and victories `11:9`. No-anchor minus anchored was reward `-0.7918`, HP `+0.0971`, and victories `20:30`. Mean-reward ordering was anchored one-step, r16, then no-anchor; the runner selected no winner because the reward leader violated the HP guardrail.

## Implication

The raw-parent anchor is not merely a conflicting constraint: it materially preserves reward and victories. Direct removal is therefore not a viable remedy. Stop this replay recipe family, keep r16 in production, and diagnose action-level drift and conservative-objective coverage before registering a structurally different training recipe. Do not tune the observed cohorts or load either simulator-only candidate in gameplay.
