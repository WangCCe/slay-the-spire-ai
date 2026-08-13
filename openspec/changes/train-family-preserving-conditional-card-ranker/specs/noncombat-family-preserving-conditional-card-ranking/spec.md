## ADDED Requirements

### Requirement: Bound merged source-only evidence
The runner SHALL bind the existing and rare-card compatible corpus partitions,
the r7 entry bootstrap, predecessor no-go evidence, exact source bytes, and the
fixed conditional-only training configuration. It MUST NOT load native code,
construct environments, access reserved audit seeds, or read development
before train-only selection passes.

#### Scenario: Preflight passes
- **WHEN** every source, corpus, checkpoint, predecessor, projection, and schedule identity matches
- **THEN** train-only crossfit may start with development, audit, native, and gameplay access disabled

#### Scenario: A bound input differs
- **WHEN** any required identity, support count, partition, or source byte differs
- **THEN** the runner fails before optimizer construction or development access

### Requirement: Family-preserving conditional fitting
The runner SHALL train exactly the 64 values of
`conditional_ranker.scorer.weight` with registered Adam. It SHALL optimize only
unequal take-vs-take counterfactual pairs in deterministic 64-row batches and
MUST preserve the family head, conditional hidden tensors and bias, all other
model state, and every entry family choice.

#### Scenario: One epoch completes
- **WHEN** valid informative rows are trained once
- **THEN** every row contributes once, all losses, gradients, optimizer state, and parameters remain finite, and only the registered scorer weight changes

#### Scenario: Frozen ownership differs
- **WHEN** any non-owned tensor, generator, family output, input order, or optimizer option changes
- **THEN** fitting fails and the model receives no downstream authority

### Requirement: Train-only fixed epoch selection
The runner SHALL evaluate checkpoints `{1, 2, 4, 8, 16, 32}` with five
seed-disjoint folds. Each fold SHALL restore identical entry bytes, fit only
the other folds, and score its held-out rows with no update.

#### Scenario: A checkpoint passes
- **WHEN** two-stage mean regret decreases, maximum regret does not increase, unique-best accuracy does not decrease, take-only pairwise accuracy increases, at least four actions are corrected, worsened actions do not exceed corrected actions, and family flips equal zero
- **THEN** one checkpoint is selected by the fixed ordering without development access

#### Scenario: No checkpoint passes
- **WHEN** every fixed checkpoint fails at least one train-only gate
- **THEN** final fitting, development, audit, tuning, and retry are blocked

### Requirement: Policy-aligned one-shot development gate
The runner SHALL fit one final model, persist and restore its complete canonical
bootstrap, then evaluate development exactly once with the same two-stage rule
used by the simulator. Overall development SHALL improve mean regret and
take-only pairwise accuracy, preserve maximum regret and unique-best accuracy,
correct at least two actions, worsen no more than it corrects, and have zero
family flips. Rare development SHALL not regress mean or maximum regret,
take-only pairwise accuracy, or unique-best accuracy, SHALL correct at least
one action, and SHALL have zero family flips.

#### Scenario: Development passes
- **WHEN** every overall and rare-only gate passes after exact model restore
- **THEN** the verdict authorizes only a separate reserved-audit proposal

#### Scenario: Development fails
- **WHEN** any overall or rare-only gate fails
- **THEN** the model is not ready and no retry, tuning, audit, live evaluation, or promotion is authorized

### Requirement: Canonical isolated evidence
The runner SHALL publish canonical configuration, folds, losses, policy-aligned
metrics, predictions, restored model, report, and manifest artifacts. Native,
gameplay, CommunicationMod, formal RL, OPE, policy-quality, qualification,
production loading, audit, and promotion authority SHALL remain false.

#### Scenario: Execution terminates
- **WHEN** train-only selection stops or one-shot development completes
- **THEN** exact artifacts and the stop reason are published without modifying production state or accessing `92320..92383`
