# Combat LightSTS Training Smoke

## Verdict

The bounded simulator-only training pipeline is technically ready for a larger
pre-registered LightSTS experiment. It is not ready for live transfer,
qualification, or promotion.

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

## Next Gate

A larger simulator experiment is justified, but it must remain isolated and
pre-register its train/evaluation cohorts, optimizer budget, and success
metrics. That experiment should test whether the held-out advantage survives a
larger seed set and more optimizer updates.

No simulator result can enter live qualification until matched real-game
divergence evidence covers action legality, successor state, reward-relevant
state, and the `CARD_SELECT` exclusion boundary.
