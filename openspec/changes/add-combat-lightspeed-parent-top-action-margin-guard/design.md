## Context

The existing soft parent cross-entropy and non-EndTurn-versus-EndTurn guard did not prevent a candidate from crossing small parent action margins. The card-only follow-up improved reward/HP but omitted parent EndTurn states and failed victory gates. A single best-versus-runner-up legal-action constraint matches the raw policy boundary that production actually wraps.

## Goals / Non-Goals

**Goals:**

- Preserve a bounded frozen-parent raw top-action margin across every legal combat action.
- Protect parent EndTurn states so the same deployment guard remains eligible.
- Keep the objective default-off, deterministic, and separately observable.
- Test once on unused training and evaluation seeds.

**Non-Goals:**

- Freeze all parent Q values or all pairwise rankings.
- Reimplement production fallback inside training.
- Change rewards, replay collection, network architecture, native mechanics, or live behavior.
- Tune weight or cap after fresh outcome access.

## Decisions

### Best legal action versus strongest legal alternative

On rows with at least two legal actions and a finite positive frozen-parent top-two margin, compute a hinge loss that requires the candidate Q for the same parent-best action to exceed its own strongest legal alternative by the parent margin clipped at the registered cap. Count a violation when another candidate action is strictly higher.

This covers EndTurn, card, potion, and target-specific drift with one O(actions) calculation. It is stronger than card-only ranking but narrower than full-Q distillation.

### Additive default-off objective

Expose independent weight and cap fields and reuse the immutable warm-start anchor. The first run retains the prior anchor and end-turn guard recipe, adding only the top-action constraint. A positive weight requires a positive cap and warm-start parent.

### Fresh simulator gate

Use unused train seeds `138000..139023` and evaluation seeds `140000..140255`, battle indices 0/3/6/9, and guard-aware evaluation. Compare the frozen candidate against production r16 shadow, the prior guarded control, and the card-only candidate. No same-cohort tuning follows.

## Risks / Trade-offs

- [Constraint suppresses useful policy changes] -> Clip the margin at `0.1` and require outcome uplift, not merely lower violations.
- [Parent raw top action is poor in bare simulation] -> Evaluate through the shared deployment proxy because production wraps the raw action.
- [Fresh result is noisy] -> Use matched 256-seed, four-stratum evaluation and victory/reward/HP guardrails.

## Migration Plan

Add regressions, wire the objective, run focused tests, then execute one registered fresh cohort. Disable with weight `0.0` or revert if the gate fails.

## Open Questions

- If the fresh gate passes, whether to confirm on a larger frozen cohort before packaging.
