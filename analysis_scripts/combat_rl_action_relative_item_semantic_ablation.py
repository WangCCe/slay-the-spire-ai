"""Run one source-committed item-semantic selective-classifier ablation."""

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
    FIXED_RECIPE as BASE_RECIPE,
    _selection_exact,
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
EXPERIMENT_ID = "combat-rl-action-relative-item-semantic-ablation-20260829-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
OUTPUT_DIR = REPORTS_ROOT / "combat_rl_action_relative_item_semantic_ablation_20260829_r1"
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_item_semantic_ablation.py",
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
        / "combat_rl_guard_advantage_corpus_20260828_r1"
        / "train_corpus.pt",
        "sha256": "ca7851f6f30846e5670f828c083413c9d653629c16748feb27c7d09aeeae7144",
    },
    "evaluation_corpus": {
        "path": REPORTS_ROOT
        / "combat_rl_guard_advantage_corpus_20260828_r1"
        / "evaluation_corpus.pt",
        "sha256": "219392d1e1d22d98bf1156c0d432275c73645658b331b4f0e85abc47b37c15c0",
    },
    "predecessor_report": {
        "path": REPORTS_ROOT
        / "combat_rl_action_relative_selective_classifier_fit_20260829_r1"
        / "report.json",
        "sha256": "e6b5a08ea89fa0519363c373e0e4ae3b90f2fa370c5bc28909d9d48d2318d1be",
    },
}

FIXED_RECIPE = {
    **copy.deepcopy(BASE_RECIPE),
    "architecture": "frozen_parent_action_relative_item_semantic_three_class_classifier",
    "include_item_semantics": True,
    "comparison_status": "consumed_development_comparison",
}

FIXED_DEVELOPMENT_GATES = {
    "minimum_intervention_count": 30,
    "minimum_intervention_precision": 0.55,
    "maximum_severe_harm_count": 5,
    "minimum_mean_selected_true_advantage_exclusive": 0.17321939766407013,
    "maximum_mean_policy_regret_exclusive": 3.1967246532440186,
    "illegal_action_count_zero": True,
    "forbidden_action_selection_count_zero": True,
}

PREDECESSOR_METRICS = {
    "intervention_count": 88,
    "intervention_precision": 0.46590909361839294,
    "mean_selected_true_advantage": 0.17321939766407013,
    "severe_harm_count": 19,
    "mean_policy_regret": 3.1967246532440186,
}

RESULT_AUTHORITY = {
    "development_ablation": True,
    "consumed_development_comparison": True,
    "fresh_corpus_authorized": False,
    "native_loading": False,
    "lightspeed": False,
    "gameplay": False,
    "communication_mod": False,
    "qualification": False,
    "promotion": False,
}


def validate_predecessor_report(report: Mapping[str, Any]) -> dict[str, Any]:
    if report.get("decision") != "offline_failed_close_without_fresh_gate_or_sweep":
        raise ValueError("item-semantic predecessor decision differs")
    selection = report.get("evaluation", {}).get("selection", {})
    ranking = report.get("evaluation", {}).get("ranking", {})
    observed = {
        "intervention_count": selection.get("intervention_count"),
        "intervention_precision": selection.get("intervention_precision"),
        "mean_selected_true_advantage": selection.get(
            "mean_selected_true_advantage"
        ),
        "severe_harm_count": selection.get("severe_harm_count"),
        "mean_policy_regret": ranking.get("mean_policy_regret"),
    }
    if observed != PREDECESSOR_METRICS:
        raise ValueError("item-semantic predecessor metrics differ")
    return observed


def apply_development_gates(metrics: Mapping[str, Any]) -> dict[str, Any]:
    selection = metrics["selection"]
    ranking = metrics["ranking"]
    conditions = {
        "minimum_intervention_count": int(selection["intervention_count"])
        >= FIXED_DEVELOPMENT_GATES["minimum_intervention_count"],
        "minimum_intervention_precision": float(selection["intervention_precision"])
        >= FIXED_DEVELOPMENT_GATES["minimum_intervention_precision"],
        "maximum_severe_harm_count": int(selection["severe_harm_count"])
        <= FIXED_DEVELOPMENT_GATES["maximum_severe_harm_count"],
        "minimum_mean_selected_true_advantage_exclusive": float(
            selection["mean_selected_true_advantage"]
        )
        > FIXED_DEVELOPMENT_GATES[
            "minimum_mean_selected_true_advantage_exclusive"
        ],
        "maximum_mean_policy_regret_exclusive": float(ranking["mean_policy_regret"])
        < FIXED_DEVELOPMENT_GATES["maximum_mean_policy_regret_exclusive"],
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
            "item_semantics_promising_propose_fresh_corpus"
            if passed
            else "item_semantics_failed_close_without_fresh_corpus"
        ),
    }


def _validated_source_commit(source_commit: str) -> str:
    source_commit = _validate_commit(source_commit)
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, _current_commit()],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("item-semantic source commit is not an ancestor of HEAD")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", source_commit, "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"item-semantic source changed after commit: {relative}")
    return source_commit


def _validated_inputs() -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in FIXED_INPUTS.items():
        path = Path(binding["path"]).resolve()
        if not path.is_file():
            raise ValueError(f"item-semantic fixed input is unavailable: {name}")
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"item-semantic fixed input hash differs: {name}")
        paths[name] = path
    staging = OUTPUT_DIR.with_name(f".{OUTPUT_DIR.name}.staging")
    if OUTPUT_DIR.exists() or staging.exists():
        raise ValueError("item-semantic output or staging already exists")
    return paths


def _render_summary(report: Mapping[str, Any]) -> str:
    selection = report["comparison"]["selection"]
    ranking = report["comparison"]["ranking"]
    return (
        "# Action-Relative Item-Semantic Ablation\n\n"
        "- Comparison status: consumed development comparison\n"
        f"- Interventions: {selection['intervention_count']}\n"
        f"- Precision: {selection['intervention_precision']:.6f}\n"
        f"- Mean selected advantage: {selection['mean_selected_true_advantage']:.6f}\n"
        f"- Mean policy regret: {ranking['mean_policy_regret']:.6f}\n"
        f"- Severe harms: {selection['severe_harm_count']}\n"
        f"- Decision: {report['decision']}\n"
    )


def run(*, source_commit: str) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("item-semantic ablation must use the Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("item-semantic ablation must run in isolated mode")
    source_commit = _validated_source_commit(source_commit)
    paths = _validated_inputs()
    predecessor = json.loads(paths["predecessor_report"].read_text(encoding="ascii"))
    predecessor_metrics = validate_predecessor_report(predecessor)

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
    split = split_selective_corpus(
        train["tensors"],
        train["metadata"],
        fit_seeds=frozenset(
            range(
                int(FIXED_RECIPE["fit_seed_first"]),
                int(FIXED_RECIPE["fit_seed_last"]) + 1,
            )
        ),
        calibration_seeds=frozenset(
            range(
                int(FIXED_RECIPE["calibration_seed_first"]),
                int(FIXED_RECIPE["calibration_seed_last"]) + 1,
            )
        ),
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
    comparison_corpus = load_corpus(
        paths["evaluation_corpus"], expected_partition="evaluation"
    )
    comparison = evaluate_selective_corpus(
        classifier,
        comparison_corpus["tensors"],
        comparison_corpus["metadata"],
        forbidden_action_indices=FIXED_RECIPE["forbidden_action_indices"],
        severe_harm_floor=-0.5,
    )
    development_gate = apply_development_gates(comparison)
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
            "consumed_development_comparison": comparison,
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
        comparison_corpus["tensors"],
        comparison_corpus["metadata"],
        FIXED_RECIPE["forbidden_action_indices"],
    ):
        raise RuntimeError("item-semantic artifact roundtrip changed policy")

    source_hashes = {
        relative: sha256_file(REPO_ROOT / relative)
        for relative in SOURCE_SNAPSHOT_PATHS
    }
    report = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "execution_commit": _current_commit(),
        "source_files": source_hashes,
        "inputs": {
            name: {"path": str(path), "sha256": FIXED_INPUTS[name]["sha256"]}
            for name, path in paths.items()
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "development_gates": copy.deepcopy(FIXED_DEVELOPMENT_GATES),
        "predecessor_metrics": predecessor_metrics,
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
        "calibration": calibration,
        "comparison_status": "consumed_development_comparison",
        "comparison": comparison,
        "development_gate": development_gate,
        "artifact_roundtrip_exact": True,
        "parameter_sweep": False,
        "decision": development_gate["decision"],
        "output_dir": str(OUTPUT_DIR),
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }
    staging = OUTPUT_DIR.with_name(f".{OUTPUT_DIR.name}.staging")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        artifact_path = staging / "item_semantic_selective_classifier_development.pth"
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
