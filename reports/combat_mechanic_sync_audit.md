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
- 2026-06-07: `FastCombatSimulator` now applies deterministic Havoc top-card
  effects when the draw-pile top card is visible. Known top attacks resolve for
  single-monster or AOE/random-target cases, known top skills and powers reuse
  the existing live simulators, and the top card contributes one exhaust event
  for exhaust synergies such as Feel No Pain. Later simulated Havoc plays skip
  top cards already consumed by the current simulated line.
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
- 2026-06-07: `CombatRLAgent` Slime Boss split survival retarget guard now
  evaluates attack damage against each candidate target. Target Vulnerable,
  Paper Phrog, and player Weak are combined with the same final-truncation
  shape as the divergence oracle before deciding whether an attacker is
  killable.
- 2026-06-07: `FastCombatSimulator` now models Bandage Up healing, including
  the upgraded 6 HP amount and max-HP cap. This syncs the confirmed colorless
  heal behavior from sim divergence into beam/fast scoring so survival
  estimates can value the card.

## Backlog

- Add a streaming `sim_divergence_trace_clean.jsonl` analyzer so large clean
  traces can be summarized by cutoff without PowerShell full-file JSON parsing.
- Expand this report into a compact coverage matrix from divergence rounds
  105-118: rows as mechanics, columns as estimator surfaces.
- Audit high-impact confirmed mechanics across live estimators:
  - Watch for newly discovered Whirlwind estimator surfaces beyond the synced
    divergence, simulator, timing, lethal, fallback damage, and priority paths.
  - Paper Phrog, Weak/Vulnerable, Strength, and upgraded attack stats.
  - Other dynamic base damage beyond the Mind Blast combat estimator and RL
    survival surfaces already covered above.
  - Havoc top-card effects, random-target boundaries, and Feel No Pain block.
  - End-turn statuses such as Burn and Decay.
  - Monster lifecycle boundaries such as Slime split and Darkling revive.
  - Combat-exit boundaries such as Smoke Bomb and Looter escape.
