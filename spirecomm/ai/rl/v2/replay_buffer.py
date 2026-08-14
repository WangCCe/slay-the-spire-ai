"""
Replay buffer for RL v2 with embedding inputs.
"""

import random
from typing import Tuple
import numpy as np


class ReplayBufferV2:
    def __init__(
        self,
        buffer_size: int,
        continuous_dim: int,
        action_dim: int,
        card_slots: int,
        potion_slots: int,
        relic_slots: int,
    ):
        self.buffer_size = buffer_size
        self.continuous_dim = continuous_dim
        self.action_dim = action_dim
        self.card_slots = card_slots
        self.potion_slots = potion_slots
        self.relic_slots = relic_slots
        self.buffer = []
        self.position = 0

    def add(
        self,
        continuous: np.ndarray,
        card_ids: np.ndarray,
        potion_ids: np.ndarray,
        relic_ids: np.ndarray,
        action: int,
        reward: float,
        next_continuous: np.ndarray,
        next_card_ids: np.ndarray,
        next_potion_ids: np.ndarray,
        next_relic_ids: np.ndarray,
        done: bool,
        action_mask: np.ndarray = None,
        next_action_mask: np.ndarray = None,
    ) -> bool:
        if continuous is not None and len(continuous) != self.continuous_dim:
            return False
        if next_continuous is not None and len(next_continuous) != self.continuous_dim:
            return False
        if card_ids is not None and len(card_ids) != self.card_slots:
            return False
        if potion_ids is not None and len(potion_ids) != self.potion_slots:
            return False
        if relic_ids is not None and len(relic_ids) != self.relic_slots:
            return False
        if action_mask is not None and len(action_mask) != self.action_dim:
            return False
        if next_action_mask is not None and len(next_action_mask) != self.action_dim:
            return False

        transition = (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action,
            reward,
            next_continuous,
            next_card_ids,
            next_potion_ids,
            next_relic_ids,
            done,
            action_mask,
            next_action_mask,
        )

        if len(self.buffer) < self.buffer_size:
            self.buffer.append(transition)
        else:
            self.buffer[self.position] = transition

        self.position = (self.position + 1) % self.buffer_size
        return True

    def sample(self, batch_size: int) -> Tuple[np.ndarray, ...]:
        if len(self.buffer) < batch_size:
            raise ValueError("Not enough transitions in buffer.")

        transitions = random.sample(self.buffer, batch_size)
        continuous = np.array([t[0] for t in transitions], dtype=np.float32)
        card_ids = np.array([t[1] for t in transitions], dtype=np.int64)
        potion_ids = np.array([t[2] for t in transitions], dtype=np.int64)
        relic_ids = np.array([t[3] for t in transitions], dtype=np.int64)
        actions = np.array([t[4] for t in transitions], dtype=np.int64)
        rewards = np.array([t[5] for t in transitions], dtype=np.float32)
        next_continuous = np.array(
            [t[6] if t[6] is not None else np.zeros(self.continuous_dim) for t in transitions],
            dtype=np.float32,
        )
        next_card_ids = np.array(
            [t[7] if t[7] is not None else np.zeros(self.card_slots) for t in transitions],
            dtype=np.int64,
        )
        next_potion_ids = np.array(
            [t[8] if t[8] is not None else np.zeros(self.potion_slots) for t in transitions],
            dtype=np.int64,
        )
        next_relic_ids = np.array(
            [t[9] if t[9] is not None else np.zeros(self.relic_slots) for t in transitions],
            dtype=np.int64,
        )
        dones = np.array([t[10] for t in transitions], dtype=np.float32)
        action_masks = np.array(
            [t[11] if t[11] is not None else np.ones(self.action_dim, dtype=bool) for t in transitions],
            dtype=bool,
        )
        next_action_masks = np.array(
            [t[12] if t[12] is not None else np.ones(self.action_dim, dtype=bool) for t in transitions],
            dtype=bool,
        )

        return (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            actions,
            rewards,
            next_continuous,
            next_card_ids,
            next_potion_ids,
            next_relic_ids,
            dones,
            action_masks,
            next_action_masks,
        )

    def is_ready(self, batch_size: int) -> bool:
        return len(self.buffer) >= batch_size
