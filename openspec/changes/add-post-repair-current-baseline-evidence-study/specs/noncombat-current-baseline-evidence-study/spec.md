## ADDED Requirements

### Requirement: Immutable Post-Repair Study Registration
The study SHALL execute only from a clean pushed registration that binds the
exact implementation, Current policy and bridge, adapter and simulator,
metadata and event semantics, native module, runtime, consumed diagnostic
lineage, completed schema and item-identity repairs, tracked seed-exclusion
inventory, cohorts, policies, gates, limits, artifact inventory, and all-false
authority.

#### Scenario: Registration is exact and execution is separately approved
- **WHEN** every tracked and external identity matches, local `HEAD` equals the
  registered pushed commit, the output root is absent, and a later explicit
  execution authorization names the same registration hash
- **THEN** the runner SHALL write a durable started journal before constructing
  an environment
- **AND** preregistration alone SHALL NOT authorize native loading or seed access

#### Scenario: Identity or authority drifts
- **WHEN** any source, evidence, module, runtime, cohort, threshold, limit,
  output, approval, or authority field differs
- **THEN** the runner SHALL fail before native module loading and environment
  construction
- **AND** it SHALL publish no floor claim or substitute another value

### Requirement: Fixed Isolated Cohorts And Policies
The study SHALL use exactly canary seeds `11000..11015` and holdout seeds
`12000..12063`, each in ascending order, and SHALL evaluate only frozen Current
and the deterministic first-candidate weak control in independent A0 Ironclad
environments. It SHALL allow at most 500 target decisions per episode, exactly
64 canary and 256 holdout policy episodes including replay, 600 seconds for the
canary, and 1,800 seconds for the whole attempt, without runtime overrides.

#### Scenario: Cohorts are proven untouched
- **WHEN** preregistration validates the tracked seed-exclusion inventory
- **THEN** all 80 study seeds SHALL be unique, disjoint, and absent from every
  registered prior consumed, fit, training, validation, test, compatibility,
  diagnostic, selected, or reserved seed
- **AND** no alternate, replacement, searched, or runtime-provided seed SHALL be
  accepted

#### Scenario: A policy episode starts
- **WHEN** one registered seed is evaluated
- **THEN** Current and first-candidate SHALL each receive a fresh independent
  environment with identical simulator configuration and baseline-controlled
  non-target behavior
- **AND** SimpleAgent and Bottled SHALL supply no action, label, reward, target,
  comparison gate, or fallback

#### Scenario: A resource bound is reached
- **WHEN** an episode, stage, policy-episode, total-episode, or wall-time bound
  would be exceeded
- **THEN** the attempt SHALL become terminally blocked
- **AND** the runner SHALL NOT classify the bound as declared support, extend
  it, or resume under another process

### Requirement: Complete Conservative Episode Accounting
The study SHALL retain exactly one canonical row per policy and selected seed,
preserve the complete deterministic target-action prefix, and keep every
selected episode in aggregate and paired denominators.

#### Scenario: An episode terminates normally
- **WHEN** a policy reaches player victory or loss within the registered limit
- **THEN** its row SHALL record terminal floor, outcome, decisions, category
  coverage, action sequence, source hashes, and replay identity
- **AND** the row SHALL enter every registered aggregate and paired metric

#### Scenario: An exact declared support blocker occurs
- **WHEN** both replays stop at the same coordinates and prefix with exactly
  `unsupported_shop_courier_restock_semantics`
- **THEN** the row SHALL be a non-victory at its last supported floor and remain
  in every denominator
- **AND** the report SHALL include reason, seed, policy, count, rate, and a
  supported-only diagnostic that cannot authorize a pass

#### Scenario: An unexpected or nondeterministic failure occurs
- **WHEN** identity, hydration, mapping, legality, transition, mutation,
  fallback, tracker, replay, bound, or publication behavior fails outside the
  exact support contract
- **THEN** the attempt SHALL retain completed evidence and become terminally
  blocked
- **AND** no failed seed, policy, prefix, or cohort SHALL be retried or replaced

### Requirement: Canary Is A Fixed Stop Gate
The runner SHALL complete and reproduce the entire canary before accessing a
holdout seed, and SHALL treat canary only as a stop decision rather than a
selection or tuning set.

#### Scenario: Canary passes
- **WHEN** all 16 paired rows are retained and replay-identical, both policies
  have zero unexpected failures and at most one declared-support row, Current
  covers route, shop, event, and card reward, Current mean floor is at least 15,
  and mean Current-minus-control floor is at least zero
- **THEN** the runner MAY continue to the immutable holdout under the same
  started journal
- **AND** no observed canary value SHALL change implementation, policy, cohort,
  threshold, bootstrap, support, limit, or authority

#### Scenario: Structurally valid canary does not pass
- **WHEN** all canary rows and replays are structurally valid but any coverage,
  support-rate, absolute, or relative check fails
- **THEN** the verdict SHALL be `study_stopped_at_canary`
- **AND** all 64 holdout seeds SHALL remain untouched and no replacement study
  SHALL be prepared in this change

#### Scenario: Canary has an unexpected structural failure
- **WHEN** any canary identity, environment, hydration, mapping, legality,
  mutation, determinism, bound, or publication check fails outside the exact
  Courier support case
- **THEN** the verdict SHALL be `study_blocked`
- **AND** all 64 holdout seeds SHALL remain untouched and the attempt SHALL NOT
  be retried

### Requirement: Untouched Holdout Floor Gates
The study SHALL classify a credible Current baseline floor only from all 64
retained holdout pairs using the fixed conservative values and deterministic
bootstrap contract.

#### Scenario: Every holdout floor gate passes
- **WHEN** both policies have zero unexpected failures and at most three
  exact Courier support rows, Current covers all four target categories,
  Current mean floor is at least 18, its 95% bootstrap lower bound is at least
  15, mean Current-minus-control floor is at least 3, and the paired 95%
  bootstrap lower bound is greater than zero
- **THEN** the verdict SHALL be `study_valid_with_baseline_floor`
- **AND** it SHALL establish only a simulator Current baseline-floor result

#### Scenario: Structure passes without every quality gate
- **WHEN** all holdout rows and replays are structurally valid but any absolute,
  paired, coverage, or support-rate floor gate fails
- **THEN** the verdict SHALL be `study_valid_without_baseline_floor`
- **AND** the runner SHALL NOT tune, extend, reinterpret, or rerun the study

#### Scenario: Bootstrap metrics are produced
- **WHEN** complete holdout rows are classified
- **THEN** absolute Current floors and paired Current-minus-control floors SHALL
  use exactly 10,000 percentile-bootstrap resamples, confidence 0.95, and seed
  `20260803`, with canonical draw hashes
- **AND** victories and supported-only summaries SHALL remain report-only and
  SHALL NOT override a failed floor gate

### Requirement: One-Shot Canonical Publication
The study SHALL allow one primary execution and one identical replay per policy
and seed within one durable attempt and SHALL atomically publish a fixed
canonical artifact inventory with no-native verification.

#### Scenario: Publication succeeds
- **WHEN** canary stops or the conditional holdout completes
- **THEN** configuration, journal, rows, bootstrap draws, metrics, report, and
  manifest SHALL bind the registration and reproduce byte-for-byte without
  loading the native module
- **AND** measured timing SHALL remain outside canonical identity

#### Scenario: Execution or publication is interrupted
- **WHEN** the process exits, hangs, is interrupted, exceeds a bound, or leaves
  a partial artifact after the journal starts
- **THEN** the journal and partial evidence SHALL remain the terminal attempt
  marker
- **AND** the registration SHALL never execute again

### Requirement: Baseline Evidence Has No Training Authority
Every registration and result SHALL keep gameplay, fresh live evidence, reward,
OPE, model fitting, formal RL, training, qualification, loading, and promotion
authority false.

#### Scenario: Baseline floor is demonstrated
- **WHEN** the final verdict is `study_valid_with_baseline_floor`
- **THEN** only a separate read-only baseline and formal-readiness refresh MAY
  consume the result
- **AND** the independent target-supported-outcome blocker SHALL remain blocked

#### Scenario: Baseline floor is not demonstrated
- **WHEN** the verdict is stopped, blocked, interrupted, unverifiable, or valid
  without the floor
- **THEN** formal non-combat RL SHALL remain `no_go`
- **AND** no diagnostic successor, replacement cohort, policy fix, training, or
  gameplay SHALL be triggered by this change
