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
