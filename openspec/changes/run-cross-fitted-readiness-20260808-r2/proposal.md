## Why

The first readiness identity terminated at `no_go_source_binding` before any
candidate inventory or rehearsal because its source contract rejected the
valid consumed schedule. That identity remains consumed, but the source-only
repair is now reviewed, pushed, synced, and archived, so one fresh one-shot
readiness publication can determine whether the remaining fixed gates are
actually eligible to run.

Success is one independently verified canonical readiness report or terminal
receipt for the new source identity, with every empirical and downstream
authority still false. A `go` result would permit only a later proposal; it
would not itself authorize an empirical successor.

## What Changes

- Preregister exactly one source-only audit named
  `noncombat-cross-fitted-empirical-successor-readiness-20260808-r2`.
- Fix the canonical output at
  `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r2`
  and isolated scratch at `.source_only_readiness_scratch_20260808_r2`; derive
  the only allowed staging sibling as
  `reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r2.<source-commit>.staging`.
- Bind the attempt to the pushed, tracked-clean commit containing the completed
  execution contract; require its source-keyed attempt directory plus output
  scratch, and derived staging paths to be absent immediately before
  invocation.
- Invoke the existing auditor command at most once, without changing code,
  paths, audit identity, ceilings, source commit, or evidence after preflight.
- Independently verify either the installed publication or terminal attempt
  receipts. The no-publication branch uses the exact standard-library
  canonical receipt-review algorithm preregistered in the design, not an
  auditor import or an ad hoc interpretation, before publishing the resulting
  project-direction decision.
- Preserve source commit `863ae5a4046df110e4f9028bb3c56d556a7c6a43` and its
  `r1` receipts as terminal and non-retryable.
- Do not load native, runtime, Torch, model, checkpoint, game, or
  CommunicationMod code; do not construct an environment, access an empirical
  outcome, fit, train, evaluate, run OPE, qualify, or promote.
- Do not create an empirical-successor registration or execution request in
  this change, regardless of the readiness decision.
- Before a started receipt exists, rollback means abandoning the planned run
  without invoking it. After the attempt is claimed, no retry, repair in place,
  path substitution, seed change, tuning, or widened ceiling is allowed.

## Capabilities

### New Capabilities

- None.

### Modified Capabilities

- `noncombat-cross-fitted-empirical-successor-readiness`: Add the exact fresh
  `20260808-r2` one-shot execution identity, preflight, terminal, and
  non-authority contract after the source-binding repair.

## Impact

The change affects only OpenSpec planning, source-control preflight, the
existing standard-library readiness auditor/verifier, source-keyed attempt
receipts, and readiness report/project-direction artifacts. No gameplay,
policy, estimator, reward, native adapter, runtime, training, or production
configuration changes are permitted.
