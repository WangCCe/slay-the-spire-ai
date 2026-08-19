## ADDED Requirements

### Requirement: Opt-in guarded frozen-parent replay behavior
The LightSTS trainer SHALL preserve uniform non-EndTurn collection by default and SHALL optionally collect replay from an immutable warm-start parent transformed by the registered deployment guard proxy.

#### Scenario: Parent branch
- **WHEN** the guarded-parent mode selects the parent branch below the action-per-turn cap
- **THEN** the frozen parent selects a raw legal action, the proxy transforms it, and replay stores the action actually executed

#### Scenario: Exploration branch
- **WHEN** the deterministic RNG draw is below the registered epsilon
- **THEN** collection uses the existing seeded selector, executing a legal non-EndTurn action when one exists and otherwise EndTurn

#### Scenario: Forced turn bound
- **WHEN** the action-per-turn bound is reached
- **THEN** collection executes EndTurn without proxy replacement

### Requirement: Behavior configuration integrity
The guarded-parent behavior SHALL require an immutable warm-start checkpoint, a registered guard proxy, and finite epsilon in `[0, 1]`.

#### Scenario: Invalid guarded behavior
- **WHEN** the parent checkpoint or proxy is absent, the mode is unknown, or epsilon is outside the valid range
- **THEN** the runner fails before trajectory collection or fitting

#### Scenario: Default compatibility
- **WHEN** uniform behavior is selected
- **THEN** existing seeded collection behavior remains unchanged

### Requirement: Behavior evidence and authority
The simulator corpus report SHALL bind mode, epsilon, branch counts, and guard intervention counts without granting production authority.

#### Scenario: Guarded collection completes
- **WHEN** guarded-parent collection publishes a report
- **THEN** parent, exploration, forced-EndTurn, raw-parent-EndTurn, eligible proxy, replacement, and unsupported replacement counts are recorded

#### Scenario: Simulator-only authority
- **WHEN** a candidate is trained from guarded-parent replay
- **THEN** it remains production-incompatible and grants no gameplay, transfer, qualification, or promotion authority

### Requirement: Fresh deployment-consistent experiment gate
The first guarded-parent behavior candidate SHALL use registered unused train and evaluation seeds with complete discounted-return targets and guard-aware evaluation.

#### Scenario: Gate fails
- **WHEN** any registered technical, reward, HP, victory, or battle-stratum criterion fails
- **THEN** r16 remains authoritative and no packaging or gameplay is authorized

#### Scenario: Gate passes
- **WHEN** all fresh criteria pass
- **THEN** the result may authorize a separately registered larger frozen comparison but SHALL NOT authorize packaging or gameplay
