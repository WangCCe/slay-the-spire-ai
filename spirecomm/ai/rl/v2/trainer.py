"""
DQN trainer for RL v2 with embedding inputs.
"""

from typing import Optional
import logging

import numpy as np
import torch
import torch.nn.functional as F

from .network import create_dqn_v2
from .replay_buffer import ReplayBufferV2

logger = logging.getLogger(__name__)


class DQNTrainerV2:
    def __init__(
        self,
        continuous_dim: int,
        action_dim: int,
        card_slots: int,
        potion_slots: int,
        relic_slots: int,
        card_vocab: int,
        potion_vocab: int,
        relic_vocab: int,
        learning_rate: float = 1e-4,
        gamma: float = 0.99,
        buffer_size: int = 100000,
        batch_size: int = 128,
        target_update_freq: int = 2000,
        train_freq: int = 4,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: int = 25000,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        network_type: str = "dueling",
        card_embed_dim: int = 32,
        potion_embed_dim: int = 8,
        relic_embed_dim: int = 16,
    ):
        self.continuous_dim = continuous_dim
        self.action_dim = action_dim
        self.card_slots = card_slots
        self.potion_slots = potion_slots
        self.relic_slots = relic_slots
        self.gamma = gamma
        self.batch_size = batch_size
        self.target_update_freq = target_update_freq
        self.train_freq = train_freq
        self.device = device
        self.learning_rate = learning_rate
        self.network_type = network_type

        self.online_network = create_dqn_v2(
            network_type=network_type,
            continuous_dim=continuous_dim,
            action_dim=action_dim,
            card_vocab=card_vocab,
            potion_vocab=potion_vocab,
            relic_vocab=relic_vocab,
            device=device,
            card_embed_dim=card_embed_dim,
            potion_embed_dim=potion_embed_dim,
            relic_embed_dim=relic_embed_dim,
            card_slots=card_slots,
            potion_slots=potion_slots,
            relic_slots=relic_slots,
        )
        self.target_network = create_dqn_v2(
            network_type=network_type,
            continuous_dim=continuous_dim,
            action_dim=action_dim,
            card_vocab=card_vocab,
            potion_vocab=potion_vocab,
            relic_vocab=relic_vocab,
            device=device,
            card_embed_dim=card_embed_dim,
            potion_embed_dim=potion_embed_dim,
            relic_embed_dim=relic_embed_dim,
            card_slots=card_slots,
            potion_slots=potion_slots,
            relic_slots=relic_slots,
        )
        self.target_network.load_state_dict(self.online_network.state_dict())
        self.target_network.eval()

        self.optimizer = torch.optim.Adam(self.online_network.parameters(), lr=learning_rate)
        self.replay_buffer = ReplayBufferV2(
            buffer_size=buffer_size,
            continuous_dim=continuous_dim,
            action_dim=action_dim,
            card_slots=card_slots,
            potion_slots=potion_slots,
            relic_slots=relic_slots,
        )

        self.epsilon = epsilon_start
        self.epsilon_start = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.total_steps = 0
        self.episode_count = 0

    def select_action(
        self,
        continuous: np.ndarray,
        card_ids: np.ndarray,
        potion_ids: np.ndarray,
        relic_ids: np.ndarray,
        action_mask: np.ndarray,
        training: bool = True,
        epsilon_override: Optional[float] = None,
    ) -> int:
        epsilon = self.epsilon if epsilon_override is None else epsilon_override
        if training and np.random.random() < epsilon:
            valid_actions = np.where(action_mask)[0]
            if len(valid_actions) == 0:
                return 0
            return int(np.random.choice(valid_actions))

        continuous_tensor = torch.from_numpy(continuous).float().unsqueeze(0).to(self.device)
        card_tensor = torch.from_numpy(card_ids).long().unsqueeze(0).to(self.device)
        potion_tensor = torch.from_numpy(potion_ids).long().unsqueeze(0).to(self.device)
        relic_tensor = torch.from_numpy(relic_ids).long().unsqueeze(0).to(self.device)
        mask_tensor = torch.from_numpy(action_mask).unsqueeze(0).to(self.device)

        with torch.no_grad():
            action = self.online_network.get_best_action(
                continuous=continuous_tensor,
                card_ids=card_tensor,
                potion_ids=potion_tensor,
                relic_ids=relic_tensor,
                action_mask=mask_tensor,
            )
            return int(action.item())

    def store_transition(
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
    ) -> None:
        self.replay_buffer.add(
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
            action_mask=action_mask,
            next_action_mask=next_action_mask,
        )
        self.total_steps += 1

    def train_step(self) -> Optional[float]:
        if not self.replay_buffer.is_ready(self.batch_size):
            return None
        if self.total_steps % self.train_freq != 0:
            return None

        (
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
        ) = self.replay_buffer.sample(self.batch_size)

        continuous = torch.from_numpy(continuous).float().to(self.device)
        card_ids = torch.from_numpy(card_ids).long().to(self.device)
        potion_ids = torch.from_numpy(potion_ids).long().to(self.device)
        relic_ids = torch.from_numpy(relic_ids).long().to(self.device)
        actions = torch.from_numpy(actions).long().to(self.device)
        rewards = torch.from_numpy(rewards).float().to(self.device)
        next_continuous = torch.from_numpy(next_continuous).float().to(self.device)
        next_card_ids = torch.from_numpy(next_card_ids).long().to(self.device)
        next_potion_ids = torch.from_numpy(next_potion_ids).long().to(self.device)
        next_relic_ids = torch.from_numpy(next_relic_ids).long().to(self.device)
        dones = torch.from_numpy(dones).float().to(self.device)
        action_masks = torch.from_numpy(action_masks).to(self.device)
        next_action_masks = torch.from_numpy(next_action_masks).to(self.device)

        current_q = self.online_network(
            continuous=continuous,
            card_ids=card_ids,
            potion_ids=potion_ids,
            relic_ids=relic_ids,
            action_mask=action_masks,
        )
        current_q = current_q.gather(1, actions.unsqueeze(1)).squeeze(1)

        with torch.no_grad():
            next_online_q = self.online_network(
                continuous=next_continuous,
                card_ids=next_card_ids,
                potion_ids=next_potion_ids,
                relic_ids=next_relic_ids,
                action_mask=next_action_masks,
            )
            next_actions = next_online_q.argmax(dim=1, keepdim=True)
            next_target_q = self.target_network(
                continuous=next_continuous,
                card_ids=next_card_ids,
                potion_ids=next_potion_ids,
                relic_ids=next_relic_ids,
                action_mask=next_action_masks,
            )
            next_q = next_target_q.gather(1, next_actions).squeeze(1)
            target_q = rewards + (1 - dones) * self.gamma * next_q

        loss = F.smooth_l1_loss(current_q, target_q)

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_network.parameters(), max_norm=10.0)
        self.optimizer.step()

        if self.total_steps % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.online_network.state_dict())

        self.epsilon = max(
            self.epsilon_end,
            self.epsilon_start
            - (self.epsilon_start - self.epsilon_end) * min(self.total_steps / self.epsilon_decay, 1.0),
        )

        return float(loss.item())

    def update_episode_count(self) -> None:
        self.episode_count += 1
