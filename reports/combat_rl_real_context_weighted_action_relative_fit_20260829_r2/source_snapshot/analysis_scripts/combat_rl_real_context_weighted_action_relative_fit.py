"""Fit one real-context-weighted action-relative item-semantic classifier."""

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

from analysis_scripts.combat_lightspeed_replay_distribution_calibration import (  # noqa: E402
    RealReplayBinding,
    load_real_replay_bindings,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    create_fresh_trainer,
    initialize_trainer,
    load_initial_checkpoint,
    parameter_sha256,
)
from analysis_scripts.combat_rl_action_relative_selective_classifier_fit import (  # noqa: E402
    FIXED_OFFLINE_GATES as BASE_OFFLINE_GATES,
    FIXED_RECIPE as BASE_RECIPE,
    _evidence,
    _pair_features,
    _selection_exact,
    _sha256_tensors,
    evaluate_selective_corpus,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    _current_commit,
    _trainer_metadata,
    _validate_commit,
    load_corpus,
    sha256_file,
)
from analysis_scripts import combat_rl_real_context_balanced_corpus as balanced  # noqa: E402
from spirecomm.ai.rl.v2.action_relative_selective_classifier import (  # noqa: E402
    BENEFICIAL_CLASS,
    CLASS_NAMES,
    ActionRelativeSelectiveClassifier,
    ActionRelativeSelectiveConfig,
    build_selective_development_artifact,
    build_supported_selective_corpus,
    build_within_state_ranking_pairs,
    load_selective_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256  # noqa: E402


SCHEMA_VERSION = "combat-rl-real-context-weighted-action-relative-fit-report-v1"
REGISTRATION_SCHEMA = (
    "combat-rl-real-context-weighted-action-relative-fit-registration-v1"
)
MANIFEST_SCHEMA = "combat-rl-real-context-weighted-action-relative-fit-manifest-v1"
EXPERIMENT_ID = "combat-rl-real-context-weighted-action-relative-fit-20260829-r2"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
OUTPUT_DIR = REPORTS_ROOT / EXPERIMENT_ID.replace("-", "_")
STAGING_DIR = REPORTS_ROOT / f".{OUTPUT_DIR.name}.staging"
REGISTRATION_PATH = REPORTS_ROOT / f"{EXPERIMENT_ID.replace('-', '_')}_registration.json"
PREFLIGHT_PATH = REPORTS_ROOT / f"{EXPERIMENT_ID.replace('-', '_')}_preflight.json"
STARTED_RECEIPT_PATH = REPORTS_ROOT / f".{EXPERIMENT_ID}.started.json"

SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_real_context_weighted_action_relative_fit.py",
    "analysis_scripts/combat_rl_action_relative_selective_classifier_fit.py",
    "analysis_scripts/combat_rl_real_context_balanced_corpus.py",
    "analysis_scripts/combat_lightspeed_replay_distribution_calibration.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "spirecomm/ai/rl/v2/action_relative_selective_classifier.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/action_space.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
    "spirecomm/ai/rl/v2/network.py",
)

FIXED_INPUTS = {
    "predecessor_failure": {
        "path": REPORTS_ROOT
        / "combat_rl_real_context_weighted_action_relative_fit_20260829_r1_failure.json",
        "sha256": "544ef6acf2d103c7c1f1bbe2aeca3f2c1355d3de63b6a2c291ea466bb14f5524",
    },
    "items_json": {
        "path": Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\export\items.json"),
        "sha256": "e23784ea8ed3092e3bfa9918240e162a9cbcb837badfb53c612eb0d83cc811dc",
    },
    "parent_checkpoint": {
        "path": REPORTS_ROOT
        / "combat_lightspeed_production_r16_shadow_20260819_r1"
        / "simulator_only_production_shadow.pth",
        "sha256": "ce2ae34f82b3f457fb35e87d429c397204c42d0f742d3ac8952d91b69119b83b",
    },
    "train_corpus": {
        "path": REPORTS_ROOT
        / "combat_rl_fresh_evaluation_context_support_supplement_20260829_r1"
        / "train_corpus.pt",
        "sha256": "af2c1d40f307eacee951333462ad5688e276f6006c8a6b0b5f5189b92845bbe2",
    },
    "base_evaluation_corpus": {
        "path": REPORTS_ROOT
        / "combat_rl_fresh_evaluation_context_support_supplement_20260829_r1"
        / "evaluation_corpus.pt",
        "sha256": "c91532a0a5eb9ce8dc5611bdf54104f24b4567a78ad03425615dec574a6de6ce",
    },
    "evaluation_supplement": {
        "path": REPORTS_ROOT
        / "combat_rl_floor_23_27_fresh_support_20260829_r1"
        / "evaluation_corpus.pt",
        "sha256": "e63bbc303abef4a71ad545cb55481d0bdeb74429a835edfcb612139aa8b3b1df",
    },
    "support_gate_report": {
        "path": REPORTS_ROOT
        / "combat_rl_floor_23_27_context_support_gate_20260829_r1.json",
        "sha256": "e7c233b6c73421871b9be2581cbcf1d8ce3be5e3b86d3e018d3e14856bb01e66",
    },
    "real_r14_replay": {
        "path": REPORTS_ROOT
        / "combat_rl_parent_on_policy_replay_collection_20260818_r14"
        / "rl_combat_model_ep20_steps3765.pth",
        "sha256": "eed11099d1b8d35baa8ce0ccbf87efb6fb4a864e6fe6246837b0cac91c505014",
    },
    "real_r15_replay": {
        "path": REPORTS_ROOT
        / "combat_rl_parent_on_policy_replay_collection_20260818_r15"
        / "rl_combat_model_ep20_steps3920.pth",
        "sha256": "67c3a49fbb2094d20793214c0a4a294684054eb6f4a24ac59573fab29c39a2dd",
    },
}

FIXED_RECIPE = copy.deepcopy(BASE_RECIPE)
FIXED_RECIPE.update(
    {
        "architecture": "frozen_parent_action_relative_item_semantic_three_class_classifier",
        "include_item_semantics": True,
        "split": "source_seed_parity_even_fit_odd_calibration",
        "classification_weighting": "state_context_weight_divided_by_supported_pair_count_then_class_normalized",
        "ranking_weighting": "state_context_weight_divided_by_ranking_pair_count",
        "calibration_method": "weighted_finite_sample_higher_negative_class",
        "fit_expected_source_rows": 4100,
        "calibration_expected_source_rows": 4213,
        "fresh_evaluation_expected_source_rows": 10688,
    }
)
for key in (
    "fit_seed_first",
    "fit_seed_last",
    "calibration_seed_first",
    "calibration_seed_last",
):
    FIXED_RECIPE.pop(key, None)
FIXED_OFFLINE_GATES = copy.deepcopy(BASE_OFFLINE_GATES)

REGISTERED_AUTHORITY = {
    "cpu_model_fitting": True,
    "fresh_evaluation": True,
    "native_loading": False,
    "lightspeed": False,
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
    "lightspeed": False,
    "gameplay": False,
    "communication_mod": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}


def _canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True).encode("ascii")
        + b"\n"
    )


def seed_parity_split_indices(
    metadata: Sequence[Mapping[str, Any]],
) -> dict[str, torch.Tensor]:
    rows: dict[str, list[int]] = {"fit": [], "calibration": []}
    for index, row in enumerate(metadata):
        seed = row.get("seed") if isinstance(row, Mapping) else None
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("weighted fit corpus seed is invalid")
        rows["fit" if seed % 2 == 0 else "calibration"].append(index)
    result = {
        name: torch.tensor(indices, dtype=torch.long) for name, indices in rows.items()
    }
    if any(not indices.numel() for indices in result.values()):
        raise ValueError("weighted fit seed parity partition is empty")
    return result


def _selected_corpus(
    corpus: Mapping[str, Any], indices: torch.Tensor, *, partition: str
) -> dict[str, Any]:
    values = balanced.validate_corpus(corpus, expected_partition=partition)
    indices = indices.reshape(-1).long().cpu()
    if not indices.numel() or bool((indices < 0).any()) or bool(
        (indices >= values["row_count"]).any()
    ):
        raise ValueError("weighted fit corpus indices are invalid")
    selected = {
        "partition": partition,
        "tensors": {
            name: values["tensors"][name][indices]
            for name in balanced.TENSOR_NAMES
        },
        "metadata": [copy.deepcopy(values["metadata"][int(index)]) for index in indices],
        "row_count": int(indices.numel()),
    }
    return balanced.validate_corpus(selected, expected_partition=partition)


def _loaded_balanced_corpus(path: Path, *, partition: str) -> dict[str, Any]:
    value = load_corpus(path, expected_partition=partition)
    projected = {
        "partition": partition,
        "tensors": {
            name: value["tensors"][name] for name in balanced.TENSOR_NAMES
        },
        "metadata": value["metadata"],
        "row_count": value["row_count"],
    }
    return balanced.validate_corpus(projected, expected_partition=partition)


def append_formal_evaluation_corpus(
    base: Mapping[str, Any], supplement: Mapping[str, Any]
) -> dict[str, Any]:
    left = balanced.validate_corpus(
        base, expected_partition="evaluation", require_both_classes=False
    )
    right = balanced.validate_corpus(
        supplement, expected_partition="evaluation", require_both_classes=False
    )
    for name in balanced.TENSOR_NAMES:
        if left["tensors"][name].shape[1:] != right["tensors"][name].shape[1:]:
            raise ValueError(f"weighted fit corpus tensor shape differs: {name}")
    appended_metadata: list[dict[str, Any]] = []
    for raw in right["metadata"]:
        row = copy.deepcopy(raw)
        if "source_component" in row:
            raise ValueError("weighted fit supplement already has a source component")
        row["source_component"] = "floor_23_27_fresh_evaluation_supplement"
        appended_metadata.append(row)
    combined = {
        "partition": "evaluation",
        "tensors": {
            name: torch.cat((left["tensors"][name], right["tensors"][name]), dim=0)
            for name in balanced.TENSOR_NAMES
        },
        "metadata": copy.deepcopy(left["metadata"]) + appended_metadata,
        "row_count": int(left["row_count"]) + int(right["row_count"]),
    }
    return balanced.validate_corpus(combined, expected_partition="evaluation")


def derive_pair_sampling_weights(
    pair_row_indices: torch.Tensor,
    state_weights: torch.Tensor,
    *,
    labels: torch.Tensor,
) -> dict[str, Any]:
    rows = pair_row_indices.reshape(-1).long().cpu()
    labels = labels.reshape(-1).long().cpu()
    state_weights = state_weights.reshape(-1).double().cpu()
    if rows.shape != labels.shape or not rows.numel():
        raise ValueError("weighted fit pair rows and labels differ")
    if bool((rows < 0).any()) or bool((rows >= state_weights.numel()).any()):
        raise ValueError("weighted fit pair row is outside state weights")
    if not bool(torch.isfinite(state_weights).all()) or bool((state_weights < 0).any()):
        raise ValueError("weighted fit state weights are invalid")
    pair_counts = torch.bincount(rows, minlength=state_weights.numel()).double()
    raw = state_weights[rows] / pair_counts[rows]
    normalized = torch.zeros_like(raw)
    class_mass: list[float] = []
    for class_index in range(3):
        mask = labels.eq(class_index)
        mass = float(raw[mask].sum())
        class_mass.append(mass)
        if mass > 0.0:
            normalized[mask] = raw[mask] / mass
    return {
        "raw": raw,
        "normalized_by_class": normalized,
        "class_mass": class_mass,
        "pair_count_per_state": pair_counts.long(),
    }


def build_weighted_class_balanced_sample_plan(
    labels: torch.Tensor,
    weights: torch.Tensor,
    *,
    updates: int,
    samples_per_class: int,
    seed: int,
) -> torch.Tensor:
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in (updates, samples_per_class)
    ):
        raise ValueError("weighted fit sampling dimensions must be positive")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("weighted fit sampling seed is invalid")
    labels = labels.reshape(-1).long().cpu()
    weights = weights.reshape(-1).double().cpu()
    if labels.shape != weights.shape or not bool(torch.isfinite(weights).all()) or bool(
        (weights < 0).any()
    ):
        raise ValueError("weighted fit class sampling inputs differ")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    samples: list[torch.Tensor] = []
    for class_index in range(3):
        pool = labels.eq(class_index).nonzero(as_tuple=False).reshape(-1)
        probabilities = weights[pool]
        mass = float(probabilities.sum())
        if not pool.numel() or not math.isfinite(mass) or mass <= 0.0:
            raise ValueError("weighted fit class lacks positive sampling mass")
        offsets = torch.multinomial(
            probabilities / mass,
            updates * samples_per_class,
            replacement=True,
            generator=generator,
        ).reshape(updates, samples_per_class)
        samples.append(pool[offsets])
    return torch.stack(samples, dim=1)


def derive_ranking_sampling_weights(
    ranking_pairs: torch.Tensor,
    pair_row_indices: torch.Tensor,
    state_weights: torch.Tensor,
) -> torch.Tensor:
    pairs = ranking_pairs.reshape(-1, 2).long().cpu()
    pair_rows = pair_row_indices.reshape(-1).long().cpu()
    state_weights = state_weights.reshape(-1).double().cpu()
    if not pairs.numel() or bool((pairs < 0).any()) or bool(
        (pairs >= pair_rows.numel()).any()
    ):
        raise ValueError("weighted fit ranking pairs are invalid")
    positive_rows = pair_rows[pairs[:, 0]]
    negative_rows = pair_rows[pairs[:, 1]]
    if not torch.equal(positive_rows, negative_rows):
        raise ValueError("weighted fit ranking pair crosses source states")
    if bool((positive_rows < 0).any()) or bool(
        (positive_rows >= state_weights.numel()).any()
    ):
        raise ValueError("weighted fit ranking state is outside weights")
    counts = torch.bincount(positive_rows, minlength=state_weights.numel()).double()
    raw = state_weights[positive_rows] / counts[positive_rows]
    mass = float(raw.sum())
    if not math.isfinite(mass) or mass <= 0.0:
        raise ValueError("weighted fit ranking lacks positive sampling mass")
    return raw / mass


def build_weighted_replacement_sample_plan(
    weights: torch.Tensor,
    *,
    updates: int,
    samples_per_update: int,
    seed: int,
) -> torch.Tensor:
    if any(
        not isinstance(value, int) or isinstance(value, bool) or value <= 0
        for value in (updates, samples_per_update)
    ):
        raise ValueError("weighted fit replacement dimensions must be positive")
    if not isinstance(seed, int) or isinstance(seed, bool) or seed < 0:
        raise ValueError("weighted fit replacement seed is invalid")
    weights = weights.reshape(-1).double().cpu()
    mass = float(weights.sum())
    if not weights.numel() or not bool(torch.isfinite(weights).all()) or bool(
        (weights < 0).any()
    ) or not math.isfinite(mass) or mass <= 0.0:
        raise ValueError("weighted fit replacement weights are invalid")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(seed)
    return torch.multinomial(
        weights / mass,
        updates * samples_per_update,
        replacement=True,
        generator=generator,
    ).reshape(updates, samples_per_update)


def weighted_higher_quantile(
    values: torch.Tensor, weights: torch.Tensor, *, quantile: float
) -> tuple[float, dict[str, Any]]:
    values = values.reshape(-1).double().cpu()
    weights = weights.reshape(-1).double().cpu()
    if values.shape != weights.shape or not values.numel():
        raise ValueError("weighted quantile values and weights differ")
    if not bool(torch.isfinite(values).all()) or not bool(torch.isfinite(weights).all()):
        raise ValueError("weighted quantile inputs must be finite")
    if bool((weights < 0.0).any()) or not 0.0 < float(quantile) < 1.0:
        raise ValueError("weighted quantile inputs are invalid")
    mass = float(weights.sum())
    if mass <= 0.0:
        raise ValueError("weighted quantile lacks positive mass")
    count = int(values.numel())
    rank = min(count, math.ceil((count + 1) * float(quantile)))
    target = rank / count
    order = torch.tensor(
        sorted(range(count), key=lambda index: (float(values[index]), index)),
        dtype=torch.long,
    )
    sorted_values = values[order]
    sorted_weights = weights[order] / mass
    cumulative = sorted_weights.cumsum(dim=0)
    position = int(torch.searchsorted(cumulative, torch.tensor(target, dtype=cumulative.dtype)))
    position = min(position, count - 1)
    threshold = float(sorted_values[position])
    return threshold, {
        "quantile": float(quantile),
        "raw_count": count,
        "finite_sample_rank": rank,
        "cumulative_target": target,
        "selected_position": position,
        "selected_cumulative_weight": float(cumulative[position]),
        "minimum": float(sorted_values[0]),
        "maximum": float(sorted_values[-1]),
    }


def weighted_policy_metrics(
    *,
    selected_true: torch.Tensor,
    best_with_guard: torch.Tensor,
    intervention_rows: torch.Tensor,
    state_weights: torch.Tensor,
    beneficial_floor: float,
) -> dict[str, float]:
    selected_true = selected_true.reshape(-1).double().cpu()
    best_with_guard = best_with_guard.reshape(-1).double().cpu()
    intervention_rows = intervention_rows.reshape(-1).bool().cpu()
    state_weights = state_weights.reshape(-1).double().cpu()
    if not (
        selected_true.shape
        == best_with_guard.shape
        == intervention_rows.shape
        == state_weights.shape
    ):
        raise ValueError("weighted policy metric rows differ")
    if not bool(torch.isfinite(selected_true).all()) or not bool(
        torch.isfinite(best_with_guard).all()
    ) or not bool(torch.isfinite(state_weights).all()) or bool((state_weights < 0).any()):
        raise ValueError("weighted policy metric inputs are invalid")
    mass = float(state_weights.sum())
    if mass <= 0.0:
        raise ValueError("weighted policy metric state mass is empty")
    normalized = state_weights / mass
    intervention_mass = float(normalized[intervention_rows].sum())
    beneficial_mass = float(
        normalized[intervention_rows & selected_true.ge(float(beneficial_floor))].sum()
    )
    return {
        "intervention_mass": intervention_mass,
        "intervention_precision": (
            beneficial_mass / intervention_mass if intervention_mass > 0.0 else 0.0
        ),
        "mean_selected_true_advantage": float((normalized * selected_true).sum()),
        "mean_policy_regret": float(
            (normalized * (best_with_guard - selected_true)).sum()
        ),
    }


def apply_weighted_offline_gates(
    raw_metrics: Mapping[str, Any], weighted_metrics: Mapping[str, Any]
) -> dict[str, Any]:
    selection = raw_metrics["selection"]
    conditions = {
        "raw_minimum_intervention_count": int(selection["intervention_count"])
        >= int(FIXED_OFFLINE_GATES["minimum_intervention_count"]),
        "weighted_minimum_intervention_precision": float(
            weighted_metrics["intervention_precision"]
        )
        >= float(FIXED_OFFLINE_GATES["minimum_intervention_precision"]),
        "weighted_minimum_mean_selected_true_advantage_exclusive": float(
            weighted_metrics["mean_selected_true_advantage"]
        )
        > float(FIXED_OFFLINE_GATES["minimum_mean_selected_true_advantage_exclusive"]),
        "weighted_maximum_mean_policy_regret_exclusive": float(
            weighted_metrics["mean_policy_regret"]
        )
        < float(FIXED_OFFLINE_GATES["maximum_mean_policy_regret_exclusive"]),
        "raw_severe_harm_count_zero": int(selection["severe_harm_count"]) == 0,
        "raw_illegal_action_count_zero": int(selection["illegal_action_count"]) == 0,
        "raw_forbidden_action_selection_count_zero": int(
            selection["forbidden_action_selection_count"]
        )
        == 0,
    }
    passed = all(conditions.values())
    return {
        "conditions": conditions,
        "all_conditions_passed": passed,
        "decision": (
            "offline_passed_propose_fresh_lightspeed_gate"
            if passed
            else "offline_failed_close_without_fresh_gate_or_sweep"
        ),
    }


def validate_support_gate_report(report: Mapping[str, Any]) -> dict[str, bool]:
    bindings = report.get("bindings", {})
    conditions = {
        "schema": report.get("schema_version")
        == "combat-rl-floor-23-27-context-support-gate-v1",
        "decision": report.get("decision")
        == "corpus_support_ready_for_separate_weighted_fit",
        "all_support_conditions": report.get("support_gate", {}).get(
            "all_conditions_passed"
        )
        is True,
        "train_rows": report.get("partitions", {}).get("train_rows") == 8313,
        "evaluation_rows": report.get("partitions", {}).get(
            "combined_evaluation_rows"
        )
        == 10688,
        "train_hash": bindings.get("base_train_corpus", {}).get("sha256")
        == FIXED_INPUTS["train_corpus"]["sha256"],
        "base_evaluation_hash": bindings.get("base_evaluation_corpus", {}).get(
            "sha256"
        )
        == FIXED_INPUTS["base_evaluation_corpus"]["sha256"],
        "supplement_hash": bindings.get("formal_evaluation_supplement", {}).get(
            "sha256"
        )
        == FIXED_INPUTS["evaluation_supplement"]["sha256"],
        "poc_excluded": report.get("selection_boundary", {}).get(
            "opportunity_poc_excluded"
        )
        is True,
        "separate_fit_authority": report.get("authority", {}).get(
            "separate_weighted_fit_proposal"
        )
        is True,
        "no_training_authority": report.get("authority", {}).get("training") is False,
        "no_game_authority": report.get("authority", {}).get("gameplay") is False,
    }
    if not all(conditions.values()):
        raise ValueError("weighted fit support gate binding differs")
    return conditions


def _fit_weighted_classifier(
    *,
    parent: torch.nn.Module,
    metadata: Mapping[str, Any],
    corpus: Mapping[str, Any],
    state_weights: torch.Tensor,
) -> tuple[ActionRelativeSelectiveClassifier, dict[str, Any]]:
    with torch.random.fork_rng(devices=[]):
        torch.manual_seed(int(FIXED_RECIPE["model_initialization_seed"]))
        classifier = ActionRelativeSelectiveClassifier(
            parent,
            metadata,
            ActionRelativeSelectiveConfig(
                hidden_dim=int(FIXED_RECIPE["hidden_dim"]),
                include_item_semantics=True,
            ),
            selection_threshold=0.0,
        )
    pair_weights = derive_pair_sampling_weights(
        corpus["pair_row_indices"], state_weights, labels=corpus["labels"]
    )
    class_plan = build_weighted_class_balanced_sample_plan(
        corpus["labels"],
        pair_weights["normalized_by_class"],
        updates=int(FIXED_RECIPE["updates"]),
        samples_per_class=int(FIXED_RECIPE["samples_per_class_per_update"]),
        seed=int(FIXED_RECIPE["sampling_seed"]),
    )
    ranking_pairs = build_within_state_ranking_pairs(
        corpus["pair_row_indices"], corpus["labels"]
    )
    ranking_weights = derive_ranking_sampling_weights(
        ranking_pairs, corpus["pair_row_indices"], state_weights
    )
    ranking_plan = build_weighted_replacement_sample_plan(
        ranking_weights,
        updates=int(FIXED_RECIPE["updates"]),
        samples_per_update=int(FIXED_RECIPE["ranking_pairs_per_update"]),
        seed=int(FIXED_RECIPE["ranking_sampling_seed"]),
    )
    features = _pair_features(classifier, corpus)
    labels = corpus["labels"].long().cpu()
    parent_before = state_dict_sha256(classifier.parent.state_dict())
    optimizer = torch.optim.Adam(
        classifier.classifier.parameters(), lr=float(FIXED_RECIPE["learning_rate"])
    )
    losses: list[float] = []
    classifier.train()
    for update in range(int(FIXED_RECIPE["updates"])):
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
        loss = classification_loss + float(
            FIXED_RECIPE["ranking_loss_weight"]
        ) * ranking_loss
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("weighted fit objective became non-finite")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if any(
            parameter.grad is not None for parameter in classifier.parent.parameters()
        ):
            raise RuntimeError("weighted fit produced frozen parent gradients")
        optimizer.step()
        losses.append(float(loss.detach()))
    classifier.eval()
    parent_after = state_dict_sha256(classifier.parent.state_dict())
    if parent_before != parent_after:
        raise RuntimeError("weighted fit changed the frozen parent")
    return classifier, {
        "update_count": int(FIXED_RECIPE["updates"]),
        "ranking_support": int(ranking_pairs.shape[0]),
        "sampling_plan_sha256": _sha256_tensors(
            class_plan,
            pair_weights["raw"],
            pair_weights["normalized_by_class"],
            ranking_pairs,
            ranking_weights,
            ranking_plan,
        ),
        "pair_weight_sha256": _sha256_tensors(pair_weights["raw"]),
        "ranking_weight_sha256": _sha256_tensors(ranking_weights),
        "class_mass": pair_weights["class_mass"],
        "loss_first": losses[0],
        "loss_last": losses[-1],
        "loss_minimum": min(losses),
        "loss_maximum": max(losses),
        "loss_mean": sum(losses) / len(losses),
        "parent_state_dict_sha256_before": parent_before,
        "parent_state_dict_sha256_after": parent_after,
        "parent_frozen": True,
        "classifier_state_dict_sha256": state_dict_sha256(
            classifier.classifier.state_dict()
        ),
    }


def _calibrate_weighted_threshold(
    classifier: ActionRelativeSelectiveClassifier,
    corpus: Mapping[str, Any],
    state_weights: torch.Tensor,
) -> tuple[ActionRelativeSelectiveClassifier, dict[str, Any]]:
    pair_weights = derive_pair_sampling_weights(
        corpus["pair_row_indices"], state_weights, labels=corpus["labels"]
    )
    features = _pair_features(classifier, corpus)
    with torch.no_grad():
        evidence = _evidence(classifier.classifier(features)).cpu()
    negative = corpus["labels"].cpu().ne(BENEFICIAL_CLASS)
    threshold, details = weighted_higher_quantile(
        evidence[negative],
        pair_weights["raw"][negative],
        quantile=float(FIXED_RECIPE["calibration_quantile"]),
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
        "negative_count": int(negative.sum()),
        "pair_count": int(evidence.numel()),
        "pair_weight_sha256": _sha256_tensors(pair_weights["raw"]),
        "classifier_state_dict_sha256": state_dict_sha256(
            calibrated.classifier.state_dict()
        ),
        **details,
    }


def _policy_vectors(
    classifier: ActionRelativeSelectiveClassifier,
    tensors: Mapping[str, torch.Tensor],
    metadata: Sequence[Mapping[str, Any]],
    forbidden_action_indices: Sequence[int],
) -> dict[str, torch.Tensor]:
    corpus = build_supported_selective_corpus(tensors, metadata)
    forbidden = frozenset(int(value) for value in forbidden_action_indices)
    with torch.no_grad():
        selection = classifier.select_actions(
            **corpus["tensors"],
            alternative_masks=corpus["alternative_masks"],
            forbidden_action_indices=forbidden,
        )
    supported_count = int(corpus["tensors"]["guard_actions"].numel())
    action_dim = int(corpus["tensors"]["action_masks"].shape[1])
    true_matrix = torch.full((supported_count, action_dim), float("-inf"))
    true_matrix[corpus["pair_row_indices"].cpu(), corpus["candidate_actions"].cpu()] = (
        corpus["raw_advantages"].cpu()
    )
    allowed = corpus["alternative_masks"].cpu().clone()
    for action in forbidden:
        allowed[:, action] = False
    rows = torch.arange(supported_count)
    interventions = selection.gate_open.cpu()
    supported_selected = torch.zeros(supported_count)
    supported_selected[interventions] = true_matrix[
        rows[interventions], selection.actions.cpu()[interventions]
    ]
    allowed_true = true_matrix.masked_fill(~allowed, float("-inf"))
    has_allowed = allowed.any(dim=1)
    best_allowed = torch.zeros(supported_count)
    best_allowed[has_allowed] = allowed_true[has_allowed].max(dim=1).values
    supported_best = torch.maximum(best_allowed, torch.zeros_like(best_allowed))
    source_count = len(metadata)
    source_indices = corpus["source_row_indices"].cpu()
    selected_true = torch.zeros(source_count)
    selected_true[source_indices] = supported_selected
    best_with_guard = torch.zeros(source_count)
    best_with_guard[source_indices] = supported_best
    intervention_rows = torch.zeros(source_count, dtype=torch.bool)
    intervention_rows[source_indices] = interventions
    return {
        "selected_true": selected_true,
        "best_with_guard": best_with_guard,
        "intervention_rows": intervention_rows,
    }


def evaluate_weighted_corpus(
    classifier: ActionRelativeSelectiveClassifier,
    corpus: Mapping[str, Any],
    state_weights: torch.Tensor,
) -> dict[str, Any]:
    raw = evaluate_selective_corpus(
        classifier,
        corpus["tensors"],
        corpus["metadata"],
        forbidden_action_indices=FIXED_RECIPE["forbidden_action_indices"],
        severe_harm_floor=float(FIXED_OFFLINE_GATES["severe_harm_floor"]),
    )
    vectors = _policy_vectors(
        classifier,
        corpus["tensors"],
        corpus["metadata"],
        FIXED_RECIPE["forbidden_action_indices"],
    )
    weighted = weighted_policy_metrics(
        **vectors,
        state_weights=state_weights,
        beneficial_floor=float(FIXED_RECIPE["beneficial_lower_inclusive"]),
    )
    return {"raw": raw, "weighted": weighted}


def _validated_source_commit(source_commit: str) -> str:
    source_commit = _validate_commit(source_commit)
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, _current_commit()],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("weighted fit source commit is not an ancestor")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", source_commit, "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"weighted fit source changed: {relative}")
    return source_commit


def _input_bindings(*, deferred_evaluation: bool) -> dict[str, Path]:
    deferred = {"base_evaluation_corpus", "evaluation_supplement"}
    paths: dict[str, Path] = {}
    for name, binding in FIXED_INPUTS.items():
        path = Path(binding["path"]).resolve()
        if deferred_evaluation and name in deferred:
            paths[name] = path
            continue
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError(f"weighted fit input binding differs: {name}")
        paths[name] = path
    return paths


def _registration_payload(
    source_commit: str, source_files: Mapping[str, str]
) -> dict[str, Any]:
    command = [
        str(EXPECTED_INTERPRETER),
        "-I",
        str((REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve()),
        "--registration",
        str(REGISTRATION_PATH.resolve()),
    ]
    return {
        "schema_version": REGISTRATION_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "interpreter": str(EXPECTED_INTERPRETER),
        "isolated_mode": True,
        "runner": {
            "path": str((REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve()),
            "sha256": source_files[SOURCE_SNAPSHOT_PATHS[0]],
        },
        "source_files": source_files,
        "inputs": {
            name: {
                "path": str(Path(binding["path"]).resolve()),
                "sha256": binding["sha256"],
            }
            for name, binding in FIXED_INPUTS.items()
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "offline_gates": copy.deepcopy(FIXED_OFFLINE_GATES),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
        "command": command,
        "cwd": str(REPO_ROOT),
        "output_dir": str(OUTPUT_DIR),
        "staging_dir": str(STAGING_DIR),
        "started_receipt": str(STARTED_RECEIPT_PATH),
        "attempt_limit": 1,
    }


def build_registration(source_commit: str) -> dict[str, Any]:
    source_commit = _validated_source_commit(source_commit)
    _input_bindings(deferred_evaluation=False)
    if any(path.exists() for path in (OUTPUT_DIR, STAGING_DIR, STARTED_RECEIPT_PATH)):
        raise ValueError("weighted fit output, staging, or started receipt already exists")
    source_files = {
        relative: sha256_file(REPO_ROOT / relative) for relative in SOURCE_SNAPSHOT_PATHS
    }
    return _registration_payload(source_commit, source_files)


def validate_registration(registration: Mapping[str, Any]) -> dict[str, Any]:
    source_commit = _validated_source_commit(registration.get("source_commit"))
    source_files = {
        relative: sha256_file(REPO_ROOT / relative) for relative in SOURCE_SNAPSHOT_PATHS
    }
    expected = _registration_payload(source_commit, source_files)
    if registration != expected:
        raise ValueError("weighted fit registration binding differs")
    return copy.deepcopy(expected)


def write_registration(source_commit: str) -> dict[str, Any]:
    if REGISTRATION_PATH.exists() or PREFLIGHT_PATH.exists():
        raise ValueError("weighted fit registration or preflight already exists")
    registration = build_registration(source_commit)
    preflight = {
        "schema_version": "combat-rl-real-context-weighted-action-relative-fit-preflight-v1",
        "verdict": "source_only_preflight_passed",
        "source_commit": registration["source_commit"],
        "head_commit": _current_commit(),
        "registration_sha256": hashlib.sha256(
            _canonical_json_bytes(registration)
        ).hexdigest(),
        "input_hashes_validated": True,
        "output_absent": True,
        "staging_absent": True,
        "started_receipt_absent": True,
        "model_loaded": False,
        "optimizer_constructed": False,
        "fresh_evaluation_loaded": False,
        "native_loaded": False,
        "game_started": False,
    }
    REGISTRATION_PATH.write_bytes(_canonical_json_bytes(registration))
    PREFLIGHT_PATH.write_bytes(_canonical_json_bytes(preflight))
    return preflight


def _write_started_receipt(registration: Mapping[str, Any]) -> dict[str, Any]:
    receipt = {
        "schema_version": "combat-rl-real-context-weighted-action-relative-fit-started-v1",
        "experiment_id": EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "registration_sha256": sha256_file(REGISTRATION_PATH),
        "started_unix_time": time.time(),
        "attempt": 1,
    }
    descriptor = os.open(
        STARTED_RECEIPT_PATH, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644
    )
    with os.fdopen(descriptor, "wb") as handle:
        handle.write(_canonical_json_bytes(receipt))
    return receipt


def _split_report(
    name: str,
    indices: torch.Tensor,
    partition: Mapping[str, Any],
    supported: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    expected = int(FIXED_RECIPE[f"{name}_expected_source_rows"])
    if partition["row_count"] != expected:
        raise ValueError(f"weighted fit {name} row count differs")
    class_support = {
        class_name: int(supported["labels"].eq(index).sum())
        for index, class_name in enumerate(CLASS_NAMES)
    }
    if any(value <= 0 for value in class_support.values()):
        raise ValueError(f"weighted fit {name} class support is incomplete")
    state_weights = context["weights"][supported["source_row_indices"].cpu()]
    ranking_pairs = build_within_state_ranking_pairs(
        supported["pair_row_indices"], supported["labels"]
    )
    if not ranking_pairs.numel():
        raise ValueError(f"weighted fit {name} ranking support is empty")
    return {
        "name": name,
        "source_row_count": int(partition["row_count"]),
        "supported_row_count": int(supported["tensors"]["guard_actions"].numel()),
        "pair_count": int(supported["labels"].numel()),
        "class_support": class_support,
        "ranking_support": int(ranking_pairs.shape[0]),
        "split_sha256": _sha256_tensors(
            indices,
            supported["source_row_indices"],
            supported["pair_row_indices"],
            supported["candidate_actions"],
            supported["labels"],
            context["weights"],
        ),
        "context_metrics": context["metrics"],
        "supported_state_weight_sha256": _sha256_tensors(state_weights),
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    raw = report["evaluation"]["raw"]["selection"]
    weighted = report["evaluation"]["weighted"]
    return (
        "# Real-Context-Weighted Action-Relative Fit\n\n"
        f"- Fit rows: {report['split']['fit']['source_row_count']}\n"
        f"- Calibration rows: {report['split']['calibration']['source_row_count']}\n"
        f"- Fresh rows: {report['evaluation_provenance']['source_row_count']}\n"
        f"- Raw interventions: {raw['intervention_count']}\n"
        f"- Weighted precision: {weighted['intervention_precision']:.6f}\n"
        f"- Weighted mean selected advantage: {weighted['mean_selected_true_advantage']:.6f}\n"
        f"- Weighted mean regret: {weighted['mean_policy_regret']:.6f}\n"
        f"- Raw severe harms: {raw['severe_harm_count']}\n"
        f"- Decision: {report['decision']}\n"
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("weighted fit must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("weighted fit must run in isolated mode")
    if registration_path.resolve() != REGISTRATION_PATH.resolve():
        raise ValueError("weighted fit registration path differs")
    registration = json.loads(registration_path.read_text(encoding="ascii"))
    normalized = validate_registration(registration)
    _validated_source_commit(normalized["source_commit"])
    paths = _input_bindings(deferred_evaluation=True)
    if OUTPUT_DIR.exists() or STAGING_DIR.exists() or STARTED_RECEIPT_PATH.exists():
        raise ValueError("weighted fit output, staging, or started receipt already exists")
    support_report = json.loads(paths["support_gate_report"].read_text(encoding="ascii"))
    support_conditions = validate_support_gate_report(support_report)
    started = _write_started_receipt(normalized)

    real, real_evidence = load_real_replay_bindings(
        (
            RealReplayBinding(
                label="r14",
                path=paths["real_r14_replay"],
                sha256=FIXED_INPUTS["real_r14_replay"]["sha256"],
            ),
            RealReplayBinding(
                label="r15",
                path=paths["real_r15_replay"],
                sha256=FIXED_INPUTS["real_r15_replay"]["sha256"],
            ),
        )
    )
    train = _loaded_balanced_corpus(paths["train_corpus"], partition="train")
    split_indices = seed_parity_split_indices(train["metadata"])
    partitions = {
        name: _selected_corpus(train, indices, partition="train")
        for name, indices in split_indices.items()
    }
    contexts = {
        name: balanced.derive_context_weights(real, partition)
        for name, partition in partitions.items()
    }
    supported = {
        name: build_supported_selective_corpus(
            partition["tensors"], partition["metadata"]
        )
        for name, partition in partitions.items()
    }
    split_reports = {
        name: _split_report(
            name, split_indices[name], partitions[name], supported[name], contexts[name]
        )
        for name in ("fit", "calibration")
    }

    mapper = build_id_mapper(paths["items_json"])
    initial = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=FIXED_INPUTS["parent_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        mapper,
        seed=int(FIXED_RECIPE["model_initialization_seed"]),
        batch_size=int(FIXED_RECIPE["samples_per_class_per_update"]) * 3,
        learning_starts=64,
    )
    parent_state, initialization = initialize_trainer(trainer, initial)
    parent = trainer.online_network
    parent.eval()
    trainer_metadata = _trainer_metadata(trainer)
    fit_state_weights = contexts["fit"]["weights"][
        supported["fit"]["source_row_indices"].cpu()
    ]
    classifier, fit_report = _fit_weighted_classifier(
        parent=parent,
        metadata=trainer_metadata,
        corpus=supported["fit"],
        state_weights=fit_state_weights,
    )
    calibration_state_weights = contexts["calibration"]["weights"][
        supported["calibration"]["source_row_indices"].cpu()
    ]
    classifier, calibration_report = _calibrate_weighted_threshold(
        classifier, supported["calibration"], calibration_state_weights
    )
    frozen_classifier_sha256 = state_dict_sha256(classifier.classifier.state_dict())

    deferred_paths = _input_bindings(deferred_evaluation=False)
    base_evaluation = _loaded_balanced_corpus(
        deferred_paths["base_evaluation_corpus"], partition="evaluation"
    )
    supplement = _loaded_balanced_corpus(
        deferred_paths["evaluation_supplement"], partition="evaluation"
    )
    evaluation = append_formal_evaluation_corpus(base_evaluation, supplement)
    if evaluation["row_count"] != FIXED_RECIPE["fresh_evaluation_expected_source_rows"]:
        raise ValueError("weighted fit fresh evaluation row count differs")
    if state_dict_sha256(classifier.classifier.state_dict()) != frozen_classifier_sha256:
        raise RuntimeError("weighted fit classifier changed before fresh evaluation")
    full_train_context = balanced.derive_context_weights(real, train)
    evaluation_context = balanced.derive_context_weights(real, evaluation)
    integrity = balanced._integrity_conditions(train, evaluation)
    support_recheck = balanced.apply_support_gates(
        train_metrics=full_train_context["metrics"],
        evaluation_metrics=evaluation_context["metrics"],
        evaluation_late_floor_rows=sum(
            23 <= int(row["floor"]) <= 34 for row in evaluation["metadata"]
        ),
        integrity_conditions=integrity,
    )
    if not support_recheck["passed"] or support_recheck["decision"] != report_decision(
        support_report
    ):
        raise ValueError("weighted fit reconstructed support gate differs")
    evaluation_metrics = evaluate_weighted_corpus(
        classifier, evaluation, evaluation_context["weights"]
    )
    offline_gate = apply_weighted_offline_gates(
        evaluation_metrics["raw"], evaluation_metrics["weighted"]
    )

    corpus_hashes = {
        "train": FIXED_INPUTS["train_corpus"]["sha256"],
        "evaluation": hashlib.sha256(
            _canonical_json_bytes(
                {
                    "base_evaluation": FIXED_INPUTS["base_evaluation_corpus"][
                        "sha256"
                    ],
                    "evaluation_supplement": FIXED_INPUTS[
                        "evaluation_supplement"
                    ]["sha256"],
                    "append_order": ["base_evaluation", "evaluation_supplement"],
                }
            )
        ).hexdigest(),
    }
    split_hashes = {
        name: split_reports[name]["split_sha256"] for name in ("fit", "calibration")
    }
    artifact = build_selective_development_artifact(
        classifier,
        parent_checkpoint_sha256=FIXED_INPUTS["parent_checkpoint"]["sha256"],
        corpus_sha256=corpus_hashes,
        recipe=FIXED_RECIPE,
        split_sha256=split_hashes,
        class_support=split_reports["fit"]["class_support"],
        ranking_support=int(fit_report["ranking_support"]),
        sampling_plan_sha256=fit_report["sampling_plan_sha256"],
        telemetry={
            "fit": fit_report,
            "calibration": calibration_report,
            "evaluation": evaluation_metrics,
        },
    )
    restored = load_selective_development_artifact(
        artifact,
        parent=parent,
        expected_metadata=trainer_metadata,
        expected_parent_checkpoint_sha256=FIXED_INPUTS["parent_checkpoint"]["sha256"],
        expected_corpus_sha256=corpus_hashes,
        expected_recipe=FIXED_RECIPE,
        expected_split_sha256=split_hashes,
        expected_sampling_plan_sha256=fit_report["sampling_plan_sha256"],
    )
    if not _selection_exact(
        classifier,
        restored,
        evaluation["tensors"],
        evaluation["metadata"],
        FIXED_RECIPE["forbidden_action_indices"],
    ):
        raise RuntimeError("weighted fit artifact roundtrip changed policy")

    report = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": normalized["source_commit"],
        "execution_commit": _current_commit(),
        "started_receipt": started,
        "source_files": {
            relative: sha256_file(REPO_ROOT / relative)
            for relative in SOURCE_SNAPSHOT_PATHS
        },
        "inputs": normalized["inputs"],
        "support_gate_conditions": support_conditions,
        "support_gate_recheck": support_recheck,
        "real_replay": real_evidence,
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "offline_gates": copy.deepcopy(FIXED_OFFLINE_GATES),
        "initialization": initialization,
        "parent_parameter_sha256": parameter_sha256(parent_state),
        "split": split_reports,
        "fit": fit_report,
        "calibration": calibration_report,
        "evaluation": evaluation_metrics,
        "evaluation_context": evaluation_context["metrics"],
        "evaluation_provenance": {
            "source_row_count": int(evaluation["row_count"]),
            "loaded_after_fit_and_calibration": True,
            "classifier_sha256_at_load": frozen_classifier_sha256,
            "poc_excluded": True,
        },
        "offline_gate": offline_gate,
        "artifact_roundtrip_exact": True,
        "parameter_sweep": False,
        "attempt": 1,
        "decision": offline_gate["decision"],
        "output_dir": str(OUTPUT_DIR),
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }
    STAGING_DIR.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = STAGING_DIR / "real_context_weighted_selective_classifier.pth"
        torch.save(artifact, artifact_path)
        report["artifact"] = {
            "path": artifact_path.name,
            "sha256": sha256_file(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
            "production_compatible": False,
        }
        (STAGING_DIR / "report.json").write_bytes(_canonical_json_bytes(report))
        (STAGING_DIR / "summary.md").write_text(
            _render_summary(report), encoding="ascii", newline="\n"
        )
        shutil.copyfile(REGISTRATION_PATH, STAGING_DIR / "registration.json")
        shutil.copyfile(PREFLIGHT_PATH, STAGING_DIR / "preflight.json")
        shutil.copyfile(STARTED_RECEIPT_PATH, STAGING_DIR / "started_receipt.json")
        snapshot_root = STAGING_DIR / "source_snapshot"
        for relative in SOURCE_SNAPSHOT_PATHS:
            target = snapshot_root / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, target)
        artifacts = {}
        for path in sorted(STAGING_DIR.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                relative = path.relative_to(STAGING_DIR).as_posix()
                artifacts[relative] = {
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "experiment_id": EXPERIMENT_ID,
            "source_commit": normalized["source_commit"],
            "decision": report["decision"],
            "artifacts": artifacts,
        }
        (STAGING_DIR / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
        os.replace(STAGING_DIR, OUTPUT_DIR)
    except BaseException:
        if STAGING_DIR.exists():
            shutil.rmtree(STAGING_DIR)
        raise
    return report


def report_decision(report: Mapping[str, Any]) -> str:
    decision = report.get("decision")
    if decision != "corpus_support_ready_for_separate_weighted_fit":
        raise ValueError("weighted fit support report decision differs")
    return str(decision)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--prepare-registration", action="store_true")
    group.add_argument("--registration", type=Path)
    parser.add_argument("--source-commit")
    arguments = parser.parse_args()
    if arguments.prepare_registration:
        if not arguments.source_commit:
            parser.error("--prepare-registration requires --source-commit")
        result = write_registration(arguments.source_commit)
    else:
        if arguments.source_commit:
            parser.error("--source-commit is only valid with --prepare-registration")
        result = run(arguments.registration)
    print(json.dumps(result, sort_keys=True))


if __name__ == "__main__":
    main()
