## ADDED Requirements

### Requirement: State-unique parent latent candidate scoring

Action-relative candidate selection SHALL compute the frozen parent latent at
most once per original state batch row and SHALL reuse that latent for every
allowed guard-candidate pair while preserving the repeated-state reference
predictions within `1e-6` and preserving actions, gates, abstentions, and safety
constraints exactly.

#### Scenario: One state has multiple allowed candidates
- **WHEN** selection evaluates multiple legal alternatives for one state
- **THEN** it performs one parent latent computation for that state and returns predictions within `1e-6` of independently scoring every expanded state-candidate pair

#### Scenario: Batch masks, forbidden actions, or abstention differ
- **WHEN** a batch contains different legal masks, guard actions, forbidden actions, and rows with no threshold-clearing candidate
- **THEN** optimized and repeated-state reference selection return identical actions, gate decisions, abstentions, legality results, and forbidden-action telemetry

#### Scenario: Fixed CPU latency preflight passes
- **WHEN** the unchanged production-r16 parent and retained action-relative artifact complete 32 warmup calls and 256 deterministic held-out CPU measurements with exact parity and no errors
- **THEN** optimized p50 speedup is at least 2x and optimized p95 latency is at most 15ms before any new live shadow registration is created

#### Scenario: Parity or latency preflight fails
- **WHEN** prediction, action, gate, abstention, safety, error, speedup, or p95 conditions fail
- **THEN** no new live cohort is launched and no model, threshold, gate, or benchmark input is changed
