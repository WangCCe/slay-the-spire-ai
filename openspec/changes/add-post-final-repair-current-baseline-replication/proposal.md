## Why

The consumed Current baseline study stopped halfway through its canary on the
offline bridge's exact `Injury` metadata representation, so it produced neither
a structurally complete policy evaluation nor a credible floor. The defect and
all other known event, shop, candidate-schema, potion, card, relic, and
card-cost compatibility surfaces are now closed, but the current readiness
spec treats this measurement failure exactly like a completed quality failure
and therefore blocks any independent post-repair evidence.

## What Changes

- Add one distinct, versioned post-final-repair replication of frozen Current
  against the deterministic first-candidate weak control. It must preserve the
  consumed registration and rows, exclude every historical seed, and retain
  the old numeric gates or make them stricter.
- **BREAKING**: narrow the baseline-readiness anti-retry rule. A structurally
  complete canary or holdout quality failure remains terminal, while an
  incomplete pre-quality measurement failure may permit exactly one distinct
  successor only after source-complete repair evidence, unchanged policy and
  control, unchanged-or-stricter gates, and fresh cohort isolation are proved.
- Make the new successor the final Current-baseline attempt. Any structural
  blocker, interruption after start, canary stop, or holdout failure terminates
  this lane and cannot trigger another bridge-fix-and-rerun cycle.
- Reuse the old two-stage evidence contract: 16 canary pairs, conditional 64
  holdout pairs, two deterministic replays, exact Courier support accounting,
  complete denominators, fixed bootstrap, fixed resource limits, canonical
  publication, and a separate execution authorization after pushed
  preregistration.
- Keep SimpleAgent and Bottled out of actions, labels, fallbacks, reward, and
  quality gates. Keep the old 18 partial rows descriptive only.
- Treat source-only implementation and preregistration readiness as this
  change's initial success metric. Empirical success is one terminal result
  under the frozen contract, whether positive or negative, and requires later
  exact execution approval.
- Do not load native code, construct a simulator environment, access or select
  a future cohort, launch gameplay, fit a model, train, qualify, load, or
  promote from proposal approval alone.
- Before a started journal exists, rollback may remove the unconsumed
  successor. After start, rollback must preserve its registration, journal,
  partial rows, artifacts, and terminal verdict byte-for-byte.

## Capabilities

### New Capabilities

- `noncombat-current-baseline-replication`: Define the unique versioned
  post-final-repair Current-versus-first-candidate study, its fixed evidence
  gates, terminal lifecycle, canonical publication, and no-training boundary.

### Modified Capabilities

- `noncombat-baseline-floor-readiness-audit`: Distinguish an incomplete
  pre-quality measurement failure from a structurally complete quality result,
  and permit only the registered final replication under closed repair and
  anti-tuning conditions.

## Impact

- Expected source work is a new focused runner and tests under
  `analysis_scripts/` and `tests/`, reusing the existing Current bridge,
  simulator adapter, tracked-seed inventory, and canonical artifact helpers
  without modifying the consumed runner or Current policy.
- Evidence inputs include the immutable blocked study, its 18 partial rows,
  the post-repair readiness review, static closure reports, and current source
  identities. No prior artifact is rewritten or reinterpreted.
- A later preregistration will bind a clean pushed implementation, regenerated
  tracked-seed inventory, exact fresh cohorts, Windows runtime, native module,
  simulator, metadata, thresholds, limits, outputs, and all-false authority.
- Formal non-combat RL remains `no_go` even if the future replication passes,
  because target-supported outcome evidence remains independently blocked with
  zero source-comparable supported victories.
