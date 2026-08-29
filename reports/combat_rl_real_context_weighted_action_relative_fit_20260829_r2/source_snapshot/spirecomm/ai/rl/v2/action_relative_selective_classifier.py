"""Development-only action-relative selective classifier."""

from __future__ import annotations

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import math
from typing import Any, Mapping, NamedTuple, Sequence

import torch
import torch.nn as nn
import torch.nn.functional as F

from spirecomm.ai.rl.v2 import action_space
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
    _cpu_state,
    _normalized_metadata,
    _validate_sha256,
    _validated_scorer_state,
    expand_action_relative_examples,
)
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2


ARTIFACT_SCHEMA_VERSION = 1
ARTIFACT_KIND = "combat_action_relative_selective_classifier_development"
SEVERE_CLASS = 0
NEUTRAL_CLASS = 1
BENEFICIAL_CLASS = 2
CLASS_NAMES = ("severe", "neutral", "beneficial")
SUPPORTED_ACTION_STOP = 90
LABEL_BOUNDARIES = {
    "severe_upper_exclusive": -0.5,
    "beneficial_lower_inclusive": 0.5,
}


@dataclass(frozen=True)
class ActionRelativeSelectiveConfig:
    hidden_dim: int = 128
    include_item_semantics: bool = False

    def validate(self) -> None:
        if not isinstance(self.hidden_dim, int) or isinstance(self.hidden_dim, bool):
            raise ValueError("selective classifier hidden_dim must be an integer")
        if self.hidden_dim <= 0:
            raise ValueError("selective classifier hidden_dim must be positive")
        if not isinstance(self.include_item_semantics, bool):
            raise ValueError("selective classifier item semantics flag must be boolean")


class ActionRelativeSelectiveSelection(NamedTuple):
    actions: torch.Tensor
    guard_actions: torch.Tensor
    residual_actions: torch.Tensor
    predicted_advantages: torch.Tensor
    gate_open: torch.Tensor
    evidence_scores: torch.Tensor
    selected_logits: torch.Tensor
    predicted_classes: torch.Tensor
    telemetry: dict[str, Any]


def classify_advantages(raw_advantages: torch.Tensor) -> torch.Tensor:
    values = raw_advantages.float()
    if not bool(torch.isfinite(values).all()):
        raise ValueError("selective classifier advantages must be finite")
    labels = torch.full_like(values, NEUTRAL_CLASS, dtype=torch.long)
    labels[values < LABEL_BOUNDARIES["severe_upper_exclusive"]] = SEVERE_CLASS
    labels[values >= LABEL_BOUNDARIES["beneficial_lower_inclusive"]] = (
        BENEFICIAL_CLASS
    )
    return labels


def _required_corpus_tensors(
    tensors: Mapping[str, torch.Tensor],
) -> dict[str, torch.Tensor]:
    required = (
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "action_masks",
        "guard_actions",
    )
    if not isinstance(tensors, Mapping) or any(name not in tensors for name in required):
        raise ValueError("selective classifier corpus tensors are incomplete")
    normalized = {name: tensors[name] for name in required}
    if any(not isinstance(value, torch.Tensor) for value in normalized.values()):
        raise ValueError("selective classifier corpus contains a non-tensor")
    row_count = int(normalized["guard_actions"].numel())
    if any(value.shape[0] != row_count for value in normalized.values()):
        raise ValueError("selective classifier corpus tensor rows differ")
    return normalized


def build_supported_selective_corpus(
    tensors: Mapping[str, torch.Tensor],
    metadata: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    normalized_tensors = _required_corpus_tensors(tensors)
    row_count = int(normalized_tensors["guard_actions"].numel())
    if not isinstance(metadata, Sequence) or len(metadata) != row_count:
        raise ValueError("selective classifier corpus metadata rows differ")
    action_dim = int(normalized_tensors["action_masks"].shape[1])
    if action_dim < SUPPORTED_ACTION_STOP:
        raise ValueError("selective classifier action space lacks combat actions")

    source_rows: list[int] = []
    supported_metadata: list[dict[str, Any]] = []
    guards = normalized_tensors["guard_actions"].reshape(-1).long()
    for row_index, raw_row in enumerate(metadata):
        if not isinstance(raw_row, Mapping):
            raise ValueError("selective classifier metadata row is invalid")
        guard = int(guards[row_index])
        if raw_row.get("guard_action_index") != guard:
            raise ValueError("selective classifier metadata guard differs")
        branches = raw_row.get("branch_returns")
        if not isinstance(branches, Mapping):
            raise ValueError("selective classifier branch returns are missing")
        normalized_branches: dict[int, Any] = {}
        for raw_action, branch_return in branches.items():
            try:
                action = int(raw_action)
            except (TypeError, ValueError) as exc:
                raise ValueError("selective classifier branch action is invalid") from exc
            if action in normalized_branches:
                raise ValueError("selective classifier branch action is duplicated")
            if not 0 <= action < action_dim:
                raise ValueError("selective classifier branch action is outside action space")
            if not isinstance(branch_return, (int, float)) or isinstance(
                branch_return, bool
            ):
                raise ValueError("selective classifier branch return is invalid")
            if not math.isfinite(float(branch_return)):
                raise ValueError("selective classifier branch return must be finite")
            if not bool(normalized_tensors["action_masks"][row_index, action]):
                raise ValueError("selective classifier branch action is illegal")
            normalized_branches[action] = branch_return
        if guard not in normalized_branches:
            raise ValueError("selective classifier guard branch is missing")
        supported_actions = sorted(
            action
            for action in normalized_branches
            if action != guard and 0 <= action < SUPPORTED_ACTION_STOP
        )
        if not supported_actions:
            continue
        filtered = copy.deepcopy(dict(raw_row))
        filtered["branch_returns"] = {
            str(action): normalized_branches[action]
            for action in [guard, *supported_actions]
        }
        source_rows.append(row_index)
        supported_metadata.append(filtered)

    device = guards.device
    source_indices = torch.tensor(source_rows, dtype=torch.long, device=device)
    supported_tensors = {
        name: value[source_indices]
        for name, value in normalized_tensors.items()
    }
    if not source_rows:
        raise ValueError("selective classifier corpus has no supported alternatives")
    expanded = expand_action_relative_examples(
        supported_tensors,
        supported_metadata,
        action_dim=action_dim,
    )
    if bool((expanded["candidate_actions"] >= SUPPORTED_ACTION_STOP).any()):
        raise RuntimeError("selective classifier retained an unsupported action")
    alternatives = torch.zeros_like(supported_tensors["action_masks"], dtype=torch.bool)
    alternatives[
        expanded["row_indices"], expanded["candidate_actions"]
    ] = True
    return {
        "tensors": supported_tensors,
        "metadata": supported_metadata,
        "source_row_indices": source_indices,
        "excluded_unsupported_only_row_count": row_count - len(source_rows),
        "pair_row_indices": expanded["row_indices"],
        "candidate_actions": expanded["candidate_actions"],
        "candidate_returns": expanded["candidate_returns"],
        "guard_returns": expanded["guard_returns"],
        "raw_advantages": expanded["raw_advantages"],
        "labels": classify_advantages(expanded["raw_advantages"]),
        "alternative_masks": alternatives,
    }


def build_class_balanced_sample_plan(
    labels: torch.Tensor,
    *,
    updates: int,
    samples_per_class: int,
    seed: int,
) -> torch.Tensor:
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in (updates, samples_per_class)
    ):
        raise ValueError("selective classifier sampling dimensions must be positive")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("selective classifier sampling seed is invalid")
    labels = labels.reshape(-1).long().cpu()
    pools = [labels.eq(class_index).nonzero(as_tuple=False).reshape(-1) for class_index in range(3)]
    if any(pool.numel() == 0 for pool in pools):
        raise ValueError("selective classifier class support is incomplete")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    samples = []
    for pool in pools:
        offsets = torch.randint(
            int(pool.numel()),
            (updates, samples_per_class),
            generator=generator,
        )
        samples.append(pool[offsets])
    return torch.stack(samples, dim=1)


def build_within_state_ranking_pairs(
    pair_row_indices: torch.Tensor,
    labels: torch.Tensor,
) -> torch.Tensor:
    rows = pair_row_indices.reshape(-1).long().cpu()
    labels = labels.reshape(-1).long().cpu()
    if rows.shape != labels.shape:
        raise ValueError("selective classifier ranking rows and labels differ")
    pairs: list[tuple[int, int]] = []
    for row in sorted(set(int(value) for value in rows.tolist())):
        member_indices = rows.eq(row).nonzero(as_tuple=False).reshape(-1)
        beneficial = member_indices[labels[member_indices].eq(BENEFICIAL_CLASS)]
        non_beneficial = member_indices[labels[member_indices].ne(BENEFICIAL_CLASS)]
        pairs.extend(
            (int(positive), int(negative))
            for positive in beneficial.tolist()
            for negative in non_beneficial.tolist()
        )
    if not pairs:
        raise ValueError("selective classifier ranking support is empty")
    return torch.tensor(pairs, dtype=torch.long)


def build_replacement_sample_plan(
    support_count: int,
    *,
    updates: int,
    samples_per_update: int,
    seed: int,
) -> torch.Tensor:
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in (support_count, updates, samples_per_update)
    ):
        raise ValueError("selective classifier replacement sampling inputs differ")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("selective classifier replacement sampling seed is invalid")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return torch.randint(
        support_count,
        (updates, samples_per_update),
        generator=generator,
    )


def finite_sample_negative_threshold(
    evidence_scores: torch.Tensor,
    labels: torch.Tensor,
    *,
    quantile: float = 0.95,
) -> tuple[float, int, int]:
    if not isinstance(quantile, (int, float)) or isinstance(quantile, bool):
        raise ValueError("selective classifier calibration quantile is invalid")
    quantile = float(quantile)
    if not 0.0 < quantile < 1.0:
        raise ValueError("selective classifier calibration quantile is invalid")
    scores = evidence_scores.reshape(-1).float().cpu()
    labels = labels.reshape(-1).long().cpu()
    if scores.shape != labels.shape or not bool(torch.isfinite(scores).all()):
        raise ValueError("selective classifier calibration tensors differ")
    negatives = scores[labels.ne(BENEFICIAL_CLASS)]
    count = int(negatives.numel())
    if count == 0:
        raise ValueError("selective classifier calibration has no negative pairs")
    rank = min(count, int(math.ceil((count + 1) * quantile)))
    threshold = float(negatives.sort().values[rank - 1])
    return threshold, rank, count


class ActionRelativeSelectiveClassifier(ActionRelativeAdvantageResidual):
    """Frozen parent plus a shared three-class candidate head."""

    def __init__(
        self,
        parent: nn.Module,
        metadata: Mapping[str, Any],
        config: ActionRelativeSelectiveConfig,
        *,
        selection_threshold: float,
    ) -> None:
        config.validate()
        if not isinstance(selection_threshold, (int, float)) or isinstance(
            selection_threshold, bool
        ):
            raise ValueError("selective classifier threshold must be numeric")
        if not math.isfinite(float(selection_threshold)):
            raise ValueError("selective classifier threshold must be finite")
        super().__init__(
            parent,
            metadata,
            ActionRelativeAdvantageConfig(hidden_dim=config.hidden_dim),
        )
        del self.scorer
        self.config = config
        self.selection_threshold = float(selection_threshold)
        self.base_feature_dim = self.feature_dim
        self.item_semantic_dim = 0
        if config.include_item_semantics:
            hand_offset = (
                StateEncoderV2.PLAYER_FEATURES
                + StateEncoderV2.MONSTER_SLOTS * StateEncoderV2.MONSTER_FEATURES
            )
            hand_end = (
                hand_offset
                + StateEncoderV2.CARD_SLOTS * StateEncoderV2.HAND_FEATURES
            )
            if self.metadata["continuous_dim"] < hand_end:
                raise ValueError("selective classifier lacks local card features")
            if self.metadata["card_slots"] < StateEncoderV2.CARD_SLOTS:
                raise ValueError("selective classifier card slots are incomplete")
            if self.metadata["potion_slots"] < StateEncoderV2.POTION_SLOTS:
                raise ValueError("selective classifier potion slots are incomplete")
            card_dim = int(self.parent.card_embedding.embedding_dim)
            potion_dim = int(self.parent.potion_embedding.embedding_dim)
            self.item_semantic_dim = (
                2 * card_dim
                + 2 * potion_dim
                + 2 * StateEncoderV2.HAND_FEATURES
                + 4
                + 2 * StateEncoderV2.CARD_SLOTS
                + 2 * action_space.TARGET_SLOTS
            )
            self.feature_dim += self.item_semantic_dim
        device = next(self.parent.parameters()).device
        self.classifier = nn.Sequential(
            nn.Linear(self.feature_dim, config.hidden_dim),
            nn.ReLU(),
            nn.Linear(config.hidden_dim, 3),
        ).to(device)

    def item_semantic_features(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        candidate_actions: torch.Tensor,
    ) -> torch.Tensor:
        if not self.config.include_item_semantics:
            raise ValueError("selective classifier item semantics are disabled")
        (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        ) = self._validated_state_inputs(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        )
        del relic_ids
        candidate_actions = candidate_actions.reshape(-1).long()
        if candidate_actions.shape != guard_actions.shape:
            raise ValueError("selective classifier candidate action shape differs")
        if bool((candidate_actions < 0).any()) or bool(
            (candidate_actions >= SUPPORTED_ACTION_STOP).any()
        ):
            raise ValueError("selective classifier candidate action is unsupported")
        rows = torch.arange(candidate_actions.numel(), device=candidate_actions.device)
        if not bool(action_masks[rows, candidate_actions].all()):
            raise ValueError("selective classifier candidate action must be legal")
        if bool(candidate_actions.eq(guard_actions).any()):
            raise ValueError("selective classifier candidate action duplicates guard")

        def decompose(actions: torch.Tensor) -> tuple[torch.Tensor, ...]:
            is_card = actions.lt(action_space.USE_POTION_OFFSET)
            is_potion = actions.ge(action_space.USE_POTION_OFFSET) & actions.lt(
                action_space.END_TURN_ACTION
            )
            slots = torch.zeros_like(actions)
            slots[is_card] = actions[is_card] // action_space.TARGET_SLOTS
            slots[is_potion] = (
                actions[is_potion] - action_space.USE_POTION_OFFSET
            ) // action_space.TARGET_SLOTS
            targets = torch.zeros_like(actions)
            item_actions = is_card | is_potion
            targets[item_actions] = actions[item_actions] % action_space.TARGET_SLOTS
            return is_card, is_potion, item_actions, slots, targets

        def item_features(actions: torch.Tensor) -> tuple[torch.Tensor, ...]:
            is_card, is_potion, is_item, slots, targets = decompose(actions)
            card_embedding = torch.zeros(
                (actions.numel(), self.parent.card_embedding.embedding_dim),
                dtype=continuous.dtype,
                device=continuous.device,
            )
            potion_embedding = torch.zeros(
                (actions.numel(), self.parent.potion_embedding.embedding_dim),
                dtype=continuous.dtype,
                device=continuous.device,
            )
            if bool(is_card.any()):
                card_rows = rows[is_card]
                card_embedding[is_card] = self.parent.card_embedding(
                    card_ids[card_rows, slots[is_card]]
                )
            if bool(is_potion.any()):
                potion_rows = rows[is_potion]
                potion_embedding[is_potion] = self.parent.potion_embedding(
                    potion_ids[potion_rows, slots[is_potion]]
                )
            hand_offset = (
                StateEncoderV2.PLAYER_FEATURES
                + StateEncoderV2.MONSTER_SLOTS * StateEncoderV2.MONSTER_FEATURES
            )
            hand_end = (
                hand_offset
                + StateEncoderV2.CARD_SLOTS * StateEncoderV2.HAND_FEATURES
            )
            hand = continuous[:, hand_offset:hand_end].reshape(
                -1, StateEncoderV2.CARD_SLOTS, StateEncoderV2.HAND_FEATURES
            )
            local = torch.zeros(
                (actions.numel(), StateEncoderV2.HAND_FEATURES),
                dtype=continuous.dtype,
                device=continuous.device,
            )
            if bool(is_card.any()):
                card_rows = rows[is_card]
                local[is_card] = hand[card_rows, slots[is_card]]
            family = torch.stack((is_card.float(), is_potion.float()), dim=1)
            slot_one_hot = torch.zeros(
                (actions.numel(), StateEncoderV2.CARD_SLOTS),
                dtype=continuous.dtype,
                device=continuous.device,
            )
            target_one_hot = torch.zeros(
                (actions.numel(), action_space.TARGET_SLOTS),
                dtype=continuous.dtype,
                device=continuous.device,
            )
            if bool(is_item.any()):
                slot_one_hot[is_item] = F.one_hot(
                    slots[is_item], num_classes=StateEncoderV2.CARD_SLOTS
                ).float()
                target_one_hot[is_item] = F.one_hot(
                    targets[is_item], num_classes=action_space.TARGET_SLOTS
                ).float()
            return card_embedding, potion_embedding, local, family, slot_one_hot, target_one_hot

        candidate = item_features(candidate_actions)
        guard = item_features(guard_actions)
        semantic = torch.cat(
            (
                candidate[0],
                candidate[1],
                guard[0],
                guard[1],
                candidate[2],
                guard[2],
                candidate[3],
                guard[3],
                candidate[4],
                guard[4],
                candidate[5],
                guard[5],
            ),
            dim=1,
        )
        if semantic.shape[1] != self.item_semantic_dim:
            raise RuntimeError("selective classifier item semantic shape differs")
        if not bool(torch.isfinite(semantic).all()):
            raise ValueError("selective classifier item semantics must be finite")
        return semantic

    def _candidate_features(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        candidate_actions: torch.Tensor,
    ) -> torch.Tensor:
        (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        ) = self._validated_state_inputs(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        )
        candidate_actions = candidate_actions.reshape(-1).long()
        if candidate_actions.shape != guard_actions.shape:
            raise ValueError("selective classifier candidate action shape differs")
        if bool((candidate_actions < 0).any()) or bool(
            (candidate_actions >= SUPPORTED_ACTION_STOP).any()
        ):
            raise ValueError("selective classifier candidate action is unsupported")
        rows = torch.arange(candidate_actions.numel(), device=candidate_actions.device)
        if not bool(action_masks[rows, candidate_actions].all()):
            raise ValueError("selective classifier candidate action must be legal")
        if bool(candidate_actions.eq(guard_actions).any()):
            raise ValueError("selective classifier candidate action duplicates guard")
        latent = self._parent_latent(continuous, card_ids, potion_ids, relic_ids)
        action_dim = self.metadata["action_dim"]
        base = torch.cat(
            (
                latent,
                F.one_hot(guard_actions, num_classes=action_dim).float(),
                F.one_hot(candidate_actions, num_classes=action_dim).float(),
                action_masks.float(),
            ),
            dim=1,
        )
        if not self.config.include_item_semantics:
            return base
        semantic = self.item_semantic_features(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
            candidate_actions,
        )
        return torch.cat((base, semantic), dim=1)

    def score_candidate_logits(self, *args: Any, **kwargs: Any) -> torch.Tensor:
        logits = self.classifier(self._candidate_features(*args, **kwargs))
        if logits.dim() != 2 or logits.shape[1] != 3:
            raise RuntimeError("selective classifier logits shape differs")
        if not bool(torch.isfinite(logits).all()):
            raise ValueError("selective classifier logits must be finite")
        return logits

    def score_candidate_evidence(self, *args: Any, **kwargs: Any) -> torch.Tensor:
        logits = self.score_candidate_logits(*args, **kwargs)
        return logits[:, BENEFICIAL_CLASS] - torch.logsumexp(
            logits[:, :BENEFICIAL_CLASS], dim=1
        )

    def score_candidates(self, *args: Any, **kwargs: Any) -> torch.Tensor:
        return self.score_candidate_evidence(*args, **kwargs)

    def select_actions(
        self,
        continuous: torch.Tensor,
        card_ids: torch.Tensor,
        potion_ids: torch.Tensor,
        relic_ids: torch.Tensor,
        action_masks: torch.Tensor,
        guard_actions: torch.Tensor,
        alternative_masks: torch.Tensor | None = None,
        *,
        forbidden_action_indices: frozenset[int] = frozenset(),
    ) -> ActionRelativeSelectiveSelection:
        (
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        ) = self._validated_state_inputs(
            continuous,
            card_ids,
            potion_ids,
            relic_ids,
            action_masks,
            guard_actions,
        )
        batch_size = guard_actions.numel()
        rows = torch.arange(batch_size, device=guard_actions.device)
        if alternative_masks is None:
            allowed = action_masks.clone()
            allowed[rows, guard_actions] = False
        else:
            if alternative_masks.dim() == 1:
                alternative_masks = alternative_masks.unsqueeze(0)
            if alternative_masks.shape != action_masks.shape:
                raise ValueError("selective classifier alternative mask shape differs")
            allowed = alternative_masks.bool().clone()
            if bool((allowed & ~action_masks).any()):
                raise ValueError("selective classifier alternatives contain illegal actions")
            if bool(allowed[rows, guard_actions].any()):
                raise ValueError("selective classifier alternatives contain guard action")
        unsupported_count = int(allowed[:, SUPPORTED_ACTION_STOP:].sum().item())
        allowed[:, SUPPORTED_ACTION_STOP:] = False
        forbidden = sorted(forbidden_action_indices)
        for action in forbidden:
            if not isinstance(action, int) or isinstance(action, bool) or not (
                0 <= action < self.metadata["action_dim"]
            ):
                raise ValueError("selective classifier forbidden action is invalid")
            allowed[:, action] = False

        residual_actions = guard_actions.clone()
        evidence_scores = torch.full(
            (batch_size,), float("-inf"), dtype=continuous.dtype, device=continuous.device
        )
        selected_logits = torch.zeros(
            (batch_size, 3), dtype=continuous.dtype, device=continuous.device
        )
        predicted_classes = torch.full(
            (batch_size,), -1, dtype=torch.long, device=guard_actions.device
        )
        has_allowed = allowed.any(dim=1)
        candidate_pairs = allowed.nonzero(as_tuple=False)
        if candidate_pairs.numel():
            state_rows = candidate_pairs[:, 0]
            candidates = candidate_pairs[:, 1]
            logits = self.score_candidate_logits(
                continuous[state_rows],
                card_ids[state_rows],
                potion_ids[state_rows],
                relic_ids[state_rows],
                action_masks[state_rows],
                guard_actions[state_rows],
                candidates,
            )
            evidence = logits[:, BENEFICIAL_CLASS] - torch.logsumexp(
                logits[:, :BENEFICIAL_CLASS], dim=1
            )
            score_matrix = torch.full(
                action_masks.shape,
                float("-inf"),
                dtype=evidence.dtype,
                device=evidence.device,
            )
            score_matrix[state_rows, candidates] = evidence
            best_scores, best_actions = score_matrix.max(dim=1)
            residual_actions[has_allowed] = best_actions[has_allowed]
            evidence_scores[has_allowed] = best_scores[has_allowed]
            best_pair = candidates.eq(best_actions[state_rows])
            best_rows = state_rows[best_pair]
            selected_logits[best_rows] = logits[best_pair]
            predicted_classes[best_rows] = logits[best_pair].argmax(dim=1)
        gate_open = has_allowed & evidence_scores.ge(self.selection_threshold)
        actions = torch.where(gate_open, residual_actions, guard_actions)
        if not bool(action_masks[rows, actions].all()):
            raise RuntimeError("selective classifier selected an illegal action")
        if bool(gate_open.any()) and not bool(
            allowed[rows[gate_open], actions[gate_open]].all()
        ):
            raise RuntimeError("selective classifier selected a forbidden action")
        forbidden_selection_count = sum(
            int(actions[gate_open].eq(action).sum().item()) for action in forbidden
        )
        return ActionRelativeSelectiveSelection(
            actions=actions,
            guard_actions=guard_actions,
            residual_actions=residual_actions,
            predicted_advantages=evidence_scores,
            gate_open=gate_open,
            evidence_scores=evidence_scores,
            selected_logits=selected_logits,
            predicted_classes=predicted_classes,
            telemetry={
                "row_count": int(batch_size),
                "intervention_count": int(gate_open.sum().item()),
                "guard_preserved_count": int((~gate_open).sum().item()),
                "no_allowed_alternative_count": int((~has_allowed).sum().item()),
                "unsupported_alternative_count": unsupported_count,
                "forbidden_action_indices": forbidden,
                "forbidden_action_selection_count": forbidden_selection_count,
                "selection_threshold": self.selection_threshold,
            },
        )


def _binding_sha256(values: Mapping[str, Any]) -> str:
    payload = json.dumps(values, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _normalized_identity_map(
    values: Mapping[str, str], expected_keys: set[str], label: str
) -> dict[str, str]:
    if not isinstance(values, Mapping) or set(values) != expected_keys:
        raise ValueError(f"selective classifier {label} identities differ")
    return {
        name: _validate_sha256(value, f"{label} {name}")
        for name, value in sorted(values.items())
    }


def _normalized_class_support(values: Mapping[str, int]) -> dict[str, int]:
    if not isinstance(values, Mapping) or set(values) != set(CLASS_NAMES):
        raise ValueError("selective classifier class support differs")
    result: dict[str, int] = {}
    for name in CLASS_NAMES:
        value = values[name]
        if not isinstance(value, int) or isinstance(value, bool) or value < 0:
            raise ValueError("selective classifier class support differs")
        result[name] = int(value)
    return result


def build_selective_development_artifact(
    classifier: ActionRelativeSelectiveClassifier,
    *,
    parent_checkpoint_sha256: str,
    corpus_sha256: Mapping[str, str],
    recipe: Mapping[str, Any],
    split_sha256: Mapping[str, str],
    class_support: Mapping[str, int],
    ranking_support: int,
    sampling_plan_sha256: str,
    telemetry: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(recipe, Mapping) or not recipe:
        raise ValueError("selective classifier recipe is missing")
    if not isinstance(ranking_support, int) or isinstance(ranking_support, bool) or ranking_support < 0:
        raise ValueError("selective classifier ranking support differs")
    state = _cpu_state(classifier.classifier.state_dict())
    artifact = {
        "checkpoint_schema_version": ARTIFACT_SCHEMA_VERSION,
        "checkpoint_kind": ARTIFACT_KIND,
        "production_compatible": False,
        "metadata": dict(classifier.metadata),
        "config": asdict(classifier.config),
        "label_boundaries": dict(LABEL_BOUNDARIES),
        "selection_threshold": classifier.selection_threshold,
        "recipe": copy.deepcopy(dict(recipe)),
        "parent_checkpoint_sha256": _validate_sha256(
            parent_checkpoint_sha256, "parent checkpoint"
        ),
        "parent_state_dict_sha256": state_dict_sha256(classifier.parent.state_dict()),
        "corpus_sha256": _normalized_identity_map(
            corpus_sha256, {"train", "evaluation"}, "corpus"
        ),
        "split_sha256": _normalized_identity_map(
            split_sha256, {"fit", "calibration"}, "split"
        ),
        "class_support": _normalized_class_support(class_support),
        "ranking_support": int(ranking_support),
        "sampling_plan_sha256": _validate_sha256(
            sampling_plan_sha256, "sampling plan"
        ),
        "classifier_state_dict": state,
        "classifier_state_dict_sha256": state_dict_sha256(state),
        "telemetry": copy.deepcopy(dict(telemetry)),
        "authority": {
            "development_only": True,
            "gameplay": False,
            "qualification": False,
            "promotion": False,
        },
    }
    artifact["binding_sha256"] = _binding_sha256(
        {name: value for name, value in artifact.items() if name not in {"classifier_state_dict", "telemetry"}}
    )
    return artifact


def load_selective_development_artifact(
    artifact: Mapping[str, Any],
    *,
    parent: nn.Module,
    expected_metadata: Mapping[str, Any],
    expected_parent_checkpoint_sha256: str,
    expected_corpus_sha256: Mapping[str, str],
    expected_recipe: Mapping[str, Any],
    expected_split_sha256: Mapping[str, str],
    expected_sampling_plan_sha256: str,
) -> ActionRelativeSelectiveClassifier:
    required = {
        "checkpoint_schema_version",
        "checkpoint_kind",
        "production_compatible",
        "metadata",
        "config",
        "label_boundaries",
        "selection_threshold",
        "recipe",
        "parent_checkpoint_sha256",
        "parent_state_dict_sha256",
        "corpus_sha256",
        "split_sha256",
        "class_support",
        "ranking_support",
        "sampling_plan_sha256",
        "classifier_state_dict",
        "classifier_state_dict_sha256",
        "telemetry",
        "authority",
        "binding_sha256",
    }
    if not isinstance(artifact, Mapping) or set(artifact) != required:
        raise ValueError("selective classifier artifact keys differ")
    observed_binding = _validate_sha256(artifact["binding_sha256"], "binding")
    expected_binding = _binding_sha256(
        {name: value for name, value in artifact.items() if name not in {"classifier_state_dict", "telemetry", "binding_sha256"}}
    )
    if observed_binding != expected_binding:
        raise ValueError("selective classifier artifact binding differs")
    if artifact["checkpoint_schema_version"] != ARTIFACT_SCHEMA_VERSION:
        raise ValueError("selective classifier artifact schema differs")
    if artifact["checkpoint_kind"] != ARTIFACT_KIND or artifact["production_compatible"] is not False:
        raise ValueError("selective classifier artifact kind differs")
    normalized_metadata = _normalized_metadata(expected_metadata)
    if artifact["metadata"] != normalized_metadata:
        raise ValueError("selective classifier metadata differs")
    if artifact["label_boundaries"] != LABEL_BOUNDARIES:
        raise ValueError("selective classifier label boundaries differ")
    if dict(artifact["recipe"]) != dict(expected_recipe):
        raise ValueError("selective classifier recipe differs")
    if _validate_sha256(artifact["parent_checkpoint_sha256"], "parent checkpoint") != _validate_sha256(
        expected_parent_checkpoint_sha256, "expected parent checkpoint"
    ):
        raise ValueError("selective classifier parent checkpoint differs")
    if state_dict_sha256(parent.state_dict()) != _validate_sha256(
        artifact["parent_state_dict_sha256"], "parent state"
    ):
        raise ValueError("selective classifier parent state differs")
    observed_corpus = _normalized_identity_map(
        artifact["corpus_sha256"], {"train", "evaluation"}, "corpus"
    )
    expected_corpus = _normalized_identity_map(
        expected_corpus_sha256, {"train", "evaluation"}, "expected corpus"
    )
    if observed_corpus != expected_corpus:
        raise ValueError("selective classifier corpus identity differs")
    observed_split = _normalized_identity_map(
        artifact["split_sha256"], {"fit", "calibration"}, "split"
    )
    expected_split = _normalized_identity_map(
        expected_split_sha256, {"fit", "calibration"}, "expected split"
    )
    if observed_split != expected_split:
        raise ValueError("selective classifier split identity differs")
    if _validate_sha256(artifact["sampling_plan_sha256"], "sampling plan") != _validate_sha256(
        expected_sampling_plan_sha256, "expected sampling plan"
    ):
        raise ValueError("selective classifier sampling plan differs")
    _normalized_class_support(artifact["class_support"])
    if not isinstance(artifact["ranking_support"], int) or artifact["ranking_support"] < 0:
        raise ValueError("selective classifier ranking support differs")
    if artifact["authority"] != {
        "development_only": True,
        "gameplay": False,
        "qualification": False,
        "promotion": False,
    }:
        raise ValueError("selective classifier artifact authority differs")
    try:
        config = ActionRelativeSelectiveConfig(**dict(artifact["config"]))
    except (TypeError, ValueError) as exc:
        raise ValueError("selective classifier config differs") from exc
    classifier = ActionRelativeSelectiveClassifier(
        parent,
        normalized_metadata,
        config,
        selection_threshold=float(artifact["selection_threshold"]),
    )
    state = _validated_scorer_state(
        artifact["classifier_state_dict"], classifier.classifier.state_dict()
    )
    if state_dict_sha256(state) != _validate_sha256(
        artifact["classifier_state_dict_sha256"], "classifier state"
    ):
        raise ValueError("selective classifier state identity differs")
    classifier.classifier.load_state_dict(state, strict=True)
    return classifier
