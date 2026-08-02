## ADDED Requirements

### Requirement: Reviewed Qualification Launch Vector Binding
The system SHALL provide one canonical builder and validator for the ordered qualifier CLI suffix, and the reviewed request source SHALL remain distinct from the absent active publication path.

#### Scenario: Canonical qualifier suffix is built
- **WHEN** an offline caller supplies a canonical qualification request, exact request file SHA-256 and size, and one lowercase reviewed commit R
- **THEN** the builder SHALL emit `qualify`, `--registration`, `--request`, `--request-hash`, `--request-file-sha256`, `--request-size`, and `--review-commit` in the trusted launcher's required order
- **AND** the `--registration` value SHALL equal the request's registered source path and the `--request` value SHALL equal `request_source_path`
- **AND** `--request` SHALL NOT equal the request's active `request_path`

#### Scenario: Candidate qualifier suffix uses the active request path
- **WHEN** a rendered candidate passes the not-yet-published active `request_path` to `--request` or differs from any canonical ordered value
- **THEN** offline validation SHALL fail closed before CommunicationMod publication or process launch
- **AND** the qualification identity SHALL receive no launch authority from that candidate
