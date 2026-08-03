## ADDED Requirements

### Requirement: Fail-Closed Native Shop Support Envelope
The adapter SHALL prevent known-invalid simulator shop states and transactions from producing policy, compatibility, or training evidence while preserving supported shop decisions.

#### Scenario: A native shop decision has The Courier
- **WHEN** the player owns The Courier at a native shop decision
- **THEN** snapshot, candidate, native-baseline, and action execution entry points SHALL fail with `unsupported_shop_courier_restock_semantics` before returning or applying policy-consumable evidence
- **AND** the adapter SHALL NOT approximate replacement item, price, RNG, or preview semantics

#### Scenario: A shop potion cannot be obtained
- **WHEN** the player has Sozu or has no free potion capacity at an otherwise supported native shop decision
- **THEN** visible potion entries SHALL remain in the snapshot and `buy_potion` candidates SHALL be omitted
- **AND** card, relic, card-removal, and leave candidate semantics SHALL remain unchanged

#### Scenario: A supported A0 shop decision is evaluated
- **WHEN** an A0 native shop has no Courier and a potion transaction is obtainable
- **THEN** the adapter SHALL preserve the deterministic visible inventory, original source slots, affordability-filtered candidates, and transition behavior already required by the API v3 contract

#### Scenario: The support envelope blocks evidence
- **WHEN** a shop state or transaction falls outside the declared support envelope
- **THEN** gameplay, fresh cohort, baseline-floor, reward, OPE, formal-RL, training, loading, qualification, and promotion authority SHALL remain false
- **AND** unsupported evidence SHALL NOT be counted as a policy mismatch or successful compatibility row
