## Context

The first real-context-balanced corpus publication preserved the registered
training and evaluation partitions and correctly closed without fitting. Its
training partition passed every support gate, while the fresh evaluation
partition missed five gates. A missing-cell audit attributes 55% of the total
uncovered real mass to floors 11 through 17, and the independent training
partition demonstrates that the existing exact-cell method can achieve the
registered thresholds with broader seed support.

The next experiment therefore needs more independent evaluation observations,
not new training rows, a new context representation, or relaxed thresholds.
The existing native module, production-r16 simulator shadow, items export,
r14/r15 replay targets, paired-return recipe, context-cell definition, and gate
implementation remain the bound evidence base.

## Goals / Non-Goals

**Goals:**

- Collect one source-bound fresh evaluation supplement from new seeds and
  early/mid battle indices that can reach floors 0 through 22.
- Preserve the prior combined training corpus byte-for-byte and append only
  validated supplement rows to the prior combined evaluation corpus.
- Recompute deterministic partition-local weights and apply every existing
  support threshold without modification.
- Publish enough immutable evidence to determine whether a separately proposed
  weighted fit is supportable.

**Non-Goals:**

- Fit, train, tune, qualify, promote, or evaluate a model.
- Start Slay the Spire or CommunicationMod, access production gameplay
  checkpoints, or claim live policy quality.
- Change the exact context cells, support thresholds, paired-return target, or
  simulator mechanics.
- Import arbitrary real states or retry a failed registered cohort with changed
  seeds, bounds, or parameters.

## Decisions

### Use a fresh evaluation-only cohort

The supplement uses seeds `271000..272023`, battle indices `0,3,6,9`, at most
two retained states per profile, and target floors `0..22`. This targets the
observed early/mid evaluation coverage deficit while remaining disjoint from
all previously bound train and evaluation partitions. Adding more training
rows was rejected because training already passed every support gate.

### Preserve the training artifact byte-for-byte

The runner loads and validates the prior balanced publication, copies its
combined training corpus without serialization, and verifies the copied hash.
Only the evaluation partition is concatenated. Rebuilding both partitions was
rejected because it would create needless provenance drift and obscure whether
the new evidence changed evaluation support alone.

### Reuse the existing weighting and gate implementation

The runner imports exact-cell weighting, corpus validation, and gate evaluation
from `combat_rl_real_context_balanced_corpus.py`. It recomputes both partition
weights against the same complete r14/r15 replay target and invokes the same
`FIXED_GATES`. A new optimizer or threshold set was rejected because the
experiment is intended to test data support, not select an easier criterion.

### Publish atomically and fail closed

All source, input, seed-isolation, corpus, weight, and output identities are
validated before atomic staging publication. A completed run publishes the
support decision even when gates fail, but never grants fitting or training
authority. Interrupted or invalid runs publish no successful output. There is
one registered attempt and no automatic retry or parameter substitution.

## Risks / Trade-offs

- [Risk] Fixed early/mid battle indices may still under-sample specific real
  context cells. -> The report preserves missing-cell mass and closes without
  fit so a later proposal can choose a different evidence source explicitly.
- [Risk] More simulator rows can increase concentration in common cells rather
  than improve effective sample size. -> The unchanged ESS, maximum-weight,
  coverage, and weighted-SMD gates jointly detect that outcome.
- [Risk] Reusing helper code couples the new runner to the archived experiment
  implementation. -> Source snapshots and hashes bind the exact helper version,
  and focused tests cover append-only behavior and unchanged gate invocation.
- [Risk] Native collection is materially slower than unit tests. -> Source-only
  preflight and focused tests run before the single registered collection; the
  full commit gate runs once at the completed source boundary.

