## Context

R1 used 256 updates on 1,722 fitting transitions. It improved validation TD loss from `3.80083` to `3.31689` and provenance-label agreement from `0.41344` to `0.59432`, but changed `236/387` validation decisions. Most changes (`203`) were desirable override-row `End Turn -> PlayCard` moves, while `20/77` direct rows also changed. The aggregate drift gate correctly blocked the candidate but could not distinguish those two effects.

## Goals / Non-Goals

**Goals:**

- Freeze a lower-budget recipe before observing a new replay cohort.
- Preserve production-r16 behavior on direct rows while learning a measurable share of executed outer-policy labels on override rows.
- Run exactly one new-corpus fit and make a fixed fresh-holdout decision.

**Non-Goals:**

- Refit, truncate, interpolate, or reevaluate the r1 candidate.
- Sweep optimizer steps, anchor weights, thresholds, splits, or seeds.
- Promote from development replay metrics or start a candidate gameplay gate in this change.

## Decisions

### Collect a new parity-qualified corpus after freezing the recipe

The change will register ten new collision-free seeds and collect production r16 with epsilon zero and learning starts above the entire batch. The resulting replay must pass the same zero-update, trace, inventory, boundary, legality, provenance reconciliation, and 100% direct eval-parent parity checks as the first parity cohort.

### Reduce the fixed optimizer budget to 64

Learning rate `1e-4`, batch size `128`, anchor weight `1.0`, frozen r16 target and anchor, 80/20 combat-group split, and CPU execution remain unchanged. Only the preregistered update budget changes from 256 to 64. This quarter-budget choice is made before the new corpus exists and is not adjusted after collection.

### Gate direct stability and override learning separately

Fresh-holdout eligibility requires:

- validation TD loss strictly improves;
- overall validation parent disagreement is at least 5%;
- direct validation parent disagreement is at most 10%;
- override validation executed-label agreement improves by at least 0.10 absolute;
- positive-energy End Turn count increases by at most two;
- all input, optimizer, provenance, finiteness, and serialization checks pass.

There is no aggregate maximum disagreement gate because override-row movement is the training objective. Direct-row drift is the safety boundary.

### Stop after one result

The runner will publish a development-only candidate even if a gate fails. Failure ends this recipe and grants no holdout authority. Success freezes the candidate hash for a separately registered holdout; it does not authorize gameplay.

## Risks / Trade-offs

- [Risk] Sixty-four updates may still be too strong or too weak. -> Mitigation: preserve the result and stop; do not tune on the new corpus.
- [Risk] A ten-game cohort may contain few direct validation rows. -> Mitigation: require both direct and override rows in each split and report exact counts; fail closed if either validation stratum is empty.
- [Risk] Override agreement can improve by copying noisy guards. -> Mitigation: keep TD improvement, direct stability, and a later independent holdout as separate requirements.
- [Risk] Real-game collection is slow. -> Mitigation: collect one bounded ten-game batch and do not run a candidate live gate in this change.

## Migration Plan

1. Commit the complete change and replay registration before launching the game.
2. Collect and audit exactly ten zero-update r16 games, then restore configuration and stop the game.
3. Bind the qualified replay hash, implement the stratified gate, and run focused verification plus one commit gate.
4. Execute one 64-update fit and publish the decision.

Rollback retains production r16 and ignores development-only artifacts; no production checkpoint is modified.

## Open Questions

None. Fresh-holdout sizing is deferred until a candidate passes this development gate.
