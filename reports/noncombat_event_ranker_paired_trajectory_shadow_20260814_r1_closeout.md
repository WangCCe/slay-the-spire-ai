# Event Ranker Paired Trajectory Closeout

## Decision

The raw event-ranker overlay is a simulator integration **no-go**. It may not be
promoted to gameplay or used as evidence that the learned event policy improves
whole-run value.

## Registered Result

- Cohort: seeds `94600..94727`, accessed once
- Complete pairs: 124 of 128; four registered Courier-restock censors
- Event-exposed pairs: 122; override pairs: 115; event overrides: 331
- Current: 0 victories, mean floor 22.387097, mean return 0.392756
- Raw overlay: 0 victories, mean floor 22.274194, mean return 0.390775
- Pair deltas: 30 improved, 31 worsened, 63 tied; no victory gains or losses
- Failed gates: mean floor noninferiority, mean return improvement, and improved
  pairs not fewer than worsened pairs

## Support-Domain Diagnosis

The bound training dataset contains 25 event identities. The raw overlay did not
check that support boundary: 74 of 331 overrides were made on unseen event
identities, affecting 36 pairs. In particular, `knowing_skull` was absent from
training but received 20 overrides across three pairs. All three pairs worsened,
with a combined floor delta of -48. This is a strong diagnostic association,
not a causal per-event estimate, because each selected trajectory can contain
multiple interacting overrides.

The stored confidence threshold is 0.50, while these extrapolating decisions had
only tiny score margins. It therefore behaves as an accept-all rule for most
non-tied model proposals and is unsafe without an explicit support boundary.

## Next Evidence Step

Evaluate a distinct policy configuration that overlays the same frozen model
only for event/candidate signatures present in its manifest-bound training
dataset, falling back to Current everywhere else. That configuration must use a
disjoint fresh paired cohort and fixed terminal gates. It is a new experiment,
not a retry or reinterpretation of this failed result.

