## Context

The initial offline decision comparator can normalize fixtures and summary data from `.run` files, but `.run` records do not preserve the full offer, candidate, price, route, or event context that existed when a decision was made. Treating those rows as complete evidence would overstate confidence and could turn an attribution gap into an unsafe gameplay-policy change.

The existing decision trace is the narrowest place to capture decision-time context without changing CommunicationMod, live command sequencing, or the policy that selects an action. The comparator can then prefer complete trace evidence while retaining fixtures and `.run` rows as explicitly labeled fallback sources.

## Goals / Non-Goals

**Goals:**

- Capture compact decision-time snapshots for shop, event, route, and card-reward decisions.
- Normalize fixture, trace, and `.run` inputs into one evidence model with explicit completeness and limitations.
- Produce deterministic reports that separate repeated high-confidence live evidence from diagnostic-only differences.
- Preserve a regression-first gate that permits at most one minimal gameplay-policy repair for a repeated, first-win-relevant mismatch.

**Non-Goals:**

- Training or tuning a model.
- Replacing the current agent or importing Bottled into live gameplay.
- Comparing combat card sequencing.
- Inferring missing offers, route candidates, or prices from `.run` summaries.

## Decisions

### Capture context at the decision-trace boundary

Category-specific snapshot builders record only the state needed to reconstruct the available decision: offered cards or shop inventory, event options, route candidates, selected action, deck, relics, gold, HP, and available commands. This keeps live behavior unchanged and avoids coupling the comparator to CommunicationMod internals.

Alternative: reconstruct context from `.run` files. Rejected because run records contain outcomes but omit key candidate sets and decision-time prices.

### Use one normalized evidence model with conservative completeness rules

Fixtures, enriched trace rows, and `.run` rows share the same normalized shape. A sample is complete only when its category-specific candidate context and the fields required by the reference adapter are present. Missing context remains visible in `limitations`; it is never silently synthesized.

Alternative: maintain separate comparator pipelines per source. Rejected because their confidence and disagreement metrics would not be directly comparable.

### Rank only repeated non-fixture evidence for repair

The report aggregates disagreements by category and decision pair, but only repeated, complete, high-confidence, non-fixture rows can become repair candidates. Fixture-only, partial, isolated, or combat rows remain diagnostic. A selected repair must begin with a failing regression and remain limited to one behavior class.

Alternative: apply every Bottled-style disagreement. Rejected because Bottled is a reference policy, not ground truth, and because outcome attribution is incomplete.

### Keep reports deterministic and auditable

Stable ordering, source metadata, confidence, limitations, current choice, reference choice, and concise reasons are preserved in the generated report. This makes report changes reviewable and allows later policy-learning work to consume the same evidence without changing live behavior.

## Risks / Trade-offs

- **Trace growth** -> Keep snapshots compact and category-specific rather than serializing the entire game state.
- **False confidence from incomplete fields** -> Require category-specific completeness checks and preserve explicit limitations.
- **Repeated rows from one run appearing stronger than independent evidence** -> Report source metadata and defer broader policy conclusions to later run-grouped evaluation.
- **Comparator logic drifting from Bottled** -> Keep the locally encoded reference labeled as Bottled-style; native Bottled execution is handled by the separate oracle-adapter change.
- **A narrow repair improves one case but harms others** -> Require a red regression, focused tests, full pytest when gameplay code changes, and fresh live evaluation before broader promotion.

## Migration Plan

The trace schema is additive. Existing trace and `.run` inputs remain readable and are classified as partial when enriched fields are absent. No live configuration or checkpoint migration is required. Rolling back the enriched fields leaves the offline comparator functional with lower-confidence evidence.

## Open Questions

None for this completed change. Run-grouped train/evaluation splits, behavior-policy identity, action propensity, and learned-policy promotion belong to a later policy-learning change.
