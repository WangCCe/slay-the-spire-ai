# spirecomm
A package for using Communication Mod with Slay the Spire, plus a simple AI

## Communication Mod

Communication Mod is a mod that allows communication between Slay the Spire and an external process. It can be found here:

https://github.com/ForgottenArbiter/CommunicationMod

The spirecomm package facilitates communicating with Slay the Spire through Communication Mod and accessing the state of the game.

## Requirements:

- Python 3.5+
- kivy, only for the example GUI for Communication Mod, found in utilities

## Running the AI:

To run a simple Slay the Spire AI, configure Communication Mod to run main.py

### Recommended Mods for RL Training

**SuperFastMode** - Speed up gameplay for faster training

SuperFastMode is a highly recommended mod that significantly accelerates game speed by skipping animations and wait times. This is especially useful for RL training, where the agent needs to play hundreds or thousands of games.

- **Repository**: https://github.com/Skrelpoid/SuperFastMode
- **Effect**: 4-5x faster gameplay (30-40 seconds per game vs 2-3 minutes)
- **Installation**: Download and extract to your Slay the Spire `mods` directory
- **Usage**: Configure speed multiplier in mod settings (default 2x, can go up to 10x)

**Why use SuperFastMode for RL training?**
- Faster data collection: 800+ games per night (vs 200 without)
- Reduced training time: 10 hours for 1000 games (vs 40+ hours)
- Better exploration: Agent sees more diverse game states in less time
- Compatible with Communication Mod and all other mods

### RL Agent

This project includes a Deep Q-Network (DQN) reinforcement learning agent that learns to play Slay the Spire autonomously.

**Features:**
- Dense reward shaping (combat damage, kills, HP preservation)
- 570-dimensional state encoding
- 1000-action space (cards, potions, map navigation, etc.)
- Experience replay and target networks
- Automatic checkpoint saving/loading

**Usage:**
```bash
# Training mode (with exploration)
python main.py --agent rl --train

# Inference mode (using trained model)
python main.py --agent rl --model checkpoints/rl_model_ep100.pth
```

**Note:** Training requires PyTorch. See `spirecomm/ai/rl/` for implementation details.

## Installing spirecomm:

Run `python setup.py install` from the distribution root directory