## Why

The first real card-acceptance training loop is now fast enough to iterate, but
its random non-card policies produced zero wins and a small global logit shift
made every frozen card decision choose `take`. A source-state-matched audit
shows this was a greedy boundary collapse at roughly 51% take probability, and
the final candidate still trailed the trained control on the consumed
development cohort.

No live-game evidence supports this policy. Simulator evidence does show that
native SimpleAgent trajectories are materially more competent than the random
rankers, so the next bounded pilot should isolate card learning on that baseline
instead of tuning entropy, learning rate, or the saturation threshold in the
current setup.

## What Changes

- Add a card-only simulator rollout mode that uses native SimpleAgent for every
  non-card decision in both arms and as the frozen all-category control.
- Relabel the existing, already-consumed card demonstration states with the
  bound Bottled `REQUESTED_STRIKE` oracle and fit the hierarchical card policy
  before any policy-gradient update. SimpleAgent card labels remain an
  auxiliary comparison, not the acceptance teacher.
- Run a bounded candidate-only residual RL pilot on already-consumed development
  seeds only when the warm start passes its fixed card-action validation gate.
- Compare the frozen candidate with native SimpleAgent on the same development
  cohort and require non-inferior mean floor, no victory regression, no
  unsupported episodes, and both card families to remain between 5% and 95% of
  greedy multi-family decisions.
- Publish a compact report and checkpoint outside production discovery. Passing
  authorizes only a separate fresh-evaluation proposal; failure rolls back to
  native SimpleAgent and stops without tuning or another run.
- Do not access the prior warm-start final-test cohort, the card-successor
  protected holdout, CommunicationMod, live gameplay, or production checkpoints.

## Capabilities

### New Capabilities

- `noncombat-card-only-native-baseline-rl-pilot`: Defines the native-baseline
  rollout bridge, card-only warm start, bounded residual update, development
  comparison, stopping rules, artifacts, and no-authority boundary.

### Modified Capabilities

None.

## Impact

The change affects the non-combat simulator adapter/runtime, Bottled card-label
bridge, hierarchical card policy initialization, exploratory training runner,
focused tests, and simulator-only reports. It reuses the bound native adapter,
the archived SimpleAgent trajectory corpus, the clean local Bottled checkout,
and the accelerated cross-fitted update; it does not alter live agent behavior,
CommunicationMod configuration, protected seed inventories, or checkpoint
auto-loading.
