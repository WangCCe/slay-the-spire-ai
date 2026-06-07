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

## Confirmed Sync Work

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
- Expand this report into a compact coverage matrix from divergence rounds
  105-118: rows as mechanics, columns as estimator surfaces.
- Audit high-impact confirmed mechanics across live estimators:
  - Watch for newly discovered Whirlwind estimator surfaces beyond the synced
    divergence, simulator, timing, lethal, fallback damage, and priority paths.
  - Paper Phrog, Weak/Vulnerable, Strength, and upgraded attack stats across
    any still-unaudited estimator surfaces.
  - Other dynamic base damage beyond the Mind Blast combat estimator and RL
    survival surfaces already covered above.
  - Havoc random-target boundaries and any remaining non-Juggernaut
    Feel No Pain block value outside the simulator, lethal, RL survival, and
    RL shared block-candidate surfaces already covered above.
  - Monster lifecycle boundaries such as Slime split and Darkling revive.
  - Combat-exit boundaries beyond the Looter/Mugger reward sync.
