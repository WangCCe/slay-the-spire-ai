## Why

Round 279's comparator report had 253 complete decision-trace rows but no repair candidate: the current gate requires a byte-for-byte context fingerprint, so ordinary run-to-run variation prevents otherwise comparable high-confidence mismatches from accumulating. We need a read-only, auditable grouping layer that can reveal repeated decision patterns without weakening the existing proof required before a gameplay change.

Success means a fixed trace input produces deterministic normalized-signature groups, each group exposes its exact member contexts and exclusions, and only a reviewed group with repeated independent complete evidence can be promoted to the existing repair gate. This is needed now because the clean simulator has shifted the first-win investigation from mechanics attribution to Act 1 decision evidence.

## What Changes

- Add category-specific normalized decision signatures alongside the existing full-context fingerprint for shop, event, route, and card-reward comparison rows.
- Produce a separate report section that groups non-fixture disagreements by a documented normalized signature, reports distinct occurrences, and links every candidate back to its full-context members and variations.
- Keep the exact-context issue ranking as the default repair authority; normalized groups are diagnostic review candidates until they satisfy explicit completeness, confidence, independence, and human-review conditions.
- Add deterministic fixtures and focused tests for signature construction, conservative exclusion of incomplete or unsupported rows, occurrence de-duplication, and report rendering.
- Regenerate one local analysis report from a fixed fresh-trace cutoff and record whether the new layer exposes a reviewable candidate. No gameplay strategy change is included in this change.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `offline-decision-comparator`: add normalized-signature diagnostics while preserving the existing strict repair gate and read-only behavior.

## Impact

- Affected code: `analysis_scripts/offline_decision_comparator.py` and `tests/test_offline_decision_comparator.py`.
- Affected evidence: one regenerated comparator report and purpose-built deterministic fixtures, if needed.
- No impact on `spirecomm/ai/agent.py`, Communication Mod, live configuration, checkpoints, training, or model parameters.
- Rollback boundary: the capability is offline-only and additive; reverting its comparator/report changes restores the existing exact-context ranking without changing any live-game behavior.
