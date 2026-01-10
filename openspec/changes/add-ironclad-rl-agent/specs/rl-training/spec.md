# Spec: RL Training Infrastructure

## ADDED Requirements

### Requirement: Experience Replay Buffer

The system SHALL provide an experience replay buffer that stores game transitions (state, action, reward, next_state, done) for off-policy training.

#### Scenario: Store transition
- **WHEN** a game transition occurs (action taken in state S resulting in state S')
- **THEN** the system SHALL store (S, a, r, S', done) tuple in replay buffer
- **AND** the buffer SHALL enforce maximum capacity (default: 100,000 transitions)
- **AND** when buffer is full, old transitions SHALL be discarded (FIFO policy)

#### Scenario: Sample training batch
- **WHEN** training step requires batch of experiences
- **THEN** the system SHALL randomly sample N transitions (default: N=64)
- **AND** each sample SHALL include (state, action, reward, next_state, done)
- **AND** sampling distribution SHALL be uniform over all stored transitions

#### Scenario: Buffer persistence
- **WHEN** training is interrupted or checkpoint saved
- **THEN** the system SHALL save replay buffer contents to disk
- **AND** the system SHALL support loading buffer from disk to resume training

### Requirement: Training Loop Orchestration

The system SHALL provide a training loop that coordinates environment interaction, data collection, and network optimization.

#### Scenario: Online training
- **WHEN** training mode is enabled
- **THEN** the system SHALL run game episodes continuously
- **AND** every environment step SHALL store transition in replay buffer
- **AND** every 4 steps SHALL trigger a network optimization step
- **AND** every 1000 steps SHALL update target network parameters

#### Scenario: Offline training from collected data
- **WHEN** training from pre-collected dataset
- **THEN** the system SHALL load transitions from disk
- **AND** populate replay buffer with loaded data
- **AND** perform training iterations without game interaction
- **AND** stop after specified number of epochs or when convergence criteria met

#### Scenario: Training checkpoint
- **WHEN** training reaches checkpoint interval (default: every 100 games)
- **THEN** the system SHALL save network parameters to disk
- **AND** save optimizer state (for Adam momentum)
- **AND** save training metadata (episode, win rate, average reward)
- **AND** the checkpoint file SHALL be loadable to resume training

### Requirement: Exploration Strategy

The system SHALL implement ε-greedy exploration to balance exploration and exploitation during training.

#### Scenario: Exploration during training
- **WHEN** agent selects action during training
- **THEN** with probability ε, select random action from valid actions
- **AND** with probability (1-ε), select action with highest Q-value (greedy)
- **AND** ε SHALL start at 1.0 (full exploration)
- **AND** ε SHALL decay linearly to 0.1 over 50,000 steps
- **AND** ε SHALL remain at 0.1 for remainder of training

#### Scenario: Disable exploration during inference
- **WHEN** agent runs in inference mode (model evaluation)
- **THEN** ε SHALL be set to 0.0 (no exploration)
- **AND** agent SHALL always select action with highest Q-value among valid actions

### Requirement: Loss Function and Optimization

The system SHALL use Huber loss with Adam optimizer for stable DQN training.

#### Scenario: Compute DQN loss
- **WHEN** training step computes loss from batch of transitions
- **THEN** the system SHALL compute target Q-value: r + γ × max_a' Q_target(s', a') if not done, else r
- **AND** use discount factor γ = 0.99
- **AND** compute predicted Q-value: Q_online(s, a)
- **AND** compute Huber loss between predicted and target Q-values
- **AND** Huber loss delta parameter SHALL be 1.0

#### Scenario: Optimization step
- **WHEN** loss is computed
- **THEN** the system SHALL backpropagate loss through network
- **AND** update network parameters using Adam optimizer
- **AND** initial learning rate SHALL be 1e-4
- **AND** learning rate SHALL decay to 1e-5 over training
- **AND** clip gradients to max norm of 10.0

### Requirement: Training Metrics and Logging

The system SHALL track and log training metrics for monitoring learning progress.

#### Scenario: Episode logging
- **WHEN** an episode (game) completes
- **THEN** the system SHALL log episode number, victory/defeat, floor reached, total reward
- **AND** log to console and CSV file (training_log.csv)
- **AND** log SHALL include timestamp for analysis

#### Scenario: Performance tracking
- **WHEN** training progresses
- **THEN** the system SHALL maintain running average of last 100 episodes' win rate
- **AND** track average reward per episode
- **AND** track average floor reached
- **AND** display these metrics every 10 episodes

#### Scenario: TensorBoard integration (optional)
- **WHEN** TensorBoard logging is enabled
- **THEN** the system SHALL log loss values per training step
- **AND** log win rate over time
- **AND** log average reward over time
- **AND** log learning rate schedule
- **AND** provide visualization of learning curves

### Requirement: Model Checkpoint Management

The system SHALL save and load model checkpoints for training resumption and model deployment.

#### Scenario: Save checkpoint
- **WHEN** checkpoint is triggered (periodic or manual)
- **THEN** the system SHALL save file named `ironclad_rl_ep{episode}_win{win_rate:.3f}.pth`
- **AND** file SHALL contain PyTorch state_dict for online network
- **AND** file SHALL contain PyTorch state_dict for target network
- **AND** file SHALL contain optimizer state_dict
- **AND** file SHALL contain training metadata (episode, epsilon, total_steps)

#### Scenario: Load checkpoint
- **WHEN** checkpoint file is loaded
- **THEN** the system SHALL restore network parameters
- **AND** restore optimizer state
- **AND** restore training metadata
- **AND** validate checkpoint version compatibility
- **AND** log successful load with metadata

#### Scenario: Checkpoint cleanup
- **WHEN** number of checkpoints exceeds limit (default: 5)
- **THEN** the system SHALL delete oldest checkpoints
- **AND** keep most recent N checkpoints
- **AND** keep checkpoint with highest win rate

### Requirement: Training CLI Interface

The system SHALL provide command-line interface for training and data collection modes.

#### Scenario: Collect training data
- **WHEN** user runs `python main.py --agent rl --mode collect --games 1000 --output data/train.pkl`
- **THEN** the system SHALL run 1000 games with random or heuristic policy
- **AND** collect all transitions from these games
- **AND** save transitions to specified output file
- **AND** log progress every 10 games

#### Scenario: Train model from collected data
- **WHEN** user runs `python main.py --agent rl --mode train --data data/train.pkl --epochs 100`
- **THEN** the system SHALL load training data from file
- **AND** populate replay buffer
- **AND** train for 100 epochs over the data
- **AND** save checkpoints every 10 epochs
- **AND** save final model to `checkpoints/ironclad_rl_final.pth`

#### Scenario: Run trained model
- **WHEN** user runs `python main.py --agent rl --model checkpoints/ironclad_rl_final.pth`
- **THEN** the system SHALL load specified model checkpoint
- **AND** disable exploration (ε=0)
- **AND** run game using trained policy
- **AND** log game results with model metadata

#### Scenario: Resume training from checkpoint
- **WHEN** user runs `python main.py --agent rl --mode train --resume checkpoints/ironclad_rl_ep500.pth`
- **THEN** the system SHALL load checkpoint (networks, optimizer, metadata)
- **AND** continue training from saved state
- **AND** continue ε decay from saved value
- **AND** save new checkpoints incrementally
