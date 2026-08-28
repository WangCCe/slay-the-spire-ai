"""Run one registered fresh LightSTS gate for an action-relative residual."""

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
from typing import Any, Mapping, NamedTuple

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
from analysis_scripts.combat_rl_action_relative_advantage_residual_fit import (  # noqa: E402
    FIXED_RECIPE as FIXED_FIT_RECIPE,
)
from analysis_scripts.combat_rl_guard_advantage_residual_evaluation import (  # noqa: E402
    evaluate_residual_policy,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    _canonical_json_bytes,
    _current_commit,
    _trainer_metadata,
    _validate_commit,
    _validate_file_binding,
    sha256_file,
)
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (  # noqa: E402
    ActionRelativeAdvantageResidual,
    load_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-action-relative-advantage-residual-evaluation-20260828-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_advantage_residual_evaluation.py",
    "analysis_scripts/combat_rl_action_relative_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_evaluation.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_corpus.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "analysis_scripts/combat_lightspeed_bridge.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/network.py",
)

FIXED_RECIPE = {
    "seed_first": 266000,
    "seed_last": 266255,
    "battle_indices": [0, 3, 6, 9],
    "ascension": 0,
    "max_decisions_per_profile": 100,
    "max_actions_per_turn": 8,
    "max_canonical_actions": 8,
    "deployment_guard_proxy": GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    "trainer_seed": 2026082824,
    "forbidden_action_indices": [90],
    "device": "cpu",
}

FIXED_POLICY_GATES = {
    "candidate_only_victories_at_least_control_only": True,
    "mean_reward_delta_non_negative": True,
    "mean_player_hp_delta_non_negative": True,
    "excluded_nonterminal_profile_count_zero": True,
    "residual_intervention_count_positive": True,
    "forbidden_action_intervention_count_zero": True,
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
    "simulator_policy_evidence": True,
    "gameplay": False,
    "communication_mod": False,
    "model_fitting": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}


class CompatibleSelection(NamedTuple):
    actions: torch.Tensor
    residual_actions: torch.Tensor
    gate_probabilities: torch.Tensor
    gate_open: torch.Tensor


class ActionRelativeEvaluationAdapter:
    """Expose action-relative predictions to the established policy loop."""

    def __init__(self, residual: ActionRelativeAdvantageResidual) -> None:
        self.residual = residual

    def eval(self) -> "ActionRelativeEvaluationAdapter":
        self.residual.eval()
        return self

    def select_actions(self, *args: Any, **kwargs: Any) -> CompatibleSelection:
        selection = self.residual.select_actions(*args, **kwargs)
        return CompatibleSelection(
            actions=selection.actions,
            residual_actions=selection.residual_actions,
            gate_probabilities=selection.predicted_advantages,
            gate_open=selection.gate_open,
        )


def validate_registration_payload(payload: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "experiment_id",
        "source_commit",
        "runner",
        "source_files",
        "inputs",
        "recipe",
        "policy_gates",
        "output_dir",
        "authority",
    }
    if not isinstance(payload, Mapping) or set(payload) != required:
        raise ValueError("action-relative evaluation registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("action-relative evaluation registration schema differs")
    if payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("action-relative evaluation experiment id differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    source_files = payload["source_files"]
    if not isinstance(source_files, Mapping):
        raise ValueError("action-relative evaluation source files are missing")
    normalized_sources: dict[str, str] = {}
    for raw_path, raw_hash in source_files.items():
        if not isinstance(raw_path, str):
            raise ValueError("action-relative evaluation source path is invalid")
        path = Path(raw_path)
        if not raw_path or path.is_absolute() or ".." in path.parts:
            raise ValueError("action-relative evaluation source path is invalid")
        normalized_path = raw_path.replace("\\", "/")
        normalized_hash = str(raw_hash).lower()
        if len(normalized_hash) != 64 or any(
            character not in "0123456789abcdef" for character in normalized_hash
        ):
            raise ValueError("action-relative evaluation source hash is invalid")
        normalized_sources[normalized_path] = normalized_hash
    if set(normalized_sources) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("action-relative evaluation source inventory differs")
    if Path(runner["path"]).resolve() != (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve():
        raise ValueError("action-relative evaluation runner path differs")
    if runner["sha256"] != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("action-relative evaluation runner hash differs")
    expected_inputs = {
        "native_module",
        "items_json",
        "parent_checkpoint",
        "residual_artifact",
        "residual_fit_report",
        "train_corpus",
        "evaluation_corpus",
    }
    inputs = payload["inputs"]
    if not isinstance(inputs, Mapping) or set(inputs) != expected_inputs:
        raise ValueError("action-relative evaluation inputs differ")
    normalized_inputs = {
        name: _validate_file_binding(inputs[name], label=name)
        for name in sorted(expected_inputs)
    }
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("action-relative evaluation fixed recipe differs")
    if payload["policy_gates"] != FIXED_POLICY_GATES:
        raise ValueError("action-relative evaluation policy gates differ")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("action-relative evaluation authority differs")
    output = payload["output_dir"]
    if not isinstance(output, str) or not Path(output).is_absolute():
        raise ValueError("action-relative evaluation output path must be absolute")
    output_path = Path(output).resolve()
    try:
        output_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("action-relative evaluation output path is outside reports") from exc
    if output_path == REPORTS_ROOT.resolve():
        raise ValueError("action-relative evaluation output cannot be reports root")
    return {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "runner": runner,
        "source_files": normalized_sources,
        "inputs": normalized_inputs,
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "policy_gates": copy.deepcopy(FIXED_POLICY_GATES),
        "output_dir": str(output_path),
        "authority": copy.deepcopy(REGISTERED_AUTHORITY),
    }


def load_committed_registration(path: Path) -> tuple[dict[str, Any], str]:
    relative = path.resolve().relative_to(REPO_ROOT.resolve()).as_posix()
    committed = subprocess.check_output(["git", "show", f"HEAD:{relative}"], cwd=REPO_ROOT)
    registration = validate_registration_payload(json.loads(committed))
    if path.read_bytes() != committed:
        raise ValueError("working evaluation registration differs from committed data")
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", registration["source_commit"], _current_commit()],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("evaluation source commit is not an ancestor of HEAD")
    for relative_path in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", registration["source_commit"], "--", relative_path],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"evaluation source changed after registration: {relative_path}")
    return registration, hashlib.sha256(committed).hexdigest()


def _execution_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    result: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"])
        if not path.is_absolute() or not path.is_file():
            raise ValueError(f"registered evaluation {name} path is unavailable")
        path = path.resolve()
        if sha256_file(path) != binding["sha256"]:
            raise ValueError(f"registered evaluation {name} hash differs")
        result[name] = path
    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("action-relative evaluation output or staging already exists")
    result["output_dir"] = output
    return result


def apply_policy_gates(
    paired: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    paired_aggregate = paired["aggregate"]
    candidate_aggregate = candidate["aggregate"]
    conditions = {
        "candidate_only_victories_at_least_control_only": int(
            paired_aggregate["candidate_only_victories"]
        )
        >= int(paired_aggregate["control_only_victories"]),
        "mean_reward_delta_non_negative": float(
            paired_aggregate["mean_reward_delta"]
        )
        >= 0.0,
        "mean_player_hp_delta_non_negative": float(
            paired_aggregate["mean_player_hp_delta"]
        )
        >= 0.0,
        "excluded_nonterminal_profile_count_zero": int(
            paired_aggregate["excluded_nonterminal_profile_count"]
        )
        == 0,
        "residual_intervention_count_positive": int(
            candidate_aggregate["residual_intervention_count"]
        )
        > 0,
        "forbidden_action_intervention_count_zero": int(
            candidate_aggregate["residual_forbidden_action_intervention_count"]
        )
        == 0,
    }
    if set(conditions) != set(FIXED_POLICY_GATES):
        raise RuntimeError("action-relative policy condition inventory differs")
    passed = all(conditions.values())
    return {
        "conditions": conditions,
        "all_conditions_passed": passed,
        "decision": (
            "action_relative_residual_promising_for_separate_real_game_validation"
            if passed
            else "action_relative_residual_failed_close_without_sweep"
        ),
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    paired = report["paired"]["aggregate"]
    candidate = report["candidate"]["aggregate"]
    return (
        "# Action-Relative Residual Fresh Paired Gate\n\n"
        f"- Candidate-only victories: {paired['candidate_only_victories']}\n"
        f"- Control-only victories: {paired['control_only_victories']}\n"
        f"- Mean reward delta: {paired['mean_reward_delta']:.6f}\n"
        f"- Mean player HP delta: {paired['mean_player_hp_delta']:.6f}\n"
        f"- Residual interventions: {candidate['residual_intervention_count']}\n"
        f"- Forbidden interventions: {candidate['residual_forbidden_action_intervention_count']}\n"
        f"- Nonterminal exclusions: {paired['excluded_nonterminal_profile_count']}\n"
        f"- Decision: {report['policy_gate']['decision']}\n"
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("action-relative evaluation must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("action-relative evaluation must run in isolated -I mode")
    registration, registration_sha256 = load_committed_registration(registration_path)
    paths = _execution_paths(registration)
    recipe = registration["recipe"]
    fit_report = json.loads(paths["residual_fit_report"].read_text(encoding="ascii"))
    if fit_report.get("decision") != "offline_integrity_passed_enter_fresh_gate":
        raise ValueError("registered residual fit did not authorize a fresh gate")
    if fit_report.get("recipe") != FIXED_FIT_RECIPE:
        raise ValueError("registered residual fit recipe differs")
    if fit_report.get("artifact", {}).get("sha256") != registration["inputs"][
        "residual_artifact"
    ]["sha256"]:
        raise ValueError("registered residual artifact differs from fit report")
    seeds = tuple(range(int(recipe["seed_first"]), int(recipe["seed_last"]) + 1))
    id_mapper = build_id_mapper(paths["items_json"])
    initial_checkpoint = load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        id_mapper,
        seed=int(recipe["trainer_seed"]),
        batch_size=64,
        learning_starts=64,
    )
    parent_state, initialization = initialize_trainer(trainer, initial_checkpoint)
    trainer.online_network.eval()
    artifact = torch.load(paths["residual_artifact"], map_location="cpu", weights_only=False)
    residual = load_development_artifact(
        trainer.online_network,
        _trainer_metadata(trainer),
        artifact,
        expected_parent_checkpoint_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
        expected_corpus_sha256={
            "train": registration["inputs"]["train_corpus"]["sha256"],
            "evaluation": registration["inputs"]["evaluation_corpus"]["sha256"],
        },
        expected_recipe=FIXED_FIT_RECIPE,
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
    candidate = evaluate_residual_policy(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        residual=ActionRelativeEvaluationAdapter(residual),
        seeds=seeds,
        config=config,
        max_canonical_actions=int(recipe["max_canonical_actions"]),
        forbidden_residual_action_indices=frozenset(
            int(action) for action in recipe["forbidden_action_indices"]
        ),
    )
    for row in candidate["decision_trace"]:
        row["predicted_advantage"] = row.pop("gate_probability")
    paired = paired_evaluation(control, candidate)
    policy_gate = apply_policy_gates(paired, candidate)
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
        "control": control,
        "candidate": {key: value for key, value in candidate.items() if key != "decision_trace"},
        "paired": paired,
        "policy_gate": policy_gate,
        "output_dir": str(paths["output_dir"]),
        "authority": copy.deepcopy(RESULT_AUTHORITY),
    }
    output = paths["output_dir"]
    staging = output.with_name(f".{output.name}.staging")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        trace_path = staging / "decision_trace.jsonl"
        with trace_path.open("wb") as stream:
            for row in candidate["decision_trace"]:
                stream.write(
                    json.dumps(row, sort_keys=True, separators=(",", ":")).encode("ascii")
                    + b"\n"
                )
        report["decision_trace"] = {
            "path": trace_path.name,
            "row_count": len(candidate["decision_trace"]),
            "sha256": sha256_file(trace_path),
            "size_bytes": trace_path.stat().st_size,
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
                "decision": report["policy_gate"]["decision"],
                "output_dir": report["output_dir"],
                "residual_interventions": report["candidate"]["aggregate"][
                    "residual_intervention_count"
                ],
            },
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
