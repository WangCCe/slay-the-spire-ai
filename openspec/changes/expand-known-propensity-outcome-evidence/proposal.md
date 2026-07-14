## Why

The frozen B3-B7 known-propensity pool is structurally valid and estimator-ready, but its 125 complete trajectories contain only one victory and that trajectory has zero weight under deterministic Current. The resulting victory comparison is therefore driven by outcome sparsity rather than an estimator defect, so the next step must pre-register and collect a larger fixed evidence set before any training, reward, or gameplay-policy change is considered.

## What Changes

- Add a committed pre-registration contract for one fixed 600-attempt experiment: 24 ordered 25-run eval sessions, deterministic seeds and identifiers, `card_reward=300` basis points, `shop=1000` basis points, and a two-alternative-attempt budget per run.
- Add a blind collection controller that freezes source and runtime provenance, validates each session structurally, and withholds victory, floor, killed-by, OPE, and policy-comparison summaries until all planned sessions have terminated or an integrity stop has been recorded.
- Add deterministic multi-session pooling and an evidence-expansion gate requiring at least 575 complete joined trajectories, exact included evidence, aggregate arm support, adequate deterministic-Current overlap, and at least three distinct victories with nonzero deterministic-Current trajectory weight.
- Reuse the frozen target-policy and validated OPE estimator contracts after unblinding, without changing the 10,000-replicate bootstrap or policy-comparison conditions.
- Keep event and route exploration shadow-only and keep `card_reward:skip` and `shop:leave` as the only executable alternatives.
- Keep formal non-combat RL training, reward design, Bottled-driven live actions, gameplay-policy edits, and live promotion out of scope.
- Stop rather than extend, lower gates, change rates, or mix source versions when the fixed experiment is insufficient or invalid. Disabling the explicit exploration configuration remains the runtime rollback boundary.

## Capabilities

### New Capabilities
- `noncombat-outcome-evidence-expansion`: Pre-register, execute blindly, unblind, and close out the fixed 600-attempt known-propensity outcome-evidence experiment.

### Modified Capabilities
- `noncombat-exploration-data-loop`: Add deterministic aggregation and structural qualification across a pre-registered sequence of bounded exploration sessions without requiring every operational session to satisfy aggregate arm-count thresholds independently.
- `noncombat-ope-readiness`: Add study-specific evidence-expansion screens for deterministic-Current support and supported victories while preserving the existing estimator and policy-comparison gates.

## Impact

- Affected areas: offline analysis and validation scripts, bounded batch orchestration, exploration session configuration generation, tests, OpenSpec contracts, and committed evidence reports.
- Live execution remains Windows-only through `D:\anaconda\envs\stsai\python.exe` and CommunicationMod-compatible eval commands; no WSL gameplay path is introduced.
- The experiment may consume approximately 24 hours at the observed rate of about 25 runs per hour. Its success metric is evidence readiness, not a favorable policy result: fewer than 575 complete trajectories, fewer than three supported victories, or any required integrity failure produces an explicit inconclusive or blocked closeout.
- No new runtime dependency, checkpoint format, training artifact, or live policy loader is introduced.
