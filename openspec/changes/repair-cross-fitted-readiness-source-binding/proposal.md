## Why

The consumed one-shot readiness identity closed as terminal
`no_go_source_binding` because the auditor and independent verifier accepted a
five-field synthetic schedule while the immutable consumed registration uses
the canonical eight-field schedule. Archiving the completed readiness change
also moved its contract out of the active-change path that the source binding
still names, so a new pushed source identity would otherwise fail before the
intended readiness checks.

Success means source-only tests accept the exact production schedule shape and
canonical main-spec path while rejecting missing, extra, or inconsistent
provenance fields and the retired active-change path.

## What Changes

- Require the consumed schedule to contain exactly the eight fields published
  by the bound cross-fitted registration, including canonical search start,
  inventory digest, and selection schema version.
- Validate those provenance fields semantically in both the auditor and the
  independent verifier instead of merely allowing unknown fields.
- Bind the readiness contract through its synced canonical main spec after the
  completed change has been archived.
- Add production-shaped positive regressions and negative regressions for
  missing, extra, malformed, and inconsistent provenance plus stale spec-path
  binding.
- Preserve the prior attempt receipts, terminal no-go, single-publication
  semantics, all-false authority, ceilings, cohort, budget, and decision
  precedence byte-for-byte.
- Do not register or execute another readiness attempt, access empirical seeds,
  load native or model code, train, evaluate, run gameplay, or use
  CommunicationMod in this change.
- Roll back only the new source-only implementation commit if its focused
  regressions fail; never modify or reinterpret the consumed attempt.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `noncombat-cross-fitted-empirical-successor-readiness`: Tighten the bound
  consumed-schedule provenance contract and move the readiness contract binding
  from the retired active-change path to the canonical main spec.

## Impact

The change is limited to the readiness auditor, its standard-library verifier,
their source-only regression tests, and the existing readiness specification.
It adds no runtime, Torch, native, game, training, registration, or promotion
dependency and grants no empirical authority.
