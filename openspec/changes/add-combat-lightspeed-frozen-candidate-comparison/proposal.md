## Why

The first-combat r4 candidate and the later-battle r5/r6 candidates were each compared only with their own randomly initialized control. Although both later-battle runs improved on their controls, the large difference in uplift magnitude does not establish which frozen candidate is strongest on one common profile surface.

## What Changes

- Add a source-only frozen candidate comparator that loads multiple simulator-only combat checkpoints without fitting or mutating them.
- Evaluate every candidate on the same registered fresh `(seed, battle_index)` cohort with one immutable LightSTS module and item mapping.
- Publish absolute metrics, pairwise deltas, per-battle-index breakdowns, reachability accounting, source identities, and artifact hashes.
- Require identical profile reachability across candidates and reject production-compatible, structurally incompatible, or source-unbound checkpoint inputs.
- Keep all gameplay, transfer, qualification, promotion, mechanics-equivalence, and live policy-quality authority false.

Success is a complete comparison with no initialization integrity failures, no unsupported states or decision-bound truncations, and a stable evidence-backed ranking across the registered indices. The current evidence is r5 (`+5.68` HP, `+6.58` reward) and r6 (`+35.77` HP, `+46.26` reward) against different random controls, so direct cross-candidate claims are not yet supported.

## Capabilities

### New Capabilities

- `combat-lightspeed-frozen-candidate-comparison`: Validate and compare multiple frozen simulator-only combat candidates on one matched later-battle LightSTS cohort.

### Modified Capabilities

None.

## Impact

The change adds one offline analysis runner, focused tests, a fixed registration, and a source-only report. It reuses the existing combat bridge, policy evaluator, safe checkpoint loader, and immutable r3 native module. It does not access production checkpoints, Steam, Slay the Spire, or CommunicationMod. Rollback is deleting the comparator artifacts; existing candidates and production behavior remain unchanged.
