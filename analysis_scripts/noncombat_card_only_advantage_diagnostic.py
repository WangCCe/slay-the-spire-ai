"""Replay one consumed card-only cohort and summarize its frozen RL signal."""

from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import importlib
import json
import math
from pathlib import Path
import statistics
import subprocess
import sys
import time
from typing import Any, Sequence


if __package__ in {None, ""}:
    sys.path.append(str(Path(__file__).resolve().parents[1]))


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _file_binding(path: Path) -> dict[str, Any]:
    payload = path.read_bytes()
    return {
        "path": path.resolve().as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _load_runtime(registration_path: Path) -> tuple[Any, Any, Any]:
    original_argv = sys.argv
    sys.argv = [
        str(Path(__file__).resolve()),
        "run-resume-worker",
        "--registration",
        str(registration_path.resolve()),
    ]
    try:
        runner = importlib.import_module(
            "analysis_scripts.noncombat_card_only_native_baseline_rl_pilot_runner"
        )
    finally:
        sys.argv = original_argv
    runtime = importlib.import_module(
        "analysis_scripts.noncombat_card_acceptance_empirical_successor_runtime"
    )
    pilot = importlib.import_module(
        "analysis_scripts.noncombat_card_only_native_baseline_rl_pilot"
    )
    return runner, runtime, pilot


def _stats(values: Sequence[float]) -> dict[str, Any]:
    normalized = tuple(float(value) for value in values)
    if not normalized or not all(math.isfinite(value) for value in normalized):
        raise RuntimeError("diagnostic statistic values are invalid")
    return {
        "count": len(normalized),
        "maximum": max(normalized),
        "mean": math.fsum(normalized) / len(normalized),
        "minimum": min(normalized),
        "negative_count": sum(value < 0.0 for value in normalized),
        "positive_count": sum(value > 0.0 for value in normalized),
        "population_stddev": statistics.pstdev(normalized),
        "zero_count": sum(value == 0.0 for value in normalized),
    }


def _correlation(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or len(left) < 2:
        return None
    left_mean = math.fsum(left) / len(left)
    right_mean = math.fsum(right) / len(right)
    numerator = math.fsum(
        (a - left_mean) * (b - right_mean)
        for a, b in zip(left, right, strict=True)
    )
    left_norm = math.sqrt(math.fsum((value - left_mean) ** 2 for value in left))
    right_norm = math.sqrt(
        math.fsum((value - right_mean) ** 2 for value in right)
    )
    if left_norm == 0.0 or right_norm == 0.0:
        return None
    return numerator / (left_norm * right_norm)


def _gradient_norms(
    loss: Any,
    *,
    torch: Any,
    parameter_names: Sequence[str],
    parameters: Sequence[Any],
) -> dict[str, Any]:
    gradients = torch.autograd.grad(
        loss, parameters, retain_graph=True, allow_unused=True
    )
    result = {}
    for head in ("family_head", "conditional_ranker"):
        squares = []
        nonzero = 0
        for name, gradient in zip(parameter_names, gradients, strict=True):
            if not name.startswith(f"{head}.") or gradient is None:
                continue
            squares.append(torch.sum(gradient.detach().double() ** 2).item())
            nonzero += int(torch.count_nonzero(gradient).item())
        result[head] = {
            "l2": math.sqrt(math.fsum(squares)),
            "nonzero_coordinates": nonzero,
        }
    return result


def run_diagnostic(
    *,
    repo_root: Path,
    registration_path: Path,
    checkpoint_path: Path,
    output_path: Path,
    maximum_seconds: float,
) -> dict[str, Any]:
    if output_path.exists():
        raise RuntimeError(f"diagnostic output already exists: {output_path}")
    if not math.isfinite(maximum_seconds) or not 0.0 < maximum_seconds <= 3600.0:
        raise RuntimeError("diagnostic maximum seconds must be in (0, 3600]")

    runner, runtime, pilot = _load_runtime(registration_path)
    torch = importlib.import_module("torch")
    registration = json.loads(registration_path.read_text(encoding="ascii"))
    checkpoint = json.loads(checkpoint_path.read_text(encoding="ascii"))
    bootstrap = runtime.restore_paired_bootstrap(
        _canonical_bytes(checkpoint["bootstrap"])
    )
    model_before = pilot.encode_candidate_card_policy(bootstrap)
    environment_factory = runner._load_environment_factory(
        registration["native"]["identity"]
    )
    seeds = tuple(registration["schedule"]["residual_chunk_seeds"][0])
    if len(seeds) != 64 or seeds != tuple(sorted(set(seeds))):
        raise RuntimeError("registered diagnostic seed schedule differs")

    deadline = time.monotonic() + maximum_seconds
    pairs = tuple(
        runtime.rollout_paired_card_only_native_baseline_training_episode(
            bootstrap,
            environment_factory=environment_factory,
            seed=seed,
            deadline=deadline,
        )
        for seed in seeds
    )
    supported, censored = pilot._validate_residual_pairs(pairs, chunk_index=0)
    baseline = runtime.build_candidate_cross_fitted_baseline(supported)
    objective_rows = runtime.build_arm_card_reward_rows(
        supported, arm="candidate", baseline=baseline
    )
    objective = runtime.build_arm_card_reward_objective(objective_rows)

    card_decisions = {
        decision.decision_id: decision
        for pair in supported
        for decision in pair.candidate.decisions
        if decision.category == "card_reward"
    }
    predictions = {row.decision_id: row for row in baseline.predictions}
    advantage_rows = []
    for decision, record in zip(
        baseline.decisions, baseline.advantage_batch.records, strict=True
    ):
        if decision.category != "card_reward":
            continue
        advantage_rows.append(
            {
                "advantage": float(record.advantage),
                "baseline_prediction": float(record.baseline_prediction),
                "decision_id": decision.decision_id,
                "raw_return": float(record.raw_return),
                "seed": int(decision.seed),
                "selected_family": card_decisions[
                    decision.decision_id
                ].card_terms.selected_family,
                "was_clipped": bool(predictions[decision.decision_id].was_clipped),
            }
        )

    by_family = {}
    for family in sorted({row["selected_family"] for row in advantage_rows}):
        selected = tuple(
            row for row in advantage_rows if row["selected_family"] == family
        )
        by_family[family] = {
            "advantage": _stats(tuple(row["advantage"] for row in selected)),
            "baseline_prediction": _stats(
                tuple(row["baseline_prediction"] for row in selected)
            ),
            "clipped_count": sum(row["was_clipped"] for row in selected),
            "raw_return": _stats(tuple(row["raw_return"] for row in selected)),
        }

    named_parameters = runtime._arm_named_trainable_parameters(
        bootstrap, arm="candidate"
    )
    parameter_names = tuple(name for name, _ in named_parameters)
    parameters = tuple(parameter for _, parameter in named_parameters)
    components = {
        "conditional_entropy_loss": objective.conditional_entropy_loss,
        "conditional_policy_loss": objective.conditional_policy_loss,
        "family_entropy_loss": objective.family_entropy_loss,
        "family_policy_loss": objective.family_policy_loss,
        "total_loss": objective.total_loss,
    }
    component_gradients = {
        name: _gradient_norms(
            value,
            torch=torch,
            parameter_names=parameter_names,
            parameters=parameters,
        )
        for name, value in components.items()
    }
    family_gradients = {}
    for family in sorted({terms.selected_family for terms, _ in objective_rows}):
        rows = tuple(
            (terms, advantage)
            for terms, advantage in objective_rows
            if terms.selected_family == family
        )
        family_objective = runtime.build_arm_card_reward_objective(rows)
        family_gradients[family] = {
            "decision_count": len(rows),
            "gradient_norms": _gradient_norms(
                family_objective.total_loss,
                torch=torch,
                parameter_names=parameter_names,
                parameters=parameters,
            ),
            "losses": {
                "conditional_entropy": float(
                    family_objective.conditional_entropy_loss.detach()
                ),
                "conditional_policy": float(
                    family_objective.conditional_policy_loss.detach()
                ),
                "family_entropy": float(
                    family_objective.family_entropy_loss.detach()
                ),
                "family_policy": float(family_objective.family_policy_loss.detach()),
                "total": float(family_objective.total_loss.detach()),
            },
        }

    advantages_by_seed: dict[int, list[float]] = defaultdict(list)
    for row in advantage_rows:
        advantages_by_seed[row["seed"]].append(row["advantage"])
    seed_rows = []
    for pair in supported:
        values = advantages_by_seed[pair.seed]
        seed_rows.append(
            {
                "candidate_floor_progress": float(pair.candidate.floor_progress),
                "card_advantage_mean": math.fsum(values) / len(values),
                "card_decision_count": len(values),
                "control_floor_progress": float(pair.control.floor_progress),
                "floor_progress_difference": float(
                    pair.candidate.floor_progress - pair.control.floor_progress
                ),
                "seed": pair.seed,
            }
        )

    if pilot.encode_candidate_card_policy(bootstrap) != model_before:
        raise RuntimeError("diagnostic replay mutated candidate model")
    report = {
        "authority": {
            "fresh_evaluation": False,
            "gameplay": False,
            "model_fitting": False,
            "optimizer_step": False,
            "promotion": False,
            "training": False,
        },
        "baseline": {
            "all_decision_count": len(baseline.decisions),
            "card_decision_count": len(advantage_rows),
            "clipped_card_prediction_count": sum(
                row["was_clipped"] for row in advantage_rows
            ),
            "fold_count": len(baseline.models),
        },
        "card_advantages": {
            "all": _stats(tuple(row["advantage"] for row in advantage_rows)),
            "by_selected_family": by_family,
        },
        "censored_pairs": list(censored),
        "environment_accesses": 128,
        "gradient_diagnostics": {
            "by_loss_component": component_gradients,
            "by_selected_family": family_gradients,
        },
        "inputs": {
            "checkpoint": _file_binding(checkpoint_path),
            "native_module": registration["native"]["identity"]["module"],
            "registration": _file_binding(registration_path),
            "source_commit": subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip(),
        },
        "model_unchanged": True,
        "objective": {
            "card_decision_count": objective.card_decision_count,
            "conditional_entropy_loss": float(
                objective.conditional_entropy_loss.detach()
            ),
            "conditional_policy_loss": float(
                objective.conditional_policy_loss.detach()
            ),
            "family_entropy_loss": float(objective.family_entropy_loss.detach()),
            "family_policy_loss": float(objective.family_policy_loss.detach()),
            "total_loss": float(objective.total_loss.detach()),
        },
        "schema_version": "noncombat-card-only-advantage-diagnostic-v1",
        "seed_level": {
            "card_advantage_mean_vs_floor_difference_correlation": _correlation(
                tuple(row["card_advantage_mean"] for row in seed_rows),
                tuple(row["floor_progress_difference"] for row in seed_rows),
            ),
            "rows": seed_rows,
        },
        "support": {
            "attempted_pairs": len(pairs),
            "supported_pairs": len(supported),
        },
        "verdict": "diagnostic_complete_no_training",
    }
    encoded = _canonical_bytes(report)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(encoded)
    return {
        "advantage_by_family": by_family,
        "censored_pairs": len(censored),
        "gradient_diagnostics": report["gradient_diagnostics"],
        "objective": report["objective"],
        "output": _file_binding(output_path),
        "seed_correlation": report["seed_level"][
            "card_advantage_mean_vs_floor_difference_correlation"
        ],
        "supported_pairs": len(supported),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--registration", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-seconds", type=float, default=3600.0)
    args = parser.parse_args()
    result = run_diagnostic(
        repo_root=args.repo_root.resolve(),
        registration_path=args.registration.resolve(),
        checkpoint_path=args.checkpoint.resolve(),
        output_path=args.output.resolve(),
        maximum_seconds=args.maximum_seconds,
    )
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
