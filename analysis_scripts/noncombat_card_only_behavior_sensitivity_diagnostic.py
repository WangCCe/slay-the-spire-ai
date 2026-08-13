"""Compare entry and final card policies on the fixed validation probe."""

from __future__ import annotations

import argparse
from collections import defaultdict
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import types
from typing import Any, Mapping, Sequence

import torch


def _bootstrap_direct_script_imports() -> None:
    if __package__:
        return
    repo_root = Path(__file__).resolve().parents[1]
    package_root = repo_root / "analysis_scripts"
    package = types.ModuleType("analysis_scripts")
    package.__file__ = str(package_root / "__init__.py")
    package.__package__ = "analysis_scripts"
    package.__path__ = [str(package_root)]
    package.__spec__ = importlib.util.spec_from_loader(
        "analysis_scripts", loader=None, is_package=True
    )
    sys.modules["analysis_scripts"] = package
    sys.path.append(str(repo_root))


if __name__ == "__main__":
    _bootstrap_direct_script_imports()

from analysis_scripts import noncombat_card_acceptance_empirical_successor_runtime as runtime
from analysis_scripts import noncombat_card_only_behavior_sensitivity_runner as runner
from analysis_scripts import noncombat_card_only_behavior_sensitivity_training as training
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts.noncombat_card_acceptance_objective import (
    build_card_acceptance_policy_terms,
)


SCHEMA_VERSION = "noncombat-card-only-function-space-diagnostic-v1"
DEFAULT_EXPERIMENT_DIR = Path(
    "reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1"
)
DEFAULT_REGISTRATION = Path(
    "reports/noncombat_card_only_behavior_sensitivity_training_20260813_r1_registration.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_card_only_behavior_sensitivity_function_space_diagnostic_20260813"
)
BOUNDARY_THRESHOLDS = (0.05, 0.10, 0.25, 0.50, 1.00)
FALSE_AUTHORITY = {
    "causal_claim": False,
    "formal_rl": False,
    "fresh_evaluation": False,
    "gameplay": False,
    "policy_quality": False,
    "production_model_loading": False,
    "promotion": False,
    "qualification": False,
    "training": False,
}


class FunctionSpaceDiagnosticBlocked(RuntimeError):
    """Raised when the fixed diagnostic inputs or calculations differ."""


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("ascii")
    except (TypeError, ValueError) as exc:
        raise FunctionSpaceDiagnosticBlocked("diagnostic output is not canonical") from exc


def _binding(path: Path | str) -> dict[str, Any]:
    resolved = Path(path).resolve()
    payload = resolved.read_bytes()
    return {
        "path": str(resolved),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _source_identity() -> dict[str, Any]:
    root = Path(__file__).resolve().parents[1]
    try:
        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError) as exc:
        raise FunctionSpaceDiagnosticBlocked("diagnostic source commit is unavailable") from exc
    if len(commit) != 40 or any(character not in "0123456789abcdef" for character in commit):
        raise FunctionSpaceDiagnosticBlocked("diagnostic source commit is invalid")
    return {"commit": commit, "script": _binding(Path(__file__))}


def _read_canonical(path: Path | str) -> dict[str, Any]:
    payload = Path(path).read_bytes()
    try:
        value = json.loads(payload.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FunctionSpaceDiagnosticBlocked(f"invalid JSON input: {path}") from exc
    if not isinstance(value, dict) or _canonical_bytes(value) != payload:
        raise FunctionSpaceDiagnosticBlocked(f"non-canonical JSON input: {path}")
    return value


def _finite_float(value: Any, label: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise FunctionSpaceDiagnosticBlocked(f"{label} must be numeric") from exc
    if not math.isfinite(result):
        raise FunctionSpaceDiagnosticBlocked(f"{label} must be finite")
    return result


def _distribution_metrics(
    entry: Sequence[float], final: Sequence[float]
) -> dict[str, float]:
    left = tuple(_finite_float(value, "entry probability") for value in entry)
    right = tuple(_finite_float(value, "final probability") for value in final)
    if not left or len(left) != len(right):
        raise FunctionSpaceDiagnosticBlocked("probability shapes differ")
    if any(value <= 0.0 for value in (*left, *right)):
        raise FunctionSpaceDiagnosticBlocked("probabilities must be positive")
    if not math.isclose(math.fsum(left), 1.0, abs_tol=1e-10) or not math.isclose(
        math.fsum(right), 1.0, abs_tol=1e-10
    ):
        raise FunctionSpaceDiagnosticBlocked("probabilities must sum to one")
    entry_to_final_kl = math.fsum(
        p * (math.log(p) - math.log(q)) for p, q in zip(left, right, strict=True)
    )
    final_to_entry_kl = math.fsum(
        q * (math.log(q) - math.log(p)) for p, q in zip(left, right, strict=True)
    )
    return {
        "entry_to_final_kl": entry_to_final_kl,
        "final_to_entry_kl": final_to_entry_kl,
        "symmetric_kl": 0.5 * (entry_to_final_kl + final_to_entry_kl),
        "total_variation": 0.5
        * math.fsum(abs(p - q) for p, q in zip(left, right, strict=True)),
    }


def _top_gap(values: torch.Tensor, indices: Sequence[int] | None = None) -> float | None:
    selected = values.detach().to(dtype=torch.float64, device="cpu")
    if indices is not None:
        selected = selected.index_select(0, torch.tensor(tuple(indices), dtype=torch.long))
    if selected.ndim != 1 or selected.shape[0] == 0 or not torch.isfinite(selected).all():
        raise FunctionSpaceDiagnosticBlocked("margin logits are invalid")
    if selected.shape[0] == 1:
        return None
    ordered = torch.sort(selected, descending=True).values
    return float((ordered[0] - ordered[1]).item())


def _policy_surface(bootstrap: Any, rows: Sequence[Any]) -> tuple[dict[str, Any], ...]:
    policy = bootstrap.candidate.card_policy
    before = pilot.encode_candidate_card_policy(bootstrap)
    policy.eval()
    values: list[dict[str, Any]] = []
    with torch.no_grad():
        for row in rows:
            output = policy(
                row.state_features,
                row.candidate_features,
                row.candidates,
                category="card_reward",
            )
            provisional = build_card_acceptance_policy_terms(
                output.family_logits,
                output.conditional_logits,
                row.candidates,
                row.candidates[0]["action_id"],
                category="card_reward",
            )
            action_id = runtime.select_two_stage_action(provisional, greedy=True)
            terms = build_card_acceptance_policy_terms(
                output.family_logits,
                output.conditional_logits,
                row.candidates,
                action_id,
                category="card_reward",
            )
            family_indices = tuple(
                index
                for index, family in enumerate(terms.candidate_families)
                if family == terms.selected_family
            )
            family_margin = _top_gap(output.family_logits)
            conditional_margin = _top_gap(
                output.conditional_logits, indices=family_indices
            )
            finite_margins = tuple(
                margin
                for margin in (family_margin, conditional_margin)
                if margin is not None
            )
            if not finite_margins:
                raise FunctionSpaceDiagnosticBlocked("two-stage margin is unavailable")
            target_index = terms.action_ids.index(row.target_action_id)
            target_family_index = terms.family_order.index(row.target_family)
            values.append(
                {
                    "acceptance_coordinate": None
                    if terms.acceptance_coordinate is None
                    else float(terms.acceptance_coordinate.item()),
                    "action_id": action_id,
                    "conditional_margin": conditional_margin,
                    "decision_index": row.decision_index,
                    "family": terms.selected_family,
                    "family_entropy": float(terms.family_entropy.item()),
                    "family_margin": family_margin,
                    "family_order": list(terms.family_order),
                    "family_probabilities": terms.family_probabilities.tolist(),
                    "joint_entropy": float(terms.joint_entropy.item()),
                    "joint_probabilities": terms.joint_probabilities.tolist(),
                    "seed": row.seed,
                    "target_action_id": row.target_action_id,
                    "target_family": row.target_family,
                    "target_family_probability": float(
                        terms.family_probabilities[target_family_index].item()
                    ),
                    "target_joint_probability": float(
                        terms.joint_probabilities[target_index].item()
                    ),
                    "two_stage_margin": min(finite_margins),
                }
            )
    if pilot.encode_candidate_card_policy(bootstrap) != before:
        raise FunctionSpaceDiagnosticBlocked("surface evaluation mutated the model")
    return tuple(values)


def _describe(values: Sequence[float]) -> dict[str, float | int]:
    normalized = sorted(_finite_float(value, "summary value") for value in values)
    if not normalized:
        raise FunctionSpaceDiagnosticBlocked("summary values are empty")

    def quantile(fraction: float) -> float:
        position = fraction * (len(normalized) - 1)
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return normalized[lower]
        weight = position - lower
        return normalized[lower] * (1.0 - weight) + normalized[upper] * weight

    return {
        "count": len(normalized),
        "max": normalized[-1],
        "mean": math.fsum(normalized) / len(normalized),
        "median": quantile(0.5),
        "min": normalized[0],
        "p90": quantile(0.9),
        "p99": quantile(0.99),
    }


def _compare_surfaces(
    entry: Sequence[Mapping[str, Any]], final: Sequence[Mapping[str, Any]]
) -> tuple[dict[str, Any], ...]:
    if len(entry) != len(final) or not entry:
        raise FunctionSpaceDiagnosticBlocked("surface row counts differ")
    rows: list[dict[str, Any]] = []
    for left, right in zip(entry, final, strict=True):
        identity = (left["seed"], left["decision_index"])
        if identity != (right["seed"], right["decision_index"]):
            raise FunctionSpaceDiagnosticBlocked("surface row identities differ")
        if left["family_order"] != right["family_order"]:
            raise FunctionSpaceDiagnosticBlocked("surface family order differs")
        family = _distribution_metrics(
            left["family_probabilities"], right["family_probabilities"]
        )
        joint = _distribution_metrics(
            left["joint_probabilities"], right["joint_probabilities"]
        )
        entry_acceptance = left["acceptance_coordinate"]
        final_acceptance = right["acceptance_coordinate"]
        if (entry_acceptance is None) != (final_acceptance is None):
            raise FunctionSpaceDiagnosticBlocked("acceptance activity differs")
        acceptance_delta = None
        if entry_acceptance is not None:
            acceptance_delta = _finite_float(
                final_acceptance, "final acceptance"
            ) - _finite_float(entry_acceptance, "entry acceptance")
        entry_margin = _finite_float(left["two_stage_margin"], "entry margin")
        final_margin = _finite_float(right["two_stage_margin"], "final margin")
        entry_target_family_probability = _finite_float(
            left["target_family_probability"], "entry target family probability"
        )
        final_target_family_probability = _finite_float(
            right["target_family_probability"], "final target family probability"
        )
        entry_target_joint_probability = _finite_float(
            left["target_joint_probability"], "entry target joint probability"
        )
        final_target_joint_probability = _finite_float(
            right["target_joint_probability"], "final target joint probability"
        )
        if min(
            entry_target_family_probability,
            final_target_family_probability,
            entry_target_joint_probability,
            final_target_joint_probability,
        ) <= 0.0:
            raise FunctionSpaceDiagnosticBlocked("target probabilities must be positive")
        rows.append(
            {
                "acceptance_coordinate_delta": acceptance_delta,
                "action_flip": left["action_id"] != right["action_id"],
                "decision_index": identity[1],
                "entry_action_id": left["action_id"],
                "entry_family": left["family"],
                "entry_two_stage_margin": entry_margin,
                "entry_target_family_probability": entry_target_family_probability,
                "entry_target_joint_probability": entry_target_joint_probability,
                "family_flip": left["family"] != right["family"],
                "family_symmetric_kl": family["symmetric_kl"],
                "family_total_variation": family["total_variation"],
                "final_action_id": right["action_id"],
                "final_family": right["family"],
                "final_two_stage_margin": final_margin,
                "final_target_family_probability": final_target_family_probability,
                "final_target_joint_probability": final_target_joint_probability,
                "joint_symmetric_kl": joint["symmetric_kl"],
                "joint_total_variation": joint["total_variation"],
                "margin_delta": final_margin - entry_margin,
                "moved_toward_boundary": final_margin < entry_margin,
                "seed": identity[0],
                "target_action_id": left["target_action_id"],
                "target_family": left["target_family"],
                "target_family_log_probability_delta": math.log(
                    final_target_family_probability
                )
                - math.log(entry_target_family_probability),
                "target_joint_log_probability_delta": math.log(
                    final_target_joint_probability
                )
                - math.log(entry_target_joint_probability),
            }
        )
    return tuple(rows)


def _breakdown(rows: Sequence[Mapping[str, Any]], field: str) -> dict[str, Any]:
    grouped: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        grouped[str(row[field])].append(row)
    return {
        key: {
            "action_flips": sum(bool(row["action_flip"]) for row in group),
            "count": len(group),
            "mean_abs_acceptance_delta": math.fsum(
                abs(float(row["acceptance_coordinate_delta"]))
                for row in group
                if row["acceptance_coordinate_delta"] is not None
            )
            / max(
                1,
                sum(row["acceptance_coordinate_delta"] is not None for row in group),
            ),
            "mean_joint_symmetric_kl": math.fsum(
                float(row["joint_symmetric_kl"]) for row in group
            )
            / len(group),
            "moved_toward_boundary": sum(
                bool(row["moved_toward_boundary"]) for row in group
            ),
        }
        for key, group in sorted(grouped.items())
    }


def _parameter_movement(entry_model: bytes, final_model: bytes) -> dict[str, Any]:
    try:
        entry = json.loads(entry_model.decode("ascii"))
        final = json.loads(final_model.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FunctionSpaceDiagnosticBlocked("candidate model encoding is invalid") from exc
    if set(entry) != set(final):
        raise FunctionSpaceDiagnosticBlocked("candidate model fields differ")
    heads: dict[str, Any] = {}
    all_squares: list[float] = []
    for head in ("conditional_ranker", "family_head"):
        if set(entry[head]) != set(final[head]):
            raise FunctionSpaceDiagnosticBlocked("candidate parameter fields differ")
        tensors = {}
        head_squares: list[float] = []
        head_entry_squares: list[float] = []
        for name in sorted(entry[head]):
            left = entry[head][name]
            right = final[head][name]
            if left["dtype"] != right["dtype"] or left["shape"] != right["shape"]:
                raise FunctionSpaceDiagnosticBlocked("candidate parameter shape differs")
            differences = tuple(
                _finite_float(b, "final parameter")
                - _finite_float(a, "entry parameter")
                for a, b in zip(left["values"], right["values"], strict=True)
            )
            squares = [value * value for value in differences]
            entry_squares = [float(value) ** 2 for value in left["values"]]
            delta_l2 = math.sqrt(math.fsum(squares))
            entry_l2 = math.sqrt(math.fsum(entry_squares))
            tensors[name] = {
                "delta_l2": delta_l2,
                "entry_l2": entry_l2,
                "relative_delta_l2": delta_l2 / max(entry_l2, 1e-12),
                "shape": left["shape"],
            }
            head_squares.extend(squares)
            head_entry_squares.extend(entry_squares)
        all_squares.extend(head_squares)
        delta_l2 = math.sqrt(math.fsum(head_squares))
        entry_l2 = math.sqrt(math.fsum(head_entry_squares))
        heads[head] = {
            "delta_l2": delta_l2,
            "entry_l2": entry_l2,
            "relative_delta_l2": delta_l2 / max(entry_l2, 1e-12),
            "tensors": tensors,
        }
    return {"global_delta_l2": math.sqrt(math.fsum(all_squares)), "heads": heads}


def _model_values(model: bytes) -> tuple[float, ...]:
    try:
        value = json.loads(model.decode("ascii"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FunctionSpaceDiagnosticBlocked("candidate model encoding is invalid") from exc
    values: list[float] = []
    for head in ("conditional_ranker", "family_head"):
        for name in sorted(value[head]):
            values.extend(
                _finite_float(item, "candidate parameter")
                for item in value[head][name]["values"]
            )
    if not values:
        raise FunctionSpaceDiagnosticBlocked("candidate model parameters are empty")
    return tuple(values)


def _vector_delta(left: Sequence[float], right: Sequence[float]) -> tuple[float, ...]:
    if len(left) != len(right) or not left:
        raise FunctionSpaceDiagnosticBlocked("parameter vector shapes differ")
    return tuple(b - a for a, b in zip(left, right, strict=True))


def _vector_l2(value: Sequence[float]) -> float:
    return math.sqrt(math.fsum(item * item for item in value))


def _cosine(left: Sequence[float], right: Sequence[float]) -> float | None:
    if len(left) != len(right) or not left:
        raise FunctionSpaceDiagnosticBlocked("update vector shapes differ")
    left_l2 = _vector_l2(left)
    right_l2 = _vector_l2(right)
    if left_l2 == 0.0 or right_l2 == 0.0:
        return None
    value = math.fsum(a * b for a, b in zip(left, right, strict=True)) / (
        left_l2 * right_l2
    )
    return max(-1.0, min(1.0, value))


def _checkpoint_index(path: Path) -> int:
    parts = path.stem.split("_")
    if len(parts) != 2 or parts[0] != "checkpoint" or not parts[1].isdigit():
        raise FunctionSpaceDiagnosticBlocked("trajectory checkpoint name differs")
    return int(parts[1])


def _checkpoint_trajectory(
    paths: Sequence[Path],
    *,
    probe_rows: Sequence[Any],
    entry_model: bytes,
) -> dict[str, Any]:
    ordered = tuple(sorted((Path(path).resolve() for path in paths), key=_checkpoint_index))
    expected = tuple(range(training.FIRST_CHUNK_INDEX, training.FINAL_CHUNK_INDEX + 1))
    if tuple(_checkpoint_index(path) for path in ordered) != expected:
        raise FunctionSpaceDiagnosticBlocked("trajectory checkpoint coordinates differ")
    entry_values = _model_values(entry_model)
    entry_surface: tuple[dict[str, Any], ...] | None = None
    previous_values: tuple[float, ...] | None = None
    previous_surface: tuple[dict[str, Any], ...] | None = None
    previous_delta: tuple[float, ...] | None = None
    points: list[dict[str, Any]] = []
    path_length = 0.0
    cosines: list[float] = []
    for path in ordered:
        restored = training.restore_behavior_sensitivity_checkpoint(
            path.read_bytes(), probe_rows=probe_rows, entry_model=entry_model
        )
        index = _checkpoint_index(path)
        if restored.next_chunk_index != index:
            raise FunctionSpaceDiagnosticBlocked("trajectory checkpoint state differs")
        model = pilot.encode_candidate_card_policy(restored.bootstrap)
        current_values = _model_values(model)
        surface = _policy_surface(restored.bootstrap, probe_rows)
        if entry_surface is None:
            entry_surface = surface
        from_entry = _compare_surfaces(entry_surface, surface)
        from_entry_summary = _build_summary(from_entry)
        step_l2 = 0.0
        step_cosine = None
        previous_action_flips = 0
        previous_joint_kl = 0.0
        if previous_values is not None and previous_surface is not None:
            delta = _vector_delta(previous_values, current_values)
            step_l2 = _vector_l2(delta)
            path_length += step_l2
            step_cosine = None if previous_delta is None else _cosine(previous_delta, delta)
            if step_cosine is not None:
                cosines.append(step_cosine)
            previous_comparison = _compare_surfaces(previous_surface, surface)
            previous_summary = _build_summary(previous_comparison)
            previous_action_flips = int(previous_summary["action_flips"])
            previous_joint_kl = float(previous_summary["joint_symmetric_kl"]["mean"])
            previous_delta = delta
        points.append(
            {
                "action_flips_from_entry": from_entry_summary["action_flips"],
                "action_flips_from_previous": previous_action_flips,
                "checkpoint": _binding(path),
                "checkpoint_index": index,
                "consecutive_update_cosine": step_cosine,
                "mean_joint_symmetric_kl_from_entry": from_entry_summary[
                    "joint_symmetric_kl"
                ]["mean"],
                "mean_joint_symmetric_kl_from_previous": previous_joint_kl,
                "mean_joint_total_variation_from_entry": from_entry_summary[
                    "joint_total_variation"
                ]["mean"],
                "model_sha256": hashlib.sha256(model).hexdigest(),
                "moved_toward_entry_boundary": from_entry_summary[
                    "moved_toward_boundary"
                ],
                "parameter_l2_from_entry": _vector_l2(
                    _vector_delta(entry_values, current_values)
                ),
                "parameter_step_l2": step_l2,
            }
        )
        previous_values = current_values
        previous_surface = surface
    net_distance = float(points[-1]["parameter_l2_from_entry"])
    return {
        "points": points,
        "summary": {
            "checkpoint_count": len(points),
            "consecutive_update_cosine": None if not cosines else _describe(cosines),
            "negative_consecutive_update_cosines": sum(value < 0.0 for value in cosines),
            "net_parameter_distance": net_distance,
            "parameter_path_length": path_length,
            "path_to_net_ratio": path_length / max(net_distance, 1e-12),
        },
    }


def _build_summary(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    acceptance_deltas = [
        abs(float(row["acceptance_coordinate_delta"]))
        for row in rows
        if row["acceptance_coordinate_delta"] is not None
    ]
    return {
        "acceptance_absolute_delta": _describe(acceptance_deltas),
        "action_flips": sum(bool(row["action_flip"]) for row in rows),
        "boundary_counts": {
            f"le_{threshold:.2f}": sum(
                float(row["final_two_stage_margin"]) <= threshold for row in rows
            )
            for threshold in BOUNDARY_THRESHOLDS
        },
        "entry_two_stage_margin": _describe(
            [float(row["entry_two_stage_margin"]) for row in rows]
        ),
        "family_flips": sum(bool(row["family_flip"]) for row in rows),
        "family_symmetric_kl": _describe(
            [float(row["family_symmetric_kl"]) for row in rows]
        ),
        "final_two_stage_margin": _describe(
            [float(row["final_two_stage_margin"]) for row in rows]
        ),
        "joint_symmetric_kl": _describe(
            [float(row["joint_symmetric_kl"]) for row in rows]
        ),
        "joint_total_variation": _describe(
            [float(row["joint_total_variation"]) for row in rows]
        ),
        "moved_toward_boundary": sum(
            bool(row["moved_toward_boundary"]) for row in rows
        ),
        "probe_rows": len(rows),
        "target_family_log_probability_delta": _describe(
            [float(row["target_family_log_probability_delta"]) for row in rows]
        ),
        "target_family_probability_improved": sum(
            float(row["target_family_log_probability_delta"]) > 0.0 for row in rows
        ),
        "target_joint_log_probability_delta": _describe(
            [float(row["target_joint_log_probability_delta"]) for row in rows]
        ),
        "target_joint_probability_improved": sum(
            float(row["target_joint_log_probability_delta"]) > 0.0 for row in rows
        ),
    }


def _render_markdown(report: Mapping[str, Any]) -> str:
    summary = report["surface_summary"]
    movement = report["parameter_movement"]
    family = movement["heads"]["family_head"]
    conditional = movement["heads"]["conditional_ranker"]
    trajectory = report["checkpoint_trajectory"]["summary"]
    lines = [
        "# Card-only behavior sensitivity function-space diagnostic",
        "",
        "## Result",
        "",
        f"- Probe rows: {summary['probe_rows']}",
        f"- Exact action flips: {summary['action_flips']}",
        f"- Family flips: {summary['family_flips']}",
        f"- Global parameter L2 movement: {movement['global_delta_l2']:.9f}",
        f"- Mean joint symmetric KL: {summary['joint_symmetric_kl']['mean']:.9f}",
        f"- Max joint symmetric KL: {summary['joint_symmetric_kl']['max']:.9f}",
        f"- Mean joint total variation: {summary['joint_total_variation']['mean']:.9f}",
        f"- Rows moving toward a greedy boundary: {summary['moved_toward_boundary']}",
        f"- Final two-stage margin median: {summary['final_two_stage_margin']['median']:.9f}",
        f"- Parameter path/net ratio: {trajectory['path_to_net_ratio']:.6f}",
        f"- Negative consecutive update cosines: {trajectory['negative_consecutive_update_cosines']}",
        f"- Mean Bottled target joint log-probability delta: {summary['target_joint_log_probability_delta']['mean']:.9f}",
        f"- Bottled target joint probability improved rows: {summary['target_joint_probability_improved']}/{summary['probe_rows']}",
        "",
        "## Parameter movement",
        "",
        f"- Family head L2: {family['delta_l2']:.9f} ({family['relative_delta_l2']:.6f} relative)",
        f"- Conditional ranker L2: {conditional['delta_l2']:.9f} ({conditional['relative_delta_l2']:.6f} relative)",
        "",
        "## Evidence coverage",
        "",
        "- Entry and final model bytes, fixed probe rows, probabilities, entropies, and greedy margins are available.",
        "- Per-step advantages, component gradients, and clipping evidence were produced in memory but were not persisted by the r1 runner.",
        "- This diagnostic therefore identifies where the policy function moved; it cannot retrospectively attribute that movement to advantage scaling or clipping.",
        "",
        "## Decision boundary",
        "",
        "- No checkpoint is selected and no training, native environment, fresh evaluation, gameplay, or production loading is authorized.",
        "- Use the measured distribution and margin movement to choose one separately registered training change.",
        "",
    ]
    return "\n".join(lines)


def build_report(
    *,
    registration_path: Path,
    entry_checkpoint_path: Path,
    final_checkpoint_path: Path,
    trajectory_checkpoint_paths: Sequence[Path],
) -> dict[str, Any]:
    registration = _read_canonical(registration_path)
    probe_rows, initialized = runner._load_probe_and_entry(registration)
    entry = training.restore_behavior_sensitivity_checkpoint(
        entry_checkpoint_path.read_bytes(),
        probe_rows=probe_rows,
        entry_model=initialized.entry_model,
    )
    final = training.restore_behavior_sensitivity_checkpoint(
        final_checkpoint_path.read_bytes(),
        probe_rows=probe_rows,
        entry_model=initialized.entry_model,
    )
    if entry.next_chunk_index != training.FIRST_CHUNK_INDEX:
        raise FunctionSpaceDiagnosticBlocked("entry checkpoint coordinate differs")
    if final.next_chunk_index != training.FINAL_CHUNK_INDEX:
        raise FunctionSpaceDiagnosticBlocked("final checkpoint coordinate differs")
    entry_surface = _policy_surface(entry.bootstrap, probe_rows)
    final_surface = _policy_surface(final.bootstrap, probe_rows)
    rows = _compare_surfaces(entry_surface, final_surface)
    final_model = pilot.encode_candidate_card_policy(final.bootstrap)
    persisted_update_fields = set().union(
        *(set(summary) for summary in final.completed_summaries)
    )
    return {
        "authority": copy.deepcopy(FALSE_AUTHORITY),
        "breakdowns": {
            "entry_family": _breakdown(rows, "entry_family"),
            "target_family": _breakdown(rows, "target_family"),
        },
        "checkpoint_trajectory": _checkpoint_trajectory(
            trajectory_checkpoint_paths,
            probe_rows=probe_rows,
            entry_model=initialized.entry_model,
        ),
        "evidence_coverage": {
            "advantage_summaries_persisted": "advantages" in persisted_update_fields,
            "gradient_clip_summaries_persisted": "optimizer_step" in persisted_update_fields,
            "optimizer_step_evidence_was_runtime_only": True,
            "persisted_chunk_summary_fields": sorted(persisted_update_fields),
        },
        "inputs": {
            "entry_checkpoint": _binding(entry_checkpoint_path),
            "entry_model_sha256": hashlib.sha256(initialized.entry_model).hexdigest(),
            "final_checkpoint": _binding(final_checkpoint_path),
            "final_model_sha256": hashlib.sha256(final_model).hexdigest(),
            "registration": _binding(registration_path),
        },
        "operations": {
            "environment_construction": False,
            "model_loading": True,
            "native_loading": False,
            "seed_access": False,
            "training": False,
        },
        "parameter_movement": _parameter_movement(initialized.entry_model, final_model),
        "rows": list(rows),
        "schema_version": SCHEMA_VERSION,
        "source": _source_identity(),
        "surface_summary": _build_summary(rows),
        "verdict": "function_space_diagnostic_complete_no_training_authority",
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, default=DEFAULT_REGISTRATION)
    parser.add_argument(
        "--entry-checkpoint",
        type=Path,
        default=DEFAULT_EXPERIMENT_DIR / "checkpoint_004.json",
    )
    parser.add_argument(
        "--final-checkpoint",
        type=Path,
        default=DEFAULT_EXPERIMENT_DIR / "checkpoint_020.json",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    output = args.output_dir.resolve()
    output.mkdir(parents=True, exist_ok=False)
    report = build_report(
        registration_path=args.registration.resolve(),
        entry_checkpoint_path=args.entry_checkpoint.resolve(),
        final_checkpoint_path=args.final_checkpoint.resolve(),
        trajectory_checkpoint_paths=tuple(
            args.entry_checkpoint.resolve().parent.glob("checkpoint_*.json")
        ),
    )
    payload = _canonical_bytes(report)
    (output / "report.json").write_bytes(payload)
    (output / "report.md").write_text(
        _render_markdown(report), encoding="ascii", newline="\n"
    )
    print(
        json.dumps(
            {
                "output_dir": str(output),
                "report_sha256": hashlib.sha256(payload).hexdigest(),
                "verdict": report["verdict"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
