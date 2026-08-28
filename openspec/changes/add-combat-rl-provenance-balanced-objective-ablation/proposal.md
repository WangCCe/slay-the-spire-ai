## Why

Two separately collected provenance-aware successors changed `20/77` and `38/106` direct validation actions. The margin audit shows repeated high-margin and potion-to-play-card flips, supporting cross-stratum interference from a global anchor loss whose batches are roughly 80% override rows; lowering optimizer steps did not solve the problem.

## What Changes

- Add a provenance-balanced parent anchor that gives the direct and override strata equal aggregate weight while preserving per-row parent versus executed label semantics.
- Add an optional direct-only parent top-action margin guard with separate loss, eligibility, and ranking-violation telemetry.
- Preregister two 64-update CPU ablation arms on the existing R2 development corpus: balanced anchor alone, and balanced anchor plus a weight-1.0/cap-0.1 direct margin guard. The existing R2 candidate is the fixed reference and is not rerun.
- Permit this bounded same-corpus ablation only as objective-design evidence. It grants no candidate, holdout, gameplay, qualification, promotion, policy-quality, or production authority.
- Select at most one objective recipe for a later new-corpus attempt only if it meets the existing TD, overall materiality, direct drift, override uplift, End Turn, integrity, and serialization gates. Otherwise stop and investigate a separate residual or head.

## Capabilities

### New Capabilities

- `combat-rl-provenance-balanced-anchor`: Defines stratum-balanced anchor loss, direct-only margin protection, telemetry, and deterministic offline ablation behavior.

### Modified Capabilities

- `combat-rl-provenance-aware-successor`: Distinguishes bounded, preregistered objective-design ablations on a failed development corpus from candidate fitting and final holdout eligibility.

## Impact

- Affects `spirecomm/ai/rl/v2/trainer.py`, the offline combat successor runner, focused trainer/successor tests, and a new immutable ablation report.
- Uses only the committed R2 replay and frozen production-r16 parent on CPU; it does not start Slay the Spire or CommunicationMod and does not access or replace production checkpoints.
- Success means only that one objective recipe may be preregistered against a newly collected replay. Failure leaves current trainer defaults and production r16 unchanged.
