## ADDED Requirements

### Requirement: Closed Potion Metadata Identity Compatibility
The bridge SHALL resolve a native potion display name that is absent from the
registered metadata only when its stable native ID, exact expected native name,
and exact canonical metadata name match one of these closed triples:
`ELIXIR_POTION` / `Elixir Potion` / `Elixir`, `FAIRY_POTION` /
`Fairy Potion` / `Fairy in a Bottle`, or `GAMBLERS_BREW` /
`Gamblers Brew` / `Gambler's Brew`. It MUST NOT infer any additional alias by
suffix removal, punctuation normalization, fuzzy matching, or display name
alone.

#### Scenario: A registered potion alias is hydrated
- **WHEN** a non-empty native potion has one registered stable ID and expected
  native display name and the canonical metadata entry is present
- **THEN** the bridge SHALL hydrate a typed potion with the stable native ID,
  canonical metadata name, source slot, and price
- **AND** it SHALL preserve the source snapshot and candidates byte-for-byte

#### Scenario: A potion name already matches metadata
- **WHEN** the native display name directly matches one registered metadata name
  case-insensitively
- **THEN** the bridge SHALL use the existing exact-name hydration path
- **AND** the closed alias mapping SHALL NOT change that potion's hydrated name

#### Scenario: A mapped identity is inconsistent
- **WHEN** a mapped native ID has an unexpected display name, its canonical
  metadata entry is absent, or a registered display difference is supplied with
  an unknown native ID
- **THEN** the bridge SHALL fail closed with `potion_metadata_missing` before
  Current executes
- **AND** it SHALL NOT select another metadata record or mutate the source

#### Scenario: An unregistered display difference is encountered
- **WHEN** a native potion display name is absent from metadata and the complete
  stable-ID/name pair is not one of the three registered triples
- **THEN** the bridge SHALL preserve the existing field-specific structural
  blocker
- **AND** it SHALL NOT apply generic normalization or fallback hydration
