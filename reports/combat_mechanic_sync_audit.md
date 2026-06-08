# Combat Mechanic Sync Audit

This report tracks mechanics that were proven during sim divergence work and
may also need to be reflected in live combat estimators. The goal is not to
make `sim_divergence.py` a shared runtime dependency; it is to prevent separate
decision-time estimators from preserving mechanics that live evidence has
already disproved.

## Estimator Surfaces

- `spirecomm/ai/sim_divergence.py`: diagnostic one-action oracle.
- `spirecomm/ai/heuristics/combat_ending.py`: lethal detection and lethal
  sequence construction.
- `spirecomm/ai/heuristics/simulation.py`: beam-search combat simulation,
  fast scoring, and sequence scoring.
- `spirecomm/ai/heuristics/ironclad_combat.py`: target choice and fallback
  combat planning.
- RL guard/reward code: action vetoes and reward estimates that may duplicate
  card or combat outcome estimates.

## Sync Rules

- Port deterministic mechanics that affect live decision estimates.
- Do not blindly port trace-settlement boundaries that only suppress diagnostic
  false positives, such as delayed CardSelect animation fields, unless the
  decision estimator also predicts that intermediate state.
- Each port should have its own focused regression in the owning estimator's
  test file before implementation.

## Coverage Matrix

Status labels:
- `synced`: focused regression exists in the owning estimator surface.
- `partial`: at least one live estimator surface is synced, but related surfaces
  still need evidence-based review before claiming full coverage.
- `n/a`: the surface does not estimate that mechanic directly.

| Mechanic family | Diagnostic evidence | Lethal detection | Beam / fast sim | Ironclad fallback / targeting | Timing planner | RL guards / reward / state | Current gap |
| --- | --- | --- | --- | --- | --- | --- | --- |
| Static zero-live attack damage, including upgrades | Headbutt and upgraded attack divergence tests | synced | synced | synced | synced | synced for survival guards and legacy state features | Check only if a new estimator reads raw `card.damage` directly. |
| Context-dependent attack base damage | Mind Blast draw-pile-count divergence tests | synced | synced | synced | synced | synced for survival guards and legacy hand-state features | Context-free card-reward features remain `n/a`; they intentionally lack draw-pile context. |
| X-energy and per-hit attacks | Whirlwind divergence and guard tests | synced | synced | synced | synced | synced for relevant RL survival multi-hit paths | Watch for newly added scalar damage shortcuts. |
| Reactive monster block timing | Twin Strike into Curl Up Louse clean divergence; earlier Malleable multi-hit evidence | synced for Curl Up and Malleable between cards | synced for Curl Up and Malleable after the full multi-hit card | n/a for scalar fallback; target reaction is owned by simulator/lethal search | n/a unless timing starts simulating target reactions directly | n/a until a guard predicts target-side reactive block | Watch for any new direct lethal/target shortcut that bypasses the shared simulator or `CombatEndingDetector`. |
| Hand-count attack damage | Fiend Fire divergence and guard tests | synced | synced | synced | synced | not currently duplicated outside encoded card identity | No immediate gap found; recheck only when RL adds Fiend Fire-specific damage guards. |
| Target-side attack modifiers | Weak, Vulnerable, Paper Phrog divergence tests | synced | synced | synced | synced | synced for Slime split survival guard | Generic scoring that does not estimate player attack damage is `n/a`. |
| Minimum attack HP damage | The Boot Pummel, Reaper, Anger, and Strike-through-block clean divergence rows | synced for per-hit and after-block lethal paths | synced for attack-hit damage after block | synced for scalar per-hit fallback estimates | n/a unless timing adds The Boot-specific scalar shortcuts | no direct RL guard/reward surface found in this round | Watch for future damage shortcuts that skip the shared simulator or lethal detector. |
| Monster lifecycle states | Darkling half-dead/revive plus Collector summon/reorder divergence evidence | n/a | synced for Darkling revive, death split, and concrete current-move summons without negative lifecycle damage score | synced | synced for SAFE timing bonus | synced for v2 state alive flag and reward exit handling | Random/generic summons still need explicit live evidence and concrete minion data before materialization. |
| Combat escape settlement | Looter/Mugger escape and Smoke Bomb divergence evidence | n/a | synced for Smoke Bomb potion escape and Looter/Mugger end-turn escape projection without kill/lethal credit | n/a | n/a | synced for in-combat and combat-exit reward | Other escape monsters should be added only with explicit intent/move evidence. |
| End-turn status damage | Burn/Burn+ and Decay divergence tests | n/a | synced | n/a | n/a | synced for RL survival/Guardian guards | No current target-selection surface uses status settlement directly. |
| Countdown monster self-detonation | Fresh floor-46 EndTurnAction row: two Exploders with `Explosive=1` dealt blockable 30 damage each, died, and killed the player while the old sim expected no damage | n/a unless lethal search starts projecting enemy self-detonation | synced for diagnostic end-turn projection, fast incoming estimates, and enemy lookahead through shared Exploder countdown helper | synced for DecisionContext threat/targeting and heuristic incoming fallback | n/a unless timing starts modeling Exploder countdown separately | synced for RL incoming and event-by-event end-turn survival damage after block | Recheck future reward/state encoders only if live evidence shows they duplicate Exploder countdown risk. |
| Player HP-loss prevention / revive | Tungsten Rod Bloodletting and end-turn HP-loss evidence; Buffer/Fossilized Helix end-turn clean divergence; Fairy in a Bottle end-turn lethal clean divergence | synced for HP-cost energy support cards | synced for card HP costs, Blue Candle, Thorns/Sharp Hide, deterministic end-turn HP-loss projection, Buffer/Fossilized Helix event-level damage prevention, Fairy HP-loss revival, and Fairy-aware outcome death checks | synced for current-turn lethal penalty using simulator HP-loss projection | n/a | synced for survival and Guardian guard end-turn lethal checks where the guard owns the HP-loss path, including Buffer event-level damage prevention | RL aggregate incoming still does not consume per-hit revives; revisit only with live evidence that it changes an action. |
| Potion-triggered relic healing | Toy Ornithopter Energy Potion clean divergence | n/a | synced for diagnostic and beam potion state simulation after any potion use | n/a | n/a | partial; no deterministic RL guard/reward surface found in this round | Potion prefilter priority still does not add Toy-specific value; change it only with evidence that ranking or guard logic changes an action. |
| Relic attack/resource effects | Pen Nib, Nunchaku, Ornamental Fan, Orichalcum divergence tests | synced where lethal is affected | synced | synced for Pen Nib scalar fallback damage estimates, Nunchaku counter-9 refund-preserving attack-before-defense ordering, Ornamental Fan direct/Havoc-top attack block, and Orichalcum effective block before defense priority | synced for Pen Nib damage estimates, Nunchaku targeted lethal search, cache invalidation over relic counters plus draw-pile/hand/deck inputs, Ornamental Fan direct/Havoc-top attack block, and Orichalcum effective turn block before fallback block scoring | synced for direct and Havoc-top Ornamental Fan survival block, Orichalcum survival block, and other survival/block guards already noted | Future scalar shortcuts must state whether non-damage relic counters are read or intentionally ignored. |
| Exhaust-triggered block/damage | Havoc, nested Havoc, Feel No Pain, Juggernaut divergence tests plus fresh Havoc top-energy and Shockwave self-exhaust evidence | synced for deterministic top attacks, top-card exhaust damage, and visible top energy skills | synced for nested top-card Havoc recursion | synced for deterministic and nested Havoc top-card block, Feel No Pain fallback priority, and direct self-exhaust Feel No Pain block | synced for deterministic Havoc top-card block, Feel No Pain in fallback scoring, and direct self-exhaust Feel No Pain block | synced for survival and shared block guards where guard can prove target/effect | Havoc random-target boundaries remain conservative by design. |
| Exhaust-triggered energy | Fresh Second Wind/Sentinel clean divergence plus same-class Fiend Fire and Sever Soul regressions | synced for Second Wind and Sever Soul support lines that unlock follow-up attacks | synced | n/a until fallback scoring starts estimating hand-exhaust energy lines directly | n/a unless timing starts searching hand-exhaust energy lines | no direct RL guard/reward surface found this round | `sim_divergence.py` now models Sentinel energy from Second Wind, Sever Soul, and Fiend Fire. Lethal detection keeps the scope to support cards that can enable exact lethal follow-up attacks. |
| Card-play-count power damage | Panache clean divergence on fifth-card Anger AOE damage | synced for immediate-trigger support cards and attack-triggered exact search | synced | n/a | n/a | n/a | Upgrade damage and non-immediate pure support advancement need fresh live evidence before broader search expansion. |
| Next-card replay effects | DuplicationPower clean divergence on Defend block plus fresh Writhing Mass Carnage+ replay/Malleable row | synced for direct next-attack lethal search, deterministic support effects inside targeted lethal search, and Malleable block between replayed attacks | synced for replayed attacks settling target reactions between plays | partial; no direct fallback reader found in this round | partial; audit only if timing code starts reading DuplicationPower outside lethal/simulator paths | partial; no direct RL guard/reward reader found in this round | Keep future scalar shortcuts honest about whether the next card is executed twice while energy is paid once, and whether target reactions settle between the replayed card plays. |
| Fatal attack resource rewards | Feed clean divergence on non-minion kill max/current HP gain | n/a | synced | n/a | n/a | n/a | Diagnostic oracle was missing Feed's post-kill HP reward; beam/fast sim already had focused coverage. |
| Healing and monster self-heal | Bandage Up, Shelled Parasite Suck divergence tests | n/a | synced | n/a | n/a | n/a | Only fast/beam sim currently predicts these HP transitions. |

## Confirmed Sync Work

- 2026-06-08: Nested Havoc top-card execution is now synced from the
  residual clean-trace floor-16 Havoc row into the diagnostic oracle and
  Ironclad fallback block estimator. Live played a visible top-deck `Havoc`,
  then that nested Havoc played the next visible `Defend`, raising player block
  by 5 while the old oracle and fallback estimator stopped after the first top
  card. `sim_divergence.py` now consumes Havoc top cards from the evolving
  expected draw pile and recursively applies nested top-card Havoc effects.
  `IroncladCombatPlanner` fallback scoring walks visible draw-pile cards from
  the top, passes through nested Havocs, and counts both the nested block card
  and per-exhaust Feel No Pain block. `FastCombatSimulator` already modeled
  this recursion, and now has a focused guard to keep that behavior locked.
- 2026-06-08: DuplicationPower attack replay now keeps card-play
  boundaries distinct from natural multi-hit attacks in the diagnostic oracle.
  The residual clean-trace Writhing Mass row showed `DuplicationPower` replaying
  `Carnage+`; live let the first replay trigger Malleable block before the
  second replay, leaving the monster at `1` HP with block, while the old oracle
  merged the replays into one larger hit sequence and marked it dead.
  `sim_divergence.py` now applies repeated attack plays one replay at a time,
  preserving the existing deferred Malleable/Curl Up behavior only within a
  single multi-hit card. Focused guard tests show `FastCombatSimulator` and
  `CombatEndingDetector` already model this replay boundary correctly, so this
  round did not change live estimator code.
- 2026-06-08: Exploder countdown explosion is now synced from the fresh
  floor-46 death row into the diagnostic oracle and live combat estimators.
  `incoming_damage.py` exposes a shared helper that recognizes an `Exploder`
  with `Explosive=1` and returns the current-turn blockable 30-damage
  explosion. `sim_divergence.py` applies that damage during EndTurn
  projection, then marks the exploding monsters gone so the oracle no longer
  expects them to remain alive. `FastCombatSimulator` carries the countdown in
  `SimulationState`, includes it in incoming-damage estimates and enemy
  lookahead, and removes the monster after the explosion. `DecisionContext`,
  heuristic incoming fallback, and RL survival guards now count the same risk
  even when the live payload has `move_id=None` and `move_adjusted_damage=0`.
- 2026-06-08: The Boot minimum attack HP damage is now synced from the fresh
  clean-trace Pummel/Strike/Reaper evidence into the diagnostic oracle and
  live combat estimators. `sim_divergence.py` applies the relic's 5-damage
  floor after attack damage is reduced by monster block, eliminating false
  monster HP divergence for small unblocked hits and small post-block HP
  damage. `FastCombatSimulator` carries The Boot in `SimulationState`, applies
  the same floor only on attack damage, and leaves direct damage such as
  potions, Panache, Juggernaut, and end-turn effects unchanged.
  `CombatEndingDetector` applies the floor both to per-hit total attack
  estimates and to exact after-block target simulation, so Pummel-style
  multi-hit lethal and Strike-through-block lethal lines are provable.
  `IroncladCombatPlanner` fallback damage estimates now apply the same per-hit
  floor after Weak handling.
- 2026-06-08: Sentinel exhaust energy is now synced from fresh
  `Second Wind` clean divergence evidence into the diagnostic oracle and
  targeted lethal detection. `sim_divergence.py` models the +2/+3 energy
  refund when `Sentinel`/`Sentinel+` is exhausted by `Second Wind`,
  `Sever Soul`, or `Fiend Fire`, reducing false player-energy divergences for
  this hand-exhaust family. `CombatEndingDetector` can now prove lethal lines
  where `Second Wind` or `Sever Soul` exhausts a visible `Sentinel` and the
  refunded energy pays for follow-up attacks, while still removing the
  exhausted cards from the remaining search state. `FastCombatSimulator`
  already had focused Sentinel exhaust coverage, so this round preserved that
  surface rather than changing it.
- 2026-06-08: Buffer/Fossilized Helix damage prevention is now synced from
  fresh Centurion/Mystic end-turn divergence evidence into the diagnostic
  oracle and live survival estimators. `sim_divergence.py` consumes one Buffer
  charge on the first unblocked HP-loss event. `FastCombatSimulator` carries
  Buffer in `SimulationState`, projects incoming damage by events so a second
  attacker can still be lethal after Buffer absorbs the first hit, and avoids
  double-applying prevention when converting final HP loss to projected HP.
  `IroncladCombatPlanner` current-turn lethal penalty now asks the simulator
  for projected HP loss after block instead of using raw `incoming - block`.
  `CombatRLAgent` survival end-turn damage now reads live Buffer powers and
  applies Buffer/Tungsten by damage event before deciding whether a block
  takeover is required.
- 2026-06-08: Curl Up reactive block timing is now synced from fresh
  `Twin Strike` clean divergence evidence into the diagnostic oracle, beam
  simulation, and lethal detection. Multi-hit attack damage now resolves all
  hits before the surviving monster gains Curl Up block, matching the live
  Louse evidence where the block did not absorb the second Twin Strike hit.
  Single-hit Curl Up behavior remains unchanged, and `CombatEndingDetector`
  carries Curl Up state between attack cards so false lethal lines such as
  `Twin Strike` plus `Strike` are rejected.
- 2026-06-08: `sim_divergence.py` now models the confirmed `Feed`
  fatal reward from the post-Toy clean batch. When `Feed` kills a non-minion
  enemy, the diagnostic oracle increases both max HP and current HP by 3, or 4
  for upgraded `Feed+`, while excluding minion kills. The live beam estimator
  already had focused `Feed` coverage for normal, upgraded, and minion cases,
  so this round did not require a live estimator code change.
- 2026-06-08: Toy Ornithopter potion healing is now synced from fresh
  Energy Potion divergence evidence into the diagnostic oracle and beam potion
  state simulation. `sim_divergence.py` applies the relic's 5 HP heal after a
  resolved potion use even when the potion's own effect value is zero.
  `FastCombatSimulator` carries Toy Ornithopter in `SimulationState` and
  `HeuristicCombatPlanner._simulate_potion_use` applies the same heal after
  potion effects, so survival/outcome estimates see the real post-potion HP.
- 2026-06-08: Fairy in a Bottle revival is now synced from the fresh
  Hexaghost end-turn lethal divergence into the diagnostic oracle and beam
  outcome scoring. `sim_divergence.py` recognizes `FairyPotion` /
  `Fairy in a Bottle`, restores 30% max HP when HP loss would kill the player,
  and consumes one Fairy so repeated hits cannot revive indefinitely.
  `FastCombatSimulator` carries Fairy revive count and revive HP in
  `SimulationState`, routes shared HP-loss paths through the same one-shot
  revival, and makes outcome scoring's death check ask whether projected
  incoming damage is survivable after Fairy instead of returning `-inf`.
- 2026-06-08: Panache fifth-card damage is now synced from fresh clean-trace
  Anger divergence evidence into the diagnostic oracle and live combat
  estimators. `sim_divergence.py` decrements the active Panache card counter
  and applies the confirmed 10 AOE damage when it reaches the trigger point,
  then resets the live-visible counter to 5. `FastCombatSimulator` carries the
  same counter in `SimulationState` and applies the triggered AOE after each
  simulated card play. `CombatEndingDetector` targeted lethal search now counts
  attack-triggered Panache damage and immediate-trigger non-attack support
  cards, while avoiding a broad expansion of pure support-card search before
  there is live evidence for non-immediate Panache setup lines.
- 2026-06-08: Tungsten Rod HP-loss prevention is now synced from fresh
  `Bloodletting` and end-turn clean-trace divergence evidence into the
  diagnostic oracle and live estimators. `sim_divergence.py` reduces actual
  player HP loss after block for self-damage, Blue Candle, Sharp Hide/Thorns,
  monster attacks, status, Combust/Brutality, and Havoc top-card replay paths.
  `FastCombatSimulator` carries the relic in `SimulationState` and routes card
  HP costs plus deterministic end-turn HP-loss projections through the same
  reduction while preserving existing Rupture trigger boundaries.
  `CombatEndingDetector` applies the reduction per repeated HP-cost energy
  support play, so 3 HP plus Tungsten Rod can still use Bloodletting for a
  deterministic kill. `CombatRLAgent` survival and Guardian guards now count
  Tungsten Rod when comparing end-turn HP loss against current HP.
- 2026-06-08: `sim_divergence.py`, `FastCombatSimulator`, and
  `CombatEndingDetector` now model the confirmed `DuplicationPower` replay
  boundary in the paths touched by fresh evidence. The divergence oracle
  accepts the clean Defend block replay case while paying energy once and
  consuming the power once; fast simulation repeats duplicated card effects
  through the existing card-effect paths; and targeted lethal search counts a
  duplicated next attack plus deterministic support effects without leaving the
  power active for later cards.
- 2026-06-08: `IroncladCombatPlanner`, `TimingAwareCombatPlanner`, and
  `CombatRLAgent` survival block estimates now count Feel No Pain block from
  directly played self-exhausting cards such as Shockwave. The shared
  lightweight detector uses the live `card.exhausts` field first, then falls
  back to card text that ends in `Exhaust.`, so cards that exhaust other cards
  are not treated as self-exhausting. The added block is not reduced by Frail.
- 2026-06-08: `CombatEndingDetector` targeted lethal search now treats
  `Havoc` with a visible draw-pile top energy skill as a deterministic support
  action. The search spends only Havoc's cost, applies the top card's
  `Seeing Red`/`Bloodletting`/`Offering` energy gain and HP loss, consumes that
  top card for later Havoc branches, and reuses the existing top-card exhaust
  damage handling. This syncs the fresh Havoc energy divergence evidence into
  live lethal detection, matching the already-synced fast simulator behavior.
- 2026-06-07: `FastCombatSimulator` now applies the Blue Candle HP-loss cost
  when a Curse is played. The HP loss bypasses block and reuses the same
  player-HP-loss path as other HP-cost cards, keeping Rupture handling
  consistent with existing simulator mechanics.
- 2026-06-07: `FastCombatSimulator` end-turn projection now revives BUFF-ready
  half-dead Darklings to half max HP and marks them live again. This syncs the
  Darkling lifecycle boundary proven by sim divergence into beam/fast scoring
  and direct enemy lookahead, while non-BUFF half-dead states remain waiting.
- 2026-06-08: `StateEncoderV2` now treats `half_dead` monsters as not alive
  even when the live payload still carries positive HP. This aligns the RL v2
  observation surface with the already-synced target masks and revive
  transition guard for monster lifecycle states.
- 2026-06-08: `IroncladCombatPlanner` target selection now excludes simulated
  `half_dead` monsters even when their HP field remains positive. This keeps
  legacy and v2 fallback target pickers aligned with the simulator's Darkling
  lifecycle handling.
- 2026-06-08: `IroncladCombatPlanner` target pruning cleanup-phase detection
  now counts only live simulated monster states, so `half_dead` monsters no
  longer prevent low-HP live targets from using greedy cleanup targeting.
- 2026-06-08: `FastCombatSimulator` SAFE timing bonus now uses the simulator
  live-monster predicate, excluding `half_dead` monsters whose HP field remains
  positive during lifecycle transitions.
- 2026-06-08: `RewardCalculator` combat-exit finishing damage now uses a live
  monster predicate that excludes `is_gone` and `half_dead` monsters, preventing
  lifecycle waiting states from generating extra damage or kill reward.
- 2026-06-08: `RewardCalculator` HP-delta and combat-exit reward now treat
  Looter/Mugger escape settlement after `EndTurnAction` as escape rather than
  player damage, a kill, or combat victory. Explicit `Intent.ESCAPE` and the
  local database's Looter/Mugger escape move id suppress damage, kill,
  finishing-damage, and all-lethal reward for that transition, while
  player-card kills against escape-intent monsters still count as real damage
  and kills.
- 2026-06-08: `FastCombatSimulator` end-turn projection now marks explicit
  escape-intent monsters and the Looter/Mugger escape move as gone while
  tracking escaped monsters separately from kills. Outcome scoring removes the
  escaped monster from live threats without awarding kill or all-lethal credit.
- 2026-06-08: `FastCombatSimulator` end-turn projection now materializes
  concrete minions for the current summoning monster move, including The
  Collector's Spawn move producing two Torch Heads. Summoned minions get HP and
  attack intent/damage from monster data so future-threat scoring can see them,
  while outcome damage scoring uses tracked player damage with an existing-slot
  fallback so newly summoned HP is not counted as negative damage.
- 2026-06-08: legacy RL `StateEncoder` hand/card-reward damage features now
  fall back to parsed static attack damage when live attack cards report zero
  damage, including upgraded static attacks such as Headbutt+. This keeps RL
  observation features aligned with the confirmed zero-live-damage Headbutt
  divergence without pretending to encode context-dependent attacks such as
  Mind Blast in the context-free card helper.
- 2026-06-08: legacy RL `StateEncoder` hand-card damage features now use the
  current draw-pile count for zero-live-damage Mind Blast when encoding a full
  combat `game`. The context-free single-card helper still leaves Mind Blast at
  zero, so card-reward features do not invent draw-pile context that they do
  not have.
- 2026-06-08: `TimingAwareCombatPlanner` scalar card-damage estimates now read
  the Pen Nib relic counter and double attack damage when the counter is 9.
  The multiplier is applied before later player Weak and target Vulnerable
  modifiers, keeping timing damage checks aligned with the Pen Nib divergence
  and fast-simulator behavior.
- 2026-06-08: `TimingAwareCombatPlanner` targeted lethal search now carries the
  Nunchaku relic counter in its search state. Attack cards played at counter 9
  add the confirmed 1 energy refund and reset the counter to 0, so timing
  fallback lethal lines can use Nunchaku-enabled follow-up attacks instead of
  stopping after the first affordable card.
- 2026-06-08: `CombatRLAgent` survival block replacement now counts the
  confirmed Ornamental Fan block from directly playing an attack when the relic
  counter shows the next attack is the third attack. This lets survival guards
  keep or choose an attack that produces 4 block instead of treating the attack
  as zero defensive value.
- 2026-06-08: `CombatRLAgent` survival replacement now counts Orichalcum's
  end-turn 6 block when the player currently has no block. This prevents the
  survival guard from replacing an otherwise safe attack just because its
  lethal check ignored the confirmed Orichalcum block settlement.
- 2026-06-08: `CombatRLAgent` survival block replacement now also counts
  Ornamental Fan block from Havoc playing a visible top-deck attack. The
  game-aware Havoc block estimate includes the top attack's third-attack Fan
  trigger, so a Fan-enabled Havoc can outrank a weaker ordinary block card.
- 2026-06-08: `TimingAwareCombatPlanner` fallback block scoring now counts
  the confirmed Ornamental Fan block when the next direct attack is the third
  attack this turn. The same card-block estimate also covers deterministic
  Havoc lines where the visible draw-pile top card is an attack, while leaving
  ordinary card block under the existing Dexterity/Frail modifiers and adding
  the relic block afterward.
- 2026-06-08: `IroncladCombatPlanner` fallback priority now counts
  Ornamental Fan block from direct attacks and deterministic Havoc top-card
  attacks when the relic counter shows the next attack is the third attack this
  turn. Fan block is added after ordinary card block modifiers, and Fan-enabled
  attacks can satisfy the fallback's missing-block check before it spends the
  turn on a weaker pure defense card.
- 2026-06-08: `IroncladCombatPlanner` no-simulation fallback damage and
  card-priority bonus damage now read Pen Nib's counter for scalar attack
  estimates. When Pen Nib is ready, source-side attack damage is doubled before
  the existing player Weak adjustment, matching the confirmed divergence and
  simulator/timing planner ordering.
- 2026-06-08: `TimingAwareCombatPlanner` cache invalidation now includes the
  mechanics-sensitive state read by recent timing estimators: relic identities
  and counters, draw pile, hand, and deck fingerprints. This prevents stale
  same-turn plans from reusing pre-Pen-Nib damage, stale Nunchaku state,
  old Mind Blast/Havoc draw-pile context, or old Fiend Fire/Perfected Strike
  card-count context.
- 2026-06-08: `TimingAwareCombatPlanner` fallback block scoring now counts
  deterministic Havoc block when the visible draw-pile top card gains block,
  plus the confirmed Feel No Pain block from exhausting that top card. This
  lets the timing-only fallback choose Havoc for known top-card defense while
  preserving the existing conservative boundary for random-target damage.
- 2026-06-08: `TimingAwareCombatPlanner` fallback block scoring now suppresses
  redundant card-block value when confirmed effective turn block already covers
  current incoming damage. This syncs Orichalcum's end-turn 6 block, plus
  existing current block and end-turn block powers, into timing-only fallback
  priorities while keeping immediate current-block mechanics such as Body Slam
  on current block only.
- 2026-06-08: `IroncladCombatPlanner` fallback priority now counts
  deterministic Havoc block when the visible draw-pile top card gains block,
  plus the confirmed Feel No Pain block from exhausting that top card. This
  lets the legacy fallback choose Havoc for known top-card defense while
  preserving the existing conservative boundary for random-target damage.
- 2026-06-08: `IroncladCombatPlanner` fallback priority now uses the simulator's
  effective turn block when deciding whether defensive cards are needed. This
  lets confirmed Orichalcum end-turn block cover low incoming damage before
  the legacy fallback spends a card on redundant defense, while immediate
  current-block mechanics such as Body Slam still read current block only.
- 2026-06-08: `IroncladCombatPlanner` fallback priority now treats a Nunchaku
  counter-9 attack as resource-preserving when that refund enables a defensive
  follow-up that would otherwise be unaffordable. This lets fallback play the
  refunding attack before spending the only current energy on defense, matching
  simulator, lethal, and timing Nunchaku behavior without changing ordinary
  attack priority.
- 2026-06-07: `CombatEndingDetector` now uses the same confirmed target-side
  attack modifier shape as the divergence oracle for:
  - player Weak plus target Vulnerable combined before final integer
    truncation (`9/8`);
  - Paper Phrog target Vulnerable (`7/4`);
  - Paper Phrog plus player Weak and target Vulnerable (`21/16`).
- 2026-06-07: `FastCombatSimulator` and the same-file no-simulation attack
  estimate now share that target-side attack modifier shape:
  - `simulate_card_play` attack branches apply player Weak plus target
    Vulnerable with one final truncation;
  - Paper Phrog increases target Vulnerable attack damage to `7/4`;
  - fallback attack damage scoring uses the same helper before Slow and hit-count
    expansion.
- 2026-06-07: `IroncladCombatPlanner` fallback attack damage estimates now
  count upgraded static attack damage when parsed card data only exposes the
  base value. This keeps Bash follow-up checks and non-clone fallback scoring
  from underestimating cards such as Headbutt+.
- 2026-06-07: `CombatRLAgent` survival and Guardian Sharp Hide guards now
  distinguish Burn's blockable end-turn damage from Decay's HP loss through
  block. Monster damage and Burn share current block; Decay remains unblocked
  when deciding whether to replace an RL attack with a defensive card.
- 2026-06-07: `TimingAwareCombatPlanner` target-specific and scalar timing
  damage estimates now use the confirmed target-side attack modifier shape:
  - player Weak plus target Vulnerable is combined before final integer
    truncation (`9/8`);
  - Paper Phrog target Vulnerable uses `7/4`;
  - Paper Phrog plus player Weak and target Vulnerable uses `21/16`.
- 2026-06-07: `IroncladCombatPlanner` no-simulation fallback attack estimates
  now apply player Weak with per-hit integer truncation. This keeps fallback
  strategic thresholds such as Bash follow-up detection from treating Weak
  attacks as if they still dealt full damage.
- 2026-06-07: `CombatRLAgent` Slime Boss split survival retarget guard now
  reduces survival attack damage while the player is Weak. This prevents the
  guard from retargeting to an attacker that only looks killable under full
  card damage.
- 2026-06-07: `IroncladCombatPlanner` fallback card-priority damage bonuses now
  reduce known scalar attack damage while the player is Weak. This keeps
  strategic bonus scoring for cards such as Iron Wave, Immolate, and Whirlwind
  from valuing full visible attack damage under Weak.
- 2026-06-08: `IroncladCombatPlanner` fallback card-priority damage bonuses
  now add Strength when falling back to parsed static attack damage for live
  cards reporting zero damage, such as Headbutt. Explicit nonzero live damage
  remains treated as already adjusted to avoid double-counting Strength.
- 2026-06-07: `FastCombatSimulator` now applies deterministic Havoc top-card
  effects when the draw-pile top card is visible. Known top attacks resolve for
  single-monster or AOE/random-target cases, known top skills and powers reuse
  the existing live simulators, and the top card contributes one exhaust event
  for exhaust synergies such as Feel No Pain. Later simulated Havoc plays skip
  top cards already consumed by the current simulated line.
- 2026-06-07: `CombatEndingDetector` now treats Havoc with a visible draw-pile
  top attack as a deterministic lethal action when the resulting target outcome
  is provable. Single-target top attacks can prove lethal only with one live
  monster, AOE top attacks apply through the existing AOE lethal damage path,
  and the returned action remains the Havoc play rather than the consumed top
  card.
- 2026-06-07: `CombatEndingDetector` now counts the deterministic
  Feel No Pain plus Juggernaut damage from Havoc exhausting a visible
  draw-pile top card. This only proves lethal when Juggernaut's random target is
  deterministic with one live monster; multi-monster cases remain conservative.
- 2026-06-07: `CombatRLAgent`'s Havoc risk guard now allows RL-selected Havoc
  when the visible draw-pile top card is a deterministic attack. Single-monster
  top attacks and AOE top attacks are treated as non-risky; targeted top attacks
  with multiple live monsters remain conservative because Havoc target selection
  is not provable there.
- 2026-06-08: `CombatRLAgent` survival block replacement now counts
  deterministic Havoc block when the draw-pile top card is visible. The
  game-aware estimate adds the visible top card's own block and the
  Feel No Pain block from exhausting that top card, so survival takeovers can
  choose Havoc when the hand card itself reports zero block.
- 2026-06-08: `CombatRLAgent`'s shared block-action candidate path now uses
  the same game-aware Havoc block estimate. Guardian pressure and other RL
  block guards that use the shared candidate can now see Feel No Pain block
  from Havoc exhausting a visible draw-pile top card instead of treating Havoc
  as zero block.
- 2026-06-07: `FastCombatSimulator` and the same-file no-simulation attack
  estimate now apply Pen Nib when the relic counter is 9. The source-side
  attack damage is doubled before player Weak and target Vulnerable, simulated
  attack plays advance or consume the counter, and fallback scalar estimates
  read the current counter without mutating state.
- 2026-06-07: Nunchaku counter-9 attack energy gain is now modeled in
  `FastCombatSimulator` and `CombatEndingDetector`. Simulated attack plays
  spend their card cost, then gain 1 energy and reset the relic counter when
  the counter reaches 9; lethal sequence search carries the counter in its
  state key so refund lines can continue into later attacks.
- 2026-06-07: `CombatEndingDetector` now counts Juggernaut damage caused by
  block-gaining card plays when the current lethal-search state has a single
  living monster. Non-attack block cards can prove lethal as support plays, and
  block-gaining attack cards add the same direct damage after their attack
  damage; multi-monster random targeting remains conservative.
- 2026-06-07: `FastCombatSimulator` now models Ornamental Fan attack-count
  block. Simulated attack plays carry a separate Fan counter in the state key
  and gain 4 block on every third attack through the normal block-gain path,
  so downstream reactions such as Juggernaut remain consistent.
- 2026-06-07: `FastCombatSimulator` now defers Malleable block during a
  single multi-hit attack card. Twin Strike/Pummel-style hits and Whirlwind's
  per-energy hits each increment Malleable, but the gained block is applied
  after that card's hits finish so it does not absorb later hits from the same
  attack.
- 2026-06-07: `CombatEndingDetector` targeted lethal and AOE-cleanup searches
  now model target HP, block, and Malleable counters separately. Malleable block
  is deferred within each attack card, then applied before later cards in the
  proposed lethal line, preventing false lethal calls where a nonlethal attack
  creates block that stops the follow-up.
- 2026-06-07: `IroncladCombatPlanner` fallback attack damage estimates and
  `TimingAwareCombatPlanner` scalar damage estimates now count Mind Blast as
  draw-pile-count attack damage when live card damage is reported as zero.
  Strength is applied as source-side attack damage, and each estimator keeps
  using its existing player Weak and target Vulnerable modifier path afterward.
- 2026-06-07: `IroncladCombatPlanner` fallback card-priority damage bonuses
  now count Whirlwind as an X-energy multi-hit attack instead of a static
  scalar damage card. The bonus uses current X-effect energy, applies Strength
  to each hit, and applies player Weak with per-hit integer truncation.
- 2026-06-07: `CombatRLAgent` survival attack damage estimates now count
  Mind Blast as draw-pile-count attack damage when live card damage is reported
  as zero. Strength and player Weak are applied before the survival retarget
  guard decides whether an attack can kill an incoming attacker.
- 2026-06-08: `CombatRLAgent` survival attack damage estimates now also apply
  Strength when falling back to static base damage for live attacks whose
  reported damage is zero, such as Headbutt. This keeps the Slime Boss split
  survival retarget guard from missing Strength-enabled kills on incoming
  attackers.
- 2026-06-08: `CombatRLAgent` survival attack damage estimates now account for
  fixed multi-hit attacks such as Twin Strike and Pummel. Static zero-damage
  fallback keeps per-hit source damage, applies Strength before player
  Weak/target Vulnerable, then multiplies the per-hit result by hit count so
  Slime Boss split retargeting can see multi-hit kills.
- 2026-06-07: `CombatRLAgent` Slime Boss split survival retarget guard now
  evaluates attack damage against each candidate target. Target Vulnerable,
  Paper Phrog, and player Weak are combined with the same final-truncation
  shape as the divergence oracle before deciding whether an attacker is
  killable.
- 2026-06-07: `FastCombatSimulator` now models Bandage Up healing, including
  the upgraded 6 HP amount and max-HP cap. This syncs the confirmed colorless
  heal behavior from sim divergence into beam/fast scoring so survival
  estimates can value the card.
- 2026-06-07: `FastCombatSimulator` enemy lookahead now models Shelled
  Parasite attack-buff self-heal from unblocked player HP loss. The healed HP
  is carried into later lookahead steps so HP-dependent future move prediction
  does not overstate follow-up damage after Suck.
- 2026-06-07: `SimulationState.turn_block()` now includes Orichalcum's 6 block
  when current block plus end-turn block is still zero. This syncs the
  confirmed end-turn relic block into beam/fast scoring surfaces that subtract
  `turn_block()` from predicted incoming damage.
- 2026-06-07: `FastCombatSimulator` end-turn projection now models current-hand
  Burn/Burn+ as blockable status damage and Decay as block-bypassing HP loss.
  Pending status costs are carried in the beam state key and removed when the
  status card is played or exhausted, keeping survival scoring aligned with the
  divergence oracle's end-turn status semantics.
- 2026-06-07: `FastCombatSimulator` current-attacker reflection scoring now
  treats Flame Barrier as player thorns and caps reflected damage by monster HP
  only, not HP plus block. This syncs the confirmed Thorns/Flame Barrier
  semantics that reflection bypasses monster block and can score the temporary
  reflection from a simulated Flame Barrier play.
- 2026-06-07: `HeuristicCombatPlanner` now models Smoke Bomb as combat escape
  in potion beam scoring without awarding kill or all-lethal rewards. Escaped
  states stop further beam expansion and receive survival value based on
  avoided incoming HP loss, syncing the observed escape-potion divergence into
  live potion decision estimates.

## Backlog

- Add a streaming `sim_divergence_trace_clean.jsonl` analyzer so large clean
  traces can be summarized by cutoff without PowerShell full-file JSON parsing.
- Keep the coverage matrix current as new divergence mechanics are confirmed.
- Audit high-impact confirmed mechanics across live estimators:
  - Watch for newly discovered Whirlwind estimator surfaces beyond the synced
    divergence, simulator, timing, lethal, fallback damage, and priority paths.
  - Paper Phrog, Weak/Vulnerable, Strength, and upgraded attack stats across
    any still-unaudited estimator surfaces.
  - Other dynamic base damage beyond the Mind Blast combat estimator and RL
    survival surfaces already covered above.
  - Havoc random-target boundaries and any remaining non-Juggernaut
    Feel No Pain block value outside the simulator, lethal, Ironclad fallback,
    timing fallback, RL survival, and RL shared block-candidate surfaces already
    covered above.
  - Monster lifecycle boundaries such as Slime split and Darkling revive.
  - Combat-exit boundaries beyond the Looter/Mugger reward sync.
