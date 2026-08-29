## Why

The sealed aligned-support evaluation closed at floor-28-34 train context
coverage `0.593220338983051` against the fixed `0.60` gate, while every other
support and integrity condition passed. Read-only attribution shows that the
previous supplemental train cohort sampled only battle index 3 and contributed
zero floor-28-34 target cells, whereas battle-index-10 fresh rows already reach
15 of the 24 uncovered target rows. This justifies one development-only
late-floor corpus and actual paired fit before spending more real-game runs.

## What Changes

- Add a source-bound LightSTS collector for fixed, lineage-disjoint
  battle-index-10 fit, calibration, and fresh cohorts.
- Treat the sealed 799-row live target and all previously inspected fresh
  artifacts as development evidence only. They may guide context acquisition
  but cannot support qualification, promotion, or a confirmatory claim.
- Merge the new late-floor fit rows with the existing merged fit corpus while
  preserving the prior calibration corpus; use a newly registered calibration
  supplement and a completely new fresh policy partition.
- Evaluate development context support once. If it passes, run the unchanged
  4,096-update current-state control and successor-delta paired fit once; if it
  fails, close without more seeds, threshold changes, or tuning.
- Use the new fresh partition only after both arms and calibration thresholds
  are frozen. A positive result permits only a separate proposal for an
  independent real-game confirmation target with run-cluster sufficiency.
- Do not start Slay the Spire or CommunicationMod in this change.

Success requires the fixed new train corpus to pass every existing support and
integrity threshold against the development target and the successor arm to
publish the existing hard-policy or descriptive paired-control decision.
Neither result grants live candidate authority.

Rollback is additive: discard the new corpus, model, and reports. The sealed
target, prior corpora, production r16 checkpoint, CommunicationMod
configuration, and deployed policy remain unchanged.

## Capabilities

### New Capabilities

- `combat-rl-late-floor-successor-development-fit`: Define fixed late-floor
  simulator acquisition, contamination boundaries, one conditional paired
  development fit, and the terminal go/no-go decision for independent live
  confirmation.

### Modified Capabilities

None.

## Impact

- Affected code: a focused wrapper around the existing successor collector,
  corpus merge, context weighting, and paired-fit utilities.
- Evidence: new source-bound registrations, one late-floor fit/calibration/fresh
  corpus package, one development support report, and conditional paired model
  artifacts.
- Runtime: bounded CPU LightSTS collection and offline PyTorch fitting with
  Windows Python; no gameplay, native production loading, or online learning.
- Production: no checkpoint replacement, candidate takeover, qualification,
  promotion, or production write.
