## Why

The latest real replay contains 2,091 transitions but only 928 RL proposals;
1,163 no-proposal takeover rows make up 68.4% of the merged override stratum.
The current replay boolean cannot distinguish those candidate-unreachable rows
from 537 changed same-state proposals, so another objective or residual fit
would optimize against a materially confounded corpus.

## What Changes

- Persist the exact proposed RL action for each new replay transition, with
  explicit no-proposal and legacy-unknown sentinels, while retaining the
  existing executed-action anchor flag and schema-v1/v2 loading compatibility.
- Define and validate four disjoint provenance classes: direct unchanged
  proposal, changed same-state proposal, no-proposal takeover, and legacy
  unknown. New live collections must have no unknown rows and must reconcile
  every transition exactly once.
- Keep no-proposal rows for wrapper diagnostics and fold their rewards and
  successor progression into the preceding proposal-bearing decision span;
  never sample them as independent candidate decisions. Unknown rows block the
  filtered fit.
- Preregister a fresh zero-update production-r16 collection and one fixed
  64-update CPU development fit using the candidate-callable subset, the
  balanced parent anchor, and the direct-only margin guard. The recipe and
  technical gates are frozen before collecting the corpus.
- Grant at most fresh-holdout eligibility if the fixed fit passes TD,
  materiality, direct-stability, changed-proposal uplift, End Turn, integrity,
  serialization, and provenance gates. It grants no gameplay, qualification,
  promotion, policy-quality, or production authority.
- Stop and move to a residual/separate-head change if the fixed fit fails; do
  not add same-corpus arms or tune weights, seeds, thresholds, or update count.

Success means a fresh replay with complete legal proposal identity and a
development report proving that every sampled training/evaluation row was
candidate-callable. Rollback keeps schema-v1/v2 checkpoints loadable, leaves
production r16 and action selection unchanged, and ignores the new optional
provenance field and development artifacts.

## Capabilities

### New Capabilities

- `combat-rl-candidate-callability-provenance`: Defines exact proposal identity,
  replay compatibility, fresh collection validation, candidate-callable
  filtering, and the fixed development experiment.

### Modified Capabilities

- `combat-rl-parent-policy-anchor`: Refines executed-action provenance so
  changed proposals and no-proposal takeovers remain separately identifiable.
- `combat-rl-provenance-aware-successor`: Requires final candidate fitting and
  stratified metrics to exclude candidate-unreachable and legacy-unknown rows.

## Impact

- Affects `RLAgentV2` pending-transition attribution, `ReplayBufferV2`
  serialization/loading, trainer/replay tests, live replay audit tooling, and a
  deterministic callability-filtered successor runner.
- Uses Windows production Python only for the bounded zero-update
  CommunicationMod collection; the subsequent fit is CPU-only and does not
  modify the production checkpoint.
- Does not change outer combat guards, fallback takeover behavior, reward
  shaping, network architecture, inference action selection, or production
  checkpoint loading.
