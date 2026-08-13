## Context

The existing expanded corpus contains 497 train and 126 development card
states, but it branches only the first two card rewards reached by each seed.
The r2 live shadow cohort then exposed nine Ironclad rare card IDs absent from
train, including three `Immolate` offers that the model scored below skip. A
read-only 16-seed full-trajectory probe found 21 rare-containing reward states
across 13 seeds and all 16 Ironclad rare IDs, so targeted collection has usable
yield without broadening the simulator contract.

## Goals / Non-Goals

**Goals:**

- Collect complete counterfactual rows only when an ordinary card reward
  contains an Ironclad rare card.
- Add enough disjoint support to fit and evaluate per-card uplift values for all
  16 rare IDs.
- Refit the existing residual family against the unchanged r7 entry checkpoint
  and make the next fresh-evaluation decision from fixed development gates.

**Non-Goals:**

- Training a new neural entry policy, accessing the reserved audit seeds,
  running CommunicationMod/gameplay, or granting live action authority.
- Generalizing the collector into a configurable experiment framework.
- Tuning schedules, thresholds, or model grids after development results are
  observed.

## Decisions

### Add one explicit card-id eligibility input

`collect_counterfactual_partition` will accept an optional immutable set of
eligible take-card IDs. With no set it preserves the current first-card-reward
behavior. With the set, it advances the native root trajectory normally and
branches only when at least one legal take candidate has a target ID. This
keeps branch evaluation, reward semantics, censor handling, and source hashing
identical to the existing collector.

The alternative was a generic predicate callback. It would make the collector
more reusable but would enlarge the registration and test surface without a
current second use case.

### Use a fixed 256/64/64 schedule

Train uses `92000..92255`, development uses `92256..92319`, and audit reserves
`92320..92383`. At most two rare-containing states are collected per seed, with
2,048/512 branch ceilings and 16/4 registered-censor ceilings. The 16-seed
probe predicts roughly 336 train and 84 development states; fixed readiness
floors are 250 and 60 states, and every target ID must occur in both completed
partitions.

The alternative 512/128 schedule would roughly double collection time before
showing whether targeted residual fitting solves the observed failure.

### Merge rows, not simulator trajectories

After collection, the runner will restore the existing large train/development
datasets, verify schedule and source identity, and create merged partitions
whose seeds and rows are the disjoint unions of the old and targeted
partitions. Duplicate source hashes or cross-partition seed overlap fail before
fitting.

### Freeze entry, refit only the residual

The r7 entry checkpoint remains byte-identical. Configuration selection uses
merged train rows only; the selected residual is persisted and restored before
development rows are scored once. Existing overall regret/ranking gates remain,
with additional rare-only coverage and take-versus-skip diagnostics. A passing
result authorizes only a fresh simulator/live-shadow proposal.

## Risks / Trade-offs

- [Rare states are concentrated early] -> Report root decision-index coverage and
  keep the later untouched audit/fresh shadow gate; do not claim broad policy quality.
- [Per-card residuals can overfit 16 IDs] -> Select configuration on seed-level
  train folds and evaluate development once with no grid changes.
- [Long native collection can fail] -> Use fixed bounds, canonical terminal
  evidence, and leave all current model/production artifacts unchanged on
  failure.
- [Changing the shared collector invalidates old source bindings] -> Preserve
  default behavior and bind the new source commit in the new registration;
  completed historical studies remain immutable evidence.
