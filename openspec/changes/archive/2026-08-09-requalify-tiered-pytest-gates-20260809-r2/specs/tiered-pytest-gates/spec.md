## MODIFIED Requirements

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
directly when that shared source changes.

#### Scenario: Shared test infrastructure changes
- **WHEN** pytest configuration, the runner, the manifest, shared fixtures, or a `full_only` test changes
- **THEN** the documented validation boundary requires direct focused coverage for affected files and the `full` profile

#### Scenario: Routine domain code changes
- **WHEN** a coherent domain change is ready to commit and owns no `full_only` test
- **THEN** the documented workflow requires the relevant focused tests followed by `commit`

#### Scenario: Source owned by a full-only file changes
- **WHEN** a coherent source change is directly imported or referenced as an executable path by one or more `full_only` files
- **THEN** the documented workflow requires every affected owning file or a documented stricter focused set before `commit`, with `full` required at the configured complete boundary
