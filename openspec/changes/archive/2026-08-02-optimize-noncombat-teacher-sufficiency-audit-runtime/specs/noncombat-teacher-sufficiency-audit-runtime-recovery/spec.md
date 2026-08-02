## ADDED Requirements

### Requirement: Preserve the consumed blocked attempt
The recovery SHALL bind the v1 registration and immutable failure record that
prove the sole execution exceeded its 120-second audit-body limit before
canonical publication. It MUST NOT retry, modify, reinterpret, or reconstruct
the consumed attempt, and it MUST retain all of its downstream authority as
false.

#### Scenario: Recovery registration is built
- **WHEN** implementation proof is complete and a v2 registration is requested
- **THEN** the builder SHALL validate and bind the exact v1 registration,
  failure classification, absent-output assertion, implementation/source
  identities, and no-retry status
- **AND** any lineage drift SHALL block before registration publication

### Requirement: Use one validated input context
Each run or strict-validation command SHALL decode and fully validate the train
archive exactly once, construct one explicit validated audit context, and pass
that context into the timed body. The timed body MUST NOT deep-copy,
recanonicalize, reload, or revalidate the complete dataset.

#### Scenario: A registered command reaches analysis
- **WHEN** all physical, runtime, corpus, lineage, and source checks pass
- **THEN** source reconstruction, representations, metrics, suitability, and
  report construction SHALL consume the same validated in-memory dataset
- **AND** archive-load/full-validation call counters SHALL remain one

#### Scenario: Unvalidated data reaches the optimized boundary
- **WHEN** a caller supplies a raw mapping, stale token, mismatched dataset
  identity, or context created outside the registered loader
- **THEN** the audit SHALL fail closed before canonical computation

### Requirement: Preserve exact representation bytes
The optimized path SHALL produce the same teacher-source,
adapter-observable-v1, legacy-hash-1024-v1, and structured-hash-2048-v1
candidate and decision signatures as the v1 reference for every valid fixture.
It MAY reuse only policy-view hashes already payload-validated and MAY cache
only exact per-decision structured global features.

#### Scenario: Reference and optimized fixtures are compared
- **WHEN** route/card fixtures cover leakage fields, ordered candidates, ties,
  duplicate semantic actions, maps, and structured numeric values
- **THEN** every semantic feature map, contiguous float32 vector byte string,
  candidate signature, decision signature, alias metric, suitability result,
  and verdict SHALL be exactly equal

#### Scenario: Cached or trusted data differs
- **WHEN** a stored policy-view hash is missing/reordered, its payload was not
  validated, a cached feature map crosses decisions, or any optimized byte
  differs from reference
- **THEN** equivalence SHALL fail and fresh registration SHALL remain forbidden

### Requirement: Prove runtime without registered corpus access
Before fresh registration, the recovery SHALL run a deterministic generated
workload containing 300 route and 302 card-reward multi-candidate decisions
through the optimized representation path under production Windows Python. It
MUST NOT read the registered train gzip or use registered seeds/states, and it
SHALL complete within 90 seconds.

#### Scenario: Synthetic performance gate passes
- **WHEN** fixture identity, row/category counts, no-corpus proof, exact outputs,
  and elapsed time all satisfy the fixed contract
- **THEN** the implementation MAY proceed to commit-gate verification and one
  fresh registration

#### Scenario: Synthetic performance or isolation fails
- **WHEN** the workload exceeds 90 seconds, touches a registered input, changes
  canonical semantics, or cannot prove exact counts
- **THEN** no fresh registration or real audit SHALL be created

### Requirement: Execute one fresh bounded recovery
The v2 registration SHALL preserve the v1 corpus, source interpretation,
signatures, semantic actions, dependency statuses, suitability checks, verdict
order, report schemas, and limits while adding only blocked-lineage and runtime
recovery identities. After it is committed and pushed, exactly one canonical
run MAY execute with the unchanged 120-second audit-body limit.

#### Scenario: Fresh audit publishes within bounds
- **WHEN** the one registered execution completes and strict recomputation
  matches every canonical byte
- **THEN** the original teacher-sufficiency change MAY consume its substantive
  verdict and complete
- **AND** every training, native, gameplay, qualification, and promotion
  authority SHALL remain false

#### Scenario: Fresh audit blocks or exceeds its bound
- **WHEN** identity, equivalence, resource, publication, or recomputation fails
- **THEN** the recovery SHALL publish or preserve a terminal failure record
- **AND** the v2 registration SHALL not be retried or tuned
