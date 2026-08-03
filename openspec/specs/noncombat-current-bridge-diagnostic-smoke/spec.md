# Non-Combat Current Bridge Diagnostic Smoke

## Purpose

Define a preregistered, fail-closed reused-development-seed diagnostic for
testing Current policy own-trajectory structural closure without granting
fresh-evidence, baseline-floor, policy-quality, training, or promotion
authority.

## Requirements

### Requirement: Immutable Reused-Seed Diagnostic Registration
The diagnostic SHALL execute only from a versioned, pushed registration that binds the exact implementation, existing shop-support successor module, adapter and simulator provenance, Current bridge and policy sources, reachable-event and shop contracts, metadata, runtime, predecessor evidence, output inventory, fixed seeds and limits, and all-false authority.

#### Scenario: Registration is exact and pushed
- **WHEN** tracked files are clean, the registration and all tracked bindings equal their `HEAD` blobs, local `HEAD` equals `origin/master`, native and physical source identity match, and the output directory is absent
- **THEN** the diagnostic MAY write its started journal
- **AND** it SHALL construct no environment before that journal is durable

#### Scenario: Registration or identity drifts
- **WHEN** any bound byte, hash, size, schema, source identity, runtime field, module identity, pushed-state check, output name, limit, seed, or authority field differs
- **THEN** the diagnostic SHALL fail before environment construction
- **AND** it SHALL publish no structural pass claim

### Requirement: Fixed Consumed Development Seed Set
The diagnostic SHALL use exactly the ordered seeds `7000`, `7100`, `2000`, and `10`, with two fresh replays per seed, at most 500 target decisions per replay, and a 600-second whole-run deadline, without runtime overrides, replacement, or seed search.

#### Scenario: Fixed diagnostic starts
- **WHEN** the pushed registration passes every preflight check
- **THEN** the runner SHALL execute the four fixed seeds in registered order with two fresh environments and Current sessions per seed
- **AND** it SHALL identify every seed as previously consumed development evidence rather than fresh or formal evidence

#### Scenario: Caller requests a different cohort or limit
- **WHEN** a caller attempts to change seed membership, order, replay count, decision limit, deadline, or replace a failed seed
- **THEN** the runner SHALL reject the request before environment construction
- **AND** it SHALL NOT reinterpret the run as a new registration

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

### Requirement: Fail-Closed Diagnostic Verdict
The diagnostic SHALL publish exactly one verdict using fixed precedence and SHALL require complete retained coverage of the fixed seed set before any non-failure verdict.

#### Scenario: Unexpected structural failure occurs
- **WHEN** identity, environment construction, native snapshot or step, bridge evaluation, candidate legality, transition mapping, source mutation, fallback, tracker, determinism, decision limit, deadline, row inventory, or aggregate category validation fails outside the declared support case
- **THEN** the verdict SHALL be `current_bridge_diagnostic_failed`
- **AND** completed prior rows and the first exact failure SHALL be preserved without retry

#### Scenario: Every retained row is support blocked
- **WHEN** all four fixed seeds have deterministic declared-support rows and none has a terminal row
- **THEN** the verdict SHALL be `current_bridge_diagnostic_support_limited`
- **AND** Current own-trajectory structural closure SHALL remain absent

#### Scenario: Structural diagnostic passes
- **WHEN** all four fixed seeds have deterministic terminal or declared-support rows, at least one row is terminal, and aggregate route, shop, event, and card-reward counts are all nonzero across retained prefixes
- **THEN** the verdict SHALL be `current_bridge_diagnostic_passed`
- **AND** the result SHALL establish only that at least one Current own-trajectory row completes under the registered supported boundary

### Requirement: One-Shot Durable Diagnostic Attempt
The diagnostic SHALL persist a started journal before the first environment and SHALL never execute the same pushed registration more than once.

#### Scenario: Execution completes normally
- **WHEN** all fixed rows complete or a handled failure stops execution
- **THEN** the journal SHALL finalize with the registration hash, preregistration commit, attempted seeds, result hash, status, and verdict
- **AND** canonical artifacts SHALL preserve the complete result

#### Scenario: Execution is interrupted
- **WHEN** the process exits, hangs, times out externally, or is interrupted after the started journal is written
- **THEN** the started or partial journal SHALL remain the durable terminal attempt marker
- **AND** the registration SHALL NOT be repaired, resumed, or rerun

### Requirement: Canonical No-Native Verification
The diagnostic SHALL publish a fixed canonical artifact inventory and SHALL support deterministic verification without importing or loading the native module.

#### Scenario: Published result is valid
- **WHEN** the verifier reads the pushed registration, predecessor bindings, journal, retained rows, metrics, report, and manifest
- **THEN** it SHALL recompute every deterministic artifact and binding byte-for-byte without native loading or environment construction
- **AND** it SHALL reproduce the published verdict and row dispositions

#### Scenario: Publication drifts
- **WHEN** an artifact is missing, added, malformed, noncanonical, inconsistently bound, or differs from deterministic recomputation
- **THEN** verification SHALL fail closed
- **AND** the result SHALL NOT support a readiness refresh

### Requirement: Diagnostic Has No Policy Or Training Authority
The diagnostic SHALL keep fresh evidence, baseline-floor, policy-quality, target-supported outcome, gameplay, model, reward, OPE, formal-RL, training, qualification, policy/model loading, and promotion authority false for every verdict.

#### Scenario: Diagnostic passes
- **WHEN** the verdict is `current_bridge_diagnostic_passed`
- **THEN** only a separate read-only baseline-floor readiness refresh MAY be considered
- **AND** all eight floor-contract checks and the independent outcome-support blocker SHALL remain unchanged

#### Scenario: Diagnostic does not pass
- **WHEN** the verdict is support-limited, failed, interrupted, or unverifiable
- **THEN** formal non-combat RL and fresh baseline-floor evidence SHALL remain blocked
- **AND** the result SHALL NOT trigger gameplay, training, policy/model loading, qualification, or promotion
