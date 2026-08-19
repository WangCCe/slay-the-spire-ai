## Context

Production traces and the guard-aware counterfactual exclude action-index and packaging errors as the main explanation for the failed candidate. The current end-turn margin guard is ineligible when the frozen parent selects EndTurn, while the production wrapper then chooses a strong card; soft cross-entropy does not preserve the parent's card-to-card Q distance. The new objective must address that narrow ranking failure without freezing the full policy.

## Goals / Non-Goals

**Goals:**

- Preserve a bounded frozen-parent preference for its best legal card action over all other legal card actions.
- Keep the objective optional, deterministic, and measurable.
- Reuse the existing immutable parent network and replay batches.
- Evaluate the first candidate through the shared deployment guard proxy before any live work.

**Non-Goals:**

- Imitate the production heuristic fallback or every parent action ordering.
- Prevent a candidate from changing card ranking when the parent has no positive margin.
- Change rewards, behavior-policy collection, replay targets, network structure, native simulation, or production code.
- Authorize qualification, packaging, promotion, or gameplay from a development-cohort ablation.

## Decisions

### Preserve the parent's best-card margin against its strongest alternative

For each replay row, restrict the legal mask to the 60 play-card action indices. Rows with fewer than two legal card actions are ineligible. On eligible rows, compute the frozen parent's best legal card action and the runner-up card Q. A positive parent margin is clipped by a configured cap. The candidate hinge loss compares the candidate Q for that same parent-best card against its own highest-Q legal card alternative.

This directly penalizes a parent-best `Bash` or `Perfected Strike` falling below an alternative `Strike`, including target selection, while avoiding an O(actions squared) all-pairs objective.

Alternative considered: stronger cross-entropy weight. Rejected because it does not bind the parent Q margin and would constrain all action families rather than the observed card-action boundary.

### Default off and share the frozen anchor

Add `parent_card_ranking_guard_weight` and `parent_card_ranking_guard_cap`, both following the existing end-turn guard lifecycle. A positive weight requires a positive cap and a valid warm-start parent; the same frozen anchor network supplies Q values.

### Record eligibility and violations separately

The trainer records loss, eligible-row count, and rows where the candidate ranks another legal card above the parent-best card. The smoke report and simulator-only checkpoint bind weight and cap. Zero eligible rows return a differentiable finite zero but block a registered positive-weight experiment.

### Gate on guard-aware evidence

The first ablation uses the previous control's training/evaluation cohort and recipe, changing only the new objective. It is not fresh evidence. The candidate is compared against production r16 shadow and the prior guarded control with the deployment guard proxy enabled. Only material improvement permits a separately registered fresh frozen comparison.

## Risks / Trade-offs

- [Parent card ranking can itself be suboptimal] -> Preserve only a clipped positive best-versus-runner-up margin and test against outcome metrics, rather than cloning all parent Q values.
- [Multiple target actions can dominate eligibility] -> Treat target-specific card actions consistently with the deployed action space and report aggregate violations.
- [A small cap may be too weak] -> Register one conservative cap before outcome access; do not tune after the ablation.
- [Development-cohort reuse can overstate evidence] -> Limit it to causal objective isolation and require fresh seeds before packaging or gameplay.

## Migration Plan

1. Add helper regressions for filtering, clipping, violations, and differentiable zero.
2. Wire default-off trainer and smoke configuration/report/checkpoint fields.
3. Run focused tests and one preregistered ablation.
4. Compare frozen policies with guard-aware evaluation and decide fresh-confirmation go/no-go.

Rollback is weight `0.0` or revert. Existing checkpoints and default trainer behavior remain compatible.

## Open Questions

- If the conservative best-card guard passes fresh evaluation, should a later change use semantic card identity rather than target-specific action indices for broader ranking preservation?
