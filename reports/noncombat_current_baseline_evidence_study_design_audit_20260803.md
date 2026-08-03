# Current Baseline Evidence Study Design Audit

Date: 2026-08-03

## Decision

One post-repair Current baseline-evidence proposal is methodologically
defensible if it replaces, rather than renames, a third structural diagnostic.
It must expose the fixed Current policy directly to a canary stop gate and an
untouched holdout, count declared support blockers conservatively, and make any
observed result terminal. This audit grants planning authority only.

## Evidence Identity

- Planning base commit:
  `50b9be19f986aed1c38993a6e3a36dd2f2aace3a`.
- Seed inventory implementation:
  `analysis_scripts/noncombat_reachable_event_native_compatibility.py`, 76,021
  bytes, SHA-256
  `9eee1fb38ce74536748237047b09dfc1efa1298348e029e6693c60d753c3b4a9`.
- Historical persisted seed inventory: 1,760,941 bytes, SHA-256
  `208f28aa92fb1e8bdec496ec8fed93afc9645a6bef536065a9161f566a915647`.
  It is retained as historical evidence and is not represented as current.
- Adapter fit report: 31,889 bytes, SHA-256
  `42d08fedd3225179bf45c4cbbaa4c8103b8cba43cc3b0ebdf220f147f6cb82b5`.
- Policy-validity metrics: 3,006 bytes, SHA-256
  `4546b12ec3540cfba9251cabc270199254fe20f43e1459ab6ee99d71a44497f1`.

## Current Seed Audit

The existing structured `build_tracked_seed_inventory` API was run in a fresh
no-bytecode Python process against tracked files only. It loaded no native
module and constructed no environment. At planning HEAD it reported:

| Measure | Value |
|---|---:|
| Tracked seed sources | 83 |
| Parsed seed rows | 8,315 |
| Unique excluded seeds | 348 |
| `11000..11015` overlap | 0 |
| `12000..12063` overlap | 0 |

The preregistration must regenerate and persist a new inventory after the
source-only implementation commit. Any overlap, source drift, or changed count
blocks registration rather than selecting new seeds.

## Threshold Anchors

The numeric floor gates are selected without observing Current outcomes:

| Historical policy | Cohort | Mean floor | Victories |
|---|---:|---:|---:|
| Deterministic first-candidate | 20 | 13.2 | 0 |
| Smoke-trained ranker | 64 | 14.5625 | 0 |
| Native SimpleAgent | 64 | 19.96875 | 0 |

SimpleAgent is contextual only because its teacher suitability failed; it is
not a comparison gate. First-candidate is a deterministic weak control, so the
final study also needs an independent absolute gate. The fixed holdout contract
requires Current mean floor at least 18, absolute 95% bootstrap lower bound at
least 15, paired mean improvement at least 3, and paired 95% lower bound above
zero. These thresholds place a credible floor above the two weak/negative
policies without requiring parity with the rejected teacher reference.

## Anti-Retry And Authority Boundary

- V1 and r2 remain immutable zero-row failures; the proposal does not create
  r3 or reuse their four development seeds.
- Canary observations may only stop the study. They cannot modify code,
  thresholds, support rules, bootstrap, policies, or holdout membership.
- Only `unsupported_shop_courier_restock_semantics` may be retained as a
  conservative support row; every other bridge, runtime, determinism, or bound
  failure blocks the terminal attempt.
- Any canary failure leaves all holdout seeds untouched and is terminal for the
  proposed identity.
- A passing holdout can support only a later read-only baseline readiness
  refresh. It does not satisfy target-supported outcomes or authorize formal
  RL.
- Native loading, environment construction, seed access, gameplay, model
  fitting, reward work, OPE, training, qualification, loading, and promotion
  remain unauthorized until their separate gates.
