# Combat LightSTS Training Smoke

## Current Verdict

The bounded simulator-only training pipeline has passed its technical smoke and
one larger pre-registered LightSTS experiment. An independent replication kept
the mean reward and HP deltas positive, but failed the victory and unsupported
guardrails only at the known `CARD_SELECT` boundary. Further same-surface
training is paused until that bridge gap is closed. Nothing here authorizes
live transfer, qualification, or promotion.

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

## Next Gate

Add deterministic `CARD_SELECT` observation and action support to the combat
LightSTS bridge, with clone-isolation and successor regressions. Only then run a
new-cohort replication. Broader elite, boss, deck, relic, and HP coverage remains
a separate prerequisite for transfer even if that replication passes.

No simulator result can enter live qualification until matched real-game
divergence evidence covers action legality, successor state, reward-relevant
state, and the `CARD_SELECT` exclusion boundary.
