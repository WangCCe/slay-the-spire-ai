## Context

The four completed shop cohorts contain 112 unique source states. Five-fold OOF results show that both the candidate-only baseline and the state-conditioned ensemble have worse mean regret than Current, so another model search on the same support is not justified. The existing native collector already produces complete counterfactual branches and 1024-wide state/candidate tensors.

## Goals / Non-Goals

**Goals:**

- Collect 384 additional complete shop states from the fixed `95556..96323` seed schedule.
- Preserve exact source tensors, legal candidates, Current action, and every branch outcome in the existing canonical partition format.
- Prove independence from all 112 historical source hashes and publish enough coverage for a later retraining proposal.

**Non-Goals:**

- Training or evaluating a learned policy.
- Accessing the unused fresh shop schedule beginning at `95492`.
- Starting Slay the Spire or CommunicationMod, or loading production checkpoints.
- Retrying, replacing seeds, or widening limits after native collection starts.

## Decisions

### Use a contiguous disjoint training schedule

The collector will use 768 seeds from `95556..96323` and stop after exactly 384 complete sources. Previous cohorts required roughly two seeds per collected shop source, so this is bounded while retaining deterministic identity. The unused `95492..95555` schedule remains reserved for future external evaluation.

### Reuse the canonical state-conditioned partition

The expansion dataset will use the same `RoutePartition` codec and shared shop collector as the prior 112 sources. This avoids a migration and permits exact compatibility checks before later aggregation. A new generalized data platform was rejected as unnecessary for one bounded expansion.

### Gate publication on support and independence

The run must reach 384 complete sources, 192 informative sources, four action kinds, and 16 deterministic replays within 28,800 charged seconds. Every new source hash must be unique and absent from the exact-bound historical corpus. Failure is terminal and publishes no retraining authorization.

## Risks / Trade-offs

- [Collection may approach the eight-hour bound] -> Use the established native Windows runtime and stop at exactly 384 sources.
- [Seed yield may be lower than prior cohorts] -> Register twice as many seeds as target sources; do not replace them if support remains short.
- [Large branch artifacts consume disk] -> Store sparse canonical tensors and cap action branches at 6,144.
- [More data may still not improve OOF regret] -> This change grants only permission for a separate retraining attempt, not policy quality or promotion.

## Migration Plan

Commit the source-bound collector, run one native collection, verify the manifest and operation disclosures, and archive the change. On failure, leave the historical 112-source corpus and Current policy unchanged.

## Open Questions

None. Corpus evidence determines whether retraining is justified.
