## MODIFIED Requirements

### Requirement: Readiness binds exact pushed source and immutable evidence
The readiness audit SHALL bind one pushed implementation commit, require local
`HEAD` and `origin/master` to equal that commit, require a clean tracked
worktree, and hash every auditor, verifier, consumed-terminal, bottleneck,
repair-closeout, historical-throughput, and contract input used by the
decision. The readiness contract SHALL be bound through the canonical main spec
at
`openspec/specs/noncombat-cross-fitted-empirical-successor-readiness/spec.md`
and SHALL NOT depend on an active or archived change path. The audit SHALL
reject missing, mutable, rehashed, or source-inconsistent inputs before any
rehearsal or candidate publication.

#### Scenario: All source and evidence bindings match
- **WHEN** every required Git blob and immutable artifact matches its registered path, size, and SHA-256 under one pushed commit, including the canonical readiness main spec
- **THEN** the audit may continue source-only and grants no registration, native, seed, fitting, training, or evaluation authority

#### Scenario: A lifecycle-dependent readiness spec path is used
- **WHEN** source binding names the retired active-change path, an archive path, or any readiness contract path other than the canonical main spec
- **THEN** the audit emits typed `no_go_source_binding` before rehearsal and does not substitute a nearby spec

#### Scenario: One bound input drifts
- **WHEN** `HEAD`, `origin/master`, tracked status, a source blob, consumed terminal artifact, closeout, contract, or historical throughput input differs
- **THEN** the claimed attempt emits typed `no_go_source_binding` before rehearsal, installs no final publication, and does not substitute a nearby file or commit

### Requirement: The candidate cohort is canonical and fully fresh
The audit SHALL reconstruct the complete historical seed inventory from the
bound Git tree and publish that canonical inventory. It SHALL derive exactly
the first 512 ascending nonnegative seeds absent from that inventory and all
reserved ranges. It SHALL extract the complete 512-seed schedule from the
consumed cross-fitted registration and require an empty intersection, including
the 500 scheduled positions that were never debited. The consumed schedule
SHALL contain exactly `canonical_search_start`, `chunk_count`, `chunks`,
`episodes_per_chunk`, `inventory_sha256`, `seeds`, `seeds_sha256`, and
`selection_schema_version`. Its canonical search start SHALL be `0`, its
inventory SHA-256 SHALL be
`435cf41b1cff21178d6de253677544b0e96f8b8ec431c181981aef36591a7174`, and its
selection schema SHALL be
`noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1`. Producer
validation and independent reconstruction SHALL use shallow or streamed
representations for the actual-scale inventory and SHALL NOT deep-copy or
concurrently materialize multiple complete canonical inventories.

#### Scenario: A fully disjoint candidate schedule exists
- **WHEN** the rebuilt inventory is canonical, its independent replay is byte-identical, the consumed schedule has the exact eight fields, canonical search start `0`, inventory SHA-256 `435cf41b1cff21178d6de253677544b0e96f8b8ec431c181981aef36591a7174`, and selection schema `noncombat-cross-fitted-hierarchical-learning-fresh-schedule-v1`, the candidate contains 512 ordered unique seeds, and its intersection with the consumed 512-seed schedule is empty
- **THEN** the audit records the candidate inventory/schedule digests and continues without treating any seed integer as an environment access

#### Scenario: Consumed schedule provenance drifts
- **WHEN** the consumed schedule omits or adds a field, changes canonical search start, changes inventory SHA-256, changes selection schema version, or supplies malformed provenance
- **THEN** readiness is `no_go_source_binding` before candidate inventory construction or rehearsal

#### Scenario: Only debited seeds are excluded
- **WHEN** any candidate seed belongs to the consumed registration even if that position has no access-journal debit
- **THEN** readiness is `no_go_cohort_not_fresh` and the schedule cannot be repaired by dropping individual collisions in place

#### Scenario: Candidate seed data is used empirically
- **WHEN** the change attempts to construct an environment, append an empirical access journal, fit, train, evaluate, or inspect an outcome for a candidate seed
- **THEN** the operation is forbidden and no readiness report is publishable
