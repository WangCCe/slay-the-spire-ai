"""Fit one registered action-relative post-guard residual on CPU."""

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
    _loss_summary,
    _trainer_metadata,
    _validate_commit,
    _validate_file_binding,
    load_corpus,
    sha256_file,
)
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (  # noqa: E402
    ActionRelativeAdvantageConfig,
    ActionRelativeAdvantageResidual,
    build_development_artifact,
    expand_action_relative_examples,
    load_development_artifact,
    transformed_advantage_targets,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-action-relative-advantage-residual-fit-20260828-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_corpus.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/network.py",
)

FIXED_RECIPE = {
    "architecture": "frozen_parent_action_relative_advantage_residual",
    "hidden_dim": 64,
    "advantage_threshold": 0.5,
    "target_clip": 20.0,
    "target_scale": 10.0,
    "optimizer": "adam",
    "learning_rate": 0.001,
    "updates": 1024,
    "batch_size": 256,
    "smooth_l1_beta": 0.1,
    "training_seed": 2026082823,
    "device": "cpu",
    "forbidden_action_indices": [90],
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
    "gameplay": False,
    "communication_mod": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
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
        "output_dir",
        "authority",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("action-relative fit registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("action-relative fit registration schema differs")
    if payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("action-relative fit experiment id differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    source_files = payload["source_files"]
    if not isinstance(source_files, Mapping):
        raise ValueError("action-relative fit source files are missing")
    normalized_sources: dict[str, str] = {}
    for raw_path, raw_sha256 in source_files.items():
        if not isinstance(raw_path, str):
            raise ValueError("action-relative fit source path is invalid")
        path = Path(raw_path)
        if not raw_path or path.is_absolute() or ".." in path.parts:
            raise ValueError("action-relative fit source path is invalid")
        normalized_sources[raw_path.replace("\\", "/")] = str(raw_sha256).lower()
        if len(normalized_sources[raw_path.replace("\\", "/")]) != 64 or any(
            character not in "0123456789abcdef"
            for character in normalized_sources[raw_path.replace("\\", "/")]
        ):
            raise ValueError("action-relative fit source hash is invalid")
    if set(normalized_sources) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("action-relative fit source inventory differs")
    expected_runner = (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve()
    if Path(runner["path"]).resolve() != expected_runner:
        raise ValueError("action-relative fit runner path differs")
    if runner["sha256"] != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("action-relative fit runner hash differs from source inventory")

    inputs = payload["inputs"]
    expected_inputs = {
        "items_json",
        "parent_checkpoint",
        "train_corpus",
        "evaluation_corpus",
    }
    if not isinstance(inputs, Mapping) or set(inputs) != expected_inputs:
        raise ValueError("action-relative fit inputs differ")
    normalized_inputs = {
        name: _validate_file_binding(inputs[name], label=name)
        for name in sorted(expected_inputs)
    }
    if normalized_inputs["train_corpus"]["sha256"] == normalized_inputs[
        "evaluation_corpus"
    ]["sha256"]:
        raise ValueError("action-relative fit corpus identities overlap")
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("action-relative fit fixed recipe differs")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("action-relative fit authority differs")
    output_dir = payload["output_dir"]
    if not isinstance(output_dir, str) or not Path(output_dir).is_absolute():
        raise ValueError("action-relative fit output path must be absolute")
    output_path = Path(output_dir).resolve()
    try:
        output_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("action-relative fit output path is outside reports") from exc
    if output_path == REPORTS_ROOT.resolve():
        raise ValueError("action-relative fit output path cannot be reports root")
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "runner": runner,
        "source_files": normalized_sources,
        "inputs": normalized_inputs,
        "recipe": copy.deepcopy(FIXED_RECIPE),
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
        raise ValueError("registered source commit is not an ancestor of HEAD")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", registration["source_commit"], "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"registered source changed after commit: {relative}")
    if path.read_bytes() != committed:
        raise ValueError("working registration differs from committed registration")
    return registration, hashlib.sha256(committed).hexdigest()


def _validated_execution_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"])
        if not path.is_absolute() or not path.is_file():
            raise ValueError(f"registered {name} path is unavailable")
        path = path.resolve()
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"registered {name} hash differs")
        paths[name] = path
    output_dir = Path(registration["output_dir"]).resolve()
    staging_dir = output_dir.with_name(f".{output_dir.name}.staging")
    if output_dir.exists() or staging_dir.exists():
        raise ValueError("action-relative fit output or staging directory already exists")
    paths["output_dir"] = output_dir
    return paths


def _config(recipe: Mapping[str, Any]) -> ActionRelativeAdvantageConfig:
    return ActionRelativeAdvantageConfig(
        hidden_dim=int(recipe["hidden_dim"]),
        advantage_threshold=float(recipe["advantage_threshold"]),
        target_clip=float(recipe["target_clip"]),
        target_scale=float(recipe["target_scale"]),
    )


def _batch_state_inputs(
    tensors: Mapping[str, torch.Tensor], row_indices: torch.Tensor
) -> dict[str, torch.Tensor]:
    return {
        name: tensors[name][row_indices]
        for name in (
            "continuous",
            "card_ids",
            "potion_ids",
            "relic_ids",
            "action_masks",
            "guard_actions",
        )
    }


def fit_residual(
    *,
    parent: torch.nn.Module,
    metadata: Mapping[str, Any],
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    recipe: Mapping[str, Any] = FIXED_RECIPE,
) -> tuple[ActionRelativeAdvantageResidual, dict[str, Any]]:
    if set(recipe) != set(FIXED_RECIPE):
        raise ValueError("action-relative fit recipe keys differ")
    torch.manual_seed(int(recipe["training_seed"]))
    residual = ActionRelativeAdvantageResidual(parent, metadata, _config(recipe))
    expanded = expand_action_relative_examples(
        tensors, corpus_metadata, action_dim=int(metadata["action_dim"])
    )
    pair_count = int(expanded["row_indices"].numel())
    if pair_count == 0:
        raise ValueError("action-relative fit requires alternatives")
    optimizer = torch.optim.Adam(
        residual.scorer.parameters(), lr=float(recipe["learning_rate"])
    )
    generator = torch.Generator(device="cpu")
    generator.manual_seed(int(recipe["training_seed"]))
    losses: list[float] = []
    parent_before = state_dict_sha256(residual.parent.state_dict())
    residual.train()
    for _ in range(int(recipe["updates"])):
        pair_indices = torch.randint(
            pair_count,
            (int(recipe["batch_size"]),),
            generator=generator,
        )
        row_indices = expanded["row_indices"][pair_indices]
        candidates = expanded["candidate_actions"][pair_indices]
        state_inputs = _batch_state_inputs(tensors, row_indices)
        predictions = residual.score_candidates(**state_inputs, candidate_actions=candidates)
        targets = transformed_advantage_targets(
            expanded["raw_advantages"][pair_indices], residual.config
        )
        loss = F.smooth_l1_loss(
            predictions / float(residual.config.target_scale),
            targets,
            beta=float(recipe["smooth_l1_beta"]),
        )
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("action-relative fit objective became non-finite")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        if any(parameter.grad is not None for parameter in residual.parent.parameters()):
            raise RuntimeError("action-relative fit produced parent gradients")
        optimizer.step()
        losses.append(float(loss.detach()))
    residual.eval()
    parent_after = state_dict_sha256(residual.parent.state_dict())
    if parent_after != parent_before:
        raise RuntimeError("action-relative fit changed the frozen parent")
    return residual, {
        "update_count": int(recipe["updates"]),
        "batch_size": int(recipe["batch_size"]),
        "alternative_count": pair_count,
        "all_objectives_finite": all(math.isfinite(value) for value in losses),
        "loss": _loss_summary(losses),
        "parent_state_dict_sha256_before": parent_before,
        "parent_state_dict_sha256_after": parent_after,
        "parent_frozen": parent_before == parent_after,
        "scorer_state_dict_sha256": state_dict_sha256(residual.scorer.state_dict()),
    }


def _alternative_masks(
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
) -> torch.Tensor:
    action_masks = tensors["action_masks"].bool()
    guards = tensors["guard_actions"].long().reshape(-1)
    result = torch.zeros_like(action_masks)
    for row_index, row in enumerate(corpus_metadata):
        branches = row.get("branch_returns")
        if not isinstance(branches, Mapping):
            raise ValueError("action-relative branch identities are missing")
        for raw_action in branches:
            action = int(raw_action)
            if action != int(guards[row_index]):
                result[row_index, action] = True
    if bool((result & ~action_masks).any()):
        raise ValueError("action-relative alternatives contain illegal actions")
    return result


def _score_expanded(
    residual: ActionRelativeAdvantageResidual,
    tensors: Mapping[str, torch.Tensor],
    expanded: Mapping[str, torch.Tensor],
    *,
    chunk_size: int = 512,
) -> torch.Tensor:
    predictions: list[torch.Tensor] = []
    pair_count = int(expanded["row_indices"].numel())
    with torch.no_grad():
        for start in range(0, pair_count, chunk_size):
            stop = min(start + chunk_size, pair_count)
            pair_slice = slice(start, stop)
            row_indices = expanded["row_indices"][pair_slice]
            state_inputs = _batch_state_inputs(tensors, row_indices)
            predictions.append(
                residual.score_candidates(
                    **state_inputs,
                    candidate_actions=expanded["candidate_actions"][pair_slice],
                ).cpu()
            )
    return torch.cat(predictions)


def evaluate_corpus(
    residual: ActionRelativeAdvantageResidual,
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    *,
    forbidden_action_indices: Sequence[int],
) -> dict[str, Any]:
    expanded = expand_action_relative_examples(
        tensors, corpus_metadata, action_dim=residual.metadata["action_dim"]
    )
    predictions = _score_expanded(residual, tensors, expanded)
    truth = expanded["raw_advantages"].cpu()
    errors = predictions - truth
    true_positive = truth.ge(float(residual.config.advantage_threshold))
    predicted_positive = predictions.ge(float(residual.config.advantage_threshold))
    sign_accuracy = predicted_positive.eq(true_positive).float().mean()

    alternatives = _alternative_masks(tensors, corpus_metadata)
    valid_forbidden = frozenset(
        int(action)
        for action in forbidden_action_indices
        if 0 <= int(action) < residual.metadata["action_dim"]
    )
    started = time.perf_counter()
    with torch.no_grad():
        selection = residual.select_actions(
            tensors["continuous"],
            tensors["card_ids"],
            tensors["potion_ids"],
            tensors["relic_ids"],
            tensors["action_masks"],
            tensors["guard_actions"],
            alternatives,
            forbidden_action_indices=valid_forbidden,
        )
    latency_ms = (time.perf_counter() - started) * 1000.0
    row_count = int(tensors["guard_actions"].numel())
    action_dim = residual.metadata["action_dim"]
    true_matrix = torch.full((row_count, action_dim), float("-inf"))
    true_matrix[
        expanded["row_indices"].cpu(), expanded["candidate_actions"].cpu()
    ] = truth
    allowed = alternatives.clone()
    for action in valid_forbidden:
        allowed[:, action] = False
    selected_true = torch.zeros(row_count)
    intervention_rows = selection.actions.ne(selection.guard_actions).cpu()
    selected_true[intervention_rows] = true_matrix[
        torch.arange(row_count)[intervention_rows],
        selection.actions.cpu()[intervention_rows],
    ]
    allowed_true = true_matrix.masked_fill(~allowed.cpu(), float("-inf"))
    has_allowed = allowed.any(dim=1).cpu()
    best_allowed_true = torch.zeros(row_count)
    if bool(has_allowed.any()):
        best_allowed_true[has_allowed] = allowed_true[has_allowed].max(dim=1).values
    best_with_guard = torch.maximum(best_allowed_true, torch.zeros_like(best_allowed_true))
    residual_true = torch.zeros(row_count)
    residual_true[has_allowed] = true_matrix[
        torch.arange(row_count)[has_allowed],
        selection.residual_actions.cpu()[has_allowed],
    ]
    top_action_correct = torch.isclose(
        residual_true[has_allowed], best_allowed_true[has_allowed], atol=1e-6, rtol=0.0
    )
    legal_rows = torch.arange(row_count)
    illegal_action_count = int(
        (~tensors["action_masks"][legal_rows, selection.actions.cpu()]).sum().item()
    )
    intervention_count = int(intervention_rows.sum().item())
    intervention_precision = (
        float(
            selected_true[intervention_rows]
            .ge(float(residual.config.advantage_threshold))
            .float()
            .mean()
            .item()
        )
        if intervention_count
        else 0.0
    )
    action_support: dict[str, dict[str, float | int]] = {}
    for action in sorted(set(expanded["candidate_actions"].tolist())):
        mask = expanded["candidate_actions"].cpu().eq(action)
        action_errors = errors[mask]
        action_support[str(action)] = {
            "count": int(mask.sum().item()),
            "mean_absolute_error": float(action_errors.abs().mean().item()),
            "mean_true_advantage": float(truth[mask].mean().item()),
            "mean_predicted_advantage": float(predictions[mask].mean().item()),
        }
    mean_selected = float(selected_true.mean().item())
    conditions = {
        "intervention_count_positive": intervention_count > 0,
        "mean_selected_true_advantage_non_negative": mean_selected >= 0.0,
        "illegal_action_count_zero": illegal_action_count == 0,
        "forbidden_action_selection_count_zero": selection.telemetry[
            "forbidden_action_selection_count"
        ]
        == 0,
    }
    return {
        "row_count": row_count,
        "alternative_count": int(truth.numel()),
        "regression": {
            "mean_absolute_error": float(errors.abs().mean().item()),
            "root_mean_squared_error": float(errors.square().mean().sqrt().item()),
            "mean_error": float(errors.mean().item()),
            "threshold_sign_accuracy": float(sign_accuracy.item()),
        },
        "ranking": {
            "best_allowed_action_accuracy": float(top_action_correct.float().mean().item())
            if bool(has_allowed.any())
            else 0.0,
            "mean_policy_regret": float((best_with_guard - selected_true).mean().item()),
        },
        "selection": {
            "intervention_count": intervention_count,
            "intervention_share": intervention_count / max(row_count, 1),
            "intervention_precision": intervention_precision,
            "mean_selected_true_advantage": mean_selected,
            "mean_intervention_true_advantage": float(
                selected_true[intervention_rows].mean().item()
            )
            if intervention_count
            else 0.0,
            "illegal_action_count": illegal_action_count,
            "forbidden_action_selection_count": selection.telemetry[
                "forbidden_action_selection_count"
            ],
            "no_allowed_alternative_count": selection.telemetry[
                "no_allowed_alternative_count"
            ],
        },
        "action_support": action_support,
        "latency": {
            "total_ms": latency_ms,
            "mean_ms_per_state": latency_ms / max(row_count, 1),
        },
        "offline_integrity_conditions": conditions,
        "all_offline_integrity_conditions_passed": all(conditions.values()),
    }


def _selection_exact(
    first: ActionRelativeAdvantageResidual,
    second: ActionRelativeAdvantageResidual,
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    forbidden_action_indices: Sequence[int],
) -> bool:
    expanded = expand_action_relative_examples(
        tensors, corpus_metadata, action_dim=first.metadata["action_dim"]
    )
    first_predictions = _score_expanded(first, tensors, expanded)
    second_predictions = _score_expanded(second, tensors, expanded)
    alternatives = _alternative_masks(tensors, corpus_metadata)
    valid_forbidden = frozenset(
        int(action)
        for action in forbidden_action_indices
        if 0 <= int(action) < first.metadata["action_dim"]
    )
    with torch.no_grad():
        first_selection = first.select_actions(
            tensors["continuous"], tensors["card_ids"], tensors["potion_ids"],
            tensors["relic_ids"], tensors["action_masks"], tensors["guard_actions"],
            alternatives, forbidden_action_indices=valid_forbidden,
        )
        second_selection = second.select_actions(
            tensors["continuous"], tensors["card_ids"], tensors["potion_ids"],
            tensors["relic_ids"], tensors["action_masks"], tensors["guard_actions"],
            alternatives, forbidden_action_indices=valid_forbidden,
        )
    return bool(
        torch.equal(first_predictions, second_predictions)
        and torch.equal(first_selection.actions, second_selection.actions)
        and torch.equal(
            first_selection.predicted_advantages,
            second_selection.predicted_advantages,
        )
    )


def _render_summary(report: Mapping[str, Any]) -> str:
    evaluation = report["evaluation"]
    selection = evaluation["selection"]
    return "\n".join(
        (
            "# Action-Relative Advantage Residual Fit",
            "",
            f"- Train alternatives: {report['corpus']['train_alternatives']}",
            f"- Evaluation alternatives: {evaluation['alternative_count']}",
            f"- Evaluation MAE: {evaluation['regression']['mean_absolute_error']:.6f}",
            f"- Best-action accuracy: {evaluation['ranking']['best_allowed_action_accuracy']:.6f}",
            f"- Interventions: {selection['intervention_count']}",
            f"- Mean selected true advantage: {selection['mean_selected_true_advantage']:.6f}",
            f"- Intervention precision: {selection['intervention_precision']:.6f}",
            f"- Offline integrity passed: {str(evaluation['all_offline_integrity_conditions_passed']).lower()}",
            f"- Decision: {report['decision']}",
            "",
        )
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("action-relative fit must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("action-relative fit must run in isolated -I mode")
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
        seed=int(recipe["training_seed"]),
        batch_size=int(recipe["batch_size"]),
        learning_starts=64,
    )
    parent_state, initialization = initialize_trainer(trainer, initial_checkpoint)
    parent = trainer.online_network
    parent.eval()
    metadata = _trainer_metadata(trainer)
    train = load_corpus(paths["train_corpus"], expected_partition="train")
    evaluation = load_corpus(
        paths["evaluation_corpus"], expected_partition="evaluation"
    )
    for name, expected in (
        ("continuous", metadata["continuous_dim"]),
        ("card_ids", metadata["card_slots"]),
        ("potion_ids", metadata["potion_slots"]),
        ("relic_ids", metadata["relic_slots"]),
        ("action_masks", metadata["action_dim"]),
    ):
        if train["tensors"][name].shape[1] != expected or evaluation["tensors"][name].shape[1] != expected:
            raise ValueError(f"action-relative corpus {name} width differs from parent")
    residual, fit = fit_residual(
        parent=parent,
        metadata=metadata,
        tensors=train["tensors"],
        corpus_metadata=train["metadata"],
        recipe=recipe,
    )
    forbidden = recipe["forbidden_action_indices"]
    train_metrics = evaluate_corpus(
        residual,
        train["tensors"],
        train["metadata"],
        forbidden_action_indices=forbidden,
    )
    evaluation_metrics = evaluate_corpus(
        residual,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden_action_indices=forbidden,
    )
    corpus_hashes = {
        "train": registration["inputs"]["train_corpus"]["sha256"],
        "evaluation": registration["inputs"]["evaluation_corpus"]["sha256"],
    }
    artifact = build_development_artifact(
        residual,
        parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        corpus_sha256=corpus_hashes,
        recipe=recipe,
        telemetry={"fit": fit, "train": train_metrics, "evaluation": evaluation_metrics},
    )
    restored = load_development_artifact(
        parent,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        expected_corpus_sha256=corpus_hashes,
        expected_recipe=recipe,
    )
    if not _selection_exact(
        residual,
        restored,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden,
    ):
        raise RuntimeError("action-relative artifact roundtrip changed held-out policy")
    decision = (
        "offline_integrity_passed_enter_fresh_gate"
        if evaluation_metrics["all_offline_integrity_conditions_passed"]
        else "offline_integrity_failed_close_without_fresh_gate"
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "execution_commit": _current_commit(),
        "registration_sha256": registration_sha256,
        "recipe": copy.deepcopy(recipe),
        "inputs": copy.deepcopy(registration["inputs"]),
        "initialization": initialization,
        "parent_parameter_sha256": parameter_sha256(parent_state),
        "corpus": {
            "train_rows": train["row_count"],
            "evaluation_rows": evaluation["row_count"],
            "train_alternatives": fit["alternative_count"],
            "evaluation_alternatives": evaluation_metrics["alternative_count"],
            "seed_disjoint": True,
        },
        "fit": fit,
        "train": train_metrics,
        "evaluation": evaluation_metrics,
        "artifact_roundtrip_exact": True,
        "threshold_tuned": False,
        "decision": decision,
        "output_dir": str(paths["output_dir"]),
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }
    output_dir = paths["output_dir"]
    staging_dir = output_dir.with_name(f".{output_dir.name}.staging")
    staging_dir.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = staging_dir / "action_relative_advantage_residual_development.pth"
        torch.save(artifact, artifact_path)
        report["artifact"] = {
            "path": artifact_path.name,
            "sha256": sha256_file(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
            "production_compatible": False,
        }
        (staging_dir / "report.json").write_bytes(_canonical_json_bytes(report))
        (staging_dir / "summary.md").write_text(
            _render_summary(report), encoding="ascii", newline="\n"
        )
        os.replace(staging_dir, output_dir)
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    report = run(args.registration)
    print(json.dumps({
        "decision": report["decision"],
        "output_dir": report["output_dir"],
        "evaluation": report["evaluation"]["selection"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
