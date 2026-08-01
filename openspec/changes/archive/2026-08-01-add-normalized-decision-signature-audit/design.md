## Context

`analysis_scripts/offline_decision_comparator.py` already preserves every sample's full JSON context fingerprint and deliberately uses that exact fingerprint in `rank_issues`. That protects the repair gate from conflating materially different offers, maps, HP states, or decks, but a recent 263-row complete-trace report produced no repeatable issue because unrelated metadata differs between otherwise comparable decisions.

The new layer remains entirely offline. It consumes the comparator's normalized samples and Bottled-style comparison rows; it does not write decision traces, change the agent, start a game, or rely on Communication Mod. Its stakeholder is the gameplay-validation loop: it needs a reviewable answer to “which mismatch shapes recur?” before a strategy change is considered.

## Goals / Non-Goals

**Goals:**

- Derive deterministic, category-aware normalized signatures that retain the policy inputs used by the relevant reference adapter while discarding incidental ordering and identifiers.
- Render transparent diagnostic groups with a stable signature, distinct-occurrence count, member sample IDs, full-context fingerprints, and a compact variation summary.
- Make diagnostic eligibility conservative: only complete, non-fixture, high-confidence disagreement rows with an unambiguous operating-decision family are eligible.
- Keep exact-context `rank_issues` and the existing regression-first repair gate unchanged.
- Regenerate a fixed-cutoff local report that states whether it found only diagnostic signals or a group worth manual investigation.

**Non-Goals:**

- Automatically treating a normalized group as a gameplay repair recommendation.
- Collapsing different offers, affordability states, HP threshold sides, route shapes, or reference-policy modes into one group.
- Training, parameter tuning, live trace-schema changes, Communication Mod changes, or agent-policy changes.
- Using partial `.run` reconstruction as complete evidence.

## Decisions

### Add a diagnostic signature, not a replacement fingerprint

Each comparison row will retain the canonical full-context fingerprint. A new normalized signature will be calculated separately and used only by a new `rank_normalized_review_candidates`-style diagnostic path. `rank_issues` remains based on the exact fingerprint and remains the only report section named “Most Worth Fixing.”

Alternative: replace the exact fingerprint in `rank_issues`. Rejected because it would silently broaden the repair gate and convert an evidence-discovery tool into a policy-change authority.

### Canonicalize only adapter-relevant decision inputs

Every signature includes category, oracle mode, normalized current choice, normalized reference choice, and a stable reference-reason class. It then adds category-specific policy inputs:

- **Card reward:** normalized offered-card multiset, skip availability, and counts of the cards that the reference policy evaluates from the deck.
- **Shop:** purchasable priority classes, purge availability and affordability, price/remaining-gold bands relative to the selected reference action, and starter-removal state.
- **Event:** event identifier, enabled option labels, the HP threshold side used by the adapter, and only relic flags that change the adapter's branch.
- **Route:** act/floor band, HP-pressure band, candidate-path feature vectors per selectable choice, and the reference action's reward/survivability ordering class.

Inputs that the adapter does not read (raw JSON key ordering, trace index, full relic/deck ordering, map coordinates, and duplicated retry rows) are not signature fields. Fields that alter an adapter branch are never generalized away. The exact serialized schema and version marker will be emitted so a later schema change cannot merge results across incompatible definitions.

Alternative: use a generic recursive JSON filter. Rejected because it cannot demonstrate that a removed field is policy-irrelevant and would be difficult to audit per decision family.

### Require independent, inspectable occurrences

The diagnostic ranker will collapse retries of the same decision and count only distinct decision occurrences. Trace-origin samples must carry stable input-path or run identity in addition to their trace offset, so same-named `trace:<index>` records from different files cannot collide and repeated callbacks cannot inflate support. A candidate requires at least two distinct eligible occurrences; report output lists the occurrence keys and full fingerprints rather than hiding the differences.

Alternative: count rows directly. Rejected because Communication Mod retries and duplicated trace rows would create false repetition.

### Separate discovery from promotion

The report will add a clearly labeled “Normalized Review Candidates” section. It will say that each group is diagnostic, show exclusions, and require an operator to inspect the member contexts and create a targeted red regression before any gameplay code is changed. A group with unresolved contextual variation, one source identity, partial evidence, or lower confidence is either excluded or reported as insufficient evidence.

Alternative: surface every Bottled disagreement as a candidate. Rejected because Bottled is a reference policy rather than a ground-truth outcome label, and current live evidence has not proved a direct policy defect.

## Risks / Trade-offs

- **A signature omits a real policy input** → Build red tests that vary each adapter-relevant branch input; include a signature-version field and show full member contexts for review.
- **A loose bucket hides a meaningful threshold** → Use explicit branch-side buckets rather than broad numeric ranges whenever the adapter has a threshold.
- **Retraces inflate support** → Deduplicate by source identity plus decision occurrence and test retry rows separately from independent runs.
- **Reports are mistaken for repair approval** → Keep the strict section and its wording unchanged; label normalized output as diagnostic and retain the regression-first requirement in the report and spec.
- **Output becomes too noisy** → Sort deterministically, cap displayed groups, and include summary/exclusion counts before detailed member links.

## Migration Plan

The report change is additive and offline-only. Existing trace, fixture, and `.run` inputs remain readable; inputs without the new stable source identity are treated conservatively and cannot contribute repeated support. Rollback consists of removing the signature diagnostic path and report section, returning to the existing exact-context comparator without any live-game migration.

## Open Questions

None for this bounded change. Whether a reviewed group improves survival remains a later, separate gameplay-validation decision backed by a red regression and fresh runs.
