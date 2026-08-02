# Non-Combat Simulator Policy Validity

## Status

The registered 2026-08-02 policy-validity study is complete. Its verdict is
`study_valid_without_baseline_signal`. The study was structurally valid, but
the frozen smoke-trained ranker did not beat the native SimpleAgent target
policy. Seeds `3000..3063` are now observed evidence and must not be rerun,
extended, or reused for selection.

This result grants no formal training, live gameplay, live loading, OPE,
qualification, simulator training, or policy-promotion authority.

## Frozen Contract

The registration is
`reports/noncombat_simulator_policy_validity_20260802_input.json`, with
canonical SHA-256
`149a0ed451f52804561de34b213fb4602f6825740705b6c1cf98ab87e0748d10`.
It binds:

- adapter implementation commit `a810d6d0ce92c1ebab8483fb8819163fc76d54fe`;
- native module SHA-256
  `b3328aea4ee3040a4fe8751d6f300a148a7ae64d68f7ebec050ae61f479d6805`;
- the API-v2 r3 fit input and `adapter_poc_ready` report;
- the canonical smoke registration, model, manifest, and trajectories;
- Python 3.10.18, PyTorch 2.5.1, simulator and submodule identities;
- compatibility seeds `2000..2003` and fresh seeds `3000..3063`;
- three fixed greedy policies, 10,000 bootstrap resamples at seed 0, and
  finite episode, decision, and wall-time bounds; and
- Current and Bottled pilot models as excluded baselines because their
  simulator feature/action bridge is not validated.

## Pre-Execution Gates

Before the fresh cohort was touched:

- physical identity collection reported no mismatches;
- both frozen rankers matched every published input hash, selected action,
  sequence, outcome, and floor on compatibility seeds `2000..2003`;
- compatibility contributed zero quality rows;
- focused pure and opt-in native tests passed; and
- the registered commit gate passed 3,204 tests with 8 explicit native skips
  in 202.05 seconds.

No live game, Java process, CommunicationMod launch, training process, or new
live evidence was used.

## Result

The one registered CLI invocation ran one 64-seed primary execution and one
identical replay. Primary and replay took 217.46 and 213.41 seconds and matched
canonically.

| Policy | Mean terminal floor | Victories |
|---|---:|---:|
| smoke trained | 14.562500 | 0/64 |
| seeded initial | 11.796875 | 0/64 |
| native SimpleAgent | 19.968750 | 0/64 |

The primary trained-minus-SimpleAgent mean floor difference was `-5.40625`.
Its registered 95% paired bootstrap interval was
`[-7.875, -2.921875]`. The trained policy therefore underperformed the fixed
baseline across this cohort.

The secondary trained-minus-initial mean difference was `+2.765625`, with a
95% interval of `[1.375, 4.25]`. This reproduces the earlier claim that the
smoke update learned something relative to its seeded initialization, but it
does not satisfy or replace the SimpleAgent primary gate. All three policies
recorded zero victories.

Canonical evidence is under
`reports/noncombat_simulator_policy_validity_20260802/`. The manifest closes
the metrics, report, and trajectories; timing is isolated in the noncanonical
execution journal.

## Isolation

Pre/post checks were identical:

- target game/training process count: `0`;
- CommunicationMod config SHA-256:
  `7ec79e01f9293a19ead3c59a26b18bb75ef900afa3dbe45d657769fe46061862`;
- checkpoint count: `208`; and
- checkpoint inventory SHA-256:
  `bf8cf55fc85087754f500d203de642f5da983ceddb34965005decb3d12cd8eec`.

## Decision

Do not start formal non-combat RL from the current smoke policy and reward
contract. The next offline proposal should establish a baseline-anchored
warm-start before another RL decision:

1. Register new simulator train/validation cohorts before collection.
2. Record native SimpleAgent target decisions as an auxiliary demonstration
   dataset, not as reward or permanent ground truth.
3. Train a separate candidate ranker to reach baseline action/floor parity
   while preserving the full candidate action space.
4. Freeze it and compare it with SimpleAgent on another untouched cohort.
5. Consider a bounded RL proposal only after that policy reaches a credible
   baseline floor and keeps all live/promotion authority false.

Bottled remains a diagnostic reference until a separate simulator
feature/action bridge is validated. It must not be copied into gameplay or
used as a mandatory target merely to pass this gate.
