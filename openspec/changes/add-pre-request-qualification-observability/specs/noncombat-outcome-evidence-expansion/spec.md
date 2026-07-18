## ADDED Requirements

### Requirement: Observable Future Qualification Gate
The system SHALL require every future replacement outcome-evidence qualification to pass the versioned pre-request observability contract before it can support a later reviewed `start` decision.

#### Scenario: A future replacement is prepared
- **WHEN** the observability implementation has passed regression, full-suite, strict OpenSpec, byte, and independent source-only review and a separate amendment prepares a previously absent qualification identity
- **THEN** that identity SHALL use qualification request/result/review-binding v3 and bootstrap-evidence v1 with a fresh source snapshot, review commit, request anchors, launch token, root, and exact CommunicationMod baseline
- **AND** no v1/v2 request, retired root, copied prefix, timeout increase, or cleanup operation SHALL substitute for a fresh v3 identity

#### Scenario: A future replacement supports start review
- **WHEN** a future v3 identity has one exact claim/stage/active-request/handoff/attempt/ready/release/zero-exit/terminal chain, restored request-bound isolation, no surviving child, externally pinned terminal anchors, and passing independent attestation
- **THEN** that evidence SHALL remain input only to a separate later review of whether to create the registered study run lock
- **AND** it SHALL NOT itself create the run lock, start collection, interpret OPE, change gameplay policy, make causal claims, train a model, or promote a policy

#### Scenario: Historical r1 through r6 evidence is replayed
- **WHEN** the preserved r1-r6 roots, requests, terminals, reports, or audits are inspected after v3 observability is implemented
- **THEN** every historical byte and its existing consumed, failed, obsolete, prepared, partial, or retired classification SHALL remain unchanged
- **AND** no historical v1/v2 identity SHALL be retried, upgraded in place, given synthetic bootstrap evidence, or used to authorize a future launch or `start`

#### Scenario: Observability implementation is complete but no replacement exists
- **WHEN** this change passes all offline implementation and review gates but no separate replacement amendment has been approved
- **THEN** the registered v2 study root SHALL remain absent and collection SHALL remain blocked
- **AND** completion of observability alone SHALL NOT authorize r7 preparation, a live game launch, study evidence collection, OPE interpretation, training, or policy change
