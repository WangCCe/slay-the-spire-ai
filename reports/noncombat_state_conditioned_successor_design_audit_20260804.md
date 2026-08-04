# Non-Combat State-Conditioned Successor Design Audit

Date: 2026-08-04

Status: `source_only_policy_input_change_recommended`

## Decision

Do not prepare or run an immediate r3 experiment. The smallest justified next
change is an additive source-only policy-input capability that connects the
validated API v3 projection to the state-conditioned ranker without editing the
r2-bound experiment implementation.

The change should:

- encode one shared state tensor separately from the candidate tensor matrix;
- preserve the existing recursive policy-leakage removal and exact API v3
  validation semantics;
- expose stable feature and projection identity for future registration;
- connect scored decisions to the existing anti-collapse diagnostic schema;
  and
- prove determinism, source non-mutation, candidate-order equivariance, and a
  state-only ordering reversal at the integrated boundary.

This is an implementation prerequisite only. Current remains the only eligible
non-teacher policy-quality comparator, but its own-trajectory structural closure
and credible floor remain undemonstrated. Formal non-combat RL and a new
experiment therefore remain `no_go`.

## Evidence Identity

- Repository commit:
  `94327c29c5f8a2749f0f0582a3ba51d89c8ab1b5`.
- r2 experiment source SHA-256:
  `3c0c39518fba5384c0fad3dcac535c29ab3bc20ef453c5ed1c9700f8022ec5c3`.
- State-conditioned ranker SHA-256:
  `60d1b710127e27c0bb283f073d6b166ccae14d9902ffb6d1911caa107d745678`.
- Policy diagnostics SHA-256:
  `bba137eb22258457f662950274580da473282416e9deb2989dd81f382bb0aea5`.
- r2 terminal postmortem SHA-256:
  `ea7c1eb8c2535d940d30956fc33bfd53e229c1587a2a362809b1e01fb1daceb1`.
- Current terminal baseline metrics SHA-256:
  `e53e12558232b6b97f1c78c60a7917fe77d5287cd8764dfd1ef4ed7c1d9cb76b`.
- Current card-cost repair closeout SHA-256:
  `cec6a2dae8269608a068c86784b8b033decf373a738bbcb910e155f99c1ce078`.
- Formal-readiness r2 report SHA-256:
  `d523f57b156af7bd87a166c2b9f6deb16a4d9670fe1463aaba2a0f0a0cfe304c`.

The audit read tracked source, specifications, and published reports only. It
did not load Torch or native simulator code, construct an environment, access a
seed, replay an episode, fit a model, launch gameplay, or modify a checkpoint.

## Architecture Gap

The r2 input path already validates exact API v3 snapshots and candidates,
recursively removes outcome, reward, seed, teacher, baseline, terminal, and
provenance fields, and produces deterministic CPU float32 hashed features.
However, `candidate_feature_matrix_v2` adds the same state vector to every
candidate vector before invoking a linear scorer. Relative scores therefore
cancel the state contribution exactly.

The new ranker closes the scorer-capacity defect but is intentionally not
integrated. No production or experiment path imports it, and the diagnostic
summarizer likewise has no producer for canonical scored-decision rows. A new
experiment would currently have to invent these two boundaries inside its
runner, which would mix architecture repair with empirical execution.

The existing API v3 projection semantics can be reused through a new additive
module. The r2-bound source must remain unchanged. The new module should use the
validated projected state and candidate mappings to create:

```text
state_features:     float32[hash_dim]
candidate_features: float32[candidate_count, hash_dim]
```

The state tensor is encoded once. Each candidate row is encoded with an empty
state mapping. The tensors are passed separately to
`StateConditionedCandidateRanker`; they must never be added together before
scoring.

## Comparator Roles

| Policy | Allowed role | Primary policy-quality comparator |
| --- | --- | --- |
| Current | Fixed non-teacher comparator candidate | Not yet; floor and structural closure are unproved |
| SimpleAgent | Auxiliary deterministic implementation control | No; teacher-sufficiency checks rejected it |
| Bottled | Auxiliary oracle, label, and diagnostic reference | No; it is not reward or policy-quality truth |
| Seeded initialization | Weak architecture/training control | No |
| r2 trained ranker | Negative historical policy evidence | No |

The Current bridge later closed the known potion, relic, and empty-cost
unplayable metadata defects. Those repairs improve future compatibility but do
not complete the consumed baseline attempt. That attempt retained only 18 of
the required 32 canary policy rows and terminated on
`card_metadata_cost_invalid` for `Injury`; it cannot be retried, resumed, or
reinterpreted.

Current is therefore the intended comparator for a future distinct study, not
an available comparator for an immediate experiment. A new Current study needs
its own rationale, identity, cohort, anti-retry contract, and explicit
execution authorization.

## Selected Source-Only Contract

The next OpenSpec change should be named
`add-state-conditioned-noncombat-policy-input` and remain limited to:

1. An additive versioned module producing separate state and candidate tensors
   from exact API v3 inputs.
2. Stable metadata binding projection version, feature version, hash width,
   dtype, device, and the state-conditioned ranker architecture identity.
3. A canonical scored-decision row builder accepted by
   `summarize_policy_diagnostics`, including candidate action IDs, kinds,
   scores, selected action, category, and decision identity.
4. Regressions for all four target categories, recursive leakage removal,
   exact repeatability, source non-mutation, candidate permutation, malformed
   input rejection, and integrated state-only ordering reversal.
5. Import-isolation proof that source-only registration validation does not
   load the native simulator, Communication Mod, gameplay, or checkpoint
   modules.

It should not edit `noncombat_simulator_rl_experiment.py`, create an experiment
runner, train a model, define a cohort, select thresholds, or claim policy
quality.

## Evidence Order After The Change

1. Complete and archive the source-only policy-input capability.
2. Perform a separate read-only post-repair Current comparator readiness review
   before proposing any new native execution. Preserve every consumed Current
   registration and seed.
3. If that review supports a distinct Current baseline proposal, preregister a
   fresh canary/holdout design and prove a credible fixed Current floor. A
   SimpleAgent, Bottled, or seeded-initial result cannot substitute for it.
4. Only after a credible comparator exists may a fresh r3 design be considered.
   It must use the separate tensors, mandatory anti-collapse diagnostics,
   Current as the fixed primary comparator, seeded initialization only as a
   secondary control, and a fresh cohort.
5. Keep the independent source-comparable target-supported outcome blocker open.
   Passing a simulator baseline does not authorize formal RL training.

## No-Go Boundary

This audit grants no r3 proposal, native loading, environment construction,
seed access, replay, cohort reuse, training, tuning, gameplay, checkpoint or
model loading, reward change, OPE, qualification, formal RL, or promotion. It
does not authorize modifying or retrying either consumed simulator experiment
or the terminal Current baseline study.
