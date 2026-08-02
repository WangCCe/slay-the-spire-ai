# Non-Combat Event Option Observation Contract Closeout

Date: 2026-08-02

## Result

The registered source-bound observation contract is complete and strictly
reproducible. It accounts for all 25 canonical Current-relevant events and all
47 aliases with zero unaccounted surfaces:

- 23 events use exact static index-to-label rules.
- `Cursed Tome` uses an exact five-phase `event_data` table covering simulator
  indices 0 through 6.
- `N'loth` uses a named dynamic rule and requires offered relic slot, id, and
  name under `state.decision_context.offered_relics`.

The contract normalizes upstream `Mindbloom` to Current `MindBloom` and records
each visible option as a contiguous Current position plus its original simulator
choice index. This prevents sparse legal choices, such as Cleric Leave at
simulator index 2, from being sent back as if Current position 0 were simulator
index 0.

The result remains `resolver_ready=false` and `adapter_ready=false`. It defines
the implementation boundary but does not implement or execute the bridge,
resolver, native adapter, simulator, gameplay runtime, model, or trainer.

## Frozen Identity

- Contract implementation commit:
  `0b08b59c9de6710eba81a3ba56bc540fc7d75ff8`
- Contract implementation SHA-256:
  `6ed2f3cf517c7f06905577f2928e3253ab65dd42449ea4ac3323145e933f3369`
- Reviewed event registry SHA-256:
  `cb525f7d077dcdc09d8c302625ac00dcf2e30aa9a60dffc8bafbbfa50eec9bb0`
- Registration:
  `reports/noncombat_event_option_observation_contract_20260802_input.json`
- Registration SHA-256:
  `3fb637a44d17d4081cba3e0ff7ba868811c1312a08c904ee3b1f5deeb1c3183b`
- Canonical artifact directory:
  `reports/noncombat_event_option_observation_contract_20260802`
- Contract artifact SHA-256:
  `785e5db26d4cecaa843c7ee3e9e276fdc98c4b77b6a61e88f4520824a50bf3fc`
- Artifact manifest SHA-256:
  `9f441052ed2527b6ef18f007ea1d2cff847c629a0069bcf364064f4b3650948e`
- Corrected r2 inventory SHA-256:
  `f30c2c8345d858c78bdbefb414b29dea2d753e6216848716ccdcd8d6c29c8066`
- Corrected r2 manifest SHA-256:
  `f00356b0690556898425992b968414cc1de43e853623df99ff1636cb125c9c12`

## Reproduction

One canonical publication created the fixed five-artifact set: configuration,
contract, metrics, report, and manifest. A subsequent `--recompute` execution
validated all managed artifacts byte-for-byte and rejected missing, changed, or
extra files. The validator consumed only registered Current, corrected r2, and
upstream source bytes.

## Verification

- Final focused contract pytest: `20 passed` in `0.45s`
- Contract module `py_compile`: passed
- Canonical publication and strict recomputation: passed
- Strict change validation: passed
- Pre-archive global OpenSpec validation: `57 passed, 0 failed`
- Repository commit gate: `3397 passed, 11 skipped` in `267.24s`
- Commit gate total: `270.43s`
- Post-archive global OpenSpec validation: `57 passed, 0 failed`

## Authority Boundary

All twelve registered authority fields remain false. This contract does not
authorize resolver or adapter implementation, simulator execution, seed use,
compatibility evaluation, baseline measurement, gameplay, reward changes, model
fitting, formal-RL readiness, training, or promotion. It is a structural
prerequisite and contains no policy-imitation claim.

## Next Boundary

The next allowed capability is a separately reviewed resolver/adapter
implementation change. It must:

1. expose the exact `N'loth` offered-relic fields in the native snapshot;
2. consume all 25 registered event rules with fail-closed unknown-state
   behavior; and
3. translate Current positions through the validated simulator-index mapping.

No native compatibility cohort may run until that implementation is regression
tested, commit-gate verified, and covered by a separate preregistration.
