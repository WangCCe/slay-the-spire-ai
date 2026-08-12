## Context

The accelerated card-acceptance runtime can now complete a 64-pair training
chunk in about nine minutes, but its five-chunk exploratory run used random
rankers for route, shop, event, and card decisions. All episodes lost, and a
small family-logit shift changed frozen greedy behavior to all-take even though
take probability remained near 51%.

Native SimpleAgent is a stronger simulator trajectory policy, but its archived
card labels are `476 take / 1 skip`, so it cannot teach card acceptance. The
clean local Bottled `REQUESTED_STRIKE` oracle maps every archived card state and
provides a balanced auxiliary label set: train is `140 take / 160 skip / 2
bowl`; validation is `89 take / 81 skip / 5 bowl`.

## Goals / Non-Goals

**Goals:**

- Isolate card-policy learning while native SimpleAgent owns trajectory quality
  outside card rewards.
- Warm start the hierarchical card policy from mapped Bottled labels without
  using Bottled as reward or permanent ground truth.
- Run one bounded candidate-only residual pilot and compare it with a frozen
  native SimpleAgent control on already-consumed development seeds.
- Produce enough evidence to decide whether a separate fresh-evaluation change
  is justified.

**Non-Goals:**

- No protected holdout/final-test access, formal RL claim, tuning loop, live
  gameplay, CommunicationMod, production loading, OPE, or promotion.
- No change to the formal reward contract, saturation thresholds, native
  SimpleAgent, Bottled checkout, or live agent policy.
- No claim that Bottled labels or consumed development outcomes identify the
  optimal card policy.

## Decisions

### Use a hybrid native-baseline rollout boundary

Candidate trajectories query native SimpleAgent for route, shop, and event
actions and query the hierarchical candidate only for card rewards. Control
trajectories query native SimpleAgent for every action. Candidate and control
use separate environments constructed from the same seed. Every native query
must remain source-preserving and map to exactly one legal action.

This isolates the learned surface and retains competent non-card behavior.
Using the prior random frozen rankers was rejected because it produced no wins
and confounded card credit with weak route/shop/event behavior.

### Warm start card heads from Bottled-labeled archived states

The pilot reads only the existing train and validation demonstration rows. It
projects each source snapshot and complete candidate set through the current
state-conditioned feature bridge, evaluates the bound Bottled oracle from
offered cards, deck, and Singing Bowl context, and maps the result back to one
exact action id.

The family head receives cross entropy on `take` versus explicit non-take
families. The conditional head receives cross entropy within the selected
family. Training uses one fixed seed and schedule. Validation is a stop gate,
not a selection set: family agreement must be at least 0.70 and improve by at
least 0.10 over zero-step, exact action agreement must be at least 0.50, every
row must map, and greedy take/non-take rates must each be 5% to 95%.

SimpleAgent card labels are retained only for disagreement reporting. Direct
SimpleAgent card imitation was rejected because its observed family support is
effectively all-take. Loading the older all-category warm-start model was
rejected because it failed its rollout floor gate and does not match the dual
card-head architecture.

The fixed supervised schedule uses model and shuffle seed `0`, CPU Adam with
learning rate `0.001`, betas `(0.9, 0.999)`, epsilon `1e-8`, zero weight decay,
`128` epochs, and deterministic batches of `32`. Each batch minimizes the
equally weighted sum of mean family cross entropy and mean selected-family
conditional cross entropy. Singleton-family conditional terms remain explicit
zero-loss terms. There is no early stopping, validation-driven selection, or
schedule change after observing the one validation result.

The archived corpus uses adapter API v2 while the current leakage-controlled
feature projection requires exact API v3. The v3 source change adds event option
semantics; card-reward snapshots retain the v2 state and candidate contract.
The pilot therefore permits one card-only projection copy that changes only
`adapter_api_version` from v2 to v3 after validating the original hash,
category, legal candidates, and `decision_count == decision_index`. The bound
v2 source snapshot remains unchanged and is retained in every label row.

### Train only a candidate card residual

After the warm-start gate passes, the pilot may run at most four 64-pair chunks
on the already-consumed `1000..1031` plus `2000..2031` seed set. Only candidate
card parameters and Adam moments may change. Candidate advantages reuse the
accelerated four-fold, trajectory-disjoint baseline and the existing formal
victory-plus-floor reward. Native control has no optimizer and no learned
parameters.

After each chunk, the candidate is evaluated on a fixed source-state probe
collected before RL. The pilot stops before another chunk if any episode is
unsupported, checkpoint restoration differs, a gradient is invalid, or frozen
greedy take/non-take coverage leaves the inclusive 5% to 95% interval. It does
not change a coefficient, threshold, seed, or schedule after observing a result.

### Treat development comparison as a proposal gate only

The final frozen comparison uses the same consumed development seeds. Candidate
must have no fewer victories, no lower mean floor progress, no unsupported
episodes, and 5% to 95% greedy take coverage relative to native control. A pass
only permits proposing a fresh isolated evaluation. A fail keeps native
SimpleAgent as the effective baseline and terminates this pilot.

## Risks / Trade-offs

- **Bottled is strategy-specific** -> Bind its clean commit, report label
  distribution and SimpleAgent disagreement, and allow RL to deviate; never use
  the labels as reward.
- **The development cohort is reused** -> Limit all conclusions to mechanism
  and proposal readiness; do not infer generalization or policy quality.
- **The native control is not differentiable** -> Train candidate only and keep
  paired control rollouts strictly evaluative.
- **Card-only changes may alter later state support** -> Preserve complete
  trajectories, legal candidate sets, and per-seed paired outcomes; block on an
  unsupported transition.
- **Thresholds may be hard to reach with 302 train rows** -> Use a single fixed
  gate and stop on failure rather than tune within the change.

## Migration Plan

1. Add and test the native-baseline hybrid rollout bridge without training.
2. Add the archived-row Bottled mapping and deterministic card warm start.
3. Publish the fixed pilot registration and source-state probe.
4. Run at most one bounded pilot, then frozen development comparison.
5. Keep all artifacts outside production checkpoint discovery.

Rollback is deletion or non-loading of the exploratory candidate artifact;
native SimpleAgent remains unchanged and no production configuration is
modified.

## Open Questions

- Whether the fixed warm-start gate is reachable is intentionally answered by
  the one pilot; failure does not authorize another schedule.
- Whether a passing development result generalizes is intentionally deferred to
  a separately preregistered fresh cohort.
