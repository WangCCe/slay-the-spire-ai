"""Test whether LightSTS guard labels improve real replay intervention selectivity.

This is an exploratory development POC. It fits intervention classifiers only,
does not construct a policy candidate, and grants no qualification authority.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import sys
from typing import Any, Mapping, Sequence

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import load_native_module  # noqa: E402
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
    FROZEN_PARENT_RAW_GREEDY_BOOTSTRAP,
    GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    ONE_STEP_TD_TARGET,
    SmokeConfig,
    collect_transitions,
    create_fresh_trainer,
    initialize_trainer,
    load_initial_checkpoint,
    parameter_sha256,
    sha256_file,
)
from analysis_scripts.combat_rl_candidate_callability_successor import (  # noqa: E402
    _validate_callability_checkpoint,
    build_candidate_decision_spans,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


SCHEMA_VERSION = "combat-rl-lightspeed-guard-transfer-poc-v1"
GAMMA = 0.99
SIMULATOR_TRAINING_SEED = 2026082814
REAL_SPLIT_SEED = 2026082815
CLASSIFIER_SEED = 2026082816
FOLD_COUNT = 5
HIDDEN_DIM = 64
SIMULATOR_UPDATES = 128
REAL_UPDATES = 128
BATCH_SIZE = 64
LEARNING_RATE = 0.001
DIRECT_OPEN_CAP = 0.10


def _parse_range(value: str) -> tuple[int, ...]:
    text = value.strip()
    if ".." in text:
        first, last = (int(part) for part in text.split("..", 1))
        if last < first:
            raise argparse.ArgumentTypeError("range end precedes start")
        return tuple(range(first, last + 1))
    return tuple(int(part.strip()) for part in text.split(",") if part.strip())


def binary_roc_auc(scores: torch.Tensor, labels: torch.Tensor) -> float:
    values = scores.detach().cpu().double().numpy().reshape(-1)
    targets = labels.detach().cpu().bool().numpy().reshape(-1)
    if values.shape != targets.shape or not values.size:
        raise ValueError("AUC inputs must have one equal non-empty shape")
    positive_count = int(targets.sum())
    negative_count = int((~targets).sum())
    if not positive_count or not negative_count:
        raise ValueError("AUC requires both classes")
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(values.size, dtype=np.float64)
    start = 0
    while start < values.size:
        end = start + 1
        while end < values.size and values[order[end]] == values[order[start]]:
            end += 1
        ranks[order[start:end]] = 0.5 * (start + 1 + end)
        start = end
    rank_sum = float(ranks[targets].sum())
    return (
        rank_sum - positive_count * (positive_count + 1) / 2.0
    ) / (positive_count * negative_count)


def threshold_at_direct_open_cap(
    scores: torch.Tensor,
    labels: torch.Tensor,
    *,
    cap: float = DIRECT_OPEN_CAP,
) -> float:
    values = scores.detach().cpu().double().reshape(-1)
    targets = labels.detach().cpu().bool().reshape(-1)
    if values.shape != targets.shape or not values.numel():
        raise ValueError("threshold inputs must have one equal non-empty shape")
    if not bool(targets.any()) or not bool((~targets).any()):
        raise ValueError("threshold calibration requires both classes")
    candidates = torch.cat(
        (torch.tensor([math.inf], dtype=torch.float64), torch.unique(values))
    )
    best_threshold = math.inf
    best_recall = -1.0
    best_precision = -1.0
    for threshold in sorted(candidates.tolist(), reverse=True):
        opened = values >= threshold
        false_positive_rate = float(opened[~targets].double().mean().item())
        if false_positive_rate > cap + 1e-12:
            continue
        recall = float(opened[targets].double().mean().item())
        precision = (
            float(targets[opened].double().mean().item())
            if bool(opened.any())
            else 1.0
        )
        if (recall, precision, threshold) > (
            best_recall,
            best_precision,
            best_threshold,
        ):
            best_threshold = threshold
            best_recall = recall
            best_precision = precision
    return float(best_threshold)


def intervention_metrics(
    scores: torch.Tensor,
    labels: torch.Tensor,
    *,
    thresholds: torch.Tensor | float,
) -> dict[str, Any]:
    scores = scores.detach().cpu().float().reshape(-1)
    labels = labels.detach().cpu().bool().reshape(-1)
    threshold_tensor = torch.as_tensor(thresholds, dtype=torch.float32)
    if threshold_tensor.ndim == 0:
        threshold_tensor = threshold_tensor.expand_as(scores)
    if scores.shape != labels.shape or threshold_tensor.shape != scores.shape:
        raise ValueError("metric inputs must have equal row shape")
    opened = scores >= threshold_tensor
    true_positive = int((opened & labels).sum().item())
    false_positive = int((opened & ~labels).sum().item())
    return {
        "row_count": int(scores.numel()),
        "changed_count": int(labels.sum().item()),
        "direct_count": int((~labels).sum().item()),
        "roc_auc": binary_roc_auc(scores, labels),
        "changed_open_share": float(opened[labels].float().mean().item()),
        "direct_open_share": float(opened[~labels].float().mean().item()),
        "opened_precision": (
            float(true_positive / (true_positive + false_positive))
            if true_positive + false_positive
            else None
        ),
        "score": _summary(scores.tolist()),
        "changed_score": _summary(scores[labels].tolist()),
        "direct_score": _summary(scores[~labels].tolist()),
    }


def _summary(values: Sequence[float]) -> dict[str, float | int | None]:
    rows = np.asarray(values, dtype=np.float64)
    if not rows.size:
        return {"count": 0, "minimum": None, "mean": None, "maximum": None}
    return {
        "count": int(rows.size),
        "minimum": float(rows.min()),
        "mean": float(rows.mean()),
        "maximum": float(rows.max()),
    }


class InterventionClassifier(nn.Module):
    def __init__(self, input_dim: int) -> None:
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(input_dim, HIDDEN_DIM),
            nn.ReLU(),
            nn.Linear(HIDDEN_DIM, 1),
        )

    def forward(self, features: torch.Tensor) -> torch.Tensor:
        return self.layers(features.float()).squeeze(1)


def fit_classifier(
    features: torch.Tensor,
    labels: torch.Tensor,
    indices: torch.Tensor,
    *,
    seed: int,
    updates: int,
    initial_state: Mapping[str, torch.Tensor] | None = None,
) -> tuple[InterventionClassifier, list[float]]:
    indices = indices.detach().cpu().long().reshape(-1)
    selected_labels = labels[indices].bool()
    positive = indices[selected_labels]
    negative = indices[~selected_labels]
    if positive.numel() < 2 or negative.numel() < 2:
        raise ValueError("classifier fit requires both classes")
    torch.manual_seed(seed)
    model = InterventionClassifier(features.shape[1])
    if initial_state is not None:
        model.load_state_dict(initial_state, strict=True)
    optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
    generator = torch.Generator().manual_seed(seed)
    per_class = BATCH_SIZE // 2
    losses: list[float] = []
    for _ in range(updates):
        positive_rows = positive[
            torch.randint(positive.numel(), (per_class,), generator=generator)
        ]
        negative_rows = negative[
            torch.randint(negative.numel(), (per_class,), generator=generator)
        ]
        batch = torch.cat((positive_rows, negative_rows))
        batch = batch[torch.randperm(batch.numel(), generator=generator)]
        logits = model(features[batch])
        loss = F.binary_cross_entropy_with_logits(logits, labels[batch].float())
        optimizer.zero_grad()
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().item()))
    if not all(math.isfinite(value) for value in losses):
        raise RuntimeError("classifier produced a non-finite loss")
    return model, losses


def classifier_scores(
    model: InterventionClassifier, features: torch.Tensor
) -> torch.Tensor:
    model.eval()
    with torch.no_grad():
        return torch.sigmoid(model(features)).cpu()


def parent_feature_views(
    parent: nn.Module,
    *,
    continuous: torch.Tensor,
    card_ids: torch.Tensor,
    potion_ids: torch.Tensor,
    relic_ids: torch.Tensor,
    action_masks: torch.Tensor,
) -> dict[str, torch.Tensor]:
    parent.eval()
    with torch.no_grad():
        card_embed = parent.card_embedding(card_ids.long()).flatten(1)
        potion_embed = parent.potion_embedding(potion_ids.long()).flatten(1)
        relic_embed = parent.relic_embedding(relic_ids.long()).flatten(1)
        raw_inputs = torch.cat(
            (continuous.float(), card_embed, potion_embed, relic_embed), dim=1
        )
        latent = parent.hidden_layers(raw_inputs)
        if hasattr(parent, "value_stream") and hasattr(parent, "advantage_stream"):
            values = parent.value_stream(latent)
            advantages = parent.advantage_stream(latent)
            q_values = values + advantages - advantages.mean(dim=1, keepdim=True)
        else:
            q_values = parent.output_layer(latent)
    masks = action_masks.float()
    return {
        "legacy": torch.cat((continuous.float(), q_values, masks), dim=1).cpu(),
        "parent_latent": torch.cat((latent, q_values, masks), dim=1).cpu(),
    }


def _real_folds(groups: torch.Tensor) -> tuple[torch.Tensor, ...]:
    unique = torch.unique(groups.detach().cpu().long(), sorted=True)
    if unique.numel() < FOLD_COUNT:
        raise ValueError("real replay has too few combat groups")
    shuffled = np.random.default_rng(REAL_SPLIT_SEED).permutation(unique.numpy())
    return tuple(torch.from_numpy(np.asarray(rows)).long() for rows in np.array_split(shuffled, FOLD_COUNT))


def _cross_fitted_real_scores(
    *,
    real_features: Mapping[str, torch.Tensor],
    real_labels: torch.Tensor,
    real_groups: torch.Tensor,
    sim_features: torch.Tensor,
    sim_labels: torch.Tensor,
    sim_train_indices: torch.Tensor,
) -> tuple[dict[str, torch.Tensor], dict[str, Any]]:
    row_count = real_labels.numel()
    names = ("legacy_real_only", "latent_real_only", "latent_sim_pretrained")
    scores = {name: torch.empty(row_count) for name in names}
    thresholds = {name: torch.empty(row_count) for name in names}
    losses: dict[str, list[float]] = {name: [] for name in names}

    simulator_model, simulator_losses = fit_classifier(
        sim_features,
        sim_labels,
        sim_train_indices,
        seed=CLASSIFIER_SEED,
        updates=SIMULATOR_UPDATES,
    )
    simulator_state = copy.deepcopy(simulator_model.state_dict())
    folds = _real_folds(real_groups)
    for fold_index, validation_groups in enumerate(folds):
        validation_mask = torch.isin(real_groups, validation_groups)
        validation_indices = torch.where(validation_mask)[0]
        training_indices = torch.where(~validation_mask)[0]
        for name, feature_name, initial_state in (
            ("legacy_real_only", "legacy", None),
            ("latent_real_only", "parent_latent", None),
            ("latent_sim_pretrained", "parent_latent", simulator_state),
        ):
            model, fold_losses = fit_classifier(
                real_features[feature_name],
                real_labels,
                training_indices,
                seed=CLASSIFIER_SEED + 100 + fold_index,
                updates=REAL_UPDATES,
                initial_state=initial_state,
            )
            all_scores = classifier_scores(model, real_features[feature_name])
            threshold = threshold_at_direct_open_cap(
                all_scores[training_indices], real_labels[training_indices]
            )
            scores[name][validation_indices] = all_scores[validation_indices]
            thresholds[name][validation_indices] = threshold
            losses[name].extend(fold_losses)
    telemetry = {
        "fold_count": FOLD_COUNT,
        "combat_group_count": int(torch.unique(real_groups).numel()),
        "simulator_pretraining_loss": _summary(simulator_losses),
        "real_fitting_loss": {
            name: _summary(values) for name, values in losses.items()
        },
    }
    return {
        name: torch.stack((scores[name], thresholds[name])) for name in names
    }, telemetry


def _independent_holdout_scores(
    *,
    development_features: Mapping[str, torch.Tensor],
    development_labels: torch.Tensor,
    holdout_features: Mapping[str, torch.Tensor],
    holdout_labels: torch.Tensor,
    sim_features: torch.Tensor,
    sim_labels: torch.Tensor,
    sim_train_indices: torch.Tensor,
) -> tuple[dict[str, dict[str, Any]], dict[str, Any]]:
    simulator_model, simulator_losses = fit_classifier(
        sim_features,
        sim_labels,
        sim_train_indices,
        seed=CLASSIFIER_SEED,
        updates=SIMULATOR_UPDATES,
    )
    simulator_state = copy.deepcopy(simulator_model.state_dict())
    development_indices = torch.arange(development_labels.numel())
    results: dict[str, dict[str, Any]] = {}
    losses: dict[str, dict[str, float | int | None]] = {}
    for offset, (name, feature_name, initial_state) in enumerate(
        (
            ("legacy_real_only", "legacy", None),
            ("latent_real_only", "parent_latent", None),
            ("latent_sim_pretrained", "parent_latent", simulator_state),
        )
    ):
        model, fit_losses = fit_classifier(
            development_features[feature_name],
            development_labels,
            development_indices,
            seed=CLASSIFIER_SEED + 500 + offset,
            updates=REAL_UPDATES,
            initial_state=initial_state,
        )
        development_scores = classifier_scores(
            model, development_features[feature_name]
        )
        threshold = threshold_at_direct_open_cap(
            development_scores, development_labels
        )
        holdout_scores = classifier_scores(model, holdout_features[feature_name])
        metrics = intervention_metrics(
            holdout_scores, holdout_labels, thresholds=threshold
        )
        metrics["development_calibrated_threshold"] = threshold
        results[name] = metrics
        losses[name] = _summary(fit_losses)
    return results, {
        "simulator_pretraining_loss": _summary(simulator_losses),
        "development_fitting_loss": losses,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    for path, expected, label in (
        (args.module, args.expected_module_sha256, "native module"),
        (args.items_json, args.expected_items_sha256, "items.json"),
        (args.parent_checkpoint, args.expected_parent_sha256, "parent checkpoint"),
        (args.real_checkpoint, args.expected_real_sha256, "real checkpoint"),
    ):
        if sha256_file(path.resolve()) != expected.lower():
            raise ValueError(f"{label} hash mismatch")
    holdout_supplied = any(
        value is not None
        for value in (
            args.holdout_real_checkpoint,
            args.expected_holdout_real_sha256,
            args.expected_holdout_real_transition_count,
        )
    )
    if holdout_supplied and not all(
        value is not None
        for value in (
            args.holdout_real_checkpoint,
            args.expected_holdout_real_sha256,
            args.expected_holdout_real_transition_count,
        )
    ):
        raise ValueError("holdout checkpoint arguments must be supplied together")
    if holdout_supplied and sha256_file(args.holdout_real_checkpoint.resolve()) != (
        args.expected_holdout_real_sha256.lower()
    ):
        raise ValueError("holdout real checkpoint hash mismatch")

    id_mapper = build_id_mapper(args.items_json)
    initial_checkpoint = load_initial_checkpoint(
        args.parent_checkpoint,
        expected_sha256=args.expected_parent_sha256,
    )
    trainer = create_fresh_trainer(
        id_mapper,
        seed=CLASSIFIER_SEED,
        batch_size=BATCH_SIZE,
        learning_starts=BATCH_SIZE,
    )
    parent_state, _ = initialize_trainer(trainer, initial_checkpoint)
    parent = trainer.online_network

    real_checkpoint = torch.load(
        args.real_checkpoint, map_location="cpu", weights_only=True
    )
    _, replay, provenance = _validate_callability_checkpoint(
        real_checkpoint,
        expected_transition_count=args.expected_real_transition_count,
    )
    if parameter_sha256(parent_state) != parameter_sha256(
        real_checkpoint["online_network_state_dict"]
    ):
        raise ValueError("simulator and real replay parents differ")
    real_spans, real_span_telemetry = build_candidate_decision_spans(
        replay, gamma=GAMMA
    )
    real_labels = real_spans["anchor_to_executed_action"].bool().cpu()
    real_features = parent_feature_views(
        parent,
        continuous=real_spans["continuous"],
        card_ids=real_spans["card_ids"],
        potion_ids=real_spans["potion_ids"],
        relic_ids=real_spans["relic_ids"],
        action_masks=real_spans["action_masks"],
    )
    holdout_binding = None
    holdout_spans = None
    holdout_labels = None
    holdout_features = None
    holdout_span_telemetry = None
    if holdout_supplied:
        holdout_checkpoint = torch.load(
            args.holdout_real_checkpoint, map_location="cpu", weights_only=True
        )
        _, holdout_replay, holdout_provenance = _validate_callability_checkpoint(
            holdout_checkpoint,
            expected_transition_count=args.expected_holdout_real_transition_count,
        )
        if parameter_sha256(holdout_checkpoint["online_network_state_dict"]) != (
            parameter_sha256(parent_state)
        ):
            raise ValueError("holdout replay parent differs")
        holdout_spans, holdout_span_telemetry = build_candidate_decision_spans(
            holdout_replay, gamma=GAMMA
        )
        holdout_labels = holdout_spans["anchor_to_executed_action"].bool().cpu()
        holdout_features = parent_feature_views(
            parent,
            continuous=holdout_spans["continuous"],
            card_ids=holdout_spans["card_ids"],
            potion_ids=holdout_spans["potion_ids"],
            relic_ids=holdout_spans["relic_ids"],
            action_masks=holdout_spans["action_masks"],
        )
        holdout_binding = {
            "checkpoint_sha256": args.expected_holdout_real_sha256.lower(),
            "provenance": holdout_provenance,
            "span_telemetry": holdout_span_telemetry,
        }

    config = SmokeConfig(
        train_seeds=args.simulator_seeds,
        evaluation_seeds=(max(args.simulator_seeds) + 1,),
        battle_indices=args.battle_indices,
        ascension=0,
        max_decisions_per_seed=100,
        max_actions_per_turn=8,
        behavior_seed=SIMULATOR_TRAINING_SEED,
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=0.1,
        network_seed=CLASSIFIER_SEED,
        batch_size=BATCH_SIZE,
        optimizer_steps=1,
        replay_target_mode=ONE_STEP_TD_TARGET,
        frozen_parent_bootstrap_policy=FROZEN_PARENT_RAW_GREEDY_BOOTSTRAP,
        complete_trajectories_only=True,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )
    config.validate()
    native_module = load_native_module(args.module, dll_directories=args.dll_dir)
    trainer.online_network.eval()
    simulator_rows, simulator_corpus = collect_transitions(
        native_module,
        id_mapper=id_mapper,
        config=config,
        behavior_trainer=trainer,
        expected_behavior_parent_sha256=parameter_sha256(parent_state),
    )
    sim_labels = torch.tensor(
        [row.guard_proxy_replaced for row in simulator_rows], dtype=torch.bool
    )
    if not bool(sim_labels.any()) or not bool((~sim_labels).any()):
        raise RuntimeError("simulator guard labels do not contain both classes")
    sim_features = parent_feature_views(
        parent,
        continuous=torch.from_numpy(np.stack([row.continuous for row in simulator_rows])),
        card_ids=torch.from_numpy(np.stack([row.card_ids for row in simulator_rows])),
        potion_ids=torch.from_numpy(np.stack([row.potion_ids for row in simulator_rows])),
        relic_ids=torch.from_numpy(np.stack([row.relic_ids for row in simulator_rows])),
        action_masks=torch.from_numpy(np.stack([row.action_mask for row in simulator_rows])),
    )["parent_latent"]
    sim_seed_values = torch.tensor([row.seed for row in simulator_rows])
    heldout_seeds = set(args.simulator_seeds[::5])
    sim_validation_mask = torch.tensor(
        [int(seed) in heldout_seeds for seed in sim_seed_values.tolist()]
    )
    sim_train_indices = torch.where(~sim_validation_mask)[0]
    sim_validation_indices = torch.where(sim_validation_mask)[0]

    cross_fitted, fit_telemetry = _cross_fitted_real_scores(
        real_features=real_features,
        real_labels=real_labels,
        real_groups=real_spans["combat_group_indices"],
        sim_features=sim_features,
        sim_labels=sim_labels,
        sim_train_indices=sim_train_indices,
    )
    simulator_model, simulator_losses = fit_classifier(
        sim_features,
        sim_labels,
        sim_train_indices,
        seed=CLASSIFIER_SEED,
        updates=SIMULATOR_UPDATES,
    )
    sim_scores = classifier_scores(simulator_model, sim_features)
    sim_threshold = threshold_at_direct_open_cap(
        sim_scores[sim_train_indices], sim_labels[sim_train_indices]
    )
    simulator_validation = intervention_metrics(
        sim_scores[sim_validation_indices],
        sim_labels[sim_validation_indices],
        thresholds=sim_threshold,
    )
    real_results = {
        name: intervention_metrics(values[0], real_labels, thresholds=values[1])
        for name, values in cross_fitted.items()
    }
    independent_holdout = None
    independent_holdout_fit = None
    if holdout_features is not None and holdout_labels is not None:
        independent_holdout, independent_holdout_fit = _independent_holdout_scores(
            development_features=real_features,
            development_labels=real_labels,
            holdout_features=holdout_features,
            holdout_labels=holdout_labels,
            sim_features=sim_features,
            sim_labels=sim_labels,
            sim_train_indices=sim_train_indices,
        )
    legacy = real_results["legacy_real_only"]
    latent = real_results["latent_real_only"]
    transfer = real_results["latent_sim_pretrained"]
    representation_auc_delta = latent["roc_auc"] - legacy["roc_auc"]
    transfer_auc_delta = transfer["roc_auc"] - latent["roc_auc"]
    transfer_recall_delta = (
        transfer["changed_open_share"] - latent["changed_open_share"]
    )
    if independent_holdout is not None:
        holdout_legacy = independent_holdout["legacy_real_only"]
        holdout_latent = independent_holdout["latent_real_only"]
        holdout_transfer = independent_holdout["latent_sim_pretrained"]
        holdout_representation_delta = (
            holdout_latent["roc_auc"] - holdout_legacy["roc_auc"]
        )
        holdout_transfer_auc_delta = (
            holdout_transfer["roc_auc"] - holdout_latent["roc_auc"]
        )
        holdout_transfer_recall_delta = (
            holdout_transfer["changed_open_share"]
            - holdout_latent["changed_open_share"]
        )
        if (
            transfer_auc_delta >= 0.02
            and holdout_transfer_auc_delta >= 0.02
            and holdout_transfer_recall_delta >= 0.05
        ):
            verdict = "lightspeed_guard_pretraining_confirmed_on_independent_replay"
        elif (
            representation_auc_delta >= 0.03
            and holdout_representation_delta >= 0.03
        ):
            verdict = "parent_latent_confirmed_but_lightspeed_transfer_not_proven"
        else:
            verdict = "lightspeed_guard_transfer_not_supported"
    elif transfer_auc_delta >= 0.02 and transfer_recall_delta >= 0.05:
        verdict = "lightspeed_guard_pretraining_has_development_signal"
    elif representation_auc_delta >= 0.03:
        verdict = "parent_latent_helps_but_lightspeed_transfer_is_not_proven"
    else:
        verdict = "lightspeed_guard_transfer_not_supported"
    return {
        "schema_version": SCHEMA_VERSION,
        "verdict": verdict,
        "authority": {
            "development_classifier_fit": True,
            "gameplay": False,
            "policy_candidate": False,
            "production_checkpoint_loading": False,
            "qualification": False,
            "promotion": False,
        },
        "bindings": {
            "native_module": str(args.module.resolve()),
            "native_module_sha256": args.expected_module_sha256.lower(),
            "items_json_sha256": args.expected_items_sha256.lower(),
            "parent_checkpoint_sha256": args.expected_parent_sha256.lower(),
            "real_checkpoint_sha256": args.expected_real_sha256.lower(),
            "holdout_real_checkpoint_sha256": (
                args.expected_holdout_real_sha256.lower()
                if holdout_supplied
                else None
            ),
            "parent_parameter_sha256": parameter_sha256(parent_state),
        },
        "recipe": {
            "simulator_seeds": [min(args.simulator_seeds), max(args.simulator_seeds)],
            "battle_indices": list(args.battle_indices),
            "fold_count": FOLD_COUNT,
            "simulator_updates": SIMULATOR_UPDATES,
            "real_updates_per_fold": REAL_UPDATES,
            "batch_size": BATCH_SIZE,
            "learning_rate": LEARNING_RATE,
            "direct_open_calibration_cap": DIRECT_OPEN_CAP,
        },
        "real_corpus": {
            "provenance": provenance,
            "span_telemetry": real_span_telemetry,
        },
        "simulator_corpus": simulator_corpus,
        "simulator_validation": simulator_validation,
        "real_cross_fitted": real_results,
        "independent_holdout_binding": holdout_binding,
        "independent_holdout": independent_holdout,
        "deltas": {
            "parent_latent_minus_legacy_roc_auc": representation_auc_delta,
            "sim_pretrained_minus_latent_real_only_roc_auc": transfer_auc_delta,
            "sim_pretrained_minus_latent_real_only_changed_open_share": (
                transfer_recall_delta
            ),
            "holdout_parent_latent_minus_legacy_roc_auc": (
                holdout_representation_delta
                if independent_holdout is not None
                else None
            ),
            "holdout_sim_pretrained_minus_latent_real_only_roc_auc": (
                holdout_transfer_auc_delta
                if independent_holdout is not None
                else None
            ),
            "holdout_sim_pretrained_minus_latent_real_only_changed_open_share": (
                holdout_transfer_recall_delta
                if independent_holdout is not None
                else None
            ),
        },
        "fit_telemetry": {
            **fit_telemetry,
            "simulator_validation_fit_loss": _summary(simulator_losses),
            "independent_holdout_fit": independent_holdout_fit,
        },
        "decision": {
            "construct_policy_candidate": False,
            "collect_fresh_gameplay": False,
            "same_closed_cohort_promotion": False,
            "next_step": (
                "Prototype a latent-gated correction head without promotion authority."
                if verdict
                == "lightspeed_guard_pretraining_confirmed_on_independent_replay"
                else (
                    "Use a fresh real replay only to confirm the latent intervention gate."
                    if "parent_latent" in verdict
                    else "Do not extend the current LightSTS guard-label recipe."
                )
            ),
        },
    }


def _summary_markdown(report: Mapping[str, Any]) -> str:
    rows = [
        "# Combat RL LightSTS guard transfer POC",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Simulator transitions: `{report['simulator_corpus']['accepted_transition_count']}`",
        f"- Real decision spans: `{report['real_corpus']['span_telemetry']['decision_span_count']}`",
        "- No policy candidate or production artifact was created.",
        "",
        "| Arm | ROC AUC | Direct open | Changed open | Open precision |",
        "|---|---:|---:|---:|---:|",
    ]
    for name, metrics in report["real_cross_fitted"].items():
        precision = metrics["opened_precision"]
        precision_text = "n/a" if precision is None else f"{precision:.4f}"
        rows.append(
            f"| `{name}` | {metrics['roc_auc']:.4f} | "
            f"{metrics['direct_open_share']:.4f} | "
            f"{metrics['changed_open_share']:.4f} | {precision_text} |"
        )
    if report.get("independent_holdout"):
        rows.extend(("", "## Independent replay holdout", ""))
        rows.extend(
            (
                "| Arm | ROC AUC | Direct open | Changed open | Open precision |",
                "|---|---:|---:|---:|---:|",
            )
        )
        for name, metrics in report["independent_holdout"].items():
            precision = metrics["opened_precision"]
            precision_text = "n/a" if precision is None else f"{precision:.4f}"
            rows.append(
                f"| `{name}` | {metrics['roc_auc']:.4f} | "
                f"{metrics['direct_open_share']:.4f} | "
                f"{metrics['changed_open_share']:.4f} | {precision_text} |"
            )
    rows.extend(
        (
            "",
            "This is development-only evidence from an already-used real replay corpus.",
            "It does not authorize gameplay, qualification, or promotion.",
            "",
        )
    )
    return "\n".join(rows)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--module", required=True, type=Path)
    parser.add_argument("--dll-dir", action="append", default=[], type=Path)
    parser.add_argument("--expected-module-sha256", required=True)
    parser.add_argument("--items-json", required=True, type=Path)
    parser.add_argument("--expected-items-sha256", required=True)
    parser.add_argument("--parent-checkpoint", required=True, type=Path)
    parser.add_argument("--expected-parent-sha256", required=True)
    parser.add_argument("--real-checkpoint", required=True, type=Path)
    parser.add_argument("--expected-real-sha256", required=True)
    parser.add_argument("--expected-real-transition-count", required=True, type=int)
    parser.add_argument("--holdout-real-checkpoint", type=Path)
    parser.add_argument("--expected-holdout-real-sha256")
    parser.add_argument("--expected-holdout-real-transition-count", type=int)
    parser.add_argument("--simulator-seeds", required=True, type=_parse_range)
    parser.add_argument("--battle-indices", default="0,3,6,9", type=_parse_range)
    parser.add_argument("--output-dir", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    if output_dir.exists():
        raise ValueError(f"output directory already exists: {output_dir}")
    report = run(args)
    output_dir.mkdir(parents=True, exist_ok=False)
    report_bytes = json.dumps(
        report, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True
    ).encode("ascii") + b"\n"
    (output_dir / "report.json").write_bytes(report_bytes)
    (output_dir / "summary.md").write_text(
        _summary_markdown(report), encoding="ascii", newline="\n"
    )
    print(json.dumps({"output_dir": str(output_dir), "verdict": report["verdict"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
