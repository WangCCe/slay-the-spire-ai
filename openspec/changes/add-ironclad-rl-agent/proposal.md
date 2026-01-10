# Change: Add Reinforcement Learning Agent for Ironclad

## Why

Current AI agents (SimpleAgent and OptimizedAgent) rely on hand-crafted heuristics and beam search. While effective, these approaches require extensive manual tuning and may not discover novel strategies. This change introduces a reinforcement learning (RL) agent for the Ironclad class to demonstrate that deep RL can learn to play Slay the Spire autonomously from scratch.

**Primary Goal**: Validate RL feasibility for Slay the Spire (not necessarily to beat existing AI performance).

**Scope**: Ironclad class only as proof-of-concept before extending to other classes.

## What Changes

- **Add RL training infrastructure**: DQN-based combat decision system with experience replay and target networks
- **Create state representation layer**: Convert complex Game objects into fixed-size feature vectors suitable for neural networks
- **Implement action space encoding**: Map playable cards, potions, and game commands to discrete action indices
- **Build reward shaping system**: Design reward signals for combat survival, damage dealt, game progression, and victory/defeat
- **Add training data collection**: Record game states, actions, and outcomes during play for offline training
- **Create RL agent interface**: New `RLAgent` class compatible with existing Communication Mod integration
- **Implement model checkpointing**: Save/load trained models and resume training from checkpoints

**BREAKING**: Adds new optional dependency on PyTorch for neural network training. Core spirecomm library remains dependency-free.

**Non-Breaking**:
- Existing SimpleAgent and OptimizedAgent remain unchanged
- RL agent is opt-in via command-line flag (`--rl` or `--agent rl`)
- Training mode separate from inference mode

## Impact

### Affected Specs
- **New**: `rl-training` - Training infrastructure, data collection, model checkpointing
- **New**: `rl-combat` - Combat decision policy network, state representation, action encoding
- **New**: `rl-decision` - High-level decision integration (card rewards, map routing, events, shops)

### Affected Code
- **New**: `spirecomm/ai/rl/` - RL-specific modules
  - `agent.py` - RLAgent class implementing decision interface
  - `network.py` - PyTorch neural network models (DQN, policy networks)
  - `replay_buffer.py` - Experience replay memory management
  - `state_encoder.py` - Convert Game objects to feature vectors
  - `action_encoder.py` - Map actions to discrete action space
  - `reward.py` - Reward shaping functions
  - `trainer.py` - Training loop, model checkpointing
- **New**: `spirecomm/ai/ml/` - ML utility modules (shared infrastructure)
  - `checkpoint.py` - Model save/load utilities
  - `metrics.py` - Training metrics logging
- **Modified**: `main.py` - Add RL agent option via CLI flags
- **Modified**: `setup.py` - Add optional PyTorch dependency

### Dependencies
- **New Optional**: `torch` (PyTorch) for neural network training
- **New Optional**: `tensorboard` for training visualization
- **Core**: No changes to dependency-free requirement for spirecomm library

### Performance Considerations
- **Training**: Game execution is bottleneck (~10 min/game), but GPU training is fast (RTX 3060: ~15-20x speedup vs CPU)
- **Inference**: Fast forward pass (~1-2ms per decision with GPU, ~10-50ms on CPU)
- **Memory**: Replay buffer requires ~1.5GB for 100k transitions, networks ~500MB (total ~2GB, fits in 6GB VRAM)
- **VRAM**: Well within RTX 3060 Laptop's 6GB budget

### Migration Path
1. Install PyTorch with CUDA: `pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118`
2. Collect training data: `python main.py --agent rl --mode collect --games 1000`
3. Train model: `python main.py --agent rl --mode train --epochs 100`
4. Run trained agent: `python main.py --agent rl --model checkpoints/ironclad_rl.pth`

### Open Questions
- Should we use DQN (value-based) or PPO (policy-based)? → **Decision**: DQN for simpler discrete action space
- How to handle variable number of monsters/card targets? → **Decision**: Fixed max size (5 monsters) with padding/masking
- Should RL handle all decisions or just combat? → **Decision**: All decisions for complete RL agent
- Training budget? → **Decision**: Local GPU training (RTX 3060), target 10k games over ~70 days (can pause/resume)
