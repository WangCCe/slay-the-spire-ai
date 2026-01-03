# Capability: AI Combat Decision System

## MODIFIED Requirements

### Requirement: Combat planning uses lookahead search

The AI MUST use beam search to plan optimal card sequences rather than greedy single-card selection.

#### Scenario: Beam search finds lethal line

**Given** the player has 3 energy and cards: [Bash (1), Iron Wave (1), Strike (1), Attack (0)]
**And** there are 2 monsters with 12 HP and 8 HP
**When** the AI plans its turn
**Then** it should simulate multiple card sequences
**And** it should find the sequence that deals maximum damage while surviving
**And** it should select cards in optimal order (e.g., Bash on high HP monster, then attacks)

#### Scenario: Combat ending detection prevents over-defending

**Given** the player has lethal damage available this turn
**When** the AI plans its turn
**Then** it should detect that lethal is possible
**And** it should play all-out offense (ignore defensive cards)
**And** it should kill all monsters this turn
**And** it should not waste block when unnecessary

#### Scenario: Adaptive beam search parameters

**Given** the combat complexity varies (number of cards × monsters)
**When** the AI plans its turn with 1-3 playable cards and 1-2 monsters
**Then** it should use beam_width=8, max_depth=3
**When** the AI plans its turn with 4-6 playable cards and 2-3 monsters
**Then** it should use beam_width=12, max_depth=4
**When** the AI plans its turn with 7+ playable cards or 4+ monsters
**Then** it should use beam_width=15, max_depth=5

### Requirement: Combat simulation accurately models game state

The beam search simulation MUST accurately predict the outcome of card plays.

#### Scenario: Damage calculation with Strength

**Given** the player has 3 Strength
**And** the player plays a Strike (6 damage)
**When** the damage is calculated
**Then** the total damage should be 9 (6 base + 3 from Strength)

#### Scenario: Vulnerable debuff increases damage

**Given** a monster has 2 Vulnerable stacks
**And** the player plays an attack that deals 10 damage
**When** the damage is calculated
**Then** the total damage should be 15 (10 × 1.5 for Vulnerable)

#### Scenario: Monster block reduces damage

**Given** a monster has 5 block
**And** the player deals 12 damage
**When** the damage is applied
**Then** the monster should lose 7 HP (12 damage - 5 block)
**And** the monster's block should be reduced to 0

#### Scenario: AOE damage distribution

**Given** there are 3 monsters with [10, 15, 20] HP
**And** the player plays Cleave dealing 8 damage to all enemies
**When** the damage is applied
**Then** the monsters should have [2, 7, 12] HP remaining

#### Scenario: Energy tracking prevents over-spending

**Given** the player has 3 energy
**And** the player has played cards costing 2 energy total
**When** the AI considers playing another card
**Then** it should only consider cards with cost <= 1
**And** it should not consider cards with cost > remaining energy

### Requirement: Smart targeting optimizes card effectiveness

The AI MUST target cards to maximize their impact based on card type and game state.

#### Scenario: Bash targets high HP monsters

**Given** there are 2 monsters with 30 HP and 15 HP
**And** the AI plays Bash (8 damage + 3 Vulnerable)
**When** the target is selected
**Then** Bash should target the monster with 30 HP
**And** the lower HP monster should not receive the Vulnerable debuff

#### Scenario: Attack cards target low HP monsters

**Given** there are 2 monsters with 8 HP and 20 HP
**And** both will die to 8 damage
**And** the AI plays a single-target attack for 8 damage
**When** the target is selected
**Then** the attack should target the monster with 8 HP
**And** the monster should be killed

#### Scenario: AOE cards used with multiple monsters

**Given** there are 3 monsters alive
**And** the AI has both Cleave and single-target attacks
**When** the AI plans its turn
**Then** it should prioritize playing Cleave
**And** it should evaluate the AOE damage value (3 monsters × damage)

### Requirement: HP-based risk assessment adjusts playstyle

The AI MUST adjust its decision-making based on current HP percentage.

#### Scenario: Aggressive play when HP is high

**Given** the player has 90% HP (75/80)
**And** lethal damage is available
**When** the AI plans its turn
**Then** it should prioritize dealing maximum damage
**And** it should play risky if it leads to faster kills

#### Scenario: Balanced play when HP is medium

**Given** the player has 60% HP (48/80)
**And** incoming damage is 15 this turn
**When** the AI plans its turn
**Then** it should ensure it has enough block to survive
**And** it should deal damage with remaining energy
**And** it should prioritize efficient cards (good stats per energy)

#### Scenario: Conservative play when HP is low

**Given** the player has 35% HP (28/80)
**And** incoming damage is 12 this turn
**When** the AI plans its turn
**Then** it should prioritize gaining block >= incoming damage
**And** it should avoid risky plays that might reduce HP further
**And** it should consider using potions for survival

#### Scenario: Desperate play when HP is critical

**Given** the player has 15% HP (12/80)
**And** any hit could be lethal
**When** the AI plans its turn
**Then** it should maximize block at all costs
**And** it should use potions immediately
**And** it should play defensively even if it means passing turn

### Requirement: Elite encounter awareness

The AI MUST recognize elite fights and adjust strategy accordingly.

#### Scenario: Detect elite fights

**Given** the room_type indicates an elite fight
**When** the AI creates a decision context
**Then** it should mark the fight as elite
**And** it should adjust playstyle (more conservative)

#### Scenario: Save potions for elite key turns

**Given** the AI is in an elite fight
**And** the AI has an attack potion
**And** the elite is at high HP with a big attack incoming
**When** the AI plans its turn
**Then** it should consider using the attack potion this turn
**And** it should not hoard the potion when it could turn the tide

#### Scenario: Play conservatively against elite hard hitters

**Given** the AI is fighting an elite with high damage attacks (e.g., Gremlin Nob)
**And** the elite intends to deal 25 damage
**When** the AI plans its turn
**Then** it should ensure it can survive the elite's next attack
**And** it should prioritize block cards
**And** it should consider using defensive potions

## ADDED Requirements

### Requirement: OptimizedAgent is default for Ironclad

When the AI starts a game as Ironclad, it MUST use OptimizedAgent instead of SimpleAgent.

#### Scenario: Automatic OptimizedAgent selection

**Given** the player class is set to IRONCLAD
**And** no explicit agent preference is specified
**When** the agent is created
**Then** OptimizedAgent should be instantiated
**And** it should use beam search combat planning
**And** it should use synergy-based card evaluation

#### Scenario: Fallback to SimpleAgent on import error

**Given** the OptimizedAgent components fail to import
**And** the player class is IRONCLAD
**When** the agent is created
**Then** SimpleAgent should be used as fallback
**And** a warning should be logged
**And** the game should continue without crashing

### Requirement: Card reward selection considers deck composition

The AI MUST evaluate card rewards based on what's already in the deck, not just static priorities.

#### Scenario: Avoid redundant effects

**Given** the deck already has 3 Bash cards
**And** the MAX_COPIES for Bash is 1
**And** a card reward offers another Bash
**When** the AI selects a card reward
**Then** it should skip the Bash
**And** it should choose a different card or skip

#### Scenario: Prioritize synergistic cards

**Given** the deck has 2 Demon Form and 1 Inflame (Strength theme)
**And** a card reward offers Limit Break and a random attack
**When** the AI selects a card reward
**Then** it should prioritize Limit Break (synergizes with Strength)
**And** it should deprioritize the random attack (no synergy)

#### Scenario: Detect deck archetype and adapt

**Given** the deck has [Demon Form, 2x Inflame, 2x Flex] (Strength archetype)
**And** a card reward offers [Bludgeon, Metallicize, Pommel Strike]
**When** the AI selects a card reward
**Then** it should detect the Strength archetype
**And** it should prioritize Bludgeon (high damage, benefits from Strength)
**And** it should deprioritize Metallicize (no synergy)

### Requirement: Act 1 priorities prioritize consistency over scaling

Card priorities for Ironclad in Act 1 MUST favor consistent, immediate value over late-game scaling.

#### Scenario: Early game priority for efficient cards

**Given** it is Act 1 floor 1-5
**And** a card reward offers [Demon Form, Iron Wave, Shrug It Off]
**When** the AI selects a card reward
**Then** it should prioritize Iron Wave or Shrug It Off (immediate value)
**And** it should deprioritize Demon Form (too slow for early game)

#### Scenario: Bash priority for early damage scaling

**Given** it is Act 1
**And** the deck has 0 Bash cards
**And** a card reward offers Bash
**When** the AI selects a card reward
**Then** it should prioritize Bash highly (Vulnerable is crucial early)
**And** it should accept Bash even over other decent cards

#### Scenario: Late Act 1 opens up scaling options

**Given** it is Act 1 floor 10+
**And** the deck has a solid foundation (block, attacks)
**And** a card reward offers Demon Form
**When** the AI selects a card reward
**Then** it should consider Demon Form more favorably (deck can support it)
**And** it should still prefer immediate impact cards if deck is weak

### Requirement: Improved Act 1 priority list order

The Ironclad card priority list MUST be reordered to optimize Act 1 performance.

#### Scenario: High priority cards for Act 1

**Given** the IroncladPriority.CARD_PRIORITY_LIST is initialized
**When** cards are prioritized for Act 1
**Then** the following cards should be in the top 20 priority:
  - Bash (Vulnerable is essential)
  - Iron Wave (efficient block + attack)
  - Shrug It Off (block + draw)
  - Pommel Strike (cheap, removes cards)
  - Headbutt (card advantage)
  - Perfected Strike (efficient damage)
  - Battle Trance (card draw)
  - Anger (adds damage, costs 1)

#### Scenario: Low priority cards for Act 1

**Given** the IroncladPriority.CARD_PRIORITY_LIST is initialized
**When** cards are prioritized for Act 1
**Then** the following cards should be lower priority (bottom 30%):
  - Limit Break (requires Strength investment)
  - Corruption (requires exhaust synergies)
  - Demon Form (too slow without setup)
  - Feel No Pain (requires Corruption synergy)
  - Rupture (specific archetype)
  - Combust (specific archetype)

### Requirement: MAX_COPIES limits prevent over-picking

The AI MUST limit the number of copies of each card it adds to the deck.

#### Scenario: Limit low-impact strikes and defends

**Given** the MAX_COPIES configuration
**When** considering card rewards
**Then** Strike_R should be limited to 4 copies
**And** Defend_R should be limited to 4 copies
**And** the AI should skip additional copies beyond these limits

#### Scenario: Limit unique high-impact cards

**Given** the MAX_COPIES configuration
**When** considering card rewards
**Then** Bash should be limited to 1 copy
**And** Cleave should be limited to 1 copy
**And** Perfected Strike should be limited to 1 copy
**And** the AI should skip additional copies beyond these limits

#### Scenario: Allow multiple copies of efficient cards

**Given** the MAX_COPIES configuration
**When** considering card rewards
**Then** Iron Wave should be allowed up to 2 copies
**And** Shrug It Off should be allowed up to 2 copies
**And** the AI should accept these copies even with duplicates in deck

### Requirement: Diagnostic logging for decision debugging

The AI MUST log key decision points for debugging and analysis.

#### Scenario: Log agent selection

**Given** the game is starting
**When** an agent is created
**Then** it should log whether OptimizedAgent or SimpleAgent is used
**And** it should log the player class

#### Scenario: Log combat planning results

**Given** the AI is planning a combat turn
**When** beam search completes
**Then** it should log the number of sequences evaluated
**And** it should log the best sequence found
**And** it should log the score of the best sequence
**And** it should log if lethal was detected

#### Scenario: Log card reward decisions

**Given** a card reward is offered
**When** the AI selects a card
**Then** it should log the available cards
**And** it should log the chosen card
**And** it should log the archetype detected (if any)
**And** it should log the synergy scores (if using optimized evaluation)

#### Scenario: Log fallback behavior

**Given** an error occurs in OptimizedAgent
**When** the AI falls back to SimpleAgent behavior
**Then** it should log that a fallback occurred
**And** it should log the error that caused the fallback
**And** it should continue the game without crashing
