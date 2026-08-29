## ADDED Requirements

### Requirement: Source-bound parent-only target registration

The system SHALL register the exact source commit, target builder and live
shadow sources, production r16 checkpoint and parameter identity, context-cell
schema, four five-run batch identities, development-run exclusion set,
CommunicationMod configuration, trace and decision-state paths, run inventory,
resource limits, output paths, and no-takeover authority before formal gameplay.

#### Scenario: Registration matches before a batch starts
- **WHEN** every source, parent, schema, cohort, exclusion, configuration,
  resource, output, and authority field matches
- **THEN** the system may start or resume only the registered parent-policy
  batch until it has five completed unique runs

#### Scenario: A bound field differs
- **WHEN** any source, parent, configuration, batch, exclusion, output, or
  authority field differs
- **THEN** the batch stops before counting a run or publishing target evidence

### Requirement: Exact guard-replacement opportunity membership

The system SHALL include a target row only when the exact r16 parent selects
end turn, the deployed guard chooses a different legal action, the production
execution equals that guard action, candidate takeover is disabled, and the
shadow row joins uniquely to an in-combat decision state with the same floor
and turn within 100 ms.

#### Scenario: A deployment opportunity joins exactly
- **WHEN** parent, guard, execution, authority, state identity, floor, turn,
  timestamp, and monotonic sequence checks all pass
- **THEN** the target records the row's run, session, decision, floor stratum,
  HP ratio and quartile, occupied potion and relic counts, and context-cell ID

#### Scenario: Membership or joining is ambiguous
- **WHEN** the parent did not end turn, the guard did not replace it, execution
  differs, or the join is absent
- **THEN** the row is excluded with a named reason and cannot contribute target
  mass

#### Scenario: Join integrity is invalid
- **WHEN** the nearest join is ambiguous or a raw decision state would be
  reused, candidate takeover was possible, or a runtime error occurred
- **THEN** target publication fails and the row cannot enter the missing-join
  exclusion budget

### Requirement: Fixed fresh holdout sufficiency

The system SHALL build formal target evidence from exactly 20 new completed AI
runs in four registered five-run batches whose run seeds are unique and absent
from the 20 development-audit runs.

#### Scenario: Holdout is sufficient
- **WHEN** all 20 run records and four batch manifests are complete, at least
  300 target rows join, at least 20 joined rows are on floors 23 through 34,
  at most five eligible rows lack a join, the missing-join rate is at most one
  percent, and all parent, authority, seed, trace, and join integrity checks
  pass
- **THEN** the target may be sealed for one aligned support evaluation

#### Scenario: Holdout is insufficient
- **WHEN** the fixed runs yield too few total or late rows or any integrity
  condition fails
- **THEN** the target closes without adding runs, substituting sessions,
  changing membership, evaluating support, fitting, or training

### Requirement: Immutable context-target publication

The system SHALL atomically publish the registration, batch and run inventory,
input hashes, exclusion counts, joined context rows, per-batch summaries,
target identity, manifest, and authority without synthesizing replay actions,
rewards, or next states.

#### Scenario: Target publication succeeds
- **WHEN** every holdout, row, round-trip, size, and manifest check completes
- **THEN** one immutable target artifact is available only for the registered
  aligned support and conditional offline paired fit

#### Scenario: Target collection fails
- **WHEN** a batch or publication fails after gameplay starts
- **THEN** the failure is retained under its identity and no same-identity
  retry, different cohort, target definition, threshold, or candidate
  authority replaces it
