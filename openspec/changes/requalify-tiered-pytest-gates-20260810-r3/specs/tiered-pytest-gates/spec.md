## MODIFIED Requirements

### Requirement: Bounded commit feedback
The measured `commit` profile SHALL complete in at most five minutes on the
designated Windows production Python under normal local load. The timing claim
MUST be supported by a recorded current qualification and MUST become invalid
after any observed conforming invocation exceeds five minutes. A
requalification after invalidation MUST freeze its measured whole-file
candidate set before the final invocation and MUST preserve any failed or slow
result without retrying or tuning that set afterward. A candidate set derived
from post-qualification ordinary test growth MUST be fixed by Git identity and
measured as one direct attribution suite before manifest publication. The
replacement boundary MUST be selected only by a preregistered per-file
eligibility and aggregate-margin rule applied to complete machine-readable
timing evidence. The attribution format, ownership mapping, duration phase,
and fail-closed completeness checks MUST be frozen before that suite runs. The
gate-affecting selection files MUST retain their frozen hashes before and after
each final gate and through the successful selection commit.

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

#### Scenario: Post-qualification ordinary tests form the candidate set
- **WHEN** Git identity fixes the complete ordinary test-file delta since the last valid qualification
- **THEN** the system measures that exact set directly, applies only the preregistered per-file and aggregate-margin rule, and does not tune candidates or thresholds in response to the attribution or final gate result

#### Scenario: Attribution evidence is incomplete
- **WHEN** a testcase lacks a unique frozen-file identity, has an invalid duration, disagrees with terminal counts, or exceeds the preregistered wall-time residual
- **THEN** attribution fails closed without manifest publication or a final qualification invocation

#### Scenario: Final gates retain selection identity
- **WHEN** a frozen replacement boundary is qualified and committed
- **THEN** the gate-affecting file hashes match the recorded ledger before and after both final gates and in the successful selection commit
