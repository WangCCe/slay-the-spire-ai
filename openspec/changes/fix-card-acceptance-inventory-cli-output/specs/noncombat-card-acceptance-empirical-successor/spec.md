## ADDED Requirements

### Requirement: Inventory CLI completion output is bounded
After `build-inventory` or `verify-inventory` returns a validated inventory,
the CLI SHALL write one canonical completion envelope rather than serializing
the full inventory to stdout. The envelope schema version SHALL be
`noncombat-card-acceptance-empirical-successor-inventory-cli-completion-v1` and
its exact fourteen fields SHALL be `schema_version`, `operation`, `status`,
`request_sha256`, `output_path`, `inventory_path`, `inventory_size_bytes`,
`inventory_file_sha256`, `inventory_sha256`,
`inventory_launch_observation_sha256`,
`operation_launch_observation_sha256`, `receipt_path`, `receipt_sha256`, and
`completion_sha256`. The only valid operation/status pairs SHALL be
`build-inventory`/`published` and `verify-inventory`/`verified`. All paths SHALL
be resolved absolute paths rendered with forward slashes. `completion_sha256`
SHALL be the production canonical SHA-256 over the exact other thirteen fields,
excluding `completion_sha256` itself, including the canonical trailing newline;
the complete encoded envelope SHALL be no more than 2,048 bytes.

Completion generation SHALL require a closed output containing only a regular
non-symlink `seed_inventory.json`, no staging root, a canonical regular
non-symlink receipt with exact request/authorization/launch/source bindings,
and matching returned-artifact identities. It SHALL read the inventory bytes
once through a fixed-size streaming SHA-256, bind the resulting
`inventory_file_sha256`, and require regular-file identity and size to remain
unchanged before, during, and immediately after that read. It SHALL NOT parse
or reconstruct inventory content, alter direct Python operation results, or
grant verification, registration, training, or downstream authority.
`inventory_launch_observation_sha256` SHALL bind the build launch recorded by
the artifact and receipt, while `operation_launch_observation_sha256` SHALL bind
the current CLI operation launch. They SHALL match for build and MAY differ for
a distinctly authorized verification.

#### Scenario: Large build result completes with bounded stdout
- **WHEN** `build-inventory` returns a validated mapping whose non-envelope content is arbitrarily large and its closed output and receipt identities match
- **THEN** the CLI exits successfully and stdout contains only the canonical completion envelope within 2,048 bytes

#### Scenario: Verification result uses the same bounded contract
- **WHEN** `verify-inventory` independently reconstructs a closed inventory successfully
- **THEN** the CLI emits a `verified` completion envelope that separately binds the inventory/build launch and current verification launch and does not serialize reconstructed rows, exclusions, or cohorts

#### Scenario: Completion identity drifts
- **WHEN** the output is not closed, staging exists, the inventory or receipt is missing, non-regular, symlinked, noncanonical, or digest-invalid, file identity or size changes during hashing, or request/authorization/launch/source/artifact identities differ
- **THEN** completion generation fails closed without writing partial or full inventory stdout and grants no registration or downstream authority

#### Scenario: Completion exceeds its frozen bound
- **WHEN** the canonical completion envelope would exceed 2,048 bytes
- **THEN** the CLI fails before writing stdout rather than truncating, streaming, or weakening the identity

#### Scenario: Dispatch and direct APIs remain compatible
- **WHEN** callers invoke `check-dispatch`, `build_inventory`, or `verify_inventory` directly
- **THEN** dispatch canonical bytes and direct full-mapping return semantics remain unchanged while only build/verify CLI result publication uses the bounded envelope
