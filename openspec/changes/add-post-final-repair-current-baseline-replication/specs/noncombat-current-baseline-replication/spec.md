## ADDED Requirements

### Requirement: Immutable Final-Replication Registration
The replication SHALL execute only from a clean pushed registration that binds the exact successor implementation, frozen Current policy and first-candidate control, Current bridge and dependencies, adapter and simulator, metadata and event semantics, native module, Windows runtime, complete consumed-study identity, post-repair readiness and closure evidence, tracked seed inventory, deterministic cohort algorithm and result, gates, limits, output inventory, and all-false downstream authority.

#### Scenario: Registration is complete and execution is separately authorized
- **WHEN** every tracked and external identity matches, local `HEAD` equals the registered pushed commit, the canonical output root is absent, and a later tracked authorization names the exact registration hash and command
- **THEN** the runner SHALL permit one empirical attempt and SHALL write a durable started journal before native loading or environment construction
- **AND** preregistration alone SHALL NOT authorize native loading, seed access, or execution

#### Scenario: Registration or authority drifts
- **WHEN** any source, predecessor artifact, repair evidence, module, runtime, cohort, algorithm, policy, threshold, limit, output, authorization, or authority field differs
- **THEN** source-only validation SHALL fail before the started journal, native loading, environment construction, or seed access
- **AND** it SHALL NOT substitute, search for, or repair any value at runtime

### Requirement: Deterministic Fresh Cohorts And Policy Isolation
The registration SHALL regenerate the tracked seed-exclusion inventory after the successor implementation commit, select the first 80 ascending unexcluded integer seeds at or above fixed search start `60000`, bind the first 16 as canary and the remaining 64 as holdout, and evaluate only frozen Current and deterministic first candidate in independent A0 Ironclad environments.

#### Scenario: Cohorts are materialized at preregistration
- **WHEN** the clean pushed implementation and tracked inventory validate
- **THEN** the registration SHALL bind exactly 80 unique ascending seeds produced by the fixed algorithm
- **AND** every consumed, selected, reserved, compatibility, diagnostic, training, evaluation, historical baseline, and old holdout seed SHALL be absent

#### Scenario: Cohort selection cannot be reproduced exactly
- **WHEN** the inventory changes, an overlap exists, the fixed search result differs, or a caller supplies, reorders, omits, replaces, or adds a seed
- **THEN** preregistration or execution validation SHALL fail closed
- **AND** no alternate search start, cohort, or runtime override SHALL be accepted

#### Scenario: A policy episode starts
- **WHEN** one registered seed is evaluated for one policy and replay
- **THEN** it SHALL receive a fresh independent environment with identical simulator configuration and baseline-controlled non-target behavior
- **AND** SimpleAgent and Bottled SHALL provide no action, label, fallback, reward, score, target, or comparison gate

### Requirement: Complete Conservative Episode Accounting
The replication SHALL retain exactly one canonical row per policy and selected seed, preserve both deterministic replay prefixes, include every selected row in aggregate and paired denominators, and treat only exact Courier support as a conservative non-victory.

#### Scenario: An episode terminates normally
- **WHEN** both replays reach the same player victory or loss within the registered limits
- **THEN** the row SHALL record terminal floor, outcome, target decisions, category coverage, action sequence, source hashes, and replay identity
- **AND** the row SHALL enter every registered aggregate and paired metric

#### Scenario: Exact Courier support is reached
- **WHEN** both replays stop at identical coordinates and prefixes with `unsupported_shop_courier_restock_semantics`
- **THEN** the row SHALL remain a non-victory at its last supported floor in every denominator
- **AND** the report SHALL record reason, seed, policy, count, rate, conservative metrics, and supported-only diagnostics that cannot authorize a pass

#### Scenario: Any other execution boundary fails
- **WHEN** identity, hydration, mapping, legality, transition, mutation, fallback, tracker, replay, native loading, resource, or publication behavior fails outside the exact Courier contract after the started journal
- **THEN** the attempt SHALL retain completed evidence and become terminally blocked
- **AND** no failed seed, policy, prefix, registration, or cohort SHALL be retried or replaced

### Requirement: Fixed Canary Stop Gate
The runner SHALL complete and reproduce all 16 canary pairs before accessing a holdout seed and SHALL use the canary only as an immutable stop decision.

#### Scenario: Canary passes
- **WHEN** all 16 paired rows are retained and replay-identical, both policies have zero unexpected failures and at most one declared-support row, Current covers route, shop, event, and card reward, Current mean floor is at least 15, and mean Current-minus-control floor is at least 0
- **THEN** the runner SHALL continue to the registered holdout within the same durable attempt
- **AND** no observed canary value SHALL change source, policy, cohort, threshold, bootstrap, support, limit, or authority

#### Scenario: Structurally valid canary does not pass
- **WHEN** every canary row is structurally valid but any coverage, support, absolute, or paired gate fails
- **THEN** the verdict SHALL be `replication_stopped_at_canary`
- **AND** every holdout seed SHALL remain unaccessed and the Current-baseline lane SHALL terminate

#### Scenario: Canary is blocked or interrupted
- **WHEN** any unexpected structural failure, bound, interruption, or invalid publication occurs after the started journal
- **THEN** the verdict SHALL be terminally blocked or interrupted with all available evidence preserved
- **AND** neither this identity nor another Current-baseline successor SHALL execute

### Requirement: Fixed Holdout Floor Gates
The replication SHALL classify a credible Current baseline floor only from all 64 retained holdout pairs using fixed conservative values and a deterministic percentile bootstrap.

#### Scenario: Every holdout gate passes
- **WHEN** both policies have zero unexpected failures and at most three exact Courier rows, Current covers all four target categories, Current mean floor is at least 18, its 95% bootstrap lower bound is at least 15, mean Current-minus-control floor is at least 3, and the paired 95% bootstrap lower bound is greater than 0
- **THEN** the verdict SHALL be `replication_valid_with_baseline_floor`
- **AND** it SHALL establish only a simulator Current baseline-floor result

#### Scenario: Structure passes without every quality gate
- **WHEN** all holdout rows and replays are structurally valid but any absolute, paired, coverage, support, or bootstrap gate fails
- **THEN** the verdict SHALL be `replication_valid_without_baseline_floor`
- **AND** the Current-baseline lane SHALL terminate without tuning, extension, repair, reinterpretation, or replacement

#### Scenario: Bootstrap metrics are produced
- **WHEN** complete holdout rows are classified
- **THEN** absolute Current floors and paired Current-minus-control floors SHALL use exactly 10,000 percentile-bootstrap resamples, confidence `0.95`, and seed `20260803`
- **AND** victories and supported-only summaries SHALL remain report-only diagnostics and SHALL NOT override a failed floor gate

### Requirement: Bounded Final Attempt Lifecycle
The replication SHALL allow repeatable source-only preparation and validation before a started journal, then exactly one empirical execution identity with at most 500 target decisions per episode, two replays per policy and seed, 64 canary policy executions, 256 conditional holdout policy executions, 600 canary seconds, and 1,800 total seconds.

#### Scenario: Source-only validation is repeated
- **WHEN** preparation or validation runs before a started journal exists
- **THEN** it SHALL load no native module, construct no environment, access no seed, and create no empirical result
- **AND** repeating the same read-only validation SHALL NOT consume the empirical attempt

#### Scenario: Empirical execution starts
- **WHEN** the exact pushed registration and authorization pass source-only validation
- **THEN** the runner SHALL atomically create the durable started journal before native loading
- **AND** any later success, failure, interruption, timeout, or publication problem SHALL consume the final replication identity

#### Scenario: A resource limit would be exceeded
- **WHEN** an episode, stage, policy-execution, total-execution, or wall-time limit would be exceeded
- **THEN** the attempt SHALL become terminally blocked
- **AND** the runner SHALL NOT extend, resume under another process, or classify the limit as declared support

### Requirement: Canonical Publication And No Downstream Authority
The replication SHALL atomically publish a fixed canonical artifact inventory, support fresh-process byte-identical verification without native loading, and keep gameplay, reward, OPE, model fitting, formal RL, training, qualification, loading, promotion, and target-supported-outcome authority false for every verdict.

#### Scenario: Terminal publication succeeds
- **WHEN** canary stops or conditional holdout completes
- **THEN** configuration, journal, rows, bootstrap draws, metrics, report, and manifest SHALL bind the registration and reproduce byte-for-byte without importing the native module
- **AND** measured timing SHALL remain outside canonical identity

#### Scenario: A baseline floor is demonstrated
- **WHEN** the verdict is `replication_valid_with_baseline_floor`
- **THEN** only a separate read-only baseline and formal-readiness refresh MAY consume the result
- **AND** target-supported outcomes and formal non-combat RL SHALL remain independently blocked

#### Scenario: A baseline floor is not demonstrated
- **WHEN** the verdict is stopped, blocked, interrupted, invalid, or valid without the floor
- **THEN** formal non-combat RL SHALL remain `no_go`
- **AND** no policy fix, diagnostic, replication, replacement cohort, training, or gameplay SHALL be triggered by this capability
