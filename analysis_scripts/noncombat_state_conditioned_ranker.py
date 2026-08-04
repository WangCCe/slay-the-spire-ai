"""Versioned CPU-only state-conditioned scoring for non-combat candidates."""

from __future__ import annotations

from numbers import Integral
from typing import Any

import torch


ARCHITECTURE_ID = "state-conditioned-candidate-ranker-mlp-v1"
DEFAULT_HIDDEN_DIM = 64
MODEL_DTYPE = torch.float32


class StateConditionedRankerError(ValueError):
    """Raised when the versioned ranker boundary is invalid."""


def _positive_int(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, Integral) or int(value) <= 0:
        raise StateConditionedRankerError(f"{label} must be a positive integer")
    return int(value)


class StateConditionedCandidateRanker(torch.nn.Module):
    """Score candidate rows after a shared state/candidate ReLU interaction."""

    def __init__(
        self, input_dim: int, hidden_dim: int = DEFAULT_HIDDEN_DIM
    ) -> None:
        super().__init__()
        self.input_dim = _positive_int(input_dim, "input_dim")
        self.hidden_dim = _positive_int(hidden_dim, "hidden_dim")
        self.hidden = torch.nn.Linear(self.input_dim * 2, self.hidden_dim)
        self.scorer = torch.nn.Linear(self.hidden_dim, 1)

    def architecture_metadata(self) -> dict[str, object]:
        return {
            "architecture_id": ARCHITECTURE_ID,
            "candidate_input_dim": self.input_dim,
            "device": "cpu",
            "dtype": "float32",
            "hidden_dim": self.hidden_dim,
            "state_conditioned": True,
            "state_input_dim": self.input_dim,
        }

    def forward(
        self, state_features: torch.Tensor, candidate_features: torch.Tensor
    ) -> torch.Tensor:
        self._validate_model()
        self._validate_inputs(state_features, candidate_features)
        repeated_state = state_features.unsqueeze(0).expand(
            candidate_features.shape[0], -1
        )
        combined = torch.cat((repeated_state, candidate_features), dim=1)
        scores = self.scorer(torch.relu(self.hidden(combined))).squeeze(-1)
        if scores.shape != (candidate_features.shape[0],):
            raise StateConditionedRankerError("ranker returned an invalid score shape")
        if not torch.isfinite(scores).all().item():
            raise StateConditionedRankerError("ranker scores must be finite")
        return scores

    def _validate_model(self) -> None:
        for name, parameter in self.named_parameters():
            if parameter.device.type != "cpu":
                raise StateConditionedRankerError(
                    f"model parameter {name} must remain on CPU"
                )
            if parameter.dtype != MODEL_DTYPE:
                raise StateConditionedRankerError(
                    f"model parameter {name} dtype must be float32"
                )
            if not torch.isfinite(parameter).all().item():
                raise StateConditionedRankerError(
                    f"model parameter {name} must be finite"
                )

    def _validate_inputs(
        self, state_features: torch.Tensor, candidate_features: torch.Tensor
    ) -> None:
        self._validate_tensor(state_features, "state_features", expected_rank=1)
        self._validate_tensor(
            candidate_features, "candidate_features", expected_rank=2
        )
        if state_features.shape[0] != self.input_dim:
            raise StateConditionedRankerError(
                f"state feature width must equal {self.input_dim}"
            )
        if candidate_features.shape[0] == 0:
            raise StateConditionedRankerError("candidate_features must be nonempty")
        if candidate_features.shape[1] != self.input_dim:
            raise StateConditionedRankerError(
                f"candidate feature width must equal {self.input_dim}"
            )

    @staticmethod
    def _validate_tensor(
        value: Any, label: str, *, expected_rank: int
    ) -> None:
        if not isinstance(value, torch.Tensor):
            raise StateConditionedRankerError(f"{label} must be a tensor")
        if value.ndim != expected_rank:
            raise StateConditionedRankerError(
                f"{label} must be rank {expected_rank}"
            )
        if value.device.type != "cpu":
            raise StateConditionedRankerError(f"{label} must remain on CPU")
        if value.dtype != MODEL_DTYPE:
            raise StateConditionedRankerError(f"{label} dtype must be float32")
        if not torch.isfinite(value).all().item():
            raise StateConditionedRankerError(f"{label} must be finite")
