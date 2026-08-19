# Parent Card-Ranking Guard Ablation

## Verdict

Retain production r16. The objective moved reward and HP in the intended direction, but it failed the preregistered material and victory gates.

## Training Evidence

- 78,500 replay transitions and 256 optimizer updates completed without blockers.
- The candidate parameter L2 delta from r16 was `1.091743`.
- Card-ranking guard eligibility averaged `90.80` rows per batch.
- Guard loss rose from `0.026117` to `0.053977`; ranking violations rose from 9 in the first batch to 19 in the last.

## Guard-Aware Outcomes

Against production r16, the candidate achieved `+0.213316` mean reward and `+0.318925` mean player HP, but candidate-only versus parent-only victories were `8:9`. It missed the registered `>0.25` reward threshold and victory guardrail.

Against the prior guarded control, it achieved `+0.151693` mean reward and `+0.313084` mean player HP, but victory splits were `8:10`. That gate also failed.

The result is useful: card-to-card preservation improves the direction of the candidate, but the clipped card-only constraint is not stable enough and does not protect parent raw EndTurn states that production deliberately recovers through its guard.

## Decision

Do not run fresh confirmation, packaging, or gameplay for this candidate, and do not tune its weight or cap on the observed cohort. The next candidate should use a bounded frozen-parent top-legal-action margin constraint, covering both EndTurn and card actions, on a newly registered cohort.
