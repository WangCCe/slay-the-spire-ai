# noncombat-route-counterfactual-ranking-training Specification

## Purpose
TBD - created by archiving change train-outcome-backed-route-ranker. Update Purpose after archive.
## Requirements
### Requirement: Complete route counterfactual rows
The runner SHALL evaluate every legal action at each eligible multi-candidate route source from an immutable cloned simulator state, SHALL use a fresh frozen Current-policy session to select every post-action branch transition, and SHALL record a row only when every branch reaches a supported terminal outcome.

#### Scenario: Complete route source
- **WHEN** a route source exposes multiple legal map-node candidates and every forced branch reaches a supported terminal outcome
- **THEN** the dataset contains one immutable source row with the candidates, formal returns, projected features, and Current-policy selected action

#### Scenario: Unsupported branch
- **WHEN** any forced branch encounters a registered unsupported simulator boundary
- **THEN** the runner excludes that source from training evidence, records the censor reason, and enforces the configured support floor

### Requirement: Train-only route ranker selection
The runner SHALL choose the fixed training epoch without accessing development rows and SHALL refit the selected architecture on all train rows before development evaluation.

#### Scenario: Checkpoint selection
- **WHEN** the fit and internal tune partitions contain sufficient unequal-return route pairs
- **THEN** the runner evaluates only the fixed epoch schedule on the tune partition and deterministically selects one epoch

### Requirement: One-shot development comparison
The runner SHALL evaluate the frozen trained model exactly once on the disjoint development cohort and SHALL compare it with the frozen initialization and Current optimized route action.

#### Scenario: Route model passes
- **WHEN** the trained ranker lowers mean regret versus Current policy, does not increase maximum regret, improves weighted pairwise accuracy versus initialization, and produces at least one correction with no excess worsened decisions
- **THEN** the report classifies the route ranker as ready for a separate fresh evaluation proposal

#### Scenario: Route model fails
- **WHEN** any development quality condition fails
- **THEN** the report issues a terminal no-go for this model configuration without authorizing same-cohort tuning

### Requirement: Development-only isolation
The runner MUST NOT launch the game or CommunicationMod, load or modify production checkpoints, access reserved card seeds, or alter production policy behavior.

#### Scenario: Bounded execution
- **WHEN** the route experiment executes
- **THEN** it writes only its configured report directory and records source, native module, metadata, cohort, resource, and authority boundaries
