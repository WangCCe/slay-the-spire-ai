## Why

The sealed cross-fitted r2 run and its independently reproduced baseline-
support audit show persistent positive direct `take`-family pressure and a
1,773/1 final-window greedy-family concentration, but that evidence does not
separate accepting a card from choosing among the offered cards. Before any
objective, architecture, coefficient, or successor proposal, the repository
needs one source-only audit that distinguishes those two mechanisms without
claiming policy value or starting another empirical run.

## What Changes

- Add an immutable source-only audit over the exact tracked 20260808-r2
  terminal bundle and the published 20260809 baseline-support audit. It will
  reverify source identity, terminal/manifest identity, inactive lease,
  checkpoint bindings, all eight canonical chunk artifacts, and the prior
  audit bytes before analysis.
- Reconstruct every multi-family card-reward decision and publish separate
  acceptance evidence (`take` versus non-`take`) and conditional-choice
  evidence within the `take` family. Preserve candidate multiplicity, family
  and conditional probabilities, normalized take entropy, top-two gaps,
  selected and greedy identities, and complete chunk order.
- Reconstruct fixed score-space gradient-descent pressure for the take-family
  translation coordinate and the current greedy-take-versus-peer conditional
  margin. Keep policy and entropy terms separate, reconcile stored scalar
  components, and report shared-parameter family/conditional component norms,
  dots, and cosines without treating them as candidate-score effects.
- Publish exact early/final and per-chunk trends plus one bounded descriptive
  verdict. No magnitude threshold will be tuned from the observed values; ties,
  sparse support, mixed signs, and row-local versus shared-parameter ambiguity
  remain explicit.
- Add synthetic contracts proving that a uniform take-family score translation
  leaves its conditional distribution unchanged, that within-take
  redistribution can change conditional choice without changing family mass,
  and that max-pooled shared scores can couple the two coordinates.
- Produce canonical JSON and Markdown from two fresh isolated source-only
  processes with byte-identical outputs and an exact all-false authority map.
- Success requires RED/GREEN arithmetic, identity, malformed-input,
  import-isolation, determinism, verdict, and authority regressions; focused
  pytest; the requalified `commit` gate; the configured `full` phase-close
  boundary; strict OpenSpec validation; and independent source review.
- The exploratory read-only probe used to scope this proposal observed 3,536
  eligible card rewards, 3-4 take candidates per row, near-uniform but
  monotonically declining mean normalized take entropy, monotonically growing
  mean top-two gaps, positive aggregate acceptance pressure in every chunk,
  and mixed direct conditional-margin signs in the final four chunks. These
  observations select no threshold and are not the published audit verdict.
- Non-goals are changing a policy, objective, reward, coefficient, ranker,
  architecture, checkpoint, simulator, gameplay path, test tier, r2 artifact,
  or authority; loading Torch/native/model state; constructing an environment;
  accessing or replaying a seed; fitting, training, evaluating, running OPE,
  qualifying, promoting, or launching CommunicationMod.

## Capabilities

### New Capabilities

- `noncombat-card-acceptance-conditional-choice-audit`: Define immutable input
  verification, exact acceptance/conditional score-space reconstruction,
  shared-gradient limitations, threshold-free bounded classification,
  deterministic publication, and all-false authority for the sealed r2 audit.

### Modified Capabilities

None.

## Impact

- Adds one standard-library analysis module, one focused test file, one new
  capability specification, canonical dated JSON/Markdown reports, and a
  project-direction entry.
- Reuses tracked r2 evidence and existing independent verification contracts;
  it does not mutate or copy the consumed bundle and does not add a dependency.
- The success metric is exact reconstruction of all 3,536 eligible card rewards
  and eight chunk ledgers, byte-identical isolated publications, and one
  evidence-bounded acceptance-versus-conditional verdict with no authority.
- Rollback removes only the new audit source, tests, reports, specification,
  archived change, and direction entry. The sealed r2 run, baseline-support
  audit, current policy, checkpoints, test gates, and live configuration remain
  unchanged.
