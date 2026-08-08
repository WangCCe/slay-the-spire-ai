## ADDED Requirements

### Requirement: The 20260808-r2 execution request is exact and non-authorizing
The system SHALL publish at most one canonical execution-request v1 derived from
the pushed registration
`noncombat-cross-fitted-hierarchical-learning-successor-20260808-r2` with
registration SHA-256
`9d792cadbece4ea21768386904633ebded2e94525fb186bdcbf4a4d7729dbdf9`.
Before rendering, the source-only CLI SHALL reverify the compact readiness
publication and exact registration. The request SHALL preserve the registration
identity, repository source, source-inventory digest, native/runtime identity,
registered output root, complete 8x64 schedule, resource ceilings, and resume
contract. Its `authority` SHALL remain all false; its requested-execution map
SHALL be true only for environment construction, execution, model fitting,
native loading, seed access, and training. The request SHALL grant no authority
without a later exact approval and tracked authorization.

#### Scenario: Exact request is rendered
- **WHEN** the pushed registration is byte-exact, immutable readiness replay
  passes, the registered output root and downstream sidecars are absent, and the
  source-only CLI exits successfully
- **THEN** one canonical request and deterministic review are published with an
  exact request digest, registration binding, producer readiness replay,
  independent structural validation, and zero blocked-dependency import delta

#### Scenario: A request term differs
- **WHEN** registration digest, identity, source, native/runtime binding, output
  root, schedule, resource, resume, operation, authority, requested authority,
  schema, request identity, or canonical serialization differs from the exact
  deterministic derivation
- **THEN** request publication fails closed without changing the registration,
  substituting a term, creating the output root, or loading a dependency

#### Scenario: Request is pushed without approval
- **WHEN** the exact request and review are present on `origin/master` but no
  exact delegated approval or authorization has been separately published
- **THEN** native loading, environment construction, seed access, fitting,
  training, execution, evaluation, gameplay, qualification, and promotion
  remain unauthorized

#### Scenario: Approval-chain content enters this change
- **WHEN** a standing-delegation resolution, delegated approval, authorization,
  execution journal, checkpoint, terminal bundle, or empirical output is
  included in the request publication scope
- **THEN** the change is invalid and SHALL stop before publication
