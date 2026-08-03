# Native Shop Sold-Inventory Sentinel Audit

Date: 2026-08-03

## Decision

The adjacent shop inventory risk is a repeated high-confidence structural
mismatch and should be repaired before another native compatibility cohort.
The correct ownership boundary is the native adapter, not Current shop policy
and not bridge metadata hydration.

The mismatch is deterministic after Current buys a card, relic, or potion in a
native shop without The Courier:

1. `sts_lightspeed` leaves the object in its fixed source slot and sets its
   price to `-1`.
2. Native legal-action generation excludes that slot.
3. The API v3 adapter nevertheless serializes every 7 card, 3 relic, and 3
   potion slot into `decision_context`.
4. The bridge hydrates every serialized item and rejects any negative shop item
   price before Current executes.

This is an A-class compatibility defect. It is not evidence about whether
Current should buy the item, and training cannot repair it.

## Source Reconciliation

### Simulator

`Shop::buyCard`, `Shop::buyRelic`, and `Shop::buyPotion` set the purchased
slot's price to `-1` when The Courier does not replace it. With The Courier,
the slot remains populated and receives a replacement item. `getAllShopActions`
and `isValidShopAction` accept inventory actions only when the relevant price
is not `-1` and current gold covers it.

The adapter's snapshot path does not apply that sentinel rule. It loops over
all fixed slots and serializes the item and raw price unconditionally. Its
candidate path separately uses the simulator's legal-action set, so a sold
snapshot item has no matching candidate.

### Live game and Communication Mod

The exact `ShopScreen` class from the installed game was extracted and
decompiled for this read-only audit. Without The Courier, `purchaseCard`
removes the card from `coloredCards` or `colorlessCards`; `updateRelics` and
`updatePotions` remove purchased wrappers from their lists. With The Courier,
the purchased slot is replaced instead.

Communication Mod reads those current lists through `ChoiceScreenUtils` and
serializes only their remaining entries in `GameStateConverter`. Its choice
surface separately filters by affordability. Therefore a Communication
Mod-compatible snapshot contains all visible unsold items, including
unaffordable items, but never a sold sentinel item.

### Bridge

`MetadataCatalog.card`, `.relic`, and `.potion` correctly reject negative shop
prices. Relaxing those validators would expose an item that is absent from the
live screen and could let Current rank or select a sold object. The bridge
already preserves adapter `slot` identity on hydrated objects, so filtering in
the adapter can compact the visible inventory while retaining exact original
slot mapping to legal candidates.

## Evidence Identity

- Installed `desktop-1.0.jar` SHA-256:
  `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`
- Extracted `ShopScreen.class` SHA-256:
  `f154dac4dd9f3e9ca4386aee96f25a32bcdf660a754ad850d482398ee16fa597`
- Communication Mod commit:
  `5e417eb189530986b9047a3c9426889fb261d146`
- `ChoiceScreenUtils.java` SHA-256:
  `adf41ef03eaa25f4f180d05a822e564edd7e5b57b6bc7f652f0bd376a7fe8a5b`
- `GameStateConverter.java` SHA-256:
  `9f708fc8ff9fd9c7b5cef05c083d2d6b59d43b905d47ce6bc72b2a0efc11a1e9`
- Simulator commit:
  `7476a81954020087da31d41d16fddf475746ec2d`
- `Shop.cpp` SHA-256:
  `1025862b24e3dd7f33dd70e9128324b0f28bfc746d01bdfdb44aa7a52b87f036`
- `GameAction.cpp` SHA-256:
  `8a84d545333b9a6a1a0b2bd8d5e705bd1821b940fa6799b52ebf4bcdd4638d9b`
- Current adapter source SHA-256:
  `77a2c0f6ada3e1c34c8d1303e9bbf50e8d8bb2924380d9f27c64c4d13710a806`
- Current bridge source SHA-256:
  `8bcdf38e62455f1fbceba154ba8873404b437ea01b3fb2dbc0b5ed1567c0a246`

The simulator checkout has pre-existing tracked changes to `CMakeLists.txt`
and the `json` and `pybind11` submodule pointers; this audit did not modify that
checkout. Communication Mod has no tracked modifications. The extracted class
and decompiler output were temporary inspection artifacts and are not project
inputs.

## Repair Boundary

The next change should:

- omit exactly `price == -1` card, relic, and potion entries from adapter shop
  snapshot arrays;
- preserve every remaining item's original fixed `slot` field;
- keep unaffordable positive-price items visible even though they have no legal
  candidate;
- preserve Courier replacement entries and their slot identity;
- reject or expose any value below `-1` as a separate structural blocker rather
  than treating every negative as sold;
- prove that bridge hydration and reverse action mapping work with sparse
  original slots; and
- rebuild and smoke-test a successor API v3 module without running a fresh
  formal compatibility cohort in the repair change.

The consumed cohorts `7000..7007` and `7100..7107` remain immutable. A future
formal native gate needs a separate pushed registration and untouched seeds,
but it should not be proposed until this adapter contract is repaired and the
remaining shop snapshot domain has been checked for another sentinel mismatch.

## Authority Boundary

This audit grants no native execution, gameplay, baseline-floor,
target-supported outcome, reward, model, OPE, formal-RL, training,
qualification, loading, or promotion authority. No project source, native
module, seed, Communication Mod process, gameplay process, model, or trainer
was changed or run.
