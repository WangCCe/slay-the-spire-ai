## MODIFIED Requirements

### Requirement: Versioned Launchable Handshake Contract
The system SHALL hash-bind the preclaim handshake contract into every future launchable outcome-evidence registration and run lock while preserving historical evidence bytes.

#### Scenario: Future registration is launchable
- **WHEN** a new outcome-evidence registration is generated after this capability is implemented
- **THEN** it SHALL use the new schema version and fix the handshake protocol version, a 120-second readiness deadline, a 10-second release deadline, attempt/ready/release artifact names, implementation files, and fail-closed continuation rule
- **AND** `start` and `run-next` SHALL reject a registration that lacks or changes any required handshake binding

#### Scenario: Cold-start state arrives after the former deadline
- **WHEN** the exact registered child has sent protocol `ready` and receives and retains its first callback-free CommunicationMod state after 30 seconds but strictly before the 120-second readiness deadline
- **THEN** the child SHALL publish and validate the bound study-ready record without initializing exploration, callbacks, an agent, or gameplay before release
- **AND** the parent SHALL continue the existing preclaim verification instead of classifying the child as timed out solely because 30 seconds elapsed

#### Scenario: Extended readiness deadline expires
- **WHEN** the exact registered child remains alive but has not received a valid CommunicationMod state by the 120-second readiness deadline
- **THEN** the child and parent SHALL preserve the existing fail-closed timeout behavior
- **AND** the system SHALL NOT retry, extend, replace, claim, or release that child

#### Scenario: Exact deadline boundaries are fail-closed
- **WHEN** the child or parent first observes state or ready at or after the 120-second readiness deadline, or the child first observes release at or after the 10-second release deadline
- **THEN** the handshake SHALL reject the late condition before publishing ready, claiming a slot, or continuing after release
- **AND** exact-deadline observations SHALL be treated as expired rather than successful

#### Scenario: Historical v1 evidence is inspected
- **WHEN** an existing v1 registration is loaded for read-only verification
- **THEN** the verifier SHALL preserve its original schema and artifact interpretation without rewriting any byte
- **AND** the runner SHALL refuse to launch or resume a v1 registered slot after this change
