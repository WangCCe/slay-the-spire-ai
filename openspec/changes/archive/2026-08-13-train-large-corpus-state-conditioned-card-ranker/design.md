## Context

The merged compatible corpus provides 773 train states across 434 seeds and
190 development states. Of the train rows, 542 across 347 seeds contain 2,142
unequal-return action pairs. The frozen r7 candidate card policy already
consumes separate state and candidate tensors, and a 64-row CPU
forward/backward/Adam step takes about 0.38 seconds. The prior 30-row pilot used
32 full-batch steps and overfit its 16-row holdout; this change needs a
train-only duration selection rather than repeating that schedule.

## Goals / Non-Goals

**Goals:**

- Train the existing state-conditioned candidate card heads on all available
  informative train evidence.
- Select training duration without exposing development or reserved audit rows.
- Produce one restored model and one-shot development evidence that can support
  or reject a later independent audit proposal.

**Non-Goals:**

- Changing model architecture, optimizer options, feature projection, reward,
  or pairwise objective.
- Loading native code, constructing simulator environments, accessing
  `92320..92383`, running gameplay, or promoting a policy.
- Tuning after crossfit or development results are observed.

## Decisions

### Reuse the complete candidate card heads

Training owns exactly the existing candidate family head and conditional
state-conditioned ranker parameters through the registered Adam optimizer.
Control and non-card parameters, generators, features, and candidate order stay
frozen. This directly addresses the per-card residual's inability to express
context while avoiding another architecture.

### Train only informative rows, evaluate all rows

Rows with equal returns for every legal action contain no pairwise gradient and
are omitted from optimization. All rows remain in crossfit and development
metrics. Informative rows are ordered by `(seed, decision_index,
source_sha256)`, partitioned into deterministic batches of 64, and never
shuffled or resampled.

### Select epochs with five seed-level folds

Five folds are built over all merged train seeds. Each fold starts from the
same entry bytes, trains on the other four folds, and emits held-out scores at
epochs 1, 2, 4, and 8. The earliest/best fixed checkpoint that decreases
cross-fitted mean regret, does not increase maximum regret, increases weighted
pairwise accuracy, does not decrease unique-best accuracy, corrects at least
eight actions, and has no more worsened than corrected actions is selected by a
fixed metric ordering. If no checkpoint passes, development is not read.

### Persist final model before development access

One fresh entry instance is trained on all informative train rows for the
selected epochs. The complete canonical paired-bootstrap bytes are written and
restored before existing and rare development datasets are parsed. Entry and
restored models are then evaluated once on merged development and rare-only
development.

### Keep strict development and rare-card gates

Merged development must improve mean regret and pairwise accuracy without
increasing maximum regret or decreasing unique-best accuracy; it must correct
at least four actions and not worsen more than it corrects. Rare-only
development must improve mean regret, preserve pairwise accuracy, and not
increase best-take-to-skip errors. Passing authorizes only a separate audit
proposal.

## Risks / Trade-offs

- [Neural heads still overfit] -> Seed-level crossfit selects duration before
  development, and any maximum-regret increase blocks audit.
- [Deterministic unshuffled batches bias updates] -> Seed-level folds and
  crossfit metrics expose the effect; reproducibility is preferred over hidden
  stochasticity for this first large-corpus fit.
- [Full bootstrap artifacts are large] -> One canonical final model is stored;
  fold models remain in memory and are not published.
- [Development has already informed model-family choice] -> It does not select
  epochs or parameters in this change; the still-unaccessed audit remains the
  independent gate.
