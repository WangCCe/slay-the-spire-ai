# Combat LightSTS Training Smoke

## Current Verdict

The bounded simulator-only training pipeline has passed its technical smoke,
one larger experiment, and a post-settlement replication. The v2 bridge closed
the known `CARD_SELECT` censorship boundary, and r4 passed every registered
technical, settlement, unsupported-state, reward, HP, and victory gate. The
current narrow encounter surface is ready for coverage expansion, not live
transfer, qualification, or promotion.

## Initial Smoke (r1)

The fixed smoke produced:

- 3,852 accepted RL v2 replay transitions from 256 training seeds.
- 64 finite CPU optimizer updates.
- Parameter L2 delta `0.6293547899230483` from the deterministic initialization.
- Loss `3.2636640071868896` on the first update and `2.8242013454437256` on the last.
- 253 training combat victories and 3 explicit `CARD_SELECT` exclusions.
- Zero training decision-bound truncations.

On 64 disjoint held-out LightSTS seeds, the fitted candidate versus its exact
pre-training initialization produced:

- 63 versus 61 combat victories.
- Mean player HP `70.28125` versus `68.09375`.
- Mean reward `30.53828125` versus `27.69765625`.
- One versus three unsupported boundaries.
- Two candidate-only victories and zero control-only victories.

Artifacts and hashes are in
`reports/combat_lightspeed_training_smoke_20260819_r1/`. The saved candidate is
schema `0`, kind `simulator_training_smoke`, and explicitly
`production_compatible=false`.

## Larger Registered Experiment (r2)

The frozen r2 registration used 1,024 new training seeds, 256 disjoint held-out
seeds, and 256 CPU optimizer updates. It produced:

- 15,031 accepted replay transitions and 256 finite updates.
- Parameter L2 delta `1.2225020697624087`.
- Candidate versus control victories `253` versus `240`.
- Mean player HP delta `+12.6640625`.
- Mean reward delta `+9.679571018448796`.
- Candidate-only versus control-only victories `14` versus `1`.
- Unsupported boundaries `3` versus `7`, with zero decision-bound truncations.

The primary reward criterion and all three victory, HP, and unsupported-state
guardrails passed. The registration is
`reports/combat_lightspeed_training_smoke_20260819_r2_large_registration.json`;
the source-bound artifacts are in
`reports/combat_lightspeed_training_smoke_20260819_r2_large/`.

## Independent Replication (r3)

The same-budget r3 replication changed the behavior seed, network
initialization, training cohort, and held-out cohort without tuning. It
produced:

- 15,443 accepted replay transitions and 256 finite updates.
- Parameter L2 delta `1.0772166200996063`.
- Mean player HP delta `+0.76171875`.
- Mean reward delta `+0.22277979103915674`.
- Candidate versus control victories `254` versus `256`.
- Unsupported boundaries `2` versus `0`, with zero decision-bound truncations.

The reward primary and HP guardrail passed, while victory and unsupported-state
guardrails failed. Both failures were the same two candidate trajectories,
seeds `50252` and `50254`, which reached `CARD_SELECT` at 74 and 80 HP while the
control trajectories completed as victories. These exclusions contributed
reward deltas `-30.15` and `-21.375`; they are bridge-coverage blockers rather
than evidence that another same-surface optimizer run is useful.

## Post-Settlement Replication (r4)

The v2 adapter settled enumerable card-selection tasks through a bounded native
auxiliary policy while preserving the 133-action RL v2 contract. A 256-seed
calibration completed 3,953 deterministic clone/successor checks, settled
`ARMAMENTS`, `DISCOVERY`, and `WARCRY`, and reported zero unsupported states.

The fixed r4 training replication then produced:

- 15,473 accepted replay transitions and 256 finite updates.
- 48 training settlement actions across seven task identities.
- Zero training, control, or candidate unsupported states and zero truncations.
- Candidate versus control victories `256` versus `229`.
- Candidate-only versus control-only victories `27` versus `0`.
- Mean player HP delta `+22.546875`.
- Mean reward delta `+17.5541015625`.
- Candidate/control held-out settlement actions `2` versus `21`.

All registered r4 criteria passed. The source-bound report and simulator-only
checkpoint are in
`reports/combat_lightspeed_training_smoke_20260819_r4_card_select_replication/`.

## Next Gate

Expand the simulator reset/evaluation surface beyond the four observed basic
Act 1 encounters to representative elite, boss, deck, relic, and HP states.
Keep the current r4 candidate simulator-only; do not spend more compute on the
same first-combat distribution.

No simulator result can enter live qualification until matched real-game
divergence evidence covers action legality, successor state, reward-relevant
state, and the `CARD_SELECT` exclusion boundary.
