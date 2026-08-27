# RL V2 Inventory Identity Encoding Specification

## Purpose

Define checkpoint-compatible potion and relic identity fallback plus auditable historical coverage for RL v2 state encoding.

## Requirements

### Requirement: Inventory identities use deterministic name fallback
The RL v2 state encoder SHALL resolve each occupied potion and relic using its existing preferred identity first and SHALL try the object's display name only when the preferred identity is absent from the bound stable vocabulary. An already-known preferred identity SHALL keep its existing numeric value.

#### Scenario: Internal potion ID is not a vocabulary key
- **WHEN** an occupied potion has an unknown internal ID and a display name present in the potion vocabulary
- **THEN** the encoder emits the existing numeric ID assigned to that display name

#### Scenario: Internal relic ID is not a vocabulary key
- **WHEN** an equipped relic has an unknown internal ID and a display name present in the relic vocabulary
- **THEN** the encoder emits the existing numeric ID assigned to that display name

#### Scenario: Preferred identity is already known
- **WHEN** the preferred inventory identity already resolves in the stable vocabulary
- **THEN** the encoder preserves that numeric ID without substituting the display-name result

### Requirement: Empty and unresolved inventory remains explicit
The RL v2 state encoder SHALL encode an empty `Potion Slot` as zero and SHALL retain zero for a non-empty object only when neither its preferred identity nor its display name resolves. The encoder MUST NOT use fuzzy or order-dependent matching.

#### Scenario: Potion slot is empty
- **WHEN** a potion object represents `Potion Slot`
- **THEN** the corresponding categorical slot is zero

#### Scenario: Both identities are unknown
- **WHEN** neither the preferred identity nor display name exists in the bound vocabulary
- **THEN** the corresponding categorical slot remains zero

### Requirement: Fallback is checkpoint compatible
The fallback SHALL NOT add, remove, reorder, or renumber vocabulary entries and SHALL NOT change categorical tensor shapes, vocabulary sizes, model parameters, or checkpoint schemas.

#### Scenario: Mapper and encoder are compared before and after the fix
- **WHEN** the same exported items payload and already-known inventory objects are encoded
- **THEN** all vocabulary sizes, numeric mappings, tensor shapes, and existing known-object encodings are identical

### Requirement: Historical coverage correction is reproducible
The audit SHALL require an exact chronological join between each registered real decision trace and complete replay snapshot, SHALL distinguish preferred-ID resolution, display-name fallback, and unresolved identities, and SHALL publish original and corrected inventory occupancy without mutating source evidence.

#### Scenario: Registered r14 and r15 evidence aligns
- **WHEN** every filtered trace row matches its replay transition on floor and normalized action family
- **THEN** the audit reports complete fallback coverage, per-source counts, identity counts, original-versus-corrected occupancy, and immutable input bindings

#### Scenario: Trace and replay do not align
- **WHEN** counts, floors, or normalized action families differ at any joined position
- **THEN** the audit fails without publishing a successful correction or modifying a checkpoint
