"""Run one fresh three-arm EndTurn safety ablation for a post-guard residual."""

from __future__ import annotations

import argparse
import copy
import hashlib
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

from analysis_scripts.combat_lightspeed_bridge import load_native_module  # noqa: E402
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    SmokeConfig,
    create_fresh_trainer,
    evaluate_policy,
    initialize_trainer,
    load_initial_checkpoint,
    paired_evaluation,
    parameter_sha256,
)
from analysis_scripts.combat_rl_guard_advantage_residual_evaluation import (  # noqa: E402
    evaluate_residual_policy,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    _current_commit,
    _trainer_metadata,
    _validate_commit,
    _validate_file_binding,
    sha256_file,
)
from spirecomm.ai.rl.v2.guard_advantage_residual import (  # noqa: E402
    load_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-guard-residual-end-turn-safety-ablation-20260828-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
END_TURN_ACTION = 90
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_guard_residual_end_turn_safety_ablation.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_evaluation.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_corpus.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "analysis_scripts/combat_lightspeed_bridge.py",
    "spirecomm/ai/rl/v2/guard_advantage_residual.py",
)

FIXED_RECIPE = {
    "seed_first": 265000,
    "seed_last": 265255,
    "battle_indices": [0, 3, 6, 9],
    "ascension": 0,
    "max_decisions_per_profile": 100,
    "max_actions_per_turn": 8,
    "max_canonical_actions": 8,
    "masked_forbidden_residual_action_indices": [END_TURN_ACTION],
    "deployment_guard_proxy": GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    "device": "cpu",
}

FIXED_ABLATION_GATES = {
    "unrestricted_end_turn_intervention_count_positive": True,
    "masked_end_turn_intervention_count_zero": True,
    "masked_forbidden_action_intervention_count_zero": True,
    "masked_candidate_only_victories_at_least_control_only": True,
    "masked_mean_reward_delta_non_negative": True,
    "masked_mean_player_hp_delta_non_negative": True,
    "masked_control_nonterminal_profile_count_zero": True,
    "masked_residual_intervention_count_positive": True,
    "masked_only_victories_at_least_unrestricted_only": True,
    "masked_minus_unrestricted_mean_reward_non_negative": True,
    "masked_minus_unrestricted_mean_player_hp_non_negative": True,
    "direct_ablation_nonterminal_profile_count_zero": True,
}

REGISTERED_AUTHORITY = {
    "cpu_evaluation": True,
    "native_loading": True,
    "gameplay": False,
    "communication_mod": False,
    "model_fitting": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}

RESULT_AUTHORITY = {
    "simulator_safety_ablation": True,
    "gameplay": False,
    "communication_mod": False,
    "model_fitting": False,
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


def validate_registration_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "experiment_id",
        "source_commit",
        "runner",
        "source_files",
        "inputs",
        "recipe",
        "ablation_gates",
        "output_dir",
        "authority",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("EndTurn ablation registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("EndTurn ablation registration schema differs")
    if payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("EndTurn ablation experiment id differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    sources = payload["source_files"]
    if not isinstance(sources, Mapping):
        raise ValueError("EndTurn ablation source files are missing")
    normalized_sources: dict[str, str] = {}
    for raw_path, raw_hash in sources.items():
        if not isinstance(raw_path, str):
            raise ValueError("EndTurn ablation source path is invalid")
        path = Path(raw_path)
        if not raw_path or path.is_absolute() or ".." in path.parts:
            raise ValueError("EndTurn ablation source path is invalid")
        normalized_path = raw_path.replace("\\", "/")
        normalized_sources[normalized_path] = _validate_file_binding(
            {"path": normalized_path, "sha256": raw_hash},
            label=f"source file {raw_path}",
        )["sha256"]
    if set(normalized_sources) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("EndTurn ablation source inventory differs")
    if Path(runner["path"]).resolve() != (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve():
        raise ValueError("EndTurn ablation runner path differs")
    if runner["sha256"] != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("EndTurn ablation runner hash differs")
    expected_inputs = {
        "native_module",
        "items_json",
        "parent_checkpoint",
        "residual_artifact",
        "train_corpus",
        "evaluation_corpus",
    }
    inputs = payload["inputs"]
    if not isinstance(inputs, Mapping) or set(inputs) != expected_inputs:
        raise ValueError("EndTurn ablation inputs differ")
    normalized_inputs = {
        name: _validate_file_binding(inputs[name], label=name)
        for name in sorted(expected_inputs)
    }
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("EndTurn ablation fixed recipe differs")
    if payload["ablation_gates"] != FIXED_ABLATION_GATES:
        raise ValueError("EndTurn ablation gates differ")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("EndTurn ablation authority differs")
    output = payload["output_dir"]
    if not isinstance(output, str) or not Path(output).is_absolute():
        raise ValueError("EndTurn ablation output path must be absolute")
    output_path = Path(output).resolve()
    try:
        output_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("EndTurn ablation output path is outside reports") from exc
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "runner": runner,
        "source_files": normalized_sources,
        "inputs": normalized_inputs,
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "ablation_gates": copy.deepcopy(FIXED_ABLATION_GATES),
        "output_dir": str(output_path),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def load_committed_registration(path: Path) -> tuple[dict[str, Any], str]:
    relative = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    committed = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=REPO_ROOT)
    registration = validate_registration_payload(json.loads(committed))
    if path.read_bytes() != committed:
        raise ValueError("working EndTurn ablation registration differs from committed data")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", registration["source_commit"], _current_commit()],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("EndTurn ablation source commit is not an ancestor of HEAD")
    for relative_path in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", registration["source_commit"], "--", relative_path],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"EndTurn ablation source changed: {relative_path}")
    return registration, hashlib.sha256(committed).hexdigest()


def _execution_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"])
        if not path.is_absolute() or not path.is_file():
            raise ValueError(f"registered EndTurn ablation {name} path is unavailable")
        path = path.resolve()
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"registered EndTurn ablation {name} hash differs")
        result[name] = path
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("EndTurn ablation output or staging already exists")
    result["output_dir"] = output
    return result


def apply_ablation_gates(
    *,
    unrestricted: Mapping[str, Any],
    masked: Mapping[str, Any],
    control_to_masked: Mapping[str, Any],
    unrestricted_to_masked: Mapping[str, Any],
) -> dict[str, Any]:
    unrestricted_aggregate = unrestricted["aggregate"]
    masked_aggregate = masked["aggregate"]
    control_pair = control_to_masked["aggregate"]
    direct_pair = unrestricted_to_masked["aggregate"]
    conditions = {
        "unrestricted_end_turn_intervention_count_positive": int(
            unrestricted_aggregate["residual_end_turn_intervention_count"]
        )
        > 0,
        "masked_end_turn_intervention_count_zero": int(
            masked_aggregate["residual_end_turn_intervention_count"]
        )
        == 0,
        "masked_forbidden_action_intervention_count_zero": int(
            masked_aggregate["residual_forbidden_action_intervention_count"]
        )
        == 0,
        "masked_candidate_only_victories_at_least_control_only": int(
            control_pair["candidate_only_victories"]
        )
        >= int(control_pair["control_only_victories"]),
        "masked_mean_reward_delta_non_negative": float(
            control_pair["mean_reward_delta"]
        )
        >= 0.0,
        "masked_mean_player_hp_delta_non_negative": float(
            control_pair["mean_player_hp_delta"]
        )
        >= 0.0,
        "masked_control_nonterminal_profile_count_zero": int(
            control_pair["excluded_nonterminal_profile_count"]
        )
        == 0,
        "masked_residual_intervention_count_positive": int(
            masked_aggregate["residual_intervention_count"]
        )
        > 0,
        "masked_only_victories_at_least_unrestricted_only": int(
            direct_pair["candidate_only_victories"]
        )
        >= int(direct_pair["control_only_victories"]),
        "masked_minus_unrestricted_mean_reward_non_negative": float(
            direct_pair["mean_reward_delta"]
        )
        >= 0.0,
        "masked_minus_unrestricted_mean_player_hp_non_negative": float(
            direct_pair["mean_player_hp_delta"]
        )
        >= 0.0,
        "direct_ablation_nonterminal_profile_count_zero": int(
            direct_pair["excluded_nonterminal_profile_count"]
        )
        == 0,
    }
    if set(conditions) != set(FIXED_ABLATION_GATES):
        raise RuntimeError("EndTurn ablation condition inventory differs")
    passed = all(conditions.values())
    return {
        "conditions": conditions,
        "all_conditions_passed": passed,
        "decision": (
            "end_turn_mask_simulator_promising_for_separate_divergence_calibration"
            if passed
            else "end_turn_safety_hypothesis_failed_close_without_second_ablation"
        ),
    }


def _write_trace(path: Path, rows: list[dict[str, Any]]) -> dict[str, Any]:
    with path.open("wb") as stream:
        for row in rows:
            stream.write(
                json.dumps(row, sort_keys=True, separators=(",", ":")).encode("ascii")
                + b"\n"
            )
    return {
        "path": path.name,
        "row_count": len(rows),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _arm_without_trace(arm: Mapping[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in arm.items() if key != "decision_trace"}


def _render_summary(report: Mapping[str, Any]) -> str:
    control_pair = report["paired"]["control_to_masked"]["aggregate"]
    direct_pair = report["paired"]["unrestricted_to_masked"]["aggregate"]
    unrestricted = report["arms"]["unrestricted"]["aggregate"]
    masked = report["arms"]["masked"]["aggregate"]
    return (
        "# Post-Guard EndTurn Safety Ablation\n\n"
        f"- Unrestricted EndTurn interventions: {unrestricted['residual_end_turn_intervention_count']}\n"
        f"- Masked EndTurn interventions: {masked['residual_end_turn_intervention_count']}\n"
        f"- Masked vs control pair wins: {control_pair['candidate_only_victories']}:{control_pair['control_only_victories']}\n"
        f"- Masked vs control reward delta: {control_pair['mean_reward_delta']:.6f}\n"
        f"- Masked vs control HP delta: {control_pair['mean_player_hp_delta']:.6f}\n"
        f"- Masked vs unrestricted pair wins: {direct_pair['candidate_only_victories']}:{direct_pair['control_only_victories']}\n"
        f"- Masked minus unrestricted reward delta: {direct_pair['mean_reward_delta']:.6f}\n"
        f"- Masked minus unrestricted HP delta: {direct_pair['mean_player_hp_delta']:.6f}\n"
        f"- Decision: {report['ablation_gate']['decision']}\n"
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("EndTurn ablation must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("EndTurn ablation must run in isolated -I mode")
    registration, registration_sha256 = load_committed_registration(registration_path)
    paths = _execution_paths(registration)
    recipe = registration["recipe"]
    seeds = tuple(range(int(recipe["seed_first"]), int(recipe["seed_last"]) + 1))
    id_mapper = build_id_mapper(paths["items_json"])
    initial_checkpoint = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        id_mapper, seed=2026082824, batch_size=64, learning_starts=64
    )
    parent_state, initialization = initialize_trainer(trainer, initial_checkpoint)
    trainer.online_network.eval()
    artifact = torch.load(
        paths["residual_artifact"], map_location="cpu", weights_only=False
    )
    residual = load_development_artifact(
        trainer.online_network,
        _trainer_metadata(trainer),
        artifact,
        expected_parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        expected_corpus_sha256={
            "train": registration["inputs"]["train_corpus"]["sha256"],
            "evaluation": registration["inputs"]["evaluation_corpus"]["sha256"],
        },
    )
    native_module = load_native_module(paths["native_module"])
    config = SmokeConfig(
        train_seeds=(int(recipe["seed_first"]) - 1,),
        evaluation_seeds=seeds,
        battle_indices=tuple(int(value) for value in recipe["battle_indices"]),
        ascension=int(recipe["ascension"]),
        max_decisions_per_seed=int(recipe["max_decisions_per_profile"]),
        max_actions_per_turn=int(recipe["max_actions_per_turn"]),
        batch_size=64,
        optimizer_steps=1,
        deployment_guard_proxy=str(recipe["deployment_guard_proxy"]),
    )
    config.validate()
    control = evaluate_policy(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        seeds=seeds,
        config=config,
    )
    unrestricted = evaluate_residual_policy(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        residual=residual,
        seeds=seeds,
        config=config,
        max_canonical_actions=int(recipe["max_canonical_actions"]),
    )
    masked = evaluate_residual_policy(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        residual=residual,
        seeds=seeds,
        config=config,
        max_canonical_actions=int(recipe["max_canonical_actions"]),
        forbidden_residual_action_indices=frozenset(
            int(value)
            for value in recipe["masked_forbidden_residual_action_indices"]
        ),
    )
    paired = {
        "control_to_unrestricted": paired_evaluation(control, unrestricted),
        "control_to_masked": paired_evaluation(control, masked),
        "unrestricted_to_masked": paired_evaluation(unrestricted, masked),
    }
    ablation_gate = apply_ablation_gates(
        unrestricted=unrestricted,
        masked=masked,
        control_to_masked=paired["control_to_masked"],
        unrestricted_to_masked=paired["unrestricted_to_masked"],
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
        "arms": {
            "control": control,
            "unrestricted": _arm_without_trace(unrestricted),
            "masked": _arm_without_trace(masked),
        },
        "paired": paired,
        "ablation_gate": ablation_gate,
        "output_dir": str(paths["output_dir"]),
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }
    output = paths["output_dir"]
    staging = output.with_name(f".{output.name}.staging")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        report["decision_traces"] = {
            "unrestricted": _write_trace(
                staging / "unrestricted_decision_trace.jsonl",
                unrestricted["decision_trace"],
            ),
            "masked": _write_trace(
                staging / "masked_decision_trace.jsonl",
                masked["decision_trace"],
            ),
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
    args = parser.parse_args()
    report = run(args.registration)
    print(
        json.dumps(
            {
                "decision": report["ablation_gate"]["decision"],
                "masked_end_turn_interventions": report["arms"]["masked"][
                    "aggregate"
                ]["residual_end_turn_intervention_count"],
                "output_dir": report["output_dir"],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
