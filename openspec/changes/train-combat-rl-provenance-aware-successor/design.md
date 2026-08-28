## Context

The parity-qualified checkpoint contains 2,109 zero-update transitions. Its online and target networks equal production r16, all actions are legal, all 466 direct actions match frozen-r16 eval-mode greedy actions, and 1,643 outer-policy transitions carry executed-action anchor overrides. The checkpoint is training-only evidence and has no holdout or policy-quality authority.

Earlier parent-anchor continuations used roughly 1,000 optimizer updates and moved the full model by relative L2 `0.022..0.025`; weight `1.0` retained 88.13% parent greedy agreement. Those runs establish a useful scale but did not have reliable live executed-action provenance.

## Goals / Non-Goals

**Goals:**

- Exercise the existing RL v2 TD and provenance-aware anchor implementation on a real, parity-qualified replay.
- Produce exactly one reproducible development candidate with enough policy movement to justify an independent holdout.
- Separate fitting rows from development validation by complete combat groups.
- Make every input, recipe, metric, decision rule, and artifact hash reviewable.

**Non-Goals:**

- Tune weights, learning rate, update count, thresholds, or split after observing this corpus.
- Start Slay the Spire, collect new gameplay, evaluate live policy quality, promote a candidate, or replace production r16.
- Change runtime combat action selection, reward shaping, replay schema, or trainer objective semantics.

## Decisions

### Use the existing trainer objective rather than a parallel fitter

The runner will instantiate `DQNTrainerV2`, restore the checkpoint's r16 online and target states, load only the training split into `ReplayBufferV2`, freeze r16 as the parent anchor, and call `train_step()`. This directly exercises the deployed TD and executed-action override behavior. A separate custom loss was rejected because it could drift from trainer semantics.

### Split complete terminal-delimited combats

The runner will deterministically assign complete combat groups to an 80% fitting partition and a 20% development-validation partition using seed `2026082803`. Array adjacency will never define multi-step returns; each row keeps its stored one-step successor and terminal flag.

### Run one moderate full-network recipe

The fixed recipe is CPU execution, seed `2026082804`, Adam at `1e-4`, batch size `128`, parent anchor weight `1.0`, frozen target and parent networks, and `256` optimizer updates. This is about one quarter of the old 1,000-update anchored continuations, aiming for material but bounded drift without a recipe sweep.

### Evaluate both task fit and policy movement

The report will compare parent and candidate in eval mode on both partitions. It will report stored one-step TD loss, greedy action disagreement, provenance-aware anchor-label agreement, direct/override strata, positive-energy End Turn counts, parameter relative L2, and objective telemetry. The anchor label is the stored action on override rows and the frozen-parent mask-aware greedy action otherwise.

### Fail closed into development-only evidence

Fresh-holdout eligibility requires all finite values, exact input identity, deterministic artifact round trip, 256 completed updates with nonzero override sampling, lower validation TD loss, no decrease in validation anchor-label agreement, validation action disagreement in `0.02..0.15`, and positive-energy End Turn count delta at most two. A failed condition does not delete the candidate, but blocks alternate recipes and downstream evaluation on this corpus.

## Risks / Trade-offs

- [Risk] The 20% validation partition is small and comes from the same ten-game cohort. -> Mitigation: treat it only as a materiality and technical gate; require separately registered fresh replay before policy-quality claims.
- [Risk] Full-network fitting can exploit noisy one-step rewards. -> Mitigation: freeze target r16, retain anchor weight `1.0`, cap greedy drift, and require anchor-label agreement not to decline.
- [Risk] Dropout makes optimization stochastic. -> Mitigation: run on CPU with fixed Python, NumPy, and Torch seeds and verify repeatability in focused tests on synthetic replay.
- [Risk] Thresholds may reject a useful candidate. -> Mitigation: preserve the report for diagnosis, but do not tune on the same corpus; any new recipe requires a new proposal and new training evidence.

## Migration Plan

1. Add and test the offline runner without changing runtime imports or configuration.
2. Execute it once against the bound checkpoint and publish the immutable output directory.
3. If eligible, freeze the candidate hash and create a separate fresh-holdout registration. If ineligible, retain r16 and stop this recipe line.

Rollback consists of ignoring or removing the development-only report directory; no production state is changed.

## Open Questions

None. Downstream fresh-holdout size and live gate criteria are deliberately deferred until this fixed training result exists.
