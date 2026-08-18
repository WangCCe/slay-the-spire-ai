## 1. Regression Contract

- [x] 1.1 Add source-level tests for adapter/schema v3 identity, indexed constructor binding, progression metadata, fixed bounds, and unchanged RL v2 dimensions.
- [x] 1.2 Add native regressions for deterministic positive-index reset, index-zero compatibility, clone isolation, and classified unreachable-index failure.

## 2. Indexed Environment

- [x] 2.1 Implement bounded native baseline-forward out-of-combat and prior-combat progression to an exact zero-based battle index.
- [x] 2.2 Publish requested/reached index, act, floor, encounter, deck size, relic count, HP, and baseline identity through snapshots and bridge validation.
- [x] 2.3 Extend calibration and training profile/config provenance without changing the RL v2 observation or action dimensions.

## 3. Focused Verification

- [x] 3.1 Build the v3 adapter in a new immutable directory and bind its module hash.
- [x] 3.2 Run focused bridge, calibration, and training tests plus strict OpenSpec validation; avoid the unrelated long full suite because this module remains production-import isolated.

## 4. Coverage And Training

- [x] 4.1 Register and run one bounded later-battle coverage calibration with no optimizer updates.
- [x] 4.2 If the preregistered coverage gate passes, register and run one stratified simulator-only training replication; otherwise stop with the calibration evidence.

## 5. Closeout

- [ ] 5.1 Review the scoped diff, commit and push `master`, sync the bridge delta spec, and archive the completed change.
