# Native Shop Domain Audit

Date: 2026-08-03

## Decision

Do not preregister or execute a third formal native compatibility gate yet.
The sold-inventory adapter repair is correct, but the bound
`sts_lightspeed` shop implementation contains two independent A-class
transition defects outside that repair:

1. Courier restocks do not preserve live item and price semantics.
2. Potion purchases spend gold and consume inventory even when Sozu or full
   potion capacity prevents obtaining the potion.

The native shop support surface is therefore not complete enough for formal
four-category evidence or shop-policy training. These are simulator mechanics
defects, not Current policy-quality evidence, and training cannot repair them.

## Finding 1: Courier Restocks Diverge

The installed game and simulator agree that initial A0 shops contain five
colored cards, two colorless cards, three relics, three potions, visible
nonnegative prices, and separately affordability-filtered choices. They do not
agree after a purchase with The Courier.

### Live semantics

The exact installed `ShopScreen`, `StoreRelic`, and `StorePotion` classes were
extracted from `desktop-1.0.jar` and decompiled for this read-only audit.

- A replacement colored card preserves the purchased card's type, rolls a new
  rarity and item, then computes a fresh price with the merchant variation,
  Courier factor `0.8`, and Membership Card factor `0.5` when present.
- A replacement relic or potion resets to the new item's base price, applies a
  fresh merchant variation, then applies Courier and Membership factors.
- Purchasing a relic applies that purchased relic's preview effect to visible
  cards before the slot is restocked.

Existing tracked live evidence independently demonstrates the replacement
boundary in
`reports/known_propensity_exploration_eval_20260714_b5_trace.jsonl`:

- decision `decision-012224dfec8635c4fccb1774eb8c4d47` at line 153 has
  384 gold, Courier, War Paint at slot 0 for 125 gold, purge available at 60;
- after the purge, decision `decision-f5c1f6eef6cc2a5ec5c35e38dfa48eab`
  at line 155 has 324 gold, the same War Paint price, purge unavailable, and
  next purge cost 80; and
- after buying War Paint, decision
  `decision-0dc175cb91028e8cfdc8355a6830b8dc` at line 157 has 199 gold and a
  Courier replacement Toy Ornithopter at the same visible slot for 114 gold.

### Simulator semantics

The bound `Shop.cpp` behaves differently in several deterministic ways:

- `buyRelic` calls `getNewPrice` without assigning its return, so the
  replacement relic retains the purchased relic's old slot price.
- `getNewPrice` replaces the supplied relic or potion base price with
  `round(random(0.95, 1.05))`, yielding 1, and discards both discount return
  values. `buyPotion` assigns that result, so Courier replacement potions cost
  1 gold.
- `getNewCardPrice` tests The Courier twice. A Courier-only replacement card
  receives both the `0.8` Courier factor and an erroneous `0.5` factor.
- A colored replacement card is sampled without preserving the purchased
  card's type.
- `buyRelic` checks the replacement slot, rather than the purchased relic, when
  applying egg preview upgrades. With Courier it can miss a purchased egg's
  effect or apply an unowned replacement egg's effect.

These differences alter later observations, affordability, action ranking,
gold transitions, and card upgrade state. A formal gate that happens not to
encounter Courier cannot establish full shop compatibility.

## Finding 2: Invalid Potion Transactions Execute

The live `StorePotion.purchasePotion` path first rejects Sozu. It then calls
`player.obtainPotion` and loses gold, records the purchase, and removes or
restocks the item only when obtaining the potion succeeds. A full potion belt
therefore leaves gold and inventory unchanged.

In the simulator:

- `GameContext::obtainPotion` returns without changing state under Sozu or when
  `potionCount == potionCapacity`;
- both `getAllShopActions` and `isValidShopAction` nevertheless report a potion
  action whenever its price is nonnegative and affordable; and
- `Shop::buyPotion` ignores the failed obtain, loses gold, then sells or
  restocks the potion.

The adapter currently inherits that candidate and transition. Current avoids
full-belt potion purchases through `_has_potion_space`, but it does not use
that helper to model Sozu, and candidate legality is a contract independent of
which action Current happens to pick. This is an A-class transition mismatch.

## Finding 3: Purge Observation Is Collapsed

This is a lower-priority observation mismatch rather than a demonstrated
Current action mismatch.

Communication Mod reports `purge_available` directly from the live screen and
reports `purge_cost` independently. Choices include purge only when it is both
available and affordable. The adapter emits only simulator `removeCost`, while
the bridge derives availability from the affordable candidate set.

Consequences:

- an available but unaffordable purge hydrates as unavailable; and
- after a purge the simulator sentinel `-1` hydrates as unavailable with cost
  0, while the live trace above reports unavailable with the next cost 80.

Current explicitly checks both availability and affordability, so the first
case does not change its immediate action. The distinction still matters for
an exact RL observation contract and should not be silently treated as live
state.

## Finding 4: Non-A0 Pricing Is Outside The Bound Surface

At ascension 16 the installed game applies a `1.1` shop price multiplier. The
simulator applies `0.8`. Current native registrations are fixed to Ironclad A0,
so this does not block the existing A0 POC, but the adapter's generic ascension
argument must not be interpreted as validated non-A0 shop support.

## Confirmed Supported Surface

For A0 shops without Courier replacement and without invalid potion
transactions, source reconciliation supports:

- initial inventory counts and colored/colorless ordering;
- initial price variation, sale-card ordering, Membership discount, Courier
  initial discount, Smiling Mask, and remove-cost progression;
- visible positive unaffordable inventory separated from legal choices;
- sparse original slot identity after non-Courier purchases; and
- exact sold `-1` filtering in the repaired adapter.

This supported subset is useful for bounded diagnostics but is not authority
for unrestricted shop training.

## Evidence Identity

- Project audit commit base:
  `9637ea78a62899c16a706b31324ab394e706e881`
- Installed `desktop-1.0.jar` SHA-256:
  `cfad868ac8d65a88e71a0bf096fb09f78811e553effe0787c5309a655e081673`
- Installed `ShopScreen.class` SHA-256:
  `f154dac4dd9f3e9ca4386aee96f25a32bcdf660a754ad850d482398ee16fa597`
- Installed `StorePotion.class` SHA-256:
  `809b1becbd6cb0171346283526b570302afd8d6bf9eba8e0ba3fd5d7255547bf`
- Installed `StoreRelic.class` SHA-256:
  `640669eab8c43b119bb5c93d4ae107c9bb7dbb8989a3fbf97b91fc1a7204eb30`
- Communication Mod commit:
  `5e417eb189530986b9047a3c9426889fb261d146`
- `ChoiceScreenUtils.java` SHA-256:
  `adf41ef03eaa25f4f180d05a822e564edd7e5b57b6bc7f652f0bd376a7fe8a5b`
- `GameStateConverter.java` SHA-256:
  `9f708fc8ff9fd9c7b5cef05c083d2d6b59d43b905d47ce6bc72b2a0efc11a1e9`
- Live Courier trace SHA-256:
  `4412e8e446ad72d572a856149985eaa2993f5131ac9ef0c1cdfba337dbf3733e`
- Commit that introduced the tracked live trace:
  `b9195667fdf1e96817b8dbfce5791476f4df4422`
- Simulator commit:
  `7476a81954020087da31d41d16fddf475746ec2d`
- `Shop.cpp` SHA-256:
  `1025862b24e3dd7f33dd70e9128324b0f28bfc746d01bdfdb44aa7a52b87f036`
- `GameAction.cpp` SHA-256:
  `8a84d545333b9a6a1a0b2bd8d5e705bd1821b940fa6799b52ebf4bcdd4638d9b`
- `GameContext.cpp` SHA-256:
  `aad9fcf6db5a667858185256722065d61167393f891ee8a717e4e37b4c28a053`

The simulator's previously recorded dirty root and submodule state remained
unchanged. Communication Mod had only its pre-existing untracked `CLAUDE.md`.
Extracted classes and decompiler output were temporary read-only audit
artifacts and are not project inputs.

## Recommended Next Change

Use a two-level response rather than consuming another gate:

1. Add a narrow, fail-closed native shop support envelope. It should make
   Courier shop decisions explicitly unsupported and prevent potion purchase
   candidates when Sozu or full capacity makes the transaction impossible.
   It must report blocker counts and grant no training authority.
2. Treat full Courier support as a separate simulator-mechanics project. The
   preferred durable fix is a provenance-bound patch against a clean
   `sts_lightspeed` source identity, not hidden price correction in the Python
   bridge. That work must cover replacement item type, RNG consumption, base
   price, discounts, egg preview effects, and potion transaction atomicity.

After the fail-closed envelope, reassess whether a third A0 gate is useful for
the supported subset. Full four-category shop RL remains no-go until the
simulator mechanics repair is source-tested and rebound to a new module.

## Authority Boundary

This audit grants no gameplay, fresh cohort, simulator loading, baseline floor,
reward, OPE, formal-RL, training, qualification, or promotion authority. No
game, Communication Mod process, trainer, model, external checkout, or live
configuration was changed or run.
