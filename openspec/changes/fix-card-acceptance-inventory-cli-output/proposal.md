## Why

The sole r3 inventory invocation atomically published a 2,675,460,894-byte
artifact and then failed when the CLI attempted to write that entire artifact
to stdout in one operation. The request was correctly closed terminal, but the
same unbounded result path would make any successor build or verification
unsafe even when its durable artifact is otherwise complete.

## What Changes

- Replace full-artifact stdout for `build-inventory` and `verify-inventory`
  with a bounded canonical completion envelope containing only operation,
  status, closed output identity, receipt identity, inventory digest, and file
  size, including one constant-memory streaming digest of the closed inventory
  bytes.
- Keep `check-dispatch` canonical stdout byte-for-byte unchanged because its
  bounded bytes are part of the preregistered dispatch identity.
- Add regressions proving completion stdout remains below a fixed byte limit
  even when the operation returns a synthetic multi-gigabyte logical artifact,
  while direct Python APIs and durable inventory bytes remain unchanged.
- Preserve receipt ordering, one-shot consumption, output closure, independent
  verifier reconstruction, and every all-false downstream authority boundary.
- Treat r3 as immutable terminal evidence; this repair creates no r4 request,
  approval, authorization, launch, registration, training, or execution
  authority.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `noncombat-card-acceptance-empirical-successor`: Require bounded CLI
  completion output for inventory build and verification without changing
  durable artifact or dispatch semantics.

## Impact

- Affected code:
  `analysis_scripts/noncombat_card_acceptance_empirical_successor_seed_inventory.py`
  and its owning test file.
- Success metric: both inventory CLI operations emit one canonical completion
  envelope below the frozen byte limit regardless of inventory size, and the
  envelope binds the exact bytes observed at completion; focused tests, the
  complete owning pytest file, and strict OpenSpec validation pass.
- Non-goals: no inventory replay, r3 verification, seed/cohort change, native
  loading, model loading, environment construction, training, evaluation,
  gameplay, qualification, promotion, or r4 authority publication.
- Rollback boundary: revert the bounded CLI-envelope code and tests as one
  cohesive change. Never delete, rewrite, verify, register, or reuse the r3
  receipt and unverified output as rollback.
