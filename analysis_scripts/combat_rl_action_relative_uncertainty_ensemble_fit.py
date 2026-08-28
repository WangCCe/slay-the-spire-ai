"""Fit one registered action-relative uncertainty ensemble on CPU."""

from __future__ import annotations

import argparse
import copy
from dataclasses import dataclass
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
from analysis_scripts.combat_rl_action_relative_advantage_residual_fit import (  # noqa: E402
    _alternative_masks,
    _batch_state_inputs,
    evaluate_corpus,
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
    expand_action_relative_examples,
    transformed_advantage_targets,
)
from spirecomm.ai.rl.v2.action_relative_uncertainty_ensemble import (  # noqa: E402
    ActionRelativeUncertaintyConfig,
    ActionRelativeUncertaintyEnsemble,
    build_ensemble_development_artifact,
    load_ensemble_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-action-relative-uncertainty-ensemble-fit-20260829-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_uncertainty_ensemble_fit.py",
    "analysis_scripts/combat_rl_action_relative_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "spirecomm/ai/rl/v2/action_relative_uncertainty_ensemble.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/network.py",
)

FIXED_RECIPE = {
    "architecture": "frozen_parent_action_relative_uncertainty_ensemble",
    "hidden_dim": 64,
    "member_count": 5,
    "member_seeds": [2026082901, 2026082902, 2026082903, 2026082904, 2026082905],
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

FIXED_OFFLINE_GATES = {
    "minimum_intervention_count": 30,
    "minimum_intervention_precision": 0.65,
    "minimum_mean_selected_true_advantage": 0.12269661575555801,
    "maximum_mean_policy_regret": 3.2472479343414307,
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
    "gameplay": False,
    "communication_mod": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}


@dataclass(frozen=True)
class BootstrapSample:
    indices: torch.Tensor
    sha256: str


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
        raise ValueError("uncertainty ensemble fit registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION or payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("uncertainty ensemble fit registration identity differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    source_files = payload["source_files"]
    if not isinstance(source_files, Mapping):
        raise ValueError("uncertainty ensemble source files are missing")
    normalized_sources: dict[str, str] = {}
    for raw_path, raw_hash in source_files.items():
        if not isinstance(raw_path, str):
            raise ValueError("uncertainty ensemble source path is invalid")
        path = Path(raw_path)
        if not raw_path or path.is_absolute() or ".." in path.parts:
            raise ValueError("uncertainty ensemble source path is invalid")
        normalized = raw_path.replace("\\", "/")
        digest = str(raw_hash).lower()
        if len(digest) != 64 or any(character not in "0123456789abcdef" for character in digest):
            raise ValueError("uncertainty ensemble source hash is invalid")
        normalized_sources[normalized] = digest
    if set(normalized_sources) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("uncertainty ensemble source inventory differs")
    if Path(runner["path"]).resolve() != (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve():
        raise ValueError("uncertainty ensemble runner path differs")
    if runner["sha256"] != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("uncertainty ensemble runner hash differs")
    expected_inputs = {
        "items_json",
        "parent_checkpoint",
        "train_corpus",
        "evaluation_corpus",
        "prior_fit_report",
    }
    inputs = payload["inputs"]
    if not isinstance(inputs, Mapping) or set(inputs) != expected_inputs:
        raise ValueError("uncertainty ensemble inputs differ")
    normalized_inputs = {
        name: _validate_file_binding(inputs[name], label=name) for name in sorted(expected_inputs)
    }
    if normalized_inputs["train_corpus"]["sha256"] == normalized_inputs[
        "evaluation_corpus"
    ]["sha256"]:
        raise ValueError("uncertainty ensemble corpus identities overlap")
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("uncertainty ensemble fixed recipe differs")
    if payload["offline_gates"] != FIXED_OFFLINE_GATES:
        raise ValueError("uncertainty ensemble offline gates differ")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("uncertainty ensemble authority differs")
    output = payload["output_dir"]
    if not isinstance(output, str) or not Path(output).is_absolute():
        raise ValueError("uncertainty ensemble output must be absolute")
    output_path = Path(output).resolve()
    try:
        output_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("uncertainty ensemble output is outside reports") from exc
    if output_path == REPORTS_ROOT.resolve():
        raise ValueError("uncertainty ensemble output cannot be reports root")
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
        raise ValueError("uncertainty ensemble source commit is not an ancestor of HEAD")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", registration["source_commit"], "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"uncertainty ensemble source changed after commit: {relative}")
    if path.read_bytes() != committed:
        raise ValueError("working uncertainty ensemble registration differs from committed data")
    return registration, hashlib.sha256(committed).hexdigest()


def _validated_execution_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"])
        if not path.is_absolute() or not path.is_file():
            raise ValueError(f"registered uncertainty ensemble {name} is unavailable")
        path = path.resolve()
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"registered uncertainty ensemble {name} hash differs")
        paths[name] = path
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("uncertainty ensemble output or staging already exists")
    paths["output_dir"] = output
    return paths


def _config(recipe: Mapping[str, Any]) -> ActionRelativeUncertaintyConfig:
    return ActionRelativeUncertaintyConfig(
        hidden_dim=int(recipe["hidden_dim"]),
        member_count=int(recipe["member_count"]),
        confidence_scale=float(recipe["confidence_scale"]),
        advantage_threshold=float(recipe["advantage_threshold"]),
        target_clip=float(recipe["target_clip"]),
        target_scale=float(recipe["target_scale"]),
    )


def deterministic_bootstrap_indices(
    pair_count: int, member_seeds: Sequence[int]
) -> tuple[BootstrapSample, ...]:
    if pair_count <= 0:
        raise ValueError("uncertainty ensemble bootstrap requires positive pair count")
    samples: list[BootstrapSample] = []
    for seed in member_seeds:
        generator = torch.Generator(device="cpu")
        generator.manual_seed(int(seed))
        indices = torch.randint(pair_count, (pair_count,), generator=generator)
        digest = hashlib.sha256(indices.numpy().tobytes()).hexdigest()
        samples.append(BootstrapSample(indices=indices, sha256=digest))
    if len({sample.sha256 for sample in samples}) != len(samples):
        raise RuntimeError("uncertainty ensemble bootstrap samples are not distinct")
    return tuple(samples)


def fit_ensemble(
    *,
    parent: torch.nn.Module,
    metadata: Mapping[str, Any],
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    recipe: Mapping[str, Any] = FIXED_RECIPE,
) -> tuple[ActionRelativeUncertaintyEnsemble, dict[str, Any]]:
    if set(recipe) != set(FIXED_RECIPE):
        raise ValueError("uncertainty ensemble fit recipe keys differ")
    ensemble = ActionRelativeUncertaintyEnsemble(
        parent,
        metadata,
        _config(recipe),
        member_seeds=recipe["member_seeds"],
    )
    expanded = expand_action_relative_examples(
        tensors, corpus_metadata, action_dim=int(metadata["action_dim"])
    )
    pair_count = int(expanded["row_indices"].numel())
    bootstraps = deterministic_bootstrap_indices(pair_count, recipe["member_seeds"])
    ensemble.bootstrap_samples = bootstraps
    parent_before = state_dict_sha256(ensemble.parent.state_dict())
    member_metrics: list[dict[str, Any]] = []
    ensemble.train()
    for member_index, (seed, bootstrap) in enumerate(zip(recipe["member_seeds"], bootstraps)):
        scorer = ensemble.member_scorers[member_index]
        optimizer = torch.optim.Adam(scorer.parameters(), lr=float(recipe["learning_rate"]))
        generator = torch.Generator(device="cpu")
        generator.manual_seed(int(seed) + 1000000)
        losses: list[float] = []
        for _ in range(int(recipe["updates"])):
            bootstrap_positions = torch.randint(
                pair_count,
                (int(recipe["batch_size"]),),
                generator=generator,
            )
            pair_indices = bootstrap.indices[bootstrap_positions]
            row_indices = expanded["row_indices"][pair_indices]
            candidates = expanded["candidate_actions"][pair_indices]
            predictions = ensemble.score_member_candidates(
                member_index,
                **_batch_state_inputs(tensors, row_indices),
                candidate_actions=candidates,
            )
            targets = transformed_advantage_targets(
                expanded["raw_advantages"][pair_indices], ensemble.config
            )
            loss = F.smooth_l1_loss(
                predictions / float(ensemble.config.target_scale),
                targets,
                beta=float(recipe["smooth_l1_beta"]),
            )
            if not bool(torch.isfinite(loss)):
                raise RuntimeError("uncertainty ensemble objective became non-finite")
            optimizer.zero_grad(set_to_none=True)
            loss.backward()
            if any(parameter.grad is not None for parameter in ensemble.parent.parameters()):
                raise RuntimeError("uncertainty ensemble produced parent gradients")
            optimizer.step()
            losses.append(float(loss.detach()))
        member_metrics.append(
            {
                "member_index": member_index,
                "member_seed": int(seed),
                "bootstrap_sha256": bootstrap.sha256,
                "update_count": int(recipe["updates"]),
                "batch_size": int(recipe["batch_size"]),
                "all_objectives_finite": all(math.isfinite(value) for value in losses),
                "loss": _loss_summary(losses),
                "scorer_state_dict_sha256": state_dict_sha256(scorer.state_dict()),
            }
        )
    ensemble.eval()
    parent_after = state_dict_sha256(ensemble.parent.state_dict())
    if parent_before != parent_after:
        raise RuntimeError("uncertainty ensemble changed the frozen parent")
    return ensemble, {
        "alternative_count": pair_count,
        "member_count": len(member_metrics),
        "members": member_metrics,
        "parent_state_dict_sha256_before": parent_before,
        "parent_state_dict_sha256_after": parent_after,
        "parent_frozen": True,
    }


def evaluate_ensemble_corpus(
    ensemble: ActionRelativeUncertaintyEnsemble,
    tensors: Mapping[str, torch.Tensor],
    corpus_metadata: Sequence[Mapping[str, Any]],
    *,
    forbidden_action_indices: Sequence[int],
) -> dict[str, Any]:
    metrics = evaluate_corpus(
        ensemble,
        tensors,
        corpus_metadata,
        forbidden_action_indices=forbidden_action_indices,
    )
    expanded = expand_action_relative_examples(
        tensors, corpus_metadata, action_dim=ensemble.metadata["action_dim"]
    )
    means: list[torch.Tensor] = []
    stds: list[torch.Tensor] = []
    lowers: list[torch.Tensor] = []
    with torch.no_grad():
        for start in range(0, int(expanded["row_indices"].numel()), 512):
            stop = min(start + 512, int(expanded["row_indices"].numel()))
            rows = expanded["row_indices"][start:stop]
            stats = ensemble.score_candidate_statistics(
                **_batch_state_inputs(tensors, rows),
                candidate_actions=expanded["candidate_actions"][start:stop],
            )
            means.append(stats.means.cpu())
            stds.append(stats.standard_deviations.cpu())
            lowers.append(stats.lower_confidence_scores.cpu())
    all_means = torch.cat(means)
    all_stds = torch.cat(stds)
    all_lowers = torch.cat(lowers)
    metrics["uncertainty"] = {
        "mean_member_prediction": float(all_means.mean().item()),
        "mean_sample_standard_deviation": float(all_stds.mean().item()),
        "maximum_sample_standard_deviation": float(all_stds.max().item()),
        "mean_lower_confidence_score": float(all_lowers.mean().item()),
        "all_statistics_finite": bool(
            torch.isfinite(all_means).all()
            and torch.isfinite(all_stds).all()
            and torch.isfinite(all_lowers).all()
        ),
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
        "mean_selected_true_advantage_above_prior": float(
            selection["mean_selected_true_advantage"]
        )
        > float(FIXED_OFFLINE_GATES["minimum_mean_selected_true_advantage"]),
        "mean_policy_regret_below_prior": float(ranking["mean_policy_regret"])
        < float(FIXED_OFFLINE_GATES["maximum_mean_policy_regret"]),
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


def _selection_exact(
    first: ActionRelativeUncertaintyEnsemble,
    second: ActionRelativeUncertaintyEnsemble,
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
        )
    )


def _render_summary(report: Mapping[str, Any]) -> str:
    selection = report["evaluation"]["selection"]
    ranking = report["evaluation"]["ranking"]
    return (
        "# Action-Relative Uncertainty Ensemble Fit\n\n"
        f"- Members: {report['fit']['member_count']}\n"
        f"- Evaluation interventions: {selection['intervention_count']}\n"
        f"- Intervention precision: {selection['intervention_precision']:.6f}\n"
        f"- Mean selected true advantage: {selection['mean_selected_true_advantage']:.6f}\n"
        f"- Mean policy regret: {ranking['mean_policy_regret']:.6f}\n"
        f"- Decision: {report['offline_gate']['decision']}\n"
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("uncertainty ensemble fit must use the registered interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("uncertainty ensemble fit must run in isolated mode")
    registration, registration_sha256 = load_committed_registration(registration_path)
    paths = _validated_execution_paths(registration)
    recipe = registration["recipe"]
    prior = json.loads(paths["prior_fit_report"].read_text(encoding="ascii"))
    prior_selection = prior.get("evaluation", {}).get("selection", {})
    prior_ranking = prior.get("evaluation", {}).get("ranking", {})
    if float(prior_selection.get("mean_selected_true_advantage", float("nan"))) != float(
        FIXED_OFFLINE_GATES["minimum_mean_selected_true_advantage"]
    ) or float(prior_ranking.get("mean_policy_regret", float("nan"))) != float(
        FIXED_OFFLINE_GATES["maximum_mean_policy_regret"]
    ):
        raise ValueError("uncertainty ensemble prior holdout baseline differs")
    id_mapper = build_id_mapper(paths["items_json"])
    initial_checkpoint = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        id_mapper,
        seed=int(recipe["member_seeds"][0]),
        batch_size=int(recipe["batch_size"]),
        learning_starts=64,
    )
    parent_state, initialization = initialize_trainer(trainer, initial_checkpoint)
    parent = trainer.online_network
    parent.eval()
    metadata = _trainer_metadata(trainer)
    train = load_corpus(paths["train_corpus"], expected_partition="train")
    for name, expected in (
        ("continuous", metadata["continuous_dim"]),
        ("card_ids", metadata["card_slots"]),
        ("potion_ids", metadata["potion_slots"]),
        ("relic_ids", metadata["relic_slots"]),
        ("action_masks", metadata["action_dim"]),
    ):
        if train["tensors"][name].shape[1] != expected:
            raise ValueError(f"uncertainty ensemble train corpus {name} width differs")
    ensemble, fit = fit_ensemble(
        parent=parent,
        metadata=metadata,
        tensors=train["tensors"],
        corpus_metadata=train["metadata"],
        recipe=recipe,
    )
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
        if evaluation["tensors"][name].shape[1] != expected:
            raise ValueError(
                f"uncertainty ensemble evaluation corpus {name} width differs"
            )
    forbidden = recipe["forbidden_action_indices"]
    train_metrics = evaluate_ensemble_corpus(
        ensemble,
        train["tensors"],
        train["metadata"],
        forbidden_action_indices=forbidden,
    )
    evaluation_metrics = evaluate_ensemble_corpus(
        ensemble,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden_action_indices=forbidden,
    )
    offline_gate = apply_offline_gates(evaluation_metrics)
    corpus_hashes = {
        "train": registration["inputs"]["train_corpus"]["sha256"],
        "evaluation": registration["inputs"]["evaluation_corpus"]["sha256"],
    }
    artifact = build_ensemble_development_artifact(
        ensemble,
        parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        corpus_sha256=corpus_hashes,
        recipe=recipe,
        bootstrap_sha256=[sample.sha256 for sample in ensemble.bootstrap_samples],
        telemetry={"fit": fit, "train": train_metrics, "evaluation": evaluation_metrics},
    )
    restored = load_ensemble_development_artifact(
        parent,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        expected_corpus_sha256=corpus_hashes,
        expected_recipe=recipe,
    )
    if not _selection_exact(
        ensemble,
        restored,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden,
    ):
        raise RuntimeError("uncertainty ensemble artifact roundtrip changed holdout policy")
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
        "corpus": {
            "train_rows": train["row_count"],
            "evaluation_rows": evaluation["row_count"],
            "train_alternatives": fit["alternative_count"],
            "evaluation_alternatives": evaluation_metrics["alternative_count"],
            "evaluation_access_after_fit": True,
            "seed_disjoint": True,
        },
        "fit": fit,
        "train": train_metrics,
        "evaluation": evaluation_metrics,
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
        artifact_path = staging / "action_relative_uncertainty_ensemble_development.pth"
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
