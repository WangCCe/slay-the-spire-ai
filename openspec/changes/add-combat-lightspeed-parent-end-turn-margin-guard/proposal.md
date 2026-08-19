## Why

The production-r16 LightSTS successor direction is harmful even at alpha `0.05`, and fresh-state drift evidence shows its earliest policy changes are concentrated where the frozen parent selects a card but the candidate replaces it with end turn. The existing masked parent-policy cross-entropy anchor encourages the parent action but does not explicitly preserve its Q margin over end turn.

## What Changes

- Add an optional frozen-parent loss that preserves the parent's clipped positive selected-non-end-turn-versus-end-turn Q margin on complete legal transitions.
- Keep the loss disabled by default so every previous registration remains reproducible.
- Report guard eligibility, loss, and ranking-violation metrics in training artifacts.
- Add focused mathematical, compatibility, and reporting regressions.
- Preregister and run one bounded fresh-seed LightSTS successor using the guard; use matched simulator outcomes as the first go/no-go gate.
- Non-goals: no game or CommunicationMod launch, no production checkpoint loading, no packaging, and no promotion based on this change alone.
- Rollback boundary: retain production r16 and disable the guard if the bounded successor misses its registered technical or matched-outcome gates.

## Capabilities

### New Capabilities

- `combat-lightspeed-parent-end-turn-margin-guard`: Defines frozen-parent end-turn margin preservation, compatibility, observability, and bounded experiment requirements.

### Modified Capabilities

- `combat-lightspeed-training-smoke`: Extends formal LightSTS training with an optional registered auxiliary objective while preserving prior default behavior.

## Impact

- Affects the LightSTS combat training runner and its focused tests and reports.
- Adds no runtime dependency and does not change production `RLAgentV2` or CommunicationMod behavior.
- Success is a technically complete fresh-seed run whose guarded candidate improves over the unguarded r1 direction and passes preregistered matched LightSTS outcome gates; otherwise production r16 remains authoritative.
