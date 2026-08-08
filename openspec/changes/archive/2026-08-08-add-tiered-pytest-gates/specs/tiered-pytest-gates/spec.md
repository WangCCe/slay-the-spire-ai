## ADDED Requirements

### Requirement: Named test profiles
The repository SHALL provide an explicit command that exposes `commit`, `protocol`, `gameplay`, `noncombat-evidence`, and `full` pytest profiles from a versioned manifest.

#### Scenario: Developer selects a profile
- **WHEN** the runner is invoked with a known profile
- **THEN** it prints the selected profile and resolved pytest command before running that profile

#### Scenario: Developer lists profiles
- **WHEN** the runner is invoked with `--list`
- **THEN** it reports every profile and its purpose without executing pytest

### Requirement: Inclusive commit gate
The `commit` profile SHALL collect the repository's configured test paths except for explicitly documented whole-file `full_only` entries.

#### Scenario: A new ordinary test file is added
- **WHEN** a test file is added under a configured pytest test path and is not listed as `full_only`
- **THEN** the `commit` profile includes that test without requiring a manifest edit

#### Scenario: A measured heavy test is excluded
- **WHEN** a whole test file is listed as `full_only` with a rationale
- **THEN** `commit` excludes it and `full` still includes it

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

### Requirement: Bounded commit feedback
The measured `commit` profile SHALL complete in at most five minutes on the designated Windows production Python under normal local load.

#### Scenario: Commit profile is qualified
- **WHEN** the finalized `commit` profile is run on `D:\anaconda\envs\stsai\python.exe`
- **THEN** its test count, exclusions, result, and wall-clock duration are recorded and the duration is no more than five minutes

### Requirement: Explicit validation boundaries
Repository documentation SHALL state which changes require a focused profile, `commit`, or `full` validation.

#### Scenario: Shared test infrastructure changes
- **WHEN** pytest configuration, the runner, the manifest, shared fixtures, or a `full_only` test changes
- **THEN** the documented validation boundary requires the `full` profile

#### Scenario: Routine domain code changes
- **WHEN** a coherent domain change is ready to commit
- **THEN** the documented workflow requires the relevant focused tests followed by `commit`
