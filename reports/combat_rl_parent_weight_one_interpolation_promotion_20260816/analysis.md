# Alpha-0.20 combat interpolation promotion

## Decision

Promote the alpha-0.20 weights-only interpolation as the production combat baseline for bounded five-game evaluation launches.

This is a separate decision from the fresh gate. The gate restored the previous parent configuration before qualification, and this promotion is based on a manual review of the completed report and artifact integrity.

## Basis

- Fresh matched gate: 20 candidate and 20 parent games with all seed pairs matched.
- Paired result: 5 candidate wins, 13 ties, 2 parent wins.
- Total floors: 492 candidate versus 444 parent.
- Act 2 entries: 11 candidate versus 9 parent.
- Act 2 boss reaches: 7 candidate versus 6 parent.
- Candidate checkpoint: finite weights-only artifact that passed exact round-trip and `RLAgentV2` loading.

## Scope

The production command remains evaluation-only with epsilon zero, conservative routing, and a five-game bound. No optimizer or replay state is loaded. The prior production configuration remains a fixed rollback artifact.

Neither gate arm achieved a victory, so this promotion improves the combat baseline without satisfying the project-level first-victory objective.
