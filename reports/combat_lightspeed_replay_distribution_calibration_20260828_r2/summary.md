# Combat LightSTS Replay Distribution Calibration

- Verdict: `replay_distribution_calibration_ready`
- Real transitions: `7685`
- Simulator transitions: `19512`
- Common strata: `['floor_00_05', 'floor_06_10', 'floor_11_17', 'floor_18_22', 'floor_23_27', 'floor_28_34']`
- Optimizer updates: `0`
- Blockers: `none`

## Largest numeric mismatches

- `floor_11_17` `potion_occupied_slots`: `1.251923`
- `floor_06_10` `potion_occupied_slots`: `0.879156`
- `floor_28_34` `potion_occupied_slots`: `0.856854`
- `floor_23_27` `potion_occupied_slots`: `0.787408`
- `floor_18_22` `relic_occupied_slots`: `0.757945`
- `floor_28_34` `relic_occupied_slots`: `0.703894`
- `floor_11_17` `relic_occupied_slots`: `0.685648`
- `floor_18_22` `potion_occupied_slots`: `0.641352`

## Largest categorical mismatches

- `floor_00_05` `relic_id_support_nonoverlap`: `0.956522`
- `floor_23_27` `potion_id_support_nonoverlap`: `0.933333`
- `floor_28_34` `potion_id_support_nonoverlap`: `0.821429`
- `floor_18_22` `potion_id_support_nonoverlap`: `0.806452`
- `floor_06_10` `relic_id_support_nonoverlap`: `0.738462`
- `floor_23_27` `relic_id_support_nonoverlap`: `0.707547`
- `floor_00_05` `potion_id_support_nonoverlap`: `0.666667`
- `floor_06_10` `potion_id_support_nonoverlap`: `0.666667`

This is an unmatched descriptive comparison. It grants no gameplay,
training, evaluation, mechanics-equivalence, policy-quality, qualification,
or promotion authority.
