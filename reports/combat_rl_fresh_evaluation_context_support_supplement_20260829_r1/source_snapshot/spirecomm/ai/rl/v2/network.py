"""
DQN network with embedding inputs for RL v2.
"""

from typing import Optional

import torch
import torch.nn as nn


class DQNetworkV2(nn.Module):
    def __init__(
        self,
        continuous_dim: int,
        action_dim: int,
        card_vocab: int,
        potion_vocab: int,
        relic_vocab: int,
        card_embed_dim: int = 32,
        potion_embed_dim: int = 8,
        relic_embed_dim: int = 16,
        card_slots: int = 10,
        potion_slots: int = 5,
        relic_slots: int = 40,
        hidden_dims=None,
    ):
        super().__init__()
        if hidden_dims is None:
            hidden_dims = [256, 256]

        self.card_embedding = nn.Embedding(card_vocab, card_embed_dim)
        self.potion_embedding = nn.Embedding(potion_vocab, potion_embed_dim)
        self.relic_embedding = nn.Embedding(relic_vocab, relic_embed_dim)

        input_dim = (
            continuous_dim
            + card_embed_dim * card_slots
            + potion_embed_dim * potion_slots
            + relic_embed_dim * relic_slots
        )

        layers = []
        last_dim = input_dim
        for hidden_dim in hidden_dims:
            layers.append(nn.Linear(last_dim, hidden_dim))
            layers.append(nn.ReLU())
            layers.append(nn.Dropout(0.05))
            last_dim = hidden_dim
        self.hidden_layers = nn.Sequential(*layers)
        self.output_layer = nn.Linear(hidden_dims[-1], action_dim)

        self._initialize_weights()

    def _initialize_weights(self):
        for module in self.modules():
            if isinstance(module, nn.Linear):
                nn.init.kaiming_normal_(module.weight, mode="fan_in", nonlinearity="relu")
                if module.bias is not None:
                    nn.init.zeros_(module.bias)

    def forward(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        if continuous.dim() == 1:
            continuous = continuous.unsqueeze(0)
        if card_ids.dim() == 1:
            card_ids = card_ids.unsqueeze(0)
        if potion_ids.dim() == 1:
            potion_ids = potion_ids.unsqueeze(0)
        if relic_ids.dim() == 1:
            relic_ids = relic_ids.unsqueeze(0)

        card_embed = self.card_embedding(card_ids).view(card_ids.size(0), -1)
        potion_embed = self.potion_embedding(potion_ids).view(potion_ids.size(0), -1)
        relic_embed = self.relic_embedding(relic_ids).view(relic_ids.size(0), -1)

        x = torch.cat([continuous, card_embed, potion_embed, relic_embed], dim=1)
        x = self.hidden_layers(x)
        q_values = self.output_layer(x)

        if action_mask is not None:
            q_values = q_values.masked_fill(action_mask == False, float("-inf"))

        return q_values

    def get_best_action(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        with torch.no_grad():
            q_values = self.forward(
                continuous=continuous,
                card_ids=card_ids,
                potion_ids=potion_ids,
                relic_ids=relic_ids,
                action_mask=action_mask,
            )
            return q_values.argmax(dim=1)


class DuelingDQNetworkV2(DQNetworkV2):
    def __init__(
        self,
        continuous_dim: int,
        action_dim: int,
        card_vocab: int,
        potion_vocab: int,
        relic_vocab: int,
        card_embed_dim: int = 32,
        potion_embed_dim: int = 8,
        relic_embed_dim: int = 16,
        card_slots: int = 10,
        potion_slots: int = 5,
        relic_slots: int = 40,
        hidden_dims=None,
    ):
        if hidden_dims is None:
            hidden_dims = [256, 256]

        super().__init__(
            continuous_dim=continuous_dim,
            action_dim=action_dim,
            card_vocab=card_vocab,
            potion_vocab=potion_vocab,
            relic_vocab=relic_vocab,
            card_embed_dim=card_embed_dim,
            potion_embed_dim=potion_embed_dim,
            relic_embed_dim=relic_embed_dim,
            card_slots=card_slots,
            potion_slots=potion_slots,
            relic_slots=relic_slots,
            hidden_dims=[hidden_dims[0]],
        )

        self.value_stream = nn.Sequential(
            nn.Linear(hidden_dims[0], hidden_dims[1]),
            nn.ReLU(),
            nn.Linear(hidden_dims[1], 1),
        )
        self.advantage_stream = nn.Sequential(
            nn.Linear(hidden_dims[0], hidden_dims[1]),
            nn.ReLU(),
            nn.Linear(hidden_dims[1], action_dim),
        )

    def forward(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_mask: Optional[torch.Tensor] = None,
    ) -> torch.Tensor:
        if continuous.dim() == 1:
            continuous = continuous.unsqueeze(0)
        if card_ids.dim() == 1:
            card_ids = card_ids.unsqueeze(0)
        if potion_ids.dim() == 1:
            potion_ids = potion_ids.unsqueeze(0)
        if relic_ids.dim() == 1:
            relic_ids = relic_ids.unsqueeze(0)

        card_embed = self.card_embedding(card_ids).view(card_ids.size(0), -1)
        potion_embed = self.potion_embedding(potion_ids).view(potion_ids.size(0), -1)
        relic_embed = self.relic_embedding(relic_ids).view(relic_ids.size(0), -1)

        x = torch.cat([continuous, card_embed, potion_embed, relic_embed], dim=1)
        x = self.hidden_layers(x)

        values = self.value_stream(x)
        advantages = self.advantage_stream(x)
        q_values = values + (advantages - advantages.mean(dim=1, keepdim=True))

        if action_mask is not None:
            q_values = q_values.masked_fill(action_mask == False, float("-inf"))

        return q_values


def create_dqn_v2(
    network_type: str,
    continuous_dim: int,
    action_dim: int,
    card_vocab: int,
    potion_vocab: int,
    relic_vocab: int,
    device: str,
    card_embed_dim: int = 32,
    potion_embed_dim: int = 8,
    relic_embed_dim: int = 16,
    card_slots: int = 10,
    potion_slots: int = 5,
    relic_slots: int = 40,
):
    if network_type == "standard":
        network = DQNetworkV2(
            continuous_dim=continuous_dim,
            action_dim=action_dim,
            card_vocab=card_vocab,
            potion_vocab=potion_vocab,
            relic_vocab=relic_vocab,
            card_embed_dim=card_embed_dim,
            potion_embed_dim=potion_embed_dim,
            relic_embed_dim=relic_embed_dim,
            card_slots=card_slots,
            potion_slots=potion_slots,
            relic_slots=relic_slots,
        )
    elif network_type == "dueling":
        network = DuelingDQNetworkV2(
            continuous_dim=continuous_dim,
            action_dim=action_dim,
            card_vocab=card_vocab,
            potion_vocab=potion_vocab,
            relic_vocab=relic_vocab,
            card_embed_dim=card_embed_dim,
            potion_embed_dim=potion_embed_dim,
            relic_embed_dim=relic_embed_dim,
            card_slots=card_slots,
            potion_slots=potion_slots,
            relic_slots=relic_slots,
        )
    else:
        raise ValueError(f"Unknown network type: {network_type}")

    return network.to(device)
