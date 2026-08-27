## MODIFIED Requirements

### Requirement: Descriptive cross-source comparison
The calibration system SHALL compare only common strata meeting the registered
minimum count, SHALL publish numeric mean deltas and standardized mean
differences plus categorical total-variation and support-overlap measures, and
MUST keep degenerate variance and unsupported strata explicit. When an exact
real trace-to-replay join demonstrates source-encoder undercount for a compared
field, the calibration interpretation SHALL publish original and corrected
source summaries separately and MUST NOT attribute the explained portion to
simulator progression or mechanics.

#### Scenario: Common strata exist
- **WHEN** at least two floor strata contain the registered minimum number of real and simulator transitions
- **THEN** the system ranks numeric and categorical mismatch signals separately and reports all source counts used by each comparison

#### Scenario: Coverage is insufficient
- **WHEN** fewer than two strata meet the common-support requirement
- **THEN** the report is technically incomplete and grants no follow-up experiment authority

#### Scenario: Exact trace evidence explains encoded inventory undercount
- **WHEN** immutable real traces align one-to-one with replay transitions and occupied display names resolve where replay categorical IDs are zero
- **THEN** a correction addendum binds the initial calibration, quantifies explained undercount, and leaves residual differences descriptive

#### Scenario: Exact trace evidence is absent or misaligned
- **WHEN** the trace source is unavailable or cannot be joined exactly to replay transitions
- **THEN** the system makes no corrected-source or encoder-attribution claim
