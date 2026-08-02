# Non-Combat Current Event Semantics Coverage Audit Closeout

Date: 2026-08-02

## Result

The registered read-only audit is complete and strictly reproducible. It
accounts for all 47 aliases used by Current's 18 event-decision branches and
maps them to 25 canonical upstream events without an unaccounted alias.

Twenty-four events are `source_complete`. `Cursed Tome` is the only
`source_partial` event because its legal-action source returns masks computed
from `eventData`:

- `0x1 << (gc.info.eventData+1)`
- `0x3 << (gc.info.eventData+1)`

The audit records those expressions instead of guessing their phase expansion.
The terminal result is therefore `resolver_ready=false`.

## Frozen Identity

- Audit implementation commit:
  `585135f8209b90d4145bc1c1f1b81c6446d5ff8d`
- Audit implementation SHA-256:
  `3d8fa10dafdfbcf68c55a4cc4e4fd4a507264cfc417902dccffdc74527492158`
- Current source SHA-256:
  `a495b56bcf2367b34e74cf679bbc8ae0a51c9509723236b2240c7577eef2a9f5`
- Upstream parent commit:
  `7476a81954020087da31d41d16fddf475746ec2d`
- Upstream complete source SHA-256:
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`
- Registration:
  `reports/noncombat_event_semantics_coverage_audit_20260802_input.json`
- Registration SHA-256:
  `8e7bd6ba6d51891e47ef8053cfab9bd5208b49784600a538d0fbd3ecfd75cef2`
- Canonical artifact directory:
  `reports/noncombat_event_semantics_coverage_audit_20260802`
- Manifest SHA-256:
  `3f1c6176e6f28b8444c4459275fe1d7369b580e43092faaf648d0b5f532429a7`

The audit bound five exact upstream source files for event identity, save ids,
legal actions, display labels, and execution effects. The upstream checkout's
dirty state and submodule identities are preserved in the registration rather
than treated as clean or inferred from its parent commit alone.

## Reproduction

One canonical publication and one `--recompute` execution produced the same
five managed artifacts byte-for-byte:

- `configuration.json`
- `event_inventory.json`
- `metrics.json`
- `report.md`
- `artifact_manifest.json`

The reconciled result is 25 canonical events, 47 aliases, 24
`source_complete`, one `source_partial`, and zero unaccounted Current aliases.

## Verification

- Focused audit pytest: `12 passed` in `0.53s`
- Strict change validation: passed
- Global OpenSpec validation: `56 passed, 0 failed`
- Repository commit gate: `3361 passed, 11 skipped` in `276.52s`
- Commit gate total: `279.93s`
- Canonical publication and strict byte-for-byte recomputation: passed

## Authority Boundary

This is static source-coverage evidence only. It does not prove exact runtime
effects, adapter completeness, policy quality, simulator compatibility, or
formal-RL readiness. Resolver extension, simulator execution, seed use,
gameplay, model fitting, reward changes, training, promotion, and formal-RL
readiness authority all remain false.

No native module, simulator episode, gameplay process, seed, model, or training
path was used to produce this evidence.

## Next Boundary

The next allowed capability is a separately reviewed source-bound event-option
adapter contract. It must define exact event-state and phase mappings to legal
indices and labels for all 25 Current-relevant events, explicitly resolve the
dynamic `Cursed Tome` masks, preserve unknown states as fail-closed, and add
contract regressions before changing the existing one-event resolver. No
compatibility cohort or reused Stage 2 seed is authorized by this closeout.
