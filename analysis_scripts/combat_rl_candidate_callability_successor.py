"""Build candidate-callable combat decision spans from sequential RL v2 replay."""

from __future__ import annotations

import argparse
import json
import math
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import numpy as np
import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
ANALYSIS_DIR = Path(__file__).resolve().parent
for import_root in (REPO_ROOT, ANALYSIS_DIR):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from combat_rl_dropout_update_ablation import _batch, _make_network  # noqa: E402
from combat_rl_inventory_embedding_successor import (  # noqa: E402
    _atomic_torch_save,
    _optimizer_state_count,
    _sha256,
    _state_dict_sha256,
    _validate_training_checkpoint,
)
from combat_rl_provenance_aware_successor import (  # noqa: E402
    _provenance_action_metrics,
    _relative_l2,
    _summary,
)
from spirecomm.ai.rl.v2.action_space import END_TURN_ACTION  # noqa: E402
from spirecomm.ai.rl.v2.replay_buffer import (
    NO_PROPOSED_ACTION,
    UNKNOWN_PROPOSED_ACTION,
)  # noqa: E402
from spirecomm.ai.rl.v2.state_encoder import StateEncoderV2  # noqa: E402
from spirecomm.ai.rl.v2.trainer import (  # noqa: E402
    parent_top_action_margin_guard_loss,
    provenance_balanced_parent_policy_anchor_loss,
)


VALIDATION_FRACTION = 0.2
SPLIT_SEED = 2026082807
TRAINING_SEED = 2026082808
LEARNING_RATE = 1e-4
BATCH_SIZE = 128
ANCHOR_WEIGHT = 1.0
DIRECT_MARGIN_WEIGHT = 1.0
DIRECT_MARGIN_CAP = 0.1
OPTIMIZER_STEPS = 64
GAMMA = 0.99
MINIMUM_OVERALL_DISAGREEMENT = 0.05
MAXIMUM_DIRECT_DISAGREEMENT = 0.10
MINIMUM_CHANGED_LABEL_UPLIFT = 0.10
MAXIMUM_POSITIVE_ENERGY_END_TURN_INCREASE = 2

FIXED_RECIPE = {
    "device": "cpu",
    "validation_fraction": VALIDATION_FRACTION,
    "split_seed": SPLIT_SEED,
    "training_seed": TRAINING_SEED,
    "learning_rate": LEARNING_RATE,
    "batch_size": BATCH_SIZE,
    "gamma": GAMMA,
    "optimizer_steps": OPTIMIZER_STEPS,
    "batch_direct_count": BATCH_SIZE // 2,
    "batch_changed_count": BATCH_SIZE // 2,
    "parent_policy_anchor_weight": ANCHOR_WEIGHT,
    "provenance_balanced_anchor": True,
    "direct_only_top_action_margin_guard": True,
    "top_action_margin_guard_weight": DIRECT_MARGIN_WEIGHT,
    "top_action_margin_guard_cap": DIRECT_MARGIN_CAP,
    "bootstrap_action_policy": "frozen_parent_masked_greedy",
    "decision_unit": "candidate_callable_smdp_span",
}

DEVELOPMENT_AUTHORITY = {
    "candidate": False,
    "communication_mod": False,
    "fresh_holdout": False,
    "gameplay": False,
    "model_fitting": True,
    "policy_quality": False,
    "production_checkpoint_writing": False,
    "promotion": False,
    "qualification": False,
    "training": True,
}


_STATE_FIELDS = ("continuous", "card_ids", "potion_ids", "relic_ids")
_NEXT_STATE_FIELDS = (
    "next_continuous",
    "next_card_ids",
    "next_potion_ids",
    "next_relic_ids",
)
_REQUIRED_FIELDS = (
    *_STATE_FIELDS,
    "actions",
    "rewards",
    *_NEXT_STATE_FIELDS,
    "dones",
    "action_masks",
    "next_action_masks",
    "anchor_to_executed_action",
    "proposed_action_indices",
)


def _validated_replay(replay: dict[str, Any], *, gamma: float) -> dict[str, torch.Tensor]:
    if not isinstance(replay, dict):
        raise ValueError("replay must be a mapping")
    if not math.isfinite(gamma) or not 0.0 < gamma <= 1.0:
        raise ValueError("gamma must be finite and within (0, 1]")
    tensors: dict[str, torch.Tensor] = {}
    count = None
    for field in _REQUIRED_FIELDS:
        value = replay.get(field)
        if not isinstance(value, torch.Tensor):
            raise ValueError(f"replay field must be a tensor: {field}")
        value = value.detach().cpu()
        if value.ndim == 0:
            raise ValueError(f"replay field must have a row dimension: {field}")
        if count is None:
            count = int(value.shape[0])
        elif int(value.shape[0]) != count:
            raise ValueError(f"replay row count mismatch: {field}")
        tensors[field] = value
    if not count:
        raise ValueError("replay must contain at least one transition")
    if tensors["dones"].dtype != torch.bool:
        raise ValueError("replay dones must be boolean")
    if tensors["action_masks"].dtype != torch.bool:
        raise ValueError("replay action masks must be boolean")
    if tensors["next_action_masks"].dtype != torch.bool:
        raise ValueError("replay next action masks must be boolean")
    if tensors["anchor_to_executed_action"].dtype != torch.bool:
        raise ValueError("replay anchor provenance must be boolean")
    for field in ("actions", "proposed_action_indices"):
        if tensors[field].dtype != torch.int64 or tensors[field].shape != (count,):
            raise ValueError(f"replay {field} must be int64 rows")
    if tensors["rewards"].shape != (count,):
        raise ValueError("replay rewards must be scalar rows")
    if tensors["action_masks"].ndim != 2:
        raise ValueError("replay action masks must be rank two")
    if tensors["next_action_masks"].shape != tensors["action_masks"].shape:
        raise ValueError("replay next action masks must match action masks")
    if not bool(tensors["dones"][-1]):
        raise ValueError("replay must be terminal-delimited")
    return tensors


def _validate_row_identity(
    replay: dict[str, torch.Tensor],
    index: int,
) -> None:
    proposed = int(replay["proposed_action_indices"][index].item())
    action = int(replay["actions"][index].item())
    override = bool(replay["anchor_to_executed_action"][index].item())
    mask = replay["action_masks"][index]
    action_dim = int(mask.shape[0])
    if proposed == UNKNOWN_PROPOSED_ACTION:
        raise ValueError(f"unknown proposal identity at source row {index}")
    if action < 0 or action >= action_dim or not bool(mask[action]):
        raise ValueError(f"invalid executed action at source row {index}")
    if proposed == NO_PROPOSED_ACTION:
        if not override:
            raise ValueError(f"no-proposal row lacks override at source row {index}")
        return
    if proposed < 0 or proposed >= action_dim or not bool(mask[proposed]):
        raise ValueError(f"invalid proposed action at source row {index}")
    if override != (proposed != action):
        raise ValueError(f"inconsistent proposal identity at source row {index}")


def _validate_successor_identity(
    replay: dict[str, torch.Tensor],
    source_end: int,
    next_decision: int,
) -> None:
    pairs = zip(_NEXT_STATE_FIELDS, _STATE_FIELDS)
    for next_field, state_field in pairs:
        if not torch.equal(
            replay[next_field][source_end],
            replay[state_field][next_decision],
        ):
            raise ValueError(
                "candidate decision successor identity mismatch: "
                f"{source_end} -> {next_decision} ({state_field})"
            )
    if not torch.equal(
        replay["next_action_masks"][source_end],
        replay["action_masks"][next_decision],
    ):
        raise ValueError(
            "candidate decision successor action mask mismatch: "
            f"{source_end} -> {next_decision}"
        )


def build_candidate_decision_spans(
    replay: dict[str, Any],
    *,
    gamma: float,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    """Collapse wrapper-controlled rows into deployment-consistent SMDP spans."""
    source = _validated_replay(replay, gamma=gamma)
    count = int(source["dones"].shape[0])
    for index in range(count):
        _validate_row_identity(source, index)

    groups: list[tuple[int, int]] = []
    group_start = 0
    for index, done in enumerate(source["dones"].tolist()):
        if done:
            groups.append((group_start, index))
            group_start = index + 1
    if group_start != count:
        raise ValueError("replay must be terminal-delimited")

    starts: list[int] = []
    ends: list[int] = []
    group_indices: list[int] = []
    span_lengths: list[int] = []
    accumulated_rewards: list[float] = []
    bootstrap_discounts: list[float] = []
    uncontrolled_prefix_count = 0
    attached_no_proposal_count = 0

    proposals = source["proposed_action_indices"]
    rewards = source["rewards"]
    for group_index, (start, end) in enumerate(groups):
        decision_rows = [
            index
            for index in range(start, end + 1)
            if int(proposals[index].item()) >= 0
        ]
        first_decision = decision_rows[0] if decision_rows else end + 1
        uncontrolled_prefix_count += first_decision - start
        for decision_offset, decision_start in enumerate(decision_rows):
            next_decision = (
                decision_rows[decision_offset + 1]
                if decision_offset + 1 < len(decision_rows)
                else None
            )
            source_end = (next_decision - 1) if next_decision is not None else end
            for index in range(decision_start + 1, source_end + 1):
                if int(proposals[index].item()) != NO_PROPOSED_ACTION:
                    raise ValueError(
                        f"unreconciled source row inside decision span: {index}"
                    )
            span_length = source_end - decision_start + 1
            reward = sum(
                (gamma**offset) * float(rewards[index].item())
                for offset, index in enumerate(
                    range(decision_start, source_end + 1)
                )
            )
            terminal = bool(source["dones"][source_end].item())
            if next_decision is not None:
                if terminal:
                    raise ValueError("terminal source row precedes a decision in one combat")
                _validate_successor_identity(source, source_end, next_decision)
            elif not terminal:
                raise ValueError("combat decision span does not end at terminal")
            starts.append(decision_start)
            ends.append(source_end)
            group_indices.append(group_index)
            span_lengths.append(span_length)
            accumulated_rewards.append(reward)
            bootstrap_discounts.append(0.0 if terminal else gamma**span_length)
            attached_no_proposal_count += span_length - 1

    start_indices = torch.tensor(starts, dtype=torch.int64)
    end_indices = torch.tensor(ends, dtype=torch.int64)
    if starts:
        spans = {
            field: source[field].index_select(0, start_indices)
            for field in (
                *_STATE_FIELDS,
                "actions",
                "action_masks",
                "anchor_to_executed_action",
                "proposed_action_indices",
            )
        }
        spans.update(
            {
                field: source[field].index_select(0, end_indices)
                for field in (*_NEXT_STATE_FIELDS, "next_action_masks", "dones")
            }
        )
    else:
        spans = {
            field: source[field][:0]
            for field in (
                *_STATE_FIELDS,
                "actions",
                *_NEXT_STATE_FIELDS,
                "dones",
                "action_masks",
                "next_action_masks",
                "anchor_to_executed_action",
                "proposed_action_indices",
            )
        }
    spans.update(
        {
            "rewards": torch.tensor(accumulated_rewards, dtype=torch.float32),
            "bootstrap_discounts": torch.tensor(
                bootstrap_discounts, dtype=torch.float32
            ),
            "source_start_indices": start_indices,
            "source_end_indices": end_indices,
            "span_lengths": torch.tensor(span_lengths, dtype=torch.int64),
            "combat_group_indices": torch.tensor(group_indices, dtype=torch.int64),
        }
    )

    decision_count = len(starts)
    direct_count = int((~spans["anchor_to_executed_action"]).sum().item())
    changed_count = int(spans["anchor_to_executed_action"].sum().item())
    reconciliation_count = (
        decision_count + attached_no_proposal_count + uncontrolled_prefix_count
    )
    if reconciliation_count != count:
        raise ValueError(
            "source row reconciliation failed: "
            f"{reconciliation_count} != {count}"
        )
    telemetry = {
        "source_transition_count": count,
        "combat_group_count": len(groups),
        "decision_span_count": decision_count,
        "direct_decision_count": direct_count,
        "changed_decision_count": changed_count,
        "attached_no_proposal_count": attached_no_proposal_count,
        "uncontrolled_prefix_count": uncontrolled_prefix_count,
        "source_row_reconciliation_count": reconciliation_count,
        "minimum_span_length": min(span_lengths) if span_lengths else 0,
        "maximum_span_length": max(span_lengths) if span_lengths else 0,
        "mean_span_length": (
            float(sum(span_lengths) / len(span_lengths)) if span_lengths else 0.0
        ),
    }
    return spans, telemetry


def _variable_bootstrap_targets(
    *,
    rewards: torch.Tensor,
    bootstrap_discounts: torch.Tensor,
    next_bootstrap: torch.Tensor,
) -> torch.Tensor:
    values = tuple(
        tensor.detach().float().reshape(-1)
        for tensor in (rewards, bootstrap_discounts, next_bootstrap)
    )
    reward, discounts, bootstrap = values
    if not reward.numel() or any(value.shape != reward.shape for value in values):
        raise ValueError("variable bootstrap tensors must have one equal nonzero shape")
    if not all(bool(torch.isfinite(value).all()) for value in values):
        raise ValueError("variable bootstrap tensors must be finite")
    if bool(((discounts < 0.0) | (discounts > 1.0)).any()):
        raise ValueError("bootstrap discounts must be within [0, 1]")
    return reward + discounts * bootstrap


def _validate_optimizer_batch_provenance(
    spans: dict[str, torch.Tensor],
    batches: tuple[torch.Tensor, ...] | list[torch.Tensor],
) -> dict[str, Any]:
    proposals = spans.get("proposed_action_indices")
    changed = spans.get("anchor_to_executed_action")
    if not isinstance(proposals, torch.Tensor) or not isinstance(changed, torch.Tensor):
        raise ValueError("span provenance tensors are missing")
    if proposals.shape != changed.shape or proposals.ndim != 1:
        raise ValueError("span provenance tensors must have equal row shape")
    direct_counts: list[int] = []
    changed_counts: list[int] = []
    ineligible_count = 0
    for batch in batches:
        indices = batch.detach().cpu().long().reshape(-1)
        if not indices.numel() or int(indices.min()) < 0 or int(indices.max()) >= len(
            proposals
        ):
            raise ValueError("optimizer batch indices are invalid")
        batch_proposals = proposals[indices]
        batch_changed = changed[indices].bool()
        ineligible = int((batch_proposals < 0).sum().item())
        ineligible_count += ineligible
        if ineligible:
            raise ValueError("optimizer batch contains a non candidate-callable row")
        direct_count = int((~batch_changed).sum().item())
        changed_count = int(batch_changed.sum().item())
        if direct_count <= 0 or changed_count <= 0:
            raise ValueError("optimizer batch must contain both direct and changed rows")
        direct_counts.append(direct_count)
        changed_counts.append(changed_count)
    if not direct_counts:
        raise ValueError("optimizer schedule is empty")
    return {
        "batch_count": len(direct_counts),
        "minimum_direct_count": min(direct_counts),
        "maximum_direct_count": max(direct_counts),
        "mean_direct_count": float(np.mean(direct_counts)),
        "minimum_changed_count": min(changed_counts),
        "maximum_changed_count": max(changed_counts),
        "mean_changed_count": float(np.mean(changed_counts)),
        "ineligible_sample_count": ineligible_count,
    }


def _stratified_optimizer_batches(
    spans: dict[str, torch.Tensor],
    train_indices: torch.Tensor,
    *,
    batch_size: int,
    optimizer_steps: int,
    seed: int,
) -> tuple[torch.Tensor, ...]:
    if batch_size <= 1 or batch_size % 2 or optimizer_steps <= 0:
        raise ValueError("stratified batch size must be positive and even")
    train = train_indices.detach().cpu().long().reshape(-1)
    changed = spans["anchor_to_executed_action"][train].bool()
    direct_rows = train[~changed].numpy()
    changed_rows = train[changed].numpy()
    per_stratum = batch_size // 2
    if len(direct_rows) < per_stratum or len(changed_rows) < per_stratum:
        raise ValueError(
            "training split must contain at least half a batch in each stratum"
        )
    rng = np.random.default_rng(seed)
    batches = []
    for _ in range(optimizer_steps):
        selected = np.concatenate(
            (
                rng.choice(direct_rows, size=per_stratum, replace=False),
                rng.choice(changed_rows, size=per_stratum, replace=False),
            )
        )
        batches.append(torch.from_numpy(rng.permutation(selected)).long())
    schedule = tuple(batches)
    _validate_optimizer_batch_provenance(spans, schedule)
    return schedule


def _split_candidate_spans(
    spans: dict[str, torch.Tensor],
    *,
    validation_fraction: float,
    seed: int,
) -> dict[str, Any]:
    groups = spans["combat_group_indices"].detach().cpu().long()
    unique_groups = torch.unique(groups, sorted=True)
    if unique_groups.numel() < 2:
        raise ValueError("candidate spans require at least two combat groups")
    rng = np.random.default_rng(seed)
    shuffled = rng.permutation(unique_groups.numpy())
    validation_count = min(
        max(1, int(round(len(shuffled) * validation_fraction))),
        len(shuffled) - 1,
    )
    validation_groups = torch.from_numpy(
        np.sort(shuffled[:validation_count])
    ).long()
    train_groups = torch.from_numpy(np.sort(shuffled[validation_count:])).long()
    validation_mask = torch.isin(groups, validation_groups)
    train_indices = torch.where(~validation_mask)[0].long()
    validation_indices = torch.where(validation_mask)[0].long()
    if not train_indices.numel() or not validation_indices.numel():
        raise ValueError("candidate span partition is empty")
    return {
        "train_indices": train_indices,
        "validation_indices": validation_indices,
        "train_group_indices": train_groups,
        "validation_group_indices": validation_groups,
        "combat_group_count": int(unique_groups.numel()),
    }


def _frozen_next_bootstrap(
    parent: torch.nn.Module,
    target: torch.nn.Module,
    spans: dict[str, torch.Tensor],
    indices: torch.Tensor,
) -> torch.Tensor:
    discounts = spans["bootstrap_discounts"][indices].float()
    bootstrap = torch.zeros(indices.numel(), dtype=torch.float32)
    active_rows = torch.where(discounts > 0.0)[0]
    if not active_rows.numel():
        return bootstrap
    active_indices = indices[active_rows]
    if not bool(spans["next_action_masks"][active_indices].any(dim=1).all()):
        raise ValueError("nonterminal SMDP span has no legal bootstrap action")
    with torch.no_grad():
        next_parent_q = parent(*_batch(spans, active_indices, "next_"))
        next_actions = next_parent_q.argmax(dim=1)
        next_target_q = target(*_batch(spans, active_indices, "next_"))
        bootstrap[active_rows] = next_target_q[
            torch.arange(active_rows.numel()), next_actions
        ]
    return bootstrap


def _fit_callability_candidate(
    *,
    metadata: dict[str, Any],
    parent_state: dict[str, torch.Tensor],
    target_state: dict[str, torch.Tensor],
    spans: dict[str, torch.Tensor],
    train_indices: torch.Tensor,
    learning_rate: float = LEARNING_RATE,
    batch_size: int = BATCH_SIZE,
    optimizer_steps: int = OPTIMIZER_STEPS,
    seed: int = TRAINING_SEED,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    if not math.isfinite(learning_rate) or learning_rate <= 0.0:
        raise ValueError("learning rate must be finite and positive")
    torch.manual_seed(seed)
    online = _make_network(metadata, parent_state)
    parent = _make_network(metadata, parent_state)
    target = _make_network(metadata, target_state)
    parent.eval()
    target.eval()
    optimizer = torch.optim.Adam(online.parameters(), lr=learning_rate)
    batches = _stratified_optimizer_batches(
        spans,
        train_indices,
        batch_size=batch_size,
        optimizer_steps=optimizer_steps,
        seed=seed,
    )
    totals: list[float] = []
    td_losses: list[float] = []
    anchor_losses: list[float] = []
    direct_anchor_losses: list[float] = []
    changed_anchor_losses: list[float] = []
    margin_losses: list[float] = []
    margin_eligible: list[float] = []
    margin_violations: list[float] = []
    for update_index, indices in enumerate(batches):
        online.train()
        torch.manual_seed(seed * 100_000 + update_index)
        current_q = online(*_batch(spans, indices))
        actions = spans["actions"][indices].long()
        selected_q = current_q[torch.arange(indices.numel()), actions]
        with torch.no_grad():
            parent_q = parent(*_batch(spans, indices))
            parent_actions = parent_q.argmax(dim=1)
            next_bootstrap = _frozen_next_bootstrap(
                parent, target, spans, indices
            )
            targets = _variable_bootstrap_targets(
                rewards=spans["rewards"][indices],
                bootstrap_discounts=spans["bootstrap_discounts"][indices],
                next_bootstrap=next_bootstrap,
            )
        td_loss = F.smooth_l1_loss(selected_q, targets)
        changed = spans["anchor_to_executed_action"][indices].bool()
        anchor_targets = torch.where(changed, actions, parent_actions)
        anchor_loss, anchor_telemetry = (
            provenance_balanced_parent_policy_anchor_loss(
                current_q,
                anchor_targets,
                changed,
            )
        )
        margin_loss, eligible_count, violation_count = (
            parent_top_action_margin_guard_loss(
                current_q,
                parent_q,
                spans["action_masks"][indices].bool(),
                margin_cap=DIRECT_MARGIN_CAP,
                eligible_rows=~changed,
            )
        )
        loss = (
            td_loss
            + ANCHOR_WEIGHT * anchor_loss
            + DIRECT_MARGIN_WEIGHT * margin_loss
        )
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("optimizer produced a non-finite objective")
        optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(online.parameters(), max_norm=10.0)
        optimizer.step()
        totals.append(float(loss.item()))
        td_losses.append(float(td_loss.item()))
        anchor_losses.append(float(anchor_loss.item()))
        direct_anchor_losses.append(float(anchor_telemetry["direct_loss"]))
        changed_anchor_losses.append(float(anchor_telemetry["override_loss"]))
        margin_losses.append(float(margin_loss.item()))
        margin_eligible.append(float(eligible_count))
        margin_violations.append(float(violation_count))

    candidate = {
        name: value.detach().cpu().clone()
        for name, value in online.state_dict().items()
    }
    telemetry = {
        "optimizer_update_count": len(totals),
        "total_loss": _summary(totals),
        "td_loss": _summary(td_losses),
        "parent_policy_anchor_loss": _summary(anchor_losses),
        "parent_policy_anchor_direct_loss": _summary(direct_anchor_losses),
        "parent_policy_anchor_changed_loss": _summary(changed_anchor_losses),
        "parent_top_action_margin_guard_loss": _summary(margin_losses),
        "parent_top_action_margin_guard_eligible_count": _summary(
            margin_eligible
        ),
        "parent_top_action_margin_guard_ranking_violation_count": _summary(
            margin_violations
        ),
        "batch_provenance": _validate_optimizer_batch_provenance(spans, batches),
        "all_objective_values_finite": all(
            math.isfinite(value)
            for series in (
                totals,
                td_losses,
                anchor_losses,
                direct_anchor_losses,
                changed_anchor_losses,
                margin_losses,
                margin_eligible,
                margin_violations,
            )
            for value in series
        ),
    }
    return candidate, telemetry


def _evaluate_callability_partition(
    *,
    metadata: dict[str, Any],
    parent_state: dict[str, torch.Tensor],
    target_state: dict[str, torch.Tensor],
    candidate_state: dict[str, torch.Tensor],
    spans: dict[str, torch.Tensor],
    indices: torch.Tensor,
) -> dict[str, Any]:
    parent = _make_network(metadata, parent_state)
    target = _make_network(metadata, target_state)
    candidate = _make_network(metadata, candidate_state)
    parent.eval()
    target.eval()
    candidate.eval()
    actions = spans["actions"][indices].long()
    rows = torch.arange(indices.numel())
    with torch.no_grad():
        parent_q = parent(*_batch(spans, indices))
        candidate_q = candidate(*_batch(spans, indices))
        targets = _variable_bootstrap_targets(
            rewards=spans["rewards"][indices],
            bootstrap_discounts=spans["bootstrap_discounts"][indices],
            next_bootstrap=_frozen_next_bootstrap(parent, target, spans, indices),
        )
    parent_actions = parent_q.argmax(dim=1)
    candidate_actions = candidate_q.argmax(dim=1)
    provenance = _provenance_action_metrics(
        parent_actions=parent_actions,
        candidate_actions=candidate_actions,
        executed_actions=actions,
        overrides=spans["anchor_to_executed_action"][indices],
    )
    provenance.pop("anchor_labels")
    continuous = spans["continuous"][indices].float()
    positive_energy = (
        continuous[:, StateEncoderV2.ENERGY_RATIO_INDEX].gt(0.0)
        if continuous.shape[1] > StateEncoderV2.ENERGY_RATIO_INDEX
        else torch.zeros(indices.numel(), dtype=torch.bool)
    )
    parent_end_turn = int(
        (positive_energy & parent_actions.eq(END_TURN_ACTION)).sum().item()
    )
    candidate_end_turn = int(
        (positive_energy & candidate_actions.eq(END_TURN_ACTION)).sum().item()
    )
    return {
        "decision_span_count": int(indices.numel()),
        "source_transition_count": int(
            spans["span_lengths"][indices].sum().item()
        ),
        "parent_smooth_l1": float(
            F.smooth_l1_loss(parent_q[rows, actions], targets).item()
        ),
        "candidate_smooth_l1": float(
            F.smooth_l1_loss(candidate_q[rows, actions], targets).item()
        ),
        "parent_anchor_label_agreement": provenance[
            "parent_anchor_label_agreement"
        ],
        "candidate_anchor_label_agreement": provenance[
            "candidate_anchor_label_agreement"
        ],
        "action_disagreement_count": provenance["action_disagreement_count"],
        "action_disagreement_share": provenance["action_disagreement_share"],
        "positive_energy_state_count": int(positive_energy.sum().item()),
        "parent_positive_energy_end_turn_count": parent_end_turn,
        "candidate_positive_energy_end_turn_count": candidate_end_turn,
        "positive_energy_end_turn_count_delta": candidate_end_turn - parent_end_turn,
        "span_lengths": _summary(
            [float(value) for value in spans["span_lengths"][indices].tolist()]
        ),
        "bootstrap_discounts": _summary(
            [
                float(value)
                for value in spans["bootstrap_discounts"][indices].tolist()
            ]
        ),
        "strata": {
            "direct": provenance["direct"],
            "changed_proposal": provenance["override"],
        },
    }


def _callability_eligibility(
    *,
    validation: dict[str, Any],
    training: dict[str, Any],
    candidate_round_trip_exact: bool,
    callability_complete: bool,
) -> dict[str, bool]:
    direct = validation["strata"]["direct"]
    changed = validation["strata"]["changed_proposal"]
    changed_uplift = float(changed["candidate_anchor_label_agreement"]) - float(
        changed["parent_anchor_label_agreement"]
    )
    batch = training["batch_provenance"]
    checks = {
        "metrics_finite": all(
            math.isfinite(float(validation[name]))
            for name in (
                "parent_smooth_l1",
                "candidate_smooth_l1",
                "action_disagreement_share",
            )
        ),
        "optimizer_budget_exact": int(training["optimizer_update_count"])
        == OPTIMIZER_STEPS,
        "objective_values_finite": bool(training["all_objective_values_finite"]),
        "candidate_round_trip_exact": bool(candidate_round_trip_exact),
        "callability_complete": bool(callability_complete),
        "optimizer_batches_candidate_callable": int(
            batch["ineligible_sample_count"]
        )
        == 0,
        "every_batch_contains_both_strata": int(batch["minimum_direct_count"])
        > 0
        and int(batch["minimum_changed_count"]) > 0,
        "validation_smdp_td_improved": float(validation["candidate_smooth_l1"])
        < float(validation["parent_smooth_l1"]),
        "overall_parent_disagreement_at_least_material_floor": float(
            validation["action_disagreement_share"]
        )
        >= MINIMUM_OVERALL_DISAGREEMENT,
        "direct_parent_disagreement_at_most_ceiling": float(
            direct["action_disagreement_share"]
        )
        <= MAXIMUM_DIRECT_DISAGREEMENT,
        "changed_proposal_executed_label_uplift_at_least_floor": changed_uplift
        >= MINIMUM_CHANGED_LABEL_UPLIFT,
        "positive_energy_end_turn_increase_bounded": int(
            validation["positive_energy_end_turn_count_delta"]
        )
        <= MAXIMUM_POSITIVE_ENERGY_END_TURN_INCREASE,
        "validation_strata_nonempty": int(direct["transition_count"]) > 0
        and int(changed["transition_count"]) > 0,
    }
    checks["all_conditions_passed"] = all(checks.values())
    return checks


def _validate_callability_checkpoint(
    checkpoint: dict[str, Any],
    *,
    expected_transition_count: int,
) -> tuple[dict[str, Any], dict[str, torch.Tensor], dict[str, int]]:
    if int(checkpoint.get("checkpoint_schema_version", -1)) != 2:
        raise ValueError("callability checkpoint must use training schema version 2")
    if checkpoint.get("checkpoint_kind") != "training":
        raise ValueError("callability checkpoint must be a training checkpoint")
    if _optimizer_state_count(checkpoint) != 0:
        raise ValueError("callability checkpoint optimizer state must be empty")
    metadata, replay = _validate_training_checkpoint(
        checkpoint, expected_transition_count=expected_transition_count
    )
    if int(replay.get("schema_version", -1)) != 3:
        raise ValueError("callability replay must use schema version 3")
    proposed = replay.get("proposed_action_indices")
    overrides = replay.get("anchor_to_executed_action")
    if not isinstance(proposed, torch.Tensor) or proposed.dtype != torch.int64:
        raise ValueError("callability replay proposal identity is missing")
    if not isinstance(overrides, torch.Tensor) or overrides.dtype != torch.bool:
        raise ValueError("callability replay anchor provenance is missing")
    if tuple(proposed.shape) != (expected_transition_count,) or tuple(
        overrides.shape
    ) != (expected_transition_count,):
        raise ValueError("callability replay provenance shape is invalid")
    if bool(proposed.eq(UNKNOWN_PROPOSED_ACTION).any()):
        raise ValueError("callability replay contains unknown proposal identity")
    actions = replay["actions"].long()
    proposal_rows = proposed.ge(0)
    direct = proposal_rows & proposed.eq(actions)
    changed = proposal_rows & proposed.ne(actions)
    no_proposal = proposed.eq(NO_PROPOSED_ACTION)
    if not bool((direct | changed | no_proposal).all()):
        raise ValueError("callability replay proposal classes do not reconcile")
    if not bool((overrides == (changed | no_proposal)).all()):
        raise ValueError("callability replay override classes do not reconcile")
    masks = replay["action_masks"].bool()
    rows = torch.arange(expected_transition_count)
    if not bool(masks[rows, actions].all()):
        raise ValueError("callability replay executed action is illegal")
    if not bool(masks[rows[proposal_rows], proposed[proposal_rows]].all()):
        raise ValueError("callability replay proposed action is illegal")
    counts = {
        "direct_unchanged_proposal_count": int(direct.sum().item()),
        "changed_same_state_proposal_count": int(changed.sum().item()),
        "no_proposal_takeover_count": int(no_proposal.sum().item()),
        "legacy_unknown_count": 0,
    }
    if counts["direct_unchanged_proposal_count"] <= 0 or counts[
        "changed_same_state_proposal_count"
    ] <= 0:
        raise ValueError("callability replay must contain both candidate strata")
    return metadata, replay, counts


def _validate_registration_recipe(registration: dict[str, Any]) -> None:
    if registration.get("schema_version") != 1:
        raise ValueError("registration schema version changed")
    if registration.get("fit_recipe") != FIXED_RECIPE:
        raise ValueError("registration fit recipe changed")
    collection = registration.get("collection", {})
    if collection.get("game_count") != 10:
        raise ValueError("registration game count changed")
    if collection.get("epsilon") != 0.0 or collection.get("learning_starts") != 100000:
        raise ValueError("registration zero-update collection changed")
    if collection.get("optimizer_updates") != 0:
        raise ValueError("registration optimizer update boundary changed")


def run(args: argparse.Namespace) -> dict[str, Any]:
    registration_path = args.registration.resolve()
    checkpoint_path = args.training_checkpoint.resolve()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    if _sha256(registration_path) != args.registration_sha256:
        raise ValueError("registration hash mismatch")
    if _sha256(checkpoint_path) != args.expected_checkpoint_sha256:
        raise ValueError("training checkpoint hash mismatch")
    registration = json.loads(registration_path.read_text(encoding="utf-8"))
    _validate_registration_recipe(registration)
    if registration.get("experiment_id") != args.experiment_id:
        raise ValueError("registration experiment id changed")
    checkpoint = torch.load(checkpoint_path, map_location="cpu", weights_only=True)
    metadata, replay, provenance_counts = _validate_callability_checkpoint(
        checkpoint,
        expected_transition_count=args.expected_transition_count,
    )
    parent_state = checkpoint["online_network_state_dict"]
    target_state = checkpoint["target_network_state_dict"]
    if _state_dict_sha256(parent_state) != _state_dict_sha256(target_state):
        raise ValueError("callability checkpoint parent and target differ")
    spans, span_telemetry = build_candidate_decision_spans(replay, gamma=GAMMA)
    split = _split_candidate_spans(
        spans,
        validation_fraction=VALIDATION_FRACTION,
        seed=SPLIT_SEED,
    )
    train_indices = split["train_indices"]
    validation_indices = split["validation_indices"]
    for label, indices in (
        ("training", train_indices),
        ("validation", validation_indices),
    ):
        changed = spans["anchor_to_executed_action"][indices].bool()
        if not bool(changed.any()) or not bool((~changed).any()):
            raise ValueError(f"{label} candidate strata are empty")
    candidate_state, training = _fit_callability_candidate(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        spans=spans,
        train_indices=train_indices,
    )
    train_evaluation = _evaluate_callability_partition(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        candidate_state=candidate_state,
        spans=spans,
        indices=train_indices,
    )
    validation = _evaluate_callability_partition(
        metadata=metadata,
        parent_state=parent_state,
        target_state=target_state,
        candidate_state=candidate_state,
        spans=spans,
        indices=validation_indices,
    )

    staging = output_dir.with_name(f".{output_dir.name}.{os.getpid()}.staging")
    if staging.exists():
        raise ValueError(f"staging directory already exists: {staging}")
    staging.mkdir(parents=True)
    try:
        checkpoint_output = staging / "callability_filtered_candidate.pth"
        _atomic_torch_save(
            {
                "checkpoint_schema_version": 1,
                "checkpoint_kind": "callability_filtered_development_candidate",
                "production_compatible": False,
                "metadata": metadata,
                "online_network_state_dict": candidate_state,
                "source": {
                    "experiment_id": args.experiment_id,
                    "source_commit": args.source_commit,
                    "training_checkpoint_sha256": args.expected_checkpoint_sha256,
                },
                "authority": DEVELOPMENT_AUTHORITY,
            },
            checkpoint_output,
        )
        reloaded = torch.load(checkpoint_output, map_location="cpu", weights_only=True)
        round_trip_exact = _state_dict_sha256(
            reloaded["online_network_state_dict"]
        ) == _state_dict_sha256(candidate_state)
        eligibility = _callability_eligibility(
            validation=validation,
            training=training,
            candidate_round_trip_exact=round_trip_exact,
            callability_complete=(
                span_telemetry["source_row_reconciliation_count"]
                == span_telemetry["source_transition_count"]
            ),
        )
        report = {
            "schema_version": 1,
            "experiment_id": args.experiment_id,
            "source_commit": args.source_commit,
            "decision": (
                "eligible_for_separate_fresh_holdout_only"
                if eligibility["all_conditions_passed"]
                else "development_candidate_not_eligible_move_to_residual_head"
            ),
            "bindings": {
                "registration": {
                    "path": str(registration_path),
                    "sha256": args.registration_sha256,
                },
                "training_checkpoint": {
                    "path": str(checkpoint_path),
                    "sha256": args.expected_checkpoint_sha256,
                    "transition_count": args.expected_transition_count,
                    "parent_state_dict_sha256": _state_dict_sha256(parent_state),
                },
            },
            "recipe": FIXED_RECIPE,
            "source_provenance": provenance_counts,
            "span_telemetry": span_telemetry,
            "partition": {
                "unit": "terminal_delimited_combat_group",
                "combat_group_count": split["combat_group_count"],
                "training_group_indices": split["train_group_indices"].tolist(),
                "validation_group_indices": split[
                    "validation_group_indices"
                ].tolist(),
                "training_decision_span_count": int(train_indices.numel()),
                "validation_decision_span_count": int(
                    validation_indices.numel()
                ),
            },
            "training": training,
            "train_evaluation": train_evaluation,
            "validation": validation,
            "parameter_movement": {
                "parent_state_dict_sha256": _state_dict_sha256(parent_state),
                "candidate_state_dict_sha256": _state_dict_sha256(candidate_state),
                "whole_model_relative_l2": _relative_l2(
                    candidate_state, parent_state
                ),
            },
            "eligibility": eligibility,
            "candidate": {
                "path": checkpoint_output.name,
                "sha256": _sha256(checkpoint_output),
                "size_bytes": checkpoint_output.stat().st_size,
                "round_trip_state_exact": round_trip_exact,
                "production_compatible": False,
            },
            "authority": DEVELOPMENT_AUTHORITY,
            "limitations": [
                "The fresh cohort is development-only and cannot serve as its own holdout.",
                "A failed fixed fit closes this corpus to alternate recipes and directs the next change to residual or separate-head architecture.",
            ],
        }
        (staging / "report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        os.replace(staging, output_dir)
        return report
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Fit one fixed candidate-callable combat RL successor."
    )
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--registration-sha256", required=True)
    parser.add_argument("--training-checkpoint", type=Path, required=True)
    parser.add_argument("--expected-checkpoint-sha256", required=True)
    parser.add_argument("--expected-transition-count", type=int, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--experiment-id", required=True)
    parser.add_argument("--source-commit", required=True)
    return parser.parse_args()


if __name__ == "__main__":
    run(_parse_args())
