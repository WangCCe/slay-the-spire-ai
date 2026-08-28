# Combat RL Abstaining Residual Collection R1

## Decision

The registered ten-game zero-update collection is qualified for a separate
runner-binding supplement. It does not yet authorize a residual fit, holdout,
gameplay evaluation, policy-quality claim, promotion, or production loading.

## Replay Evidence

- The final schema-v3 checkpoint contains 1,916 transitions and 852
  candidate-decision SMDP spans across 143 terminal-delimited combats.
- Proposal provenance is complete: 350 direct, 502 changed-proposal, 1,064
  no-proposal takeover, and zero legacy-unknown rows.
- Direct proposal agreement with frozen production r16 is 100%; online and
  target parameters remain exact r16 and the optimizer state is empty.
- All 1,916 replay action families match the corresponding decision-trace rows.
  Card, potion, and relic inventory mismatch counts are all zero. `Ghostly`
  remains the known representation-only OOV and maps consistently to zero.

## Runtime Evidence

- Exactly ten registered seeds produced ten AI markers and ten run records;
  there was no eleventh game.
- Floors ranged from 16 to 50 with mean 24.3 and zero victories. These outcomes
  are descriptive only and are not a policy gate for the collection.
- The batch emitted one `Max games reached (10)` exit, no new traceback,
  exception, RL failure, or error-severity log entry.
- CommunicationMod config was restored byte-for-byte, with no remaining
  project/game process or Ironclad autosave.

## Next Boundary

Implement and bind the fixed runner from the registration without changing the
cohort, recipe, thresholds, or seeds. Only that supplement may authorize one
CPU development fit; any failed gate closes this corpus without retry or tune.
