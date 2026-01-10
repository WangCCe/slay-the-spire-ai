# Design: Reinforcement Learning Agent for Ironclad

## Context

Slay the Spire is a roguelike deck-building game with complex state space (~709 cards, 178 relics, 66 monsters). Current AI uses hand-crafted heuristics requiring extensive tuning. This design introduces a deep RL agent that learns to play autonomously.

**Constraints**:
- Local GPU training available (RTX 3060 Laptop GPU, 6GB VRAM)
- Dependency-free core library (PyTorch optional)
- Real-time decision requirements (~100ms response)
- Communication Mod compatibility (stdin/stdout protocol)
- Ironclad class only (proof of concept)

**Stakeholders**:
- Researchers: Study RL learning dynamics in complex games
- Players: Benchmark AI performance against human strategies
- Developers: Extensible RL framework for other characters

## Goals / Non-Goals

### Goals
- ✅ Implement functional DQN agent for Ironclad that can complete runs
- ✅ Design state/action representations that capture game complexity
- ✅ Create training pipeline for local CPU training
- ✅ Demonstrate learning progress (win rate improvement over training)
- ✅ Integrate with existing spirecomm architecture (coordinator, actions)

### Non-Goals
- ❌ Beat existing OptimizedAgent performance (validation only)
- ❌ Optimize for GPU/cluster training (local CPU focus)
- ❌ Support all character classes (Ironclad proof of concept)
- ❌ Real-time training (train offline, deploy online)
- ❌ Multi-agent or self-play (single agent vs game)

## Decisions

### Decision 1: DQN Algorithm (Deep Q-Network)

**What**: Use DQN with experience replay and target networks.

**Why**:
- Discrete action space (play card X at monster Y, use potion, end turn)
- Stable and well-understood (works in Atari, Doom)
- Off-policy: can reuse historical data efficiently
- Easier to debug than policy gradient methods

**Alternatives Considered**:
- **PPO**: Better for continuous control, but overkill for discrete actions
- **A3C**: Requires parallel environments (complex on single machine)
- **Dueling DQN**: Possible enhancement, but added complexity not needed for validation

**Trade-offs**:
- ✅ Stable convergence with target networks
- ✅ Sample efficient with replay buffer
- ✅ Fast training with GPU acceleration (RTX 3060)
- ❌ Struggles with large action spaces (mitigated by action masking)

### Decision 2: Fixed State Representation (512-dim vector)

**What**: Convert Game object to fixed-size 512-dimensional feature vector.

**Why**:
- Neural networks require fixed-size inputs
- Captures essential information without explosion
- Feasible for CPU training

**Feature Components** (total 512 dims):
- Player state (20): HP, max HP, energy, block, gold, hand size, deck size, discard pile size, draw pile size, current floor, act number, ascension level, 8 one-hot for player class
- Hand cards encoding (150): Max 10 cards × 15 features each (card_id, cost, damage, block, type, is_upgraded, etc.)
- Deck composition (120): One-hot encoding of top 120 most common Ironclad cards (count of each in deck+discard+draw)
- Monster states (150): Max 5 monsters × 30 features each (HP, max HP, block, intent, last two intents, buffs/debuffs, powers, is_gone, etc.)
- Relic states (89): Binary vector of all relics owned
- Potion states (15): Max 5 potions × 3 features (potion_id, count, can_use)
- Context features (28): Room type, turn number, cards played this turn, cards drawn this combat, damage dealt this combat, etc.

**Alternatives Considered**:
- **CNN/attention on card lists**: More expressive but slower on CPU
- **Graph neural network**: Captures relationships but complex to implement
- **Raw JSON → embedding**: Data preprocessing bottleneck

**Trade-offs**:
- ✅ Fixed size enables standard MLP networks
- ✅ Fast forward pass on CPU (~10-50ms)
- ❌ Loses some information (e.g., exact card order beyond hand)
- ❌ Hard-coded features require maintenance (card additions)

### Decision 3: Action Space with Masking

**What**: Discrete action space (max 1000 actions) with action masking.

**Action Encoding**:
- **0-99**: Play card 0-9 at monster 0-9 (10 cards × 10 monster targets)
- **100-119**: Use potion 0-9 at monster 0-9 (10 potions × 10 targets)
- **120**: End turn
- **121-130**: Card reward selection (10 cards)
- **131-135**: Map path choices (5 options)
- **136-140**: Event choices (5 options)
- **141-150**: Shop purchase actions (buy card, buy relic, buy potion, remove card, etc.)
- **151-160**: Rest site options (rest, smith, lift, dig)

**Action Masking**: At each step, compute valid action mask and set Q-values for invalid actions to -inf during training/inference.

**Alternatives Considered**:
- **Parameterized actions**: (card_id, target_id) as continuous outputs → Harder to train
- **Hierarchical actions**: First choose action type, then specific action → Adds complexity
- **Separate networks per decision type**: Duplicate parameters, no sharing

**Trade-offs**:
- ✅ Simple interface (single discrete action per step)
- ✅ Easy to implement action masking
- ❌ Large action space (mitigated by masking)
- ❌ Wastes capacity on invalid actions (acceptable)

### Decision 4: Reward Shaping

**What**: Dense reward shaping to guide learning, with sparse terminal rewards.

**Reward Components**:
- **Combat rewards**:
  - Damage dealt: `+0.1 × damage` (capped at +10 per turn)
  - Monster killed: `+10` per monster
  - All monsters killed: `+50` bonus
  - Player HP lost: `-5 × HP_lost`
  - Turn end penalty: `-0.1` (encourage efficiency)

- **Progression rewards**:
  - Floor advanced: `+1 × floor_number`
  - Elite defeated: `+30`
  - Boss defeated: `+100`
  - Card obtained: `+5` (scaled by card power)
  - Relic obtained: `+20`
  - Gold obtained: `+0.01 × gold`

- **Terminal rewards**:
  - Victory: `+1000`
  - Defeat: `-500`

- **Penalties**:
  - Invalid action: `-10` (should not happen with masking)
  - Game over: `-500`

**Reward Normalization**: Scale rewards to have std ≈ 1 during training (empirically measured).

**Alternatives Considered**:
- **Sparse rewards only**: Only victory/defeat → Too hard to learn
- **Inverse reinforcement learning**: Learn from expert demonstrations → Overkill for validation
- **Curriculum learning**: Start with simple scenarios → Complex to implement

**Trade-offs**:
- ✅ Dense rewards provide learning signal throughout game
- ✅ Terminal rewards incentivize winning
- ❌ Reward shaping may bias policy (acceptable for validation)
- ❌ Requires tuning reward weights (iterative process)

### Decision 5: Network Architecture

**What**: 3-layer MLP with ReLU activations.

**Architecture**:
```
Input (512) → Linear(512, 512) → ReLU →
Linear(512, 256) → ReLU →
Linear(256, 128) → ReLU →
Linear(128, 1000) → Q-values
```

**Total Parameters**: ~420K (trainable on CPU)

**Training Details**:
- Loss: Huber loss (smooth L1)
- Optimizer: Adam (lr=1e-4, decay to 1e-5)
- Batch size: 128 (increased for GPU, up from 64)
- Target network update: Every 1000 steps
- Replay buffer: 100k transitions
- Training frequency: Every 4 environment steps
- Exploration: ε-greedy (ε=1.0 → 0.1 over 50k steps)
- **GPU acceleration**: CUDA-enabled for training (RTX 3060 Laptop GPU)
- **Mixed precision**: FP16 where supported for faster training

**Alternatives Considered**:
- **Deeper network (5+ layers)**: More expressive but slower
- **Dueling architecture**: Separate value/advantage streams → Added complexity
- **Recurrent network (LSTM/GRU)**: Capture temporal dependencies → Harder to train

**Trade-offs**:
- ✅ Simple architecture, easy to debug
- ✅ Fast forward pass on CPU (~10ms)
- ✅ Very fast forward pass on GPU (~1-2ms)
- ❌ Limited expressiveness (acceptable for validation)
- ❌ No memory of past states beyond current observation

## Risks / Trade-offs

### Risk 1: Training Speed Limited by Game Execution

**Risk**: While GPU training is fast, data collection still requires running the actual game (bottleneck is game speed, not computation).

**Mitigation**:
- GPU accelerates network training by ~10-20x vs CPU
- Batch size increased to 128 for better GPU utilization
- Mixed precision (FP16) training where supported for 2x speedup
- Game execution is still the bottleneck (~10 min per game)
- Target: 10k games = ~70 days of continuous game running (acceptable for research)
- Can use checkpoint/resume to train over weeks/months

### Risk 2: Large State Space

**Risk**: 512-dim state may not capture important nuances (card synergies, relic combos).

**Mitigation**:
- Include engineered features (archetype detection in state vector)
- Iteratively add features if agent struggles
- Use ensemble methods if single network insufficient

### Risk 3: Sparse Reward for Long-Term Decisions

**Risk**: Card rewards/decisions affect game 10+ floors later; credit assignment problem.

**Mitigation**:
- Dense intermediate rewards (gold, relics, floor progress)
- N-step returns (n=10) to propagate rewards faster
- Prioritized experience replay for high-reward transitions

### Risk 4: Action Space Explosion with Many Cards

**Risk**: Late game has 20+ cards in deck, 10+ in hand → huge action space.

**Mitigation**:
- Action capping: Only consider top 10 cards by some heuristic
- Hierarchical actions: First select card type, then specific card
- Prune obviously bad actions (0-cost cards when no energy, etc.)

### Risk 5: Overfitting to Training Scenarios

**Risk**: Agent learns to exploit specific monster patterns/relic combos.

**Mitigation**:
- Random seed variation during training
- Validation on unseen seeds
- Regularization (dropout, L2) in network

## Migration Plan

### Phase 1: Infrastructure (Week 1)
1. Create `spirecomm/ai/rl/` module structure
2. Implement state encoder (Game → 512-dim vector)
3. Implement action encoder (action index → Action object)
4. Create replay buffer and training loop skeleton
5. Test data pipeline with random actions

### Phase 2: Network and Training (Week 2-3)
1. Implement DQN network in PyTorch
2. Implement reward shaping functions
3. Implement ε-greedy exploration with decay
4. Train on simple scenarios (single monster combat)
5. Debug and tune hyperparameters

### Phase 3: Integration (Week 4)
1. Integrate RLAgent with Communication Mod
2. Implement action masking for valid actions
3. Add model checkpointing/resume capability
4. Test full game runs with random/early-trained model

### Phase 4: Training and Validation (Week 5-8)
1. Run training for 10k games (local CPU)
2. Monitor win rate, floor progress, reward curves
3. Analyze learned policies (what strategies emerge?)
4. Document findings and lessons learned

### Rollback Plan
- If RL fails to converge: Fall back to OptimizedAgent, document failure modes
- If training too slow: Reduce state dim, simplify network, limit to Act 1
- If integration breaks: Keep SimpleAgent/OptimizedAgent as default, RL as experimental feature

## Open Questions

1. **Training time estimate**: How long for 10k games with GPU?
   - Game execution: ~10 min per game × 10k = ~70 days (bottleneck)
   - Network training: GPU accelerates by ~15x, so minimal overhead
   - Total: ~70 days of game running (can be paused/resumed)
   - Alternative: Start with 1-2k games for initial validation (~1-2 weeks)
   - Acceptable for research project (not production)

2. **Network capacity**: Is 420K parameters sufficient?
   - Monitor for underfitting (training loss doesn't decrease)
   - Scale up if needed (512→1024 hidden dims)

3. **Action space design**: Should combat/non-combat actions be separate?
   - Current: Unified action space with masking
   - Alternative: Hierarchical policy (meta-decision → specific action)

4. **Pre-training**: Should we pre-train on expert data?
   - Current: Pure RL from scratch
   - Alternative: Imitation learning pre-training → RL fine-tuning

5. **Validation metrics**: How to measure success?
   - Win rate vs random agent?
   - Win rate vs OptimizedAgent?
   - Learning curve shape?
   - Emergent strategy analysis?

## Implementation Notes

### Key Files
- `spirecomm/ai/rl/network.py`: DQN architecture
- `spirecomm/ai/rl/state_encoder.py`: Feature extraction
- `spirecomm/ai/rl/action_encoder.py`: Action mapping
- `spirecomm/ai/rl/reward.py`: Reward functions
- `spirecomm/ai/rl/replay_buffer.py`: Experience storage
- `spirecomm/ai/rl/trainer.py`: Training loop
- `spirecomm/ai/rl/agent.py`: RLAgent interface
- `spirecomm/ai/ml/checkpoint.py`: Model persistence
- `spirecomm/ai/ml/metrics.py`: TensorBoard logging

### Dependencies
```python
# setup.py extras_require
extras_require={
    'rl': [
        'torch>=1.9.0',
        'tensorboard>=2.6.0',
    ]
}
```

### CLI Interface
```bash
# Collect data (online training - play and train simultaneously)
python main.py --agent rl --mode train --games 1000 --checkpoint checkpoints/

# Train from collected data (offline training)
python main.py --agent rl --mode train --data data/training_data.pkl --epochs 100 --checkpoint checkpoints/

# Run trained model
python main.py --agent rl --model checkpoints/ironclad_rl.pth --seed 12345

# Resume training from checkpoint
python main.py --agent rl --mode train --resume checkpoints/ironclad_rl_ep500.pth
```

### GPU Performance Expectations (RTX 3060 Laptop)
- **Forward pass**: ~1-2ms per state (GPU) vs ~10-50ms (CPU)
- **Training step**: ~5-10ms per batch (GPU) vs ~100-200ms (CPU)
- **Speedup**: ~15-20x faster training on GPU
- **VRAM usage**: ~500MB for networks + ~1.5GB for replay buffer = ~2GB total (well within 6GB)
