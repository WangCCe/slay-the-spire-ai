## Why

The bounded simulator-training smoke produced a reproducible terminal-floor
signal against its seeded random initialization, but both policies won 0/64
holdout runs and the trained policy was not compared with a meaningful fixed
simulator baseline. Before formal non-combat RL can be considered, the frozen
model needs a separately registered fresh-cohort evaluation against the native
`sts_lightspeed` SimpleAgent under the same state and candidate semantics.

## What Changes

- Add a read-only native-baseline query to the optional simulator adapter. At
  every target state it must deterministically identify exactly one currently
  reported legal candidate without mutating the source environment.
- Bind the completed smoke registration, canonical model, manifest, repaired
  fit evidence, adapter/module/runtime identities, and a new disjoint seed
  cohort before evaluation begins.
- Add an offline-only paired evaluator for the frozen trained model, the exact
  seeded initial ranker, and the native SimpleAgent target policy. It performs
  no gradient update, checkpoint discovery, reward change, or model selection.
- Make trained-versus-SimpleAgent paired terminal-floor improvement the primary
  validity metric. A positive mean counts as baseline-relevant signal only when
  the pre-registered paired-bootstrap confidence interval lower bound exceeds
  zero. Trained-versus-initial replication is secondary evidence.
- Report per-policy victories, terminal floors, category coverage, legal
  selections, pairwise differences, and same-input reproduction separately.
  A floor signal with no victory signal remains an explicit limitation.
- Exclude the frozen Current-imitation and Bottled-auxiliary pilot models from
  the primary study because their live-sample state and action identities do
  not have a validated simulator feature bridge.
- Keep all formal-training, live loading, gameplay, OPE, qualification, and
  promotion authority false regardless of the result. No live game or new live
  evidence is part of this change.

Success means the native baseline action is deterministic and candidate-legal,
the frozen model evaluates reproducibly on untouched seeds, and the report
classifies structural validity separately from the pre-registered baseline
signal gate. It does not mean the policy is victory-capable or promotion-ready.

## Capabilities

### New Capabilities

- `noncombat-simulator-policy-validity`: Provenance-bound fresh-cohort
  evaluation of a frozen simulator policy against fixed same-schema baselines.

### Modified Capabilities

- `noncombat-simulator-adapter`: Expose a deterministic, non-mutating native
  SimpleAgent action that maps to exactly one reported target candidate.
- `noncombat-simulator-training-smoke`: Permit the completed canonical model to
  be consumed only as a frozen offline evaluation candidate without reusing its
  observed holdout for selection or training.
- `noncombat-rl-decision-loop`: Keep simulator policy-validity metrics in their
  own evidence class with no live/OPE/training authority.

## Impact

- Adds an offline evaluator, registration/report schemas, focused tests, one
  frozen input, and isolated report artifacts under `reports/`.
- Narrowly extends `simulator_adapters/sts_lightspeed/noncombat_adapter.cpp` and
  rebuilds the ignored optional native module against the explicit local
  `D:\CLionProjects\sts_lightspeed` checkout.
- Reads the completed smoke artifacts and supervised-pilot metadata, but does
  not alter them. Current/Bottled pilot models are compatibility diagnostics
  only and are not executed as study baselines.
- Does not modify CommunicationMod, gameplay policy code, launchers, production
  checkpoints, `.run` files, logs, or the external simulator checkout.
- Live evidence remains the previously frozen historical-prefix coverage; this
  study creates only simulator evidence and cannot increase live support.
- Rollback removes the optional baseline query, evaluator, tests, registration,
  and study artifacts. No live or production migration is required.
