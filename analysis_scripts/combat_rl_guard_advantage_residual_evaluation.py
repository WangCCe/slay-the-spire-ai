"""Run one registered fresh paired LightSTS gate for a post-guard residual."""

from __future__ import annotations

import argparse
from collections import Counter
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
from types import ModuleType
from typing import Any, Mapping, Sequence

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_bridge import (  # noqa: E402
    MappedCombatState,
    NativeCombatEnvironment,
    load_native_module,
    validate_card_select_settlement,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    DEPLOYMENT_GUARD_TELEMETRY_FIELDS,
    EXPECTED_UNREACHABLE_PROFILE_REASONS,
    GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    SmokeConfig,
    _policy_action,
    _state,
    apply_deployment_guard_proxy,
    calculate_native_reward,
    create_fresh_trainer,
    evaluate_policy,
    initialization_failure_reason,
    initialize_trainer,
    load_initial_checkpoint,
    paired_evaluation,
    parameter_sha256,
    successor_disposition,
)
from analysis_scripts.combat_rl_guard_advantage_corpus import (  # noqa: E402
    canonicalize_actions,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    _current_commit,
    _trainer_metadata,
    _validate_commit,
    _validate_file_binding,
    sha256_file,
)
from spirecomm.ai.rl.v2.guard_advantage_residual import (  # noqa: E402
    GuardAdvantageResidual,
    load_development_artifact,
)
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-guard-advantage-residual-evaluation-20260828-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_guard_advantage_residual_evaluation.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_corpus.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "analysis_scripts/combat_lightspeed_bridge.py",
    "spirecomm/ai/rl/v2/guard_advantage_residual.py",
)

FIXED_RECIPE = {
    "seed_first": 264000,
    "seed_last": 264255,
    "battle_indices": [0, 3, 6, 9],
    "ascension": 0,
    "max_decisions_per_profile": 100,
    "max_actions_per_turn": 8,
    "max_canonical_actions": 8,
    "deployment_guard_proxy": GREEDY_NATIVE_REWARD_DEPLOYMENT_GUARD_PROXY,
    "device": "cpu",
}

FIXED_POLICY_GATES = {
    "candidate_only_victories_at_least_control_only": True,
    "mean_reward_delta_non_negative": True,
    "mean_player_hp_delta_non_negative": True,
    "excluded_nonterminal_profile_count_zero": True,
    "residual_intervention_count_positive": True,
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
    "simulator_mechanism_evidence": True,
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


def _validate_registration(payload: Mapping[str, Any]) -> dict[str, Any]:
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
        raise ValueError("residual evaluation registration root keys differ")
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("residual evaluation registration schema differs")
    if payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("residual evaluation experiment id differs")
    source_commit = _validate_commit(payload["source_commit"])
    runner = _validate_file_binding(payload["runner"], label="runner")
    source_files = payload["source_files"]
    if not isinstance(source_files, Mapping):
        raise ValueError("residual evaluation source files are missing")
    normalized_sources: dict[str, str] = {}
    for raw_path, raw_hash in source_files.items():
        if not isinstance(raw_path, str):
            raise ValueError("residual evaluation source path is invalid")
        path = Path(raw_path)
        if not raw_path or path.is_absolute() or ".." in path.parts:
            raise ValueError("residual evaluation source path is invalid")
        normalized_sources[raw_path.replace("\\", "/")] = str(raw_hash).lower()
        if len(normalized_sources[raw_path.replace("\\", "/")]) != 64:
            raise ValueError("residual evaluation source hash is invalid")
    if set(normalized_sources) != set(SOURCE_SNAPSHOT_PATHS):
        raise ValueError("residual evaluation source inventory differs")
    if Path(runner["path"]).resolve() != (REPO_ROOT / SOURCE_SNAPSHOT_PATHS[0]).resolve():
        raise ValueError("residual evaluation runner path differs")
    if runner["sha256"] != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("residual evaluation runner hash differs")
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
        raise ValueError("residual evaluation inputs differ")
    normalized_inputs = {
        name: _validate_file_binding(inputs[name], label=name)
        for name in sorted(expected_inputs)
    }
    if payload["recipe"] != FIXED_RECIPE:
        raise ValueError("residual evaluation fixed recipe differs")
    if payload["policy_gates"] != FIXED_POLICY_GATES:
        raise ValueError("residual evaluation policy gates differ")
    if payload["authority"] != REGISTERED_AUTHORITY:
        raise ValueError("residual evaluation authority differs")
    output = payload["output_dir"]
    if not isinstance(output, str) or not Path(output).is_absolute():
        raise ValueError("residual evaluation output path must be absolute")
    output_path = Path(output).resolve()
    try:
        output_path.relative_to(REPORTS_ROOT.resolve())
    except ValueError as exc:
        raise ValueError("residual evaluation output path is outside reports") from exc
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
    registration = _validate_registration(json.loads(committed))
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
        raise ValueError("residual evaluation output or staging already exists")
    result["output_dir"] = output
    return result


def select_post_guard_action(
    residual: GuardAdvantageResidual,
    *,
    mapped: MappedCombatState,
    legal_actions: Sequence[Mapping[str, Any]],
    guarded_action: Mapping[str, Any],
    guard_replaced: bool,
    max_canonical_actions: int,
) -> tuple[dict[str, Any], dict[str, Any] | None, str]:
    guarded = dict(guarded_action)
    if not guard_replaced:
        return guarded, None, "guard_not_replaced"
    canonical, exact_to_representative = canonicalize_actions(legal_actions, mapped)
    if len(canonical) <= 1:
        return guarded, None, "no_distinct_alternative"
    if len(canonical) > max_canonical_actions:
        return guarded, None, "too_many_canonical_actions"
    exact_guard_index = int(guarded["rl_action_index"])
    canonical_guard_index = exact_to_representative[exact_guard_index]
    alternative_mask = torch.zeros((1, mapped.action_mask.shape[0]), dtype=torch.bool)
    for action in canonical:
        index = int(action["rl_action_index"])
        if index != canonical_guard_index:
            alternative_mask[0, index] = True
    if not bool(alternative_mask.any()):
        return guarded, None, "no_distinct_alternative"
    start = time.perf_counter()
    with torch.no_grad():
        selection = residual.select_actions(
            torch.from_numpy(mapped.state.continuous.copy()).float(),
            torch.from_numpy(mapped.state.card_ids.copy()).long(),
            torch.from_numpy(mapped.state.potion_ids.copy()).long(),
            torch.from_numpy(mapped.state.relic_ids.copy()).long(),
            torch.from_numpy(mapped.action_mask.copy()).bool(),
            torch.tensor([canonical_guard_index]),
            alternative_mask,
        )
    latency_ms = (time.perf_counter() - start) * 1000.0
    gate_open = bool(selection.gate_open[0].item())
    residual_index = int(selection.residual_actions[0].item())
    selected = guarded
    if gate_open:
        selected = next(
            dict(action)
            for action in legal_actions
            if int(action["rl_action_index"]) == residual_index
        )
    trace = {
        "guard_action_index": exact_guard_index,
        "canonical_guard_action_index": canonical_guard_index,
        "residual_action_index": residual_index,
        "gate_probability": float(selection.gate_probabilities[0].item()),
        "gate_open": gate_open,
        "final_action_index": int(selected["rl_action_index"]),
        "intervened": int(selected["rl_action_index"]) != exact_guard_index,
        "latency_ms": latency_ms,
    }
    return selected, trace, ""


def evaluate_residual_policy(
    native_module: ModuleType,
    *,
    id_mapper: Any,
    trainer: Any,
    residual: GuardAdvantageResidual,
    seeds: Sequence[int],
    config: SmokeConfig,
    max_canonical_actions: int,
) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    decision_trace: list[dict[str, Any]] = []
    was_training = trainer.online_network.training
    trainer.online_network.eval()
    residual.eval()
    try:
        for seed, battle_index in config.profiles(seeds):
            try:
                environment = NativeCombatEnvironment.reset(
                    native_module, seed, config.ascension, battle_index
                )
            except Exception as exc:
                rows.append(
                    {
                        "seed": int(seed),
                        "battle_index": int(battle_index),
                        "outcome": "initialization_failure",
                        "player_hp": 0,
                        "decisions": 0,
                        "reward": 0.0,
                        "initialization_failure_reason": initialization_failure_reason(exc),
                        "unsupported_reason": f"initialization_failure:{exc}",
                        "truncated": False,
                        "card_select_settlement_count": 0,
                        "card_select_settlement_task_counts": {},
                        "residual_eligible_count": 0,
                        "residual_gate_open_count": 0,
                        "residual_intervention_count": 0,
                        "residual_abstention_count": 0,
                        "residual_support_skip_count": 0,
                        "residual_support_skip_reason_counts": {},
                        **{field: 0 for field in DEPLOYMENT_GUARD_TELEMETRY_FIELDS},
                    }
                )
                continue
            progression = dict(environment.snapshot().get("progression") or {})
            actions_since_end_turn = 0
            total_reward = 0.0
            decisions = 0
            unsupported_reason = ""
            outcome = "undecided"
            truncated = False
            settlement_actions = 0
            settlement_tasks = Counter()
            guard_telemetry = Counter()
            residual_telemetry = Counter()
            support_reasons = Counter()
            for decision_index in range(config.max_decisions_per_seed):
                status = environment.status()
                disposition, reason = successor_disposition(status)
                if disposition == "terminal":
                    outcome = reason
                    break
                if disposition == "exclude":
                    unsupported_reason = reason
                    break
                mapped = environment.mapped_state(id_mapper=id_mapper)
                before = environment.snapshot()
                legal = environment.legal_actions()
                policy_selected = actions_since_end_turn < config.max_actions_per_turn
                raw = _policy_action(
                    trainer,
                    mapped,
                    legal,
                    actions_since_end_turn=actions_since_end_turn,
                    max_actions_per_turn=config.max_actions_per_turn,
                )
                guarded, step_guard = apply_deployment_guard_proxy(
                    environment,
                    raw,
                    legal,
                    before,
                    mode=config.deployment_guard_proxy,
                    policy_selected=policy_selected,
                )
                guard_telemetry.update(step_guard)
                selected, trace, support_reason = select_post_guard_action(
                    residual,
                    mapped=mapped,
                    legal_actions=legal,
                    guarded_action=guarded,
                    guard_replaced=bool(step_guard["guard_proxy_replacement_count"]),
                    max_canonical_actions=max_canonical_actions,
                )
                if support_reason and support_reason != "guard_not_replaced":
                    residual_telemetry["residual_support_skip_count"] += 1
                    support_reasons[support_reason] += 1
                if trace is not None:
                    residual_telemetry["residual_eligible_count"] += 1
                    residual_telemetry["residual_gate_open_count"] += int(trace["gate_open"])
                    residual_telemetry["residual_intervention_count"] += int(trace["intervened"])
                    residual_telemetry["residual_abstention_count"] += int(not trace["gate_open"])
                    decision_trace.append(
                        {
                            "seed": int(seed),
                            "battle_index": int(battle_index),
                            "decision_index": decision_index,
                            "act": int(before["state"]["act"]),
                            "floor": int(before["state"]["floor"]),
                            "turn": int(before["state"]["turn"]),
                            **trace,
                        }
                    )
                environment.step(str(selected["action_id"]))
                status = environment.status()
                after = environment.snapshot()
                settlement = validate_card_select_settlement(
                    after.get("card_select_settlement")
                )
                settlement_actions += int(settlement["count"])
                settlement_tasks.update(settlement["tasks"])
                total_reward += calculate_native_reward(
                    before,
                    after,
                    action_kind=str(selected["kind"]),
                    outcome=str(status.get("outcome") or "undecided"),
                )["total"]
                decisions += 1
                actions_since_end_turn = (
                    0 if selected["kind"] == "end_turn" else actions_since_end_turn + 1
                )
            else:
                truncated = True
            final_state = _state(environment.snapshot())
            rows.append(
                {
                    "seed": int(seed),
                    "battle_index": int(battle_index),
                    "progression": progression,
                    "outcome": outcome,
                    "player_hp": int(dict(final_state.get("player") or {}).get("current_hp", 0)),
                    "decisions": decisions,
                    "reward": float(total_reward),
                    "unsupported_reason": unsupported_reason,
                    "truncated": truncated,
                    "card_select_settlement_count": settlement_actions,
                    "card_select_settlement_task_counts": dict(sorted(settlement_tasks.items())),
                    "residual_eligible_count": int(residual_telemetry["residual_eligible_count"]),
                    "residual_gate_open_count": int(residual_telemetry["residual_gate_open_count"]),
                    "residual_intervention_count": int(residual_telemetry["residual_intervention_count"]),
                    "residual_abstention_count": int(residual_telemetry["residual_abstention_count"]),
                    "residual_support_skip_count": int(residual_telemetry["residual_support_skip_count"]),
                    "residual_support_skip_reason_counts": dict(sorted(support_reasons.items())),
                    **{field: int(guard_telemetry[field]) for field in DEPLOYMENT_GUARD_TELEMETRY_FIELDS},
                }
            )
    finally:
        trainer.online_network.train(was_training)

    rewards = np.asarray([row["reward"] for row in rows], dtype=np.float64)
    hp = np.asarray([row["player_hp"] for row in rows], dtype=np.float64)
    decisions = np.asarray([row["decisions"] for row in rows], dtype=np.float64)
    support_counts = Counter()
    for row in rows:
        support_counts.update(row["residual_support_skip_reason_counts"])
    latencies = np.asarray(
        [row["latency_ms"] for row in decision_trace], dtype=np.float64
    )
    return {
        "deployment_guard_proxy": config.deployment_guard_proxy,
        "rows": rows,
        "decision_trace": decision_trace,
        "aggregate": {
            "deployment_guard_proxy": config.deployment_guard_proxy,
            "mean_decisions": float(decisions.mean()),
            "mean_player_hp": float(hp.mean()),
            "mean_reward": float(rewards.mean()),
            "player_loss_count": sum(row["outcome"] == "player_loss" for row in rows),
            "player_victory_count": sum(row["outcome"] == "player_victory" for row in rows),
            "seed_count": len(rows),
            "profile_count": len(rows),
            "profile_count_initialized": sum(row["outcome"] != "initialization_failure" for row in rows),
            "profile_count_unreachable": sum(
                row["outcome"] == "initialization_failure"
                and row.get("initialization_failure_reason") in EXPECTED_UNREACHABLE_PROFILE_REASONS
                for row in rows
            ),
            "truncated_count": sum(bool(row["truncated"]) for row in rows),
            "unsupported_count": sum(
                bool(row["unsupported_reason"])
                and row["outcome"] != "initialization_failure"
                for row in rows
            ),
            "residual_eligible_count": sum(int(row["residual_eligible_count"]) for row in rows),
            "residual_gate_open_count": sum(int(row["residual_gate_open_count"]) for row in rows),
            "residual_intervention_count": sum(int(row["residual_intervention_count"]) for row in rows),
            "residual_abstention_count": sum(int(row["residual_abstention_count"]) for row in rows),
            "residual_support_skip_count": sum(int(row["residual_support_skip_count"]) for row in rows),
            "residual_support_skip_reason_counts": dict(sorted(support_counts.items())),
            "residual_latency_ms": {
                "count": int(latencies.size),
                "mean": float(latencies.mean()) if latencies.size else 0.0,
                "p95": float(np.quantile(latencies, 0.95)) if latencies.size else 0.0,
                "maximum": float(latencies.max()) if latencies.size else 0.0,
            },
            **{
                field: sum(int(row[field]) for row in rows)
                for field in DEPLOYMENT_GUARD_TELEMETRY_FIELDS
            },
        },
    }


def apply_policy_gates(
    paired: Mapping[str, Any], candidate: Mapping[str, Any]
) -> dict[str, Any]:
    aggregate = paired["aggregate"]
    candidate_aggregate = candidate["aggregate"]
    conditions = {
        "candidate_only_victories_at_least_control_only": int(
            aggregate["candidate_only_victories"]
        )
        >= int(aggregate["control_only_victories"]),
        "mean_reward_delta_non_negative": float(aggregate["mean_reward_delta"]) >= 0.0,
        "mean_player_hp_delta_non_negative": float(
            aggregate["mean_player_hp_delta"]
        )
        >= 0.0,
        "excluded_nonterminal_profile_count_zero": int(
            aggregate["excluded_nonterminal_profile_count"]
        )
        == 0,
        "residual_intervention_count_positive": int(
            candidate_aggregate["residual_intervention_count"]
        )
        > 0,
    }
    if set(conditions) != set(FIXED_POLICY_GATES):
        raise RuntimeError("residual evaluation policy condition inventory differs")
    passed = all(conditions.values())
    return {
        "conditions": conditions,
        "all_conditions_passed": passed,
        "decision": (
            "simulator_promising_retain_for_separate_divergence_calibration"
            if passed
            else "fixed_residual_recipe_failed_close_without_sweep"
        ),
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    paired = report["paired"]["aggregate"]
    candidate = report["candidate"]["aggregate"]
    return (
        "# Guard-Advantage Residual Fresh Paired Gate\n\n"
        f"- Candidate-only victories: {paired['candidate_only_victories']}\n"
        f"- Control-only victories: {paired['control_only_victories']}\n"
        f"- Mean reward delta: {paired['mean_reward_delta']:.6f}\n"
        f"- Mean player HP delta: {paired['mean_player_hp_delta']:.6f}\n"
        f"- Residual interventions: {candidate['residual_intervention_count']}\n"
        f"- Nonterminal exclusions: {paired['excluded_nonterminal_profile_count']}\n"
        f"- Decision: {report['policy_gate']['decision']}\n"
    )


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("residual evaluation must use the registered Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("residual evaluation must run in isolated -I mode")
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
        id_mapper,
        seed=2026082823,
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
        residual=residual,
        seeds=seeds,
        config=config,
        max_canonical_actions=int(recipe["max_canonical_actions"]),
    )
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
                stream.write(json.dumps(row, sort_keys=True, separators=(",", ":")).encode("ascii") + b"\n")
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
