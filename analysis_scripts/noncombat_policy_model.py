"""Deterministic CPU-only candidate ranking for offline non-combat policy rows."""

from __future__ import annotations

import copy
import hashlib
import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from types import MappingProxyType
from typing import Any

import torch
import torch.nn.functional as functional


LABEL_MODES = ("current", "bottled")
ARTIFACT_STEMS = {
    "current": "noncombat_policy_current",
    "bottled": "noncombat_policy_bottled",
}


@dataclass(frozen=True)
class FeatureConfig:
    version: str = "noncombat-policy-features-v1"
    hash_dim: int = 1024


@dataclass(frozen=True)
class TrainingConfig:
    seed: int = 0
    learning_rate: float = 1e-3
    max_epochs: int = 50
    patience: int = 5
    device: str = "cpu"


@dataclass(frozen=True)
class Prediction:
    sample_id: str
    predicted_action_id: str
    target_action_id: str
    confidence: float
    probabilities: tuple[float, ...]


@dataclass(frozen=True)
class TrainingResult:
    model: "CandidateRanker"
    epochs_run: int
    best_validation_loss: float
    history: tuple[Mapping[str, float], ...]
    artifact_manifest: Mapping[str, Any]

    def __post_init__(self):
        object.__setattr__(
            self,
            "history",
            tuple(_freeze_json_compatible(item) for item in self.history),
        )
        object.__setattr__(
            self,
            "artifact_manifest",
            _freeze_json_compatible(self.artifact_manifest),
        )


class CandidateRanker(torch.nn.Module):
    def __init__(self, input_dim: int = 1024) -> None:
        super().__init__()
        self.scorer = torch.nn.Linear(input_dim, 1)

    def forward(self, candidate_features: torch.Tensor) -> torch.Tensor:
        return self.scorer(candidate_features).squeeze(-1)


def candidate_feature_vector(row, candidate, config: FeatureConfig) -> torch.Tensor:
    """Encode one state/candidate pair into a stable CPU float32 vector."""
    _validate_feature_config(config)
    if not isinstance(getattr(row, "state", None), Mapping):
        raise TypeError("row.state must be a mapping")
    if not isinstance(candidate, Mapping):
        raise TypeError("candidate must be a mapping")

    features = torch.zeros(config.hash_dim, dtype=torch.float32, device="cpu")
    for path, value in _flatten_values("state", row.state):
        _add_feature_value(features, path, value)
    for path, value in _flatten_values("candidate", candidate):
        _add_feature_value(features, path, value)
    return features


def train_ranker(
    train_rows,
    validation_rows,
    *,
    feature_config: FeatureConfig,
    training_config: TrainingConfig,
) -> TrainingResult:
    """Train a bounded supervised candidate ranker from one isolated label mode."""
    _validate_feature_config(feature_config)
    _validate_training_config(training_config)
    train_rows = _ordered_rows(train_rows, split_name="train")
    validation_rows = _ordered_rows(validation_rows, split_name="validation")
    label_mode = _shared_label_mode(train_rows, validation_rows)
    _validate_rows(train_rows)
    _validate_rows(validation_rows)

    random.seed(training_config.seed)
    torch.manual_seed(training_config.seed)
    model = CandidateRanker(input_dim=feature_config.hash_dim)
    optimizer = torch.optim.Adam(model.parameters(), lr=training_config.learning_rate)

    best_validation_loss = math.inf
    best_state = None
    non_improving_epochs = 0
    history = []
    for epoch in range(1, training_config.max_epochs + 1):
        model.train()
        train_losses = []
        for row in train_rows:
            optimizer.zero_grad()
            logits = model(_candidate_features(row, feature_config))
            loss = functional.cross_entropy(
                logits.unsqueeze(0),
                torch.tensor([_target_index(row)], dtype=torch.long, device="cpu"),
            )
            loss.backward()
            optimizer.step()
            train_losses.append(float(loss.item()))

        validation_loss = _validation_loss(model, validation_rows, feature_config)
        history.append(
            {
                "epoch": float(epoch),
                "train_loss": sum(train_losses) / len(train_losses),
                "validation_loss": validation_loss,
            }
        )
        if validation_loss < best_validation_loss:
            best_validation_loss = validation_loss
            best_state = copy.deepcopy(model.state_dict())
            non_improving_epochs = 0
        else:
            non_improving_epochs += 1
            if non_improving_epochs >= training_config.patience:
                break

    if best_state is None:
        raise AssertionError("training did not produce a validation state")
    model.load_state_dict(best_state)
    manifest = {
        "feature_config": {
            "version": feature_config.version,
            "hash_dim": feature_config.hash_dim,
        },
        "training_config": {
            "seed": training_config.seed,
            "learning_rate": training_config.learning_rate,
            "max_epochs": training_config.max_epochs,
            "patience": training_config.patience,
            "device": training_config.device,
        },
        "label_mode": label_mode,
        "artifact_stem": ARTIFACT_STEMS[label_mode],
        "epochs_run": len(history),
        "best_validation_loss": best_validation_loss,
        "formal_noncombat_rl_training_ready": False,
        "live_policy_promotion_ready": False,
    }
    return TrainingResult(
        model=model,
        epochs_run=len(history),
        best_validation_loss=best_validation_loss,
        history=tuple(history),
        artifact_manifest=manifest,
    )


def predict_ranker(
    model: CandidateRanker,
    rows,
    *,
    feature_config: FeatureConfig,
) -> tuple[Prediction, ...]:
    """Return masked candidate probabilities in the original row candidate order."""
    _validate_feature_config(feature_config)
    if next(model.parameters()).device.type != "cpu":
        raise ValueError("CandidateRanker must remain on CPU")
    if model.scorer.in_features != feature_config.hash_dim:
        raise ValueError("feature_config.hash_dim must match the model input dimension")

    predictions = []
    model.eval()
    with torch.no_grad():
        for row in _ordered_rows(rows, split_name="prediction"):
            _validate_row(row)
            logits = model(_candidate_features(row, feature_config))
            probabilities = torch.softmax(logits, dim=0)
            predicted_index = int(torch.argmax(probabilities).item())
            candidate_ids = _candidate_ids(row)
            probability_values = tuple(float(value) for value in probabilities.tolist())
            predictions.append(
                Prediction(
                    sample_id=str(row.sample_id),
                    predicted_action_id=candidate_ids[predicted_index],
                    target_action_id=str(row.target_action_id),
                    confidence=probability_values[predicted_index],
                    probabilities=probability_values,
                )
            )
    return tuple(predictions)


def _validate_feature_config(config: FeatureConfig) -> None:
    if isinstance(config.hash_dim, bool) or not isinstance(config.hash_dim, int) or config.hash_dim <= 0:
        raise ValueError("hash_dim must be a positive integer")


def _validate_training_config(config: TrainingConfig) -> None:
    if config.device != "cpu":
        raise ValueError("only CPU training is supported")
    if isinstance(config.max_epochs, bool) or not isinstance(config.max_epochs, int) or not 1 <= config.max_epochs <= 50:
        raise ValueError("max_epochs must be an integer from 1 through 50")
    if isinstance(config.patience, bool) or not isinstance(config.patience, int) or not 1 <= config.patience <= 5:
        raise ValueError("patience must be an integer from 1 through 5")
    if not isinstance(config.learning_rate, Real) or isinstance(config.learning_rate, bool):
        raise ValueError("learning_rate must be finite and positive")
    if not math.isfinite(config.learning_rate) or config.learning_rate <= 0:
        raise ValueError("learning_rate must be finite and positive")


def _ordered_rows(rows, *, split_name: str) -> tuple[Any, ...]:
    ordered = tuple(rows)
    if not ordered:
        raise ValueError(f"{split_name} rows must be nonempty")
    for row in ordered:
        sample_id = getattr(row, "sample_id", None)
        if not isinstance(sample_id, str) or not sample_id:
            raise ValueError("rows require nonempty sample_id values")
    return tuple(sorted(ordered, key=lambda row: row.sample_id))


def _shared_label_mode(train_rows, validation_rows) -> str:
    label_modes = {getattr(row, "label_mode", None) for row in (*train_rows, *validation_rows)}
    if len(label_modes) != 1:
        raise ValueError("train and validation rows must share one label mode")
    label_mode = label_modes.pop()
    if label_mode not in LABEL_MODES:
        raise ValueError("rows require one nonempty supported label mode")
    return label_mode


def _validate_rows(rows) -> None:
    for row in rows:
        _validate_row(row)


def _validate_row(row) -> None:
    candidate_ids = _candidate_ids(row)
    target_action_id = getattr(row, "target_action_id", None)
    if not isinstance(target_action_id, str) or target_action_id not in candidate_ids:
        raise ValueError("target_action_id must map to one candidate")


def _candidate_ids(row) -> tuple[str, ...]:
    candidates = getattr(row, "candidates", None)
    if not isinstance(candidates, Sequence) or isinstance(candidates, (str, bytes)) or not candidates:
        raise ValueError("rows require at least one candidate")
    candidate_ids = []
    for candidate in candidates:
        if not isinstance(candidate, Mapping):
            raise ValueError("candidates must be mappings")
        action_id = candidate.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise ValueError("candidates require nonempty action_id values")
        candidate_ids.append(action_id)
    if len(candidate_ids) != len(set(candidate_ids)):
        raise ValueError("candidate action_ids must be unique")
    return tuple(candidate_ids)


def _candidate_features(row, feature_config: FeatureConfig) -> torch.Tensor:
    return torch.stack(
        [candidate_feature_vector(row, candidate, feature_config) for candidate in row.candidates]
    )


def _target_index(row) -> int:
    return _candidate_ids(row).index(row.target_action_id)


def _validation_loss(model, rows, feature_config: FeatureConfig) -> float:
    model.eval()
    losses = []
    with torch.no_grad():
        for row in rows:
            logits = model(_candidate_features(row, feature_config))
            loss = functional.cross_entropy(
                logits.unsqueeze(0),
                torch.tensor([_target_index(row)], dtype=torch.long, device="cpu"),
            )
            losses.append(float(loss.item()))
    return sum(losses) / len(losses)


def _flatten_values(path: str, value):
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            yield from _flatten_values(f"{path}.{key}", value[key])
        return
    if isinstance(value, (list, tuple)):
        for index, item in enumerate(value):
            yield from _flatten_values(f"{path}[{index}]", item)
        return
    yield path, value


def _add_feature_value(features: torch.Tensor, path: str, value) -> None:
    if value is None or isinstance(value, (bool, str)):
        feature_bin, sign = _signed_hash(f"{path}={value}", features.numel())
        features[feature_bin] += sign
        return
    if isinstance(value, Real):
        try:
            numeric_value = float(value)
        except OverflowError:
            numeric_value = -math.inf if value < 0 else math.inf
        if math.isnan(numeric_value):
            raise ValueError("numeric feature values must not be NaN")
        normalized = math.copysign(
            min(math.log1p(abs(numeric_value)), 10.0) / 10.0,
            numeric_value,
        )
        feature_bin, _ = _signed_hash(path, features.numel())
        features[feature_bin] += normalized
        return
    raise TypeError(f"unsupported feature value: {type(value).__name__}")


def _signed_hash(token: str, hash_dim: int) -> tuple[int, float]:
    digest = hashlib.sha256(token.encode("utf-8")).digest()
    feature_bin = int.from_bytes(digest[:8], "big") % hash_dim
    sign = -1.0 if digest[8] & 1 else 1.0
    return feature_bin, sign


def _freeze_json_compatible(value):
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze_json_compatible(value[key]) for key in sorted(value, key=str)}
        )
    if isinstance(value, (list, tuple)):
        return tuple(_freeze_json_compatible(item) for item in value)
    if value is None or isinstance(value, (bool, int, float, str)):
        return value
    raise TypeError(f"value is not JSON-compatible: {type(value).__name__}")
