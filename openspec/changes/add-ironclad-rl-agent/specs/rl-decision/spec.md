# Spec: RL Decision Integration

## ADDED Requirements

### Requirement: RL Agent Interface

The system SHALL provide an RLAgent class that implements the same interface as SimpleAgent for seamless integration with Communication Mod.

#### Scenario: Initialize RL agent
- **WHEN** RLAgent is instantiated
- **THEN** load PyTorch model from specified checkpoint file
- **AND** initialize state encoder
- **AND** initialize action encoder
- **AND** set agent to inference mode (model.eval())
- **AND** disable dropout and gradient computation
- **AND** if checkpoint file not found, raise FileNotFoundError

#### Scenario: Get action during combat
- **WHEN** game state is updated and action is required in combat
- **THEN** encode current game state to 512-dim vector
- **AND** pass state through DQN network to get Q-values
- **AND** compute action mask for valid combat actions
- **AND** select action with highest Q-value among valid actions
- **AND** convert action index to Action object (PlayCardAction, PotionAction, or EndTurnAction)
- **AND** return Action object to coordinator

#### Scenario: Get action at card reward screen
- **WHEN** game state shows card reward screen
- **THEN** encode game state (including reward cards)
- **THEN** pass state through DQN network
- **AND** compute action mask for card reward actions
- **AND** select action (choose card or skip)
- **AND** convert action index to ChooseAction
- **AND** return ChooseAction to coordinator

#### Scenario: Get action at map screen
- **WHEN** game state shows map screen
- **THEN** encode game state (including available map nodes)
- **AND** pass state through DQN network
- **AND** compute action mask for map path actions
- **AND** select action (choose path)
- **AND** convert action index to ChooseAction (map node index)
- **AND** return ChooseAction to coordinator

#### Scenario: Get action at shop screen
- **WHEN** game state shows shop screen
- **THEN** encode game state (including shop inventory, gold)
- **AND** pass state through DQN network
- **AND** compute action mask for shop actions (buy, purge, exit)
- **AND** select action
- **AND** convert action index to appropriate Action (ChooseAction or ProceedAction)
- **AND** return Action to coordinator

#### Scenario: Get action at rest site
- **WHEN** game state shows rest site
- **THEN** encode game state (including HP, deck contents)
- **AND** pass state through DQN network
- **AND** compute action mask for rest options (rest, smith, lift, dig)
- **AND** select action
- **AND** convert action index to ChooseAction
- **AND** return ChooseAction to coordinator

#### Scenario: Get action at event screen
- **WHEN** game state shows event screen
- **THEN** encode game state (including event context, available choices)
- **AND** pass state through DQN network
- **AND** compute action mask for event choices
- **AND** select action
- **AND** convert action index to ChooseAction
- **AND** return ChooseAction to coordinator

### Requirement: Game State Callback Integration

The system SHALL integrate RL agent with Communication Mod's callback-based state updates.

#### Scenario: Register state change callback
- **WHEN** RLAgent is registered with coordinator
- **THEN** agent SHALL register callback for state_change events
- **AND** callback SHALL receive updated Game object
- **AND** callback SHALL trigger action selection when game is ready

#### Scenario: Track game progression for rewards
- **WHEN** game state updates
- **THEN** agent SHALL track:
  - Previous state (for reward calculation)
  - Last action taken
  - Cumulative reward for current episode
  - Floor progression
  - Monsters killed
  - Cards obtained
  - Relics obtained
- **AND** store tracking information for reward computation

#### Scenario: Detect game termination
- **WHEN** game state indicates victory or defeat
- **THEN** agent SHALL compute terminal reward (+1000 or -500)
- **AND** assign terminal reward to last action taken
- **AND** reset tracking for next episode
- **AND** log episode outcome (victory/defeat, floor reached, total reward)

### Requirement: Error Handling and Fallback

The system SHALL gracefully handle errors and provide fallback behavior to prevent game crashes.

#### Scenario: Handle encoding errors
- **WHEN** state encoder raises exception (e.g., unexpected card/monster)
- **THEN** log error to stderr and ai_debug.log
- **AND** return safe fallback action (EndTurnAction or ProceedAction)
- **AND** continue game without crashing

#### Scenario: Handle model inference errors
- **WHEN** PyTorch model raises exception during forward pass
- **THEN** log error with stack trace
- **AND** return safe fallback action
- **AND** continue game without crashing

#### Scenario: Handle action conversion errors
- **WHEN** action encoder fails to convert action index to Action object
- **THEN** log error with action index and state context
- **AND** return safe fallback action
- **AND** continue game without crashing

### Requirement: Training Mode vs Inference Mode

The system SHALL support both training mode (with exploration and data collection) and inference mode (pure exploitation).

#### Scenario: Enable training mode
- **WHEN** agent is instantiated with `mode='train'`
- **THEN** set model to training mode (model.train())
- **AND** enable ε-greedy exploration
- **AND** initialize replay buffer
- **AND** enable experience collection (store transitions)
- **AND** enable periodic network updates (every 4 steps)
- **AND** enable target network updates (every 1000 steps)

#### Scenario: Enable inference mode
- **WHEN** agent is instantiated with `mode='inference'` (default)
- **THEN** set model to evaluation mode (model.eval())
- **AND** disable exploration (ε = 0.0)
- **AND** disable experience collection
- **AND** disable network updates
- **AND** use deterministic action selection (argmax Q-values)

#### Scenario: Switch between modes
- **WHEN** agent needs to switch from training to inference
- **THEN** save replay buffer to disk if training interrupted
- **AND** save final checkpoint
- **AND** reset exploration (ε = 0.0)
- **AND** disable data collection
- **AND** log mode transition

### Requirement: Multi-Screen Decision Routing

The system SHALL route decisions to appropriate action encoders based on current screen type.

#### Scenario: Combat screen routing
- **WHEN** game.screen_type == 'COMBAT' or 'BOSS'
- **THEN** route to combat action encoder
- **AND** generate combat actions (play card, use potion, end turn)
- **AND** validate action targets are valid monsters

#### Scenario: Card reward screen routing
- **WHEN** game.screen_type == 'CARD_REWARD' or 'BOSS_REWARD'
- **THEN** route to card reward action encoder
- **AND** generate selection actions (choose card or skip)
- **AND** encode reward cards into state vector

#### Scenario: Map screen routing
- **WHEN** game.screen_type == 'MAP'
- **THEN** route to map action encoder
- **AND** generate path selection actions
- **AND** encode available map nodes into state vector

#### Scenario: Shop screen routing
- **WHEN** game.screen_type == 'SHOP_ROOM'
- **THEN** route to shop action encoder
- **AND** generate purchase/actions (buy cards, relics, potions, purge)
- **AND** encode shop inventory and player gold into state

#### Scenario: Rest site routing
- **WHEN** game.screen_type == 'REST'
- **THEN** route to rest action encoder
- **AND** generate rest options (rest, smith, lift, dig)
- **AND** encode player HP and deck into state

#### Scenario: Event screen routing
- **WHEN** game.screen_type == 'EVENT'
- **THEN** route to event action encoder
- **AND** generate event choice actions
- **AND** encode event context and choices into state

#### Scenario: Default fallback routing
- **WHEN** game.screen_type is unrecognized or None
- **THEN** log warning with screen_type
- **AND** return ProceedAction() as safe fallback
- **AND** continue game without crashing

### Requirement: Data Collection for Training

The system SHALL collect experience data during training for offline or online training.

#### Scenario: Collect transition
- **WHEN** agent takes action in training mode
- **THEN** store (state, action, reward, next_state, done) tuple in replay buffer
- **AND** state SHALL be 512-dim feature vector
- **AND** action SHALL be integer index (0-999)
- **AND** reward SHALL be scalar float
- **AND** next_state SHALL be 512-dim feature vector (None if terminal)
- **AND** done SHALL be boolean (True if episode ended)

#### Scenario: Save collected data
- **WHEN** training session ends or checkpoint saved
- **THEN** save replay buffer contents to disk as pickle file
- **AND** filename SHALL include timestamp and episode count
- **AND** file SHALL contain list of (state, action, reward, next_state, done) tuples
- **AND** log file size and number of transitions

#### Scenario: Load collected data
- **WHEN** training from pre-collected data
- **THEN** load pickle file
- **AND** populate replay buffer with loaded transitions
- **AND** validate data integrity (shapes, ranges)
- **AND** log number of loaded transitions

### Requirement: Performance Metrics Tracking

The system SHALL track performance metrics during both training and inference.

#### Scenario: Track episode statistics
- **WHEN** episode (game) completes
- **THEN** record:
  - Victory or defeat
  - Floor reached
  - Total reward
  - Number of turns
  - Number of combats
  - Damage dealt
  - Damage taken
  - Cards obtained
  - Relics obtained
  - Gold spent
  - Ascension level
- **AND** append to training log CSV

#### Scenario: Compute running averages
- **WHEN** multiple episodes completed
- **THEN** maintain running average of last 100 episodes for:
  - Win rate
  - Average floor reached
  - Average reward per episode
  - Average turns per combat
- **AND** display these metrics every 10 episodes

#### Scenario: Generate performance report
- **WHEN** training completes or user requests report
- **THEN** generate summary report including:
  - Total episodes trained
  - Final win rate
  - Best win rate achieved
  - Learning curve data (episodes vs win rate)
  - Comparison vs random baseline
  - Comparison vs SimpleAgent (if available)
- **AND** save report as markdown file

### Requirement: Model Persistence and Versioning

The system SHALL save and load trained models with version compatibility.

#### Scenario: Save trained model
- **WHEN** model is saved to disk
- **THEN** save as PyTorch .pth file
- **AND** include metadata:
  - Model version (e.g., "v1.0")
  - PyTorch version used
  - Training episode count
  - Win rate at save time
  - Network architecture hyperparameters
  - State encoder version
  - Action encoder version
- **AND** verify file was written successfully

#### Scenario: Load model with version check
- **WHEN** model is loaded from disk
- **THEN** check PyTorch version compatibility
- **AND** check state/action encoder versions
- **AND** log warning if version mismatch
- **AND** attempt to load with backward compatibility if possible
- **AND** raise error if incompatible version

#### Scenario: Model checkpoint naming
- **WHEN** saving checkpoint
- **THEN** use filename format: `ironclad_rl_ep{episode:05d}_win{win_rate:.3f}_{timestamp}.pth`
- **AND** example: `ironclad_rl_em00500_win0.425_20250110_153022.pth`
- **AND** ensure filenames are sortable and descriptive
