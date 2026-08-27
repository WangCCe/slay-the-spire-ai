# combat-lightspeed-deployment-consistent-behavior Specification

## Purpose

Define simulator-only replay collection from a frozen parent plus deployment guard, including bounded exploration, evidence binding, and fresh outcome gates.

## Requirements

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

### Requirement: Frozen-parent guarded target-action provenance
The LightSTS runner SHALL optionally retain the deterministic frozen-parent deployment-guard action for every accepted complete-trajectory state independently of the action selected by epsilon behavior exploration.

#### Scenario: Parent behavior branch
- **WHEN** guarded-parent behavior selects the parent branch below the action-per-turn cap
- **THEN** the stored target-policy action equals the guarded parent action and the executed behavior action uses that same action

#### Scenario: Exploration behavior branch
- **WHEN** guarded-parent behavior selects the epsilon exploration branch
- **THEN** the runner still computes and stores the deterministic guarded parent target-policy action while executing the independently seeded exploration action

#### Scenario: Forced action bound
- **WHEN** the action-per-turn bound forces EndTurn
- **THEN** the stored target-policy action and executed behavior action are EndTurn and no target-policy guard replacement is recorded

#### Scenario: Target-action evidence
- **WHEN** target-action provenance is enabled and collection completes
- **THEN** the report binds target-policy action counts, target guard replacement counts, behavior branch counts, and a canonical target-policy action identity without changing the existing source-transition identity contract

### Requirement: Guard-aware target-action configuration integrity
The LightSTS runner MUST require guarded-parent behavior, an immutable warm-start parent, complete trajectories, and the registered deployment guard whenever frozen-parent guard-aware bootstrap provenance is selected.

#### Scenario: Compatible guard-aware configuration
- **WHEN** guard-aware bootstrap is selected with guarded-parent behavior, a valid immutable parent, complete-trajectory collection, and the registered deployment guard
- **THEN** target-action collection and target preparation may proceed

#### Scenario: Incompatible guard-aware configuration
- **WHEN** any required parent, behavior, trajectory, or guard condition is absent
- **THEN** the runner fails before native trajectory collection or fitting

#### Scenario: Default compatibility
- **WHEN** raw-greedy bootstrap or a non-n-step target mode is used without guard-aware bootstrap
- **THEN** target-policy action provenance is not required and existing behavior selection remains unchanged

### Requirement: Guard replacement anchor provenance
The LightSTS runner SHALL retain whether each collected transition was produced by an actual registered guard-proxy replacement and SHALL preserve that provenance through target preparation, replay balancing, and replay insertion.

#### Scenario: Guard replaces raw parent action
- **WHEN** guarded-parent collection replaces the frozen parent's raw action with a different legal executed action
- **THEN** the transition is marked as a guard-proxy replacement and replay receives an executed-action anchor override only when the proxy-aware label mode is active

#### Scenario: Non-replacement behavior rows
- **WHEN** a transition comes from an unchanged parent action, epsilon exploration, uniform collection, or forced EndTurn
- **THEN** the transition is not marked as a guard-proxy replacement and remains frozen-parent anchored

### Requirement: Proxy-aware anchor mode integrity
The LightSTS runner SHALL support the explicit anchor label modes `frozen-parent-greedy-v1` and `guard-replacement-executed-action-v1`, SHALL default to `frozen-parent-greedy-v1`, and MUST reject incompatible proxy-aware configurations before collection.

#### Scenario: Compatible proxy-aware configuration
- **WHEN** proxy-aware mode is configured with guarded-parent behavior, a positive parent anchor weight, an immutable warm-start parent, and the registered guard proxy
- **THEN** collection and fitting may proceed with row-level replacement provenance

#### Scenario: Incompatible proxy-aware configuration
- **WHEN** proxy-aware mode lacks guarded-parent behavior, a positive parent anchor weight, the warm-start parent, or the registered guard proxy
- **THEN** the runner fails before trajectory collection or fitting

#### Scenario: Default label compatibility
- **WHEN** the anchor label mode is absent or `frozen-parent-greedy-v1`
- **THEN** all replay rows retain the existing frozen-parent greedy anchor behavior

### Requirement: Proxy-aware anchor evidence
The simulator corpus and training reports SHALL bind the configured anchor label mode, collected guard replacement count, and sampled override-label usage without granting production authority.

#### Scenario: Proxy-aware smoke completes
- **WHEN** a proxy-aware LightSTS training smoke publishes a report
- **THEN** the report identifies the label mode and separately records collected replacement rows and sampled executed-action anchor overrides

#### Scenario: Simulator-only authority remains
- **WHEN** proxy-aware anchor evidence is positive
- **THEN** the candidate remains production-incompatible and the evidence grants no gameplay, packaging, qualification, or promotion authority

### Requirement: Fresh deployment-consistent experiment gate
The first guarded-parent behavior candidate SHALL use registered unused train and evaluation seeds with complete discounted-return targets and guard-aware evaluation.

#### Scenario: Gate fails
- **WHEN** any registered technical, reward, HP, victory, or battle-stratum criterion fails
- **THEN** r16 remains authoritative and no packaging or gameplay is authorized

#### Scenario: Gate passes
- **WHEN** all fresh criteria pass
- **THEN** the result may authorize a separately registered larger frozen comparison but SHALL NOT authorize packaging or gameplay
