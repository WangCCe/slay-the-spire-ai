## ADDED Requirements

### Requirement: Readiness-derived artifacts are not historical seed evidence
The readiness producer and standalone verifier SHALL reconstruct historical seed evidence from eligible structured artifacts in the exact bound Git tree while excluding every canonical path that begins with `reports/noncombat_cross_fitted_empirical_successor_readiness_` or `reports/.noncombat_cross_fitted_empirical_successor_readiness_`. Exclusion SHALL occur before format selection, Git blob loading, decompression, JSON parsing, or recursive seed extraction. The two implementations SHALL independently reproduce the same included source bindings without importing one another. Existing handling for every other report path, supported format, malformed artifact, reserved range, and unsupported seed-like format SHALL remain unchanged.

#### Scenario: Prior readiness evidence is tracked
- **WHEN** the bound Git tree contains readiness attempt receipts, final publications, closeouts, predictable staging, or random sealed siblings under either excluded namespace
- **THEN** neither producer nor verifier loads those blobs or treats their candidate schedules, historical rows, or metadata as seed evidence

#### Scenario: Legitimate empirical evidence is tracked
- **WHEN** a supported structured report outside both excluded namespaces contains seed-valued fields
- **THEN** producer and verifier retain the report in the historical inventory under the existing canonical parsing and source-binding rules

#### Scenario: A lookalike path is tracked
- **WHEN** a report path contains readiness words or a candidate inventory basename but does not begin with either exact excluded namespace
- **THEN** the path is not excluded and existing supported-format or fail-closed unsupported-format handling applies

#### Scenario: Producer and verifier selection differs
- **WHEN** either implementation includes a path the other excludes or produces different included source bindings for the same bound Git tree
- **THEN** independent verification fails closed before publication and grants no proposal or downstream authority

### Requirement: Runner-owned staging is retired before terminal closure
The readiness runner SHALL record ownership only after it exclusively creates the exact source/output-derived staging directory. On every pre-install failure after ownership is established, including candidate canonical or stored ceiling failure, report construction failure, and independent-verifier failure or timeout, it SHALL remove only that exact runner-owned staging tree and prove absence before writing the terminal receipt. A pre-existing, replaced, mismatched, or otherwise unowned path SHALL NOT be deleted. Existing final-output, sealed-snapshot, process-tree, typed-decision, all-false-authority, and no-retry rules SHALL remain unchanged.

#### Scenario: Candidate serialization exceeds a ceiling
- **WHEN** streaming candidate publication crosses the unchanged stored or canonical byte ceiling after the runner created staging
- **THEN** the exact owned staging tree is absent before one typed `no_go_artifact_binding` terminal receipt is written, so no-publication receipt review can verify closure

#### Scenario: Independent verification fails
- **WHEN** the standalone verifier returns nonzero, times out, or rejects staged publication bytes
- **THEN** its process tree is confirmed absent, the exact owned staging tree is removed, no final output is installed, and the attempt terminalizes once as `no_go_artifact_binding`

#### Scenario: Staging existed before runner ownership
- **WHEN** the exact derived staging path exists before the invocation successfully creates it
- **THEN** readiness fails source binding without deleting or modifying that path and does not claim staging ownership

#### Scenario: Owned staging cleanup fails
- **WHEN** bounded removal of exact owned staging raises or absence cannot be proven
- **THEN** the runner writes one durable typed `no_go_artifact_binding` terminal receipt with cleanup diagnostics, leaves terminal verification and every downstream authority false, preserves any residue for review, and does not retry or delete through another path

#### Scenario: Publication succeeds
- **WHEN** all gates and independent verification pass and the verified staging snapshot is sealed and installed
- **THEN** existing verified-receipt, staging-retirement, sealed-copy, and atomic-output semantics remain unchanged
