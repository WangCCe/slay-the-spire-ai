# Deployment-Consistent Behavior Result

## Verdict

Retain production r16. The guarded-parent behavior plus full discounted-return recipe is technically valid but fails the fresh outcome gate and ranks last in the five-policy frozen comparison. It authorizes no larger confirmation, packaging, or gameplay.

## Training Evidence

The run retained 50,459 complete-trajectory transitions and balanced them to 65,488 replay rows for 256 optimizer updates. Collection used the frozen r16 parent for 45,380 decisions, deterministic exploration for 5,003 decisions, and the guard proxy replaced 20,766 raw parent EndTurns. The parent parameter hash remained unchanged throughout collection.

Full discounted returns changed the mean target from `1.7152` immediate reward to `20.1484`; mean TD loss was `9.8493`. The candidate moved an L2 distance of `1.7825` from r16 despite the parent anchor.

## Fresh Outcome Gate

Against r16 on unused seeds, candidate-minus-parent results were reward `-0.2892`, HP `-0.0597`, and candidate-only versus parent-only victories `14:17`. Battle reward deltas were `+0.15`, `-0.57`, `+0.12`, and `-1.14` for battle indices 0, 3, 6, and 9.

The five-policy comparison also placed the new candidate below every prior guarded candidate. Its reward deltas were `-0.6604` versus the card-ranking candidate, `-0.5759` versus the prior guarded control, and `-0.5687` versus the top-action candidate.

## Implication

Aligning replay behavior with deployed execution was not sufficient when paired with full episode returns. The evidence does not isolate behavior collection as harmful; the return scale and long horizon are a plausible source of instability, but that remains a hypothesis.

Do not tune epsilon or loss weights on this cohort. The next bounded training question is whether the same deployment-consistent behavior with a frozen-parent 3-step target retains local credit assignment and improves fresh guard-aware outcomes on unused seeds.
