## Why

Both candidate-only and state-conditioned shop rankers fail source-level OOF evaluation on the current 112-source corpus, with their best mean regrets exceeding Current. The shared failure across model capacities makes independent simulator support, rather than another architecture variant, the next bottleneck to address.

## What Changes

- Collect exactly 384 new supported shop source states from a fixed disjoint seed schedule, evaluating every legal action under frozen Current-policy continuation.
- Bind the existing 112 historical source hashes and reject any overlap with the expansion cohort.
- Require complete branch outcomes, replay determinism, action-kind coverage, informative support, bounded time, and verified artifacts.
- Publish one expansion dataset that can raise the later training corpus to 496 sources.
- Do not train, tune, evaluate a learned model, access fresh evaluation seeds, or integrate a policy in this change.

Success requires 384 complete unique sources, at least 192 informative sources, at least four action kinds, 16 deterministic replays, and no overlap with the historical corpus. The rollback boundary is the standalone collector and its report directory; Current and all production checkpoints remain unchanged.

## Capabilities

### New Capabilities

- `noncombat-shop-counterfactual-corpus-expansion`: Defines a source-bound, large shop counterfactual collection run and its isolation, overlap, coverage, and publication gates.

### Modified Capabilities

None.

## Impact

The change adds one development-only native collector, focused tests, and a bounded report dataset of roughly 20–25 MB. It reuses the current simulator bridge and shop counterfactual branch evaluator; it does not affect gameplay or CommunicationMod configuration.
