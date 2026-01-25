"""
Replay buffer for experience storage and sampling in DQN training.

Stores and samples transitions (state, action, reward, next_state, done) for off-policy learning.
"""

import random
from typing import List, Tuple
import numpy as np


class ReplayBuffer:
    """
    Experience replay buffer for DQN training.

    Stores up to buffer_size transitions and samples uniform random batches.
    """

    def __init__(self, buffer_size: int = 100000, state_dim: int = 512, action_dim: int = 1000):
        """
        Initialize replay buffer.

        Args:
            buffer_size: Maximum number of transitions to store
            state_dim: Dimension of state vectors (default 512)
        """
        self.buffer_size = buffer_size
        self.state_dim = state_dim
        self.action_dim = action_dim
        self.buffer = []
        self.position = 0

    def add(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool,
        action_mask: np.ndarray = None,
        next_action_mask: np.ndarray = None,
    ) -> None:
        """
        Add a transition to the buffer.

        Args:
            state: Current state (512-dim vector)
            action: Action taken (0-999)
            reward: Reward received
            next_state: Next state (512-dim vector), None if terminal
            done: Whether episode ended
        """
        # Validate state dimension
        if state is not None and len(state) != self.state_dim:
            import logging
            logging.warning(
                f"State dimension mismatch! Expected {self.state_dim}, got {len(state)}. "
                f"Skipping this transition to prevent buffer corruption."
            )
            return

        # Validate next_state dimension
        if next_state is not None and len(next_state) != self.state_dim:
            import logging
            logging.warning(
                f"Next state dimension mismatch! Expected {self.state_dim}, got {len(next_state)}. "
                f"Skipping this transition to prevent buffer corruption."
            )
            return

        # Validate action mask dimension if provided
        if action_mask is not None and len(action_mask) != self.action_dim:
            import logging
            logging.warning(
                f"Action mask dimension mismatch! Expected {self.action_dim}, got {len(action_mask)}. "
                f"Skipping this transition to prevent buffer corruption."
            )
            return

        if next_action_mask is not None and len(next_action_mask) != self.action_dim:
            import logging
            logging.warning(
                f"Next action mask dimension mismatch! Expected {self.action_dim}, got {len(next_action_mask)}. "
                f"Skipping this transition to prevent buffer corruption."
            )
            return

        transition = (state, action, reward, next_state, done, action_mask, next_action_mask)

        if len(self.buffer) < self.buffer_size:
            self.buffer.append(transition)
        else:
            # Overwrite oldest transition (FIFO policy)
            self.buffer[self.position] = transition

        self.position = (self.position + 1) % self.buffer_size

    def sample(
        self, batch_size: int
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """
        Sample a batch of transitions uniformly at random.

        Args:
            batch_size: Number of transitions to sample

        Returns:
            Tuple of (states, actions, rewards, next_states, dones) as numpy arrays
        """
        if len(self.buffer) < batch_size:
            raise ValueError(f"Not enough transitions in buffer. Have {len(self.buffer)}, need {batch_size}")

        transitions = random.sample(self.buffer, batch_size)

        # Unpack transitions
        states = np.array([t[0] for t in transitions], dtype=np.float32)
        actions = np.array([t[1] for t in transitions], dtype=np.int64)
        rewards = np.array([t[2] for t in transitions], dtype=np.float32)
        next_states = np.array(
            [t[3] if t[3] is not None else np.zeros(self.state_dim) for t in transitions],
            dtype=np.float32
        )
        dones = np.array([t[4] for t in transitions], dtype=np.float32)
        action_masks = np.array(
            [t[5] if t[5] is not None else np.ones(self.action_dim, dtype=bool) for t in transitions],
            dtype=bool
        )
        next_action_masks = np.array(
            [t[6] if t[6] is not None else np.ones(self.action_dim, dtype=bool) for t in transitions],
            dtype=bool
        )

        return states, actions, rewards, next_states, dones, action_masks, next_action_masks

    def __len__(self) -> int:
        """Return current buffer size."""
        return len(self.buffer)

    def is_ready(self, batch_size: int) -> bool:
        """Check if buffer has enough samples for training."""
        return len(self.buffer) >= batch_size

    def clear(self) -> None:
        """Clear all transitions from buffer."""
        self.buffer = []
        self.position = 0

    def save(self, filepath: str) -> None:
        """
        Save buffer to disk.

        Args:
            filepath: Path to save file (.npz)
        """
        if len(self.buffer) == 0:
            return

        states = np.array([t[0] for t in self.buffer])
        actions = np.array([t[1] for t in self.buffer])
        rewards = np.array([t[2] for t in self.buffer])
        next_states = np.array(
            [t[3] if t[3] is not None else np.zeros(self.state_dim) for t in self.buffer]
        )
        dones = np.array([t[4] for t in self.buffer])
        action_masks = np.array(
            [t[5] if t[5] is not None else np.ones(self.action_dim, dtype=bool) for t in self.buffer]
        )
        next_action_masks = np.array(
            [t[6] if t[6] is not None else np.ones(self.action_dim, dtype=bool) for t in self.buffer]
        )

        np.savez_compressed(
            filepath,
            states=states,
            actions=actions,
            rewards=rewards,
            next_states=next_states,
            dones=dones,
            action_masks=action_masks,
            next_action_masks=next_action_masks,
        )

    def load(self, filepath: str) -> None:
        """
        Load buffer from disk.

        Args:
            filepath: Path to load file (.npz)
        """
        data = np.load(filepath)

        num_transitions = len(data['states'])
        has_masks = 'action_masks' in data and 'next_action_masks' in data
        for i in range(num_transitions):
            next_state = data['next_states'][i]
            # Check if next_state is all zeros (terminal state)
            if np.all(next_state == 0):
                next_state = None

            self.add(
                data['states'][i],
                int(data['actions'][i]),
                float(data['rewards'][i]),
                next_state,
                bool(data['dones'][i]),
                data['action_masks'][i] if has_masks else None,
                data['next_action_masks'][i] if has_masks else None,
            )
