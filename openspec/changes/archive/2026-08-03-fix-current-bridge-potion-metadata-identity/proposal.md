## Why

The consumed r2 Current-bridge diagnostic stopped with zero rows because the
bridge validated upstream potion display names directly against Communication
Mod metadata. A complete static comparison proved three deterministic naming
differences, so the bridge cannot hydrate otherwise valid native snapshots
without a closed identity-compatibility boundary.

## What Changes

- Add red offline regressions for the exact `ELIXIR_POTION`, `FAIRY_POTION`,
  and `GAMBLERS_BREW` native-display/metadata-name triples.
- Resolve only those proven differences through a closed mapping keyed by the
  stable native potion ID and guarded by both expected names.
- Preserve exact case-insensitive name matching for every already compatible
  potion and fail closed for unknown IDs, unexpected native names, or absent
  canonical metadata.
- Record the complete 42-potion static audit and the three-pair boundary in a
  durable report.
- Verify the source repair offline with focused regressions, adjacent bridge
  tests, the repository commit gate, strict OpenSpec validation, and a cohesive
  commit.
- Do not rerun r2, prepare r3, construct a native environment, access a seed,
  launch gameplay, or perform OPE, model fitting, reward changes, formal RL,
  training, qualification, loading, or promotion.

Success means all three proven aliases hydrate without mutating their source
records, all negative identity cases remain blocked, and existing exact-name
behavior remains unchanged. The rollback boundary is the closed alias constant,
its single metadata lookup branch, tests, report, and specification delta.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-current-policy-simulator-bridge`: Permit only the three proven,
  stable-ID-bound potion metadata aliases during exact snapshot hydration while
  retaining fail-closed behavior for every inconsistent identity.

## Impact

The implementation is limited to
`analysis_scripts/noncombat_current_policy_simulator_bridge.py`, its focused
tests, one offline audit report, the existing bridge specification, and project
direction. It changes no native adapter, simulator, gameplay policy, action
mapping, diagnostic registration, cohort, model, reward, or training surface.
