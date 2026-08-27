# tiered-pytest-gates Specification

## Purpose
Define validated focused, routine commit, and complete pytest profiles that
preserve fail-closed coverage boundaries while keeping normal pre-commit
feedback bounded on the designated Windows interpreter.
## Requirements
### Requirement: Named test profiles
The repository SHALL provide an explicit command that exposes `commit`, `protocol`, `gameplay`, `noncombat-evidence`, and `full` pytest profiles from a versioned manifest.

#### Scenario: Developer selects a profile
- **WHEN** the runner is invoked with a known profile
- **THEN** it prints the selected profile and resolved pytest command before running that profile

#### Scenario: Developer lists profiles
- **WHEN** the runner is invoked with `--list`
- **THEN** it reports every profile and its purpose without executing pytest

### Requirement: Inclusive commit gate
The `commit` profile SHALL collect the repository's configured test paths
except for explicitly documented whole-file `full_only` entries. Each
`full_only` entry MUST have fresh measured runtime evidence and a rationale,
and changing that file or its owned source MUST require direct focused
validation in addition to the complete boundary.

#### Scenario: A new ordinary test file is added
- **WHEN** a test file is added under a configured pytest test path and is not listed as `full_only`
- **THEN** the `commit` profile includes that test without requiring a manifest edit

#### Scenario: A measured heavy test is excluded
- **WHEN** a whole test file has fresh material runtime evidence and is listed as `full_only` with a rationale
- **THEN** `commit` excludes it, direct focused validation remains required for owned changes, and `full` still includes it

#### Scenario: An unmeasured exclusion is proposed
- **WHEN** a test file lacks fresh measured runtime evidence or a nonblank rationale
- **THEN** it remains in `commit` and the bounded-feedback claim cannot use that exclusion

### Requirement: Unchanged full validation
The `full` profile SHALL execute the repository's configured pytest test paths without applying `full_only` exclusions.

#### Scenario: Full validation is requested
- **WHEN** the runner is invoked with the `full` profile
- **THEN** it constructs the ordinary complete pytest suite using the existing repository configuration

### Requirement: Fail-closed manifest validation
The runner MUST validate the manifest and referenced file targets before launching pytest.

#### Scenario: Manifest is invalid
- **WHEN** the manifest has an unsupported version, unknown structure, malformed list, duplicate name, nonexistent file target, empty positive profile, or invalid `full_only` entry
- **THEN** the runner exits with a command-usage failure before invoking pytest

#### Scenario: Positive profile uses a node ID
- **WHEN** a domain profile contains a valid pytest node ID under an existing test file
- **THEN** the runner accepts the target for focused execution

### Requirement: Repository-local execution
The runner SHALL invoke pytest with the current Python interpreter, disable pytest's cache provider, and use a repository-local base temporary directory.

#### Scenario: Production Windows Python runs a gate
- **WHEN** `D:\anaconda\envs\stsai\python.exe` invokes the runner
- **THEN** the pytest child command uses that same interpreter and writes temporary test data under the repository

### Requirement: Faithful result reporting
The runner SHALL report wall-clock duration and preserve pytest's result status without automatic retry.

#### Scenario: Pytest fails
- **WHEN** a selected test fails, collection fails, or pytest is interrupted
- **THEN** the runner returns pytest's nonzero exit code and does not retry or report success

#### Scenario: Pytest passes
- **WHEN** all selected tests pass
- **THEN** the runner returns zero and reports the elapsed duration

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

### Requirement: Bounded commit feedback
The measured `commit` profile SHALL complete in at most five minutes on the
designated Windows production Python under normal local load. The timing claim
MUST be supported by a recorded current qualification and MUST become invalid
after any observed conforming invocation exceeds five minutes. A
requalification after invalidation MUST freeze its measured whole-file
candidate set before the final invocation and MUST preserve any failed or slow
result without retrying or tuning that set afterward.

#### Scenario: Commit profile is qualified
- **WHEN** the finalized `commit` profile is run on `D:\anaconda\envs\stsai\python.exe`
- **THEN** its test count, exclusions, result, and wall-clock duration are recorded and the duration is no more than five minutes

#### Scenario: Qualified timing later drifts
- **WHEN** a conforming `commit` invocation takes more than five minutes
- **THEN** the previous bounded-feedback claim is invalid until a measured requalification passes without weakening the complete suite

#### Scenario: Qualification is slow but tests pass
- **WHEN** a qualification run passes pytest but exceeds five minutes
- **THEN** correctness remains green, timing remains unqualified, and the runner does not retry or reinterpret the result

#### Scenario: Qualification is slow and one test fails
- **WHEN** a conforming qualification exceeds five minutes and pytest reports a failure
- **THEN** both timing and correctness remain unqualified, the exact result is preserved, and the invocation is not retried or used to tune exclusions

#### Scenario: Requalification candidates are frozen
- **WHEN** fresh whole-file measurements and rationales select a replacement `full_only` boundary
- **THEN** that exact boundary is validated before one final qualification and is not expanded in response to its outcome

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
