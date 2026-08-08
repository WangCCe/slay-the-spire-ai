## ADDED Requirements

### Requirement: The 20260808-r2 delegated approval and authorization are exact and separately published
The system SHALL preserve the external-human standing grant from message
`item-22027` in task `019eb771-30f7-7ed2-9af2-ea4b22fadc11`, granted at
`2026-08-08T09:46:47Z`, in one canonical standing-delegation v1 manifest. Before
approval publication it SHALL confirm that no later explicit human revocation
exists. It SHALL resolve that manifest only to execution-request SHA-256
`6257a36c6573c8c412bb8727736e81b063dd0c7076f1ea5b41a70d4a08206c2e`
as delegated-approval v2. Only after that exact approval and its review are
pushed SHALL the system derive and separately push one tracked authorization
v1. The change SHALL stop without creating the registered output root or
performing any empirical operation.

#### Scenario: Standing delegation resolves the exact request
- **WHEN** registration and request bytes revalidate, the recorded grant and
  provenance match the external human message, and no later explicit human
  revocation exists at the publication check
- **THEN** one canonical standing delegation, delegated approval, and
  deterministic review are published with exact delegation, request,
  registration, source, and resolution bindings

#### Scenario: Grant provenance or revocation state is invalid
- **WHEN** grant text, grant time, message ID, task ID, external-human source,
  delegation scope, exclusion, self-digest, or current revocation state differs
  from the registered contract
- **THEN** approval publication fails closed without generating authorization,
  creating the output root, or performing an empirical operation

#### Scenario: Authorization follows pushed approval
- **WHEN** the exact delegated approval is present on `origin/master` and the
  producer and independent validator revalidate the complete approval chain
- **THEN** one canonical tracked authorization and deterministic review are
  published in a later commit, binding the unchanged request and only its exact
  requested authority map

#### Scenario: Approval and authorization are combined or execution begins
- **WHEN** approval and authorization enter the same publication commit, or the
  registered output root, native loading, environment construction, seed
  access, fitting, training, evaluation, gameplay, or execution appears in this
  change
- **THEN** the change is invalid and SHALL stop before publication
