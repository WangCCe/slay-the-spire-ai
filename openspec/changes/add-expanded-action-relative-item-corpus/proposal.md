## Why

Both the base and item-semantic selective classifiers fit their 3,806 training
pairs but failed immediately on the seed-disjoint calibration partition. The
item model reached `0.981` fit accuracy and precision `1.0`, then fell to
`0.472` calibration accuracy, precision `0.32`, and 13 severe harms, which is
direct evidence that the current 192 fit seeds are insufficient for this head.

## What Changes

- Generate one immutable expanded paired-return corpus with the already-bound
  native module and unchanged branch-return recipe: 1,024 training seeds
  (`264000..265023`) and 256 fresh evaluation seeds (`266000..266255`).
- Split training seeds before fitting into 768 fit seeds and 256 calibration
  seeds; never use fresh evaluation rows for fitting, threshold selection, or
  recipe changes.
- Fit the existing item-semantic three-class classifier once with the same
  4,096-update optimizer, sampling, ranking loss, class boundaries, and
  calibration method.
- Require at least 30 fresh interventions, precision at least `0.65`, mean
  selected advantage above `0.18881003558635712`, regret below
  `3.1811342239379883`, and zero severe, illegal, or forbidden selections.
- Do not start CommunicationMod or gameplay, change production r16, tune after
  seeing results, or run a fresh LightSTS policy gate unless every offline gate
  passes and a later change separately authorizes it.

Success is a source-bound expanded corpus plus an item-aware candidate that
passes every untouched fresh offline gate. Failure closes the recipe without
additional heads, thresholds, seeds, or sweeps. Rollback is non-use of the new
corpus and development artifact; existing r16 and prior evidence remain
unchanged.

## Capabilities

### New Capabilities

- `combat-rl-action-relative-expanded-corpus`: Immutable native paired-return
  corpus generation, partition identity, sufficiency, and authority boundaries
  for the expanded seed cohort.

### Modified Capabilities

- `combat-rl-action-relative-selective-classifier`: Permit one item-semantic
  fit on the expanded corpus and define the untouched fresh offline decision.

## Impact

The change reuses the existing native adapter, corpus generator, r16 shadow,
items export, selective model, and fit helpers. It adds OpenSpec artifacts,
one corpus registration and report, one compact fixed training runner, focused
tests, and development reports. It changes no production API, dependency,
action space, reward, live policy, or CommunicationMod configuration.
