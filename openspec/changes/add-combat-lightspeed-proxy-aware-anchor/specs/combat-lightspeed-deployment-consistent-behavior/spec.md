## ADDED Requirements

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
