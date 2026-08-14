## ADDED Requirements

### Requirement: Bound train-only source
The trainer MUST consume only the exact committed state-conditioned shop train
dataset and its deterministic fit/tune split before fresh evaluation.

#### Scenario: Train dataset differs
- **WHEN** dataset hash, schema, source count, feature width, or split differs
- **THEN** execution stops before fitting or fresh seed access

### Requirement: Current-relative weighted objective
The trainer SHALL optimize each unequal-return candidate only against the
Current action using absolute return difference as pair weight.

#### Scenario: Candidate outperforms Current
- **WHEN** a candidate return is greater than Current's return
- **THEN** its score is trained above Current in proportion to the return difference

#### Scenario: Candidate underperforms Current
- **WHEN** a candidate return is less than Current's return
- **THEN** its score is trained below Current in proportion to the return difference

### Requirement: Harm-free train-only selection
The trainer SHALL select epoch and override margin only from the fixed grid on
tune rows and SHALL retain the selected fit-only model without refitting.

#### Scenario: Safe selection exists
- **WHEN** a configuration has nonzero overrides and corrections, zero harms, lower mean regret, and non-inferior maximum regret versus Current
- **THEN** deterministic ordering selects exactly one model and margin

#### Scenario: No safe selection exists
- **WHEN** no fixed configuration satisfies every tune gate
- **THEN** execution stops before native fresh evaluation

### Requirement: One-shot fresh gated evaluation
The trainer SHALL collect one fixed fresh shop cohort and evaluate only the
selected Current-gated model against Current.

#### Scenario: Gated model passes
- **WHEN** fresh support passes, overrides and corrections are nonzero, mean regret improves Current, maximum regret is non-inferior, and harms do not exceed corrections
- **THEN** the verdict permits only a separate live-shadow proposal

#### Scenario: Gated model fails
- **WHEN** any fresh gate fails
- **THEN** the verdict is terminal without tuning, refitting, or rerun

### Requirement: Reproducible isolation
The experiment MUST publish canonical train binding, selection, model, fresh
dataset, metrics, report, and manifest without production policy access.

#### Scenario: Experiment executes
- **WHEN** CPU fitting and native fresh evaluation run
- **THEN** no prior development/fresh outcome, protected seed inventory, production checkpoint, gameplay, CommunicationMod, intervention, qualification, or promotion operation occurs
