## ADDED Requirements

### Requirement: Frozen artifact-replay commit boundary

The `commit` profile SHALL deselect exactly the six artifact-replay nodes frozen
by the 2026-08-29 timing audit, SHALL retain every other node in their containing
files, and SHALL leave direct pytest, positive domain profiles, and `full`
inclusive.

#### Scenario: Routine commit gate is constructed
- **WHEN** the repository manifest is loaded for the `commit` profile
- **THEN** the six measured artifact-replay node IDs are emitted as deselections
  and their containing files remain collected

#### Scenario: Full or focused validation is constructed
- **WHEN** the `full`, `protocol`, `gameplay`, or `noncombat-evidence` profile is
  selected, or a node is invoked directly
- **THEN** none of the six artifact-replay deselections weakens that validation

#### Scenario: Excluded ownership changes
- **WHEN** an excluded node, its directly owned source, its bound artifact
  schema, or an executable helper used by the node changes
- **THEN** that node is run directly before the routine `commit` gate

### Requirement: One-shot artifact-replay boundary qualification

The exact six-node boundary MUST receive one timing-enabled `commit`
qualification on the designated Windows production Python and MUST NOT be
expanded, retried, or tuned in response to the observed result.

#### Scenario: Frozen qualification passes the target
- **WHEN** the single qualification exits zero in no more than 190 runner
  seconds
- **THEN** its test count, exclusion count, timing report, and inclusive `full`
  dry-run evidence are recorded as the current routine boundary

#### Scenario: Frozen qualification is slow or fails
- **WHEN** the single qualification exceeds 190 runner seconds or exits nonzero
- **THEN** the exact result is preserved, no second qualification is run, and
  the six new exclusions are rolled back together without adding candidates
