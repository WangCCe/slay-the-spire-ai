## Context

The closed selective-classifier recipe used frozen r16 latent state, guard and
candidate action one-hots, and the legal mask. It converged over 4,096 updates
but selected 19 severe-harm actions. Severe errors span Defend, Strike,
Combust, several skills, and potions; parent Q margin does not separate them.

An action index identifies a slot and target, not the item occupying that slot.
The current head can recover item identity only by learning an interaction
between a flattened latent representation and an action one-hot from 3,806 fit
pairs. The ablation tests whether direct local semantics remove that burden.

## Goals / Non-Goals

**Goals:**

- Preserve the existing classifier and artifacts when item semantics are off.
- Expose candidate and guard item identity, local card features, family, and
  target directly to the head while keeping r16 frozen.
- Run one fixed CPU ablation and decide whether a new fresh corpus is worth its
  native-generation cost.

**Non-Goals:**

- Treating the consumed `263xxx` comparison as fresh or promotional evidence.
- Changing labels, optimizer, loss, updates, sampling, calibration, or the
  production guard.
- Loading native code, generating a corpus, starting CommunicationMod, running
  gameplay, or changing production r16 in this change.

## Decisions

### Backward-compatible optional feature path

`ActionRelativeSelectiveConfig` gains `include_item_semantics`, defaulting to
false. Existing artifacts omit the field and therefore retain the exact old
feature shape and policy. New artifacts bind the true value in their config and
artifact hash.

When enabled, each pair appends:

- frozen parent card embedding or potion embedding for the candidate;
- the corresponding frozen embedding for the guard;
- the 14 local hand features for candidate and guard card slots, zero for
  potion actions;
- candidate and guard family indicators; and
- candidate and guard target-slot one-hots.

The existing action one-hots and legal mask remain. Raw item one-hots were
rejected because they add a new trainable sparse representation with little
support. Parent Q margin was rejected because its observed correlation with
paired advantage is `0.031`.

### One source-committed development ablation

The runner keeps all recipe and input hashes as committed constants and accepts
only its source commit at execution. This replaces another multi-file
authorization protocol while retaining reproducibility and single-execution
output semantics.

Fit and calibration remain seeds `262000..262191` and `262192..262255`.
Seeds `263000..263127` are explicitly named `consumed_development_comparison`.
They decide only whether to invest in a separately proposed fresh corpus.

The item path is promising only with at least 30 interventions, precision at
least `0.55`, no more than 5 severe harms, mean selected advantage above
`0.17321939766407013`, mean regret below `3.1967246532440186`, and exact
legality, parent freezing, and artifact roundtrip. No condition may be changed
after execution.

### Verification budget

Use RED/GREEN feature and artifact tests, runner-focused tests, strict OpenSpec
validation, and exactly one timed commit gate for the completed source boundary.
Do not run a second full gate for report-only closure.

## Risks / Trade-offs

- [Frozen item embeddings may not encode combat value] -> The result is an
  ablation gate, not a promotion claim; close if fixed comparison gates fail.
- [Consumed comparison can reward architecture selection] -> Require a future
  fresh seed corpus before any qualification claim.
- [Card local features duplicate latent input] -> Duplication is intentional;
  the experiment tests whether direct candidate-local access is the missing
  inductive bias.
- [Feature extraction can misalign slots] -> Add exact card, potion, family,
  target, and old-artifact roundtrip regressions before fitting.

## Migration Plan

1. Add the optional feature path and backward-compatibility tests.
2. Add the compact fixed runner and focused comparison tests.
3. Commit the source recipe and execute the ablation once.
4. Publish pass/fail, run one final gate, sync, archive, commit, and push.

Rollback is non-use of the item-semantic development artifact. The default
configuration remains byte-compatible in behavior with the closed classifier.

## Open Questions

None for this ablation. A passing result would require a new change to select
fresh corpus seeds and authorize native generation.
