# Combat RL transition integrity repair

## Decision

Do not continue the old post-training checkpoint. The 25-game update failed the matched greedy gate, and the training path contained confirmed transition-attribution defects.

## Evidence

- The exact 10-seed `epsilon=0` comparison favored the entry checkpoint on 4 seeds, the post-training checkpoint on 2, and tied on 4. Mean floor was `23.4` for entry and `22.4` post-training.
- The checkpoint update was real: `3,638` accepted-step attempts produced `878` Adam updates, with finite tensors and bounded parameter drift.
- The outer combat safety layer could replace an RL-selected action after RL v2 had already recorded the original action index. Replay could therefore assign the replacement action's outcome to an action that was not executed.
- Pending transitions were settled only on the next RL-controlled state. Combat rewards and game-over states route outside RL, so final actions could be dropped or carried across reward, route, shop, event, and card-reward decisions into a later combat.
- Terminal all-false next-action masks produced `0 * -inf` in the target expression, which can create a NaN loss.
- Invalid replay shapes were rejected without preventing `total_steps` from advancing.

## Repair

- Observe and settle the previous pending transition at the outer combat-agent state boundary.
- Bind pending replay attribution to the final action emitted after all safety guards.
- Do not create transitions for unencodable coordination waits.
- Defer ordinary dead-monster transition settlement until the combat-reward state, while preserving half-dead revive actions.
- Finalize normal game completion and discard pending state on failed/aborted games.
- Zero terminal bootstrap values before target construction and advance `total_steps` only for accepted replay rows.

## Verification

- Python compilation passed for all changed runtime and test modules.
- Focused transition contract: `6 passed` before wrapper review additions.
- Related CombatRL, v2, reward, checkpoint, batch-runner, gate, decision-trace, and main lifecycle regression: `392 passed in 16.57s`.
- No full-suite pytest and no live gameplay were run for this repair.

## Next gate

Start from the frozen entry checkpoint, not the corrupted post-training continuation. Run one small repaired training batch, then compare its frozen output against the same entry checkpoint on a fresh fixed `epsilon=0` seed cohort. Continue only if paired greedy outcomes improve without transition-rejection or non-finite-loss markers.
