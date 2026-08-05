## Context

The checked-in terminal collapse audit already binds the simulator-learning
bundle and records that the canary stopped without holdout access. A source-only
POC over its frozen scored rows found that max-pooled family probabilities are
not a neutral replacement for flat candidate probabilities: family mass and
joint-probability argmax move substantially for card rewards and shops, while
event and route rows have only one family. Before training or deterministic
selection semantics can be designed, those effects need a reproducible,
fail-closed measurement over the exact checked-in bytes.

The audit is diagnostic only. It must not reopen checkpoints, replay seeds,
construct the simulator environment, load native modules, or turn a descriptive
counterfactual into policy or experiment authority.

## Goals / Non-Goals

**Goals:**

- Bind the analysis to the terminal collapse audit and the exact
  `training_rows.json` and `evaluation.json` identities recorded there.
- Recompute flat and max-pooled family distributions for training, initial
  canary, and trained canary rows using the checked-in distribution helper.
- Separate stochastic family mass, entropy-objective coverage, score-greedy
  semantics, and joint-probability-greedy semantics in the output.
- Publish canonical JSON and deterministic Markdown with enough counts and
  invariants to support a later design decision.

**Non-Goals:**

- Validating the original experiment recursively or reopening checkpoints,
  manifests, seeds, replay rows, native modules, or holdout rows.
- Changing the action-family distribution, ranker, runner, training objective,
  deterministic policy, or production gameplay.
- Choosing entropy coefficients, proving intervention effectiveness, promoting
  a model, or authorizing another experiment.

## Decisions

### Use the terminal audit as the trust root

The tool will accept three explicit paths: the checked-in collapse audit, its
source root, and output paths. It will require the collapse audit's terminal
schema, status, verdict, all-false authority, unaccessed holdout marker, and
canonical JSON. It will locate only the `training_rows.json` and
`evaluation.json` identities in `integrity.source_artifacts`, then verify their
exact relative paths, sizes, SHA-256 digests, canonical JSON encoding, and that
neither path traverses a symlink.

This avoids silently broadening the audit into a second experiment verifier.
Recursively reopening checkpoints was rejected because the terminal audit
already established that chain and the requested counterfactual depends only
on frozen candidates and scores.

### Analyze diagnostic rows, not experiment execution

Training decision rows and the initial/trained canary diagnostic rows are the
only analyzed records. The tool will validate the evaluation wrapper and prove
`holdout.accessed=false` with zero episodes. It will validate row counts and
candidate/score alignment against the terminal audit, but it will not analyze
replay rows or access another cohort.

### Reuse the checked-in distribution implementation

Each row's scores will be converted to a CPU float32 tensor and passed to
`build_action_family_distribution`. The audit will require the helper's exact
schema, max-pooling identity, float64 distribution dtype, entropy decomposition,
and all-false authority. A stable float64 flat candidate softmax is retained
only as the descriptive control.

Reimplementing max pooling inside the audit was rejected because it could drift
from the capability under review. Replacing the helper or changing its API is
also out of scope.

### Keep selection semantics explicitly separate

For each row the audit will report:

- flat family mass from ordinary candidate softmax;
- hierarchical family mass and family, conditional, and joint entropy;
- raw score argmax and ties;
- two-stage score argmax, defined as max family logit followed by max score
  within that family; and
- joint-probability argmax from the hierarchical candidate probabilities.

Rows with ties are counted separately and are not used to claim deterministic
equivalence. Joint-probability argmax is a counterfactual diagnostic, not a
recommended policy rule.

### Fail closed and publish deterministically

The audit will reject unexpected schemas, keys, non-finite scores, duplicate or
misaligned action identities, count drift, authority drift, source identity
drift, output paths inside the source tree, and any holdout access. JSON is
canonical and each explicit output is staged and atomically replaced only after
all validation and analysis succeeds. A handled replacement failure rolls back
already replaced output; if rollback itself fails, recovery backups are
preserved and named in the error boundary. The two independent output paths do
not claim crash-atomic transaction semantics. Reports contain no wall-clock
timestamp.

## Risks / Trade-offs

- [Reading the large frozen row files is slow and memory-intensive] -> Parse
  each file once, avoid checkpoint traversal, and keep the tool offline and
  bounded to the two hash-bound artifacts.
- [Floating-point summaries can obscure exact boundaries] -> Preserve integer
  counts, use float64 controls, test normalization and entropy identities, and
  report ties explicitly.
- [Joint-probability argmax may be mistaken for a recommended selector] -> Label
  it counterfactual throughout and keep every training, promotion, gameplay,
  and experiment authority field false.
- [The terminal audit could later be replaced] -> Require explicit paths and
  verify exact source identities on every run; a different trust root requires
  a new reviewed invocation and report.
- [The process can terminate between two independent file replacements] -> Do
  not claim pair-transaction atomicity; use per-file atomic replacement,
  handled-failure rollback, preserved recovery backups, and byte-identical
  reproduction as the publication boundary.
