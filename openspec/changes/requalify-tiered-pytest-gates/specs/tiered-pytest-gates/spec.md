## MODIFIED Requirements

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

### Requirement: Bounded commit feedback
The measured `commit` profile SHALL complete in at most five minutes on the
designated Windows production Python under normal local load. The timing claim
MUST be supported by a recorded current qualification and MUST become invalid
after any observed conforming invocation exceeds five minutes.

#### Scenario: Commit profile is qualified
- **WHEN** the finalized `commit` profile is run on `D:\anaconda\envs\stsai\python.exe`
- **THEN** its test count, exclusions, result, and wall-clock duration are recorded and the duration is no more than five minutes

#### Scenario: Qualified timing later drifts
- **WHEN** a conforming `commit` invocation takes more than five minutes
- **THEN** the previous bounded-feedback claim is invalid until a measured requalification passes without weakening the complete suite

#### Scenario: Qualification is slow but tests pass
- **WHEN** a qualification run passes pytest but exceeds five minutes
- **THEN** correctness remains green, timing remains unqualified, and the runner does not retry or reinterpret the result

### Requirement: Explicit validation boundaries
Repository documentation SHALL state which changes require a focused profile,
direct whole-file validation, `commit`, or `full` validation.

#### Scenario: Shared test infrastructure changes
- **WHEN** pytest configuration, the runner, the manifest, shared fixtures, or a `full_only` test changes
- **THEN** the documented validation boundary requires direct focused coverage for affected files and the `full` profile

#### Scenario: Routine domain code changes
- **WHEN** a coherent domain change is ready to commit and owns no `full_only` test
- **THEN** the documented workflow requires the relevant focused tests followed by `commit`

#### Scenario: Source owned by a full-only file changes
- **WHEN** a coherent source change is covered by a `full_only` file
- **THEN** the documented workflow requires that file or a stricter focused set before `commit`, with `full` required at the configured complete boundary
