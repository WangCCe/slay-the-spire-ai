## Why

After closing the observed potion boundary, a complete read-only audit of the
remaining item hydration surface found that the bridge will deterministically
reject 17 valid upstream relic identities. Fifteen differ from Communication
Mod metadata only by punctuation or possessive spelling, while simulator-reachable
`Circlet` and `Red Circlet` are absent from the exporter metadata entirely.

## What Changes

- Record the complete card/relic metadata identity audit: all 370 upstream card
  display names are covered, while 17 of 180 non-invalid relic identities need
  a closed compatibility rule.
- Add red regressions for all 15 exact stable-ID/native-name/canonical-name
  triples and both exact stable-ID/native-name metadata exemptions.
- Add one closed relic identity table keyed by stable native ID. Require the
  expected native name for every listed ID; require the canonical metadata name
  for the 15 aliases; permit metadata absence only for `CIRCLET` and
  `RED_CIRCLET`.
- Canonicalize only aliased hydrated relic names. Preserve stable native ID,
  source slot, counter, price, exact-name behavior, and source bytes.
- Fail closed for changed names, unknown IDs, missing canonical metadata, or
  any new exemption; do not use fuzzy or punctuation normalization.
- Verify offline with focused and adjacent regressions, `py_compile`, the
  repository commit gate, strict OpenSpec validation, and a cohesive commit.
- Do not rerun either diagnostic, prepare r3, construct a native environment,
  access a seed, launch gameplay, or perform OPE, fitting, reward changes,
  formal RL, training, qualification, loading, or promotion.

There is no new live evidence in this change. Success means all 17 audited
identities hydrate through their exact closed contracts, every negative case
remains blocked, and all 163 directly matching relic names plus the complete
card surface retain existing behavior. The rollback boundary is the closed
identity table, its single relic lookup branch, tests, report, and spec delta.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-current-policy-simulator-bridge`: Permit the 15 proven relic-name
  aliases and two exact metadata-absent fallback relics while retaining strict
  stable-ID/name validation and fail-closed behavior.

## Impact

The implementation is limited to
`analysis_scripts/noncombat_current_policy_simulator_bridge.py`, its focused
tests, one read-only audit report, the existing bridge specification, and
project direction. It changes no card or potion mapping, native adapter,
simulator source, gameplay policy, action mapping, diagnostic evidence, model,
reward, or training surface.
