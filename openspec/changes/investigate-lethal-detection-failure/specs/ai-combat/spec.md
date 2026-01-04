# ai-combat Specification Delta

## MODIFIED Requirements

### Requirement: Lethal Detection Before Combat Planning
The OptimizedAgent SHALL detect when all monsters can be killed this turn before executing beam search. Lethal detection SHALL:

1. Calculate total affordable damage from playable cards (respecting energy constraints)
2. Calculate total monster HP (including block)
3. Apply a 10% margin requirement: `affordable_damage >= total_monster_hp * 1.1`
4. Validate targeting feasibility (single-target vs AOE constraints)
5. Apply HP safety threshold: only go for lethal when player HP > 30 OR HP percentage > 30%

When lethal is detected, the agent SHALL construct a lethal action sequence and execute it immediately, skipping beam search.

#### Scenario: Exact lethal detection
- **GIVEN** player has 2 energy, hand contains [Strike (6 dmg), Strike (6 dmg)]
- **AND** single monster with 12 HP and 0 block
- **WHEN** checking for lethal
- **THEN** the detector SHALL return True (12 damage >= 12 HP × 1.0, exceeds threshold after margin calculation)

#### Scenario: Lethal with energy constraint
- **GIVEN** player has 2 energy, hand contains [Heavy Blade (14 dmg, 2 cost), Strike (6 dmg, 1 cost)]
- **AND** single monster with 14 HP and 0 block
- **WHEN** checking for lethal
- **THEN** the detector SHALL return True (can afford Heavy Blade, 14 damage >= 14 HP × 1.1 threshold)

#### Scenario: Lethal blocked by insufficient energy
- **GIVEN** player has 2 energy, hand contains [Heavy Blade (14 dmg, 2 cost), Heavy Blade (14 dmg, 2 cost)]
- **AND** single monster with 25 HP and 0 block
- **WHEN** checking for lethal
- **THEN** the detector SHALL return False (cannot afford both Heavy Blades with only 2 energy)

#### Scenario: Multi-monster lethal requires AOE
- **GIVEN** player has 2 energy, hand contains [Cleave (8 dmg AOE, 1 cost), Strike (6 dmg, 1 cost)]
- **AND** two monsters with 8 HP each
- **WHEN** checking for lethal
- **THEN** the detector SHALL return True (Cleave kills both, 8 damage to each >= 8 HP threshold)

#### Scenario: Low HP safety threshold
- **GIVEN** player at 15 HP (30% max HP = 15, so at threshold boundary)
- **AND** lethal is available but risky
- **WHEN** checking for lethal
- **THEN** the detector SHALL return True (HP >= 30 AND HP >= 30% threshold)

#### Scenario: Very low HP blocks risky lethal
- **GIVEN** player at 10 HP (below 30 HP threshold)
- **AND** lethal is available but monster has Thorns (will deal damage)
- **WHEN** checking for lethal
- **THEN** the detector SHALL return False (HP too low for risky lethal)

---

### Requirement: Lethal Sequence Construction
When lethal is detected, the agent SHALL construct a valid action sequence that kills all monsters. Sequence construction SHALL:

1. Use beam search with AGGRESSIVE combat mode (maximize damage)
2. Respect energy constraints (total card cost <= available energy)
3. Respect targeting constraints (single-target vs AOE cards)
4. Validate the sequence by simulating it to confirm all monsters die
5. Return the validated sequence or empty list if construction fails

#### Scenario: Simple lethal sequence
- **GIVEN** hand contains [Strike (6 dmg), Strike (6 dmg), Bash (8 dmg)]
- **AND** single monster with 12 HP
- **AND** player has 2 energy
- **WHEN** constructing lethal sequence
- **THEN** the agent SHALL return [PlayCardAction(Strike), PlayCardAction(Strike)]

#### Scenario: AOE lethal sequence
- **GIVEN** hand contains [Cleave (8 dmg AOE), Strike (6 dmg)]
- **AND** two monsters with 8 HP each
- **AND** player has 2 energy
- **WHEN** constructing lethal sequence
- **THEN** the agent SHALL return [PlayCardAction(Cleave)]

#### Scenario: Energy-constrained lethal
- **GIVEN** hand contains [Heavy Blade (14 dmg, 2 cost), Strike (6 dmg, 1 cost)]
- **AND** single monster with 14 HP
- **AND** player has 2 energy
- **WHEN** constructing lethal sequence
- **THEN** the agent SHALL return [PlayCardAction(Heavy Blade)] (only one card affordable)

#### Scenario: Vulnerable synergy lethal
- **GIVEN** hand contains [Bash (8 dmg, applies Vulnerable), Strike (6 dmg)]
- **AND** single monster with 18 HP
- **AND** player has 2 energy
- **WHEN** constructing lethal sequence
- **THEN** the agent SHALL return [PlayCardAction(Bash), PlayCardAction(Strike)] (Bash makes Strike deal 9 damage, total 17 + 9 = 26 damage with Vulnerable)

#### Scenario: Construction failure fallback
- **GIVEN** lethal detected by can_kill_all()
- **BUT** beam search fails to construct valid sequence (energy/targeting constraint violation)
- **WHEN** constructing lethal sequence
- **THEN** the agent SHALL return empty list and fall back to standard beam search

---

### Requirement: Beam Search Lethal Prioritization
When lethal is not detected by the pre-check (false negative or truly unavailable), the beam search scoring function SHALL still strongly prioritize sequences that kill all monsters. The scoring function SHALL:

1. Add an exponential ALL_LETHAL_BONUS of 500 points when all monsters are killed
2. Keep the existing KILL_BONUS of 100 points per monster killed
3. Reduce BLOCK_WEIGHT by 70% when lethal damage is available (penalize defense when kills are possible)
4. Maintain damage priority (DAMAGE_WEIGHT = 2.0) to favor aggressive sequences

#### Scenario: All-kill bonus outscores defense
- **GIVEN** two sequences: Sequence A kills all 3 monsters (deals 30 damage), Sequence B gains 12 block and deals 10 damage
- **WHEN** scoring both sequences
- **THEN** Sequence A SHALL score higher: 500 (all-kill) + 300 (3 kills × 100) + 60 (30 dmg × 2.0) = 860 > Sequence B: 18 (12 block × 1.5) + 20 (10 dmg × 2.0) = 38

#### Scenario: Partial kill vs full defense
- **GIVEN** two sequences: Sequence A kills 2 of 3 monsters (deals 20 damage), Sequence B gains 8 block and kills 0 monsters
- **WHEN** scoring both sequences
- **THEN** Sequence A SHALL score higher: 200 (2 kills × 100) + 40 (20 dmg × 2.0) = 240 > Sequence B: 12 (8 block × 1.5) + 0 = 12

#### Scenario: Block penalty when lethal available
- **GIVEN** lethal damage is available (can kill all monsters)
- **AND** two sequences: Sequence A kills all (0 block), Sequence B gains 15 block and kills 0
- **WHEN** scoring both sequences
- **THEN** block cards in Sequence B SHALL be penalized: score += 15 × 1.5 × 0.3 = 6.75 (70% reduction)

#### Scenario: Near-lethal still prioritized over defense
- **GIVEN** two sequences: Sequence A deals 25 damage (kills 2 monsters, leaves 1 at 2 HP), Sequence B gains 10 block and deals 5 damage
- **WHEN** scoring both sequences
- **THEN** Sequence A SHALL score higher: 200 (2 kills × 100) + 50 (25 dmg × 2.0) = 250 > Sequence B: 15 (10 block × 1.5) + 10 (5 dmg × 2.0) = 25

---

## ADDED Requirements

### Requirement: SimpleAgent Lethal Detection
The SimpleAgent (used for Silent and Defect) SHALL implement basic lethal detection before card selection. When lethal damage is available, SimpleAgent SHALL:

1. Calculate total damage from all attack cards in hand
2. Add player Strength to attack damage
3. Check if total damage >= total monster HP + block (no margin required for SimpleAgent)
4. If lethal detected, play attack cards in priority order (highest damage first)
5. Skip defensive cards when lethal is available

#### Scenario: SimpleAgent basic lethal detection
- **GIVEN** Silent with hand containing [Strike (6 dmg), Strike (6 dmg), Defend (5 block)]
- **AND** single monster with 12 HP
- **AND** 2 energy available
- **WHEN** selecting card to play
- **THEN** SimpleAgent SHALL play Strike (skip Defend)

#### Scenario: SimpleAgent multi-card lethal
- **GIVEN** Silent with hand containing [Strike (6 dmg), Strike (6 dmg), Slash (8 dmg)]
- **AND** two monsters with 8 HP each
- **AND** 3 energy available
- **WHEN** selecting cards to play
- **THEN** SimpleAgent SHALL play all three attack cards (skip any defensive cards)

#### Scenario: SimpleAgent no lethal, play defense
- **GIVEN** Silent with hand containing [Defend (5 block), Strike (6 dmg)]
- **AND** monster with 20 HP (not killable)
- **AND** monster intends to attack for 12 damage
- **WHEN** selecting card to play
- **THEN** SimpleAgent SHALL play Defend (normal priority logic applies)

---

### Requirement: Lethal Detection Logging
The combat planner SHALL log all lethal detection decisions for debugging and validation. Logs SHALL include:

1. Lethal check result (True/False) with reasoning
2. Total affordable damage calculated
3. Total monster HP calculated
4. Energy available vs energy required
5. HP safety threshold check result
6. Lethal sequence constructed (if applicable)
7. Sequence validation result (if applicable)

#### Scenario: Lethal detected log
- **GIVEN** lethal damage is available
- **WHEN** checking for lethal
- **THEN** the agent SHALL log "[LETHAL_DETECTION] Lethal detected! affordable_damage=24, total_monster_hp=20, margin_ok=True, energy_ok=True, hp_safe=True"

#### Scenario: Lethal not detected log
- **GIVEN** lethal damage is NOT available
- **WHEN** checking for lethal
- **THEN** the agent SHALL log "[LETHAL_DETECTION] No lethal. affordable_damage=15, total_monster_hp=20, margin_ok=False, reason=Insufficient damage (15 < 22 with 10% margin)"

#### Scenario: Sequence construction log
- **GIVEN** lethal detected and sequence constructed
- **WHEN** building lethal sequence
- **THEN** the agent SHALL log "[LETHAL_SEQUENCE] Constructed sequence with 3 cards: [Strike, Strike, Bash], validated=True"

#### Scenario: Construction failure log
- **GIVEN** lethal detected but sequence construction failed
- **WHEN** building lethal sequence
- **THEN** the agent SHALL log "[LETHAL_SEQUENCE] Construction failed: beam search returned empty sequence, falling back to standard planning"
