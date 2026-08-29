## MODIFIED Requirements

### Requirement: Real-context support before fitting

The system SHALL derive source-state context weights against the registered
fresh parent-only live guard-replacement opportunity target and SHALL apply the
unchanged coverage, effective sample size, maximum concentration, floor
coverage, weighted balance, legality, provenance, and seed-isolation gates
before constructing an optimizer.

#### Scenario: Aligned corpus support passes
- **WHEN** the merged fit, unchanged calibration, and merged fresh source states
  satisfy every unchanged context-support condition against the complete fresh
  live-opportunity target
- **THEN** the runner may derive pair and ranking weights and execute the
  existing registered paired control/successor fit exactly once

#### Scenario: Aligned corpus support fails
- **WHEN** any target sufficiency, coverage, concentration, balance, legality,
  provenance, or isolation condition fails
- **THEN** the experiment closes before optimizer construction, model fitting,
  calibration, fresh policy evaluation, additional gameplay, or tuning

## ADDED Requirements

### Requirement: Aligned target and fit registration

The system SHALL bind the immutable live target, merged successor corpora and
their support report, frozen r16 parent, fixed arm recipe, calibration rule,
deferred fresh evaluation, policy gates, resource limits, output paths, and
development-only authority before aligned support is evaluated.

#### Scenario: Every aligned input matches
- **WHEN** the target, corpora, parent, source, recipe, gate, resource, output,
  and authority hashes match the registration
- **THEN** the runner may evaluate support and conditionally execute the fixed
  paired fit without changing either arm

#### Scenario: Any aligned input differs
- **WHEN** a target row, corpus identity, parent byte, source, recipe, gate,
  resource, output, or authority field differs
- **THEN** execution stops before support evaluation or optimizer construction

### Requirement: One conditional paired execution

The system SHALL use identical context weights, source and pair rows, labels,
class/ranking samples, arm seeds, Adam `0.001`, 4,096 updates, calibration
procedure, and fresh rows for the current-state control and successor-delta arm.

#### Scenario: Aligned support passes
- **WHEN** the target and every unchanged support and integrity condition pass
- **THEN** both arms are fitted, frozen, calibrated, and evaluated once under
  the existing hard policy and descriptive paired-control decisions

#### Scenario: Fit or evaluation closes
- **WHEN** support fails or the conditional execution publishes a terminal
  decision
- **THEN** no additional target run, fit retry, seed substitution, threshold
  change, tuning, live candidate takeover, qualification, or promotion occurs
