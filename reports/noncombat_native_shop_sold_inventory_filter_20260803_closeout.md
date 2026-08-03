# Native Shop Sold-Inventory Filter Closeout

Date: 2026-08-03

## Decision

The native shop sold-inventory compatibility defect is repaired, its delta
spec is synced, and `filter-native-shop-sold-inventory` is archived.

The successor API v3 module now omits exactly card, relic, and potion source
slots whose price is the simulator's canonical sold sentinel `-1`. It retains
all nonnegative entries, including unaffordable inventory and Courier
replacements, with their original fixed `slot`. Any item price below `-1`
fails snapshot generation with inventory-kind and source-slot context.

This closeout does not authorize a third formal native cohort. The remaining
shop snapshot domain should first receive a bounded read-only sentinel and
state-semantics audit.

## Evidence Chain

- Source-complete defect audit: commit `0893d2992` and
  `reports/noncombat_shop_sold_inventory_sentinel_audit_20260803.md`.
- Pushed OpenSpec planning boundary: commit `d28e23999`.
- Minimal adapter repair and bridge/source regressions: commit `097a342b2`.
- Reused-seed native lifecycle regression: commit `43ef7584c`.

The pre-fix focused run produced the required red result:

- `test_adapter_v3_source_filters_only_sold_shop_inventory_slots`: failed
  because the adapter still serialized raw fixed slots.
- Adjacent bridge regressions: 4 passed, proving sparse nonnegative inventory
  already hydrated correctly and sold item prices remained rejected.

After the repair, the same focused selection passed `5 passed in 0.58s`.
The broader pure adapter/bridge run passed `77 passed, 5 skipped in 3.11s`;
the skips were the expected native tests before a successor module was bound.

## Implementation Boundary

`simulator_adapters/sts_lightspeed/noncombat_adapter.cpp` now validates every
shop item price before constructing JSON:

- `price == -1`: omit the sold fixed slot;
- `price < -1`: throw a field-specific structural error;
- `price >= 0`: serialize the item and its original source slot.

Candidate generation, Current shop policy, bridge metadata validation,
affordability, rewards, models, and schemas were not changed. API v3 remains
appropriate because its shop arrays were already variable-length and each
entry already carried an explicit source slot.

## Successor Provenance

The successor was built in the ignored directory
`.sts_lightspeed_adapter_v3_sold_inventory_build`. The frozen predecessor in
`.sts_lightspeed_adapter_v3_build` was never rebuilt or overwritten.

- Adapter implementation commit:
  `097a342b2ee9c7925afe772cc633abb918c77ebd`
- Native lifecycle test commit:
  `43ef7584cbc86728854c06c3790c25cb8e59c787`
- Bound adapter source SHA-256:
  `9b56b48e2c3298bfaee5f8b0cc4fdce7f89bdf0cc6b1aa799858ce1ee0b03f11`
- `noncombat_adapter.cpp` SHA-256:
  `75200dc948341a71421cdc1f859b8911352e4256eb77744d5291b63224934f46`
- Adapter `CMakeLists.txt` SHA-256:
  `709d4c081b3121f6497306085493ea78afc6fafb0887300d019ff8996d252220`
- Successor module SHA-256:
  `f5dde34657156db74e437bcb954fc0ceb739604bb43a3bcb10da5fd861bc48b8`
- Successor module size: `4224512` bytes
- Frozen predecessor module SHA-256 before and after:
  `410ac6b742192cfcd3568e36975bc87ecab4c2de9093d30113258b74a887e8cb`
- Frozen predecessor module size: `4223488` bytes
- Adapter API: `sts-lightspeed-noncombat-adapter-v3`
- Baseline policy: `sts_lightspeed_simple_agent_no_potions_v1`
- Native target policy: `sts_lightspeed_simple_agent_target_v1`
- Compiler: GCC `15.2.0`, C++ `201703`
- CMake: `4.3.1`, generator `Ninja`
- Python: `3.10.18`
- pybind11 build identity: `3.0.2a0`

The external simulator remained at commit
`7476a81954020087da31d41d16fddf475746ec2d` with compiled-source SHA-256
`a3f98721ec37373b1b00aef660832a3307f0186ba0614d07a3b1e7de8ab2e46a`
over 79 files. Its pre-existing dirty state remained:

- modified root `CMakeLists.txt`;
- checked-out `json` submodule commit
  `55f93686c01528224f448c19128836e7df245f72`;
- checked-out `pybind11` submodule commit
  `8f68ecd32c8e18d3b064dbf0ea5fc31a6cb37e9a`; and
- pre-existing untracked `AGENTS.md` and `CLAUDE.md`.

The first isolated configure attempt timed out during compiler ABI detection
because MinGW `windres` was absent from the sandbox PATH. A second attempt
failed before generation because a backslash path was written unescaped. The
verified partial directory contained zero `.pyd` files and was removed. The
successful configure used explicit forward-slash paths for `g++`, `windres`,
`ar`, `ranlib`, Ninja, Python, and the read-only simulator checkout.

## Bounded Native Verification

No fresh formal seed was consumed. All native execution reused the existing
development seeds `0..19` and existing historical-prefix fixtures.

- Targeted deterministic shop lifecycle smoke:
  `1 passed in 6.93s`.
- Full native adapter plus Current bridge focused suite:
  `82 passed in 145.71s`.
- Partitioned repository commit gate:
  `3507 passed, 11 skipped in 222.59s`; total gate time `225.48s`.
- Strict OpenSpec validation: passed.

The reused-seed smoke asserted that:

- every emitted card, relic, and potion price is a nonnegative integer;
- each collection has unique original source slots;
- every legal inventory candidate resolves to a visible entry with the same
  source slot and price;
- positive unaffordable entries remain visible and have no legal buy action;
- at least one inventory purchase occurs; and
- after a purchase, a non-Courier sold slot is absent from the next shop
  snapshot, while a Courier slot must contain its nonnegative replacement.

## Immutable Evidence And Authority

Formal cohorts `7000..7007` and `7100..7107`, their registrations, manifests,
ledgers, and the frozen predecessor module remained unchanged. No game,
Communication Mod process, trainer, model, or live configuration was started
or changed.

The closeout authority is explicitly:

- `baseline_floor_authorized = false`
- `fresh_evidence_authorized = false`
- `gameplay_authorized = false`
- `loading_authorized = false`
- `ope_authorized = false`
- `promotion_authorized = false`
- `qualification_authorized = false`
- `reward_authorized = false`
- `training_authorized = false`
- `formal_rl_readiness_authorized = false`

## Next Decision

Perform one read-only audit of the remaining native shop snapshot fields and
sentinels: inventory identities, remove state, discounts, potion capacity,
Courier/Membership interactions, and candidate/state separation. Only a clean
audit should lead to a separately preregistered third formal native gate with
untouched seeds. Another A-class mismatch should instead receive its own narrow
regression and repair.
