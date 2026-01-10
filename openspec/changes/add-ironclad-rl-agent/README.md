# Reinforcement Learning Agent for Ironclad - Proposal Summary

## 🎯 Overview

This proposal adds a **pure reinforcement learning agent** for the Ironclad class in Slay the Spire, using DQN (Deep Q-Network) to learn from scratch without relying on hand-crafted heuristics.

## 📋 Quick Facts

- **Change ID**: `add-ironclad-rl-agent`
- **Algorithm**: DQN with experience replay and target networks
- **State Space**: 512-dimensional feature vector (player, cards, monsters, relics, potions, context)
- **Action Space**: 1000 discrete actions (combat, rewards, map, shop, events, rest)
- **Network**: 3-layer MLP (420K parameters)
- **Goal**: Validate RL feasibility (not beat existing AI)
- **Training**: Local GPU (RTX 3060 Laptop), ~10k games target
- **Dependencies**: PyTorch with CUDA (optional), core remains dependency-free

## 🏗️ Architecture

```
Game State (JSON)
    ↓
StateEncoder (Game → 512-dim vector)
    ↓
DQN Network (512 → 512 → 256 → 128 → 1000)
    ↓
Q-values (1000 actions)
    ↓
Action Masking (valid actions only)
    ↓
Best Action → ActionEncoder → Action Object → Communication Mod
```

## 📁 Files Structure

```
spirecomm/ai/rl/
├── __init__.py
├── agent.py              # RLAgent class (main interface)
├── network.py            # DQN PyTorch model
├── state_encoder.py      # Game → 512-dim vector
├── action_encoder.py     # Action index ↔ Action object
├── reward.py             # Reward shaping functions
├── replay_buffer.py      # Experience storage
└── trainer.py            # Training loop, checkpointing

spirecomm/ai/ml/
├── __init__.py
├── checkpoint.py         # Model save/load utilities
└── metrics.py            # TensorBoard logging
```

## 🎮 Decision Coverage

The RL agent handles **all decisions** for complete autonomous play:

1. **Combat**: Play cards, use potions, end turn
2. **Card Rewards**: Choose cards or skip
3. **Map Routing**: Select optimal path
4. **Events**: Make event choices
5. **Shops**: Buy cards/relics/potions, remove cards
6. **Rest Sites**: Rest, upgrade, lift, dig

## 📊 State Representation (512 dims)

| Component | Dimensions | Description |
|-----------|------------|-------------|
| Player State | 20 | HP, energy, block, gold, floor, act, ascension |
| Hand Cards | 150 | Max 10 cards × 15 features each |
| Deck Composition | 120 | One-hot of top 120 Ironclad cards (counts) |
| Monster States | 150 | Max 5 monsters × 30 features each |
| Relic States | 89 | Binary vector of all relics |
| Potion States | 15 | Max 5 potions × 3 features each |
| Context Features | 28 | Room type, turn, damage dealt, etc. |

## 🎯 Action Space (1000 actions)

| Range | Actions | Description |
|-------|---------|-------------|
| 0-99 | Play card | Card 0-9 at monster 0-9 |
| 100-119 | Use potion | Potion 0-9 at monster 0-9 |
| 120 | End turn | - |
| 121-124 | Card rewards | Choose card 0-2 or skip |
| 131-135 | Map paths | Choose path 0-4 |
| 136-140 | Event choices | Choose event option 0-4 |
| 141-150 | Shop actions | Buy, purge, exit |
| 151-154 | Rest options | Rest, smith, lift, dig |

## 🏆 Reward Shaping

**Combat Rewards**:
- Damage dealt: `+0.1 × damage` (capped at +10/turn)
- Monster killed: `+10`
- All monsters killed: `+50`
- HP lost: `-5 × HP_lost`
- Turn end: `-0.1`

**Progression Rewards**:
- Floor advanced: `+1 × floor_number`
- Elite defeated: `+30`
- Boss defeated: `+100`
- Card obtained: `+5` to `+15`
- Relic obtained: `+20`
- Gold: `+0.01 × gold`

**Terminal Rewards**:
- Victory: `+1000`
- Defeat: `-500`

## ⚙️ Training Configuration

```python
# Network
HIDDEN_LAYERS = [512, 256, 128]
ACTIVATION = "ReLU"
DROPOUT = 0.1
INITIALIZATION = "Kaiming"

# DQN
ALGORITHM = "DQN"
DISCOUNT_FACTOR = 0.99
LOSS = "Huber" (delta=1.0)
OPTIMIZER = "Adam"
LEARNING_RATE = 1e-4 → 1e-5 (decay)
GRADIENT_CLIP = 10.0

# Training
REPLAY_BUFFER_SIZE = 100_000
BATCH_SIZE = 128 (increased for GPU)
TARGET_NETWORK_UPDATE = 1000 steps
TRAINING_FREQUENCY = 4 steps

# Exploration
EPSILON_START = 1.0
EPSILON_END = 0.1
EPSILON_DECAY = 50_000 steps

# Hardware (RTX 3060 Laptop GPU)
PLATFORM = "CUDA" (GPU acceleration)
VRAM_USAGE = ~2GB (500MB networks + 1.5GB buffer)
GPU_SPEEDUP = ~15-20x faster than CPU
GAMES_TARGET = 10_000
```

## 📈 Performance Targets

**Validation Goals** (not performance benchmarks):
- ✅ Agent can complete full games without crashing
- ✅ Win rate > random agent (~5%)
- ✅ Learning progress visible (win rate improves over training)
- ✅ Learned policies interpretable (can analyze strategies)

**Stretch Goals** (if training goes well):
- Win rate > 20% on A10
- Win rate > 10% on A15
- Discover novel strategies not in SimpleAgent/OptimizedAgent

## 🚀 CLI Usage

```bash
# Install dependencies (with CUDA support for RTX 3060)
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
pip install tensorboard

# Collect training data while training simultaneously (recommended)
python main.py --agent rl --mode train --games 1000 --checkpoint checkpoints/

# Or collect data first, then train offline
python main.py --agent rl --mode collect --games 1000 --output data/train.pkl
python main.py --agent rl --mode train --data data/train.pkl --epochs 100 --checkpoint checkpoints/

# Run trained model
python main.py --agent rl --model checkpoints/ironclad_rl_final.pth

# Resume training from checkpoint
python main.py --agent rl --mode train --resume checkpoints/ironclad_rl_ep500.pth
```

## 🎮 GPU Performance (RTX 3060 Laptop)

| Operation | GPU Time | CPU Time | Speedup |
|-----------|----------|----------|---------|
| Forward pass (inference) | 1-2ms | 10-50ms | ~15-20x |
| Training step (batch=128) | 5-10ms | 100-200ms | ~15-20x |
| VRAM usage | ~2GB | N/A | N/A |

**Key insight**: Network training is fast on GPU, but game execution (~10 min/game) is the bottleneck.

## 📅 Implementation Timeline

**8 weeks** (part-time, single developer):

- **Weeks 1-2**: Infrastructure (state encoder, action encoder, replay buffer)
- **Weeks 3-4**: Network implementation (DQN, trainer, reward shaping)
- **Week 5**: Integration (RLAgent, Communication Mod, testing)
- **Weeks 6-8**: Training and evaluation (10k games, analysis, documentation)

## 📖 Key Design Decisions

### 1. DQN over PPO/A3C
- **Rationale**: Discrete action space, stable, off-policy (sample efficient)
- **Trade-off**: Slower convergence, but simpler implementation

### 2. Fixed 512-dim state vector
- **Rationale**: Fast CPU inference, no complex architectures
- **Trade-off**: Loses some information (card order, exact synergies)

### 3. Large action space with masking
- **Rationale**: Unified interface, simple masking
- **Trade-off**: Wastes capacity on invalid actions

### 4. Dense reward shaping
- **Rationale**: Provide learning signal throughout long games
- **Trade-off**: May bias policy (acceptable for validation)

### 5. Local GPU training
- **Rationale**: RTX 3060 available, much faster than CPU, no cloud costs
- **Trade-off**: Game execution still bottleneck (~70 days for 10k games), but network training is fast
- **Mitigation**: Use checkpoint/resume, train over weeks/months, start with 1-2k games for validation

## ⚠️ Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Training speed limited by game execution | High | GPU speeds up network training 15-20x, but game is still bottleneck (~70 days for 10k games). Use checkpoint/resume. |
| State space too large | Medium | Add engineered features (archetype detection) |
| Sparse rewards for long-term | Medium | N-step returns, prioritized replay |
| Action space explosion | Low | Action capping (top 10 cards only) |
| Overfitting to scenarios | Low | Random seeds, validation on unseen data |

## 🔬 Success Metrics

**Technical Validation**:
- [ ] Network trains without crashing
- [ ] Loss decreases over time
- [ ] Win rate improves over training
- [ ] Agent completes full games (all floors)

**Research Outcomes**:
- [ ] Analyze learned policies (what states/actions have high Q-values?)
- [ ] Identify emergent strategies (e.g., aggressive vs defensive play)
- [ ] Compare decision patterns with human experts
- [ ] Document failure modes (when/why does agent lose?)

**Future Work**:
- Extend to Silent/Defect/Watcher classes
- Try other algorithms (PPO, Dueling DQN)
- Implement imitation learning pre-training
- Add self-play / curriculum learning

## 📚 Documentation

- **Full Proposal**: `proposal.md`
- **Technical Design**: `design.md`
- **Implementation Tasks**: `tasks.md`
- **Specifications**:
  - `specs/rl-training/spec.md` - Training infrastructure
  - `specs/rl-combat/spec.md` - Combat decisions
  - `specs/rl-decision/spec.md` - High-level integration

## 🤝 Next Steps

1. **Review this proposal** - Check alignment with goals and constraints
2. **Ask questions** - Clarify any ambiguities
3. **Approve or revise** - Provide feedback on design decisions
4. **Start implementation** - Begin with Task 1.1 in `tasks.md`

## 💬 Notes

- This is a **research/exploratory project**, not production code
- Goal is **feasibility validation**, not beating existing AI
- Training on local GPU (RTX 3060) - network training fast, but **game execution is bottleneck** (~70 days for 10k games)
- Can **pause and resume** training over weeks/months
- Start with **1-2k games** for initial validation (~1-2 weeks)
- PyTorch dependency is **optional** (core library unchanged)
- RL agent **coexists** with SimpleAgent/OptimizedAgent (not replacing them)
