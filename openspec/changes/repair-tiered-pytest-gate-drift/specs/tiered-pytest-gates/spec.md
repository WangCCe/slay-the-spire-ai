## ADDED Requirements

### Requirement: Opt-in machine-readable timing evidence
The gate runner SHALL optionally publish deterministic per-test and per-file timing evidence without changing the selected pytest profile, the pytest result, or default command behavior.

#### Scenario: Timing report requested
- **WHEN** a developer supplies a new absent timing-report path for a known profile
- **THEN** the runner executes that same profile once and publishes profile identity, pytest exit code, runner elapsed time, outcome counts, attributed per-file durations, and slow-test durations

#### Scenario: Pytest fails with timing enabled
- **WHEN** pytest returns nonzero while timing evidence is enabled
- **THEN** the runner publishes the observed timing evidence, returns the same nonzero exit code, and does not retry

#### Scenario: Timing report path is unsafe
- **WHEN** the requested report path already exists, escapes the repository, or cannot be attributed to complete pytest testcase evidence
- **THEN** the runner fails closed without overwriting evidence or claiming a qualified timing result

#### Scenario: Default command compatibility
- **WHEN** no timing-report path is supplied
- **THEN** the constructed pytest argv remains exactly compatible with the existing named profile command

### Requirement: Correctness-first gate repair
An invalidated commit qualification MUST repair observed correctness failures before selecting a replacement timing boundary and MUST NOT classify a failing file as `full_only` solely because it fails.

#### Scenario: Profiling baseline has failures
- **WHEN** a commit profiling invocation reports one or more failures
- **THEN** each independent failure cluster is repaired or explicitly remains a correctness blocker before candidate exclusions are frozen

#### Scenario: Frozen timing candidates
- **WHEN** post-repair machine-readable evidence identifies material whole-file costs with documented ownership and rationales
- **THEN** the exact replacement boundary is frozen before one final qualification and is not expanded after its result

## MODIFIED Requirements

### Requirement: Explicit validation boundaries
Repository documentation SHALL state which changes require a focused profile,
direct whole-file validation, `commit`, or `full` validation. A `full_only`
file SHALL own every source module it directly imports or references as an
executable path. Shared source MAY be owned by more than one `full_only` file;
all affected owning files or a documented stricter focused set MUST run
directly when that shared source changes. Narrow coherent changes SHALL use
focused coverage followed by `commit`; `full` SHALL be reserved for explicit
complete boundaries rather than routine red-green iteration.

#### Scenario: Shared test infrastructure changes
- **WHEN** pytest configuration, shared fixtures, profile selection logic, the manifest, or a `full_only` test changes
- **THEN** the documented validation boundary requires direct focused coverage for affected files and the `full` profile

#### Scenario: Selection-equivalent timing telemetry changes
- **WHEN** a gate-runner change affects only opt-in timing publication and regressions prove the selected pytest arguments remain equivalent
- **THEN** runner-focused tests plus `commit` are sufficient and `full` is not required solely for telemetry output

#### Scenario: Routine domain code changes
- **WHEN** a coherent domain change is ready to commit and owns no `full_only` test
- **THEN** the documented workflow requires the relevant focused tests followed by `commit`

#### Scenario: Source owned by a full-only file changes
- **WHEN** a coherent source change is directly imported or referenced as an executable path by one or more `full_only` files
- **THEN** the documented workflow requires every affected owning file or a documented stricter focused set before `commit`, with `full` required at the configured complete boundary

#### Scenario: Release or phase-close boundary
- **WHEN** a broad cross-domain refactor, release, phase close, or explicit complete qualification is prepared
- **THEN** the unchanged inclusive `full` profile remains required and its exact result is recorded without retry
