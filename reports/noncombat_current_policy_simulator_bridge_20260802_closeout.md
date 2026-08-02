# Current Policy Simulator Bridge POC Closeout

## Status

The source-bound frozen-row POC is complete and strictly reproducible. Its
terminal verdict is `frozen_bridge_not_compatible`.

- Implementation commit: `ebe2fb8e2deb639edfe0e4bac1320d3befd55f9e`
- Registration SHA-256: `2c8cf7fae0acc707cd37d31fa75f79066fa3764f827962979e877be6581ba192`
- Frozen source: the existing warm-start train dataset, seed `4000`
- Current identity: `current_optimized_ironclad_a0_conservative_snapshot_v1`
- Replay count: two fresh Current sessions per selected row

## Result

| Category | Decision | Result |
| --- | ---: | --- |
| route | 0 | passed, `route:map_node:0:0` |
| card reward | 1 | passed, `card_reward:take:0:0:armaments` |
| shop | 5 | passed, `shop:remove_card` |
| event | 11 | failed, `missing_event_option_semantics` |

The three passing categories used the exact Current screen path, mapped to one
legal simulator candidate, repeated deterministically, retained tracker and
gameplay I/O isolation, and left source snapshots and candidates unchanged.
The event adapter row contains event identity and generic option indices but
does not contain the exact option labels that Current reads for semantic choice.
The bridge correctly refused to manufacture those labels.

## Stage 2 And Authority

Stage 1 did not pass, so the registered reused seeds `2000..2003` were not run.
No own-trajectory compatibility, terminal quality, baseline floor, reward,
outcome-support, training, gameplay, qualification, promotion, or formal-RL
authority was created. Every authority flag remains false.

## Next Boundary

Create a separate OpenSpec change for source-bound simulator event-option
semantics. It must add exact labels to adapter snapshots and regressions without
changing Current gameplay behavior. After that change, strictly recompute this
same registration and frozen four-row Stage 1 POC. Do not alter the selected
rows, Current configuration, category minima, replay count, or Stage 2 seeds,
and do not consume fresh simulator or live-game evidence.
