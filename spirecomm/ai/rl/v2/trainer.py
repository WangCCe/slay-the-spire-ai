"""
DQN trainer for RL v2 with embedding inputs.
"""

from typing import Mapping, Optional
import copy
from collections import deque
import logging

import numpy as np
import torch
import torch.nn.functional as F

from .network import create_dqn_v2
from .replay_buffer import ReplayBufferV2
from .action_space import END_TURN_ACTION, PLAY_CARD_COUNT, PLAY_CARD_OFFSET
from .state_encoder import StateEncoderV2

logger = logging.getLogger(__name__)


def parent_end_turn_margin_guard_loss(
    current_q_values: torch.Tensor,
    parent_q_values: torch.Tensor,
    action_masks: torch.Tensor,
    *,
    margin_cap: float,
) -> tuple[torch.Tensor, int, int]:
    if current_q_values.shape != parent_q_values.shape:
        raise ValueError("candidate and parent Q shapes must match")
    if current_q_values.shape != action_masks.shape or current_q_values.ndim != 2:
        raise ValueError("Q values and action masks must be matching matrices")
    if current_q_values.shape[1] <= END_TURN_ACTION:
        raise ValueError("Q values do not include end-turn action")
    if not np.isfinite(margin_cap) or margin_cap <= 0.0:
        raise ValueError("parent end-turn margin guard cap must be finite and positive")

    masks = action_masks.bool()
    if not bool(masks.any(dim=1).all()):
        raise ValueError("parent end-turn margin guard requires a valid action per row")
    masked_parent_q = parent_q_values.masked_fill(~masks, float("-inf"))
    parent_actions = masked_parent_q.argmax(dim=1)
    row_indices = torch.arange(current_q_values.shape[0], device=current_q_values.device)
    parent_selected_q = masked_parent_q[row_indices, parent_actions]
    parent_end_turn_q = masked_parent_q[:, END_TURN_ACTION]
    parent_margins = parent_selected_q - parent_end_turn_q
    eligible = (
        masks[:, END_TURN_ACTION]
        & (parent_actions != END_TURN_ACTION)
        & torch.isfinite(parent_margins)
        & (parent_margins > 0.0)
    )
    eligible_count = int(eligible.sum().item())
    if not eligible_count:
        finite_q = torch.where(
            torch.isfinite(current_q_values),
            current_q_values,
            torch.zeros_like(current_q_values),
        )
        return finite_q.sum() * 0.0, 0, 0

    eligible_rows = row_indices[eligible]
    eligible_parent_actions = parent_actions[eligible]
    candidate_selected_q = current_q_values[
        eligible_rows, eligible_parent_actions
    ]
    candidate_end_turn_q = current_q_values[eligible, END_TURN_ACTION]
    candidate_margins = candidate_selected_q - candidate_end_turn_q
    if not bool(torch.isfinite(candidate_margins).all()):
        raise ValueError("eligible candidate end-turn margins must be finite")
    required_margins = parent_margins[eligible].clamp(max=float(margin_cap))
    ranking_violation_count = int((candidate_margins < 0.0).sum().item())
    loss = F.relu(required_margins - candidate_margins).mean()
    return loss, eligible_count, ranking_violation_count


def parent_card_ranking_guard_loss(
    current_q_values: torch.Tensor,
    parent_q_values: torch.Tensor,
    action_masks: torch.Tensor,
    *,
    margin_cap: float,
) -> tuple[torch.Tensor, int, int]:
    if current_q_values.shape != parent_q_values.shape:
        raise ValueError("candidate and parent Q shapes must match")
    if current_q_values.shape != action_masks.shape or current_q_values.ndim != 2:
        raise ValueError("Q values and action masks must be matching matrices")
    card_end = PLAY_CARD_OFFSET + PLAY_CARD_COUNT
    if current_q_values.shape[1] < card_end:
        raise ValueError("Q values do not include every play-card action")
    if not np.isfinite(margin_cap) or margin_cap <= 0.0:
        raise ValueError("parent card-ranking guard cap must be finite and positive")

    card_masks = action_masks[:, PLAY_CARD_OFFSET:card_end].bool()
    masked_parent_card_q = parent_q_values[:, PLAY_CARD_OFFSET:card_end].masked_fill(
        ~card_masks, float("-inf")
    )
    parent_top_two = torch.topk(masked_parent_card_q, k=2, dim=1)
    parent_best_card_actions = parent_top_two.indices[:, 0]
    parent_margins = parent_top_two.values[:, 0] - parent_top_two.values[:, 1]
    eligible = (
        (card_masks.sum(dim=1) >= 2)
        & torch.isfinite(parent_margins)
        & (parent_margins > 0.0)
    )
    eligible_count = int(eligible.sum().item())
    if not eligible_count:
        finite_q = torch.where(
            torch.isfinite(current_q_values),
            current_q_values,
            torch.zeros_like(current_q_values),
        )
        return finite_q.sum() * 0.0, 0, 0

    candidate_card_q = current_q_values[:, PLAY_CARD_OFFSET:card_end].masked_fill(
        ~card_masks, float("-inf")
    )
    candidate_parent_best_q = candidate_card_q.gather(
        1, parent_best_card_actions.unsqueeze(1)
    ).squeeze(1)
    candidate_alternative_q = candidate_card_q.clone()
    candidate_alternative_q.scatter_(
        1,
        parent_best_card_actions.unsqueeze(1),
        float("-inf"),
    )
    candidate_margins = (
        candidate_parent_best_q - candidate_alternative_q.max(dim=1).values
    )[eligible]
    if not bool(torch.isfinite(candidate_margins).all()):
        raise ValueError("eligible candidate card-ranking margins must be finite")
    required_margins = parent_margins[eligible].clamp(max=float(margin_cap))
    ranking_violation_count = int((candidate_margins < 0.0).sum().item())
    loss = F.relu(required_margins - candidate_margins).mean()
    return loss, eligible_count, ranking_violation_count


def parent_top_action_margin_guard_loss(
    current_q_values: torch.Tensor,
    parent_q_values: torch.Tensor,
    action_masks: torch.Tensor,
    *,
    margin_cap: float,
) -> tuple[torch.Tensor, int, int]:
    if current_q_values.shape != parent_q_values.shape:
        raise ValueError("candidate and parent Q shapes must match")
    if current_q_values.shape != action_masks.shape or current_q_values.ndim != 2:
        raise ValueError("Q values and action masks must be matching matrices")
    if current_q_values.shape[1] < 2:
        raise ValueError("top-action margin guard requires at least two actions")
    if not np.isfinite(margin_cap) or margin_cap <= 0.0:
        raise ValueError("parent top-action margin guard cap must be finite and positive")

    masks = action_masks.bool()
    masked_parent_q = parent_q_values.masked_fill(~masks, float("-inf"))
    parent_top_two = torch.topk(masked_parent_q, k=2, dim=1)
    parent_best_actions = parent_top_two.indices[:, 0]
    parent_margins = parent_top_two.values[:, 0] - parent_top_two.values[:, 1]
    eligible = (
        (masks.sum(dim=1) >= 2)
        & torch.isfinite(parent_margins)
        & (parent_margins > 0.0)
    )
    eligible_count = int(eligible.sum().item())
    if not eligible_count:
        finite_q = torch.where(
            torch.isfinite(current_q_values),
            current_q_values,
            torch.zeros_like(current_q_values),
        )
        return finite_q.sum() * 0.0, 0, 0

    candidate_q = current_q_values.masked_fill(~masks, float("-inf"))
    candidate_parent_best_q = candidate_q.gather(
        1, parent_best_actions.unsqueeze(1)
    ).squeeze(1)
    candidate_alternative_q = candidate_q.clone()
    candidate_alternative_q.scatter_(
        1,
        parent_best_actions.unsqueeze(1),
        float("-inf"),
    )
    candidate_margins = (
        candidate_parent_best_q - candidate_alternative_q.max(dim=1).values
    )[eligible]
    if not bool(torch.isfinite(candidate_margins).all()):
        raise ValueError("eligible candidate top-action margins must be finite")
    required_margins = parent_margins[eligible].clamp(max=float(margin_cap))
    ranking_violation_count = int((candidate_margins < 0.0).sum().item())
    loss = F.relu(required_margins - candidate_margins).mean()
    return loss, eligible_count, ranking_violation_count


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
        learning_starts: int = None,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.05,
        epsilon_decay: int = 100000,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
        network_type: str = "dueling",
        card_embed_dim: int = 32,
        potion_embed_dim: int = 8,
        relic_embed_dim: int = 16,
        parent_policy_anchor_weight: float = 0.0,
        parent_end_turn_margin_guard_weight: float = 0.0,
        parent_end_turn_margin_guard_cap: float = 0.1,
        positive_energy_action_imitation_weight: float = 0.0,
        positive_energy_parent_end_turn_imitation_weight: float = 0.0,
        parent_card_ranking_guard_weight: float = 0.0,
        parent_card_ranking_guard_cap: float = 0.1,
        parent_top_action_margin_guard_weight: float = 0.0,
        parent_top_action_margin_guard_cap: float = 0.1,
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
        self.learning_starts = max(
            int(batch_size if learning_starts is None else learning_starts),
            int(batch_size),
        )
        self.device = device
        self.learning_rate = learning_rate
        self.network_type = network_type
        if not np.isfinite(parent_policy_anchor_weight) or parent_policy_anchor_weight < 0:
            raise ValueError("parent_policy_anchor_weight must be finite and non-negative")
        self.parent_policy_anchor_weight = float(parent_policy_anchor_weight)
        if (
            not np.isfinite(parent_end_turn_margin_guard_weight)
            or parent_end_turn_margin_guard_weight < 0.0
        ):
            raise ValueError(
                "parent end-turn margin guard weight must be finite and non-negative"
            )
        if (
            not np.isfinite(parent_end_turn_margin_guard_cap)
            or parent_end_turn_margin_guard_cap < 0.0
        ):
            raise ValueError(
                "parent end-turn margin guard cap must be finite and non-negative"
            )
        if (
            parent_end_turn_margin_guard_weight > 0.0
            and parent_end_turn_margin_guard_cap <= 0.0
        ):
            raise ValueError(
                "positive parent end-turn margin guard weight requires a positive cap"
            )
        self.parent_end_turn_margin_guard_weight = float(
            parent_end_turn_margin_guard_weight
        )
        self.parent_end_turn_margin_guard_cap = float(
            parent_end_turn_margin_guard_cap
        )
        if (
            not np.isfinite(parent_card_ranking_guard_weight)
            or parent_card_ranking_guard_weight < 0.0
        ):
            raise ValueError(
                "parent card-ranking guard weight must be finite and non-negative"
            )
        if (
            not np.isfinite(parent_card_ranking_guard_cap)
            or parent_card_ranking_guard_cap < 0.0
        ):
            raise ValueError(
                "parent card-ranking guard cap must be finite and non-negative"
            )
        if (
            parent_card_ranking_guard_weight > 0.0
            and parent_card_ranking_guard_cap <= 0.0
        ):
            raise ValueError(
                "positive parent card-ranking guard weight requires a positive cap"
            )
        self.parent_card_ranking_guard_weight = float(
            parent_card_ranking_guard_weight
        )
        self.parent_card_ranking_guard_cap = float(parent_card_ranking_guard_cap)
        if (
            not np.isfinite(parent_top_action_margin_guard_weight)
            or parent_top_action_margin_guard_weight < 0.0
        ):
            raise ValueError(
                "parent top-action margin guard weight must be finite and non-negative"
            )
        if (
            not np.isfinite(parent_top_action_margin_guard_cap)
            or parent_top_action_margin_guard_cap < 0.0
        ):
            raise ValueError(
                "parent top-action margin guard cap must be finite and non-negative"
            )
        if (
            parent_top_action_margin_guard_weight > 0.0
            and parent_top_action_margin_guard_cap <= 0.0
        ):
            raise ValueError(
                "positive parent top-action margin guard weight requires a positive cap"
            )
        self.parent_top_action_margin_guard_weight = float(
            parent_top_action_margin_guard_weight
        )
        self.parent_top_action_margin_guard_cap = float(
            parent_top_action_margin_guard_cap
        )
        if (
            not np.isfinite(positive_energy_action_imitation_weight)
            or positive_energy_action_imitation_weight < 0
        ):
            raise ValueError(
                "positive_energy_action_imitation_weight must be finite and non-negative"
            )
        self.positive_energy_action_imitation_weight = float(
            positive_energy_action_imitation_weight
        )
        if (
            not np.isfinite(positive_energy_parent_end_turn_imitation_weight)
            or positive_energy_parent_end_turn_imitation_weight < 0
        ):
            raise ValueError(
                "positive_energy_parent_end_turn_imitation_weight must be "
                "finite and non-negative"
            )
        self.positive_energy_parent_end_turn_imitation_weight = float(
            positive_energy_parent_end_turn_imitation_weight
        )
        if (
            self.positive_energy_action_imitation_weight > 0.0
            and self.positive_energy_parent_end_turn_imitation_weight > 0.0
        ):
            raise ValueError("positive-energy imitation objectives are mutually exclusive")
        if (
            self.positive_energy_parent_end_turn_imitation_weight > 0.0
            and self.parent_policy_anchor_weight <= 0.0
        ):
            raise ValueError(
                "parent-EndTurn imitation requires a positive parent policy anchor weight"
            )

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
        self.parent_policy_anchor_network = None
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
        self.loss_history = deque(maxlen=100)
        self.last_loss = None
        self.last_td_loss = None
        self.last_parent_policy_anchor_loss = 0.0
        self.last_parent_end_turn_margin_guard_loss = 0.0
        self.last_parent_end_turn_margin_guard_eligible_count = 0
        self.last_parent_end_turn_margin_guard_ranking_violation_count = 0
        self.last_parent_card_ranking_guard_loss = 0.0
        self.last_parent_card_ranking_guard_eligible_count = 0
        self.last_parent_card_ranking_guard_ranking_violation_count = 0
        self.last_parent_top_action_margin_guard_loss = 0.0
        self.last_parent_top_action_margin_guard_eligible_count = 0
        self.last_parent_top_action_margin_guard_ranking_violation_count = 0
        self.last_positive_energy_action_imitation_loss = 0.0
        self.last_positive_energy_action_imitation_count = 0
        self.last_positive_energy_parent_end_turn_imitation_loss = 0.0
        self.last_positive_energy_parent_end_turn_imitation_count = 0

    def set_parent_policy_anchor(self, state_dict: Mapping[str, torch.Tensor]) -> None:
        if (
            self.parent_policy_anchor_weight <= 0.0
            and self.parent_end_turn_margin_guard_weight <= 0.0
            and self.parent_card_ranking_guard_weight <= 0.0
            and self.parent_top_action_margin_guard_weight <= 0.0
        ):
            raise ValueError("a frozen-parent objective weight must be positive")
        anchor = copy.deepcopy(self.online_network)
        anchor.load_state_dict(state_dict)
        anchor.eval()
        for parameter in anchor.parameters():
            parameter.requires_grad_(False)
        self.parent_policy_anchor_network = anchor

    def get_parent_policy_anchor_actions(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
    ) -> torch.Tensor:
        _anchor_q, anchor_actions = self.get_parent_policy_anchor_q_and_actions(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
        )
        return anchor_actions

    def get_parent_policy_anchor_q_and_actions(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
    ) -> tuple[torch.Tensor, torch.Tensor]:
        if self.parent_policy_anchor_network is None:
            raise RuntimeError("parent policy anchor network is not initialized")
        if not bool(action_masks.any(dim=1).all()):
            raise ValueError("parent policy anchor requires at least one valid action")
        with torch.no_grad():
            anchor_q = self.parent_policy_anchor_network(
                continuous=continuous,
                card_ids=card_ids,
                potion_ids=potion_ids,
                relic_ids=relic_ids,
                action_mask=action_masks,
            )
            return anchor_q, anchor_q.argmax(dim=1)

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
    ) -> bool:
        accepted = self.replay_buffer.add(
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
        if accepted:
            self.total_steps += 1
        return accepted

    def train_step(self) -> Optional[float]:
        if len(self.replay_buffer) < self.learning_starts:
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

        current_q_values = self.online_network(
            continuous=continuous,
            card_ids=card_ids,
            potion_ids=potion_ids,
            relic_ids=relic_ids,
            action_mask=action_masks,
        )
        current_q = current_q_values.gather(1, actions.unsqueeze(1)).squeeze(1)

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
            next_q = torch.where(dones.bool(), torch.zeros_like(next_q), next_q)
            target_q = rewards + (1 - dones) * self.gamma * next_q

        td_loss = F.smooth_l1_loss(current_q, target_q)
        anchor_loss = torch.zeros((), dtype=td_loss.dtype, device=self.device)
        anchor_q = None
        anchor_actions = None
        if (
            self.parent_policy_anchor_weight > 0.0
            or self.parent_end_turn_margin_guard_weight > 0.0
            or self.parent_card_ranking_guard_weight > 0.0
            or self.parent_top_action_margin_guard_weight > 0.0
        ):
            anchor_q, anchor_actions = self.get_parent_policy_anchor_q_and_actions(
                continuous,
                card_ids,
                potion_ids,
                relic_ids,
                action_masks,
            )
        if self.parent_policy_anchor_weight > 0.0:
            anchor_loss = F.cross_entropy(current_q_values, anchor_actions)
        parent_end_turn_margin_guard_loss_value = torch.zeros(
            (), dtype=td_loss.dtype, device=self.device
        )
        parent_end_turn_margin_guard_eligible_count = 0
        parent_end_turn_margin_guard_ranking_violation_count = 0
        if self.parent_end_turn_margin_guard_weight > 0.0:
            if anchor_q is None:
                raise RuntimeError("parent end-turn margin guard requires parent Q values")
            (
                parent_end_turn_margin_guard_loss_value,
                parent_end_turn_margin_guard_eligible_count,
                parent_end_turn_margin_guard_ranking_violation_count,
            ) = parent_end_turn_margin_guard_loss(
                current_q_values,
                anchor_q,
                action_masks,
                margin_cap=self.parent_end_turn_margin_guard_cap,
            )
        parent_card_ranking_guard_loss_value = torch.zeros(
            (), dtype=td_loss.dtype, device=self.device
        )
        parent_card_ranking_guard_eligible_count = 0
        parent_card_ranking_guard_ranking_violation_count = 0
        if self.parent_card_ranking_guard_weight > 0.0:
            if anchor_q is None:
                raise RuntimeError("parent card-ranking guard requires parent Q values")
            (
                parent_card_ranking_guard_loss_value,
                parent_card_ranking_guard_eligible_count,
                parent_card_ranking_guard_ranking_violation_count,
            ) = parent_card_ranking_guard_loss(
                current_q_values,
                anchor_q,
                action_masks,
                margin_cap=self.parent_card_ranking_guard_cap,
            )
        parent_top_action_margin_guard_loss_value = torch.zeros(
            (), dtype=td_loss.dtype, device=self.device
        )
        parent_top_action_margin_guard_eligible_count = 0
        parent_top_action_margin_guard_ranking_violation_count = 0
        if self.parent_top_action_margin_guard_weight > 0.0:
            if anchor_q is None:
                raise RuntimeError("parent top-action margin guard requires parent Q values")
            (
                parent_top_action_margin_guard_loss_value,
                parent_top_action_margin_guard_eligible_count,
                parent_top_action_margin_guard_ranking_violation_count,
            ) = parent_top_action_margin_guard_loss(
                current_q_values,
                anchor_q,
                action_masks,
                margin_cap=self.parent_top_action_margin_guard_cap,
            )
        positive_energy_action_imitation_loss = torch.zeros(
            (), dtype=td_loss.dtype, device=self.device
        )
        positive_energy_action_imitation_count = 0
        if self.positive_energy_action_imitation_weight > 0.0:
            eligible = (
                continuous[:, StateEncoderV2.ENERGY_RATIO_INDEX] > 0.0
            ) & (actions != END_TURN_ACTION)
            positive_energy_action_imitation_count = int(eligible.sum().item())
            if positive_energy_action_imitation_count:
                positive_energy_action_imitation_loss = F.cross_entropy(
                    current_q_values[eligible], actions[eligible]
                )
        positive_energy_parent_end_turn_imitation_loss = torch.zeros(
            (), dtype=td_loss.dtype, device=self.device
        )
        positive_energy_parent_end_turn_imitation_count = 0
        if self.positive_energy_parent_end_turn_imitation_weight > 0.0:
            if anchor_actions is None:
                raise RuntimeError("parent-EndTurn imitation requires anchor actions")
            eligible = (
                (continuous[:, StateEncoderV2.ENERGY_RATIO_INDEX] > 0.0)
                & (actions != END_TURN_ACTION)
                & (anchor_actions == END_TURN_ACTION)
            )
            positive_energy_parent_end_turn_imitation_count = int(
                eligible.sum().item()
            )
            if positive_energy_parent_end_turn_imitation_count:
                positive_energy_parent_end_turn_imitation_loss = F.cross_entropy(
                    current_q_values[eligible], actions[eligible]
                )
        loss = (
            td_loss
            + self.parent_policy_anchor_weight * anchor_loss
            + self.parent_end_turn_margin_guard_weight
            * parent_end_turn_margin_guard_loss_value
            + self.parent_card_ranking_guard_weight
            * parent_card_ranking_guard_loss_value
            + self.parent_top_action_margin_guard_weight
            * parent_top_action_margin_guard_loss_value
            + self.positive_energy_action_imitation_weight
            * positive_energy_action_imitation_loss
            + self.positive_energy_parent_end_turn_imitation_weight
            * positive_energy_parent_end_turn_imitation_loss
        )
        loss_value = float(loss.item())
        self.last_td_loss = float(td_loss.item())
        self.last_parent_policy_anchor_loss = float(anchor_loss.item())
        self.last_parent_end_turn_margin_guard_loss = float(
            parent_end_turn_margin_guard_loss_value.item()
        )
        self.last_parent_end_turn_margin_guard_eligible_count = (
            parent_end_turn_margin_guard_eligible_count
        )
        self.last_parent_end_turn_margin_guard_ranking_violation_count = (
            parent_end_turn_margin_guard_ranking_violation_count
        )
        self.last_parent_card_ranking_guard_loss = float(
            parent_card_ranking_guard_loss_value.item()
        )
        self.last_parent_card_ranking_guard_eligible_count = (
            parent_card_ranking_guard_eligible_count
        )
        self.last_parent_card_ranking_guard_ranking_violation_count = (
            parent_card_ranking_guard_ranking_violation_count
        )
        self.last_parent_top_action_margin_guard_loss = float(
            parent_top_action_margin_guard_loss_value.item()
        )
        self.last_parent_top_action_margin_guard_eligible_count = (
            parent_top_action_margin_guard_eligible_count
        )
        self.last_parent_top_action_margin_guard_ranking_violation_count = (
            parent_top_action_margin_guard_ranking_violation_count
        )
        self.last_positive_energy_action_imitation_loss = float(
            positive_energy_action_imitation_loss.item()
        )
        self.last_positive_energy_action_imitation_count = (
            positive_energy_action_imitation_count
        )
        self.last_positive_energy_parent_end_turn_imitation_loss = float(
            positive_energy_parent_end_turn_imitation_loss.item()
        )
        self.last_positive_energy_parent_end_turn_imitation_count = (
            positive_energy_parent_end_turn_imitation_count
        )
        self.loss_history.append(loss_value)
        self.last_loss = loss_value

        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.online_network.parameters(), max_norm=10.0)
        self.optimizer.step()

        if self.parent_policy_anchor_weight > 0.0 and self.total_steps % 100 == 0:
            logger.info(
                "RL parent policy anchor update: total_steps=%s total_loss=%.6f "
                "td_loss=%.6f anchor_loss=%.6f weight=%.6f",
                self.total_steps,
                loss_value,
                self.last_td_loss,
                self.last_parent_policy_anchor_loss,
                self.parent_policy_anchor_weight,
            )

        if (
            self.parent_end_turn_margin_guard_weight > 0.0
            and self.total_steps % 100 == 0
        ):
            logger.info(
                "RL parent end-turn margin guard update: total_steps=%s "
                "loss=%.6f weight=%.6f cap=%.6f eligible=%s violations=%s",
                self.total_steps,
                self.last_parent_end_turn_margin_guard_loss,
                self.parent_end_turn_margin_guard_weight,
                self.parent_end_turn_margin_guard_cap,
                self.last_parent_end_turn_margin_guard_eligible_count,
                self.last_parent_end_turn_margin_guard_ranking_violation_count,
            )

        if (
            self.parent_card_ranking_guard_weight > 0.0
            and self.total_steps % 100 == 0
        ):
            logger.info(
                "RL parent card-ranking guard update: total_steps=%s "
                "loss=%.6f weight=%.6f cap=%.6f eligible=%s violations=%s",
                self.total_steps,
                self.last_parent_card_ranking_guard_loss,
                self.parent_card_ranking_guard_weight,
                self.parent_card_ranking_guard_cap,
                self.last_parent_card_ranking_guard_eligible_count,
                self.last_parent_card_ranking_guard_ranking_violation_count,
            )

        if (
            self.parent_top_action_margin_guard_weight > 0.0
            and self.total_steps % 100 == 0
        ):
            logger.info(
                "RL parent top-action margin guard update: total_steps=%s "
                "loss=%.6f weight=%.6f cap=%.6f eligible=%s violations=%s",
                self.total_steps,
                self.last_parent_top_action_margin_guard_loss,
                self.parent_top_action_margin_guard_weight,
                self.parent_top_action_margin_guard_cap,
                self.last_parent_top_action_margin_guard_eligible_count,
                self.last_parent_top_action_margin_guard_ranking_violation_count,
            )

        if (
            self.positive_energy_action_imitation_weight > 0.0
            and self.total_steps % 100 == 0
        ):
            logger.info(
                "RL positive-energy action imitation update: total_steps=%s "
                "loss=%.6f weight=%.6f eligible=%s",
                self.total_steps,
                self.last_positive_energy_action_imitation_loss,
                self.positive_energy_action_imitation_weight,
                self.last_positive_energy_action_imitation_count,
            )

        if (
            self.positive_energy_parent_end_turn_imitation_weight > 0.0
            and self.total_steps % 100 == 0
        ):
            logger.info(
                "RL positive-energy parent-EndTurn imitation update: "
                "total_steps=%s loss=%.6f weight=%.6f eligible=%s",
                self.total_steps,
                self.last_positive_energy_parent_end_turn_imitation_loss,
                self.positive_energy_parent_end_turn_imitation_weight,
                self.last_positive_energy_parent_end_turn_imitation_count,
            )

        if self.total_steps % self.target_update_freq == 0:
            self.target_network.load_state_dict(self.online_network.state_dict())

        self.epsilon = max(
            self.epsilon_end,
            self.epsilon_start
            - (self.epsilon_start - self.epsilon_end) * min(self.total_steps / self.epsilon_decay, 1.0),
        )

        return loss_value

    def update_episode_count(self) -> None:
        self.episode_count += 1

    def get_avg_loss(self) -> float:
        if not self.loss_history:
            return 0.0
        return float(sum(self.loss_history) / len(self.loss_history))

    def get_epsilon(self) -> float:
        return float(self.epsilon)
