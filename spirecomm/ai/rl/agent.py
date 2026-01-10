"""
RL Agent for Slay the Spire.

Integrates StateEncoder, ActionEncoder, RewardCalculator, and DQNTrainer
into a complete RL agent compatible with Communication Mod.
"""

import numpy as np
import torch
import logging
from typing import Optional

from .state_encoder import StateEncoder
from .action_encoder import ActionEncoder
from .reward import RewardCalculator
from .trainer import DQNTrainer
from .network import create_dqn
from spirecomm.spire.game import Game
from spirecomm.communication.action import Action

logger = logging.getLogger(__name__)


class RLAgent:
    """
    Reinforcement Learning Agent for Slay the Spire.

    Uses DQN to learn to play the game autonomously.
    Compatible with existing Communication Mod integration.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        training: bool = False,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        epsilon: float = 0.0  # Exploration rate (0 = greedy, higher = more random)
    ):
        """
        Initialize RL agent.

        Args:
            model_path: Path to saved model checkpoint (if loading)
            training: Whether agent is in training mode
            device: Device for neural network ("cuda" or "cpu")
            epsilon: Exploration rate for inference-time exploration
        """
        self.device = device
        self.training_mode = training

        # Initialize components
        self.state_encoder = StateEncoder()
        self.action_encoder = ActionEncoder()
        self.reward_calculator = RewardCalculator()

        # Initialize trainer
        self.trainer = DQNTrainer(device=device) if training else None

        # Load model or create new network
        if model_path is not None:
            self.load_model(model_path)
            logger.info(f"Loaded model from {model_path}")
        else:
            # Create network for inference
            self.network = create_dqn("standard", device=device)
            self.network.eval()
            logger.info("Initialized new network")

        self.epsilon = epsilon
        self.last_state = None
        self.last_action = None

        # Episode tracking
        self.episode_reward = 0.0
        self.episode_steps = 0

    def get_next_action_in_game(self, game: Game) -> Action:
        """
        Get next action for current game state.

        Main entry point for Communication Mod integration.

        Args:
            game: Current game state

        Returns:
            Action object to execute
        """
        try:
            # Encode current state
            state = self.state_encoder.encode(game)

            # Get action mask
            action_mask = np.array(self.action_encoder.get_action_mask(game), dtype=bool)

            # Select action
            if self.training_mode and self.trainer is not None:
                action_idx = self.trainer.select_action(state, action_mask, training=True)
            else:
                # Inference mode with optional exploration
                if np.random.random() < self.epsilon:
                    # Exploration
                    valid_actions = np.where(action_mask)[0]
                    action_idx = np.random.choice(valid_actions) if len(valid_actions) > 0 else 0
                else:
                    # Exploitation
                    state_tensor = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
                    mask_tensor = torch.from_numpy(action_mask).unsqueeze(0).to(self.device)

                    with torch.no_grad():
                        action_idx = self.network.get_best_action(state_tensor, mask_tensor).item()

            # Decode action to Action object
            action = self.action_encoder.decode_action(action_idx, game)

            # Track state and action for training
            if self.last_state is not None and self.training_mode:
                # Calculate reward (simplified, would need game context)
                reward = 0.0  # Placeholder
                done = not game.in_combat if hasattr(game, 'in_combat') else False

                # Store transition
                self.trainer.store_transition(
                    self.last_state,
                    self.last_action,
                    reward,
                    state,
                    done
                )

                # Train periodically
                loss = self.trainer.train_step()
                if loss is not None:
                    logger.debug(f"Training step, loss: {loss:.4f}")

            self.last_state = state
            self.last_action = action_idx

            return action

        except Exception as e:
            logger.error(f"Error in get_next_action_in_game: {e}")
            # Return safe fallback action
            from spirecomm.communication.action import EndTurnAction
            return EndTurnAction()

    def reset(self) -> None:
        """Reset agent state for new episode."""
        self.last_state = None
        self.last_action = None
        self.episode_reward = 0.0
        self.episode_steps = 0

        if self.training_mode and self.trainer is not None:
            self.trainer.update_episode_count()

    def load_model(self, model_path: str) -> None:
        """Load model from checkpoint file."""
        checkpoint = torch.load(model_path, map_location=self.device)

        # Create network if needed
        if not hasattr(self, 'network') or self.network is None:
            self.network = create_dqn("standard", device=self.device)

        # Load state dict
        if 'online_network_state_dict' in checkpoint:
            # Full checkpoint from trainer
            self.network.load_state_dict(checkpoint['online_network_state_dict'])
            self.network.eval()
        else:
            # Network state dict only
            self.network.load_state_dict(checkpoint)
            self.network.eval()

        logger.info(f"Loaded model from {model_path}")

    def save_model(self, model_path: str, episode: int = 0) -> None:
        """Save current model to checkpoint file."""
        if self.training_mode and self.trainer is not None:
            self.trainer.save_checkpoint(model_path, episode)
        else:
            # Save just the network
            checkpoint = {
                'online_network_state_dict': self.network.state_dict(),
                'episode': episode,
            }
            torch.save(checkpoint, model_path)
            logger.info(f"Saved model to {model_path}")


# Convenience function for creating agents
def create_agent(
    model_path: Optional[str] = None,
    training: bool = False,
    device: str = "cuda" if torch.cuda.is_available() else "cpu"
) -> RLAgent:
    """
    Create RL agent with specified configuration.

    Args:
        model_path: Path to saved model
        training: Whether in training mode
        device: Device for neural network

    Returns:
        Initialized RLAgent
    """
    return RLAgent(
        model_path=model_path,
        training=training,
        device=device
    )
