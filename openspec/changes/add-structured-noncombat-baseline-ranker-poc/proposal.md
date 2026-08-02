## Why

The completed baseline warm-start failed its untouched rollout floor after
diverging on teacher states, while its headline agreement was inflated by
forced singleton choices. A bounded structured-ranker POC is needed to test
whether candidate-relative, category-aware representations can improve real
multi-candidate imitation before the project spends fresh simulator evidence
or considers formal non-combat RL.

## What Changes

- Add an offline-only structured baseline-ranker POC over the already observed
  warm-start train demonstrations (`4000..4031`), with no native simulator use
  and no access to the observed validation or untouched final cohorts.
- Add deterministic, versioned permutation-invariant state summaries and
  category-specific candidate-relative features for route, card reward, shop,
  and event decisions while preserving each complete legal candidate set.
- Add seed-grouped train-only model comparison that reports singleton rows
  separately and treats multi-candidate agreement, macro category agreement,
  cross entropy, coverage, and fold stability as the implementation-fit
  evidence.
- Publish hash-closed configuration, fold assignments, metrics, selected-model
  artifact, report, manifest, and deterministic replay with all training,
  rollout, live, qualification, promotion, and formal-RL authority false.
- Require a separate OpenSpec and an entirely fresh preregistration before any
  native collection, rollout-quality claim, DAgger-style labeling, or formal
  RL work.

No live evidence is collected or changed. The motivating evidence is the
completed simulator-only warm-start result and its read-only failure audit;
existing `.run`, trace, CommunicationMod, checkpoint, simulator study, and
validation artifacts remain immutable. POC success means a deterministic
seed-grouped comparison in which the preregistered structured candidate wins
the train-only multi-candidate implementation-fit gate across the required
categories without data leakage. Failure or ambiguity stops without a fresh
study, alternate evidence, live gameplay, or formal RL.

## Capabilities

### New Capabilities

- `noncombat-structured-baseline-ranker`: Defines leakage-controlled structured
  candidate features, seed-grouped train-only comparison, multi-candidate
  competence metrics, deterministic artifacts, and no-authority POC verdicts.

### Modified Capabilities

None.

## Impact

- Adds a dedicated offline analysis/training surface under `analysis_scripts/`,
  focused tests, one train-only POC registration, and generated reports.
- Reads the preserved baseline warm-start train demonstration artifact without
  modifying or replacing the prior runner, model, cohorts, or verdict.
- Changes no CommunicationMod configuration, live agent behavior, checkpoint
  discovery, external simulator checkout, production dependency, or formal-RL
  path. Rollback is deletion of the new POC code, tests, change artifacts, and
  reports.
