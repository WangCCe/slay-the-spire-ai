## Why

The first three-class selective classifier converged but reached only `0.466`
holdout precision and selected 19 severe-harm actions. Its frozen latent plus
action-one-hot representation must infer the card or potion occupying a slot
indirectly, while the failures span many item identities and parent Q margin
has only `0.031` correlation with paired return advantage.

## What Changes

- Add an optional item-semantic feature path to the development-only selective
  classifier: direct candidate and guard item embeddings, selected-card local
  features, action family, slot, and target identity.
- Run one fixed 4,096-update CPU ablation with the same fit, calibration, loss,
  and optimizer recipe as the closed classifier experiment.
- Treat seeds `263000..263127` as an already-consumed development comparison,
  not a fresh holdout or promotion result.
- Authorize a later separately registered fresh corpus only if the ablation
  reaches at least 30 interventions, precision at least `0.55`, no more than 5
  severe harms, mean selected advantage above `0.17321939766407013`, and mean
  regret below `3.1967246532440186`.
- Do not run native code, LightSTS corpus generation, CommunicationMod, or
  gameplay in this change. Do not tune the recipe after seeing the result.

Success is evidence that direct item semantics materially improve every fixed
development comparison condition. Failure closes the feature path without a
sweep. Rollback is non-use of the development artifact; production r16 and the
closed classifier artifact remain unchanged.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `combat-rl-action-relative-selective-classifier`: Add an optional direct
  item-semantic feature contract and a development-only ablation decision that
  cannot itself authorize qualification or promotion.

## Impact

The change touches the isolated selective-classifier module, one compact
development runner, focused tests, OpenSpec artifacts, and reports. It adds no
dependency and changes no live routing, action space, checkpoint, reward,
CommunicationMod configuration, or gameplay behavior.
