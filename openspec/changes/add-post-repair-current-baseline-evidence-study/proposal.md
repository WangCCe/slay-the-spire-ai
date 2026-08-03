## Why

Both registered Current diagnostics were consumed before retaining one row,
while their independent candidate-schema and item-identity defects are now
fixed and the known static card, potion, and relic hydration surface is closed.
A third structural diagnostic would continue the retry loop without measuring
policy quality, so the next useful evidence should be one preregistered,
terminal post-repair baseline study that bears structural risk conservatively.

## What Changes

- Add a simulator-only, no-training study that evaluates the exact frozen
  Current policy against the deterministic first-candidate weak control on
  paired A0 Ironclad trajectories. SimpleAgent and Bottled remain historical
  context only and never enter action selection, reward, or a pass gate.
- Fix a two-stage cohort before implementation: canary seeds `11000..11015`
  and untouched holdout seeds `12000..12063`. A no-native recomputation at
  planning HEAD found 348 excluded seeds across 83 tracked sources and zero
  overlap with either set. No alternate, replacement, selected, or searched
  seed is allowed.
- Make canary a stop gate, not a tuning set. It must retain all 16 paired rows,
  have zero unexpected structural failures, at most one exact declared-support
  row per policy, all four target categories, Current mean floor at least 15,
  and mean Current-minus-control floor at least zero. Failure leaves every
  holdout seed untouched.
- Fix the final floor gates before any execution: retain all 64 paired rows,
  zero unexpected structural failures, at most three exact declared-support
  rows per policy, all four target categories, Current mean floor at least 18,
  a deterministic 95% bootstrap lower bound on Current mean floor of at least
  15, Current-minus-control mean floor of at least 3, and a paired 95%
  bootstrap lower bound greater than zero. Victories are reported but do not
  satisfy the independently blocked outcome-support domain.
- Require one canonical primary execution and one identical replay, 10,000
  fixed bootstrap resamples, conservative last-supported-floor/non-victory
  disposition only for `unsupported_shop_courier_restock_semantics`, complete
  seed denominators, at most 500 target decisions per episode, at most 64
  canary and 256 holdout policy episodes, a 600-second canary limit, an
  1,800-second whole-attempt limit, immutable artifacts, and no retry or
  parameter change after observation.
- **BREAKING**: replace the post-r2 requirement for another diagnostic with one
  narrow integrated post-repair study path. This exception does not revive v1
  or r2, create r3, or generalize to future failed experiments. A passing study
  permits only a later read-only readiness refresh.
- Separate planning, source implementation, preregistration, and empirical
  execution. The pushed preregistration grants no execution by itself; native
  environment construction and seed access require a later explicit approval.
- Keep gameplay, Communication Mod, policy edits, model fitting, reward
  selection, OPE, formal RL, training, loading, qualification, and promotion
  out of scope. Success is one deterministic terminal result, positive or
  negative, under the fixed contract.
- Before a started journal exists, rollback may remove unconsumed study code
  and registration. After the journal exists, rollback must preserve the
  registration, journal, rows, artifacts, and terminal verdict byte-for-byte.

## Capabilities

### New Capabilities

- `noncombat-current-baseline-evidence-study`: Define the immutable two-stage
  Current-versus-weak-control study, conservative support handling, numeric
  floor gates, deterministic publication, and no-training authority boundary.

### Modified Capabilities

- `noncombat-baseline-floor-readiness-audit`: Permit one integrated post-repair
  baseline study instead of a third diagnostic only after both consumed
  failures and their independently verified static repairs are preserved.
- `noncombat-simulator-adapter`: Authorize adapter use within this separately
  reviewed fixed-cohort study while preserving offline isolation and all
  downstream no-authority flags.

## Impact

- Expected implementation: a new focused runner and tests under
  `analysis_scripts/` and `tests/`, reusing the existing adapter, Current
  bridge, canonical artifact, and deterministic bootstrap helpers without
  copying the diagnostic runner.
- Evidence: one checked-in seed/exclusion audit and preregistration, followed
  only after separate approval by canary and conditional holdout artifacts.
- External runtime: the existing hash-bound Windows Python, API v3 native
  adapter module, `sts_lightspeed` checkout, metadata, and MinGW runtime. No
  dependency, simulator, native-module, gameplay, or Communication Mod change
  is planned.
- Formal RL remains `no_go` regardless of this proposal. Even a passing floor
  result leaves source-comparable target-supported outcomes independently
  blocked.
