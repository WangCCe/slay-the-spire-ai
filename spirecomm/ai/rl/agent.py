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
from spirecomm.spire.character import PlayerClass

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
        self.chosen_class = PlayerClass.IRONCLAD  # Default to Ironclad

        logger.info("Initializing StateEncoder...")
        # Initialize components
        self.state_encoder = StateEncoder()
        logger.info("StateEncoder initialized")

        logger.info("Initializing ActionEncoder...")
        self.action_encoder = ActionEncoder()
        logger.info("ActionEncoder initialized")

        logger.info("Initializing RewardCalculator...")
        self.reward_calculator = RewardCalculator()
        logger.info("RewardCalculator initialized")

        # Initialize trainer with correct state dimension
        if training:
            logger.info(f"Initializing DQNTrainer (device={device})...")
            self.trainer = DQNTrainer(state_dim=self.state_encoder.feature_dim, device=device)
            logger.info("DQNTrainer initialized")
        else:
            self.trainer = None
            logger.info("No trainer (inference mode)")

        # Load model or create new network
        if model_path is not None:
            logger.info(f"Loading model from {model_path}...")
            self.load_model(model_path)
            logger.info(f"Loaded model from {model_path}")
        else:
            # Create network for inference with correct state dimension
            logger.info(f"Creating new network (device={device})...")
            self.network = create_dqn("standard", state_dim=self.state_encoder.feature_dim, device=device)
            self.network.eval()
            logger.info("Network initialized")

        self.epsilon = epsilon
        self.last_state = None
        self.last_action = None
        self.last_game = None  # Track previous game state for reward calculation

        # Episode tracking
        self.episode_reward = 0.0
        self.episode_steps = 0

        # Failed action tracking to prevent action loops
        self.failed_actions = set()  # Set of action indices that failed recently
        self.consecutive_failures = {}  # action_index -> failure count
        self.max_consecutive_failures = 3  # Disable action after 3 consecutive failures

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

            # Get action mask and exclude recently failed actions
            action_mask = np.array(self.action_encoder.get_action_mask(game), dtype=bool)

            # Exclude actions that have failed repeatedly
            for failed_idx in self.failed_actions:
                if failed_idx < len(action_mask):
                    action_mask[failed_idx] = False

            # Ensure at least one action is valid
            if not action_mask.any():
                logger.warning(f"All actions masked, clearing failed actions set")
                self.failed_actions.clear()
                self.consecutive_failures.clear()
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

            # Clear failure record for this action (we're trying it again)
            if action_idx in self.failed_actions:
                logger.debug(f"Retrying previously failed action {action_idx}")
                self.failed_actions.discard(action_idx)
                self.consecutive_failures.pop(action_idx, None)

            # Decode action to Action object
            action = self.action_encoder.decode_action(action_idx, game)

            # Track state and action for training
            if self.training_mode and self.trainer is not None:
                # Calculate reward using RewardCalculator
                if self.last_state is not None and self.last_game is not None:
                    # Use RewardCalculator to compare game states and calculate reward
                    reward = self.reward_calculator.calculate_step_reward(
                        current_game=game,
                        last_game=self.last_game,
                        action_type="combat"
                    )

                    # Check for game over
                    done = "GAME_OVER" in str(game.screen_type) or (
                        hasattr(game, 'player') and game.player is not None and
                        hasattr(game.player, 'current_hp') and game.player.current_hp <= 0
                    )
                else:
                    # First action, no reward yet
                    reward = 0.0
                    done = False

                # Store transition (if we have a last_state)
                if self.last_state is not None:
                    self.trainer.store_transition(
                        self.last_state,
                        self.last_action,
                        reward,
                        state,
                        done
                    )

                # Train periodically (every step if buffer is ready and train_freq allows)
                try:
                    loss = self.trainer.train_step()
                    if loss is not None:
                        self.episode_reward += reward
                        self.episode_steps += 1
                        logger.debug(f"Training step {self.trainer.total_steps}, loss: {loss:.4f}, reward: {reward:.2f}")
                except Exception as e:
                    # Training error should not block decision making
                    logger.warning(f"Training step failed (continuing with inference): {e}")
                    import traceback
                    logger.debug(traceback.format_exc())

            # Update last state, action, and game
            self.last_state = state
            self.last_action = action_idx
            self.last_game = game

            return action

        except Exception as e:
            import traceback
            logger.error(f"Error in get_next_action_in_game: {e}\n" + "".join(traceback.format_exc()))
            # Return safe fallback action
            from spirecomm.communication.action import EndTurnAction
            return EndTurnAction()

    def reset(self) -> None:
        """Reset agent state for new episode."""
        self.last_state = None
        self.last_action = None
        self.last_game = None  # Reset game state tracking
        self.episode_reward = 0.0
        self.episode_steps = 0

        # Clear failed action tracking for new episode
        self.failed_actions.clear()
        self.consecutive_failures.clear()

        if self.training_mode and self.trainer is not None:
            self.trainer.update_episode_count()
            # Reset reward calculator tracking for new episode
            self.reward_calculator.reset()
            # NOTE: Don't clear replay buffer - we need to accumulate experience across episodes
            # Only clear if buffer has mixed dimension data (shouldn't happen after fixes)

    def handle_error(self, error):
        """
        Handle errors from Communication Mod.

        Logs the error, tracks failed actions to prevent loops, and returns a safe action.
        """
        logger.error(f"RL Agent error: {error}")

        # Track failed action to prevent repeated failures
        if hasattr(self, 'last_action') and self.last_action is not None:
            action_idx = self.last_action
            self.consecutive_failures[action_idx] = self.consecutive_failures.get(action_idx, 0) + 1

            # If action has failed too many times, add to blocked set
            if self.consecutive_failures[action_idx] >= self.max_consecutive_failures:
                if action_idx not in self.failed_actions:
                    logger.warning(f"Action {action_idx} failed {self.consecutive_failures[action_idx]} times, disabling temporarily")
                self.failed_actions.add(action_idx)

        # Import StateAction to get current state instead of raising
        from spirecomm.communication.action import StateAction
        return StateAction()

    def get_next_action_out_of_game(self):
        """
        Handle out-of-game states (main menu, character select, etc.).

        Always returns StartGameAction to start a new game with the chosen character.
        """
        from spirecomm.communication.action import StartGameAction
        return StartGameAction(self.chosen_class)

    def load_model(self, model_path: str) -> None:
        """Load model from checkpoint file."""
        checkpoint = torch.load(model_path, map_location=self.device)

        # Create network if needed
        if not hasattr(self, 'network') or self.network is None:
            self.network = create_dqn("standard", state_dim=self.state_encoder.feature_dim, device=self.device)

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
        """
        Save current model to checkpoint file with atomic write operation.

        Uses a temporary file and atomic rename to prevent corruption if the
        process crashes during writing.
        """
        import os
        import shutil
        import tempfile

        if self.training_mode and self.trainer is not None:
            self.trainer.save_checkpoint(model_path, episode)
        else:
            # Save just the network (inference mode)
            checkpoint = {
                'online_network_state_dict': self.network.state_dict(),
                'episode': episode,
            }

            # Atomic write: save to temporary file first, then rename
            temp_fd, temp_path = tempfile.mkstemp(
                dir=os.path.dirname(model_path),
                prefix=os.path.basename(model_path) + '.tmp_'
            )

            try:
                # Close the file descriptor (torch.save will handle opening)
                os.close(temp_fd)

                # Save to temporary file
                torch.save(checkpoint, temp_path)

                # Atomic rename (overwrites existing file if present)
                shutil.move(temp_path, model_path)

                logger.info(f"Saved model to {model_path}")

            except Exception as e:
                # Clean up temporary file if something went wrong
                try:
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except:
                    pass
                raise



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
