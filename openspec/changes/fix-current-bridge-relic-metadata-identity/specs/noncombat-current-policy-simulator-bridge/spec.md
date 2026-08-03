## ADDED Requirements

### Requirement: Closed Relic Metadata Identity Compatibility
The bridge SHALL resolve native relic identities through a closed table keyed by
stable native ID. It MUST require the exact expected native display name for
every table entry, require an exact canonical metadata record for every alias,
and permit metadata absence only for the exact simulator fallback identities
`CIRCLET` / `Circlet` and `RED_CIRCLET` / `Red Circlet`.

The closed metadata aliases SHALL be exactly:

- `BIRD_FACED_URN` / `Bird Faced Urn` / `Bird-Faced Urn`
- `CAPTAINS_WHEEL` / `Captains Wheel` / `Captain's Wheel`
- `CHARONS_ASHES` / `Charons Ashes` / `Charon's Ashes`
- `NILRYS_CODEX` / `Nilrys Codex` / `Nilry's Codex`
- `PHILOSOPHERS_STONE` / `Philosophers Stone` /
  `Philosopher's Stone`
- `SELF_FORMING_CLAY` / `Self Forming Clay` / `Self-Forming Clay`
- `DU_VU_DOLL` / `Du Vu Doll` / `Du-Vu Doll`
- `GOLD_PLATED_CABLES` / `Goldplated Cables` / `Gold-Plated Cables`
- `NEOWS_LAMENT` / `Neows Lament` / `Neow's Lament`
- `SLAVERS_COLLAR` / `Slavers Collar` / `Slaver's Collar`
- `DOLLYS_MIRROR` / `Dollys Mirror` / `Dolly's Mirror`
- `LEES_WAFFLE` / `Lees Waffle` / `Lee's Waffle`
- `NLOTHS_GIFT` / `Nloths Gift` / `N'loth's Gift`
- `NLOTHS_HUNGRY_FACE` / `Nloths Hungry Face` / `N'loth's Hungry Face`
- `PANDORAS_BOX` / `Pandoras Box` / `Pandora's Box`

The bridge MUST NOT infer another identity through punctuation removal,
possessive repair, compact-ID matching, fuzzy matching, or display name alone.

#### Scenario: A registered relic alias is hydrated
- **WHEN** a native relic has one registered stable ID and expected native name
  and its canonical metadata entry is present
- **THEN** the bridge SHALL hydrate the typed relic with the stable native ID,
  canonical metadata name, source slot when present, counter, and price
- **AND** it SHALL preserve the source snapshot and candidates byte-for-byte

#### Scenario: An audited fallback relic lacks metadata
- **WHEN** `CIRCLET` / `Circlet` or `RED_CIRCLET` / `Red Circlet` is encountered
  and its direct metadata entry is absent
- **THEN** the bridge SHALL hydrate that exact native identity without creating
  or selecting a metadata record
- **AND** no other stable ID or display name SHALL inherit this exemption

#### Scenario: A relic name already matches metadata
- **WHEN** an unlisted native relic display name directly matches one registered
  metadata name case-insensitively
- **THEN** the bridge SHALL use the existing exact-name hydration path
- **AND** the closed identity table SHALL NOT change its hydrated name

#### Scenario: A listed relic identity is inconsistent
- **WHEN** a listed stable ID has an unexpected native name, an alias target is
  absent from metadata, or an audited display name is supplied under another ID
- **THEN** the bridge SHALL fail closed with `relic_metadata_missing` before
  Current executes
- **AND** it SHALL NOT select a different metadata record or mutate the source

#### Scenario: An unregistered relic difference is encountered
- **WHEN** a native relic name is absent from metadata and its exact stable-ID
  and native-name pair is not one of the 17 table entries
- **THEN** the bridge SHALL preserve the existing structural blocker
- **AND** it SHALL NOT apply generic normalization or fallback hydration
