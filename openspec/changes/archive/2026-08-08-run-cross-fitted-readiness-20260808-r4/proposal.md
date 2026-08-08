## Why

The consumed r3 readiness attempt exposed recursive source selection and
runner-owned staging-retirement defects, and pushed repair commit
`479f5536ca21e2abd543f33f970bef93103ba0d8` now corrects both boundaries while
preserving every fixed readiness ceiling. Because readiness is source-bound and
non-retryable, the repair requires one separately preregistered r4 source-only
attempt before any empirical successor can be considered.

Success is one independently verified canonical r4 publication or terminal
receipt for the new source identity, with every empirical and downstream
authority still false. A verified `go` would permit only a later successor-
registration proposal and would not authorize empirical execution.

## What Changes

- Preregister exactly one source-only audit named
  `noncombat-cross-fitted-empirical-successor-readiness-20260808-r4`.
- Fix the canonical output at
  `reports/noncombat_cross_fitted_empirical_successor_readiness_20260808_r4`,
  isolated scratch at `.source_only_readiness_scratch_20260808_r4`, and the
  only allowed staging sibling at
  `reports/.noncombat_cross_fitted_empirical_successor_readiness_20260808_r4.<source-commit>.staging`.
- Require the final source identity to be one pushed, tracked-clean commit that
  descends from and preserves repair commit
  `479f5536ca21e2abd543f33f970bef93103ba0d8`, contains the complete synced r4
  plan, and has no prior source-keyed readiness attempt.
- Preserve r1, r2, and consumed r3 attempts, receipts, publication, closeout,
  and r3 staging residue as immutable evidence; never delete, rewrite, verify
  in place, or retry r3.
- Recheck exact source, paths, bound inputs, fixed evidence, and r4 absence
  immediately before invocation. Any mismatch stops without choosing another
  commit, id, path, ceiling, or command.
- Require a new exact human authorization naming the final source commit,
  complete command and paths, fixed ceilings, all-false maps, one-shot claim,
  no-retry boundary, and 7,200-second outer wait. Standing repository or
  similar-run authorization is insufficient.
- Invoke the existing repaired auditor at most once and independently verify
  either an installed publication or canonical terminal receipts only after
  true process exit. This proposal phase does not invoke the auditor or create
  an attempt.
- Do not load native, runtime, Torch, model, checkpoint, game, or
  CommunicationMod code; construct an environment; access empirical outcomes;
  fit; train; evaluate; run OPE; register a successor; qualify; or promote.
- Before a started receipt exists, rollback means abandoning the planned run.
  After the attempt is claimed, no retry, resume, repair in place, path
  substitution, seed change, tuning, or widened ceiling is allowed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-cross-fitted-empirical-successor-readiness`: Add the exact repaired-
  source `20260808-r4` one-shot identity, immutable r3 evidence boundary,
  explicit authorization gate, preflight, terminal verification, and non-
  authority contract.

## Impact

The change affects only OpenSpec planning, source-control preflight, the
existing standard-library readiness auditor and verifier, source-keyed attempt
receipts, and later readiness closeout artifacts. No gameplay, policy,
estimator, reward, native adapter, runtime, training, checkpoint, or production
configuration changes are permitted.
