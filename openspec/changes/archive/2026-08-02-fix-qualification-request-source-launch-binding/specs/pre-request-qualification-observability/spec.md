## ADDED Requirements

### Requirement: Offline Qualification Launch Vector Semantic Gate
Every future qualification preparation SHALL derive and validate its exact final CommunicationMod qualifier suffix against the reviewed request before publication.

#### Scenario: Offline go-no-go reviews the final vector
- **WHEN** a future replacement candidate renders its request, bootstrap envelope, launch token, and CommunicationMod command vector
- **THEN** the go/no-go evidence SHALL show that the final vector exactly equals the canonical builder output
- **AND** it SHALL explicitly prove that `--request` names the committed `request_source_path`, differs from the absent active request path, and carries the reviewed request hash, file SHA-256, byte size, and R

#### Scenario: Source and active request roles are confused
- **WHEN** the candidate vector uses the active publication path as the request source or the semantic vector check is absent, stale, or mismatched
- **THEN** the offline decision SHALL be no-go
- **AND** the system SHALL leave CommunicationMod, the external qualification root, game processes, study state, and training state unchanged
