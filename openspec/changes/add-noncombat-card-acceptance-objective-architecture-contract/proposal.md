## Why

The completed card-acceptance audits show persistent direct `take` pressure and
conditional card-choice concentration, while the current max-pooled family
logit and conditional softmax share one candidate-ranker parameter set. The
latest source-only audit proves an independent acceptance coordinate is
representable, but it selects no architecture or objective; a source-only
contract is required before any empirical successor can be proposed safely.

## What Changes

- Add an authority-free card-reward architecture contract with two completely
  disjoint parameter namespaces: an unchanged candidate ranker for conditional
  logits and an independent family head for explicit family logits.
- Define each family feature as the permutation-invariant mean of the projected
  candidate features with that exact `kind`, using float64 accumulation before
  a checked float32 conversion; score every observed family, including `take`,
  `skip`, and `bowl`, without merging non-`take` identities. The `take`
  acceptance coordinate is computed in float64 relative to the log-sum-exp of
  all explicit non-`take` family logits.
- Add an explicit-logit hierarchical objective boundary exposing selected
  family, conditional, and joint log probabilities; family, per-family,
  expected-conditional, and joint entropy; complete tie metadata; and no loss,
  coefficient, reward, advantage, optimizer, sampling, or execution API.
- Prove parameter ownership with synthetic autograd contracts: family-policy
  terms cannot update conditional parameters, conditional-policy terms cannot
  update family parameters, named component gradients reconstruct exactly,
  and acceptance-only changes preserve within-family probabilities, ordering,
  margins, and per-family entropy.
- Cover one-family fallback, missing-`take` fail-closed behavior, `bowl`,
  candidate and family permutation, tied maxima, finite float32 extremes,
  checkpoint namespace identity, deterministic reports, import isolation, and
  exact all-false authority.
- Fix the public source-only API signatures, ordered output dataclasses,
  tensor shapes/dtypes, metadata mappings, nested report schemas, schema
  versions, exact report and authority fields, prohibited import set, 128 KiB
  JSON and 32 KiB Markdown bounds, and canonical dated report names before
  regression implementation.
- Preserve the existing max-pooled distribution, hierarchical objective,
  candidate ranker, consumed cross-fitted runtime, checkpoints, verifier,
  production policy, and CommunicationMod configuration byte-for-byte.
- Record future empirical entry conditions without authorizing execution: a
  separate successor must use fresh paired cohorts, a bounded structural
  canary before an untouched holdout, independent candidate/control artifacts,
  pre-canary immutable candidate/control binding, exact candidate-arm metric
  denominators, at-most-once canary/holdout, explicit rollback triggers and
  target, and separate execution authorization.
- Non-goals are selecting a combined loss or entropy term, coefficient,
  initialization, optimizer, reward, baseline, cohort, checkpoint migration,
  empirical successor, evaluation, OPE, policy, qualification, promotion, or
  live gameplay behavior.

## Capabilities

### New Capabilities

- `noncombat-card-acceptance-objective-architecture-contract`: Define the
  disjoint family/conditional architecture, explicit-logit policy terms,
  gradient ownership, synthetic invariants, deterministic design evidence,
  future successor entry conditions, rollback boundary, and all-false
  authority.

### Modified Capabilities

None.

## Impact

- Adds source-only modules
  `analysis_scripts/noncombat_card_acceptance_policy.py` and
  `analysis_scripts/noncombat_card_acceptance_objective.py`, focused tests, a
  deterministic compact design report, and one new capability specification.
- Accepts already projected finite tensors and reuses only the existing
  candidate-ranker class as a public source dependency. Neither new module
  imports the policy-input projector, simulator adapter, simulator RL
  experiment, or consumed cross-fitted surfaces. The family head is a separate
  ranker instance over family-mean features; no parameter object may be shared
  with the conditional ranker.
- Live evidence remains the canonical item 58/59 reports over 512 trajectories,
  11,729 decisions, 3,536 card rewards, and eight gradient chunks. Only chunks
  1 and 4 had conflicting recorded family/conditional gradients; this is
  descriptive mechanism evidence, not policy-quality or causal evidence.
- Success means exact synthetic coordinate and gradient isolation, stable API
  and checkpoint metadata, focused and repository gate evidence, strict
  OpenSpec validation, and independent review. Fresh gameplay validation is
  not applicable because the capability remains absent from production and
  empirical runtime imports.
- Rollback removes only the new source-only modules, tests, report,
  specification, archived change, and project-direction entry. Existing
  modules, experiments, artifacts, checkpoints, production configuration, and
  live behavior remain unchanged.
