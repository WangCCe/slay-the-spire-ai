"""Fit one source-bound development latent-gated combat correction candidate."""

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

import numpy as np
import torch
import torch.nn as nn


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_latent_gated_candidate_fit.py",
    "analysis_scripts/combat_lightspeed_bridge.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "analysis_scripts/combat_rl_candidate_callability_successor.py",
    "analysis_scripts/combat_rl_lightspeed_guard_transfer_poc.py",
    "analysis_scripts/combat_rl_dropout_update_ablation.py",
    "analysis_scripts/combat_rl_inventory_embedding_successor.py",
    "analysis_scripts/combat_rl_provenance_aware_successor.py",
    "spirecomm/ai/rl/v2/action_space.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/latent_gated_adapter.py",
    "spirecomm/ai/rl/v2/network.py",
    "spirecomm/ai/rl/v2/replay_buffer.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
    "spirecomm/ai/rl/v2/trainer.py",
)
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
from analysis_scripts.combat_rl_lightspeed_guard_transfer_poc import (  # noqa: E402
    classifier_scores,
    fit_action_classifier,
    fit_classifier,
    gated_action_metrics,
    parent_feature_views,
    threshold_at_direct_open_cap,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import (  # noqa: E402
    LatentGateConfig,
    LatentGatedActionAdapter,
    build_development_artifact,
    load_development_artifact,
    state_dict_sha256,
)


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-latent-gated-candidate-fit-20260828-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
GAMMA = 0.99

FIXED_RECIPE = {
    "architecture": "frozen_parent_latent_gated_legal_action_correction",
    "hidden_dim": 64,
    "simulator_seed_first": 185000,
    "simulator_seed_last": 185255,
    "battle_indices": [0, 3, 6, 9],
    "simulator_training_seed": 2026082814,
    "classifier_seed": 2026082816,
    "simulator_updates": 128,
    "development_gate_updates": 128,
    "action_updates": 256,
    "batch_size": 64,
    "learning_rate": 0.001,
    "direct_open_calibration_cap": 0.10,
    "simulator_validation_stride": 5,
    "device": "cpu",
}

FIXED_TECHNICAL_GATES = {
    "direct_gate_open_share_maximum": 0.15,
    "changed_gate_open_share_minimum": 0.75,
    "direct_candidate_agreement_minimum": 0.85,
    "changed_correction_agreement_minimum": 0.35,
    "changed_candidate_agreement_minimum": 0.25,
    "overall_candidate_agreement_uplift_minimum": 0.10,
    "positive_energy_end_turn_increase_maximum": 0,
}

REGISTERED_AUTHORITY = {
    "cpu_development_fit": True,
    "native_loading": True,
    "gameplay": False,
    "communication_mod": False,
    "online_training": False,
    "production_checkpoint_loading": False,
    "qualification": False,
    "promotion": False,
}

RESULT_AUTHORITY = {
    "development_candidate": True,
    "gameplay": False,
    "communication_mod": False,
    "online_training": False,
    "production_checkpoint_loading": False,
    "qualification": False,
    "promotion": False,
}


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ).encode("ascii") + b"\n"


def _validate_sha256(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} SHA-256 is missing")
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{label} SHA-256 is invalid")
    return normalized


def _validate_commit(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value.lower()
    ):
        raise ValueError("source commit is invalid")
    return value.lower()


def _validate_file_binding(
    value: Any,
    *,
    label: str,
    transition_count: bool = False,
    identity: bool = False,
) -> dict[str, Any]:
    required = {"path", "sha256"}
    if transition_count:
        required.add("transition_count")
    if identity:
        required.add("id")
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError(f"{label} binding keys differ")
    path = value["path"]
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"{label} path is invalid")
    normalized = {"path": path, "sha256": _validate_sha256(value["sha256"], label)}
    if transition_count:
        count = value["transition_count"]
        if not isinstance(count, int) or isinstance(count, bool) or count <= 0:
            raise ValueError(f"{label} transition count is invalid")
        normalized["transition_count"] = count
    if identity:
        identifier = value["id"]
        if not isinstance(identifier, str) or not identifier.strip():
            raise ValueError(f"{label} id is invalid")
        normalized["id"] = identifier
    return normalized


def validate_registration_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "experiment_id",
        "source_commit",
        "runner",
        "source_files",
        "inputs",
        "recipe",
        "technical_gates",
        "output_dir",
        "authority",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("registration schema version differs")
    if payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("registration experiment id differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    source_files = payload["source_files"]
    if not isinstance(source_files, Mapping) or not source_files:
        raise ValueError("registration source files are missing")
    normalized_source_files: dict[str, str] = {}
    for path, sha256 in source_files.items():
        relative_path = Path(path) if isinstance(path, str) else None
        if (
            relative_path is None
            or not path
            or relative_path.is_absolute()
            or ".." in relative_path.parts
        ):
            raise ValueError("registration source file path is invalid")
        normalized_source_files[path.replace("\\", "/")] = _validate_sha256(
            sha256, f"source file {path}"
        )
    if set(normalized_source_files) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("registration source file inventory differs")
    expected_runner_path = (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve()
    if Path(runner["path"]).resolve() != expected_runner_path:
        raise ValueError("registration runner path differs")
    if runner["sha256"] != normalized_source_files[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("registration runner hash differs from source inventory")

    inputs = payload["inputs"]
    input_keys = {
        "native_module",
        "dll_directories",
        "items_json",
        "parent_checkpoint",
        "development_replay",
        "evaluation_replays",
    }
    if not isinstance(inputs, Mapping) or set(inputs) != input_keys:
        raise ValueError("registration input keys differ")
    dll_directories = inputs["dll_directories"]
    if dll_directories != []:
        raise ValueError("registration DLL directories differ")
    evaluations = inputs["evaluation_replays"]
    if not isinstance(evaluations, list) or not evaluations:
        raise ValueError("registration evaluation replays are missing")
    normalized_evaluations = [
        _validate_file_binding(
            value,
            label="evaluation replay",
            transition_count=True,
            identity=True,
        )
        for value in evaluations
    ]
    evaluation_ids = [value["id"] for value in normalized_evaluations]
    if len(set(evaluation_ids)) != len(evaluation_ids):
        raise ValueError("registration evaluation replay ids are not unique")
    development = _validate_file_binding(
        inputs["development_replay"],
        label="development replay",
        transition_count=True,
    )
    evaluation_hashes = [value["sha256"] for value in normalized_evaluations]
    evaluation_paths = [
        str(Path(value["path"]).resolve()).casefold()
        for value in normalized_evaluations
    ]
    if development["sha256"] in evaluation_hashes:
        raise ValueError("development and evaluation replay identities overlap")
    if str(Path(development["path"]).resolve()).casefold() in evaluation_paths:
        raise ValueError("development and evaluation replay paths overlap")
    if len(set(evaluation_hashes)) != len(evaluation_hashes):
        raise ValueError("registration evaluation replay identities overlap")
    if len(set(evaluation_paths)) != len(evaluation_paths):
        raise ValueError("registration evaluation replay paths overlap")
    output_dir = payload["output_dir"]
    if not isinstance(output_dir, str) or not output_dir.strip():
        raise ValueError("registration output directory is invalid")
    output_path = Path(output_dir)
    if not output_path.is_absolute():
        raise ValueError("registration output directory must be absolute")
    try:
        output_path.resolve().relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("registration output directory is outside reports") from exc
    if output_path.resolve() == REPORTS_ROOT.resolve():
        raise ValueError("registration output directory cannot be reports root")
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("registration fixed recipe differs")
    if payload["technical_gates"] != FIXED_TECHNICAL_GATES:
        raise ValueError("registration technical gates differ")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("registration authority differs")
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "runner": runner,
        "source_files": normalized_source_files,
        "inputs": {
            "native_module": _validate_file_binding(
                inputs["native_module"], label="native module"
            ),
            "dll_directories": list(dll_directories),
            "items_json": _validate_file_binding(
                inputs["items_json"], label="items.json"
            ),
            "parent_checkpoint": _validate_file_binding(
                inputs["parent_checkpoint"], label="parent checkpoint"
            ),
            "development_replay": development,
            "evaluation_replays": normalized_evaluations,
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "technical_gates": copy.deepcopy(FIXED_TECHNICAL_GATES),
        "output_dir": str(output_path),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def _loss_summary(values: Sequence[float]) -> dict[str, float | int | None]:
    if not values:
        return {"count": 0, "minimum": None, "mean": None, "maximum": None}
    rows = np.asarray(values, dtype=np.float64)
    return {
        "count": int(rows.size),
        "minimum": float(rows.min()),
        "mean": float(rows.mean()),
        "maximum": float(rows.max()),
    }


def _adapter_metadata(parent: nn.Module, metadata: Mapping[str, Any]) -> dict[str, Any]:
    required = (
        "network_type",
        "continuous_dim",
        "action_dim",
        "card_vocab",
        "potion_vocab",
        "relic_vocab",
        "card_slots",
        "potion_slots",
        "relic_slots",
    )
    if any(name not in metadata for name in required):
        raise ValueError("candidate adapter metadata is incomplete")
    normalized = {name: metadata[name] for name in required}
    expected_vocab = {
        "card_vocab": parent.card_embedding.num_embeddings,
        "potion_vocab": parent.potion_embedding.num_embeddings,
        "relic_vocab": parent.relic_embedding.num_embeddings,
    }
    if any(normalized[name] != value for name, value in expected_vocab.items()):
        raise ValueError("candidate adapter metadata vocabulary differs")
    return normalized


def _copy_poc_head(source: nn.Module, target: nn.Sequential) -> None:
    state = {
        name.removeprefix("layers."): tensor.detach().clone()
        for name, tensor in source.state_dict().items()
    }
    target.load_state_dict(state, strict=True)


def _validate_fit_recipe(recipe: Mapping[str, Any]) -> None:
    required = set(FIXED_RECIPE)
    if not isinstance(recipe, Mapping) or set(recipe) != required:
        raise ValueError("candidate fit recipe keys differ")
    for name in (
        "hidden_dim",
        "simulator_updates",
        "development_gate_updates",
        "action_updates",
        "batch_size",
    ):
        value = recipe[name]
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ValueError(f"candidate fit recipe {name} is invalid")
    for name in ("learning_rate", "direct_open_calibration_cap"):
        value = recipe[name]
        if not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"candidate fit recipe {name} is invalid")
    if int(recipe["hidden_dim"]) != 64:
        raise ValueError("candidate fit hidden dimension differs from confirmed POC")


def fit_candidate(
    *,
    parent: nn.Module,
    metadata: Mapping[str, Any],
    simulator_features: torch.Tensor,
    simulator_labels: torch.Tensor,
    simulator_train_indices: torch.Tensor,
    development_features: torch.Tensor,
    development_masks: torch.Tensor,
    development_actions: torch.Tensor,
    development_changed: torch.Tensor,
    recipe: Mapping[str, Any] = FIXED_RECIPE,
) -> tuple[LatentGatedActionAdapter, dict[str, Any]]:
    _validate_fit_recipe(recipe)
    normalized_metadata = _adapter_metadata(parent, metadata)
    simulator_features = simulator_features.detach().cpu().float()
    simulator_labels = simulator_labels.detach().cpu().bool().reshape(-1)
    simulator_train_indices = simulator_train_indices.detach().cpu().long().reshape(-1)
    development_features = development_features.detach().cpu().float()
    development_masks = development_masks.detach().cpu().bool()
    development_actions = development_actions.detach().cpu().long().reshape(-1)
    development_changed = development_changed.detach().cpu().bool().reshape(-1)
    if simulator_features.shape[0] != simulator_labels.numel():
        raise ValueError("candidate simulator row count differs")
    development_rows = development_changed.numel()
    if any(
        value.shape[0] != development_rows
        for value in (development_features, development_masks)
    ) or development_actions.numel() != development_rows:
        raise ValueError("candidate development row count differs")
    if not bool(development_changed.any()) or not bool((~development_changed).any()):
        raise ValueError("candidate development provenance strata are empty")
    if development_masks.shape[1] != normalized_metadata["action_dim"]:
        raise ValueError("candidate development action mask width differs")

    parent_hash_before = state_dict_sha256(parent.state_dict())
    simulator_gate, simulator_losses = fit_classifier(
        simulator_features,
        simulator_labels,
        simulator_train_indices,
        seed=int(recipe["classifier_seed"]),
        updates=int(recipe["simulator_updates"]),
    )
    development_indices = torch.arange(development_rows)
    gate, gate_losses = fit_classifier(
        development_features,
        development_changed,
        development_indices,
        seed=int(recipe["classifier_seed"]) + 700,
        updates=int(recipe["development_gate_updates"]),
        initial_state=simulator_gate.state_dict(),
    )
    development_scores = classifier_scores(gate, development_features)
    threshold = threshold_at_direct_open_cap(
        development_scores,
        development_changed,
        cap=float(recipe["direct_open_calibration_cap"]),
    )
    if not math.isfinite(threshold) or not 0.0 < threshold < 1.0:
        raise RuntimeError("candidate calibrated threshold is not finite and open")
    action_head, action_losses = fit_action_classifier(
        development_features,
        development_masks,
        development_actions,
        development_changed,
        seed=int(recipe["classifier_seed"]) + 701,
        updates=int(recipe["action_updates"]),
    )
    adapter = LatentGatedActionAdapter(
        parent,
        normalized_metadata,
        LatentGateConfig(
            hidden_dim=int(recipe["hidden_dim"]),
            gate_threshold=threshold,
        ),
    )
    _copy_poc_head(gate, adapter.gate)
    _copy_poc_head(action_head, adapter.correction)
    parent_hash_after = state_dict_sha256(adapter.parent.state_dict())
    if parent_hash_after != parent_hash_before:
        raise RuntimeError("candidate fit changed the frozen parent identity")
    losses = [*simulator_losses, *gate_losses, *action_losses]
    if not all(math.isfinite(value) for value in losses):
        raise RuntimeError("candidate fit produced a non-finite objective")
    return adapter, {
        "simulator_gate_loss": _loss_summary(simulator_losses),
        "development_gate_loss": _loss_summary(gate_losses),
        "development_action_loss": _loss_summary(action_losses),
        "simulator_update_count": len(simulator_losses),
        "development_gate_update_count": len(gate_losses),
        "action_update_count": len(action_losses),
        "calibrated_gate_threshold": threshold,
        "development_direct_open_share": float(
            development_scores[~development_changed]
            .ge(threshold)
            .float()
            .mean()
            .item()
        ),
        "development_changed_open_share": float(
            development_scores[development_changed]
            .ge(threshold)
            .float()
            .mean()
            .item()
        ),
        "parent_state_dict_sha256_before": parent_hash_before,
        "parent_state_dict_sha256_after": parent_hash_after,
        "gate_state_dict_sha256": state_dict_sha256(adapter.gate.state_dict()),
        "correction_state_dict_sha256": state_dict_sha256(
            adapter.correction.state_dict()
        ),
        "all_objectives_finite": True,
    }


def evaluate_candidate(
    *,
    adapter: LatentGatedActionAdapter,
    continuous: torch.Tensor,
    card_ids: torch.Tensor,
    potion_ids: torch.Tensor,
    relic_ids: torch.Tensor,
    action_masks: torch.Tensor,
    executed_actions: torch.Tensor,
    changed: torch.Tensor,
    gates: Mapping[str, Any] = FIXED_TECHNICAL_GATES,
) -> dict[str, Any]:
    if gates != FIXED_TECHNICAL_GATES:
        raise ValueError("candidate technical gates differ")
    changed = changed.detach().cpu().bool().reshape(-1)
    executed_actions = executed_actions.detach().cpu().long().reshape(-1)
    if not bool(changed.any()) or not bool((~changed).any()):
        raise ValueError("candidate evaluation provenance strata are empty")
    adapter.eval()
    with torch.no_grad():
        selected = adapter.select_actions(
            continuous, card_ids, potion_ids, relic_ids, action_masks
        )
    metrics = gated_action_metrics(
        parent_actions=selected.parent_actions,
        correction_actions=selected.correction_actions,
        executed_actions=executed_actions,
        changed=changed,
        gate_open=selected.gate_open,
        continuous=continuous,
    )
    direct = metrics["direct"]
    changed_metrics = metrics["changed"]
    checks = {
        "direct_gate_open_share_at_most_ceiling": float(
            direct["gate_open_share"]
        )
        <= float(gates["direct_gate_open_share_maximum"]),
        "changed_gate_open_share_at_least_floor": float(
            changed_metrics["gate_open_share"]
        )
        >= float(gates["changed_gate_open_share_minimum"]),
        "direct_candidate_agreement_at_least_floor": float(
            direct["candidate_agreement"]
        )
        >= float(gates["direct_candidate_agreement_minimum"]),
        "changed_correction_agreement_at_least_floor": float(
            changed_metrics["correction_agreement"]
        )
        >= float(gates["changed_correction_agreement_minimum"]),
        "changed_candidate_agreement_at_least_floor": float(
            changed_metrics["candidate_agreement"]
        )
        >= float(gates["changed_candidate_agreement_minimum"]),
        "overall_candidate_agreement_uplift_at_least_floor": float(
            metrics["candidate_agreement"]
        )
        >= float(metrics["parent_agreement"])
        + float(gates["overall_candidate_agreement_uplift_minimum"]),
        "positive_energy_end_turn_increase_at_most_ceiling": int(
            metrics["positive_energy_end_turn_count_delta"]
        )
        <= int(gates["positive_energy_end_turn_increase_maximum"]),
    }
    checks["all_conditions_passed"] = all(checks.values())
    return {"metrics": metrics, "criteria": checks}


def aggregate_eligibility(evaluations: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    if not isinstance(evaluations, Mapping) or not evaluations:
        raise ValueError("candidate evaluations are missing")
    per_replay = {
        name: bool(value.get("criteria", {}).get("all_conditions_passed"))
        for name, value in evaluations.items()
    }
    all_passed = all(per_replay.values())
    return {
        "evaluation_replay_count": len(per_replay),
        "per_replay_passed": per_replay,
        "all_conditions_passed": all_passed,
        "decision": (
            "eligible_for_separately_registered_gameplay_evaluation"
            if all_passed
            else "fixed_candidate_fit_failed_cohort_closed"
        ),
    }


def publish_result(
    output_dir: Path,
    artifact: Mapping[str, Any],
    report: Mapping[str, Any],
) -> dict[str, Any]:
    output_dir = output_dir.resolve()
    staging_dir = output_dir.with_name(f".{output_dir.name}.staging")
    if output_dir.exists():
        raise ValueError(f"candidate output directory already exists: {output_dir}")
    if staging_dir.exists():
        raise ValueError(f"candidate staging directory already exists: {staging_dir}")
    if artifact.get("production_compatible") is not False:
        raise ValueError("candidate artifact must not be production-compatible")
    if report.get("authority") != RESULT_AUTHORITY:
        raise ValueError("candidate report authority differs")
    staging_dir.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = staging_dir / "latent_gated_development_adapter.pth"
        torch.save(dict(artifact), artifact_path)
        final_report = copy.deepcopy(dict(report))
        final_report["artifact"] = {
            "path": artifact_path.name,
            "sha256": sha256_file(artifact_path),
            "size_bytes": artifact_path.stat().st_size,
            "production_compatible": False,
        }
        (staging_dir / "report.json").write_bytes(
            _canonical_json_bytes(final_report)
        )
        os.replace(staging_dir, output_dir)
        return final_report
    except Exception:
        shutil.rmtree(staging_dir, ignore_errors=True)
        raise


def _resolve_absolute_path(value: str, label: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        raise ValueError(f"registered {label} path must be absolute")
    return path.resolve()


def _current_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
    ).strip().lower()


def _require_source_ancestor(source_commit: str) -> None:
    completed = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, _current_commit()],
        cwd=REPO_ROOT,
        check=False,
    )
    if completed.returncode != 0:
        raise ValueError("registered source commit is not an ancestor of current HEAD")


def _source_file_unchanged(source_commit: str, relative_path: str) -> bool:
    return (
        subprocess.run(
            ["git", "diff", "--quiet", source_commit, "--", relative_path],
            cwd=REPO_ROOT,
            check=False,
        ).returncode
        == 0
    )


def _committed_registration_bytes(relative_path: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"HEAD:{relative_path}"],
        cwd=REPO_ROOT,
    )


def load_committed_registration(
    registration_path: Path,
) -> tuple[dict[str, Any], str]:
    registration_path = registration_path.resolve()
    try:
        relative = registration_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("registration path is outside reports") from exc
    if registration_path.suffix.lower() != ".json" or not relative.parts:
        raise ValueError("registration path is invalid")
    repository_relative = registration_path.relative_to(REPO_ROOT).as_posix()
    raw = registration_path.read_bytes()
    try:
        observed_payload = json.loads(raw)
        committed_payload = json.loads(
            _committed_registration_bytes(repository_relative)
        )
    except (json.JSONDecodeError, subprocess.CalledProcessError) as exc:
        raise ValueError("registration is not committed at current HEAD") from exc
    if observed_payload != committed_payload or not _source_file_unchanged(
        _current_commit(), repository_relative
    ):
        raise ValueError("registration differs from committed content")
    return (
        validate_registration_payload(observed_payload),
        hashlib.sha256(raw).hexdigest(),
    )


def _validate_execution_bindings(
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    _require_source_ancestor(registration["source_commit"])
    runner_path = _resolve_absolute_path(registration["runner"]["path"], "runner")
    if runner_path != Path(__file__).resolve():
        raise ValueError("registered runner path differs")
    if sha256_file(runner_path) != registration["runner"]["sha256"]:
        raise ValueError("registered runner hash differs")
    for relative, expected in registration["source_files"].items():
        source_path = (REPO_ROOT / relative).resolve()
        try:
            source_path.relative_to(REPO_ROOT)
        except ValueError as exc:
            raise ValueError("registered source file escapes repository") from exc
        if (
            not source_path.is_file()
            or sha256_file(source_path) != expected
            or not _source_file_unchanged(
                registration["source_commit"], relative
            )
        ):
            raise ValueError(f"registered source file hash differs: {relative}")

    inputs = registration["inputs"]
    paths: dict[str, Any] = {}
    for name in (
        "native_module",
        "items_json",
        "parent_checkpoint",
        "development_replay",
    ):
        binding = inputs[name]
        path = _resolve_absolute_path(binding["path"], name)
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError(f"registered {name} hash differs")
        paths[name] = path
    evaluation_paths: dict[str, Path] = {}
    for binding in inputs["evaluation_replays"]:
        path = _resolve_absolute_path(binding["path"], "evaluation replay")
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError(
                f"registered evaluation replay hash differs: {binding['id']}"
            )
        evaluation_paths[binding["id"]] = path
    dll_directories = [
        _resolve_absolute_path(value, "DLL directory")
        for value in inputs["dll_directories"]
    ]
    if any(not path.is_dir() for path in dll_directories):
        raise ValueError("registered DLL directory does not exist")
    output_dir = _resolve_absolute_path(registration["output_dir"], "output")
    try:
        output_dir.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("registered output directory is outside reports") from exc
    if output_dir.exists():
        raise ValueError(f"candidate output directory already exists: {output_dir}")
    staging_dir = output_dir.with_name(f".{output_dir.name}.staging")
    if staging_dir.exists():
        raise ValueError(f"candidate staging directory already exists: {staging_dir}")
    paths["evaluation_replays"] = evaluation_paths
    paths["dll_directories"] = dll_directories
    paths["output_dir"] = output_dir
    return paths


def _trainer_metadata(trainer: Any) -> dict[str, Any]:
    network = trainer.online_network
    return {
        "network_type": trainer.network_type,
        "continuous_dim": trainer.continuous_dim,
        "action_dim": trainer.action_dim,
        "card_vocab": network.card_embedding.num_embeddings,
        "potion_vocab": network.potion_embedding.num_embeddings,
        "relic_vocab": network.relic_embedding.num_embeddings,
        "card_slots": trainer.card_slots,
        "potion_slots": trainer.potion_slots,
        "relic_slots": trainer.relic_slots,
    }


def _load_replay_corpus(
    *,
    path: Path,
    expected_transition_count: int,
    parent: nn.Module,
    expected_parent_sha256: str,
) -> dict[str, Any]:
    checkpoint = torch.load(path, map_location="cpu", weights_only=True)
    metadata, replay, provenance = _validate_callability_checkpoint(
        checkpoint,
        expected_transition_count=expected_transition_count,
    )
    online_state = checkpoint["online_network_state_dict"]
    if parameter_sha256(online_state) != expected_parent_sha256:
        raise ValueError("registered replay parent identity differs")
    spans, span_telemetry = build_candidate_decision_spans(replay, gamma=GAMMA)
    changed = spans["anchor_to_executed_action"].bool().cpu()
    if not bool(changed.any()) or not bool((~changed).any()):
        raise ValueError("registered replay provenance strata are empty")
    raw = {
        "continuous": spans["continuous"].float().cpu(),
        "card_ids": spans["card_ids"].long().cpu(),
        "potion_ids": spans["potion_ids"].long().cpu(),
        "relic_ids": spans["relic_ids"].long().cpu(),
        "action_masks": spans["action_masks"].bool().cpu(),
        "executed_actions": spans["actions"].long().cpu(),
        "changed": changed,
    }
    features = parent_feature_views(
        parent,
        continuous=raw["continuous"],
        card_ids=raw["card_ids"],
        potion_ids=raw["potion_ids"],
        relic_ids=raw["relic_ids"],
        action_masks=raw["action_masks"],
    )["parent_latent"]
    return {
        "metadata": metadata,
        "features": features,
        "raw": raw,
        "provenance": provenance,
        "span_telemetry": span_telemetry,
    }


def _collect_simulator_corpus(
    *,
    native_module: Any,
    id_mapper: Any,
    trainer: Any,
    parent_state: Mapping[str, torch.Tensor],
    recipe: Mapping[str, Any],
) -> dict[str, Any]:
    simulator_seeds = tuple(
        range(
            int(recipe["simulator_seed_first"]),
            int(recipe["simulator_seed_last"]) + 1,
        )
    )
    config = SmokeConfig(
        train_seeds=simulator_seeds,
        evaluation_seeds=(max(simulator_seeds) + 1,),
        battle_indices=tuple(int(value) for value in recipe["battle_indices"]),
        ascension=0,
        max_decisions_per_seed=100,
        max_actions_per_turn=8,
        behavior_seed=int(recipe["simulator_training_seed"]),
        behavior_policy=FROZEN_PARENT_GUARDED_EPSILON_BEHAVIOR,
        behavior_epsilon=0.1,
        network_seed=int(recipe["classifier_seed"]),
        batch_size=int(recipe["batch_size"]),
        optimizer_steps=1,
        replay_target_mode=ONE_STEP_TD_TARGET,
        frozen_parent_bootstrap_policy=FROZEN_PARENT_RAW_GREEDY_BOOTSTRAP,
        complete_trajectories_only=True,
        deployment_guard_proxy=GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    )
    config.validate()
    trainer.online_network.eval()
    rows, telemetry = collect_transitions(
        native_module,
        id_mapper=id_mapper,
        config=config,
        behavior_trainer=trainer,
        expected_behavior_parent_sha256=parameter_sha256(parent_state),
    )
    labels = torch.tensor(
        [row.guard_proxy_replaced for row in rows], dtype=torch.bool
    )
    if not bool(labels.any()) or not bool((~labels).any()):
        raise RuntimeError("simulator guard labels do not contain both classes")
    features = parent_feature_views(
        trainer.online_network,
        continuous=torch.from_numpy(np.stack([row.continuous for row in rows])),
        card_ids=torch.from_numpy(np.stack([row.card_ids for row in rows])),
        potion_ids=torch.from_numpy(np.stack([row.potion_ids for row in rows])),
        relic_ids=torch.from_numpy(np.stack([row.relic_ids for row in rows])),
        action_masks=torch.from_numpy(np.stack([row.action_mask for row in rows])),
    )["parent_latent"]
    heldout_seeds = set(simulator_seeds[:: int(recipe["simulator_validation_stride"])])
    validation_mask = torch.tensor([row.seed in heldout_seeds for row in rows])
    train_indices = torch.where(~validation_mask)[0]
    validation_indices = torch.where(validation_mask)[0]
    if not train_indices.numel() or not validation_indices.numel():
        raise RuntimeError("simulator train or validation rows are empty")
    return {
        "features": features,
        "labels": labels,
        "train_indices": train_indices,
        "validation_indices": validation_indices,
        "telemetry": telemetry,
        "row_count": len(rows),
    }


def _selection_exact(
    original: LatentGatedActionAdapter,
    restored: LatentGatedActionAdapter,
    raw: Mapping[str, torch.Tensor],
) -> bool:
    names = (
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "action_masks",
    )
    with torch.no_grad():
        expected = original.select_actions(*(raw[name] for name in names))
        actual = restored.select_actions(*(raw[name] for name in names))
    return (
        torch.equal(expected.actions, actual.actions)
        and torch.equal(expected.parent_actions, actual.parent_actions)
        and torch.equal(expected.correction_actions, actual.correction_actions)
        and torch.equal(expected.gate_probabilities, actual.gate_probabilities)
        and torch.equal(expected.gate_open, actual.gate_open)
        and expected.telemetry == actual.telemetry
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("candidate fit must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("candidate fit must run in isolated -I mode")
    registration_path = registration_path.resolve()
    registration, registration_sha256 = load_committed_registration(
        registration_path
    )
    paths = _validate_execution_bindings(registration)
    inputs = registration["inputs"]
    recipe = registration["recipe"]

    id_mapper = build_id_mapper(paths["items_json"])
    initial_checkpoint = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=inputs["parent_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        id_mapper,
        seed=int(recipe["classifier_seed"]),
        batch_size=int(recipe["batch_size"]),
        learning_starts=int(recipe["batch_size"]),
    )
    parent_state, initialization = initialize_trainer(trainer, initial_checkpoint)
    parent_hash = parameter_sha256(parent_state)
    parent = trainer.online_network
    parent.eval()
    metadata = _trainer_metadata(trainer)

    development_binding = inputs["development_replay"]
    development = _load_replay_corpus(
        path=paths["development_replay"],
        expected_transition_count=development_binding["transition_count"],
        parent=parent,
        expected_parent_sha256=parent_hash,
    )
    if _adapter_metadata(parent, development["metadata"]) != _adapter_metadata(
        parent, metadata
    ):
        raise ValueError("development replay metadata differs from parent")
    evaluations: dict[str, dict[str, Any]] = {}
    for binding in inputs["evaluation_replays"]:
        corpus = _load_replay_corpus(
            path=paths["evaluation_replays"][binding["id"]],
            expected_transition_count=binding["transition_count"],
            parent=parent,
            expected_parent_sha256=parent_hash,
        )
        if _adapter_metadata(parent, corpus["metadata"]) != _adapter_metadata(
            parent, metadata
        ):
            raise ValueError(f"evaluation replay metadata differs: {binding['id']}")
        evaluations[binding["id"]] = corpus

    native_module = load_native_module(
        paths["native_module"],
        dll_directories=paths["dll_directories"],
    )
    simulator = _collect_simulator_corpus(
        native_module=native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        parent_state=parent_state,
        recipe=recipe,
    )
    adapter, fit_telemetry = fit_candidate(
        parent=parent,
        metadata=metadata,
        simulator_features=simulator["features"],
        simulator_labels=simulator["labels"],
        simulator_train_indices=simulator["train_indices"],
        development_features=development["features"],
        development_masks=development["raw"]["action_masks"],
        development_actions=development["raw"]["executed_actions"],
        development_changed=development["raw"]["changed"],
        recipe=recipe,
    )
    evaluation_reports = {
        name: evaluate_candidate(
            adapter=adapter,
            gates=registration["technical_gates"],
            **corpus["raw"],
        )
        for name, corpus in evaluations.items()
    }
    eligibility = aggregate_eligibility(evaluation_reports)
    artifact = build_development_artifact(
        adapter,
        parent_checkpoint_sha256=inputs["parent_checkpoint"]["sha256"],
        telemetry={
            "experiment_id": EXPERIMENT_ID,
            "source_commit": registration["source_commit"],
            "fit": fit_telemetry,
        },
    )
    restored = load_development_artifact(
        parent,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=inputs["parent_checkpoint"]["sha256"],
    )
    round_trip = {
        "development": _selection_exact(
            adapter, restored, development["raw"]
        ),
        **{
            name: _selection_exact(adapter, restored, corpus["raw"])
            for name, corpus in evaluations.items()
        },
    }
    if not all(round_trip.values()):
        raise RuntimeError("candidate artifact round trip differs")

    report = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "registration": {
            "path": str(registration_path),
            "sha256": registration_sha256,
        },
        "bindings": copy.deepcopy(inputs),
        "recipe": copy.deepcopy(recipe),
        "technical_gates": copy.deepcopy(registration["technical_gates"]),
        "parent": {
            "parameter_sha256": parent_hash,
            "adapter_state_dict_sha256": state_dict_sha256(parent.state_dict()),
            "initialization": initialization,
        },
        "simulator": {
            "row_count": simulator["row_count"],
            "training_row_count": int(simulator["train_indices"].numel()),
            "validation_row_count": int(simulator["validation_indices"].numel()),
            "telemetry": simulator["telemetry"],
        },
        "development_replay": {
            "provenance": development["provenance"],
            "span_telemetry": development["span_telemetry"],
        },
        "fit": fit_telemetry,
        "evaluations": {
            name: {
                "binding": next(
                    value
                    for value in inputs["evaluation_replays"]
                    if value["id"] == name
                ),
                "provenance": evaluations[name]["provenance"],
                "span_telemetry": evaluations[name]["span_telemetry"],
                **evaluation,
            }
            for name, evaluation in evaluation_reports.items()
        },
        "artifact_round_trip_exact": round_trip,
        "eligibility": eligibility,
        "decision": eligibility["decision"],
        "authority": copy.deepcopy(RESULT_AUTHORITY),
        "limitations": [
            "The adapter artifact is development-only and not loadable as an RL v2 production checkpoint.",
            "Evaluation replay success does not establish live gameplay improvement.",
            "A separately registered gameplay evaluation is required before qualification.",
            "Production r16 and combat agent routing remain unchanged.",
        ],
    }
    return publish_result(paths["output_dir"], artifact, report)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", required=True, type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    report = run(args.registration)
    print(
        json.dumps(
            {
                "experiment_id": report["experiment_id"],
                "decision": report["decision"],
                "artifact_sha256": report["artifact"]["sha256"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
