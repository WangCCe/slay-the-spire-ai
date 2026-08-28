## 1. Paired Advantage Corpus

- [x] 1.1 Add regressions for canonical duplicate-slot actions, cloned branch return accumulation, unsupported-branch exclusion, and deterministic best-action tie-breaking.
- [x] 1.2 Implement bounded guard-intervention state sampling from the frozen r16 guarded LightSTS policy.
- [x] 1.3 Implement source-bound paired branch rollouts with the fixed eight-decision horizon, 0.99 discount, and whole-state exclusion semantics.
- [x] 1.4 Publish corpus coverage, advantage distribution, action diversity, encounter coverage, and provenance for train and seed-disjoint evaluation partitions.

## 2. Sufficiency Decision

- [x] 2.1 Encode and test the fixed positive margin and corpus sufficiency gate.
- [x] 2.2 Stop with a no-go report if the corpus lacks both classes, 100 positive training states, or three positive target identities. The registered corpus passed every condition, so fitting may proceed.

## 3. Post-Guard Residual

- [x] 3.1 If the corpus passes, add a frozen-parent post-guard residual with guarded-action input, legal masking, hard abstention, and exact artifact round trip.
- [x] 3.2 Fit exactly one registered CPU recipe and report train plus seed-disjoint classification metrics without threshold or optimizer tuning.
- [x] 3.3 Add a frozen residual policy path for LightSTS paired evaluation that records every intervention and preserves the guard action when abstaining.

## 4. Evaluation And Publication

- [ ] 4.1 Run the registered fresh paired simulator gate and publish victories, reward, HP, intervention, support, latency, and authority metrics.
- [ ] 4.2 Apply the fixed all-condition decision, retaining only a simulator-promising recipe or closing the POC without a sweep.
- [ ] 4.3 Run focused and adjacent offline tests, validate the OpenSpec change strictly, and commit only the implementation, bounded reports, and development-only artifact.
