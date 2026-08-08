## ADDED Requirements

### Requirement: New registrations bind compact independently verified readiness evidence
Any new empirical-successor registration SHALL use a compact canonical registration schema that retains the complete 512-seed schedule and replaces an embedded historical inventory with exact bindings to one immutable pushed readiness publication commit, independent-verification receipt, report, and deterministic-gzip candidate artifact. The binding SHALL include the publication commit, canonical repository paths, stored sizes and SHA-256 digests, candidate canonical size and SHA-256, encoding, readiness identity, and verification-receipt identity. The publication commit SHALL contain all three exact artifacts, descend from the readiness source commit, and be an ancestor of the current pushed head. Historical embedded-inventory registrations SHALL remain verifiable against their own registered Git source but SHALL NOT be used to publish a new successor identity.

#### Scenario: A compact registration is built from eligible readiness evidence
- **WHEN** one independently verified readiness report is `go`, grants only registration-proposal eligibility, retains all downstream authority as false, and its exact candidate artifact reconstructs the registration source commit and complete fresh 8x64 schedule
- **THEN** the source-only builder may emit one all-false compact registration whose canonical digest transitively binds all three readiness artifacts without embedding the historical inventory

#### Scenario: A historical registration is verified
- **WHEN** an existing terminal bundle contains the embedded-inventory v1 schema
- **THEN** the independent verifier resolves source bytes from that registration's repository commit rather than the current worktree, while no new-registration builder may emit v1

### Requirement: Readiness evidence is reverified before dependency loading
For a compact registration, source-only inspection, request rendering, and execution preflight SHALL read the verification receipt, readiness report, and candidate artifact from their exact publication-commit Git paths. They SHALL bound each Git object before reading it, verify the receipt self-digest and exact publication bindings, then require the registered source commit, independently verified `go`, exact all-false authority, proposal eligibility, readiness identity, candidate binding, complete historical inventory, canonical fresh schedule, consumed cohort and its exact source binding, zero collisions, and registration schedule to agree before Torch, native, model, environment, fitting, training, or seed access is possible. Authority and eligibility values SHALL be exact JSON booleans, and seed and collision counts SHALL be exact JSON integers rather than numerically equal alternate JSON types. Every registration source-inventory row SHALL match its blob under the readiness source commit, and readiness's control-plane, terminal-verifier, seed-helper, successor-contract, and consumed-registration bindings SHALL match the exact registered implementation, contract, and historical cohort identities.

#### Scenario: Exact compact evidence passes
- **WHEN** the pushed verification receipt, report, and deterministic-gzip candidate match every registered path, byte binding, source identity, authority, freshness, disjointness, and schedule term
- **THEN** source-only validation records those checks and may continue to the unchanged source, runtime, native, isolation, request, approval, and authorization gates

#### Scenario: Readiness evidence drifts
- **WHEN** a publication commit, ancestry relation, verification receipt, report or candidate path, byte, digest, size, encoding, source commit, source row, required readiness binding, authority bit, decision, eligibility flag, readiness identity, seed, chunk, inventory digest, consumed-cohort term, or collision result differs
- **THEN** validation fails before dependency loading and does not substitute a nearby artifact, recompute another cohort, or alter the registration

#### Scenario: Old readiness is paired with changed execution source
- **WHEN** a compact registration cites a readiness report whose bound control plane, terminal verifier, seed helper, successor contract, or source commit predates any registered implementation byte
- **THEN** source-only validation fails before dependency loading even if the old report itself was a verified `go`

#### Scenario: Candidate decoding exceeds a bound
- **WHEN** candidate storage exceeds 64 MiB, canonical content exceeds 512 MiB, gzip bytes are nondeterministic or contain alternate members or trailing data, or JSON is noncanonical
- **THEN** validation stops within the registered bounds and grants no downstream authority

### Requirement: Compact evidence remains independently terminal-verifiable
The standard-library terminal verifier SHALL independently parse compact registration semantics, read registered source from the registration's immutable source commit, and re-read the exact readiness artifacts from the immutable publication commit without importing producer, readiness-auditor, Torch, runtime, native, gameplay, or CommunicationMod modules. The registration stored in the terminal bundle SHALL remain compact canonical JSON; external readiness inputs SHALL NOT be copied into or charged against the empirical output bundle, and all existing per-artifact and bundle ceilings SHALL remain unchanged.

#### Scenario: A compact terminal bundle closes
- **WHEN** producer preflight passed and all terminal artifacts are otherwise valid
- **THEN** the independent verifier reconstructs the readiness binding and schedule from pushed evidence and includes the compact registration digest in the unchanged terminal identity checks

#### Scenario: External readiness evidence is unavailable at closeout
- **WHEN** the verifier cannot read the exact pushed verification receipt, report, or candidate or independently reproduce its registered identity
- **THEN** terminal verification fails closed even if the producer's persisted source-preflight document claims that readiness checks passed
