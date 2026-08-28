## MODIFIED Requirements

### Requirement: Inclusive commit gate
The `commit` profile SHALL collect the repository's configured test paths
except for explicitly documented whole-file `full_only` entries and measured
node-level `commit_deselect` entries. Each exclusion MUST have fresh measured
runtime evidence and a rationale. Changing an excluded test or its owned source
MUST require direct focused validation in addition to the complete boundary.

#### Scenario: A new ordinary test is added
- **WHEN** a test is added under a configured pytest test path and is not listed in `full_only` or `commit_deselect`
- **THEN** the `commit` profile includes that test without requiring a manifest edit

#### Scenario: A measured heavy file is excluded
- **WHEN** a whole test file has fresh material runtime evidence and is listed as `full_only` with a rationale
- **THEN** `commit` excludes it, direct focused validation remains required for owned changes, and `full` still includes it

#### Scenario: A measured isolated node is excluded
- **WHEN** a test node has fresh material runtime evidence and is listed as `commit_deselect` with a rationale
- **THEN** `commit` deselects only that node, retains the containing file's other tests, direct focused validation remains required for owned changes, and `full` still includes it

#### Scenario: An unmeasured exclusion is proposed
- **WHEN** a test file or node lacks fresh measured runtime evidence or a nonblank rationale
- **THEN** it remains in `commit` and the bounded-feedback claim cannot use that exclusion

### Requirement: Unchanged full validation
The `full` profile SHALL execute the repository's configured pytest test paths
without applying `full_only` or `commit_deselect` exclusions.

#### Scenario: Full validation is requested
- **WHEN** the runner is invoked with the `full` profile
- **THEN** it constructs the ordinary complete pytest suite using the existing repository configuration

### Requirement: Fail-closed manifest validation
The runner MUST validate the manifest and referenced file targets before launching pytest.

#### Scenario: Manifest is invalid
- **WHEN** the manifest has an unsupported version, unknown structure, malformed list, duplicate name, nonexistent file target, empty positive profile, invalid `full_only` entry, or invalid `commit_deselect` entry
- **THEN** the runner exits with a command-usage failure before invoking pytest

#### Scenario: Positive profile uses a node ID
- **WHEN** a domain profile contains a valid pytest node ID under an existing test file
- **THEN** the runner accepts the target for focused execution

### Requirement: Bounded commit feedback
The measured `commit` profile SHALL complete in at most five minutes on the
designated Windows production Python under normal local load. The timing claim
MUST be supported by a recorded current qualification and MUST become invalid
after any observed conforming invocation exceeds five minutes. A
requalification after invalidation MUST freeze its measured whole-file and
node-level candidate set before the final invocation and MUST preserve any
failed or slow result without retrying or tuning that set afterward.

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
- **WHEN** fresh measurements and rationales select replacement `full_only` and `commit_deselect` boundaries
- **THEN** that exact boundary is validated before one final qualification and is not expanded in response to its outcome

### Requirement: Explicit validation boundaries
Repository documentation SHALL state which changes require a focused profile,
direct test validation, `commit`, or `full` validation. An excluded file or
node SHALL own every source module it directly imports or references as an
executable path. Shared source MAY have more than one excluded owner; all
affected owners or a documented stricter focused set MUST run directly when
that shared source changes. Narrow coherent changes SHALL use focused coverage
followed by `commit`; `full` SHALL be reserved for explicit complete boundaries
rather than routine red-green iteration.

#### Scenario: Shared test infrastructure changes
- **WHEN** pytest configuration, shared fixtures, complete-profile selection logic, or an excluded test changes in a way that can affect `full`
- **THEN** the documented validation boundary requires direct focused coverage for affected tests and the `full` profile

#### Scenario: Commit-only selection changes
- **WHEN** the runner or manifest changes only `commit` exclusions and runner regressions plus a dry-run prove the `full` pytest arguments remain unchanged and inclusive
- **THEN** runner-focused tests plus one frozen `commit` qualification are sufficient, and raw `full` remains reserved for the next configured complete boundary

#### Scenario: Selection-equivalent timing telemetry changes
- **WHEN** a gate-runner change affects only opt-in timing publication and regressions prove the selected pytest arguments remain equivalent
- **THEN** runner-focused tests plus `commit` are sufficient and `full` is not required solely for telemetry output

#### Scenario: Routine domain code changes
- **WHEN** a coherent domain change is ready to commit and owns no excluded test
- **THEN** the documented workflow requires the relevant focused tests followed by `commit`

#### Scenario: Source owned by an excluded test changes
- **WHEN** a coherent source change is directly imported or referenced as an executable path by one or more excluded tests
- **THEN** the documented workflow requires every affected owning test or a documented stricter focused set before `commit`, with `full` required at the configured complete boundary

#### Scenario: Release or phase-close boundary
- **WHEN** a broad cross-domain refactor, release, phase close, or explicit complete qualification is prepared
- **THEN** the unchanged inclusive `full` profile remains required and its exact result is recorded without retry
