## ADDED Requirements

### Requirement: Request-Bound Qualification Isolation
The system SHALL bind broad live isolation into every newly reviewed launch qualification and SHALL require independent replay before that qualification can support a later `start` decision.

#### Scenario: Isolation baseline is reviewed
- **WHEN** a new qualification request is built before any live process or control artifact exists
- **THEN** request v2 SHALL canonically bind the original CommunicationMod bytes and semantics, AI marker state, recursive run-record inventory digest, registration-selected checkpoint inventory digest, and exact global AI-log states
- **AND** every digest SHALL cover sorted path, regular-file kind, byte size, and content SHA-256 observations under fixed absolute roots
- **AND** the producer SHALL reject missing required roots, malformed bytes, symlinks, Windows reparse points, non-regular entries, traversal ambiguity, or an incomplete observation

#### Scenario: Reviewed baseline drifts before child launch
- **WHEN** the qualifier starts and any marker, run, checkpoint, or global-log observation differs from the reviewed baseline
- **THEN** it SHALL fail before publishing an attempt or starting a child
- **AND** the live CommunicationMod configuration SHALL be accepted only when every non-command property equals the baseline and the command property exactly matches the trusted launcher derived from the external R and request anchors
- **AND** no completion, run lock, ledger, gameplay artifact, collection, or training authority SHALL result

#### Scenario: Qualifier restores and seals exact isolation
- **WHEN** the owned no-action child exits after a valid attempt, ready, and release lifecycle
- **THEN** the qualifier SHALL restore CommunicationMod to the exact request-bound original bytes, recollect every isolation observation, and prove the owned child PID is no longer alive before publishing completion
- **AND** a passing result SHALL bind the baseline hash, post-observation hash, exact comparison result, restoration result, and child-liveness observation
- **AND** any mismatch or restoration/process ambiguity SHALL fail closed without a passing terminal or live authority

#### Scenario: Controlled qualification failure occurs
- **WHEN** the qualifier encounters an ordinary failure after consuming the request
- **THEN** it SHALL terminate the owned child when required, attempt exact CommunicationMod restoration, recollect available isolation evidence, and bind every cleanup or isolation failure in the exclusive failure result
- **AND** a crash, failed terminal publication, or incomplete evidence prefix SHALL remain consumed and SHALL NOT be repaired, retried, or promoted

#### Scenario: Independent verifier replays isolation
- **WHEN** terminal evidence is supplied with exact external request, R, result self-hash, file-SHA, and size anchors
- **THEN** the standalone verifier SHALL independently recollect the current CommunicationMod, marker, run, checkpoint, and global-log state and require exact equality with the request baseline and terminal observations
- **AND** it SHALL independently require that the terminal child PID is not alive
- **AND** any missing field, schema mismatch, resource drift, process ambiguity, or collector disagreement SHALL reject verification and leave every study, run-lock, collection, policy, causal, and training authority false

#### Scenario: Historical v1 evidence is replayed
- **WHEN** immutable r1, r2, or r3 request and terminal evidence uses the prior schema without request-bound broad isolation
- **THEN** the verifier MAY replay that evidence only as historical consumed or failure evidence
- **AND** it SHALL identify the absent isolation binding and SHALL NOT use v1 evidence to qualify a new launch or authorize `start`
