## ADDED Requirements

### Requirement: Explicit shadow inference device isolation

The action-relative live shadow SHALL accept a schema-v2 registration that
binds CPU inference, SHALL execute the residual against a frozen CPU mirror of
the registered production parent, and MUST NOT move, mutate, or replace the
production agent's parent network or action.

#### Scenario: Schema-v2 CPU shadow initializes
- **WHEN** a committed source-bound registration specifies `inference_device: cpu` and all parent and artifact identities match
- **THEN** initialization creates a distinct CPU residual parent with the registered state hash while the production parent retains its original device and state

#### Scenario: Device registration is invalid
- **WHEN** schema v2 omits the inference device, includes unsupported keys, or specifies any device other than CPU
- **THEN** initialization fails before artifact loading, trace publication, or gameplay

#### Scenario: Historical schema-v1 registration is read
- **WHEN** a schema-v1 registration is loaded for historical validation
- **THEN** its exact legacy keys remain valid and its inference device is reported as inherited from the production parent

#### Scenario: CPU and production predictions are compared
- **WHEN** the same registered states are evaluated on the CPU mirror and production CUDA parent
- **THEN** predictions match within `rtol=1e-5` and `atol=1e-5`, and actions, gates, abstentions, legality, forbidden-action handling, and telemetry match exactly

#### Scenario: CPU live readiness is summarized
- **WHEN** a schema-v2 CPU shadow trace is summarized
- **THEN** the report identifies schema v2 and CPU inference and applies the unchanged identity, neutrality, support, legality, error, budget, and 20ms p95 latency conditions
