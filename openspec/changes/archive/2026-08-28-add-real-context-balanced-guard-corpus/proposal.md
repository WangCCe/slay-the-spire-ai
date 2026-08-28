## Why

The expanded guard-advantage corpus is large enough to fit models but remains
heavily skewed toward early, high-HP, potion-rich LightSTS contexts. A read-only
match against 7,685 complete production-r16 replay transitions reduced the
dominant inventory SMDs, while fresh evaluation covered only 72.93% of real
context mass and had 18 rows at floors 28..34, so another fit would not provide
reliable evidence.

## What Changes

- Add an immutable late-progression paired-return supplement using disjoint
  train and fresh-evaluation seeds and the diagnostic-supported battle indices
  `10..14`.
- Add deterministic real-context post-stratification over floor stratum, potion
  occupancy, relic occupancy, and player-HP quartile.
- Publish unweighted and weighted support, effective-sample-size, context-mass,
  floor-coverage, legality, provenance, and artifact-identity evidence.
- Permit a separately registered training change only when the corpus support
  gates pass; otherwise close without fitting, tuning, gameplay, or seed reuse.
- Keep exact real-state import as a rollback alternative only if targeted
  LightSTS sampling cannot satisfy the preregistered support gates.

## Capabilities

### New Capabilities

- `combat-rl-real-context-balanced-corpus`: Defines targeted late-floor corpus
  supplementation, real-context weighting, support gates, immutable
  publication, and downstream authority boundaries.

### Modified Capabilities

None.

## Impact

The change affects offline analysis and corpus-generation runners under
`analysis_scripts/`, focused tests, one new OpenSpec capability, and immutable
artifacts under `reports/`. It reuses the registered native LightSTS module,
production-r16 simulator shadow, items export, complete r14/r15 replay
checkpoints, and existing paired-return semantics.

Success means both disjoint partitions publish aligned paired-return tensors,
the fresh evaluation partition materially improves floors 23..34 support over
the 2026-08-29 diagnostic, and the preregistered context-mass and effective
sample-size gates pass. Live gameplay, CommunicationMod, production checkpoint
loading or writing, policy qualification, promotion, arbitrary state import,
new model architectures, hyperparameter sweeps, and causal simulator-equivalence
claims are non-goals.

The rollback boundary is the current expanded corpus and context-matching POC.
If collection or support gates fail, no combined training corpus or training
authority is published, and existing source, production, and report artifacts
remain unchanged.
