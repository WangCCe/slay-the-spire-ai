## Why

The one-shot Current baseline study terminated on
`card_metadata_cost_invalid` for `Injury`. A separate read-only audit at commit
`6d448fcc5` proves this is a closed exporter/bridge representation mismatch:
23 empty-cost metadata records for 20 stable native card IDs explicitly declare
`Unplayable.`, while the bridge accepts other unplayable literals but rejects
the exporter's empty representation.

## What Changes

- Add a closed stable-native-ID contract for exactly the 20 audited empty-cost,
  explicitly unplayable card identities. Require exact native name, metadata
  name, metadata type, empty cost, and leading `Unplayable.` description before
  hydrating SpireComm cost `-2`.
- Add red regressions for every positive ID, including upgraded
  `Reflex`/`Tactician`/`Deus Ex Machina`, and production-shaped `Injury` deck
  hydration.
- Preserve integer costs and `X -> -1`; keep `SLIMED`, `PRIDE`, and
  `WHIRLWIND` as explicit negative controls.
- Keep the three audited Wish option identities and every unknown, renamed,
  type-drifted, non-empty, or non-unplayable empty-cost record fail closed.
- Prove snapshot, candidate, and metadata inputs remain unmodified and run the
  focused bridge/metadata suites plus the registered repository commit gate.
- Record the repair as implementation-only compatibility evidence. Do not run
  native environments, access seeds, retry or reinterpret the baseline study,
  change Current policy, or authorize formal RL or gameplay.

Success is all 20 positive identities hydrating with cost `-2`, every reverse
and negative control retaining its registered behavior, exact source
non-mutation, and all focused and repository gates passing.

Rollback removes only the new closed mapping, its helper/tests, and this
change's synced requirement. The archived study registration, authorization,
journal, rows, artifacts, verdict, and readiness refresh remain immutable.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-current-policy-simulator-bridge`: Define closed stable-ID-bound
  hydration for the audited empty-cost unplayable card metadata domain while
  preserving fail-closed handling for every other empty-cost identity.

## Impact

- Expected source: `analysis_scripts/noncombat_current_policy_simulator_bridge.py`.
- Expected tests: `tests/test_noncombat_current_policy_simulator_bridge.py` and
  focused adjacent Current bridge/study verifiers.
- Evidence source:
  `reports/noncombat_current_bridge_card_metadata_cost_domain_audit_20260804.json`
  and its Markdown companion.
- No dependency, native adapter, simulator checkout, Communication Mod,
  gameplay policy, reward, model, trainer, OPE, cohort, or study artifact
  changes are planned.
