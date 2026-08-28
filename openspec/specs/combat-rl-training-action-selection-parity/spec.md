# combat-rl-training-action-selection-parity Specification

## Purpose

Require RL v2 training and replay collection to select greedy behavior actions with production inference semantics while preserving optimizer train mode and evidence-gating training input.

## Requirements

### Requirement: Inference-mode greedy behavior selection
The RL v2 trainer SHALL evaluate its online network with inference-mode module semantics when selecting a greedy behavior action, including zero-epsilon replay collection, and SHALL preserve the stored action mask and weights.

#### Scenario: Training-mode network selects a greedy action
- **WHEN** action selection reaches the online-network greedy branch while the module is in train mode
- **THEN** the forward pass runs with the module in eval mode and returns the masked greedy action

#### Scenario: Eval-mode network selects a greedy action
- **WHEN** action selection reaches the online-network greedy branch while the module is already in eval mode
- **THEN** the forward pass runs in eval mode without changing weights or the stored action mask

#### Scenario: Epsilon exploration selects a random action
- **WHEN** epsilon exploration chooses a valid random action without evaluating the online network
- **THEN** the network's module mode remains unchanged

### Requirement: Exact module-mode restoration
The RL v2 trainer SHALL restore the online network's exact prior module mode after greedy behavior action selection, whether the forward pass succeeds or raises, so optimizer updates retain current train-mode semantics.

#### Scenario: Successful selection restores train mode
- **WHEN** a train-mode online network completes greedy action selection
- **THEN** the online network is back in train mode before `select_action()` returns

#### Scenario: Failed selection restores train mode
- **WHEN** a train-mode online network raises during greedy action selection
- **THEN** the exception propagates and the online network is restored to train mode

#### Scenario: Existing eval mode remains eval mode
- **WHEN** an eval-mode online network completes or fails greedy action selection
- **THEN** the online network remains in eval mode

### Requirement: Fresh deployment-parity validation
A zero-update training-mode replay SHALL NOT become provenance-aware training input until a fresh registered cohort shows that every direct unmarked action equals the frozen parent eval-mode greedy action while stored override actions remain legal and nonzero.

#### Scenario: Fresh parity cohort passes
- **WHEN** the fresh replay has zero optimizer updates, complete trace binding, 100% direct-action eval-parent agreement, and reconciled legal overrides
- **THEN** its report may approve the cohort for a separate registered provenance-aware training change

#### Scenario: Fresh parity cohort fails
- **WHEN** any direct unmarked action differs from the frozen parent eval-mode greedy action or any override is illegal or unreconciled
- **THEN** the report blocks training and retains the cohort only as diagnostic evidence
