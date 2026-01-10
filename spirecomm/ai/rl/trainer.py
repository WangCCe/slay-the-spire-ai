"""
DQN Trainer for Slay the Spire RL agent.

Implements training loop, experience collection, and model updates.
"""

import torch
import torch.nn.functional as F
import numpy as np
from typing import Optional, Tuple
import logging

from .network import DQNetwork, create_dqn
from .replay_buffer import ReplayBuffer
from .reward import RewardCalculator

logger = logging.getLogger(__name__)


class DQNTrainer:
    """
    DQN training loop with experience replay and target networks.

    Implements:
    - Experience collection and storage
    - Q-learning updates with Huber loss
    - Target network updates
    - ε-greedy exploration with decay
    - Model checkpointing
    """

    def __init__(
        self,
        state_dim: int = 570,
        action_dim: int = 1000,
        hidden_dims: list = [512, 256, 128],
        learning_rate: float = 1e-4,
        gamma: float = 0.99,
        buffer_size: int = 100000,
        batch_size: int = 128,
        target_update_freq: int = 1000,
        train_freq: int = 4,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.1,
        epsilon_decay: int = 50000,
        device: str = "cuda" if torch.cuda.is_available() else "cpu"
    ):
        """
        Initialize DQN trainer.

        Args:
            state_dim: State vector dimension
            action_dim: Number of possible actions
            hidden_dims: Hidden layer dimensions
            learning_rate: Learning rate for Adam optimizer
            gamma: Discount factor for TD targets
            buffer_size: Maximum replay buffer size
            batch_size: Training batch size
            target_update_freq: Steps between target network updates
            train_freq: Steps between training updates
            epsilon_start: Initial exploration rate
            epsilon_end: Final exploration rate
            epsilon_decay: Steps to decay epsilon
            device: Device for training ("cuda" or "cpu")
        """
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.train_freq = train_freq
        self.device = device

        # Networks
        logger.debug(f"Creating online network on {device}...")
        self.online_network = create_dqn("standard", state_dim, action_dim, device)
        logger.debug(f"Creating target network on {device}...")
        self.target_network = create_dqn("standard", state_dim, action_dim, device)
        logger.debug(f"Syncing target network with online network...")
        self.target_network.load_state_dict(self.online_network.state_dict())
        self.target_network.eval()
        logger.debug(f"Networks created and synced successfully")

        # Optimizer
        self.optimizer = torch.optim.Adam(self.online_network.parameters(), lr=learning_rate)

        # Replay buffer
        self.replay_buffer = ReplayBuffer(buffer_size, state_dim)

        # Exploration
        self.epsilon = epsilon_start
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.total_steps = 0

        # Training metrics
        self.episode_count = 0
        self.total_loss = 0.0
        self.total_updates = 0

        logger.info(f"Initialized DQNTrainer on device: {device}")

    def select_action(self, state: np.ndarray, action_mask: np.ndarray,
                     training: bool = True) -> int:
        """
        Select action using ε-greedy policy.

        Args:
            state: Current state (state_dim,)
            action_mask: Boolean mask of valid actions (action_dim,)
            training: Whether in training mode (affects exploration)

        Returns:
            Selected action index
        """
        # Exploration: random action
        if training and np.random.random() < self.epsilon:
            valid_actions = np.where(action_mask)[0]
            if len(valid_actions) == 0:
                return 0  # Fallback
            return np.random.choice(valid_actions)

        # Exploitation: best action according to Q-values
        state_tensor = torch.from_numpy(state).float().unsqueeze(0).to(self.device)
        mask_tensor = torch.from_numpy(action_mask).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action = self.online_network.get_best_action(state_tensor, mask_tensor)
            return action.item()

    def store_transition(self, state: np.ndarray, action: int, reward: float,
                         next_state: Optional[np.ndarray], done: bool) -> None:
        """Store transition in replay buffer and increment step counter."""
        self.replay_buffer.add(state, action, reward, next_state, done)
        self.total_steps += 1  # Count environment steps, not training steps

    def train_step(self) -> Optional[float]:
        """
        Perform one training step.

        Returns:
            Loss value if training occurred, None otherwise
        """
        # Check if we should train
        if not self.replay_buffer.is_ready(self.batch_size):
            return None

        if self.total_steps % self.train_freq != 0:
            return None

        # Sample batch from replay buffer
        states, actions, rewards, next_states, dones = self.replay_buffer.sample(self.batch_size)

        # Convert to tensors
        states = torch.from_numpy(states).float().to(self.device)
        actions = torch.from_numpy(actions).long().to(self.device)
        rewards = torch.from_numpy(rewards).float().to(self.device)
        next_states = torch.from_numpy(next_states).float().to(self.device)
        dones = torch.from_numpy(dones).float().to(self.device)

        # Compute Q-values for current states
        current_q_values = self.online_network(states)
        current_q = current_q_values.gather(1, actions.unsqueeze(1)).squeeze(1)

        # Compute TD targets
        with torch.no_grad():
            next_q_values = self.target_network(next_states)
            max_next_q = next_q_values.max(1)[0]
            target_q = rewards + (1 - dones) * self.gamma * max_next_q

        # Compute loss (Huber loss)
        loss = F.smooth_l1_loss(current_q, target_q)

        # Optimize
        self.optimizer.zero_grad()
        loss.backward()

        # Gradient clipping
        torch.nn.utils.clip_grad_norm_(self.online_network.parameters(), max_norm=10.0)

        self.optimizer.step()

        # Update target network
        if self.total_steps % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.online_network.state_dict())
            logger.debug(f"Updated target network at step {self.total_steps}")

        # Decay epsilon
        self.epsilon = max(
            self.epsilon_end,
            self.epsilon_start - (self.epsilon_start - self.epsilon_end) *
            min(self.total_steps / self.epsilon_decay, 1.0)
        )

        # Track metrics
        self.total_loss += loss.item()
        self.total_updates += 1

        return loss.item()

    def update_episode_count(self) -> None:
        """Increment episode counter."""
        self.episode_count += 1

    def get_epsilon(self) -> float:
        """Get current exploration rate."""
        return self.epsilon

    def get_avg_loss(self) -> float:
        """Get average training loss."""
        if self.total_updates == 0:
            return 0.0
        return self.total_loss / self.total_updates

    def save_checkpoint(self, filepath: str, episode: int, additional_info: dict = None) -> None:
        """
        Save training checkpoint.

        Args:
            filepath: Path to save checkpoint
            episode: Current episode number
            additional_info: Additional metadata to save
        """
        checkpoint = {
            'episode': episode,
            'online_network_state_dict': self.online_network.state_dict(),
            'target_network_state_dict': self.target_network.state_dict(),
            'optimizer_state_dict': self.optimizer.state_dict(),
            'epsilon': self.epsilon,
            'total_steps': self.total_steps,
            'total_updates': self.total_updates,
            'avg_loss': self.get_avg_loss(),
        }

        if additional_info:
            checkpoint.update(additional_info)

        torch.save(checkpoint, filepath)
        logger.info(f"Saved checkpoint to {filepath}")

    def load_checkpoint(self, filepath: str) -> dict:
        """
        Load training checkpoint.

        Args:
            filepath: Path to checkpoint file

        Returns:
            Checkpoint dictionary with metadata
        """
        checkpoint = torch.load(filepath, map_location=self.device)

        self.online_network.load_state_dict(checkpoint['online_network_state_dict'])
        self.target_network.load_state_dict(checkpoint['target_network_state_dict'])
        self.optimizer.load_state_dict(checkpoint['optimizer_state_dict'])
        self.epsilon = checkpoint['epsilon']
        self.total_steps = checkpoint['total_steps']
        self.total_updates = checkpoint['total_updates']

        logger.info(f"Loaded checkpoint from {filepath}")
        logger.info(f"  Episode: {checkpoint['episode']}")
        logger.info(f"  Epsilon: {self.epsilon:.3f}")
        logger.info(f"  Steps: {self.total_steps}")

        return checkpoint

    def set_eval_mode(self) -> None:
        """Set networks to evaluation mode (disables dropout, etc.)."""
        self.online_network.eval()
        self.target_network.eval()

    def set_train_mode(self) -> None:
        """Set online network to training mode."""
        self.online_network.train()
        # Target network stays in eval mode


# Convenience function
def create_trainer(device: str = "cuda" if torch.cuda.is_available() else "cpu") -> DQNTrainer:
    """Create DQN trainer with default settings."""
    return DQNTrainer(device=device)
