## ADDED Requirements

### Requirement: Seed inventory evidence is compact and bounded
The source-only seed inventory SHALL use schema
`noncombat-card-acceptance-empirical-successor-seed-inventory-v4`. It SHALL bind
the exact ordered source registry, each source byte SHA-256, size, format,
document count, and seed-occurrence row count; the total row count; the complete
sorted unique excluded-seed set and digest; fixed cohorts and role digests;
authority evidence; and the whole-inventory digest. It SHALL NOT inline
per-occurrence provenance rows.

Build and verification SHALL independently traverse the same registered source
bytes with the existing role semantics and compare the exact source registry,
per-source and total row counts, excluded seeds, cohorts, and digests. Inventory
construction SHALL accumulate counts and unique seeds without retaining a
repository-wide occurrence-row list. Canonical inventory bytes SHALL be no more
than 64 MiB and SHALL be checked before staging or output publication.

#### Scenario: Repeated provenance does not expand publication
- **WHEN** one or more registered fixtures contain arbitrarily many repeated occurrences of the same seed under valid seed contexts
- **THEN** row counts include every occurrence while the inventory stores only source identities, aggregate counts, and the unique excluded seed once

#### Scenario: Independent compact reconstruction matches
- **WHEN** build and verification scan the same closed registered source bytes
- **THEN** they reconstruct identical source identities, per-source and total row counts, excluded seeds, cohorts, role digests, and whole-inventory digest without comparing inline occurrence rows

#### Scenario: Aggregate evidence drifts
- **WHEN** a source byte identity, document count, row count, total row count, excluded seed, cohort, role digest, or inventory digest differs during validation or independent verification
- **THEN** verification fails closed and no registration or downstream authority is granted

#### Scenario: Canonical inventory exceeds its ceiling
- **WHEN** validated canonical inventory bytes would exceed 64 MiB
- **THEN** build fails before creating staging or output publication rather than truncating, compressing, splitting, or raising the bound

#### Scenario: Legacy inline rows are supplied
- **WHEN** a v3 inventory or a v4 mapping containing `rows` is supplied to the compact validator
- **THEN** it is rejected as the wrong schema or an unknown-field mapping and cannot be used for verification or registration

#### Scenario: Terminal r3 evidence is present
- **WHEN** the compact source repair and its tests are executed
- **THEN** the r3 output and receipt are not read, modified, deleted, verified, converted, or registered and parent task 6.2 remains incomplete
