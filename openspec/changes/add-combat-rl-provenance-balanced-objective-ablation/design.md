## Context

The R1 and R2 full-network successors use one cross-entropy anchor over mixed provenance batches. Because override rows make up 78-81% of each corpus, their executed-action labels dominate the aggregate loss. Both successors improved TD fit and override agreement but moved direct parent actions toward Play Card, including actions with substantial parent Q margins.

The trainer already supports a parent top-action margin guard, but it currently applies to every eligible row. Applying it unchanged would protect the parent action on override rows and directly oppose the intended executed-action learning. The next experiment therefore needs both stratum-balanced imitation and direct-only ranking protection.

## Goals / Non-Goals

**Goals:**

- Give direct and override anchor strata equal aggregate objective weight without changing their label semantics.
- Protect the frozen parent's top legal action margin only on direct rows.
- Run two deterministic 64-update arms on the committed R2 development corpus and select at most one objective recipe for a later new-corpus attempt.
- Preserve exact hashes, telemetry, fixed gates, and explicit no-authority boundaries.

**Non-Goals:**

- Produce a holdout-eligible candidate from the reused corpus.
- Start the game, CommunicationMod, LightSTS native simulation, or a live policy gate.
- Change production defaults, r16, replay contents, network architecture, reward shaping, or the existing failed candidates.
- Sweep weights, caps, update counts, seeds, splits, or thresholds after seeing results.

## Decisions

### Balance anchor loss by provenance stratum

When both strata are present, the balanced anchor is `0.5 * mean(direct CE) + 0.5 * mean(override CE)`. Direct labels remain frozen-parent greedy actions and override labels remain executed actions. The trainer reports direct and override counts and component losses separately. The existing global mean remains the default for every current caller.

This is preferred over inverse-frequency per-row weights because the two explicit means are easier to test, interpret, and keep stable when batch composition changes.

### Filter the existing top-action margin guard to direct rows

The margin-loss helper will accept an optional eligibility mask. A new trainer option will pass `~anchor_to_executed_action` to that helper while leaving the existing all-row mode unchanged. The fixed guarded arm uses weight `1.0` and cap `0.1`: it preserves ranking with a small positive margin rather than trying to reproduce the parent's full Q scale.

This is preferred over a separate network head because the evidence first warrants testing objective interference; an architectural split remains the fallback if direct ranking still fails.

### Run a fixed two-arm offline ablation

Both arms reset from production r16 and use the committed R2 replay, combat-group split seed `2026082805`, training seed `2026082806`, CPU, learning rate `1e-4`, batch size `128`, anchor weight `1.0`, gamma `0.99`, and exactly 64 updates:

1. `balanced_anchor`: provenance-balanced anchor, no top-action margin guard.
2. `balanced_anchor_direct_margin`: provenance-balanced anchor plus direct-only top-action margin guard weight `1.0`, cap `0.1`.

The existing R2 result is the immutable global-anchor reference and is not rerun. The runner validates all bindings before fitting and writes arm artifacts atomically.

### Separate objective selection from candidate authority

An arm is technically acceptable only if the existing stratified development gates pass: validation TD improves, overall drift is at least 5%, direct drift is at most 10%, override executed-label uplift is at least 0.10, positive-energy End Turn increase is at most two, both strata are nonempty, and integrity checks pass.

If both arms pass, select the lower direct drift; then higher override uplift; then the simpler balanced-only arm on an exact tie. The selected output is only a recommended recipe. A final candidate requires a new replay collected after that recipe is frozen.

### Allow exact infrastructure retries without adaptive tuning

An infrastructure or entrypoint failure may be retried with the same source, input hashes, arm matrix, seeds, and thresholds because the run is deterministic and consumes no external outcome. Any recipe, seed, threshold, or arm change requires a new registration. This replaces fragile one-invocation ceremony with an immutable-recipe boundary.

## Risks / Trade-offs

- [Risk] Balanced anchor may improve direct stability but reduce override learning. -> Mitigation: retain the fixed override uplift and TD gates.
- [Risk] The direct margin guard may dominate the objective. -> Mitigation: cap required margin at `0.1`, report its loss and violations, and keep weight fixed at `1.0`.
- [Risk] Reusing the R2 development split overfits objective selection. -> Mitigation: grant no candidate or holdout authority and require a new corpus for the selected recipe.
- [Risk] Neither arm reaches 10% direct drift. -> Mitigation: stop and propose a residual or separate-head architecture rather than adding more arms.

## Migration Plan

1. Add RED unit coverage for balanced loss, direct-only eligibility, telemetry, and unchanged defaults.
2. Implement the trainer options and deterministic two-arm runner.
3. Run focused tests, strict OpenSpec validation, and one optimized commit gate; commit and push the immutable source.
4. Execute the fixed ablation, publish hashes and the objective decision, then sync and archive the change.

Rollback leaves both new options disabled and ignores exploratory artifacts. Production r16 and existing callers remain unchanged.

## Open Questions

None. A residual/head design is intentionally deferred unless both fixed arms fail.
