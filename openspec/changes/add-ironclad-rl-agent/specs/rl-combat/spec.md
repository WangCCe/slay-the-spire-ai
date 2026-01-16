# Spec: RL Combat Decision System

## ADDED Requirements

### Requirement: State Representation Encoding

The system SHALL encode the complete game state into a fixed-size 570-dimensional feature vector suitable for neural network input.

#### Scenario: Encode complete game state
- **WHEN** a game state needs to be processed by the neural network
- **THEN** the system SHALL extract features from Game object
- **AND** produce a fixed-size 570-dimensional vector (float32)
- **AND** features SHALL be normalized/scaled appropriately (e.g., HP/max_hp, block/10)
- **AND** features SHALL not contain NaN or Inf values

#### Scenario: Player state encoding (20 dims)
- **WHEN** encoding player state
- **THEN** include normalized HP (current_hp / max_hp)
- **AND** include current energy (0-3+ scaled to 0-1)
- **AND** include current block (scaled to 0-1, cap at 20)
- **AND** include gold (log-scaled: log10(gold+1) / 4)
- **AND** include hand size, deck size, discard size, draw pile size
- **AND** include current floor (0-55 scaled to 0-1)
- **AND** include act number (1-4 one-hot encoded)
- **AND** include ascension level (0-20 scaled to 0-1)
- **AND** include player class (Ironclad/Silent/Defect/Watcher one-hot)
- **AND** include player strength (scaled, cap at 10)
- **AND** include player dexterity (scaled, cap at 10)

#### Scenario: Hand cards encoding (150 dims)
- **WHEN** encoding cards in hand
- **THEN** encode up to 10 cards (if fewer, pad with zeros)
- **AND** for each card, include 15 features:
  - Card ID (one-hot of top 100 Ironclad cards)
  - Cost for turn (0-3+ scaled to 0-1)
  - Base damage (scaled to 0-1, cap at 30)
  - Base block (scaled to 0-1, cap at 20)
  - Card type (Attack/Skill/Power/Status-or-Curse one-hot)
  - Is upgraded (binary)
  - Is ethereal (binary)
  - Exhausts (binary)
  - Has retain (binary)
  - Is target-required (binary)
  - Apply weak (binary)
  - Apply vulnerable (binary)

#### Scenario: Deck composition encoding (120 dims)
- **WHEN** encoding deck composition
- **THEN** one-hot encode top 120 most common Ironclad cards
- **AND** for each card, store count in (deck + discard + draw)
- **AND** counts capped at 5 (for any card more than 5, clip to 5)
- **AND** cards not in deck have value 0

#### Scenario: Monster states encoding (150 dims)
- **WHEN** encoding monster states
- **THEN** encode up to 5 monsters (if fewer, pad with zeros)
- **AND** for each monster, include 30 features:
  - Monster ID (one-hot of top 60 Act 1-3 monsters)
  - Current HP (current_hp / max_hp)
  - Max HP (log-scaled)
  - Current block (scaled to 0-1, cap at 20)
  - Current intent (one-hot: Attack/Defend/Buff/Debuff/Unknown)
  - Intent damage (if attack, scaled to 0-1)
  - Intent hits (if multi-hit, scaled to 0-1, cap at 5)
  - Intent block (if defend, scaled to 0-1)
  - Strength (scaled, capped at 20)
  - Weak stacks (capped at 5)
  - Frail stacks (capped at 5)
  - Vulnerable stacks (capped at 5)
  - Poison stacks (capped at 20)
  - Artifact stacks (capped at 5)
  - Metallicize (scaled, cap at 10)
  - Regeneration (scaled, cap at 10)
  - Is gone (dead/escaped, binary)
  - Is minion (binary)
  - Half dead (has lost half HP, binary)

#### Scenario: Relic states encoding (89 dims)
- **WHEN** encoding owned relics
- **THEN** create binary vector of all 89 relics
- **AND** set to 1 if player owns relic, 0 otherwise
- **AND** relics include all base game relics (not DLC-specific)

#### Scenario: Potion states encoding (15 dims)
- **WHEN** encoding potions
- **THEN** encode up to 5 potions (if fewer, pad with zeros)
- **AND** for each potion, include 3 features:
  - Potion ID (one-hot of top 30 potions)
  - Count (0-5)
  - Can use this turn (binary, checks valid targets)

#### Scenario: Context features encoding (26 dims)
- **WHEN** encoding contextual game information
- **THEN** include room type (Monster/Event/Shop/Rest/Treasure/Boss one-hot)
- **AND** include turn number in combat (scaled to 0-1, cap at 20)
- **AND** include screen context flags (combat, combat_reward, hand_select, grid, event, shop, map, rest, other)
- **AND** include choice_available (binary)
- **AND** include choice list size (scaled to 0-1, cap at 10)
- **AND** include required selections (scaled to 0-1, cap at 5)
- **AND** include selected count (scaled to 0-1, cap at 5)
- **AND** include can_confirm (binary)
- **AND** include can_cancel (binary)
- **AND** include can_proceed (binary)
- **AND** include hand size at start of turn
- **AND** include energy at start of turn
- **AND** include max energy this combat (Bottled Flame/Relic effects)

### Requirement: Action Space Definition

The system SHALL define a discrete action space of up to 1000 actions covering all possible game interactions.

#### Scenario: Combat action encoding
- **WHEN** encoding combat actions
- **THEN** actions 0-99 represent playing card 0-9 on monster 0-9
  - Format: `action_index = card_index * 10 + monster_index`
  - card_index 0-9: indices of cards in hand
  - monster_index 0-9: target monster (0-4 for actual monsters, others for special targets)
- **AND** actions 100-119 represent using potion 0-9 on monster 0-9
  - Format: `action_index = 100 + potion_index * 10 + monster_index`
- **AND** action 120 represents ending turn

#### Scenario: Card reward action encoding
- **WHEN** at card reward screen with up to 3 cards + skip option
- **THEN** actions 121-123 represent choosing card 0, 1, or 2
- **AND** action 124 represents skip (take no card)
- **AND** invalid card indices SHALL be masked (e.g., only 2 cards available, action 123 masked)

#### Scenario: Map node action encoding
- **WHEN** at map screen choosing next node
- **THEN** actions 131-135 represent choosing map path 0-4
- **AND** map paths correspond to available connections from current node
- **AND** invalid/out-of-bounds paths SHALL be masked

#### Scenario: Event choice action encoding
- **WHEN** at event screen with choices
- **THEN** actions 136-140 represent event choice 0-4
- **AND** choices correspond to buttons in event
- **AND** invalid choices SHALL be masked based on event logic

#### Scenario: Shop action encoding
- **WHEN** at shop screen
- **THEN** actions 141-150 represent shop interactions:
  - 141: Buy card (leftmost card)
  - 142: Buy card (middle card)
  - 143: Buy card (rightmost card)
  - 144: Buy relic
  - 145: Buy potion
  - 146: Remove card (purge service)
  - 147: Exit shop
  - 148-150: Reserved for future shop actions
- **AND** actions SHALL be masked based on affordability (gold check)

#### Scenario: Rest site action encoding
- **WHEN** at rest site
- **THEN** actions 151-154 represent rest options:
  - 151: Rest (heal 30% HP)
  - 152: Smith (upgrade card)
  - 153: Lift (copy card - totem hook format)
  - 154: Dig (get relic - wheel format)
- **AND** invalid options SHALL be masked based on available actions

### Requirement: Action Masking

The system SHALL mask invalid actions to prevent the agent from selecting impossible or illegal actions.

#### Scenario: Compute valid action mask
- **WHEN** agent needs to select action in current game state
- **THEN** the system SHALL compute boolean mask of size 1000
- **AND** set mask[i] = True if action i is valid, False otherwise
- **AND** mask SHALL consider:
  - Hand size (only cards 0 to hand_size-1 valid)
  - Energy availability (only affordable cards valid)
  - Monster count (only targets 0 to num_monsters-1 valid)
  - Potion availability and validity
  - Screen-specific constraints

#### Scenario: Combat action masking
- **WHEN** in combat screen
- **THEN** mask card actions beyond current hand size
- **AND** mask card actions with insufficient energy (use card.cost_for_turn)
- **AND** mask card targets that don't exist (monster_index >= num_monsters)
- **AND** mask potion actions if potion not available or invalid target
- **AND** unmask End Turn action (always valid)

#### Scenario: Card reward action masking
- **WHEN** at card reward screen
- **THEN** only unmask actions for available cards (0-2 based on offer size)
- **AND** unmask skip action
- **AND** mask all combat/shop/map/event actions

#### Scenario: Shop action masking
- **WHEN** at shop screen
- **THEN** mask buy actions if insufficient gold
- **AND** mask card purge if insufficient gold or no cards to purge
- **AND** unmask exit action

#### Scenario: Apply mask to Q-values
- **WHEN** computing action from Q-values
- **THEN** set Q-value for masked actions to -inf
- **AND** select action with highest Q-value among unmasked actions
- **AND** during training, random action selection also respects mask
- **AND** ε-greedy random choice uniformly samples from valid actions only

### Requirement: DQN Network Architecture

The system SHALL implement a deep Q-network with specified architecture for processing game states.

#### Scenario: Network forward pass
- **WHEN** state vector (512-dim) is passed through network
- **THEN** network SHALL produce Q-values for all 1000 actions
- **AND** architecture SHALL be:
  - Linear(512 → 512) + ReLU + Dropout(0.1)
  - Linear(512 → 256) + ReLU + Dropout(0.1)
  - Linear(256 → 128) + ReLU + Dropout(0.1)
  - Linear(128 → 1000)
- **AND** output layer SHALL NOT have activation function (linear)

#### Scenario: Network parameter count
- **WHEN** network is initialized
- **THEN** total trainable parameters SHALL be approximately 420K
- **AND** parameters SHALL be initialized with Kaiming (He) initialization
- **AND** biases SHALL be initialized to zero

#### Scenario: Action masking in forward pass
- **WHEN** forward pass receives action mask
- **THEN** before returning Q-values, apply mask: Q[mask == False] = -inf
- **AND** ensure masked actions have no chance of being selected

### Requirement: Target Network Update

The system SHALL maintain a target network for stable Q-value estimation.

#### Scenario: Initialize target network
- **WHEN** training starts
- **THEN** create target network as copy of online network
- **AND** target network parameters SHALL be frozen (not trained)
- **AND** target network used only for computing Q(s', a') in TD error

#### Scenario: Periodic target network update
- **WHEN** training step count is multiple of 1000
- **THEN** copy all parameters from online network to target network
- **AND** use hard update (θ_target = θ_online, not polyak averaging)
- **AND** log target network update to console

### Requirement: Reward Calculation

The system SHALL calculate shaped rewards for each action to provide learning feedback.

#### Scenario: Combat rewards
- **WHEN** agent deals damage to monster
- **THEN** reward += 0.1 × damage dealt (capped at +10 per turn)
- **AND** **WHEN** monster is killed, reward += 10
- **AND** **WHEN** all monsters killed, reward += 50
- **AND** **WHEN** player loses HP, reward -= 5 × HP_lost
- **AND** **WHEN** turn ends, reward -= 0.1 (efficiency incentive)

#### Scenario: Progression rewards
- **WHEN** player advances to next floor
- **THEN** reward += 1 × floor_number
- **AND** **WHEN** elite defeated, reward += 30
- **AND** **WHEN** boss defeated, reward += 100
- **AND** **WHEN** card obtained, reward += 5 × card_power_score (1-3)
- **AND** **WHEN** relic obtained, reward += 20
- **AND** **WHEN** gold obtained, reward += 0.01 × gold_amount

#### Scenario: Terminal rewards
- **WHEN** game ends in victory
- **THEN** reward += 1000
- **AND** **WHEN** game ends in defeat
- **THEN** reward += -500
- **AND** this reward SHALL be assigned to the last action before termination

#### Scenario: Penalties
- **WHEN** agent attempts invalid action (should not happen with masking)
- **THEN** reward -= 10
- **AND** log warning about invalid action attempt
- **AND** **WHEN** game over (defeat)
- **THEN** no further actions possible, terminal reward applied

### Requirement: Inference Speed

The system SHALL make combat decisions within time constraints for real-time play.

#### Scenario: Forward pass timing
- **WHEN** agent computes action for a given state
- **THEN** forward pass (state → Q-values) SHALL complete within 100ms on CPU
- **AND** action masking SHALL add < 10ms overhead
- **AND** total decision time (encode + forward + mask + select) < 150ms

#### Scenario: Batch processing for training
- **WHEN** training processes batch of 64 states
- **THEN** forward pass SHALL complete within 500ms on CPU
- **AND** backward pass (loss computation) SHALL complete within 1s on CPU
- **AND** memory usage SHALL not exceed 2GB for replay buffer + networks
