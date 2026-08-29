"""Fit and evaluate one registered action-relative selective classifier."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Mapping, Sequence

import torch
import torch.nn.functional as F


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    create_fresh_trainer,
    initialize_trainer,
    load_initial_checkpoint,
    parameter_sha256,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    _canonical_json_bytes,
    _committed_registration_bytes,
    _current_commit,
    _trainer_metadata,
    _validate_commit,
    _validate_file_binding,
    load_corpus,
    sha256_file,
)
from spirecomm.ai.rl.v2.action_relative_selective_classifier import (  # noqa: E402
    BENEFICIAL_CLASS,
    CLASS_NAMES,
    NEUTRAL_CLASS,
    SEVERE_CLASS,
    ActionRelativeSelectiveClassifier,
    ActionRelativeSelectiveConfig,
    build_class_balanced_sample_plan,
    build_replacement_sample_plan,
    build_selective_development_artifact,
    build_supported_selective_corpus,
    build_within_state_ranking_pairs,
    finite_sample_negative_threshold,
    load_selective_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-action-relative-selective-classifier-fit-20260829-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_selective_classifier_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "spirecomm/ai/rl/v2/action_relative_selective_classifier.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/network.py",
)

FIXED_RECIPE = {
    "architecture": "frozen_parent_action_relative_three_class_classifier",
    "hidden_dim": 128,
    "model_initialization_seed": 2026082920,
    "sampling_seed": 2026082921,
    "ranking_sampling_seed": 2026082922,
    "fit_seed_first": 262000,
    "fit_seed_last": 262191,
    "calibration_seed_first": 262192,
    "calibration_seed_last": 262255,
    "severe_upper_exclusive": -0.5,
    "beneficial_lower_inclusive": 0.5,
    "card_action_first": 0,
    "card_action_last": 59,
    "potion_action_first": 60,
    "potion_action_last": 89,
    "forbidden_action_indices": [90],
    "optimizer": "adam",
    "learning_rate": 0.001,
    "updates": 4096,
    "samples_per_class_per_update": 128,
    "ranking_pairs_per_update": 128,
    "ranking_loss_weight": 0.5,
    "calibration_quantile": 0.95,
    "calibration_method": "finite_sample_higher_negative_class",
    "device": "cpu",
}

FIXED_OFFLINE_GATES = {
    "minimum_intervention_count": 30,
    "minimum_intervention_precision": 0.65,
    "minimum_mean_selected_true_advantage_exclusive": 0.18881003558635712,
    "maximum_mean_policy_regret_exclusive": 3.1811342239379883,
    "severe_harm_floor": -0.5,
    "maximum_severe_harm_count": 0,
    "illegal_action_count_zero": True,
    "forbidden_action_selection_count_zero": True,
}

REGISTERED_AUTHORITY = {
    "cpu_model_fitting": True,
    "native_loading": False,
    "gameplay": False,
    "communication_mod": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}

RESULT_AUTHORITY = {
    "development_candidate": True,
    "fresh_lightspeed_gate": False,
    "native_loading": False,
    "gameplay": False,
    "communication_mod": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}


def _sha256_tensors(*values: torch.Tensor) -> str:
    digest = hashlib.sha256()
    for value in values:
        tensor = value.detach().cpu().contiguous()
        digest.update(str(tensor.dtype).encode("ascii"))
        digest.update(json.dumps(list(tensor.shape), separators=(",", ":")).encode("ascii"))
        digest.update(tensor.numpy().tobytes())
    return digest.hexdigest()


def _loss_summary(values: Sequence[float]) -> dict[str, float]:
    tensor = torch.tensor(values, dtype=torch.float64)
    return {
        "first": float(tensor[0]),
        "last": float(tensor[-1]),
        "minimum": float(tensor.min()),
        "maximum": float(tensor.max()),
        "mean": float(tensor.mean()),
    }


def split_selective_corpus(
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    *,
    fit_seeds: frozenset[int],
    calibration_seeds: frozenset[int],
) -> dict[str, dict[str, Any]]:
    if not fit_seeds or not calibration_seeds or fit_seeds & calibration_seeds:
        raise ValueError("selective classifier seed partitions must be disjoint")
    row_count = len(corpus_metadata)
    if row_count <= 0 or any(value.shape[0] != row_count for value in tensors.values()):
        raise ValueError("selective classifier corpus rows differ")
    rows = {"fit": [], "calibration": []}
    for row_index, metadata in enumerate(corpus_metadata):
        seed = metadata.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("selective classifier corpus seed is invalid")
        if seed in fit_seeds:
            rows["fit"].append(row_index)
        elif seed in calibration_seeds:
            rows["calibration"].append(row_index)
        else:
            raise ValueError("selective classifier corpus seed is outside the split")
    result: dict[str, dict[str, Any]] = {}
    for name in ("fit", "calibration"):
        indices = torch.tensor(rows[name], dtype=torch.long)
        if not indices.numel():
            raise ValueError(f"selective classifier {name} partition is empty")
        partition_tensors = {key: value[indices] for key, value in tensors.items()}
        partition_metadata = [corpus_metadata[int(index)] for index in indices]
        supported = build_supported_selective_corpus(
            partition_tensors, partition_metadata
        )
        split_sha256 = _sha256_tensors(
            indices, supported["source_row_indices"], supported["pair_row_indices"],
            supported["candidate_actions"], supported["labels"]
        )
        class_support = {
            name: int(supported["labels"].eq(class_index).sum().item())
            for class_index, name in enumerate(CLASS_NAMES)
        }
        if any(value <= 0 for value in class_support.values()):
            raise ValueError(f"selective classifier {name} class support is incomplete")
        result[name] = {
            "row_indices": indices,
            "split_sha256": split_sha256,
            "source_row_count": int(indices.numel()),
            "supported_row_count": int(
                supported["tensors"]["guard_actions"].numel()
            ),
            "excluded_unsupported_only_row_count": int(
                supported["excluded_unsupported_only_row_count"]
            ),
            "pair_count": int(supported["candidate_actions"].numel()),
            "class_support": class_support,
            "corpus": supported,
        }
    return result


def _pair_features(
    classifier: ActionRelativeSelectiveClassifier,
    corpus: Mapping[str, Any],
) -> torch.Tensor:
    rows = corpus["pair_row_indices"]
    tensors = corpus["tensors"]
    with torch.no_grad():
        return classifier._candidate_features(
            **{name: value[rows] for name, value in tensors.items()},
            candidate_actions=corpus["candidate_actions"],
        ).detach()


def _evidence(logits: torch.Tensor) -> torch.Tensor:
    return logits[:, BENEFICIAL_CLASS] - torch.logsumexp(
        logits[:, :BENEFICIAL_CLASS], dim=1
    )


def fit_selective_classifier(
    *,
    parent: torch.nn.Module,
    metadata: Mapping[str, Any],
    corpus: Mapping[str, Any],
    recipe: Mapping[str, Any],
) -> tuple[ActionRelativeSelectiveClassifier, dict[str, Any]]:
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(int(recipe["model_initialization_seed"]))
        classifier = ActionRelativeSelectiveClassifier(
            parent,
            metadata,
            ActionRelativeSelectiveConfig(
                hidden_dim=int(recipe["hidden_dim"]),
                include_item_semantics=bool(
                    recipe.get("include_item_semantics", False)
                ),
            ),
            selection_threshold=0.0,
        )
    labels = corpus["labels"].long().cpu()
    class_plan = build_class_balanced_sample_plan(
        labels,
        updates=int(recipe["updates"]),
        samples_per_class=int(recipe["samples_per_class_per_update"]),
        seed=int(recipe["sampling_seed"]),
    )
    ranking_pairs = build_within_state_ranking_pairs(
        corpus["pair_row_indices"], labels
    )
    ranking_plan = build_replacement_sample_plan(
        int(ranking_pairs.shape[0]),
        updates=int(recipe["updates"]),
        samples_per_update=int(recipe["ranking_pairs_per_update"]),
        seed=int(recipe["ranking_sampling_seed"]),
    )
    sampling_plan_sha256 = _sha256_tensors(
        class_plan, ranking_pairs, ranking_plan
    )
    features = _pair_features(classifier, corpus)
    parent_before = state_dict_sha256(classifier.parent.state_dict())
    optimizer = torch.optim.Adam(
        classifier.classifier.parameters(), lr=float(recipe["learning_rate"])
    )
    total_losses: list[float] = []
    classification_losses: list[float] = []
    ranking_losses: list[float] = []
    classifier.train()
    for update in range(int(recipe["updates"])):
        class_indices = class_plan[update].reshape(-1)
        class_logits = classifier.classifier(features[class_indices])
        classification_loss = F.cross_entropy(class_logits, labels[class_indices])

        selected_pairs = ranking_pairs[ranking_plan[update]]
        ranking_indices = selected_pairs.reshape(-1)
        ranking_logits = classifier.classifier(features[ranking_indices]).reshape(
            -1, 2, 3
        )
        ranking_evidence = _evidence(ranking_logits.reshape(-1, 3)).reshape(-1, 2)
        ranking_loss = F.softplus(
            -(ranking_evidence[:, 0] - ranking_evidence[:, 1])
        ).mean()
        loss = classification_loss + float(recipe["ranking_loss_weight"]) * ranking_loss
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("selective classifier objective became non-finite")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if any(parameter.grad is not None for parameter in classifier.parent.parameters()):
            raise RuntimeError("selective classifier fit produced parent gradients")
        optimizer.step()
        total_losses.append(float(loss.detach()))
        classification_losses.append(float(classification_loss.detach()))
        ranking_losses.append(float(ranking_loss.detach()))
    classifier.eval()
    parent_after = state_dict_sha256(classifier.parent.state_dict())
    if parent_after != parent_before:
        raise RuntimeError("selective classifier fit changed the frozen parent")
    return classifier, {
        "update_count": int(recipe["updates"]),
        "samples_per_class_per_update": int(recipe["samples_per_class_per_update"]),
        "ranking_pairs_per_update": int(recipe["ranking_pairs_per_update"]),
        "ranking_support": int(ranking_pairs.shape[0]),
        "sampling_plan_sha256": sampling_plan_sha256,
        "feature_sha256": _sha256_tensors(features),
        "loss": _loss_summary(total_losses),
        "classification_loss": _loss_summary(classification_losses),
        "ranking_loss": _loss_summary(ranking_losses),
        "all_objectives_finite": True,
        "parent_state_dict_sha256_before": parent_before,
        "parent_state_dict_sha256_after": parent_after,
        "parent_frozen": True,
        "classifier_state_dict_sha256": state_dict_sha256(
            classifier.classifier.state_dict()
        ),
    }


def calibrate_threshold(
    classifier: ActionRelativeSelectiveClassifier,
    corpus: Mapping[str, Any],
    *,
    quantile: float,
) -> tuple[ActionRelativeSelectiveClassifier, dict[str, Any]]:
    features = _pair_features(classifier, corpus)
    with torch.no_grad():
        logits = classifier.classifier(features)
        evidence = _evidence(logits)
    threshold, rank, negative_count = finite_sample_negative_threshold(
        evidence, corpus["labels"], quantile=quantile
    )
    calibrated = ActionRelativeSelectiveClassifier(
        classifier.parent,
        classifier.metadata,
        classifier.config,
        selection_threshold=threshold,
    )
    calibrated.classifier.load_state_dict(classifier.classifier.state_dict(), strict=True)
    calibrated.eval()
    return calibrated, {
        "selection_threshold": threshold,
        "quantile": float(quantile),
        "negative_count": negative_count,
        "finite_sample_rank": rank,
        "pair_count": int(evidence.numel()),
        "beneficial_count": int(
            corpus["labels"].eq(BENEFICIAL_CLASS).sum().item()
        ),
        "evidence_minimum": float(evidence.min()),
        "evidence_maximum": float(evidence.max()),
        "classifier_state_dict_sha256": state_dict_sha256(
            calibrated.classifier.state_dict()
        ),
    }


def evaluate_selective_corpus(
    classifier: ActionRelativeSelectiveClassifier,
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    *,
    forbidden_action_indices: Sequence[int],
    severe_harm_floor: float,
) -> dict[str, Any]:
    corpus = build_supported_selective_corpus(tensors, corpus_metadata)
    features = _pair_features(classifier, corpus)
    with torch.no_grad():
        logits = classifier.classifier(features)
        evidence = _evidence(logits)
    labels = corpus["labels"].cpu()
    predictions = logits.argmax(dim=1).cpu()
    confusion = torch.zeros((3, 3), dtype=torch.long)
    for truth, predicted in zip(labels.tolist(), predictions.tolist()):
        confusion[truth, predicted] += 1
    family_metrics: dict[str, dict[str, Any]] = {}
    candidate_actions = corpus["candidate_actions"].cpu()
    for family, mask in (
        ("card", candidate_actions.lt(60)),
        ("potion", candidate_actions.ge(60) & candidate_actions.lt(90)),
    ):
        family_labels = labels[mask]
        family_predictions = predictions[mask]
        predicted_beneficial = family_predictions.eq(BENEFICIAL_CLASS)
        family_metrics[family] = {
            "pair_count": int(mask.sum().item()),
            "beneficial_count": int(family_labels.eq(BENEFICIAL_CLASS).sum().item()),
            "predicted_beneficial_count": int(predicted_beneficial.sum().item()),
            "predicted_beneficial_precision": float(
                family_labels[predicted_beneficial]
                .eq(BENEFICIAL_CLASS)
                .float()
                .mean()
                .item()
            )
            if bool(predicted_beneficial.any())
            else 0.0,
        }

    supported_tensors = corpus["tensors"]
    forbidden = frozenset(int(value) for value in forbidden_action_indices)
    started = time.perf_counter()
    with torch.no_grad():
        selection = classifier.select_actions(
            **supported_tensors,
            alternative_masks=corpus["alternative_masks"],
            forbidden_action_indices=forbidden,
        )
    latency_ms = (time.perf_counter() - started) * 1000.0
    supported_row_count = int(supported_tensors["guard_actions"].numel())
    source_row_count = len(corpus_metadata)
    action_dim = int(supported_tensors["action_masks"].shape[1])
    true_matrix = torch.full((supported_row_count, action_dim), float("-inf"))
    true_matrix[
        corpus["pair_row_indices"].cpu(), corpus["candidate_actions"].cpu()
    ] = corpus["raw_advantages"].cpu()
    allowed = corpus["alternative_masks"].cpu().clone()
    for action in forbidden:
        allowed[:, action] = False
    supported_rows = torch.arange(supported_row_count)
    supported_interventions = selection.gate_open.cpu()
    supported_selected_true = torch.zeros(supported_row_count)
    supported_selected_true[supported_interventions] = true_matrix[
        supported_rows[supported_interventions],
        selection.actions.cpu()[supported_interventions],
    ]
    allowed_true = true_matrix.masked_fill(~allowed, float("-inf"))
    has_allowed = allowed.any(dim=1)
    best_allowed = torch.zeros(supported_row_count)
    best_allowed[has_allowed] = allowed_true[has_allowed].max(dim=1).values
    supported_best_with_guard = torch.maximum(
        best_allowed, torch.zeros_like(best_allowed)
    )
    residual_true = torch.zeros(supported_row_count)
    residual_true[has_allowed] = true_matrix[
        supported_rows[has_allowed], selection.residual_actions.cpu()[has_allowed]
    ]
    top_action_correct = torch.isclose(
        residual_true[has_allowed], best_allowed[has_allowed], atol=1e-6, rtol=0.0
    )
    source_indices = corpus["source_row_indices"].cpu()
    selected_true = torch.zeros(source_row_count)
    selected_true[source_indices] = supported_selected_true
    best_with_guard = torch.zeros(source_row_count)
    best_with_guard[source_indices] = supported_best_with_guard
    intervention_rows = torch.zeros(source_row_count, dtype=torch.bool)
    intervention_rows[source_indices] = supported_interventions
    intervention_count = int(supported_interventions.sum().item())
    legal_masks = supported_tensors["action_masks"].cpu()
    illegal_count = int(
        (~legal_masks[supported_rows, selection.actions.cpu()]).sum().item()
    )
    severe_count = int(
        supported_selected_true[supported_interventions]
        .lt(float(severe_harm_floor))
        .sum()
        .item()
    )
    intervention_precision = (
        float(
            supported_selected_true[supported_interventions]
            .ge(0.5)
            .float()
            .mean()
            .item()
        )
        if intervention_count
        else 0.0
    )
    return {
        "source_row_count": source_row_count,
        "row_count": source_row_count,
        "supported_row_count": supported_row_count,
        "excluded_unsupported_only_row_count": int(
            corpus["excluded_unsupported_only_row_count"]
        ),
        "alternative_count": int(labels.numel()),
        "classification": {
            "accuracy": float(predictions.eq(labels).float().mean().item()),
            "confusion_matrix_truth_rows": confusion.tolist(),
            "class_support": {
                name: int(labels.eq(class_index).sum().item())
                for class_index, name in enumerate(CLASS_NAMES)
            },
            "family": family_metrics,
        },
        "ranking": {
            "best_allowed_action_accuracy": float(
                top_action_correct.float().mean().item()
            )
            if bool(has_allowed.any())
            else 0.0,
            "mean_policy_regret": float((best_with_guard - selected_true).mean().item()),
        },
        "selection": {
            "selection_threshold": classifier.selection_threshold,
            "intervention_count": intervention_count,
            "intervention_share": intervention_count / max(source_row_count, 1),
            "intervention_precision": intervention_precision,
            "mean_selected_true_advantage": float(selected_true.mean().item()),
            "mean_intervention_true_advantage": float(
                supported_selected_true[supported_interventions].mean().item()
            )
            if intervention_count
            else 0.0,
            "severe_harm_count": severe_count,
            "illegal_action_count": illegal_count,
            "forbidden_action_selection_count": selection.telemetry[
                "forbidden_action_selection_count"
            ],
            "no_allowed_alternative_count": selection.telemetry[
                "no_allowed_alternative_count"
            ]
            + int(corpus["excluded_unsupported_only_row_count"]),
        },
        "evidence": {
            "minimum": float(evidence.min()),
            "maximum": float(evidence.max()),
            "mean": float(evidence.mean()),
        },
        "latency": {
            "total_ms": latency_ms,
            "mean_ms_per_state": latency_ms / max(source_row_count, 1),
        },
    }


def apply_offline_gates(metrics: Mapping[str, Any]) -> dict[str, Any]:
    selection = metrics["selection"]
    ranking = metrics["ranking"]
    conditions = {
        "minimum_intervention_count": int(selection["intervention_count"])
        >= int(FIXED_OFFLINE_GATES["minimum_intervention_count"]),
        "minimum_intervention_precision": float(selection["intervention_precision"])
        >= float(FIXED_OFFLINE_GATES["minimum_intervention_precision"]),
        "minimum_mean_selected_true_advantage_exclusive": float(
            selection["mean_selected_true_advantage"]
        )
        > float(
            FIXED_OFFLINE_GATES[
                "minimum_mean_selected_true_advantage_exclusive"
            ]
        ),
        "maximum_mean_policy_regret_exclusive": float(ranking["mean_policy_regret"])
        < float(FIXED_OFFLINE_GATES["maximum_mean_policy_regret_exclusive"]),
        "maximum_severe_harm_count": int(selection["severe_harm_count"])
        <= int(FIXED_OFFLINE_GATES["maximum_severe_harm_count"]),
        "illegal_action_count_zero": int(selection["illegal_action_count"]) == 0,
        "forbidden_action_selection_count_zero": int(
            selection["forbidden_action_selection_count"]
        )
        == 0,
    }
    passed = all(conditions.values())
    return {
        "conditions": conditions,
        "all_conditions_passed": passed,
        "decision": (
            "offline_passed_enter_fresh_lightspeed_gate"
            if passed
            else "offline_failed_close_without_fresh_gate_or_sweep"
        ),
    }


def validate_registration_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version", "experiment_id", "source_commit", "runner",
        "source_files", "inputs", "recipe", "offline_gates", "output_dir",
        "authority",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("selective classifier registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION or payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("selective classifier registration identity differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    source_files = payload["source_files"]
    if not isinstance(source_files, Mapping) or set(source_files) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("selective classifier source inventory differs")
    normalized_sources: dict[str, str] = {}
    for raw_path, raw_hash in source_files.items():
        if not isinstance(raw_path, str) or Path(raw_path).is_absolute() or ".." in Path(raw_path).parts:
            raise ValueError("selective classifier source path is invalid")
        digest = str(raw_hash).lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("selective classifier source hash is invalid")
        normalized_sources[raw_path.replace("\\", "/")] = digest
    if Path(runner["path"]).resolve() != (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve():
        raise ValueError("selective classifier runner path differs")
    if runner["sha256"] != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("selective classifier runner hash differs")
    expected_inputs = {
        "items_json", "parent_checkpoint", "train_corpus", "evaluation_corpus",
        "objective_audit",
    }
    inputs = payload["inputs"]
    if not isinstance(inputs, Mapping) or set(inputs) != expected_inputs:
        raise ValueError("selective classifier inputs differ")
    normalized_inputs = {
        name: _validate_file_binding(inputs[name], label=name)
        for name in sorted(expected_inputs)
    }
    if normalized_inputs["train_corpus"]["sha256"] == normalized_inputs["evaluation_corpus"]["sha256"]:
        raise ValueError("selective classifier corpus identities overlap")
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("selective classifier fixed recipe differs")
    if payload["offline_gates"] != FIXED_OFFLINE_GATES:
        raise ValueError("selective classifier offline gates differ")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("selective classifier authority differs")
    output = payload["output_dir"]
    if not isinstance(output, str) or not Path(output).is_absolute():
        raise ValueError("selective classifier output must be absolute")
    output_path = Path(output).resolve()
    try:
        output_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("selective classifier output is outside reports") from exc
    if output_path == REPORTS_ROOT.resolve():
        raise ValueError("selective classifier output cannot be reports root")
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "runner": runner,
        "source_files": normalized_sources,
        "inputs": normalized_inputs,
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "offline_gates": copy.deepcopy(FIXED_OFFLINE_GATES),
        "output_dir": str(output_path),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def load_committed_registration(path: Path) -> tuple[dict[str, Any], str]:
    committed = _committed_registration_bytes(path)
    registration = validate_registration_payload(json.loads(committed))
    current = _current_commit()
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", registration["source_commit"], current],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("selective classifier source commit is not an ancestor of HEAD")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", registration["source_commit"], "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"selective classifier source changed after commit: {relative}")
    if path.read_bytes() != committed:
        raise ValueError("working selective classifier registration differs")
    return registration, hashlib.sha256(committed).hexdigest()


def _validated_execution_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"])
        if not path.is_absolute() or not path.is_file():
            raise ValueError(f"registered selective classifier {name} is unavailable")
        path = path.resolve()
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"registered selective classifier {name} hash differs")
        paths[name] = path
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("selective classifier output or staging already exists")
    paths["output_dir"] = output
    return paths


def _selection_exact(
    first: ActionRelativeSelectiveClassifier,
    second: ActionRelativeSelectiveClassifier,
    tensors: Mapping[str, torch.Tensor],
    metadata: Sequence[Mapping[str, Any]],
    forbidden: Sequence[int],
) -> bool:
    corpus = build_supported_selective_corpus(tensors, metadata)
    arguments = {
        **corpus["tensors"],
        "alternative_masks": corpus["alternative_masks"],
        "forbidden_action_indices": frozenset(int(value) for value in forbidden),
    }
    left = first.select_actions(**arguments)
    right = second.select_actions(**arguments)
    return all(
        torch.equal(getattr(left, field), getattr(right, field))
        for field in (
            "actions", "guard_actions", "residual_actions", "predicted_advantages",
            "gate_open", "evidence_scores", "selected_logits", "predicted_classes",
        )
    ) and left.telemetry == right.telemetry


def _render_summary(report: Mapping[str, Any]) -> str:
    selection = report["evaluation"]["selection"]
    ranking = report["evaluation"]["ranking"]
    return (
        "# Action-Relative Selective Classifier Fit\n\n"
        f"- Calibration threshold: {report['calibration']['selection_threshold']:.6f}\n"
        f"- Holdout interventions: {selection['intervention_count']}\n"
        f"- Holdout precision: {selection['intervention_precision']:.6f}\n"
        f"- Mean selected advantage: {selection['mean_selected_true_advantage']:.6f}\n"
        f"- Mean policy regret: {ranking['mean_policy_regret']:.6f}\n"
        f"- Severe harms: {selection['severe_harm_count']}\n"
        f"- Decision: {report['decision']}\n"
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("selective classifier fit must use the registered interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("selective classifier fit must run in isolated mode")
    registration, registration_sha256 = load_committed_registration(registration_path)
    paths = _validated_execution_paths(registration)
    recipe = registration["recipe"]
    id_mapper = build_id_mapper(paths["items_json"])
    initial_checkpoint = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        id_mapper,
        seed=int(recipe["model_initialization_seed"]),
        batch_size=int(recipe["samples_per_class_per_update"]) * 3,
        learning_starts=64,
    )
    parent_state, initialization = initialize_trainer(trainer, initial_checkpoint)
    parent = trainer.online_network
    parent.eval()
    metadata = _trainer_metadata(trainer)
    train = load_corpus(paths["train_corpus"], expected_partition="train")
    split = split_selective_corpus(
        train["tensors"],
        train["metadata"],
        fit_seeds=frozenset(
            range(int(recipe["fit_seed_first"]), int(recipe["fit_seed_last"]) + 1)
        ),
        calibration_seeds=frozenset(
            range(
                int(recipe["calibration_seed_first"]),
                int(recipe["calibration_seed_last"]) + 1,
            )
        ),
    )
    classifier, fit = fit_selective_classifier(
        parent=parent,
        metadata=metadata,
        corpus=split["fit"]["corpus"],
        recipe=recipe,
    )
    classifier, calibration = calibrate_threshold(
        classifier,
        split["calibration"]["corpus"],
        quantile=float(recipe["calibration_quantile"]),
    )
    evaluation = load_corpus(paths["evaluation_corpus"], expected_partition="evaluation")
    forbidden = recipe["forbidden_action_indices"]
    fit_metrics = evaluate_selective_corpus(
        classifier,
        split["fit"]["corpus"]["tensors"],
        split["fit"]["corpus"]["metadata"],
        forbidden_action_indices=forbidden,
        severe_harm_floor=float(FIXED_OFFLINE_GATES["severe_harm_floor"]),
    )
    calibration_metrics = evaluate_selective_corpus(
        classifier,
        split["calibration"]["corpus"]["tensors"],
        split["calibration"]["corpus"]["metadata"],
        forbidden_action_indices=forbidden,
        severe_harm_floor=float(FIXED_OFFLINE_GATES["severe_harm_floor"]),
    )
    evaluation_metrics = evaluate_selective_corpus(
        classifier,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden_action_indices=forbidden,
        severe_harm_floor=float(FIXED_OFFLINE_GATES["severe_harm_floor"]),
    )
    offline_gate = apply_offline_gates(evaluation_metrics)
    split_hashes = {
        name: split[name]["split_sha256"] for name in ("fit", "calibration")
    }
    corpus_hashes = {
        "train": registration["inputs"]["train_corpus"]["sha256"],
        "evaluation": registration["inputs"]["evaluation_corpus"]["sha256"],
    }
    artifact = build_selective_development_artifact(
        classifier,
        parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        corpus_sha256=corpus_hashes,
        recipe=recipe,
        split_sha256=split_hashes,
        class_support=split["fit"]["class_support"],
        ranking_support=int(fit["ranking_support"]),
        sampling_plan_sha256=fit["sampling_plan_sha256"],
        telemetry={
            "fit": fit,
            "calibration": calibration,
            "fit_partition": fit_metrics,
            "calibration_partition": calibration_metrics,
            "evaluation": evaluation_metrics,
        },
    )
    restored = load_selective_development_artifact(
        artifact,
        parent=parent,
        expected_metadata=metadata,
        expected_parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        expected_corpus_sha256=corpus_hashes,
        expected_recipe=recipe,
        expected_split_sha256=split_hashes,
        expected_sampling_plan_sha256=fit["sampling_plan_sha256"],
    )
    if not _selection_exact(
        classifier, restored, evaluation["tensors"], evaluation["metadata"], forbidden
    ):
        raise RuntimeError("selective classifier artifact roundtrip changed policy")
    report = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "execution_commit": _current_commit(),
        "registration_sha256": registration_sha256,
        "recipe": copy.deepcopy(recipe),
        "offline_gates": copy.deepcopy(registration["offline_gates"]),
        "inputs": copy.deepcopy(registration["inputs"]),
        "initialization": initialization,
        "parent_parameter_sha256": parameter_sha256(parent_state),
        "split": {
            name: {
                key: value
                for key, value in split[name].items()
                if key not in {"corpus", "row_indices"}
            }
            for name in ("fit", "calibration")
        },
        "fit": fit,
        "fit_partition": fit_metrics,
        "calibration": calibration,
        "calibration_partition": calibration_metrics,
        "evaluation": evaluation_metrics,
        "evaluation_provenance": {
            "row_count": evaluation["row_count"],
            "loaded_after_fit_and_calibration": True,
            "seed_disjoint": True,
        },
        "offline_gate": offline_gate,
        "artifact_roundtrip_exact": True,
        "parameter_sweep": False,
        "decision": offline_gate["decision"],
        "output_dir": str(paths["output_dir"]),
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }
    output = paths["output_dir"]
    staging = output.with_name(f".{output.name}.staging")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = staging / "action_relative_selective_classifier_development.pth"
        torch.save(artifact, artifact_path)
        report["artifact"] = {
            "path": artifact_path.name,
            "sha256": sha256_file(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
            "production_compatible": False,
        }
        (staging / "report.json").write_bytes(_canonical_json_bytes(report))
        (staging / "summary.md").write_text(
            _render_summary(report), encoding="ascii", newline="\n"
        )
        os.replace(staging, output)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, required=True)
    arguments = parser.parse_args()
    report = run(arguments.registration)
    print(json.dumps({"decision": report["decision"], "output_dir": report["output_dir"]}))


if __name__ == "__main__":
    main()
