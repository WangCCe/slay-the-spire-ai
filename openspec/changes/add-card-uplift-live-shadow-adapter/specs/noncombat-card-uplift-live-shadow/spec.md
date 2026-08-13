## ADDED Requirements

### Requirement: Shadow startup is explicit and source bound
The runtime SHALL remain inert unless `STS_CARD_UPLIFT_SHADOW_CONFIG` names a
canonical configuration that binds tracked source bytes, the source commit,
exact r7 entry and residual bytes, output path, projection version, and all-false
training, action, exploration, qualification, and promotion authority.

#### Scenario: Shadow mode is not configured
- **WHEN** the environment variable is absent
- **THEN** startup, callback wiring, model loading, logging, and Current behavior
  remain unchanged

#### Scenario: A configured binding drifts
- **WHEN** a source, model, schema, path, or authority binding differs
- **THEN** startup fails before registering a gameplay callback

### Requirement: Live projection is bounded and diagnostic
The projector SHALL score only ordinary non-combat rewards with exactly three
take candidates and one skip candidate, no bowl, and no generated combat card
choice. Every scored row MUST identify projection version
`live-best-effort-v1` and list known non-equivalent or estimated fields.

#### Scenario: An eligible card reward is observed
- **WHEN** Current returns an action for an eligible live card reward
- **THEN** the runtime constructs a validated API-v3-shaped snapshot and
  candidates, restores frozen scores, and records Current and shadow choices

#### Scenario: A card reward is outside the boundary
- **WHEN** the reward is generated in combat, has bowl, cannot skip, or does not
  expose exactly three cards
- **THEN** it is recorded as ineligible and no shadow score is used

### Requirement: Current retains action ownership
The shadow wrapper SHALL call Current exactly once and return the exact object
returned by Current under every eligible, ineligible, scoring-error, and
persistence-error path. It MUST NOT instantiate or substitute a gameplay
action.

#### Scenario: Shadow recommends a different action
- **WHEN** the frozen shadow choice disagrees with Current
- **THEN** the disagreement is recorded and the original Current action object
  is returned unchanged

#### Scenario: Shadow observation fails
- **WHEN** projection, model scoring, or JSONL persistence raises
- **THEN** the error is logged, does not cross the callback boundary, and the
  original Current action object is returned unchanged

### Requirement: Evidence rows are canonical and deduplicated
Each JSONL row SHALL include schema/projection/model/config identities, run key,
floor, decision ordinal, offer hash, Current and shadow action ids, base and
composed scores, agreement, known shifts, latency, status, and error or
ineligibility reason. Exact duplicate decision keys MUST be suppressed.

#### Scenario: A complete eligible row is written
- **WHEN** scoring and persistence succeed
- **THEN** the row is canonical JSON, finite, traceable to frozen bytes, and
  contains no mutable training state

### Requirement: Fresh shadow cohort gates a later canary
The live shadow study SHALL run with training disabled for at most five fresh
games. It SHALL require at least 12 complete eligible rows, at least three
Current-versus-shadow disagreements, zero shadow substitutions, zero runtime
errors, bounded latency, and intact model/config/source bindings.

#### Scenario: Every shadow gate passes
- **WHEN** the bounded cohort satisfies every structural, coverage,
  disagreement, identity, latency, and zero-substitution gate
- **THEN** the result authorizes only a separate card-intervention canary
  proposal

#### Scenario: A shadow gate fails
- **WHEN** the cohort ends without satisfying every gate
- **THEN** Current remains the policy owner and no intervention, promotion, or
  training authority is granted
