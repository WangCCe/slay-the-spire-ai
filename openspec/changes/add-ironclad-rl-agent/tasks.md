# Tasks: Add Reinforcement Learning Agent for Ironclad

## 1. Infrastructure and Data Pipeline

- [ ] 1.1 Create `spirecomm/ai/rl/` module directory structure with `__init__.py`
- [ ] 1.2 Implement `StateEncoder` class to convert Game objects to 570-dim feature vectors
  - [ ] 1.2.1 Encode player state (HP, energy, block, gold, etc.)
  - [ ] 1.2.1.1 Encode player combat stats (strength, dexterity, debuffs)
  - [ ] 1.2.2 Encode hand cards (max 10 cards × 15 features)
  - [ ] 1.2.2.1 Encode card targeting/exhaust/retain flags
  - [ ] 1.2.3 Encode deck composition (one-hot of top 120 Ironclad cards)
  - [ ] 1.2.4 Encode monster states (max 5 monsters × 30 features)
  - [ ] 1.2.4.1 Encode intents, multi-hit counts, and key debuffs
  - [ ] 1.2.5 Encode relics (binary vector of all relics)
  - [ ] 1.2.6 Encode potions (max 5 potions × 3 features)
  - [ ] 1.2.7 Encode context (room type, turn, floor, etc.)
  - [ ] 1.2.7.1 Encode in-combat popup context (screen type, choice counts, confirm/cancel)
  - [ ] 1.2.8 Add unit tests for encoding correctness
- [ ] 1.3 Implement `ActionEncoder` class to map discrete actions to Action objects
  - [ ] 1.3.1 Define action space constants (max 1000 actions)
  - [ ] 1.3.2 Implement action index → PlayCardAction mapping
  - [ ] 1.3.3 Implement action index → PotionAction mapping
  - [ ] 1.3.4 Implement action index → ChooseAction mapping (cards, map, events)
  - [ ] 1.3.5 Implement action index → EndTurnAction mapping
  - [ ] 1.3.6 Add action masking function to filter invalid actions
- [ ] 1.4 Implement `ReplayBuffer` class for experience storage and sampling
  - [ ] 1.4.1 Store transitions (state, action, reward, next_state, done)
  - [ ] 1.4.2 Implement uniform random sampling
  - [ ] 1.4.3 Add buffer size limits (100k transitions)
  - [ ] 1.4.4 Test with random data
- [ ] 1.5 Implement `RewardCalculator` class for reward shaping
  - [ ] 1.5.1 Implement combat rewards (damage, kills, HP loss)
  - [ ] 1.5.2 Implement progression rewards (floors, elites, bosses)
  - [ ] 1.5.3 Implement acquisition rewards (cards, relics, gold)
  - [ ] 1.5.4 Implement terminal rewards (victory, defeat)
  - [ ] 1.5.5 Add reward normalization/scaling

## 2. Neural Network Implementation

- [ ] 2.1 Install PyTorch as optional dependency (update setup.py)
- [ ] 2.2 Implement `DQNetwork` class as PyTorch Module
  - [ ] 2.2.1 Define network architecture (512→512→256→128→1000)
  - [ ] 2.2.2 Implement forward pass
  - [ ] 2.2.3 Add network initialization (Xavier/Kaiming)
- [ ] 2.3 Implement `DQNTrainer` class for training loop
  - [ ] 2.3.1 Implement forward pass with action masking
  - [ ] 2.3.2 Compute loss (Huber loss between predicted and target Q-values)
  - [ ] 2.3.3 Implement optimizer (Adam with lr decay)
  - [ ] 2.3.4 Implement target network update (every 1000 steps)
  - [ ] 2.3.5 Implement ε-greedy exploration with decay
  - [ ] 2.3.6 Add gradient clipping (max norm 10.0)
- [ ] 2.4 Implement `model checkpoint` utilities
  - [ ] 2.4.1 Save model state (network, optimizer, training metadata)
  - [ ] 2.4.2 Load model from checkpoint
  - [ ] 2.4.3 Resume training from checkpoint
  - [ ] 2.4.4 Handle versioning (PyTorch version compatibility)

## 3. RL Agent Integration

- [ ] 3.1 Implement `RLAgent` class implementing agent interface
  - [ ] 3.1.1 Inherit from or mimic SimpleAgent interface
  - [ ] 3.1.2 Implement `get_next_action_in_game()` using DQN forward pass
  - [ ] 3.1.3 Implement action masking for valid actions only
  - [ ] 3.1.4 Implement ε-greedy action selection during training
  - [ ] 3.1.5 Handle all screen types (COMBAT, CARD_REWARD, MAP, SHOP, etc.)
  - [ ] 3.1.5.1 Route in-combat popup screens (HAND_SELECT/GRID/COMBAT_REWARD) through RL
  - [ ] 3.1.6 Integrate with coordinator callbacks for state updates
- [ ] 3.2 Implement training mode vs inference mode
  - [ ] 3.2.1 Add `is_training` flag to RLAgent
  - [ ] 3.2.2 Collect experiences during training games
  - [ ] 3.2.3 Periodically update network during training
  - [ ] 3.2.4 Disable exploration during inference
- [ ] 3.3 Implement `TransitionCollector` for data collection
  - [ ] 3.3.1 Record (state, action, reward) tuples during game
  - [ ] 3.3.2 Handle game termination (victory/defeat rewards)
  - [ ] 3.3.3 Save collected data to disk for offline training
- [ ] 3.4 Update `main.py` to support RL agent
  - [ ] 3.4.1 Add `--agent rl` CLI flag
  - [ ] 3.4.2 Add `--mode train|collect|inference` flag
  - [ ] 3.4.3 Add `--model` flag for loading checkpoints
  - [ ] 3.4.4 Add `--output` flag for data collection
  - [ ] 3.4.5 Add error handling for missing PyTorch dependency

## 4. ML Utilities

- [ ] 4.1 Implement `checkpoint.py` in `spirecomm/ai/ml/`
  - [ ] 4.1.1 Save/load PyTorch models
  - [ ] 4.1.2 Store training metadata (epoch, loss, win rate)
  - [ ] 4.1.3 Handle checkpoint versioning
- [ ] 4.2 Implement `metrics.py` in `spirecomm/ai/ml/`
  - [ ] 4.2.1 Log training metrics (loss, reward, win rate)
  - [ ] 4.2.2 Integrate with TensorBoard (optional)
  - [ ] 4.2.3 Plot learning curves (matplotlib)
  - [ ] 4.2.4 Compute performance statistics

## 5. Testing and Validation

- [ ] 5.1 Test state encoding with real game states
  - [ ] 5.1.1 Run 100 games and encode all states
  - [ ] 5.1.2 Verify encoding dimensionality (always 512)
  - [ ] 5.1.3 Check for NaN/Inf values
  - [ ] 5.1.4 Visualize encoded states (PCA/t-SNE)
- [ ] 5.2 Test action encoding/masking
  - [ ] 5.2.1 Enumerate all valid actions in various game states
  - [ ] 5.2.2 Verify action masking correctness
  - [ ] 5.2.3 Test edge cases (empty hand, no monsters, etc.)
- [ ] 5.3 Test replay buffer
  - [ ] 5.3.1 Store and retrieve 10k random transitions
  - [ ] 5.3.2 Verify sampling distribution
  - [ ] 5.3.3 Test buffer overflow behavior
- [ ] 5.4 Test DQN forward pass
  - [ ] 5.4.1 Pass random states through network
  - [ ] 5.4.2 Verify output shape (batch_size × 1000)
  - [ ] 5.4.3 Test action masking in forward pass
  - [ ] 5.4.4 Benchmark inference speed (target < 100ms)
- [ ] 5.5 Integration test: Play 10 complete games with random actions
  - [ ] 5.5.1 Verify RLAgent doesn't crash
  - [ ] 5.5.2 Check Communication Mod integration
  - [ ] 5.5.3 Validate all screen types handled
  - [ ] 5.5.4 Confirm data collection works

## 6. Training and Evaluation

- [ ] 6.1 Implement training script
  - [ ] 6.1.1 Load collected data or train online
  - [ ] 6.1.2 Implement training loop with checkpointing
  - [ ] 6.1.3 Add validation every N episodes
  - [ ] 6.1.4 Add early stopping if no improvement
- [ ] 6.2 Run initial training (1k games)
  - [ ] 6.2.1 Start with random policy
  - [ ] 6.2.2 Monitor loss curves
  - [ ] 6.2.3 Track win rate progress
  - [ ] 6.2.4 Debug convergence issues
- [ ] 6.3 Analyze learned policies
  - [ ] 6.3.1 Visualize Q-values for different states
  - [ ] 6.3.2 Identify high-value states/actions
  - [ ] 6.3.3 Compare with human strategies
  - [ ] 6.3.4 Look for emergent behaviors
- [ ] 6.4 Extended training (10k games)
  - [ ] 6.4.1 Run training on local machine
  - [ ] 6.4.2 Monitor performance metrics
  - [ ] 6.4.3 Compare win rate vs random agent
  - [ ] 6.4.4 Document training time and resource usage
- [ ] 6.5 Performance comparison
  - [ ] 6.5.1 Compare win rate vs SimpleAgent
  - [ ] 6.5.2 Compare win rate vs OptimizedAgent (A10 baseline)
  - [ ] 6.5.3 Analyze failure modes
  - [ ] 6.5.4 Document lessons learned

## 7. Documentation

- [ ] 7.1 Create README for RL agent
  - [ ] 7.1.1 Installation instructions (PyTorch setup)
  - [ ] 7.1.2 Quick start guide (run trained model)
  - [ ] 7.1.3 Training guide (collect data, train model)
  - [ ] 7.1.4 Architecture overview
- [ ] 7.2 Document state representation
  - [ ] 7.2.1 List all 512 features with indices
  - [ ] 7.2.2 Explain encoding choices
  - [ ] 7.2.3 Provide examples
- [ ] 7.3 Document reward shaping
  - [ ] 7.3.1 Explain reward components
  - [ ] 7.3.2 Provide reward function code
  - [ ] 7.3.3 Discuss tuning trade-offs
- [ ] 7.4 Create training guide
  - [ ] 7.4.1 Hyperparameter recommendations
  - [ ] 7.4.2 Debugging tips
  - [ ] 7.4.3 Expected training timeline
  - [ ] 7.4.4 Common issues and solutions
- [ ] 7.5 Update project documentation
  - [ ] 7.5.1 Update CLAUDE.md with RL agent info
  - [ ] 7.5.2 Update project.md with new dependencies
  - [ ] 7.5.3 Add RL agent to AGENTS.md if needed

## Dependencies and Parallelization Notes

- **Tasks 1-2** can be done in parallel after module creation
- **Task 3** depends on **Tasks 1-2**
- **Task 4** can be done in parallel with **Tasks 1-3**
- **Task 5** requires **Tasks 1-4** to complete
- **Task 6** requires **Task 5** to complete
- **Task 7** can be done throughout implementation

**Estimated Timeline**: 8 weeks (assuming part-time work)
- Weeks 1-2: Tasks 1-2 (Infrastructure + Network)
- Weeks 3-4: Task 3 (Integration)
- Week 5: Task 4 (Utilities) + Task 5 (Testing)
- Weeks 6-8: Task 6 (Training and Evaluation)
- Throughout: Task 7 (Documentation)
