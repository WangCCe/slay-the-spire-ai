## ADDED Requirements

### Requirement: Float32-equivalent state-unique candidate selection

Action-relative candidate selection SHALL compute the frozen parent latent at
most once per original state batch row and reuse it for allowed guard-candidate
pairs. Relative to repeated-state candidate scoring, predictions MUST match
with `rtol=1e-5` and `atol=1e-5`, while selected actions, gate decisions,
abstentions, legality, forbidden-action behavior, and telemetry MUST match
exactly.

#### Scenario: Batch-shape arithmetic differs within float32 tolerance
- **WHEN** repeated-state and state-unique parent evaluation produce prediction differences within `rtol=1e-5` and `atol=1e-5`
- **THEN** selection is equivalent only if actions, gates, abstentions, legality, forbidden-action handling, and telemetry are also identical

#### Scenario: Numerical or behavioral equivalence fails
- **WHEN** any prediction exceeds the fixed tolerance or any action, gate, abstention, safety, legality, or telemetry result differs
- **THEN** the offline preflight fails and no new live shadow is authorized

#### Scenario: Fixed CPU latency preflight passes
- **WHEN** the unchanged production-r16 parent and retained residual artifact complete 32 warmup calls and 256 deterministic held-out CPU measurements with exact behavioral equivalence and no errors
- **THEN** optimized p50 speedup MUST be at least 2x and optimized p95 latency MUST be at most 15ms before a new live registration is committed

#### Scenario: Diagnostic evidence informs a new registration
- **WHEN** a post-failure read-only audit characterizes numerical margins from an earlier immutable attempt
- **THEN** it has no qualification authority and the revised source, tolerance, inputs, schedule, and limits MUST be frozen in a new registration before execution
