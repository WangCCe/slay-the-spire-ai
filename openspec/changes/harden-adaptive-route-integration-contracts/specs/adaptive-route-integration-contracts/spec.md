## ADDED Requirements

### Requirement: One-shot conservative recovery from adaptive candidate failure
When adaptive candidate generation or validation fails but the active map origin and committed route history remain valid, the system SHALL invoke the existing conservative route builder exactly once, validate its returned complete route, and commit that route with reason `candidate_generation_failed`.

#### Scenario: Irrelevant earlier map defect does not block fallback
- **WHEN** strict adaptive whole-map validation finds a malformed node that is earlier than and unreachable from the valid current origin
- **THEN** the system SHALL preserve the validated committed history prefix
- **AND** SHALL invoke the conservative builder exactly once without repeating strict whole-map validation
- **AND** SHALL commit the validated conservative full route with reason `candidate_generation_failed`

#### Scenario: Candidate production fails on a valid active branch
- **WHEN** either adaptive candidate is incomplete, truncated, disconnected, off-branch, or otherwise fails candidate validation while origin and history remain valid
- **THEN** the system SHALL discard the adaptive pair
- **AND** SHALL invoke and validate one conservative fallback candidate
- **AND** SHALL NOT retry adaptive or conservative generation again

#### Scenario: Committed history or active origin is invalid
- **WHEN** the existing route history is short, stale, disconnected, does not end at the current node, or the active decision origin cannot be resolved safely
- **THEN** the system SHALL propagate the integrity error
- **AND** SHALL NOT invoke a recovery planner or mutate route, metadata, or adaptive decision logs

#### Scenario: Conservative fallback output or implementation fails
- **WHEN** the one conservative builder raises an unexpected error or returns an incomplete, disconnected, off-branch, or otherwise invalid full route
- **THEN** the system SHALL propagate the error without another fallback
- **AND** SHALL leave route, metadata, and adaptive decision logs unchanged

### Requirement: Adaptive routing requires a heuristic map owner
The system SHALL reject full-RL startup with `--elite-route adaptive` because full RL owns MAP actions and does not execute the heuristic adaptive router. The system SHALL continue to support adaptive routing for `simple`, `optimized`, Ironclad `auto`, and `combat_rl` agents.

#### Scenario: Full RL requests adaptive routing
- **WHEN** agent type `rl` is constructed with elite route mode `adaptive`
- **THEN** startup SHALL fail before the RL factory, checkpoint loading, or learned MAP policy initialization
- **AND** SHALL report a stable error stating that adaptive routing requires a heuristic map owner

#### Scenario: Combat RL requests adaptive routing
- **WHEN** agent type `combat_rl` is constructed with elite route mode `adaptive`
- **THEN** its heuristic non-combat fallback SHALL receive adaptive mode
- **AND** MAP decisions SHALL continue through that heuristic owner without changing combat RL behavior

#### Scenario: Heuristic agent requests adaptive routing
- **WHEN** `simple`, `optimized`, or Ironclad `auto` is constructed with elite route mode `adaptive`
- **THEN** the resulting heuristic map owner SHALL initialize adaptive candidates, history, and observability

#### Scenario: Full RL uses a legacy route option
- **WHEN** agent type `rl` uses existing conservative or aggressive CLI input
- **THEN** this follow-up SHALL preserve its prior learned MAP behavior and startup compatibility

### Requirement: Complete outcome-aware adaptive decision record
Each successfully committed adaptive map decision SHALL emit exactly one parameterized INFO record prefixed `[ADAPTIVE_ROUTE]`. The record SHALL distinguish outcome and data availability and SHALL include validated normalized state, history, candidate summaries, minimum and added elite counts, fallback evidence, budget, selection, and reason codes whenever those values exist.

#### Scenario: Complete candidate pair is selected
- **WHEN** adaptive selection commits a success or forced candidate from a complete conservative/aggressive pair
- **THEN** the record SHALL identify outcome `success` or `forced`
- **AND** SHALL include valid HP percentage, elite exposure, latest rest floor, both candidate summaries, conservative minimum elite count, aggressive added elite count, budget, selection, and reasons
- **AND** SHALL mark fallback `not_used`

#### Scenario: Unsupported character uses conservative behavior
- **WHEN** adaptive mode commits the conservative route for an unsupported character
- **THEN** the record SHALL identify outcome `unsupported`
- **AND** SHALL mark the candidate pair `not_attempted`, pair-derived summaries/counts `unavailable`, fallback `not_applicable`, and reason `unsupported_character`

#### Scenario: Candidate generation uses conservative recovery
- **WHEN** adaptive candidate generation fails and the validated conservative recovery route is committed
- **THEN** the record SHALL identify outcome `candidate_generation_failed`
- **AND** SHALL mark pair-derived summaries/counts `unavailable`
- **AND** SHALL include the validated conservative fallback candidate summary with symbols, elite count/floors, and recovery distances

#### Scenario: Normalized state is invalid
- **WHEN** the current adaptive state cannot be normalized safely
- **THEN** the record SHALL mark state invalid and affected policy inputs unavailable
- **AND** SHALL NOT present normalization sentinels as valid HP percentage or history values

#### Scenario: Route decision does not commit
- **WHEN** candidate, fallback, chosen-path logging, payload preparation, or route validation raises before route commit
- **THEN** no `[ADAPTIVE_ROUTE]` decision record SHALL be emitted
- **AND** route and replan metadata SHALL remain unchanged

### Requirement: Fresh qualification after blocked whole-change review
The system change SHALL preserve the original adaptive automated PASS report and whole-change FAIL review without overwrite and SHALL require fresh follow-up evidence before task `4.4` or live qualification can proceed.

#### Scenario: Follow-up implementation is ready for qualification
- **WHEN** all follow-up task reviews and focused routing/main regressions are clean
- **THEN** one host-permission `gameplay`, `commit`, and `full` gate sequence SHALL run in order with no retry
- **AND** each reached command's raw terminal transcript, resolved command, unique basetemp, count, duration, and exit code SHALL be preserved separately from the original reports

#### Scenario: A fresh gate fails
- **WHEN** any fresh gameplay, commit, or full gate exits nonzero
- **THEN** follow-up qualification SHALL stop at that result
- **AND** a known stream-silence diagnostic SHALL remain attribution-only and SHALL NOT convert a failed full gate to success
- **AND** live qualification SHALL remain forbidden

#### Scenario: Fresh gates and review pass
- **WHEN** gameplay, commit, and full each exit `0`, final OpenSpec and diff validation are clean, and an independent whole-range review has no unresolved Critical or Important finding
- **THEN** the follow-up MAY satisfy the original adaptive change task `4.4`
- **AND** the previously specified bounded no-training live cohort MAY begin without changing defaults or persistent rollback configuration

#### Scenario: Fresh review finds a blocking issue
- **WHEN** the independent whole-range review reports a Critical or Important finding
- **THEN** both changes SHALL remain blocked
- **AND** the finding SHALL require a separately proposed change and new evidence rather than a same-attempt code fix
