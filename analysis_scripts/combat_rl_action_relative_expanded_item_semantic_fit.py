"""Fit one item-semantic classifier on the expanded paired-return corpus."""

from __future__ import annotations

import argparse
import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, Mapping

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
from analysis_scripts.combat_rl_action_relative_selective_classifier_fit import (  # noqa: E402
    FIXED_OFFLINE_GATES as BASE_OFFLINE_GATES,
    FIXED_RECIPE as BASE_RECIPE,
    _selection_exact,
    apply_offline_gates as _apply_base_offline_gates,
    calibrate_threshold,
    evaluate_selective_corpus,
    fit_selective_classifier,
    split_selective_corpus,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    _canonical_json_bytes,
    _current_commit,
    _trainer_metadata,
    _validate_commit,
    load_corpus,
    sha256_file,
)
from spirecomm.ai.rl.v2.action_relative_selective_classifier import (  # noqa: E402
    build_selective_development_artifact,
    load_selective_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-action-relative-expanded-item-semantic-fit-20260829-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
OUTPUT_DIR = REPORTS_ROOT / EXPERIMENT_ID.replace("-", "_")
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_expanded_item_semantic_fit.py",
    "analysis_scripts/combat_rl_action_relative_selective_classifier_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "spirecomm/ai/rl/v2/action_relative_selective_classifier.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/action_space.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
    "spirecomm/ai/rl/v2/network.py",
)

FIXED_INPUTS = {
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
        / "combat_rl_guard_advantage_expanded_corpus_20260829_r1"
        / "train_corpus.pt",
        "sha256": "90f3e83763f2591065380e89b24ebbedc7bbc3ef529a749b0cbb54a2dab2fa1f",
    },
    "evaluation_corpus": {
        "path": REPORTS_ROOT
        / "combat_rl_guard_advantage_expanded_corpus_20260829_r1"
        / "evaluation_corpus.pt",
        "sha256": "028d51871b12fd509b87b6d45adb161b399a29c34782b30b28f66c0a97e48e58",
    },
    "corpus_report": {
        "path": REPORTS_ROOT
        / "combat_rl_guard_advantage_expanded_corpus_20260829_r1"
        / "report.json",
        "sha256": "5993832214c60dbfd275f7dc10109fb127454f8a989aedec20252693c4077325",
    },
}

FIXED_RECIPE = copy.deepcopy(BASE_RECIPE)
FIXED_RECIPE.update(
    {
        "architecture": "frozen_parent_action_relative_item_semantic_three_class_classifier",
        "include_item_semantics": True,
        "fit_seed_first": 264000,
        "fit_seed_last": 264767,
        "calibration_seed_first": 264768,
        "calibration_seed_last": 265023,
        "fresh_evaluation_seed_first": 266000,
        "fresh_evaluation_seed_last": 266255,
    }
)
FIXED_OFFLINE_GATES = copy.deepcopy(BASE_OFFLINE_GATES)

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


def apply_offline_gates(metrics: Mapping[str, Any]) -> dict[str, Any]:
    result = _apply_base_offline_gates(metrics)
    if result["all_conditions_passed"]:
        result["decision"] = "offline_passed_propose_fresh_lightspeed_gate"
    return result


def validate_corpus_report(report: Mapping[str, Any]) -> dict[str, Any]:
    config = report.get("config", {})
    train_seeds = list(range(264000, 265024))
    evaluation_seeds = list(range(266000, 266256))
    conditions = {
        "schema": report.get("schema_version") == 1,
        "kind": report.get("corpus_kind") == "combat_guard_advantage_corpus",
        "train_seeds": config.get("train_seeds") == train_seeds,
        "evaluation_seeds": config.get("evaluation_seeds") == evaluation_seeds,
        "battle_indices": config.get("battle_indices") == [0, 3, 6, 9],
        "max_states_per_profile": config.get("max_states_per_profile") == 2,
        "sufficient": report.get("sufficiency", {}).get("all_conditions_passed")
        is True,
        "train_rows": report.get("partitions", {})
        .get("train", {})
        .get("retained_state_count")
        == 6473,
        "evaluation_rows": report.get("partitions", {})
        .get("evaluation", {})
        .get("retained_state_count")
        == 1643,
        "no_game_authority": report.get("authority", {}).get("gameplay") is False
        and report.get("authority", {}).get("communication_mod") is False,
    }
    if not all(conditions.values()):
        raise ValueError("expanded corpus report binding differs")
    return conditions


def _validated_source_commit(source_commit: str) -> str:
    source_commit = _validate_commit(source_commit)
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, _current_commit()],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("expanded item-semantic source commit is not an ancestor")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", source_commit, "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"expanded item-semantic source changed: {relative}")
    return source_commit


def _validated_inputs() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in FIXED_INPUTS.items():
        path = Path(binding["path"]).resolve()
        if not path.is_file():
            raise ValueError(f"expanded item-semantic input is unavailable: {name}")
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"expanded item-semantic input hash differs: {name}")
        paths[name] = path
    staging = OUTPUT_DIR.with_name(f".{OUTPUT_DIR.name}.staging")
    if OUTPUT_DIR.exists() or staging.exists():
        raise ValueError("expanded item-semantic output or staging already exists")
    return paths


def _validate_seed_coverage(
    corpus: Mapping[str, Any], *, first: int, last: int, label: str
) -> dict[str, int]:
    observed = {int(row["seed"]) for row in corpus["metadata"]}
    expected = set(range(first, last + 1))
    if observed != expected:
        raise ValueError(f"expanded item-semantic {label} seed coverage differs")
    return {
        "seed_first": first,
        "seed_last": last,
        "seed_count": len(observed),
        "row_count": int(corpus["row_count"]),
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    selection = report["evaluation"]["selection"]
    ranking = report["evaluation"]["ranking"]
    return (
        "# Expanded Item-Semantic Selective Classifier Fit\n\n"
        f"- Fit rows: {report['split']['fit']['source_row_count']}\n"
        f"- Calibration rows: {report['split']['calibration']['source_row_count']}\n"
        f"- Fresh interventions: {selection['intervention_count']}\n"
        f"- Fresh precision: {selection['intervention_precision']:.6f}\n"
        f"- Mean selected advantage: {selection['mean_selected_true_advantage']:.6f}\n"
        f"- Mean policy regret: {ranking['mean_policy_regret']:.6f}\n"
        f"- Severe harms: {selection['severe_harm_count']}\n"
        f"- Decision: {report['decision']}\n"
    )


def run(*, source_commit: str) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("expanded item-semantic fit must use the Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("expanded item-semantic fit must run in isolated mode")
    source_commit = _validated_source_commit(source_commit)
    paths = _validated_inputs()
    corpus_report = json.loads(paths["corpus_report"].read_text(encoding="ascii"))
    corpus_conditions = validate_corpus_report(corpus_report)

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
    metadata = _trainer_metadata(trainer)

    train = load_corpus(paths["train_corpus"], expected_partition="train")
    train_coverage = _validate_seed_coverage(
        train, first=264000, last=265023, label="train"
    )
    split = split_selective_corpus(
        train["tensors"],
        train["metadata"],
        fit_seeds=frozenset(range(264000, 264768)),
        calibration_seeds=frozenset(range(264768, 265024)),
    )
    classifier, fit = fit_selective_classifier(
        parent=parent,
        metadata=metadata,
        corpus=split["fit"]["corpus"],
        recipe=FIXED_RECIPE,
    )
    classifier, calibration = calibrate_threshold(
        classifier,
        split["calibration"]["corpus"],
        quantile=float(FIXED_RECIPE["calibration_quantile"]),
    )

    evaluation = load_corpus(
        paths["evaluation_corpus"], expected_partition="evaluation"
    )
    evaluation_coverage = _validate_seed_coverage(
        evaluation, first=266000, last=266255, label="evaluation"
    )
    forbidden = FIXED_RECIPE["forbidden_action_indices"]
    severe_floor = float(FIXED_OFFLINE_GATES["severe_harm_floor"])
    fit_metrics = evaluate_selective_corpus(
        classifier,
        split["fit"]["corpus"]["tensors"],
        split["fit"]["corpus"]["metadata"],
        forbidden_action_indices=forbidden,
        severe_harm_floor=severe_floor,
    )
    calibration_metrics = evaluate_selective_corpus(
        classifier,
        split["calibration"]["corpus"]["tensors"],
        split["calibration"]["corpus"]["metadata"],
        forbidden_action_indices=forbidden,
        severe_harm_floor=severe_floor,
    )
    evaluation_metrics = evaluate_selective_corpus(
        classifier,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden_action_indices=forbidden,
        severe_harm_floor=severe_floor,
    )
    offline_gate = apply_offline_gates(evaluation_metrics)
    split_hashes = {
        name: split[name]["split_sha256"] for name in ("fit", "calibration")
    }
    corpus_hashes = {
        "train": FIXED_INPUTS["train_corpus"]["sha256"],
        "evaluation": FIXED_INPUTS["evaluation_corpus"]["sha256"],
    }
    artifact = build_selective_development_artifact(
        classifier,
        parent_checkpoint_sha256=FIXED_INPUTS["parent_checkpoint"]["sha256"],
        corpus_sha256=corpus_hashes,
        recipe=FIXED_RECIPE,
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
        expected_parent_checkpoint_sha256=FIXED_INPUTS["parent_checkpoint"][
            "sha256"
        ],
        expected_corpus_sha256=corpus_hashes,
        expected_recipe=FIXED_RECIPE,
        expected_split_sha256=split_hashes,
        expected_sampling_plan_sha256=fit["sampling_plan_sha256"],
    )
    if not _selection_exact(
        classifier,
        restored,
        evaluation["tensors"],
        evaluation["metadata"],
        forbidden,
    ):
        raise RuntimeError("expanded item-semantic artifact roundtrip changed policy")

    report = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "execution_commit": _current_commit(),
        "source_files": {
            relative: sha256_file(REPO_ROOT / relative)
            for relative in SOURCE_SNAPSHOT_PATHS
        },
        "inputs": {
            name: {"path": str(path), "sha256": FIXED_INPUTS[name]["sha256"]}
            for name, path in paths.items()
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "offline_gates": copy.deepcopy(FIXED_OFFLINE_GATES),
        "corpus_report_conditions": corpus_conditions,
        "initialization": initialization,
        "parent_parameter_sha256": parameter_sha256(parent_state),
        "train_coverage": train_coverage,
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
            **evaluation_coverage,
            "loaded_after_fit_and_calibration": True,
            "seed_disjoint": True,
            "untouched_before_evaluation": True,
        },
        "offline_gate": offline_gate,
        "artifact_roundtrip_exact": True,
        "parameter_sweep": False,
        "decision": offline_gate["decision"],
        "output_dir": str(OUTPUT_DIR),
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }
    staging = OUTPUT_DIR.with_name(f".{OUTPUT_DIR.name}.staging")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = staging / "expanded_item_semantic_selective_classifier.pth"
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
        os.replace(staging, OUTPUT_DIR)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-commit", required=True)
    arguments = parser.parse_args()
    report = run(source_commit=arguments.source_commit)
    print(json.dumps({"decision": report["decision"], "output_dir": report["output_dir"]}))


if __name__ == "__main__":
    main()
