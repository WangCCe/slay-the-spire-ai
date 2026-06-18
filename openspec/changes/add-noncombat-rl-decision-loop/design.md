## Context
The existing offline comparator already normalizes shop, event, route, and card-reward rows from fixtures, `.run` records, and enriched decision traces. It is useful for diagnosis, but its rows are not yet a stable training dataset because they lack a canonical sample schema, explicit candidate actions, outcome linkage, and a promotion gate that says whether non-combat RL work is ready to advance.

Combat RL is a separate concern. The current live mode can use `combat_rl`, where RL handles combat and the optimized heuristic agent handles non-combat decisions. This change keeps that split intact and uses non-combat decision data to prepare RL readiness rather than training a new non-combat policy immediately.

## Goals
- Record all priority non-combat decisions as deterministic, versioned samples.
- Preserve both the current policy choice and a Bottled-style reference label without forcing either to be the live decision.
- Attach live outcomes only when the join is reliable enough for evaluation.
- Produce a repeatable fresh-eval report that blocks or allows promotion based on explicit gates.
- Keep combat RL smoke training small and limited to training-pipeline health checks.

## Non-Goals
- No formal non-combat RL training loop in this change.
- No replacement of current shop, event, route, or reward decision logic.
- No import-time or runtime dependency on the local Bottled checkout.
- No broad RL action-space redesign beyond what is needed to describe non-combat candidate actions.

## Decisions
- Decision samples SHALL be emitted by an analysis/export path built on the existing decision trace and comparator logic, not by mutating live strategy decisions.
- Candidate actions SHALL be category-specific but normalized into a shared shape with `action_id`, `kind`, `label`, `raw`, and `available` fields.
- State snapshots SHALL keep compact, JSON-serializable fields already present in decision traces: floor, act, HP, gold, deck, relics, potions, screen context, and category-specific context.
- Bottled labels SHALL remain reference labels with confidence and reason fields, not ground-truth rewards.
- Reward readiness SHALL be represented as a documented contract before training starts. It can define candidate reward components and required outcome fields, but this change does not tune weights or optimize a policy against them.
- Outcome joins SHALL be conservative and timestamp based for the first implementation. A sample is promotion-eligible only when its trace `unix_time` maps to exactly one AI-marked `.run` file window derived from the run timestamp and playtime. Explicit trace run ids can be added later, but are not required for this first gate.
- Promotion gating SHALL live in analysis/report tooling first. The gate can be called after a fresh eval batch and must report `allowed` or `blocked` with reasons.
- Formal non-combat RL training SHALL remain blocked by this change even when the data-loop promotion gate is allowed. A later approved change must explicitly turn the readiness artifacts into a trainer.

## Risks / Trade-offs
- Trace rows may miss enough context for complete candidate actions. Mitigation: keep evidence-quality labels and report missing fields by category.
- Bottled labels can conflict with future RL exploration. Mitigation: treat Bottled as a comparison label and optional behavior-cloning target, not as the reward function.
- `.run` files are outcome summaries, not exact decision logs. Mitigation: only join outcomes when timestamp/run identity is reliable and make missing joins explicit.
- Full pytest is currently slow enough to affect iteration. Mitigation: require focused tests for the new exporters/gates and run full pytest before promotion or commits that touch shared live paths.

## Resolved Questions
- First outcome join: use trace `unix_time` plus AI-marked `.run` windows. If there is no unique match, mark `missing` or `ambiguous` and exclude the sample from live-outcome metrics.
- Reward definitions: report them as a readiness contract in the evaluator before any non-combat RL trainer is scaffolded.
