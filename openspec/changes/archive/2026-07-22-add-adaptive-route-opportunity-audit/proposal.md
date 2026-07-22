## Why

The 2026-07-21 adaptive-routing qualification emitted many candidate records but produced no attributable optional-elite treatment. A read-only audit is needed now to distinguish candidate availability, aggressive selection, immediate action divergence, later revocation, and realized elite exposure before any route threshold or commitment change is considered.

## What Changes

- Add an offline adaptive-route opportunity audit that joins frozen `[ADAPTIVE_ROUTE]` log records, map decision-trace rows, and ordered `.run` records.
- Collapse repeated Communication Mod callbacks without losing source multiplicity, provenance, or malformed-input evidence.
- Report a treatment-uptake funnel from zero-versus-one candidate states through aggressive selection, coordinate-level divergence, survival to divergence, and optional-elite realization.
- Preserve source paths, SHA-256 identities, line counts, join diagnostics, and per-opportunity evidence in a machine-readable JSON artifact.
- Produce a dated POC report for the existing ten-game qualification cohort and verify that it reproduces the known `346 -> 173` callback collapse, `58` zero-versus-one opportunities, one aggressive selection, and zero realized optional-elite treatments.
- Keep the change read-only: no gameplay policy, threshold, route default, training, checkpoint, protocol, live configuration, or cohort rerun.

## Capabilities

### New Capabilities

- `adaptive-route-opportunity-audit`: Defines deterministic, fail-closed offline evidence ingestion, correlation, treatment attribution, and reporting for adaptive route opportunities.

### Modified Capabilities

None.

## Impact

- New analysis code under `analysis_scripts/` and focused tests under `tests/`.
- New versioned JSON and Markdown evidence under `reports/` for the frozen 2026-07-21 qualification cohort.
- No runtime dependency, gameplay API, Communication Mod command, checkpoint, or persistent configuration impact.
- Success is a reproducible, integrity-qualified audit artifact that explains treatment uptake without changing the policy. The rollback boundary is therefore analytical only: discard the new artifacts and script if validation fails; the live conservative configuration remains unchanged throughout.
