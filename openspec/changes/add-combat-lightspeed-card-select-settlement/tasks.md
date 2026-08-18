## 1. Regression Contract

- [x] 1.1 Add source-level tests for adapter v2 identity, bounded settlement evidence, explicit task allowlisting, and unchanged RL v2 dimensions.
- [x] 1.2 Add native regressions proving the r3 blocker seeds settle deterministically across clones while an unsafe or unenumerable task remains unsupported.

## 2. Settlement Implementation

- [x] 2.1 Implement bounded native `CARD_SELECT` preflight, deterministic auxiliary settlement, progress checks, and evidence fields.
- [x] 2.2 Update the Python bridge to validate adapter v2 settlement evidence without expanding the encoded state or 133-action mask.
- [x] 2.3 Aggregate settlement counts and task identities in simulator training reports.

## 3. Focused Verification

- [x] 3.1 Build the changed adapter in a new immutable directory and bind the new module hash.
- [x] 3.2 Run focused bridge, calibration, and training pytest gates plus strict OpenSpec validation; do not run the unrelated full suite because the module remains production-import isolated.

## 4. Fresh Replication

- [x] 4.1 Freeze one new training/evaluation cohort and unchanged optimizer budget before outcome access, then run at most once without tuning or retry.
- [x] 4.2 Publish source-bound artifacts and decide the reward, HP, victory, unsupported-state, and settlement-coverage gates.

## 5. Closeout

- [ ] 5.1 Review the scoped diff, commit and push `master`, sync the bridge delta spec, and archive the completed change.
