## Why

The first fallback-plan qualification batch reached an Astrolabe GRID with
three total selections and two already selected. `SimpleAgent` returned three
cards instead of the one remaining card, causing 39 repeated local legality
exceptions and preventing the second run from completing. This fresh A-class
failure blocks further baseline qualification.

## What Changes

- Make GRID selection honor the remaining required count, not the total count.
- Exclude already selected cards using stable reconstructed-card identity and
  duplicate-aware matching.
- Preserve existing upgrade, purge, transform, remove, and neutral GRID
  ranking behavior.
- Add exact partial-Astrolabe and duplicate-card regressions.
- Keep `CardSelectAction` strict; do not mask invalid caller cardinality.
- Re-run the failed Batch 1 qualification from a new cutoff only after focused,
  full-suite, and independent review gates pass.

Success means a `num_cards=3`, `selected_cards=2` GRID produces exactly one
new unselected card, no cardinality exception, and the fresh 25-game retry can
complete without this A-class cluster.

Non-goals are coordinator queue changes, action-side truncation, policy
retuning, RL training, and changes to non-GRID screen behavior.

The rollback boundary is one cohesive GRID selector commit; the failed Batch 1
report remains unchanged audit evidence.

## Capabilities

### New Capabilities

- `grid-card-selection`: Correct cardinality and duplicate-aware candidate
  selection for initial and partially completed GRID screens.

### Modified Capabilities

None.

## Impact

- Affected code: `spirecomm/ai/agent.py` GRID handling.
- Affected tests: focused SimpleAgent screen guards and CardSelectAction
  cardinality coverage.
- Live validation: a new Batch 1 retry report, fresh `.run` records,
  `ai_debug.log`, and decision/sim-divergence traces.
- No API, dependency, configuration, training, or non-combat policy change.
