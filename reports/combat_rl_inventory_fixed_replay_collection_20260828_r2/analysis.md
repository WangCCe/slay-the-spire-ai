# Inventory-Fixed Replay Collection R2

## Result

The clean retry completed all 20 registered seeds in order and produced 3,634
real combat transitions. The online and target networks remain byte-equivalent
to production r16, the optimizer state is empty, and `learning_starts=100000`
prevented every update.

The inventory repair is confirmed on fresh gameplay: all 3,634 replay rows join
one-to-one with the decision trace, with zero potion or relic identity mismatch
and zero unresolved occupied inventory objects. The new corpus contains 1,209
potion and 1,891 relic display-name fallback occurrences that are now encoded
directly rather than recovered after collection.

## Boundary Disposition

One EndTurn transition at source index 2528 crossed from floor 21 to floor 22
with `done=false`. Its stored successor retained the prior potion inventory,
while the following combat began with a newly acquired Power Potion. The raw
checkpoint is preserved as evidence and is not directly training-eligible.

The training copy removes only that transition through the production
`ReplayBufferV2` load/state-dict path. Every remaining replay tensor equals the
raw source with exact index 2528 removed; online, target, and optimizer state are
unchanged. The sanitized 3,633-transition checkpoint is training-only and does
not carry holdout, evaluation, or promotion authority.

## Next Step

Use the sanitized checkpoint to train one candidate with a material policy
change. Freeze the candidate before collecting a separate fresh holdout; do not
reuse these 20 seeds for candidate selection or promotion.
