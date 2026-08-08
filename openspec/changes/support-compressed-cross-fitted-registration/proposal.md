## Why

The verified `20260808-r2` readiness candidate is 347,575,355 canonical bytes but only 6,020,468 bytes as deterministic gzip. The current registration embeds the complete inventory, which would exceed both the successor's 64 MiB per-artifact limit and 256 MiB uncompressed-bundle limit even though the same immutable inventory already has a compact, independently verified representation.

## What Changes

- Add a backward-compatible compact registration schema that replaces the embedded historical inventory with exact bindings to one independently verified readiness publication commit, report, and deterministic `gzip-mtime-zero-v1` candidate artifact while retaining the complete 512-seed schedule.
- Require source-only preflight to read both readiness artifacts from their exact immutable Git commit and paths; cross-bind the complete registration source inventory to that readiness source; enforce the existing 64 MiB stored and 512 MiB candidate-canonical ceilings; and reject noncanonical JSON, nondeterministic gzip, trailing or oversized data, non-`go` readiness, authority drift, source drift, schedule drift, or cohort collisions before dependency loading.
- Keep historical embedded-inventory registrations auditable against their own frozen repository commits, but require new empirical-successor registrations to use the compact readiness-bound schema.
- Preserve schedule, source/native/isolation identities, authority maps, execution lifecycle, artifact ceilings, terminal bundle, independent verifier semantics, and canonical request/authorization binding.
- Success requires focused transport and fail-closed regressions plus a later actual-scale readiness run bound to the changed pushed source before any empirical-successor registration is proposed.
- Non-goals are publishing a new registration or execution request, approving or authorizing execution, loading native or model dependencies, accessing seeds, fitting, training, evaluation, gameplay, CommunicationMod, qualification, or promotion.
- Rollback is deletion or revert before a new readiness source is claimed. After a new readiness source is claimed, any transport defect closes that source as no-go and requires a new pushed source identity rather than an in-place retry.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-cross-fitted-hierarchical-learning-successor`: add a compact readiness-bound registration representation and require exact pushed report/candidate verification before runtime loading without weakening existing resource or authority gates.

## Impact

- `analysis_scripts/noncombat_cross_fitted_hierarchical_learning_experiment.py`
- Focused cross-fitted control-plane tests and source-preservation tests
- The successor main specification after delta sync
- A subsequent, separate one-shot readiness change and source identity; no current registration or execution authority changes
