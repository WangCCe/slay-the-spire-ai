# ai-combat Specification

## Purpose
TBD - created by archiving change optimize-beam-search-combat. Update Purpose after archive.
## Requirements
### Requirement: Accurate Debuff Simulation
The beam search combat simulator SHALL apply debuff multipliers according to Slay the Spire game mechanics:
- **Vulnerable**: Fixed 1.5x damage multiplier when present (>0 stacks), applies only to attack damage
- **Weak**: Fixed 0.75x damage multiplier when present (>0 stacks), applies only to attack damage
- **Frail**: Fixed 0.75x block gain multiplier when present (>0 stacks), applies only to gaining block

Debuff stacks SHALL be treated as duration counters, not intensity scalars. The multiplier SHALL be binary (present/absent) regardless of stack count.

#### Scenario: Vulnerable damage calculation
- **GIVEN** a monster with 2 vulnerable stacks
- **WHEN** an attack card deals 10 base damage
- **THEN** the simulator SHALL calculate 15 damage (10 × 1.5), NOT 20 damage (10 × 2.0)

#### Scenario: Weak damage reduction
- **GIVEN** a monster with 3 weak stacks
- **WHEN** the monster attacks for 12 base damage
- **THEN** the simulator SHALL calculate 9 damage (12 × 0.75), NOT 3 damage (12 × 0.25)

#### Scenario: Frail block reduction
- **GIVEN** the player has 1 frail stack
- **WHEN** playing a skill that grants 8 block
- **THEN** the simulator SHALL grant 6 block (8 × 0.75)

#### Scenario: Zero debuff stacks
- **GIVEN** a monster with 0 vulnerable stacks
- **WHEN** an attack card deals 10 base damage
- **THEN** the simulator SHALL calculate 10 damage (no multiplier applied)

---

### Requirement: Survival-First Scoring
The combat evaluation function SHALL prioritize minimizing HP loss over maximizing damage output. The scorer SHALL:

1. Estimate expected incoming damage for the next turn based on monster intents
2. Calculate net HP loss after accounting for player block
3. Apply a heavy penalty (W_DEATHRISK = 5.0 to 12.0) to sequences with HP loss
4. Assign negative infinite score to any sequence that results in player death
5. Apply an additional "danger threshold" penalty when player HP falls below act-dependent thresholds (Act 1: 20 HP, Act 2: 25 HP, Act 3: 30 HP)

#### Scenario: Lethal damage avoidance
- **GIVEN** two action sequences where Sequence A deals 30 damage but leaves player at 5 HP, and Sequence B deals 20 damage but leaves player at 15 HP
- **WHEN** the expected incoming damage is 15
- **THEN** Sequence B SHALL receive a higher score (survival priority over damage)

#### Scenario: Death penalty
- **GIVEN** an action sequence that results in expected HP loss >= player current HP
- **WHEN** evaluating the sequence
- **THEN** the score SHALL be set to negative infinity, making it the lowest-ranked sequence

#### Scenario: Danger threshold penalty
- **GIVEN** player at 18 HP in Act 2 (danger threshold = 25)
- **WHEN** a sequence results in expected HP loss of 8 HP (leaving player at 10 HP)
- **THEN** the sequence SHALL receive an additional penalty score of -50 or more

#### Scenario: Block mitigation
- **GIVEN** expected incoming damage of 20 and player block of 12
- **WHEN** calculating HP loss
- **THEN** the net HP loss SHALL be 8 (20 - 12), with survival penalty applied to 8 HP loss

---

### Requirement: Replan Triggers
The OptimizedAgent SHALL detect when a cached action sequence becomes invalid and trigger re-planning. Replanning SHALL occur when:

1. Hand cards change unexpectedly (card draws, card generation, card exhaustion)
2. Available energy changes (Bloodletting, Energy potions, relics)
3. Monster set changes (monster deaths, new monsters spawned)
4. Monster intents change (e.g., after Stunned status expires)
5. Random effects occur (random targeting, deck shuffling, card randomization)

The agent SHALL maintain a TurnPlanSignature capturing the initial game state and compare it against the current state before executing each cached action.

#### Scenario: Card draw triggers replan
- **GIVEN** a cached action sequence [Bash, Strike, Defend]
- **WHEN** playing Battle Trance draws 3 cards before executing the cached Bash
- **THEN** the agent SHALL discard the cached sequence and re-run beam search with the new hand

#### Scenario: Monster death triggers replan
- **GIVEN** a cached action sequence targeting Monster A (lowest HP)
- **WHEN** Monster A dies from a card effect before executing the next cached action
- **THEN** the agent SHALL invalidate the cache and re-plan targeting remaining monsters

#### Scenario: Energy change triggers replan
- **GIVEN** a cached action sequence spending 3 energy
- **WHEN** the player plays Bloodletting and gains 2 energy mid-turn
- **THEN** the agent SHALL detect the energy mismatch and re-plan to utilize the extra energy

#### Scenario: Stable state preserves cache
- **GIVEN** a cached action sequence with valid targets and sufficient energy
- **WHEN** no hand/energy/monster changes occur before executing the next action
- **THEN** the agent SHALL continue executing the cached sequence without re-planning

---

### Requirement: Transposition Table
The beam search algorithm SHALL maintain a transposition table that deduplicates identical game states reached via different action sequences. The transposition table SHALL:

1. Generate a state key including: player HP/block/energy/strength, monster HP/block/debuffs/intents, hand card multiset
2. Store the highest-scoring path to each unique state
3. Merge duplicate states by keeping only the best-scoring path
4. Enable wider effective beam search without increasing computational cost

The state key SHALL include all game-relevant fields; two states SHALL be considered identical only if all fields match exactly.

#### Scenario: Commuting cards merged
- **GIVEN** two action sequences: [Iron Wave + Strike] and [Strike + Iron Wave]
- **WHEN** both sequences result in identical final state (same HP, block, monsters, hand)
- **THEN** the transposition table SHALL store only one entry with the higher-scoring path

#### Scenario: Differentiated states preserved
- **GIVEN** two action sequences that differ in final player block (Sequence A: 12 block, Sequence B: 10 block)
- **WHEN** generating state keys
- **THEN** the keys SHALL differ, and both sequences SHALL be retained in the beam

#### Scenario: Monster state distinction
- **GIVEN** two game states where Monster A has 10 HP in State 1 and 8 HP in State 2 (all other fields identical)
- **WHEN** generating state keys
- **THEN** the keys SHALL differ, treating the states as distinct

#### Scenario: Beam width optimization
- **GIVEN** beam_width = 15 and 100 candidate sequences after expansion
- **WHEN** 40 sequences map to 10 unique states via transposition
- **THEN** the beam SHALL retain the 15 unique highest-scoring states (effectively widening from 100→15 to 100→10→15)

---

### Requirement: Two-Stage Action Expansion
The beam search algorithm SHALL use a two-stage action expansion strategy to efficiently prune low-value actions. Stage 1 (FastScore) SHALL:

1. Compute a lightweight score for each playable action without full simulation
2. Prioritize: zero-cost cards (+20), attacks when monsters alive (+10), block at low HP (+15), base damage estimate (+2 per damage)
3. Sort actions by FastScore in descending order
4. Select only the top M actions for Stage 2, where M decreases with search depth (Progressive Widening)

Stage 2 (FullSim) SHALL run full simulation and evaluation only on the top M actions from Stage 1.

Progressive widening parameters: Depth 0→M=12, Depth 1→M=10, Depth 2→M=7, Depth 3→M=5, Depth 4→M=4.

#### Scenario: Action pruning at depth 0
- **GIVEN** 8 playable cards at depth 0
- **WHEN** running FastScore evaluation
- **THEN** only the top 12 cards (or all if fewer than 12) SHALL proceed to FullSim simulation

#### Scenario: Progressive narrowing
- **GIVEN** 10 playable cards at depth 3
- **WHEN** running FastScore evaluation
- **THEN** only the top 5 cards SHALL proceed to FullSim simulation (M=5 at depth 3)

#### Scenario: Zero-cost prioritization
- **GIVEN** actions: [Clothesline (2 cost, 14 damage), Apex (0 cost, 5 damage), Bash (1 cost, 8 damage)]
- **WHEN** computing FastScore
- **THEN** Apex SHALL receive the highest FastScore due to zero-cost bonus (+20), prioritizing it for simulation

#### Scenario: Block-at-low-HP prioritization
- **GIVEN** player at 18 HP with actions: [Iron Wave (5 block, 5 damage), Heavy Blade (14 damage)]
- **WHEN** computing FastScore
- **THEN** Iron Wave SHALL receive a +15 bonus for block at low HP, potentially outranking Heavy Blade

---

### Requirement: Threat-Based Targeting
The combat planner SHALL select targets for attack/debuff cards based on threat level rather than lowest HP. Threat calculation SHALL include:

1. Expected damage next turn (from monster intent)
2. Debuff threat (Weak/Vulnerable application: +10)
3. Scaling threat (buffs/growth over time: +15)
4. AOE threat (buffs other monsters: +8)

Target selection priority SHALL be:
1. Killable targets (can be defeated this turn) sorted by threat (highest first)
2. If no killable targets, highest threat target overall

#### Scenario: Threat-prioritization over HP
- **GIVEN** Monster A (15 HP, intends 18 damage attack) and Monster B (8 HP, intends 6 damage attack)
- **WHEN** playing a single-target attack for 8 damage
- **THEN** the planner SHALL target Monster A (threat=18) despite Monster B having lower HP

#### Scenario: Kill priority
- **GIVEN** Monster A (8 HP, threat=12) and Monster B (15 HP, threat=25), playing an attack for 10 damage
- **WHEN** selecting a target
- **THEN** the planner SHALL target Monster A (killable, reduces incoming damage by 12)

#### Scenario: Debuff threat consideration
- **GIVEN** Monster A (20 HP, intends to apply Vulnerable) and Monster B (20 HP, intends 12 damage attack)
- **WHEN** playing Bash (applies Vulnerable)
- **THEN** the planner SHALL target Monster B (high damage threat) to maximize the Vulnerable benefit, NOT Monster A

#### Scenario: Elite threat prioritization
- **GIVEN** Monster A (Gremlin Nob, 40 HP, intends 10 damage, scaling threat) and Monster B (Slimed, 12 HP, intends 8 damage)
- **WHEN** playing an attack that can kill either
- **THEN** the planner SHALL prioritize killing Monster A due to scaling threat (+15 bonus)

---

### Requirement: Engine Event Tracking
The simulation state SHALL track engine-related events during beam search to implicitly evaluate card synergies. Tracked events SHALL include:

1. `cards_exhausted`: Count of cards moved to exhaust pile
2. `cards_drawn`: Count of cards drawn from draw pile
3. `skills_played`: Count of skill cards played
4. `attacks_played`: Count of attack cards played
5. `damage_instances`: Count of individual damage triggers (for multi-hit effects)
6. `energy_gained`: Energy generated this turn (outside initial pool)
7. `energy_saved`: Energy reduced/avoided (e.g., Corruption free costs)

The scoring function SHALL incorporate these event counts using pre-tuned synergy values (e.g., exhaust_events × FeelNoPain_value, cards_drawn × draw_value).

#### Scenario: Feel No Pain exhaust synergy
- **GIVEN** Feel No Pain power active (value = 3 block per exhaust)
- **WHEN** simulating a sequence that exhausts 3 cards
- **THEN** the score SHALL include a bonus of 9 (3 exhausts × 3) for implicit block value

#### Scenario: Dark Embrace draw synergy
- **GIVEN** Dark Embrace power active (value = 2 per exhaust + draw)
- **WHEN** simulating Second Wind (exhaust all attacks in hand)
- **THEN** the score SHALL add (cards_exhausted × 2) to account for card advantage generated

#### Scenario: Corruption energy-free synergy
- **GIVEN** Corruption power active (skills cost 0)
- **WHEN** playing 3 skills that would cost 5 energy total
- **THEN** the score SHALL include an energy_saved bonus of 5 × energy_value (e.g., 5 × 4 = 20)

#### Scenario: Battle Trance draw value
- **GIVEN** no draw-related powers
- **WHEN** simulating Battle Trance (draw 3)
- **THEN** the score SHALL add cards_drawn × draw_value (e.g., 3 × 3 = 9) to account for card advantage

---

### Requirement: Beam Search Performance
The combat planner SHALL complete beam search and return an action sequence within approximately 100ms per turn to avoid Communication Mod timeouts. The planner SHALL adapt search parameters based on game complexity:

- Base beam_width: 12-15 (Act 1), 18-25 (Act 2/3)
- Max depth: 3-5 cards (adaptive based on energy and hand size)
- With transposition table enabled, effective beam width SHALL increase without computational cost

If beam search exceeds 80ms, the planner SHALL interrupt and return the best sequence found so far (fallback to cached plan if available).

#### Scenario: Timeout protection
- **GIVEN** a complex combat with 12 playable cards and 4 monsters
- **WHEN** beam search reaches 80ms elapsed time
- **THEN** the planner SHALL stop expansion and return the current best sequence

#### Scenario: Adaptive depth
- **GIVEN** 3 energy and 2 playable cards
- **WHEN** setting max_depth
- **THEN** depth SHALL be set to 2 (equal to playable cards), not 5

#### Scenario: Act 3 increased beam
- **GIVEN** combat in Act 3 with transposition table active
- **WHEN** initializing beam search
- **THEN** beam_width SHALL be set to 25 (higher than Act 1's 15) to handle increased complexity

#### Scenario: Simple case fast path
- **GIVEN** 1 or 2 playable cards in hand
- **WHEN** planning turn
- **THEN** the planner SHALL skip beam search and use simple card ranking (completes in <10ms)

