# Non-Combat Reachable Event Surface Audit Specification

## Purpose

Define source-complete, provenance-bound accounting for every simulator-reachable
Ironclad A0 event and its Current explicit-versus-generic handling without
granting native execution, gameplay, policy-quality, or training authority.

## Requirements

### Requirement: Provenance-Bound Reachable Surface Audit
The audit SHALL run only from an explicit registration that binds its implementation commit, Current event-policy source, simulator parent and full physical source identity, pool, guard, setup, legal-action, display, execution, identity and save-id sources, predecessor contract and failure evidence, expected artifacts, and all-false authority.

#### Scenario: Every source identity matches
- **WHEN** the registered repository and simulator sources reproduce every path, commit, dirty flag, size, and SHA-256 field
- **THEN** the audit SHALL perform static analysis without importing or loading the native module
- **AND** it SHALL NOT construct an environment, read a seed, or launch gameplay

#### Scenario: A registered source drifts
- **WHEN** any implementation, Current, simulator, predecessor, or output identity differs
- **THEN** the audit SHALL stop before publishing a reachable-surface classification
- **AND** it SHALL NOT reuse counts from a predecessor report

### Requirement: Exact Pool And Runtime Partition
The audit SHALL distinguish A0 pool declarations from permanent runtime disablement, direct transitions that expose no event-option target, and reachable event-option targets, with every declared identity appearing in exactly one terminal partition.

#### Scenario: The registered simulator identity is audited
- **WHEN** the seven registered A0 one-time, act-event, and shrine declarations are parsed with their exact guards, setup transitions, and legal cases
- **THEN** the audit SHALL reconcile 51 pool-declared identities as 2 permanently disabled, 1 direct transition, and 48 event-option targets
- **AND** the disabled and direct-transition reasons SHALL name their exact source spans and proof fields

#### Scenario: Pool or reachability structure changes
- **WHEN** an array declaration, duplicate identity, permanent guard, setup transition, legal case, or expected partition differs from the registered source form
- **THEN** the audit SHALL fail with a field-specific accounting blocker
- **AND** it SHALL NOT move an event between partitions by heuristic inference

### Requirement: Complete Current Handling Partition
The audit SHALL classify every reachable event-option target as either explicit policy-sensitive handling or generic Current default handling from exact Current AST and alias evidence, with no overlap or remainder.

#### Scenario: Current handling reconciles
- **WHEN** the registered Current source and predecessor contract are analyzed against all reachable event-option identities
- **THEN** exactly 25 targets SHALL map to explicit predecessor rules and 23 SHALL map to the generic default set
- **AND** every generic event SHALL be absent from explicit branches and risky aliases while every explicit alias maps uniquely

#### Scenario: A generic identity becomes policy-sensitive
- **WHEN** any game id, save id, alias, branch, or risky-set member links a generic event to event-specific Current behavior
- **THEN** generic classification SHALL fail closed
- **AND** the audit SHALL require an explicit successor rule instead of preserving the generic label

### Requirement: Canonical Source-Only Publication
The audit SHALL publish canonical configuration, pool inventory, target inventory, Current partition, metrics, report, and manifest artifacts that can be recomputed byte-for-byte from registered sources.

#### Scenario: Publication succeeds
- **WHEN** identity, partition, and Current handling gates all pass
- **THEN** every pool identity and every target identity SHALL appear exactly once and all counts and hashes SHALL reconcile
- **AND** strict recomputation SHALL reject changed, missing, or extra managed files

#### Scenario: Audit evidence is interpreted downstream
- **WHEN** any source row is complete, partial, disabled, direct-transition, explicit, generic, or blocked
- **THEN** native compatibility, baseline-floor, outcome, reward, model, OPE, formal-RL, training, gameplay, loading, qualification, and promotion authority SHALL remain false
- **AND** another native cohort SHALL require a separately reviewed and pushed registration
