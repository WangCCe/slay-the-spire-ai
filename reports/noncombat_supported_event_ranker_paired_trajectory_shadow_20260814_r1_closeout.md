# Supported Event Ranker Paired Trajectory Closeout

## Decision

The frozen event ranker is a simulator integration **no-go**, including when
restricted to exact training-support signatures. This ends the current event
ranker integration path. The model may not be promoted, threshold-tuned against
this cohort, or rerun on replacement seeds.

## Registered Result

- Cohort: seeds `94800..94927`, accessed once
- Complete pairs: 122 of 128; six registered Courier-restock censors
- Event-exposed pairs: 121; support-exposed pairs: 120; override pairs: 113
- Supported decisions: 393; Current fallbacks: 96; event overrides: 252
- Current: 1 victory, mean floor 21.836066, mean return 0.399482
- Supported overlay: 1 victory, mean floor 21.573770, mean return 0.394881
- Pair deltas: 21 improved, 34 worsened, 67 tied
- Victory changes: one gain and one loss, including a paired Current win lost by
  the overlay

The failed gates were mean floor noninferiority, mean return improvement,
improved pairs not fewer than worsened pairs, and zero paired victory losses.
All pair-support, event/support exposure, override, fallback-accounting, and
out-of-support safety gates passed.

## Interpretation

The training support boundary worked as designed: all 96 unseen signatures fell
back to Current, and no unsupported action was overridden. The remaining failure
therefore cannot be attributed to raw support leakage.

Model confidence remained collapsed despite exact support: 252 overridden
decisions ranged from 0.500008 to 0.508350, with median 0.502260. Event-associated
trajectory deltas varied substantially, but each trajectory can contain multiple
interacting overrides; those associations are diagnostic only and are not
per-event causal estimates.

## Consequence

Do not spend another cohort on this frozen model or choose a threshold from these
outcomes. Any future event-policy work must be a new training change with a
different objective or calibration design and fresh preregistered evaluation.
The next project step should return to an existing real-training line instead of
adding another event-ranker audit layer.

