# Non-Combat Current Event Semantics Coverage Audit r2 Closeout

Date: 2026-08-02

## Result

The registered comment-aware r2 audit is complete and strictly reproducible.
It preserves the r1 Current, upstream, event-registry, and authority identities
while removing exactly four display entries that r1 derived from commented C++
output:

- `Big Fish` index 0 label `Offer`
- `Cursed Tome` index 0 label `Continue`
- `Cursed Tome` index 0 label `Take`
- `Cursed Tome` index 1 label `Stop`

No display entry was added. The corrected active labels are `Banana`, `Donut`,
and `Box` for `Big Fish`, and `Read`, `Leave`, `Take`, and `Stop` at indices 0,
1, 5, and 6 for `Cursed Tome`.

The reconciled result remains 25 canonical events, 47 Current aliases, 24
`source_complete`, one `source_partial`, and zero unaccounted aliases. `Cursed
Tome` remains partial because its legal-action masks are dynamic expressions of
`eventData`; the terminal result therefore remains `resolver_ready=false`.

## Supersession

The r1 registration and five canonical artifacts remain immutable. Their event
and alias accounting remains valid, but the r1 display-label matrix is
superseded and must not be used as the adapter-contract input. The registered
r1-to-r2 delta proves that the four removals above are the only row-level
changes and that event, alias, status, resolver-readiness, unaccounted-alias,
and authority values did not drift.

## Frozen Identity

- Audit implementation commit:
  `d7af2840febb64ff3805ea6681e5c001470e4f1b`
- Audit implementation SHA-256:
  `0bec7b66556aa64483c802a1d0b0304c0ebeaf06de73921a22573b9c1201906c`
- Current source SHA-256:
  `a495b56bcf2367b34e74cf679bbc8ae0a51c9509723236b2240c7577eef2a9f5`
- Upstream parent commit:
  `7476a81954020087da31d41d16fddf475746ec2d`
- Upstream complete source SHA-256:
  `a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`
- r2 registration:
  `reports/noncombat_event_semantics_coverage_audit_20260802_r2_input.json`
- r2 registration SHA-256:
  `c8ce94fbe1337ec9e245c1747ffffb0c9bd48594414410234da7d06d5ff62d6a`
- r2 canonical artifact directory:
  `reports/noncombat_event_semantics_coverage_audit_20260802_r2`
- r2 manifest SHA-256:
  `f00356b0690556898425992b968414cc1de43e853623df99ff1636cb125c9c12`
- Delta registration SHA-256:
  `d5bd43673488416c85b4c70fcc4ac87947c068112a32ec93599938ee649a220b`
- Delta report SHA-256:
  `f5096b1e5b94a4155b684fbf53de707e38354289ca9c43c094d5d55ad224d36b`
- Immutable r1 manifest SHA-256:
  `3f1c6176e6f28b8444c4459275fe1d7369b580e43092faaf648d0b5f532429a7`

## Reproduction

One canonical r2 publication and one `--recompute` execution produced the same
five managed artifacts byte-for-byte. The registered delta report was also
created once and then recomputed byte-for-byte. No file was added to either
canonical audit directory outside the fixed five-artifact set.

## Verification

- Focused audit pytest: `28 passed` in `1.04s`
- Strict change validation: passed
- Pre-archive global OpenSpec validation: `57 passed, 0 failed`
- Post-archive global OpenSpec validation: `56 passed, 0 failed`
- Repository commit gate: `3377 passed, 11 skipped` in `281.12s`
- Commit gate total: `284.43s`
- Canonical r2 publication and strict recomputation: passed
- Registered r1-to-r2 comparison and strict recomputation: passed

## Authority Boundary

This remains static source-coverage evidence only. Resolver extension,
simulator execution, seed use, gameplay, model fitting, reward changes,
training, promotion, and formal-RL readiness authority all remain false. No
native module, simulator episode, gameplay process, seed, model, or training
path was used.

## Next Boundary

The next allowed capability remains a separately reviewed source-bound
event-option adapter contract. It must consume the corrected r2 inventory,
define exact state and phase mappings for all 25 Current-relevant events,
resolve the dynamic `Cursed Tome` masks, and preserve unknown states as
fail-closed before any resolver implementation or new compatibility evaluation
is proposed.
