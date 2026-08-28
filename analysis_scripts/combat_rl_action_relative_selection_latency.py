"""Benchmark parity and CPU latency for action-relative candidate selection."""

from __future__ import annotations

import argparse
import json
import math
import os
from pathlib import Path
import shutil
import sys
import time
from typing import Any, Callable, Mapping, Sequence

import numpy as np
import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_rl_action_relative_advantage_residual_fit import (  # noqa: E402
    FIXED_RECIPE as FIXED_FIT_RECIPE,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    load_corpus,
    sha256_file,
)
from spirecomm.ai.rl.v2.action_relative_advantage_residual import (  # noqa: E402
    ActionRelativeAdvantageResidual,
    ActionRelativeSelection,
    load_development_artifact,
)
from spirecomm.ai.rl.v2.agent import RLAgentV2  # noqa: E402
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_adapter import state_dict_sha256  # noqa: E402
from spirecomm.ai.rl.v2.latent_gated_live_shadow import (  # noqa: E402
    _require_committed_registration,
    _require_source_binding,
    _resolve_path,
    _validate_sha256,
)


SCHEMA_VERSION = 1
EXPERIMENT_ID = "combat-rl-action-relative-selection-latency-20260829-r2"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
SOURCE_BOUND_PATHS = (
    "analysis_scripts/combat_rl_action_relative_selection_latency.py",
    "analysis_scripts/combat_rl_action_relative_advantage_residual_fit.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "spirecomm/ai/rl/checkpoint_io.py",
    "spirecomm/ai/rl/v2/action_relative_advantage_residual.py",
    "spirecomm/ai/rl/v2/agent.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/network.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
)
FIXED_RECIPE = {
    "device": "cpu",
    "forbidden_action_indices": [90],
    "measurement_calls": 256,
    "row_selection_seed": 2026082825,
    "warmup_calls": 32,
}
FIXED_GATES = {
    "maximum_optimized_p95_ms": 15.0,
    "minimum_p50_speedup": 2.0,
    "prediction_atol": 1e-5,
    "prediction_rtol": 1e-5,
}
FIXED_AUTHORITY = {
    "candidate_action_authority": False,
    "communication_mod": False,
    "cpu_benchmark": True,
    "gameplay": False,
    "model_fitting": False,
    "promotion": False,
    "qualification": False,
    "training": False,
}
AMBIENT_COMBAT_RUNTIME_ENV = (
    "STS_COMBAT_RL_ACTION_RELATIVE_SHADOW_REGISTRATION",
    "STS_COMBAT_RL_LATENT_CANDIDATE_REGISTRATION",
    "STS_COMBAT_RL_LATENT_SHADOW_REGISTRATION",
)


def _reject_ambient_combat_runtime() -> None:
    configured = sorted(name for name in AMBIENT_COMBAT_RUNTIME_ENV if os.environ.get(name))
    if configured:
        raise ValueError(
            "action-relative latency benchmark rejects ambient combat runtime: "
            + ", ".join(configured)
        )


def repeated_state_reference_select(
    residual: ActionRelativeAdvantageResidual,
    continuous: torch.Tensor,
    card_ids: torch.Tensor,
    potion_ids: torch.Tensor,
    relic_ids: torch.Tensor,
    action_masks: torch.Tensor,
    guard_actions: torch.Tensor,
    alternative_masks: torch.Tensor,
    *,
    forbidden_action_indices: frozenset[int],
) -> ActionRelativeSelection:
    allowed = alternative_masks.bool().clone()
    for action in sorted(forbidden_action_indices):
        allowed[:, action] = False
    candidate_pairs = allowed.nonzero(as_tuple=False)
    residual_actions = guard_actions.clone()
    predicted_advantages = torch.full(
        guard_actions.shape,
        float("-inf"),
        dtype=continuous.dtype,
        device=continuous.device,
    )
    has_allowed = allowed.any(dim=1)
    if candidate_pairs.numel():
        state_rows = candidate_pairs[:, 0]
        candidates = candidate_pairs[:, 1]
        pair_predictions = residual.score_candidates(
            continuous[state_rows],
            card_ids[state_rows],
            potion_ids[state_rows],
            relic_ids[state_rows],
            action_masks[state_rows],
            guard_actions[state_rows],
            candidates,
        )
        score_matrix = torch.full(
            action_masks.shape,
            float("-inf"),
            dtype=pair_predictions.dtype,
            device=pair_predictions.device,
        )
        score_matrix[state_rows, candidates] = pair_predictions
        best_scores, best_actions = score_matrix.max(dim=1)
        residual_actions[has_allowed] = best_actions[has_allowed]
        predicted_advantages[has_allowed] = best_scores[has_allowed]
    gate_open = has_allowed & predicted_advantages.ge(
        float(residual.config.advantage_threshold)
    )
    actions = torch.where(gate_open, residual_actions, guard_actions)
    forbidden = sorted(forbidden_action_indices)
    return ActionRelativeSelection(
        actions=actions,
        guard_actions=guard_actions,
        residual_actions=residual_actions,
        predicted_advantages=predicted_advantages,
        gate_open=gate_open,
        telemetry={
            "row_count": int(guard_actions.numel()),
            "intervention_count": int(gate_open.sum().item()),
            "guard_preserved_count": int((~gate_open).sum().item()),
            "no_allowed_alternative_count": int((~has_allowed).sum().item()),
            "forbidden_action_indices": forbidden,
            "forbidden_action_selection_count": sum(
                int(actions[gate_open].eq(action).sum().item()) for action in forbidden
            ),
            "advantage_threshold": float(residual.config.advantage_threshold),
        },
    )


def _row_inputs(
    tensors: Mapping[str, torch.Tensor], row_index: int
) -> dict[str, torch.Tensor]:
    row = slice(row_index, row_index + 1)
    return {
        name: tensors[name][row]
        for name in (
            "continuous",
            "card_ids",
            "potion_ids",
            "relic_ids",
            "action_masks",
            "guard_actions",
            "alternative_masks",
        )
    }


def _assert_parity(
    reference: ActionRelativeSelection,
    optimized: ActionRelativeSelection,
    *,
    rtol: float,
    atol: float,
) -> float:
    for field in ("actions", "guard_actions", "residual_actions", "gate_open"):
        if not torch.equal(getattr(reference, field), getattr(optimized, field)):
            raise RuntimeError(f"action-relative latency parity failed for {field}")
    if reference.telemetry != optimized.telemetry:
        raise RuntimeError("action-relative latency telemetry parity failed")
    if not torch.allclose(
        reference.predicted_advantages,
        optimized.predicted_advantages,
        rtol=rtol,
        atol=atol,
        equal_nan=True,
    ):
        raise RuntimeError("action-relative latency prediction parity failed")
    finite = torch.isfinite(reference.predicted_advantages)
    if not bool(finite.any()):
        return 0.0
    return float(
        (
            reference.predicted_advantages[finite]
            - optimized.predicted_advantages[finite]
        )
        .abs()
        .max()
        .item()
    )


def _timed(call: Callable[[], ActionRelativeSelection]) -> tuple[ActionRelativeSelection, float]:
    started = time.perf_counter_ns()
    result = call()
    return result, (time.perf_counter_ns() - started) / 1_000_000.0


def _latency_summary(values: Sequence[float]) -> dict[str, float | int]:
    array = np.asarray(values, dtype=np.float64)
    return {
        "count": int(array.size),
        "mean_ms": float(array.mean()),
        "p50_ms": float(np.quantile(array, 0.50)),
        "p95_ms": float(np.quantile(array, 0.95)),
        "maximum_ms": float(array.max()),
    }


def benchmark_selection(
    residual: ActionRelativeAdvantageResidual,
    tensors: Mapping[str, torch.Tensor],
    *,
    warmup_calls: int,
    measurement_calls: int,
    row_selection_seed: int,
    forbidden_action_indices: frozenset[int],
    gates: Mapping[str, float],
) -> dict[str, Any]:
    row_count = int(tensors["guard_actions"].numel())
    if row_count <= 0 or warmup_calls < 0 or measurement_calls <= 0:
        raise ValueError("action-relative latency benchmark sizes are invalid")
    generator = torch.Generator(device="cpu")
    generator.manual_seed(int(row_selection_seed))
    total_calls = warmup_calls + measurement_calls
    rows: list[int] = []
    while len(rows) < total_calls:
        rows.extend(torch.randperm(row_count, generator=generator).tolist())
    rows = rows[:total_calls]
    rtol = float(gates["prediction_rtol"])
    atol = float(gates["prediction_atol"])

    def calls(row_index: int):
        inputs = _row_inputs(tensors, row_index)
        reference = lambda: repeated_state_reference_select(
            residual,
            **inputs,
            forbidden_action_indices=forbidden_action_indices,
        )
        optimized = lambda: residual.select_actions(
            **inputs,
            forbidden_action_indices=forbidden_action_indices,
        )
        return reference, optimized

    maximum_prediction_delta = 0.0
    with torch.inference_mode():
        for row_index in rows[:warmup_calls]:
            reference, optimized = calls(row_index)
            maximum_prediction_delta = max(
                maximum_prediction_delta,
                _assert_parity(reference(), optimized(), rtol=rtol, atol=atol),
            )

        reference_latency: list[float] = []
        optimized_latency: list[float] = []
        for measurement_index, row_index in enumerate(rows[warmup_calls:]):
            reference, optimized = calls(row_index)
            if measurement_index % 2:
                optimized_result, optimized_ms = _timed(optimized)
                reference_result, reference_ms = _timed(reference)
            else:
                reference_result, reference_ms = _timed(reference)
                optimized_result, optimized_ms = _timed(optimized)
            maximum_prediction_delta = max(
                maximum_prediction_delta,
                _assert_parity(
                    reference_result,
                    optimized_result,
                    rtol=rtol,
                    atol=atol,
                ),
            )
            reference_latency.append(reference_ms)
            optimized_latency.append(optimized_ms)

    reference_summary = _latency_summary(reference_latency)
    optimized_summary = _latency_summary(optimized_latency)
    p50_speedup = float(reference_summary["p50_ms"]) / float(
        optimized_summary["p50_ms"]
    )
    conditions = {
        "measurement_count_exact": len(optimized_latency) == measurement_calls,
        "prediction_parity": maximum_prediction_delta <= atol,
        "p50_speedup_reached": p50_speedup
        >= float(gates["minimum_p50_speedup"]),
        "optimized_p95_within_ceiling": float(optimized_summary["p95_ms"])
        <= float(gates["maximum_optimized_p95_ms"]),
    }
    passed = all(conditions.values())
    return {
        "row_count": row_count,
        "warmup_calls": warmup_calls,
        "measurement_calls": measurement_calls,
        "row_selection_seed": row_selection_seed,
        "maximum_prediction_delta": maximum_prediction_delta,
        "reference_latency": reference_summary,
        "optimized_latency": optimized_summary,
        "p50_speedup": p50_speedup,
        "conditions": conditions,
        "all_conditions_passed": passed,
        "decision": (
            "offline_latency_preflight_passed"
            if passed
            else "offline_latency_preflight_failed"
        ),
    }


def _exact_keys(value: Any, expected: set[str], label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or set(value) != expected:
        raise ValueError(f"action-relative latency {label} keys differ")
    return value


def load_registration(
    path: Path, *, require_committed: bool = True
) -> tuple[dict[str, Any], str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError("action-relative latency registration is missing")
    data = resolved.read_bytes()
    if require_committed:
        _require_committed_registration(resolved, REPO_ROOT)
    payload = _exact_keys(
        json.loads(data),
        {
            "schema_version",
            "experiment_id",
            "source_commit",
            "inputs",
            "artifact_bindings",
            "parent_state_dict_sha256",
            "recipe",
            "gates",
            "output_dir",
            "authority",
        },
        "registration",
    )
    if payload["schema_version"] != SCHEMA_VERSION:
        raise ValueError("action-relative latency registration schema differs")
    if payload["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("action-relative latency experiment id differs")
    source_commit = str(payload["source_commit"]).lower()
    if len(source_commit) != 40 or any(c not in "0123456789abcdef" for c in source_commit):
        raise ValueError("action-relative latency source commit is invalid")
    inputs = _exact_keys(
        payload["inputs"],
        {"items_json", "production_parent_checkpoint", "residual_artifact", "evaluation_corpus"},
        "inputs",
    )
    normalized_inputs: dict[str, dict[str, str]] = {}
    for name, binding in inputs.items():
        binding = _exact_keys(binding, {"path", "sha256"}, name)
        normalized_inputs[name] = {
            "path": str(_resolve_path(binding["path"], label=name)),
            "sha256": _validate_sha256(binding["sha256"], name),
        }
    artifact_bindings = _exact_keys(
        payload["artifact_bindings"],
        {"parent_checkpoint_sha256", "train_corpus_sha256", "evaluation_corpus_sha256"},
        "artifact bindings",
    )
    normalized_artifact = {
        name: _validate_sha256(value, name)
        for name, value in artifact_bindings.items()
    }
    parent_state = _validate_sha256(
        payload["parent_state_dict_sha256"], "parent state"
    )
    if payload["recipe"] != FIXED_RECIPE or payload["gates"] != FIXED_GATES:
        raise ValueError("action-relative latency fixed configuration differs")
    if payload["authority"] != FIXED_AUTHORITY:
        raise ValueError("action-relative latency authority differs")
    output = _resolve_path(payload["output_dir"], label="output")
    try:
        output.relative_to((REPO_ROOT / "reports").resolve())
    except ValueError as exc:
        raise ValueError("action-relative latency output is outside reports") from exc
    return {
        "source_commit": source_commit,
        "inputs": normalized_inputs,
        "artifact_bindings": normalized_artifact,
        "parent_state_dict_sha256": parent_state,
        "recipe": dict(FIXED_RECIPE),
        "gates": dict(FIXED_GATES),
        "output_dir": str(output),
        "authority": dict(FIXED_AUTHORITY),
    }, sha256_file(resolved)


def run(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("action-relative latency benchmark requires Windows Python")
    if not sys.flags.isolated:
        raise ValueError("action-relative latency benchmark requires isolated mode")
    _reject_ambient_combat_runtime()
    registration, registration_sha256 = load_registration(registration_path)
    _require_source_binding(
        registration["source_commit"],
        REPO_ROOT,
        source_bound_paths=SOURCE_BOUND_PATHS,
    )
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"])
        if not path.is_file() or sha256_file(path) != binding["sha256"]:
            raise ValueError(f"action-relative latency {name} binding differs")
        paths[name] = path
    output = Path(registration["output_dir"])
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("action-relative latency output or staging already exists")

    id_mapper = build_id_mapper(str(paths["items_json"]))
    agent = RLAgentV2(
        model_path=str(paths["production_parent_checkpoint"]),
        training=False,
        device="cpu",
        epsilon=0.0,
        id_mapper=id_mapper,
        expert_mix_enabled=False,
        parent_policy_anchor_weight=0.0,
        positive_energy_action_imitation_weight=0.0,
        positive_energy_parent_end_turn_imitation_weight=0.0,
    )
    if state_dict_sha256(agent.network.state_dict()) != registration[
        "parent_state_dict_sha256"
    ]:
        raise ValueError("action-relative latency parent state differs")
    metadata = agent._build_metadata().as_dict()
    metadata.pop("rl_space_version")
    artifact = torch.load(paths["residual_artifact"], map_location="cpu", weights_only=False)
    residual = load_development_artifact(
        agent.network,
        metadata,
        artifact,
        expected_parent_checkpoint_sha256=registration["artifact_bindings"][
            "parent_checkpoint_sha256"
        ],
        expected_corpus_sha256={
            "train": registration["artifact_bindings"]["train_corpus_sha256"],
            "evaluation": registration["artifact_bindings"][
                "evaluation_corpus_sha256"
            ],
        },
        expected_recipe=FIXED_FIT_RECIPE,
    )
    corpus = load_corpus(paths["evaluation_corpus"], expected_partition="evaluation")
    result = benchmark_selection(
        residual,
        corpus["tensors"],
        warmup_calls=FIXED_RECIPE["warmup_calls"],
        measurement_calls=FIXED_RECIPE["measurement_calls"],
        row_selection_seed=FIXED_RECIPE["row_selection_seed"],
        forbidden_action_indices=frozenset(FIXED_RECIPE["forbidden_action_indices"]),
        gates=FIXED_GATES,
    )
    report = {
        "schema_version": SCHEMA_VERSION,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "registration_sha256": registration_sha256,
        "inputs": registration["inputs"],
        "artifact_bindings": registration["artifact_bindings"],
        "parent_state_dict_sha256": registration["parent_state_dict_sha256"],
        "recipe": registration["recipe"],
        "gates": registration["gates"],
        "benchmark": result,
        "authority": registration["authority"],
    }
    staging.mkdir(parents=True)
    try:
        (staging / "report.json").write_text(
            json.dumps(report, allow_nan=False, indent=2, sort_keys=True) + "\n",
            encoding="ascii",
            newline="\n",
        )
        (staging / "summary.md").write_text(
            "\n".join(
                (
                    "# Action-Relative Selection Latency",
                    "",
                    f"- Reference p50 ms: {result['reference_latency']['p50_ms']:.6f}",
                    f"- Optimized p50 ms: {result['optimized_latency']['p50_ms']:.6f}",
                    f"- Optimized p95 ms: {result['optimized_latency']['p95_ms']:.6f}",
                    f"- P50 speedup: {result['p50_speedup']:.6f}x",
                    f"- Decision: {result['decision']}",
                    "",
                )
            ),
            encoding="ascii",
            newline="\n",
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
    print(json.dumps({"decision": report["benchmark"]["decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()
