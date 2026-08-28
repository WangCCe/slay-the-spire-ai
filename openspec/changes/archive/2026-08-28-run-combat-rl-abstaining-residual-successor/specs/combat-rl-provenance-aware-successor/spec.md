## ADDED Requirements

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
