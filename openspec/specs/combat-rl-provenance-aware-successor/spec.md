# combat-rl-provenance-aware-successor Specification

## Purpose

Define deterministic, evidence-gated full-network combat RL successor fitting
from parity-qualified replay with exact candidate-callability provenance.

## Requirements

### Requirement: Immutable parity-qualified training input
The system MUST accept only the preregistered zero-update parity checkpoint with the expected SHA-256, transition count, compatible RL v2 metadata, empty optimizer state, equal parent and target parameters, legal stored actions, complete schema-v3 proposal identity, no legacy-unknown rows, and nonempty direct and changed-proposal candidate-callable strata.

#### Scenario: Qualified checkpoint is supplied
- **WHEN** every bound checkpoint identity, replay invariant, proposal reconciliation, and candidate-callability condition matches
- **THEN** the runner may construct terminal-combat development partitions and candidate-decision SMDP spans before fitting

#### Scenario: Input identity or invariant differs
- **WHEN** the checkpoint hash, transition count, metadata, optimizer state, parameter equality, action legality, proposal identity, class coverage, or override consistency differs
- **THEN** the runner fails before creating a final output directory

### Requirement: Recipe-before-corpus parity collection
The system MUST freeze the optimizer recipe, SMDP span rule, terminal-combat split, callability-stratified eligibility thresholds, seed-generation rule, and production-r16 collection behavior before collecting a new training replay. The new replay MUST pass zero-update, trace, inventory, boundary, action legality, proposal legality, provenance reconciliation, class coverage, and direct eval-parent parity checks before fitting.

#### Scenario: Registered fresh cohort passes
- **WHEN** exactly the registered games complete on the registered seeds and every parity and callability check passes
- **THEN** the immutable replay hash may be bound as training-only input for the registered callability-filtered recipe

#### Scenario: Collection or parity check fails
- **WHEN** game count, seed order, zero-update state, trace binding, inventory identity, boundary integrity, action legality, proposal identity, class coverage, or direct eval-parent agreement fails
- **THEN** the cohort remains diagnostic-only and no candidate is fitted

### Requirement: Deterministic bounded full-network fitting
The system SHALL partition complete terminal-delimited combats with the registered split seed, construct candidate-decision SMDP spans without crossing partitions, and fit all online-network parameters with the registered CPU seed, learning rate, batches containing exactly 64 direct and 64 changed-proposal spans sampled without replacement within each stratum, frozen target, frozen parent anchor, parent anchor weight, direct-only margin guard, variable bootstrap multipliers, and exact optimizer-update budget. No no-proposal or legacy-unknown row may be sampled as an independent candidate decision.

#### Scenario: Registered recipe is executed twice on equivalent temporary inputs
- **WHEN** the same checkpoint and registered configuration are supplied
- **THEN** partition indices, span identities, accumulated rewards, bootstrap multipliers, objective summaries, candidate parameters, and candidate hash are identical

#### Scenario: Training update budget or callability boundary is invalid
- **WHEN** the optimizer update count differs, any loss is non-finite, an SMDP span crosses a combat partition, or an independent sample lacks a proposal
- **THEN** the result is ineligible for a fresh holdout

### Requirement: Provenance-aware parent anchor labels
The system SHALL use the stored executed action as the parent-policy anchor label on every sampled changed-proposal row and the frozen parent's mask-aware greedy action on every sampled direct unchanged row. It MUST NOT construct candidate anchor labels from no-proposal or legacy-unknown rows.

#### Scenario: Mixed candidate-callable batch is sampled
- **WHEN** an optimizer batch contains direct and changed-proposal decision spans
- **THEN** anchor telemetry reports both counts, each row uses its required label source, and no ineligible source row is sampled independently

#### Scenario: Changed proposal action is invalid
- **WHEN** any changed-proposal executed action or retained proposal is invalid under its stored action mask
- **THEN** fitting fails before applying an optimizer update

### Requirement: Partitioned development evidence
The system SHALL report parent and candidate SMDP TD loss, greedy action disagreement, provenance-aware anchor-label agreement, positive-energy End Turn behavior, parameter movement, objective telemetry, source-span length, bootstrap discount, and source-row reconciliation separately for fitting and validation partitions, including direct and changed-proposal validation strata.

#### Scenario: Bounded fitting completes
- **WHEN** all registered optimizer updates finish
- **THEN** the report binds every metric and span summary to the input hash, terminal-combat partitions, recipe, candidate hash, callability identity, and development-only authority

### Requirement: Fixed downstream eligibility gate
The system SHALL permit only a separately registered fresh holdout when all preregistered technical, SMDP fit, materiality, direct-policy stability, changed-proposal uplift, callability, provenance, and serialization checks pass. It MUST NOT grant gameplay, qualification, promotion, or production authority, and the candidate pipeline MUST stop on the corpus after any failed fit.

#### Scenario: Every callability-filtered development condition passes
- **WHEN** validation SMDP TD loss improves, overall parent disagreement is at least 5%, direct parent disagreement is at most 10%, changed-proposal executed-label agreement improves by at least 0.10 absolute, positive-energy End Turn count increases by at most two, both validation candidate-callable strata are nonempty, and all integrity checks pass
- **THEN** the frozen candidate hash is eligible only for a separate fresh holdout

#### Scenario: Any condition fails
- **WHEN** one or more fixed conditions fail
- **THEN** production r16 remains authoritative, no alternate candidate recipe is fitted on the corpus, and residual or separate-head architecture requires a new change

#### Scenario: Same-corpus reuse is adaptive or grants downstream authority
- **WHEN** a reuse attempt changes the recipe after observing results or claims gameplay, qualification, promotion, policy-quality, or production authority
- **THEN** the system rejects the attempt

### Requirement: Frozen-parent residual successor continuation
After the fixed full-network callability fit fails direct-policy stability, the
system SHALL permit only a separately proposed frozen-parent residual or head
architecture. That continuation MUST preserve the prior fresh-cohort evidence
gates and MUST NOT reinterpret a mechanism smoke as policy evidence.

#### Scenario: Residual mechanism is ready
- **WHEN** zero-entry equivalence, frozen-parent integrity, deterministic training, bounded correction, and artifact round trip all pass
- **THEN** a new immutable fresh-cohort registration may be prepared without changing production r16

#### Scenario: Residual mechanism fails
- **WHEN** any parent mutation, non-finite value, nondeterminism, illegal action, unbounded correction, or serialization mismatch occurs
- **THEN** the residual path stops before gameplay, fresh data access, or policy-bearing fitting

### Requirement: Residual successor callability gate
The provenance-aware successor SHALL apply the existing candidate-decision
SMDP construction and fixed downstream stability gates to a frozen-parent
abstaining residual result. It MUST additionally enforce the preregistered
direct and changed gate-open thresholds and correction-only optimizer boundary.

#### Scenario: Residual validation evidence passes
- **WHEN** both validation candidate-callable strata are nonempty and every TD, disagreement, executed-label, gate-open, End Turn, parent-integrity, serialization, and provenance condition passes
- **THEN** the adapter hash may be named in a new fresh-holdout registration without granting gameplay or production authority

#### Scenario: Residual validation evidence fails
- **WHEN** any callability, stability, gate-open, correction-only, or integrity condition fails
- **THEN** the cohort is closed to further fitting and production r16 remains the only authorized combat policy

### Requirement: Immutable runner binding
The system SHALL require a supplement that binds the runner source,
interpreter, command, checkpoint, collection report, output path, and execution
identity before fitting. The supplement MUST NOT change any registered cohort,
recipe, seed, threshold, gate, or authority field.

#### Scenario: Runner binding is exact
- **WHEN** every supplement identity matches the source tree and qualified collection before data access
- **THEN** one CPU development fit may start under the registered failure policy

#### Scenario: Runner binding is missing or altered
- **WHEN** the supplement is absent, already consumed, or differs from the current source, command, input, or output identity
- **THEN** fitting stops before loading replay into the optimizer
