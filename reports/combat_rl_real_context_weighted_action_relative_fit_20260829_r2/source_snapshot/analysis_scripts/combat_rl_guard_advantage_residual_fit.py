"""Fit one registered post-guard residual from a paired LightSTS corpus."""

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
from spirecomm.ai.rl.v2.guard_advantage_residual import (  # noqa: E402
    GuardAdvantageResidual,
    GuardAdvantageResidualConfig,
    build_development_artifact,
    load_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-guard-advantage-residual-fit-20260828-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_corpus.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "spirecomm/ai/rl/v2/guard_advantage_residual.py",
    "spirecomm/ai/rl/v2/network.py",
)

FIXED_RECIPE = {
    "architecture": "frozen_parent_post_guard_abstaining_residual",
    "hidden_dim": 64,
    "gate_threshold": 0.5,
    "optimizer": "adam",
    "learning_rate": 0.001,
    "updates": 512,
    "positive_rows_per_batch": 32,
    "negative_rows_per_batch": 32,
    "training_seed": 2026082822,
    "device": "cpu",
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


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        allow_nan=False,
        ensure_ascii=True,
        indent=2,
        sort_keys=True,
    ).encode("ascii") + b"\n"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


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


def _validate_file_binding(value: Any, *, label: str) -> dict[str, str]:
    if not isinstance(value, Mapping) or set(value) != {"path", "sha256"}:
        raise ValueError(f"{label} binding keys differ")
    path = value["path"]
    if not isinstance(path, str) or not path.strip():
        raise ValueError(f"{label} path is invalid")
    return {"path": path, "sha256": _validate_sha256(value["sha256"], label)}


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
        raise ValueError("residual fit registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("residual fit registration schema differs")
    if payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("residual fit experiment id differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    source_files = payload["source_files"]
    if not isinstance(source_files, Mapping):
        raise ValueError("residual fit source files are missing")
    normalized_sources: dict[str, str] = {}
    for raw_path, raw_sha256 in source_files.items():
        if not isinstance(raw_path, str):
            raise ValueError("residual fit source path is invalid")
        path = Path(raw_path)
        if not raw_path or path.is_absolute() or ".." in path.parts:
            raise ValueError("residual fit source path is invalid")
        normalized_sources[raw_path.replace("\\", "/")] = _validate_sha256(
            raw_sha256, f"source file {raw_path}"
        )
    if set(normalized_sources) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("residual fit source inventory differs")
    expected_runner = (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve()
    if Path(runner["path"]).resolve() != expected_runner:
        raise ValueError("residual fit runner path differs")
    if runner["sha256"] != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("residual fit runner hash differs from source inventory")

    inputs = payload["inputs"]
    expected_inputs = {
        "items_json",
        "parent_checkpoint",
        "train_corpus",
        "evaluation_corpus",
    }
    if not isinstance(inputs, Mapping) or set(inputs) != expected_inputs:
        raise ValueError("residual fit inputs differ")
    normalized_inputs = {
        name: _validate_file_binding(inputs[name], label=name)
        for name in sorted(expected_inputs)
    }
    if normalized_inputs["train_corpus"]["sha256"] == normalized_inputs[
        "evaluation_corpus"
    ]["sha256"]:
        raise ValueError("residual fit corpus identities overlap")
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("residual fit fixed recipe differs")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("residual fit authority differs")
    output_dir = payload["output_dir"]
    if not isinstance(output_dir, str) or not Path(output_dir).is_absolute():
        raise ValueError("residual fit output path must be absolute")
    output_path = Path(output_dir).resolve()
    try:
        output_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("residual fit output path is outside reports") from exc
    if output_path == REPORTS_ROOT.resolve():
        raise ValueError("residual fit output path cannot be reports root")
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


def _current_commit() -> str:
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip().lower()


def _committed_registration_bytes(path: Path) -> bytes:
    relative = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    return subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=REPO_ROOT)


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
        raise ValueError("residual fit output or staging directory already exists")
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


def _alternative_masks(
    metadata: Sequence[Mapping[str, Any]],
    action_masks: torch.Tensor,
    guard_actions: torch.Tensor,
) -> torch.Tensor:
    if len(metadata) != action_masks.shape[0]:
        raise ValueError("residual corpus metadata row count differs")
    result = torch.zeros_like(action_masks, dtype=torch.bool)
    for row_index, row in enumerate(metadata):
        branches = row.get("branch_returns")
        if not isinstance(branches, Mapping) or len(branches) < 2:
            raise ValueError("residual corpus branch identities are missing")
        guard = int(guard_actions[row_index])
        for raw_index in branches:
            index = int(raw_index)
            if not 0 <= index < action_masks.shape[1]:
                raise ValueError("residual corpus branch action is outside action space")
            if index != guard:
                result[row_index, index] = True
    if bool((result & ~action_masks).any()) or not bool(result.any(dim=1).all()):
        raise ValueError("residual corpus alternatives are not legal and non-empty")
    return result


def load_corpus(path: Path, *, expected_partition: str) -> dict[str, Any]:
    payload = torch.load(path, map_location="cpu", weights_only=False)
    if not isinstance(payload, Mapping):
        raise ValueError("residual corpus root is invalid")
    required = {"schema_version", "corpus_kind", "partition", "tensors", "metadata"}
    if set(payload) != required or payload["schema_version"] != 1:
        raise ValueError("residual corpus schema differs")
    if payload["corpus_kind"] != "combat_guard_advantage_corpus":
        raise ValueError("residual corpus kind differs")
    if payload["partition"] != expected_partition:
        raise ValueError("residual corpus partition differs")
    tensors = payload["tensors"]
    expected_tensors = {
        "continuous",
        "card_ids",
        "potion_ids",
        "relic_ids",
        "action_masks",
        "guard_actions",
        "target_actions",
        "advantages",
        "positive",
    }
    if not isinstance(tensors, Mapping) or set(tensors) != expected_tensors:
        raise ValueError("residual corpus tensor inventory differs")
    normalized = {
        "continuous": tensors["continuous"].float().cpu(),
        "card_ids": tensors["card_ids"].long().cpu(),
        "potion_ids": tensors["potion_ids"].long().cpu(),
        "relic_ids": tensors["relic_ids"].long().cpu(),
        "action_masks": tensors["action_masks"].bool().cpu(),
        "guard_actions": tensors["guard_actions"].long().cpu().reshape(-1),
        "target_actions": tensors["target_actions"].long().cpu().reshape(-1),
        "advantages": tensors["advantages"].float().cpu().reshape(-1),
        "positive": tensors["positive"].bool().cpu().reshape(-1),
    }
    row_count = normalized["positive"].numel()
    if row_count == 0 or any(value.shape[0] != row_count for value in normalized.values()):
        raise ValueError("residual corpus tensor row counts differ")
    if not bool(normalized["positive"].any()) or not bool(
        (~normalized["positive"]).any()
    ):
        raise ValueError("residual corpus requires both label classes")
    metadata = payload["metadata"]
    if not isinstance(metadata, list):
        raise ValueError("residual corpus metadata is invalid")
    normalized["alternative_masks"] = _alternative_masks(
        metadata, normalized["action_masks"], normalized["guard_actions"]
    )
    rows = torch.arange(row_count)
    if not bool(
        normalized["action_masks"][rows, normalized["guard_actions"]].all()
    ):
        raise ValueError("residual corpus guard action is illegal")
    positive_rows = normalized["positive"]
    if not bool(
        normalized["alternative_masks"][
            rows[positive_rows], normalized["target_actions"][positive_rows]
        ].all()
    ):
        raise ValueError("residual corpus positive target is not an alternative")
    return {"tensors": normalized, "metadata": metadata, "row_count": row_count}


def _loss_summary(values: Sequence[float]) -> dict[str, float | int]:
    rows = torch.tensor(values, dtype=torch.float64)
    return {
        "count": len(values),
        "minimum": float(rows.min().item()),
        "mean": float(rows.mean().item()),
        "maximum": float(rows.max().item()),
        "final": float(rows[-1].item()),
    }


def fit_residual(
    *,
    parent: torch.nn.Module,
    metadata: Mapping[str, Any],
    corpus: Mapping[str, torch.Tensor],
    recipe: Mapping[str, Any] = FIXED_RECIPE,
) -> tuple[GuardAdvantageResidual, dict[str, Any]]:
    if recipe != FIXED_RECIPE:
        required = set(FIXED_RECIPE)
        if not isinstance(recipe, Mapping) or set(recipe) != required:
            raise ValueError("residual fit recipe keys differ")
    torch.manual_seed(int(recipe["training_seed"]))
    residual = GuardAdvantageResidual(
        parent,
        metadata,
        GuardAdvantageResidualConfig(
            hidden_dim=int(recipe["hidden_dim"]),
            gate_threshold=float(recipe["gate_threshold"]),
        ),
    )
    parent_before = state_dict_sha256(residual.parent.state_dict())
    residual.train()
    with torch.no_grad():
        features = residual.residual_components(
            corpus["continuous"],
            corpus["card_ids"],
            corpus["potion_ids"],
            corpus["relic_ids"],
            corpus["action_masks"],
            corpus["guard_actions"],
            corpus["alternative_masks"],
        ).features.detach()
    positive_indices = torch.where(corpus["positive"])[0]
    negative_indices = torch.where(~corpus["positive"])[0]
    if not positive_indices.numel() or not negative_indices.numel():
        raise ValueError("residual fit requires both training classes")
    optimizer = torch.optim.Adam(
        [*residual.gate.parameters(), *residual.action_head.parameters()],
        lr=float(recipe["learning_rate"]),
    )
    generator = torch.Generator(device="cpu")
    generator.manual_seed(int(recipe["training_seed"]) + 1)
    losses: list[float] = []
    gate_losses: list[float] = []
    action_losses: list[float] = []
    for _ in range(int(recipe["updates"])):
        positive_rows = positive_indices[
            torch.randint(
                positive_indices.numel(),
                (int(recipe["positive_rows_per_batch"]),),
                generator=generator,
            )
        ]
        negative_rows = negative_indices[
            torch.randint(
                negative_indices.numel(),
                (int(recipe["negative_rows_per_batch"]),),
                generator=generator,
            )
        ]
        rows = torch.cat((positive_rows, negative_rows))
        gate_logits = residual.gate(features[rows]).squeeze(1)
        gate_labels = corpus["positive"][rows].float()
        gate_loss = F.binary_cross_entropy_with_logits(gate_logits, gate_labels)
        action_logits = residual.action_head(features[positive_rows]).masked_fill(
            ~corpus["alternative_masks"][positive_rows], float("-inf")
        )
        action_loss = F.cross_entropy(
            action_logits, corpus["target_actions"][positive_rows]
        )
        loss = gate_loss + action_loss
        if not bool(torch.isfinite(loss)):
            raise RuntimeError("residual fit objective became non-finite")
        optimizer.zero_grad(set_to_none=True)
        loss.backward()
        optimizer.step()
        losses.append(float(loss.detach().item()))
        gate_losses.append(float(gate_loss.detach().item()))
        action_losses.append(float(action_loss.detach().item()))
    residual.eval()
    parent_after = state_dict_sha256(residual.parent.state_dict())
    if parent_after != parent_before or any(
        parameter.grad is not None for parameter in residual.parent.parameters()
    ):
        raise RuntimeError("residual fit changed the frozen parent")
    return residual, {
        "update_count": len(losses),
        "total_loss": _loss_summary(losses),
        "gate_loss": _loss_summary(gate_losses),
        "action_loss": _loss_summary(action_losses),
        "parent_state_dict_sha256_before": parent_before,
        "parent_state_dict_sha256_after": parent_after,
        "gate_state_dict_sha256": state_dict_sha256(residual.gate.state_dict()),
        "action_state_dict_sha256": state_dict_sha256(
            residual.action_head.state_dict()
        ),
        "all_objectives_finite": True,
    }


def classification_metrics(
    residual: GuardAdvantageResidual,
    corpus: Mapping[str, torch.Tensor],
) -> dict[str, Any]:
    residual.eval()
    with torch.no_grad():
        selected = residual.select_actions(
            corpus["continuous"],
            corpus["card_ids"],
            corpus["potion_ids"],
            corpus["relic_ids"],
            corpus["action_masks"],
            corpus["guard_actions"],
            corpus["alternative_masks"],
        )
    labels = corpus["positive"]
    predicted = selected.gate_open
    tp = int((predicted & labels).sum().item())
    tn = int((~predicted & ~labels).sum().item())
    fp = int((predicted & ~labels).sum().item())
    fn = int((~predicted & labels).sum().item())
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    action_correct = selected.residual_actions[labels].eq(
        corpus["target_actions"][labels]
    )
    expected_policy = torch.where(
        labels, corpus["target_actions"], corpus["guard_actions"]
    )
    return {
        "row_count": int(labels.numel()),
        "positive_count": int(labels.sum().item()),
        "negative_count": int((~labels).sum().item()),
        "confusion": {"true_positive": tp, "true_negative": tn, "false_positive": fp, "false_negative": fn},
        "gate_accuracy": (tp + tn) / labels.numel(),
        "gate_precision": precision,
        "gate_recall": recall,
        "gate_specificity": specificity,
        "gate_f1": 2.0 * precision * recall / max(precision + recall, 1e-12),
        "gate_balanced_accuracy": 0.5 * (recall + specificity),
        "gate_open_share": float(predicted.float().mean().item()),
        "positive_action_accuracy": float(action_correct.float().mean().item()),
        "hard_policy_accuracy": float(selected.actions.eq(expected_policy).float().mean().item()),
        "intervention_count": int(selected.actions.ne(corpus["guard_actions"]).sum().item()),
        "illegal_action_count": int(
            (~corpus["action_masks"][torch.arange(labels.numel()), selected.actions]).sum().item()
        ),
        "threshold": float(residual.config.gate_threshold),
    }


def _selection_exact(
    original: GuardAdvantageResidual,
    restored: GuardAdvantageResidual,
    corpus: Mapping[str, torch.Tensor],
) -> bool:
    arguments = (
        corpus["continuous"],
        corpus["card_ids"],
        corpus["potion_ids"],
        corpus["relic_ids"],
        corpus["action_masks"],
        corpus["guard_actions"],
        corpus["alternative_masks"],
    )
    with torch.no_grad():
        expected = original.select_actions(*arguments)
        actual = restored.select_actions(*arguments)
    return all(
        torch.equal(getattr(expected, name), getattr(actual, name))
        for name in (
            "actions",
            "guard_actions",
            "residual_actions",
            "gate_probabilities",
            "gate_open",
        )
    ) and expected.telemetry == actual.telemetry


def _render_summary(report: Mapping[str, Any]) -> str:
    train = report["classification"]["train"]
    evaluation = report["classification"]["evaluation"]
    return (
        "# Guard-Advantage Residual Fit\n\n"
        f"- Training rows: {train['row_count']}\n"
        f"- Evaluation rows: {evaluation['row_count']}\n"
        f"- Evaluation gate balanced accuracy: {evaluation['gate_balanced_accuracy']:.6f}\n"
        f"- Evaluation positive action accuracy: {evaluation['positive_action_accuracy']:.6f}\n"
        f"- Evaluation hard policy accuracy: {evaluation['hard_policy_accuracy']:.6f}\n"
        f"- Interventions at threshold 0.5: {evaluation['intervention_count']}\n"
        "- Authority: development-only; no gameplay or promotion authority.\n"
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("residual fit must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("residual fit must run in isolated -I mode")
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
        batch_size=int(recipe["positive_rows_per_batch"])
        + int(recipe["negative_rows_per_batch"]),
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
            raise ValueError(f"residual corpus {name} width differs from parent")
    residual, fit = fit_residual(
        parent=parent,
        metadata=metadata,
        corpus=train["tensors"],
        recipe=recipe,
    )
    classification = {
        "train": classification_metrics(residual, train["tensors"]),
        "evaluation": classification_metrics(residual, evaluation["tensors"]),
    }
    corpus_hashes = {
        "train": registration["inputs"]["train_corpus"]["sha256"],
        "evaluation": registration["inputs"]["evaluation_corpus"]["sha256"],
    }
    artifact = build_development_artifact(
        residual,
        parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        corpus_sha256=corpus_hashes,
        telemetry={"fit": fit, "classification": classification},
    )
    restored = load_development_artifact(
        parent,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        expected_corpus_sha256=corpus_hashes,
    )
    if not _selection_exact(residual, restored, evaluation["tensors"]):
        raise RuntimeError("residual artifact round trip changed evaluation selection")
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
            "seed_disjoint": True,
        },
        "fit": fit,
        "classification": classification,
        "artifact_round_trip_exact": True,
        "threshold_tuned": False,
        "output_dir": str(paths["output_dir"]),
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }
    output_dir = paths["output_dir"]
    staging_dir = output_dir.with_name(f".{output_dir.name}.staging")
    staging_dir.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = staging_dir / "guard_advantage_residual_development.pth"
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
    print(
        json.dumps(
            {
                "experiment_id": report["experiment_id"],
                "evaluation_gate_balanced_accuracy": report["classification"][
                    "evaluation"
                ]["gate_balanced_accuracy"],
                "evaluation_positive_action_accuracy": report["classification"][
                    "evaluation"
                ]["positive_action_accuracy"],
                "output_dir": report["output_dir"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
