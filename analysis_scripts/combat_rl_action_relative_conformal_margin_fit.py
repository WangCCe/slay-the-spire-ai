"""Fit and calibrate one registered action-relative conformal margin gate."""

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
from typing import Any, Mapping, Sequence

import torch


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
from analysis_scripts.combat_rl_action_relative_advantage_residual_fit import (  # noqa: E402
    _alternative_masks,
    _batch_state_inputs,
    evaluate_corpus,
)
from analysis_scripts.combat_rl_action_relative_uncertainty_ensemble_fit import (  # noqa: E402
    evaluate_ensemble_corpus,
    fit_ensemble,
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
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (  # noqa: E402
    expand_action_relative_examples,
)
from spirecomm.ai.rl.v2.action_relative_conformal_margin import (  # noqa: E402
    ActionRelativeConformalConfig,
    ActionRelativeConformalMarginGate,
    build_conformal_development_artifact,
    load_conformal_development_artifact,
)
from spirecomm.ai.rl.v2.action_relative_uncertainty_ensemble import (  # noqa: E402
    build_ensemble_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-action-relative-conformal-margin-fit-20260829-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_conformal_margin_fit.py",
    "analysis_scripts/combat_rl_action_relative_uncertainty_ensemble_fit.py",
    "analysis_scripts/combat_rl_action_relative_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "spirecomm/ai/rl/v2/action_relative_conformal_margin.py",
    "spirecomm/ai/rl/v2/action_relative_uncertainty_ensemble.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/network.py",
)

ENSEMBLE_RECIPE = {
    "architecture": "frozen_parent_action_relative_uncertainty_ensemble",
    "hidden_dim": 64,
    "member_count": 5,
    "member_seeds": [2026082911, 2026082912, 2026082913, 2026082914, 2026082915],
    "bootstrap_unit": "expanded_action_relative_pair",
    "bootstrap_sample_size": "full_pair_count_with_replacement",
    "confidence_scale": 1.0,
    "advantage_threshold": 0.5,
    "target_clip": 20.0,
    "target_scale": 10.0,
    "optimizer": "adam",
    "learning_rate": 0.001,
    "updates": 1024,
    "batch_size": 256,
    "smooth_l1_beta": 0.1,
    "device": "cpu",
    "forbidden_action_indices": [90],
}

FIXED_RECIPE = {
    "architecture": "action_relative_family_conformal_margin_gate",
    "ensemble_recipe": ENSEMBLE_RECIPE,
    "fit_seed_first": 262000,
    "fit_seed_last": 262191,
    "calibration_seed_first": 262192,
    "calibration_seed_last": 262255,
    "calibration_alpha": 0.1,
    "calibration_quantile": "finite_sample_higher",
    "correction_floor": 0.0,
    "card_action_first": 0,
    "card_action_last": 59,
    "potion_action_first": 60,
    "potion_action_last": 89,
    "minimum_family_support": 100,
    "forbidden_action_indices": [90],
    "device": "cpu",
}

FIXED_OFFLINE_GATES = {
    "minimum_intervention_count": 30,
    "minimum_intervention_precision": 0.65,
    "minimum_mean_selected_true_advantage": 0.12269661575555801,
    "maximum_mean_policy_regret": 3.2472479343414307,
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


def _sha256_indices(indices: torch.Tensor) -> str:
    return hashlib.sha256(indices.long().contiguous().numpy().tobytes()).hexdigest()


def _family_support(candidate_actions: torch.Tensor) -> dict[str, int]:
    actions = candidate_actions.long()
    return {
        "card": int(((0 <= actions) & (actions < 60)).sum().item()),
        "potion": int(((60 <= actions) & (actions < 90)).sum().item()),
    }


def split_fit_calibration_corpus(
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    *,
    fit_seeds: frozenset[int],
    calibration_seeds: frozenset[int],
    minimum_family_support: int,
) -> dict[str, dict[str, Any]]:
    if not fit_seeds or not calibration_seeds or fit_seeds & calibration_seeds:
        raise ValueError("conformal seed partitions must be non-empty and disjoint")
    row_count = len(corpus_metadata)
    if row_count <= 0 or any(tensor.shape[0] != row_count for tensor in tensors.values()):
        raise ValueError("conformal corpus tensor and metadata alignment differs")
    partition_rows = {"fit": [], "calibration": []}
    for row_index, row in enumerate(corpus_metadata):
        seed = row.get("seed")
        if not isinstance(seed, int) or isinstance(seed, bool):
            raise ValueError("conformal corpus seed is invalid")
        if seed in fit_seeds:
            partition_rows["fit"].append(row_index)
        elif seed in calibration_seeds:
            partition_rows["calibration"].append(row_index)
        else:
            raise ValueError("conformal corpus seed is outside registered partitions")
    result: dict[str, dict[str, Any]] = {}
    for name in ("fit", "calibration"):
        indices = torch.tensor(partition_rows[name], dtype=torch.long)
        if not indices.numel():
            raise ValueError(f"conformal {name} partition is empty")
        partition_tensors = {key: value[indices] for key, value in tensors.items()}
        partition_metadata = [corpus_metadata[int(index)] for index in indices]
        expanded = expand_action_relative_examples(
            partition_tensors,
            partition_metadata,
            action_dim=int(tensors["action_masks"].shape[1]),
        )
        support = _family_support(expanded["candidate_actions"])
        if any(value < minimum_family_support for value in support.values()):
            raise ValueError(f"conformal {name} action-family support is insufficient")
        result[name] = {
            "row_indices": indices,
            "row_sha256": _sha256_indices(indices),
            "row_count": int(indices.numel()),
            "pair_count": int(expanded["candidate_actions"].numel()),
            "family_support": support,
            "tensors": partition_tensors,
            "metadata": partition_metadata,
        }
    return result


def finite_sample_conformal_correction(
    nonconformity: torch.Tensor, *, alpha: float
) -> dict[str, Any]:
    values = nonconformity.detach().cpu().float().reshape(-1)
    if not values.numel() or not bool(torch.isfinite(values).all()):
        raise ValueError("conformal nonconformity values must be finite and non-empty")
    if not math.isfinite(float(alpha)) or not 0.0 < float(alpha) < 1.0:
        raise ValueError("conformal alpha differs")
    count = int(values.numel())
    rank = min(count, math.ceil((count + 1) * (1.0 - float(alpha))))
    raw = float(values.sort().values[rank - 1].item())
    correction = max(0.0, raw)
    return {
        "count": count,
        "rank": rank,
        "alpha": float(alpha),
        "raw_correction": raw,
        "correction": correction,
    }


def calibrate_action_families(
    *,
    candidate_actions: torch.Tensor,
    raw_scores: torch.Tensor,
    true_advantages: torch.Tensor,
    alpha: float,
    minimum_family_support: int,
) -> dict[str, Any]:
    actions = candidate_actions.detach().cpu().long().reshape(-1)
    raw = raw_scores.detach().cpu().float().reshape(-1)
    truth = true_advantages.detach().cpu().float().reshape(-1)
    if actions.shape != raw.shape or raw.shape != truth.shape:
        raise ValueError("conformal calibration tensor shapes differ")
    supported = (0 <= actions) & (actions < 90)
    excluded_unsupported_count = int((~supported).sum().item())
    actions = actions[supported]
    raw = raw[supported]
    truth = truth[supported]
    masks = {"card": actions.lt(60), "potion": actions.ge(60) & actions.lt(90)}
    details: dict[str, dict[str, Any]] = {}
    corrections: dict[str, float] = {}
    support: dict[str, int] = {}
    for family, mask in masks.items():
        count = int(mask.sum().item())
        if count < minimum_family_support:
            raise ValueError(f"conformal {family} calibration support is insufficient")
        detail = finite_sample_conformal_correction(raw[mask] - truth[mask], alpha=alpha)
        detail["empirical_coverage"] = float(
            truth[mask].ge(raw[mask] - float(detail["correction"])).float().mean().item()
        )
        details[family] = detail
        corrections[family] = float(detail["correction"])
        support[family] = count
    return {
        "corrections": corrections,
        "support": support,
        "families": details,
        "excluded_unsupported_count": excluded_unsupported_count,
    }


def _supported_corpus_metadata(
    corpus_metadata: Sequence[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    supported: list[dict[str, Any]] = []
    for row in corpus_metadata:
        guard = int(row["guard_action_index"])
        if not 0 <= guard < 90:
            raise ValueError("conformal guard action is outside supported families")
        branches = {
            str(action): value
            for raw_action, value in row["branch_returns"].items()
            if 0 <= (action := int(raw_action)) < 90
        }
        if str(guard) not in branches:
            raise ValueError("conformal supported branches omit the guard")
        normalized = dict(row)
        normalized["branch_returns"] = branches
        normalized["branch_count"] = len(branches)
        supported.append(normalized)
    return supported


def _score_raw_ensemble(
    ensemble: Any,
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
    expanded = expand_action_relative_examples(
        tensors, corpus_metadata, action_dim=ensemble.metadata["action_dim"]
    )
    scores: list[torch.Tensor] = []
    with torch.no_grad():
        for start in range(0, int(expanded["row_indices"].numel()), 512):
            stop = min(start + 512, int(expanded["row_indices"].numel()))
            row_indices = expanded["row_indices"][start:stop]
            stats = ensemble.score_candidate_statistics(
                **_batch_state_inputs(tensors, row_indices),
                candidate_actions=expanded["candidate_actions"][start:stop],
            )
            scores.append(stats.lower_confidence_scores.cpu())
    return (
        expanded["candidate_actions"].cpu(),
        torch.cat(scores),
        expanded["raw_advantages"].cpu(),
    )


def evaluate_conformal_corpus(
    gate: ActionRelativeConformalMarginGate,
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    *,
    forbidden_action_indices: Sequence[int],
    severe_harm_floor: float,
) -> dict[str, Any]:
    supported_metadata = _supported_corpus_metadata(corpus_metadata)
    metrics = evaluate_corpus(
        gate,
        tensors,
        supported_metadata,
        forbidden_action_indices=forbidden_action_indices,
    )
    expanded = expand_action_relative_examples(
        tensors, supported_metadata, action_dim=gate.metadata["action_dim"]
    )
    alternatives = _alternative_masks(tensors, supported_metadata)
    with torch.no_grad():
        selection = gate.select_actions(
            tensors["continuous"],
            tensors["card_ids"],
            tensors["potion_ids"],
            tensors["relic_ids"],
            tensors["action_masks"],
            tensors["guard_actions"],
            alternatives,
            forbidden_action_indices=frozenset(forbidden_action_indices),
        )
    true_matrix = torch.full(
        (len(corpus_metadata), gate.metadata["action_dim"]), float("-inf")
    )
    true_matrix[expanded["row_indices"], expanded["candidate_actions"]] = expanded[
        "raw_advantages"
    ]
    intervention_rows = selection.gate_open.cpu()
    selected_true = true_matrix[
        torch.arange(len(corpus_metadata))[intervention_rows],
        selection.actions.cpu()[intervention_rows],
    ]
    metrics["selection"]["severe_harm_floor"] = float(severe_harm_floor)
    metrics["selection"]["severe_harm_count"] = int(
        selected_true.lt(float(severe_harm_floor)).sum().item()
    )
    metrics["selection"]["minimum_intervention_true_advantage"] = (
        float(selected_true.min().item()) if selected_true.numel() else None
    )
    metrics["conformal"] = {
        "alpha": float(gate.config.alpha),
        "corrections": dict(gate.corrections),
    }
    return metrics


def apply_offline_gates(metrics: Mapping[str, Any]) -> dict[str, Any]:
    selection = metrics["selection"]
    ranking = metrics["ranking"]
    conditions = {
        "intervention_count_at_least_minimum": int(selection["intervention_count"])
        >= int(FIXED_OFFLINE_GATES["minimum_intervention_count"]),
        "intervention_precision_at_least_minimum": float(selection["intervention_precision"])
        >= float(FIXED_OFFLINE_GATES["minimum_intervention_precision"]),
        "mean_selected_true_advantage_above_baseline": float(
            selection["mean_selected_true_advantage"]
        )
        > float(FIXED_OFFLINE_GATES["minimum_mean_selected_true_advantage"]),
        "mean_policy_regret_below_baseline": float(ranking["mean_policy_regret"])
        < float(FIXED_OFFLINE_GATES["maximum_mean_policy_regret"]),
        "severe_harm_count_at_most_maximum": int(selection["severe_harm_count"])
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
        "schema_version",
        "experiment_id",
        "source_commit",
        "runner",
        "source_files",
        "inputs",
        "recipe",
        "offline_gates",
        "output_dir",
        "authority",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("conformal fit registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION or payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("conformal fit registration identity differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    source_files = payload["source_files"]
    if not isinstance(source_files, Mapping):
        raise ValueError("conformal source files are missing")
    normalized_sources: dict[str, str] = {}
    for raw_path, raw_hash in source_files.items():
        if not isinstance(raw_path, str):
            raise ValueError("conformal source path is invalid")
        path = Path(raw_path)
        if not raw_path or path.is_absolute() or ".." in path.parts:
            raise ValueError("conformal source path is invalid")
        normalized = raw_path.replace("\\", "/")
        digest = str(raw_hash).lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("conformal source hash is invalid")
        normalized_sources[normalized] = digest
    if set(normalized_sources) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("conformal source inventory differs")
    if Path(runner["path"]).resolve() != (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve():
        raise ValueError("conformal runner path differs")
    if runner["sha256"] != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("conformal runner hash differs")
    expected_inputs = {
        "items_json",
        "parent_checkpoint",
        "train_corpus",
        "evaluation_corpus",
        "baseline_fit_report",
        "uncertainty_fit_report",
        "error_audit",
    }
    inputs = payload["inputs"]
    if not isinstance(inputs, Mapping) or set(inputs) != expected_inputs:
        raise ValueError("conformal inputs differ")
    normalized_inputs = {
        name: _validate_file_binding(inputs[name], label=name) for name in sorted(expected_inputs)
    }
    if normalized_inputs["train_corpus"]["sha256"] == normalized_inputs[
        "evaluation_corpus"
    ]["sha256"]:
        raise ValueError("conformal corpus identities overlap")
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("conformal fixed recipe differs")
    if payload["offline_gates"] != FIXED_OFFLINE_GATES:
        raise ValueError("conformal offline gates differ")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("conformal authority differs")
    output = payload["output_dir"]
    if not isinstance(output, str) or not Path(output).is_absolute():
        raise ValueError("conformal output must be absolute")
    output_path = Path(output).resolve()
    try:
        output_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("conformal output is outside reports") from exc
    if output_path == REPORTS_ROOT.resolve():
        raise ValueError("conformal output cannot be reports root")
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
        raise ValueError("conformal source commit is not an ancestor of HEAD")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", registration["source_commit"], "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"conformal source changed after commit: {relative}")
    if path.read_bytes() != committed:
        raise ValueError("working conformal registration differs from committed data")
    return registration, hashlib.sha256(committed).hexdigest()


def _validated_execution_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"])
        if not path.is_absolute() or not path.is_file():
            raise ValueError(f"registered conformal {name} is unavailable")
        path = path.resolve()
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"registered conformal {name} hash differs")
        paths[name] = path
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("conformal output or staging already exists")
    paths["output_dir"] = output
    return paths


def _selection_exact(
    first: ActionRelativeConformalMarginGate,
    second: ActionRelativeConformalMarginGate,
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    forbidden: Sequence[int],
) -> bool:
    alternatives = _alternative_masks(tensors, corpus_metadata)
    arguments = (
        tensors["continuous"],
        tensors["card_ids"],
        tensors["potion_ids"],
        tensors["relic_ids"],
        tensors["action_masks"],
        tensors["guard_actions"],
        alternatives,
    )
    left = first.select_actions(*arguments, forbidden_action_indices=frozenset(forbidden))
    right = second.select_actions(*arguments, forbidden_action_indices=frozenset(forbidden))
    return all(
        torch.equal(getattr(left, field), getattr(right, field))
        for field in (
            "actions",
            "residual_actions",
            "predicted_advantages",
            "gate_open",
            "member_means",
            "member_standard_deviations",
            "raw_lower_scores",
            "family_corrections",
        )
    )


def _render_summary(report: Mapping[str, Any]) -> str:
    selection = report["evaluation"]["selection"]
    return (
        "# Action-Relative Conformal Margin Fit\n\n"
        f"- Card correction: {report['calibration']['corrections']['card']:.6f}\n"
        f"- Potion correction: {report['calibration']['corrections']['potion']:.6f}\n"
        f"- Holdout interventions: {selection['intervention_count']}\n"
        f"- Holdout precision: {selection['intervention_precision']:.6f}\n"
        f"- Severe harms: {selection['severe_harm_count']}\n"
        f"- Decision: {report['offline_gate']['decision']}\n"
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("conformal fit must use the registered interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("conformal fit must run in isolated mode")
    registration, registration_sha256 = load_committed_registration(registration_path)
    paths = _validated_execution_paths(registration)
    recipe = registration["recipe"]
    baseline = json.loads(paths["baseline_fit_report"].read_text(encoding="ascii"))
    baseline_selection = baseline.get("evaluation", {}).get("selection", {})
    baseline_ranking = baseline.get("evaluation", {}).get("ranking", {})
    if float(baseline_selection.get("mean_selected_true_advantage", float("nan"))) != float(
        FIXED_OFFLINE_GATES["minimum_mean_selected_true_advantage"]
    ) or float(baseline_ranking.get("mean_policy_regret", float("nan"))) != float(
        FIXED_OFFLINE_GATES["maximum_mean_policy_regret"]
    ):
        raise ValueError("conformal baseline holdout metrics differ")
    uncertainty = json.loads(paths["uncertainty_fit_report"].read_text(encoding="ascii"))
    if uncertainty.get("decision") != "offline_failed_close_without_fresh_gate_or_sweep":
        raise ValueError("conformal predecessor decision differs")

    id_mapper = build_id_mapper(paths["items_json"])
    initial_checkpoint = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    ensemble_recipe = recipe["ensemble_recipe"]
    trainer = create_fresh_trainer(
        id_mapper,
        seed=int(ensemble_recipe["member_seeds"][0]),
        batch_size=int(ensemble_recipe["batch_size"]),
        learning_starts=64,
    )
    parent_state, initialization = initialize_trainer(trainer, initial_checkpoint)
    parent = trainer.online_network
    parent.eval()
    metadata = _trainer_metadata(trainer)
    train = load_corpus(paths["train_corpus"], expected_partition="train")
    split = split_fit_calibration_corpus(
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
        minimum_family_support=int(recipe["minimum_family_support"]),
    )
    ensemble, fit = fit_ensemble(
        parent=parent,
        metadata=metadata,
        tensors=split["fit"]["tensors"],
        corpus_metadata=split["fit"]["metadata"],
        recipe=ensemble_recipe,
    )
    candidate_actions, raw_scores, true_advantages = _score_raw_ensemble(
        ensemble,
        split["calibration"]["tensors"],
        split["calibration"]["metadata"],
    )
    calibration = calibrate_action_families(
        candidate_actions=candidate_actions,
        raw_scores=raw_scores,
        true_advantages=true_advantages,
        alpha=float(recipe["calibration_alpha"]),
        minimum_family_support=int(recipe["minimum_family_support"]),
    )
    gate = ActionRelativeConformalMarginGate(
        ensemble,
        ActionRelativeConformalConfig(
            alpha=float(recipe["calibration_alpha"]),
            advantage_threshold=float(ensemble_recipe["advantage_threshold"]),
        ),
        corrections=calibration["corrections"],
    )

    evaluation = load_corpus(paths["evaluation_corpus"], expected_partition="evaluation")
    forbidden = recipe["forbidden_action_indices"]
    fit_metrics = evaluate_ensemble_corpus(
        ensemble,
        split["fit"]["tensors"],
        split["fit"]["metadata"],
        forbidden_action_indices=forbidden,
    )
    calibration_metrics = evaluate_conformal_corpus(
        gate,
        split["calibration"]["tensors"],
        split["calibration"]["metadata"],
        forbidden_action_indices=forbidden,
        severe_harm_floor=float(FIXED_OFFLINE_GATES["severe_harm_floor"]),
    )
    evaluation_metrics = evaluate_conformal_corpus(
        gate,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden_action_indices=forbidden,
        severe_harm_floor=float(FIXED_OFFLINE_GATES["severe_harm_floor"]),
    )
    offline_gate = apply_offline_gates(evaluation_metrics)
    corpus_hashes = {
        "train": registration["inputs"]["train_corpus"]["sha256"],
        "evaluation": registration["inputs"]["evaluation_corpus"]["sha256"],
    }
    ensemble_artifact = build_ensemble_development_artifact(
        ensemble,
        parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        corpus_sha256=corpus_hashes,
        recipe=ensemble_recipe,
        bootstrap_sha256=[sample.sha256 for sample in ensemble.bootstrap_samples],
        telemetry={"fit": fit, "fit_partition": fit_metrics},
    )
    split_hashes = {
        "fit": split["fit"]["row_sha256"],
        "calibration": split["calibration"]["row_sha256"],
    }
    artifact = build_conformal_development_artifact(
        gate,
        ensemble_artifact=ensemble_artifact,
        recipe=recipe,
        split_sha256=split_hashes,
        calibration_support=calibration["support"],
        telemetry={
            "fit": fit,
            "calibration": calibration,
            "calibration_partition": calibration_metrics,
            "evaluation": evaluation_metrics,
        },
    )
    restored = load_conformal_development_artifact(
        parent,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        expected_corpus_sha256=corpus_hashes,
        expected_recipe=recipe,
        expected_split_sha256=split_hashes,
    )
    if not _selection_exact(
        gate,
        restored,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden,
    ):
        raise RuntimeError("conformal artifact roundtrip changed holdout policy")
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
                if key not in {"tensors", "metadata", "row_indices"}
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
        artifact_path = staging / "action_relative_conformal_margin_development.pth"
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
