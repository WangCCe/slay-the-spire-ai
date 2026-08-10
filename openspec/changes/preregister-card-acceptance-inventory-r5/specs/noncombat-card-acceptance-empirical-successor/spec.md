## ADDED Requirements

### Requirement: Verified compact r5 registration follows terminal r4
R4 SHALL remain terminal without accepted verification or registration. R5
SHALL use the pushed verification-hardening source, a distinct build identity,
and a distinct `inventory-verification` authority chain. R5 SHALL permit at most
one build process invocation and, after exact build publication, at most one
verification process invocation. Neither operation SHALL be retried, resumed,
reinvoked, tuned, or repaired in place after process creation or failure.

Only exact agreement among the compact v4 inventory, build receipt and bounded
completion, verification receipt and bounded flushed completion, source-only
reconstruction, and standalone structural verification SHALL authorize one
canonical all-false registration for the fixed `512/128/512` cohorts. Build or
verification completion alone SHALL grant no registration, training request,
or downstream authority.

#### Scenario: Distinct r5 passes the build gate
- **WHEN** r1-r4 are terminal, the hardened pushed source and path preflight are exact, every r5 write surface is absent, and fresh r5 build authority validates
- **THEN** the system permits one r5 build process invocation with no native, model, environment, training, evaluation, gameplay, qualification, promotion, or downstream authority

#### Scenario: Build invocation fails
- **WHEN** the r5 build process fails before or after receipt creation, lacks exact bounded completion, or leaves any access or child-process state ambiguous
- **THEN** r5 build is terminal without retry or reinvocation, no verification authority or registration is published, and a future attempt requires a distinct successor identity

#### Scenario: Distinct verification authority is derived from build evidence
- **WHEN** the compact inventory, build receipt, and completion are exact, tracked, committed, and pushed
- **THEN** one canonical verification request may bind their exact request, authorization, launch, receipt, file, and semantic digests before separate approval, authorization, and fresh launch publication

#### Scenario: Hardened verification invocation fails
- **WHEN** the one r5 verification process fails, its receipt or completion is missing or invalid, reconstruction differs, or any access state is ambiguous
- **THEN** r5 verification is terminal without retry or replacement, no registration is published, and parent task 6.2 remains incomplete

#### Scenario: R5 verification and standalone reconstruction agree
- **WHEN** source-only verification and the standalone verifier reproduce every compact source, count, exclusion, cohort, role, authority, receipt, output, and digest binding exactly
- **THEN** one all-false r5 registration may be published and parent task 6.2 may be completed while task 6.3 and every training or downstream authority remain incomplete

#### Scenario: A predecessor or legacy command is substituted
- **WHEN** r5 uses any r1-r4 request, authority, launch, receipt, output, verification binding, or the legacy build-only verification CLI shape
- **THEN** the operation fails before eligible evidence access and cannot authorize r5 verification or registration
