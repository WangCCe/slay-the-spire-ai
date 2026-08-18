# Combat LightSTS Frozen Candidate Comparison Specification

## Purpose

Define source-bound, matched evaluation of multiple frozen simulator-only combat checkpoints without fitting, gameplay, or production authority.

## Requirements

### Requirement: Bound frozen candidate inputs
The system SHALL compare only an explicitly registered set of immutable simulator-only combat checkpoints and SHALL verify their hashes, checkpoint classifications, production incompatibility, state-dict keys, and tensor shapes before loading them for evaluation.

#### Scenario: Compatible candidate set
- **WHEN** every registered checkpoint matches its bound hash, is classified as a simulator training smoke, is not production compatible, and has the same network structure
- **THEN** the comparator loads each frozen state dict on CPU without modifying or fitting it

#### Scenario: Invalid candidate input
- **WHEN** a checkpoint is missing, hash-mismatched, production compatible, incorrectly classified, or structurally incompatible
- **THEN** the comparator stops before native profile evaluation and publishes no ranking

### Requirement: Matched multi-profile evaluation
The system SHALL evaluate every frozen candidate on the same registered LightSTS `(seed, ascension, battle_index)` profiles, native module, item mapping, and decision bounds.

#### Scenario: Reachable profile
- **WHEN** the native baseline reaches a registered profile for every candidate
- **THEN** each candidate acts from the identical initial state and the report records its outcome, player HP, reward, decisions, progression identity, card-selection settlement, unsupported reason, and truncation state

#### Scenario: Matching natural unreachability
- **WHEN** the baseline loses or the run terminates before the requested battle identically for every candidate
- **THEN** the comparator records the classified coverage gap and excludes that profile from policy aggregates

#### Scenario: Evaluation integrity mismatch
- **WHEN** candidates differ in profile reachability or initialization reason, or any candidate reaches an unsupported state or decision bound
- **THEN** the comparison receives a non-ready verdict and does not claim a candidate ranking

### Requirement: Absolute and pairwise evidence
The system SHALL publish reachable-profile absolute metrics for every candidate, all pairwise deltas, and per-battle-index breakdowns with profile counts.

#### Scenario: Complete comparison
- **WHEN** all registered profiles complete without an integrity blocker
- **THEN** the report ranks candidates by mean reward and includes victories, losses, player HP, decisions, pairwise candidate-only victories, control-only victories, HP and reward deltas, and the same metrics per battle index

#### Scenario: Ranking guardrail conflict
- **WHEN** the mean-reward leader loses a victory-count or player-HP guardrail against another candidate
- **THEN** the report preserves the conflicting metrics and does not declare an unqualified winner

### Requirement: Offline authority boundary
The comparator SHALL perform no model fitting, gameplay, CommunicationMod access, production checkpoint access, transfer, qualification, promotion, OPE, mechanics-equivalence claim, or live policy-quality claim.

#### Scenario: Ready report
- **WHEN** the frozen comparison completes with a ready verdict
- **THEN** it authorizes only selecting evidence for a separately reviewed real-game evaluation and all production or live authority flags remain false
