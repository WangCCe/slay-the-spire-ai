# Fresh-replay pairwise EndTurn margin ablation

## Decision

The selected weight `0.05` may proceed to one fresh matched zero-epsilon gate.
The weights-only candidate has no automatic promotion authority.

## Why this objective

The fresh parent replay contains 2,002 positive-energy states where the raw
parent selects EndTurn but the effective gameplay layer executes another
action. Direct cross-entropy over the executed action changed too many other
action relationships. Pairwise margin training instead asks only that the
recorded executed action outrank EndTurn by a margin on those intervention
states.

The existing action-cross-entropy parent anchor was also non-zero at parent
initialization and caused policy drift by itself. The selected design uses
SmoothL1 regression to the frozen parent's Q values on legal actions, giving a
local behavior-preserving anchor. TD weight is zero in this bounded
distillation step.

## Held-out evidence

Across three deterministic batch schedules, weight `0.05` is the only scanned
weight that passes every gate. Parent agreement is `90.36%` on average and
never below `88.87%`. Executed-action agreement rises from the zero-weight
control mean `37.40%` to `39.91%`, and the recorded intervention action
outranks EndTurn on `7.40%` of intervention states versus `1.43%` for the
control. SmoothL1 remains within the registered 10% bound.

The targeted cross-entropy control selects no eligible weight. Larger pairwise
weights improve intervention coverage but fail the parent-agreement guard.

## Full-replay candidate

The deterministic full-replay fit retains `92.89%` parent agreement and
improves executed-action agreement from `34.52%` to `36.15%`. Positive-energy
EndTurn share falls from `69.67%` to `63.30%`, while SmoothL1 improves slightly
from `4.1689` to `4.1530`.

Only 274 replay decisions differ from the parent. Of those, 189 are in the
targeted intervention set; off-target drift is 85 of 1,854 states (`4.58%`).
Parameter relative L2 from the parent is `0.00189`. A real CPU `RLAgentV2`
load using the production item mapping succeeds.

## Next step

Run one fresh 20-pair candidate-versus-parent zero-epsilon gate. Require exact
seed matching, no runtime failures, non-inferior aggregate floor outcomes and
Act progression, and a lower aligned positive-energy raw EndTurn share. Retain
the parent unless every pre-registered condition passes.
