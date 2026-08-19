## Context

The one-step production-r16 successor used TD loss plus a masked frozen-parent policy cross-entropy anchor. It failed matched LightSTS evaluation, and interpolation plus fresh-state drift audits show monotonic harm beginning at low-margin boundaries: at alpha `0.05`, `134/229` action flips are parent play-card to end-turn. The feature must remain simulator-only, default-off, and reproducible for old registrations.

## Goals / Non-Goals

**Goals:**

- Preserve the frozen parent's positive selected-non-end-turn-versus-end-turn Q margin on eligible replay states.
- Make the objective independently weighted, bounded, observable, and default-off.
- Run one fresh-seed bounded successor and stop at the matched LightSTS gate unless it is eligible.

**Non-Goals:**

- Freeze all parent action identities or prevent card-to-card policy changes.
- Modify production inference, load production checkpoints through `RLAgentV2`, launch the game, or claim simulator-to-game transfer.
- Tune repeatedly on the same cohort.

## Decisions

1. On each replay batch, use the immutable parent anchor to select its legal greedy action and compute its Q difference against `END_TURN_ACTION`. A row is eligible only when end turn is legal and the parent selects a different action.
2. The required margin is `clamp(parent_selected_q - parent_end_turn_q, min=0, max=cap)`. The candidate loss is the mean hinge `relu(required_margin - (candidate_selected_q - candidate_end_turn_q))` over eligible rows. This preserves fragile positive ordering without forcing large historical margins.
3. Keep parent-policy cross-entropy and the new guard independently weighted. Either objective may require the same frozen parent network; zero guard weight creates no new behavior or report blocker.
4. Report per-update guard loss, eligible count, and pre-update end-turn ranking-violation count. Bind weight and cap into the simulator-only checkpoint source metadata.
5. Preregister one run with the production-r16 simulator shadow, fresh disjoint seeds, the previous one-step recipe, parent-policy anchor weight `1.0`, guard weight `1.0`, and cap `0.1`. The cap is fixed from the audit's parent-margin p10 near `0.105`, not tuned on successor outcomes.

Alternatives rejected: full greedy-action margin preservation would also freeze card-to-card changes that the audit does not identify as the dominant failure; a fixed minimum margin would invent confidence beyond the parent; another lower alpha would repeat a direction already shown locally harmful.

## Risks / Trade-offs

- [The guard may over-constrain useful end-turn changes] -> Clip at `0.1`, target only parent non-end-turn versus end-turn, and require fresh matched outcomes.
- [A batch may contain no eligible rows] -> Return a differentiable zero loss, report zero eligibility, and require positive eligibility over a guarded run.
- [The guard can pass technically but remain harmful] -> Retain production r16 unless preregistered matched reward, HP, victory, and battle-stratum gates pass.
- [Core trainer API expansion could affect production] -> Default all new parameters to zero and add compatibility regressions; do not expose the option through production agent configuration.
