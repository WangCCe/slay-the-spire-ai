## MODIFIED Requirements

### Requirement: Deterministic Terminal And Declared-Support Rows
The diagnostic SHALL preserve exactly one deterministic row per fixed seed whose disposition is either `terminal` or `declared_support_blocked`, and SHALL validate action legality, transition identity, source nonmutation, policy input hashes, Current mapping, event coordinates, fallback and tracker isolation, and replay equality. Candidate consumption SHALL use only fields guaranteed by the validated adapter candidate schema; evaluator-only action metadata SHALL NOT be required from a candidate.

#### Scenario: Both replays reach terminal state
- **WHEN** both fresh replays for a seed select only reported legal actions, produce identical canonical trajectories, and end with a valid player victory or loss
- **THEN** the diagnostic SHALL retain one `terminal` row with the replay count, terminal floor, outcome, decision prefix, category counts, and trajectory hash
- **AND** it SHALL treat floor and outcome only as structural diagnostics

#### Scenario: Both replays reach the Courier support envelope
- **WHEN** both replays fail during snapshot, candidate generation, or a post-step snapshot at the same coordinates with the exact underlying reason `unsupported_shop_courier_restock_semantics` and have identical retained completed-transition prefixes
- **THEN** the diagnostic SHALL retain one `declared_support_blocked` row with no terminal outcome
- **AND** it SHALL continue to the next fixed seed without dropping, replacing, or retrying the blocked row

#### Scenario: Support classification is not exact
- **WHEN** only one replay is blocked, coordinates or prefixes differ, or the native error is not the exact declared Courier reason
- **THEN** the diagnostic SHALL classify an unexpected structural failure
- **AND** it SHALL stop without executing later seeds

#### Scenario: Production candidate omits evaluator metadata
- **WHEN** a validated candidate contains exactly `action_id`, `category`, `available`, `kind`, `label`, and `raw`, and a Current evaluation selects its unique `action_id`
- **THEN** the runner SHALL evaluate and execute the candidate without reading candidate-side `action_type`
- **AND** it SHALL preserve the Current evaluation's non-empty string `action_type` in the decision row

#### Scenario: Current evaluation action metadata is invalid
- **WHEN** the selected Current evaluation omits `action_type` or provides a non-string or empty value
- **THEN** the runner SHALL classify an unexpected structural failure before action execution
- **AND** it SHALL NOT manufacture action metadata from the candidate
