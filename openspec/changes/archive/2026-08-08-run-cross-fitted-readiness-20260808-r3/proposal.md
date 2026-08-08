## Why

Compact registration support changed the readiness-bound control plane after
the independently verified r2 `go`, so r2 remains valid historical evidence but
cannot establish registration eligibility for the new source. Pushed compact
implementation commit `08d2c74e6e923380f32bc8aa5aa75c8c337f27d7` now permits
one separately preregistered source-only readiness audit to re-evaluate the
unchanged fixed gates.

Success is one independently verified canonical readiness publication or
terminal receipt for the new source identity, with every empirical and
downstream authority still false. A `go` result would permit only a later
compact-registration proposal and would not authorize empirical execution.

## What Changes

- Preregister exactly one source-only audit named
  `noncombat-cross-fitted-empirical-successor-readiness-20260808-r3`.
- Fix the canonical output at
  `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r3`,
  isolated scratch at `.source_only_readiness_scratch_20260808_r3`, and the
  only allowed staging sibling at
  `reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r3.<source-commit>.staging`.
- Require the final source identity to be one pushed, tracked-clean commit that
  descends from and preserves compact implementation commit
  `08d2c74e6e923380f32bc8aa5aa75c8c337f27d7`, contains the complete synced r3
  plan, and has no prior source-keyed attempt.
- Recheck exact source, paths, bound inputs, preserved r2 evidence, and absence
  immediately before invocation. Any mismatch stops without changing the
  commit, id, path, ceiling, or command.
- Require a new exact human authorization naming the final source commit, audit
  id, output, scratch, staging derivation, one-shot rule, and 7,200-second outer
  wait before invocation. Standing repository authorization is not execution
  authorization for this attempt.
- Invoke the existing auditor at most once and independently verify either the
  installed publication or canonical terminal receipts after true process
  exit. This proposal phase does not invoke the auditor.
- Preserve r1 and r2 attempts, receipts, and publications as immutable and
  non-retryable; do not reuse r2 eligibility for the changed source.
- Do not load native, runtime, Torch, model, checkpoint, game, or
  CommunicationMod code; construct an environment; access an empirical
  outcome; fit; train; evaluate; run OPE; qualify; or promote.
- Do not create a compact successor registration or execution request in this
  change, regardless of the readiness result.
- Before a started receipt exists, rollback means abandoning the planned run.
  After the attempt is claimed, no retry, resume, repair in place, path
  substitution, seed change, tuning, or widened ceiling is allowed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-cross-fitted-empirical-successor-readiness`: Add the exact compact-
  source `20260808-r3` one-shot identity, explicit authorization boundary,
  preflight, terminal verification, and non-authority contract.

## Impact

The change affects only OpenSpec planning, source-control preflight, the
existing standard-library readiness auditor and verifier, source-keyed attempt
receipts, and later readiness report/project-direction artifacts. No gameplay,
policy, estimator, reward, native adapter, runtime, training, or production
configuration changes are permitted.
