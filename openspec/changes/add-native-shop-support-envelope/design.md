## Context

The repaired adapter accurately filters sold inventory, but the bound
simulator still produces invalid transitions in two source-proven cases. With
The Courier, replacement item, price, and preview semantics diverge from the
installed game. For potion purchases, the simulator reports and executes a
purchase even when Sozu or full capacity makes `obtainPotion` a no-op.

The adapter is an evidence boundary over a read-only external checkout. It
must stop or narrow unsupported actions rather than make downstream consumers
infer which transitions are corrupt. Prior formal cohorts and native modules
remain immutable, and no new formal seed is available to this change.

## Goals / Non-Goals

**Goals:**

- Prevent every known-invalid Courier shop state from producing adapter
  evidence.
- Prevent Sozu/full-capacity potion transactions from appearing as selectable
  adapter actions while preserving visible inventory.
- Keep supported A0 shop snapshots and actions deterministic and unchanged.
- Bind the resulting behavior to a new physical module identity.

**Non-Goals:**

- Repair or approximate Courier restock mechanics.
- Change Current policy, the Python bridge, purge observations, or live code.
- Broaden native support to non-A0 shops.
- Run a formal cohort, train, load, qualify, or promote a policy.

## Decisions

### Fail the entire Courier shop decision

A shared native guard will detect `category() == "shop"` together with The
Courier and throw the exact reason
`unsupported_shop_courier_restock_semantics`. Snapshot and action-entry paths
will invoke the guard before returning policy-consumable bytes or executing an
action.

Allowing only leave or purge was rejected because the snapshot would still be
mistaken for generally supported shop evidence, and Current/native baseline
inventory choices would fail later with less specific mapping errors. Hidden
adapter-side price correction was rejected because it cannot reconstruct item
type, RNG, and purchased-relic preview semantics reliably.

### Filter only impossible potion purchase candidates

Shop potion entries remain visible, matching Communication Mod. Before
mapping upstream actions, the adapter will omit potion purchases when the
player has Sozu or `potionCount >= potionCapacity`. Card, relic, removal, and
leave candidates remain unchanged.

Failing every full-belt shop was rejected because Current can still make valid
card, relic, remove, or leave decisions there. Keeping the upstream potion
candidate was rejected because its transition spends gold without obtaining
the item.

### Preserve API v3 and provenance-bind a successor

No JSON field or candidate schema changes. The module therefore remains API
v3, while source and module hashes distinguish the support envelope from all
frozen predecessors. The successor will be built in a new ignored directory.

An API bump was rejected because callers require no migration. Rebuilding an
existing directory was rejected because it would invalidate historical module
identity.

### Use source-complete evidence plus bounded regression

Source-contract tests will lock the exact guard reason and the potion predicate
at every required call site. A fresh successor build proves C++ integration,
and existing development seeds `0..19` prove supported behavior remains
deterministic. No seed search will be used to manufacture Courier coverage and
no formal cohort will run.

## Risks / Trade-offs

- [Courier trajectories stop earlier and reduce coverage] -> Count them as an
  explicit unsupported domain; never reinterpret absence as policy failure.
- [Source-contract tests do not synthesize a Courier game state] -> Bind them
  to exact installed-game, Communication Mod, simulator, source, and module
  identities, and keep the long-term mechanics repair separate.
- [Filtered potion actions differ from Communication Mod's price-only choice
  list] -> Model meaningful executable transitions: live purchase leaves gold
  and inventory unchanged when obtain fails, while other shop decisions remain
  available.
- [A future simulator fixes these mechanics] -> Remove the envelope only in a
  separately reviewed source-reconciliation change with a new module identity.

## Migration Plan

1. Commit and push this planning boundary.
2. Add red source regressions and the minimal native guard/filter.
3. Build a successor API v3 module in a new ignored directory and verify all
   frozen module hashes remain unchanged.
4. Run reused-seed native smoke, focused pytest, the commit gate, and strict
   OpenSpec validation.
5. Publish a no-authority closeout, sync, archive, and push.

Rollback removes the guard, filter, tests, ignored successor, and closeout. It
does not alter external simulator files, frozen modules, or consumed cohorts.

## Open Questions

No question blocks this fail-closed change. Full Courier support and exact
purge observation remain separate go/no-go inputs.
