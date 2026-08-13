"""Train the existing state-conditioned card heads on the merged large corpus."""

from __future__ import annotations

import argparse
import copy
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import subprocess
import sys
import types
from collections.abc import Mapping, Sequence
from typing import Any

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
from analysis_scripts import noncombat_card_counterfactual_ranking_training as ranking
from analysis_scripts import noncombat_card_counterfactual_uplift_residual_crossfit as uplift
from analysis_scripts import noncombat_card_only_native_baseline_rl_pilot as pilot
from analysis_scripts import noncombat_large_corpus_card_uplift_residual as residual


SCHEMA_VERSION = "noncombat-large-corpus-state-conditioned-card-ranking-v1"
CONFIGURATION_SCHEMA_VERSION = f"{SCHEMA_VERSION}-configuration"
FOLDS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-folds"
METRICS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-metrics"
PREDICTIONS_SCHEMA_VERSION = f"{SCHEMA_VERSION}-predictions"
REPORT_SCHEMA_VERSION = f"{SCHEMA_VERSION}-report"
MANIFEST_SCHEMA_VERSION = f"{SCHEMA_VERSION}-manifest"
MODEL_SCHEMA_VERSION = f"{SCHEMA_VERSION}-model"

FOLD_COUNT = 5
BATCH_SIZE = 64
EPOCH_CHECKPOINTS = (1, 2, 4, 8)
MIN_CROSSFIT_CORRECTED_ACTIONS = 8
MIN_DEVELOPMENT_CORRECTED_ACTIONS = 4
EXPECTED_TRAIN_ROWS = 773
EXPECTED_DEVELOPMENT_ROWS = 190
EXPECTED_INFORMATIVE_TRAIN_ROWS = 542
EXPECTED_TRAIN_SEED_COUNT = 434
EXPECTED_INFORMATIVE_TRAIN_SEED_COUNT = 347
MAX_MODEL_BYTES = 64 * 1024 * 1024
MAX_REPORT_BYTES = 4 * 1024 * 1024

DEFAULT_CORPUS_ROOT = residual.DEFAULT_CORPUS_ROOT
DEFAULT_RARE_CORPUS_ROOT = residual.DEFAULT_RARE_CORPUS_ROOT
DEFAULT_OUTPUT_DIR = Path(
    "reports/noncombat_large_corpus_state_conditioned_card_ranking_20260814_r1"
)
SOURCE_PATHS = tuple(
    sorted(
        {
            *residual.SOURCE_PATHS,
            "analysis_scripts/noncombat_large_corpus_state_conditioned_card_ranking.py",
        }
    )
)
AUTHORITY = {
    name: False
    for name in (
        "audit_access",
        "causal_claim",
        "communication_mod",
        "formal_rl",
        "fresh_evaluation",
        "gameplay",
        "native_loading",
        "ope",
        "policy_quality",
        "production_model_loading",
        "promotion",
        "qualification",
    )
}
OPERATIONS = {
    "audit_access": False,
    "communication_mod": False,
    "development_evaluation": True,
    "environment_construction": False,
    "gameplay": False,
    "model_fitting": True,
    "model_loading": True,
    "native_loading": False,
    "ope": False,
    "production_model_loading": False,
    "seed_access": False,
    "training": True,
}


class StateConditionedRankingBlocked(RuntimeError):
    """Raised when the fixed large-corpus ranking contract cannot proceed."""


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
        raise StateConditionedRankingBlocked("artifact is not canonical") from exc


def _binding(path: Path | str) -> dict[str, Any]:
    source = Path(path).resolve()
    try:
        payload = source.read_bytes()
    except OSError as exc:
        raise StateConditionedRankingBlocked(f"input is unavailable: {source}") from exc
    return {
        "path": source.as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _source_bindings(root: Path, source_commit: str) -> dict[str, Any]:
    try:
        if (
            subprocess.run(
                ["git", "cat-file", "-t", source_commit],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            != "commit"
        ):
            raise StateConditionedRankingBlocked("source commit is unavailable")
        subprocess.run(
            ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise StateConditionedRankingBlocked(
            "source commit is not an ancestor"
        ) from exc
    bindings: dict[str, Any] = {}
    for relative in SOURCE_PATHS:
        actual = _binding(root / relative)
        try:
            committed = subprocess.run(
                ["git", "show", f"{source_commit}:{relative}"],
                cwd=root,
                check=True,
                capture_output=True,
            ).stdout
        except (OSError, subprocess.CalledProcessError) as exc:
            raise StateConditionedRankingBlocked(
                f"source path is unavailable at commit: {relative}"
            ) from exc
        if hashlib.sha256(committed).hexdigest() != actual["sha256"]:
            raise StateConditionedRankingBlocked(f"source bytes differ: {relative}")
        bindings[relative] = actual
    return bindings


def _row_key(row: ranking.CounterfactualRankingRow) -> tuple[int, int, str]:
    return row.seed, row.decision_index, row.source_sha256


def informative_rows(
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> tuple[ranking.CounterfactualRankingRow, ...]:
    normalized = uplift.validate_rows(rows)
    return tuple(
        sorted(
            (
                row
                for row in normalized
                if max(row.action_returns) > min(row.action_returns)
            ),
            key=_row_key,
        )
    )


def deterministic_batches(
    rows: Sequence[ranking.CounterfactualRankingRow],
    *,
    batch_size: int = BATCH_SIZE,
) -> tuple[tuple[ranking.CounterfactualRankingRow, ...], ...]:
    if isinstance(batch_size, bool) or not isinstance(batch_size, int) or batch_size <= 0:
        raise StateConditionedRankingBlocked("batch size differs")
    ordered = informative_rows(rows)
    if not ordered:
        raise StateConditionedRankingBlocked("training rows are uninformative")
    return tuple(
        tuple(ordered[index : index + batch_size])
        for index in range(0, len(ordered), batch_size)
    )


def _optimizer_parameters(
    bootstrap: runtime.PairedBootstrap,
    optimizer: torch.optim.Optimizer,
) -> tuple[torch.nn.Parameter, ...]:
    try:
        parameters = runtime._validated_registered_adam(optimizer)
    except runtime.SuccessorRuntimeError as exc:
        raise StateConditionedRankingBlocked(str(exc)) from exc
    expected = tuple(bootstrap.candidate.card_policy.family_head.parameters()) + tuple(
        bootstrap.candidate.card_policy.conditional_ranker.parameters()
    )
    if tuple(map(id, parameters)) != tuple(map(id, expected)):
        raise StateConditionedRankingBlocked("optimizer ownership differs")
    return parameters


def _optimizer_state_is_finite(value: Any) -> bool:
    if isinstance(value, torch.Tensor):
        return bool(torch.isfinite(value).all().item())
    if isinstance(value, float):
        return math.isfinite(value)
    if isinstance(value, Mapping):
        return all(_optimizer_state_is_finite(item) for item in value.values())
    if isinstance(value, (tuple, list)):
        return all(_optimizer_state_is_finite(item) for item in value)
    return isinstance(value, (bool, int, str)) or value is None


def train_one_epoch(
    bootstrap: runtime.PairedBootstrap,
    optimizer: torch.optim.Optimizer,
    rows: Sequence[ranking.CounterfactualRankingRow],
    *,
    batch_size: int = BATCH_SIZE,
) -> dict[str, Any]:
    parameters = _optimizer_parameters(bootstrap, optimizer)
    entry_card = pilot.encode_candidate_card_policy(bootstrap)
    guard_before = ranking._guard_bytes(bootstrap)
    losses: list[float] = []
    for batch in deterministic_batches(rows, batch_size=batch_size):
        optimizer.zero_grad(set_to_none=True)
        try:
            loss = ranking.pairwise_ranking_loss(bootstrap, batch)
        except ranking.CounterfactualRankingBlocked as exc:
            raise StateConditionedRankingBlocked(str(exc)) from exc
        loss_value = float(loss.detach().item())
        if not math.isfinite(loss_value):
            raise StateConditionedRankingBlocked("training loss is nonfinite")
        loss.backward()
        if any(
            parameter.grad is None
            or not bool(torch.isfinite(parameter.grad).all().item())
            for parameter in parameters
        ):
            raise StateConditionedRankingBlocked("training gradients are invalid")
        optimizer.step()
        if any(not bool(torch.isfinite(parameter).all().item()) for parameter in parameters):
            raise StateConditionedRankingBlocked("trained parameter is nonfinite")
        if not _optimizer_state_is_finite(optimizer.state):
            raise StateConditionedRankingBlocked("optimizer state is nonfinite")
        losses.append(loss_value)
    if ranking._guard_bytes(bootstrap) != guard_before:
        raise StateConditionedRankingBlocked("frozen model state changed")
    if pilot.encode_candidate_card_policy(bootstrap) == entry_card:
        raise StateConditionedRankingBlocked("training did not change card heads")
    return {
        "batch_count": len(losses),
        "maximum_batch_loss": max(losses),
        "mean_batch_loss": math.fsum(losses) / len(losses),
        "minimum_batch_loss": min(losses),
    }


def score_rows(
    bootstrap: runtime.PairedBootstrap,
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> dict[str, tuple[float, ...]]:
    normalized = uplift.validate_rows(rows)
    scores: dict[str, tuple[float, ...]] = {}
    with torch.no_grad():
        for row in normalized:
            try:
                values = tuple(
                    float(value)
                    for value in ranking._joint_log_probabilities(bootstrap, row)
                    .detach()
                    .tolist()
                )
            except ranking.CounterfactualRankingBlocked as exc:
                raise StateConditionedRankingBlocked(str(exc)) from exc
            if len(values) != len(row.candidates) or any(
                not math.isfinite(value) for value in values
            ):
                raise StateConditionedRankingBlocked("model scores differ")
            scores[row.source_sha256] = values
    return scores


def encode_model(bootstrap: runtime.PairedBootstrap) -> bytes:
    try:
        bootstrap_bytes = runtime.encode_paired_bootstrap(bootstrap)
    except runtime.SuccessorRuntimeError as exc:
        raise StateConditionedRankingBlocked(str(exc)) from exc
    payload = _canonical_bytes(
        {
            "bootstrap": json.loads(bootstrap_bytes.decode("ascii")),
            "schema_version": MODEL_SCHEMA_VERSION,
        }
    )
    if len(payload) > MAX_MODEL_BYTES:
        raise StateConditionedRankingBlocked("model exceeds byte bound")
    return payload


def restore_model(payload: bytes) -> runtime.PairedBootstrap:
    try:
        value = json.loads(payload.decode("ascii"))
        if (
            not isinstance(value, dict)
            or set(value) != {"bootstrap", "schema_version"}
            or value["schema_version"] != MODEL_SCHEMA_VERSION
            or _canonical_bytes(value) != payload
        ):
            raise StateConditionedRankingBlocked("model envelope differs")
        bootstrap = runtime.restore_paired_bootstrap(
            _canonical_bytes(value["bootstrap"])
        )
    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
        runtime.SuccessorRuntimeError,
    ) as exc:
        raise StateConditionedRankingBlocked("model restore failed") from exc
    if encode_model(bootstrap) != payload:
        raise StateConditionedRankingBlocked("model round trip differs")
    return bootstrap


def train_checkpoints(
    entry_bytes: bytes,
    *,
    fit_rows: Sequence[ranking.CounterfactualRankingRow],
    score_partition: Sequence[ranking.CounterfactualRankingRow],
    epoch_checkpoints: Sequence[int] = EPOCH_CHECKPOINTS,
    batch_size: int = BATCH_SIZE,
) -> tuple[
    dict[int, dict[str, tuple[float, ...]]],
    list[dict[str, Any]],
    runtime.PairedBootstrap,
]:
    checkpoints = tuple(epoch_checkpoints)
    if (
        not checkpoints
        or tuple(sorted(set(checkpoints))) != checkpoints
        or any(isinstance(epoch, bool) or not isinstance(epoch, int) or epoch <= 0 for epoch in checkpoints)
    ):
        raise StateConditionedRankingBlocked("epoch checkpoints differ")
    model = restore_model(entry_bytes)
    entry_card = pilot.encode_candidate_card_policy(model)
    guard_before = ranking._guard_bytes(model)
    optimizer = runtime.build_candidate_card_optimizer(model)
    if optimizer.state:
        raise StateConditionedRankingBlocked("optimizer must start fresh")
    losses: list[dict[str, Any]] = []
    scores: dict[int, dict[str, tuple[float, ...]]] = {}
    for epoch in range(1, checkpoints[-1] + 1):
        diagnostic = train_one_epoch(
            model, optimizer, fit_rows, batch_size=batch_size
        )
        diagnostic["epoch"] = epoch
        losses.append(diagnostic)
        if epoch in checkpoints:
            scores[epoch] = score_rows(model, score_partition)
    if ranking._guard_bytes(model) != guard_before:
        raise StateConditionedRankingBlocked("frozen model state changed")
    if pilot.encode_candidate_card_policy(model) == entry_card:
        raise StateConditionedRankingBlocked("training did not change card heads")
    return scores, losses, model


def _comparison_checks(
    base: Mapping[str, Any],
    candidate: Mapping[str, Any],
    comparison: Mapping[str, int],
    *,
    minimum_corrected_actions: int,
) -> dict[str, bool]:
    return {
        "corrected_actions": comparison["corrected_actions"]
        >= minimum_corrected_actions,
        "maximum_regret_nonincreasing": candidate["maximum_top_action_regret"]
        <= base["maximum_top_action_regret"],
        "mean_regret_decreased": candidate["mean_top_action_regret"]
        < base["mean_top_action_regret"],
        "pairwise_accuracy_increased": candidate["weighted_pairwise_accuracy"]
        > base["weighted_pairwise_accuracy"],
        "unique_best_accuracy_nondecreasing": candidate["unique_best_accuracy"]
        >= base["unique_best_accuracy"],
        "worsened_actions_bounded": comparison["worsened_actions"]
        <= comparison["corrected_actions"],
    }


def _selection_key(candidate: Mapping[str, Any]) -> tuple[float, float, float, float, int]:
    metrics = candidate["metrics"]
    return (
        float(metrics["mean_top_action_regret"]),
        float(metrics["maximum_top_action_regret"]),
        -float(metrics["weighted_pairwise_accuracy"]),
        -float(metrics["unique_best_accuracy"]),
        int(candidate["epochs"]),
    )


def crossfit_select_epochs(
    entry_bytes: bytes,
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> dict[str, Any]:
    normalized = uplift.validate_rows(rows)
    seeds = sorted({row.seed for row in normalized})
    folds = uplift.build_seed_folds(seeds, FOLD_COUNT)
    entry = restore_model(entry_bytes)
    entry_card = pilot.encode_candidate_card_policy(entry)
    base_scores = score_rows(entry, normalized)
    base_metrics = uplift.evaluate_scores(normalized, base_scores)
    crossfit_scores = {epoch: {} for epoch in EPOCH_CHECKPOINTS}
    fold_losses: list[dict[str, Any]] = []
    for fold_index, fold in enumerate(folds):
        heldout = set(fold)
        fit_rows = tuple(row for row in normalized if row.seed not in heldout)
        heldout_rows = tuple(row for row in normalized if row.seed in heldout)
        scores, losses, _model = train_checkpoints(
            entry_bytes,
            fit_rows=fit_rows,
            score_partition=heldout_rows,
        )
        fold_losses.append(
            {
                "fold_index": fold_index,
                "heldout_seeds": list(fold),
                "losses": losses,
            }
        )
        for epoch in EPOCH_CHECKPOINTS:
            overlap = set(crossfit_scores[epoch]) & set(scores[epoch])
            if overlap:
                raise StateConditionedRankingBlocked(
                    "crossfit source identity repeats"
                )
            crossfit_scores[epoch].update(scores[epoch])
    if pilot.encode_candidate_card_policy(entry) != entry_card:
        raise StateConditionedRankingBlocked("entry model changed during crossfit")
    candidates: list[dict[str, Any]] = []
    for epoch in EPOCH_CHECKPOINTS:
        metrics = uplift.evaluate_scores(normalized, crossfit_scores[epoch])
        comparison = uplift.compare_predictions(base_metrics, metrics)
        checks = _comparison_checks(
            base_metrics,
            metrics,
            comparison,
            minimum_corrected_actions=MIN_CROSSFIT_CORRECTED_ACTIONS,
        )
        candidates.append(
            {
                "checks": checks,
                "comparison": comparison,
                "epochs": epoch,
                "metrics": residual._metrics_without_predictions(metrics),
                "selection_key": list(
                    _selection_key({"epochs": epoch, "metrics": metrics})
                ),
            }
        )
    passing = [candidate for candidate in candidates if all(candidate["checks"].values())]
    selected = min(passing, key=_selection_key) if passing else None
    return {
        "base_metrics": base_metrics,
        "candidates": candidates,
        "crossfit_scores": crossfit_scores,
        "fold_losses": fold_losses,
        "folds": folds,
        "selected_epochs": None if selected is None else selected["epochs"],
        "selected_checks": None if selected is None else selected["checks"],
    }


def _write_artifact(
    staging: Path, output: Path, name: str, payload: bytes
) -> dict[str, Any]:
    byte_limit = MAX_MODEL_BYTES if name == "trained_model.json" else MAX_REPORT_BYTES
    if not payload or len(payload) > byte_limit:
        raise StateConditionedRankingBlocked(f"artifact byte bound differs: {name}")
    (staging / name).write_bytes(payload)
    return {
        "path": (output / name).as_posix(),
        "sha256": hashlib.sha256(payload).hexdigest(),
        "size_bytes": len(payload),
    }


def _validate_train_support(
    rows: Sequence[ranking.CounterfactualRankingRow],
) -> tuple[ranking.CounterfactualRankingRow, ...]:
    normalized = uplift.validate_rows(rows)
    informative = informative_rows(normalized)
    if (
        len(normalized) != EXPECTED_TRAIN_ROWS
        or len(informative) != EXPECTED_INFORMATIVE_TRAIN_ROWS
        or len({row.seed for row in normalized}) != EXPECTED_TRAIN_SEED_COUNT
        or len({row.seed for row in informative})
        != EXPECTED_INFORMATIVE_TRAIN_SEED_COUNT
    ):
        raise StateConditionedRankingBlocked("merged train support differs")
    return normalized


def _configuration(
    *,
    inputs: Mapping[str, Any],
    source: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "authority": copy.deepcopy(AUTHORITY),
        "batch_size": BATCH_SIZE,
        "development_gates": {
            "minimum_corrected_actions": MIN_DEVELOPMENT_CORRECTED_ACTIONS,
            "rare_best_take_to_skip_errors_must_not_increase": True,
            "rare_mean_regret_must_decrease": True,
            "rare_pairwise_accuracy_must_not_decrease": True,
            "worsened_actions_must_not_exceed_corrected": True,
        },
        "epoch_checkpoints": list(EPOCH_CHECKPOINTS),
        "fold_count": FOLD_COUNT,
        "inputs": copy.deepcopy(dict(inputs)),
        "operations": copy.deepcopy(OPERATIONS),
        "optimizer": copy.deepcopy(runtime._REGISTERED_ADAM_OPTIONS),
        "schema_version": CONFIGURATION_SCHEMA_VERSION,
        "selection_gates": {
            "minimum_corrected_actions": MIN_CROSSFIT_CORRECTED_ACTIONS,
            "worsened_actions_must_not_exceed_corrected": True,
        },
        "source": copy.deepcopy(dict(source)),
    }


def _render_report(report: Mapping[str, Any]) -> str:
    lines = [
        "# Large-Corpus State-Conditioned Card Ranking",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Selected epochs: `{report['selected_epochs']}`",
        f"- Development accessed: `{report['development_accessed']}`",
        f"- Audit accessed: `{report['audit_accessed']}`",
        "",
    ]
    if report.get("development_checks") is not None:
        lines.extend(
            [
                f"- Development checks: `{report['development_checks']}`",
                f"- Rare development checks: `{report['rare_development_checks']}`",
                f"- Rare best-take-to-skip errors: `{report['rare_best_take_to_skip_errors']}`",
                "",
            ]
        )
    lines.extend(["## Boundary", "", "- Epoch selection used train seeds only."])
    if report["development_accessed"]:
        lines.append(
            "- The final model was persisted and restored before development access."
        )
    else:
        lines.append("- No final model was fit and development remained unread.")
    lines.extend(
        [
            "- Native code, game, CommunicationMod, and reserved audit seeds were not accessed.",
            "- A positive verdict authorizes only a separate reserved-audit proposal.",
            "",
        ]
    )
    return "\n".join(lines)


def execute(
    *,
    repo_root: Path | str,
    source_commit: str,
    corpus_root: Path | str = DEFAULT_CORPUS_ROOT,
    rare_corpus_root: Path | str = DEFAULT_RARE_CORPUS_ROOT,
    output_dir: Path | str = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    corpus_path = Path(corpus_root).resolve()
    rare_path = Path(rare_corpus_root).resolve()
    output = Path(output_dir).resolve()
    staging = output.with_name(f".{output.name}.{source_commit}.staging")
    if output.exists() or staging.exists():
        raise StateConditionedRankingBlocked("output boundary differs")
    source = {
        "bindings": _source_bindings(root, source_commit),
        "commit": source_commit,
        "repo_root": root.as_posix(),
    }
    existing_train, entry, inputs = residual._load_train_inputs(corpus_path)
    rare_train, rare_inputs = residual._load_rare_train_inputs(rare_path)
    inputs.update(rare_inputs)
    train_rows = _validate_train_support(
        residual._merge_disjoint_rows(existing_train, rare_train)
    )
    entry_bytes = encode_model(entry)
    entry_card = pilot.encode_candidate_card_policy(entry)
    entry_guard = ranking._guard_bytes(entry)
    selection = crossfit_select_epochs(entry_bytes, train_rows)

    staging.mkdir(parents=False, exist_ok=False)
    configuration = _configuration(inputs=inputs, source=source)
    configuration_binding = _write_artifact(
        staging, output, "configuration.json", _canonical_bytes(configuration)
    )
    folds = {
        "candidates": selection["candidates"],
        "fold_losses": selection["fold_losses"],
        "folds": [list(fold) for fold in selection["folds"]],
        "schema_version": FOLDS_SCHEMA_VERSION,
        "selected_epochs": selection["selected_epochs"],
    }
    folds_binding = _write_artifact(
        staging, output, "folds.json", _canonical_bytes(folds)
    )
    crossfit_predictions = {
        str(epoch): uplift.evaluate_scores(
            train_rows, selection["crossfit_scores"][epoch]
        )["predictions"]
        for epoch in EPOCH_CHECKPOINTS
    }
    selected_epochs = selection["selected_epochs"]
    if selected_epochs is None:
        report = {
            "audit_accessed": False,
            "authority": copy.deepcopy(AUTHORITY),
            "development_accessed": False,
            "development_checks": None,
            "operations": copy.deepcopy(OPERATIONS),
            "rare_best_take_to_skip_errors": None,
            "rare_development_checks": None,
            "schema_version": REPORT_SCHEMA_VERSION,
            "selected_epochs": None,
            "train_only_stop": True,
            "verdict": "state_conditioned_card_ranking_not_ready_after_crossfit",
        }
        metrics = {
            "crossfit_base": residual._metrics_without_predictions(
                selection["base_metrics"]
            ),
            "crossfit_candidates": selection["candidates"],
            "schema_version": METRICS_SCHEMA_VERSION,
        }
        predictions = {
            "crossfit": crossfit_predictions,
            "schema_version": PREDICTIONS_SCHEMA_VERSION,
        }
        artifact_payloads = {
            "configuration.json": configuration_binding,
            "folds.json": folds_binding,
            "metrics.json": _write_artifact(
                staging, output, "metrics.json", _canonical_bytes(metrics)
            ),
            "predictions.json": _write_artifact(
                staging, output, "predictions.json", _canonical_bytes(predictions)
            ),
            "report.json": _write_artifact(
                staging, output, "report.json", _canonical_bytes(report)
            ),
            "report.md": _write_artifact(
                staging,
                output,
                "report.md",
                _render_report(report).encode("ascii"),
            ),
        }
        manifest = {
            "artifacts": artifact_payloads,
            "schema_version": MANIFEST_SCHEMA_VERSION,
            "verdict": report["verdict"],
        }
        _write_artifact(
            staging, output, "artifact_manifest.json", _canonical_bytes(manifest)
        )
        staging.rename(output)
        return report

    final_scores, final_losses, final_model = train_checkpoints(
        entry_bytes,
        fit_rows=train_rows,
        score_partition=train_rows,
        epoch_checkpoints=(selected_epochs,),
    )
    model_payload = encode_model(final_model)
    model_binding = _write_artifact(
        staging, output, "trained_model.json", model_payload
    )
    restored = restore_model(model_payload)
    if (
        ranking._guard_bytes(restored) != entry_guard
        or pilot.encode_candidate_card_policy(restored) == entry_card
        or encode_model(restored) != model_payload
    ):
        raise StateConditionedRankingBlocked("restored final model differs")

    corpus_report = residual._read_canonical(corpus_path / "report.json")
    existing_development, development_binding = residual._load_development_inputs(
        corpus_path, corpus_report
    )
    rare_report = residual._read_canonical(rare_path / "report.json")
    rare_development, rare_development_binding, rare_projection = (
        residual._load_rare_development_inputs(rare_path, rare_report)
    )
    development_rows = residual._merge_disjoint_rows(
        existing_development, rare_development
    )
    if len(development_rows) != EXPECTED_DEVELOPMENT_ROWS:
        raise StateConditionedRankingBlocked("merged development support differs")
    inputs["development_dataset"] = development_binding
    inputs["rare_development_dataset"] = rare_development_binding
    inputs["rare_development_projection"] = rare_projection
    configuration = _configuration(inputs=inputs, source=source)
    (staging / "configuration.json").write_bytes(_canonical_bytes(configuration))
    configuration_binding = _binding(staging / "configuration.json")
    configuration_binding["path"] = (output / "configuration.json").as_posix()

    entry_development_scores = score_rows(entry, development_rows)
    trained_development_scores = score_rows(restored, development_rows)
    entry_development = uplift.evaluate_scores(
        development_rows, entry_development_scores
    )
    trained_development = uplift.evaluate_scores(
        development_rows, trained_development_scores
    )
    development_comparison = uplift.compare_predictions(
        entry_development, trained_development
    )
    development_checks = _comparison_checks(
        entry_development,
        trained_development,
        development_comparison,
        minimum_corrected_actions=MIN_DEVELOPMENT_CORRECTED_ACTIONS,
    )
    rare_sources = {row.source_sha256 for row in rare_development}
    rare_entry_scores = {
        source_id: values
        for source_id, values in entry_development_scores.items()
        if source_id in rare_sources
    }
    rare_trained_scores = {
        source_id: values
        for source_id, values in trained_development_scores.items()
        if source_id in rare_sources
    }
    rare_entry = uplift.evaluate_scores(rare_development, rare_entry_scores)
    rare_trained = uplift.evaluate_scores(rare_development, rare_trained_scores)
    rare_comparison = uplift.compare_predictions(rare_entry, rare_trained)
    entry_skip_errors = residual._best_take_to_skip_errors(
        rare_development, rare_entry_scores
    )
    trained_skip_errors = residual._best_take_to_skip_errors(
        rare_development, rare_trained_scores
    )
    rare_checks = residual._rare_development_checks(
        rare_entry,
        rare_trained,
        base_best_take_to_skip_errors=entry_skip_errors,
        candidate_best_take_to_skip_errors=trained_skip_errors,
    )
    if (
        pilot.encode_candidate_card_policy(entry) != entry_card
        or ranking._guard_bytes(entry) != entry_guard
        or encode_model(restored) != model_payload
    ):
        raise StateConditionedRankingBlocked("model changed during development")
    ready = all(development_checks.values()) and all(rare_checks.values())
    verdict = (
        "state_conditioned_card_ranking_ready_for_reserved_audit_proposal"
        if ready
        else "state_conditioned_card_ranking_not_ready_after_development"
    )
    metrics = {
        "crossfit_base": residual._metrics_without_predictions(
            selection["base_metrics"]
        ),
        "crossfit_candidates": selection["candidates"],
        "development": {
            "comparison": development_comparison,
            "entry": residual._metrics_without_predictions(entry_development),
            "checks": development_checks,
            "trained": residual._metrics_without_predictions(trained_development),
        },
        "final_train": {
            "entry": residual._metrics_without_predictions(
                uplift.evaluate_scores(train_rows, score_rows(entry, train_rows))
            ),
            "losses": final_losses,
            "trained": residual._metrics_without_predictions(
                uplift.evaluate_scores(train_rows, final_scores[selected_epochs])
            ),
        },
        "rare_development": {
            "best_take_to_skip_errors": {
                "entry": entry_skip_errors,
                "trained": trained_skip_errors,
            },
            "comparison": rare_comparison,
            "entry": residual._metrics_without_predictions(rare_entry),
            "checks": rare_checks,
            "trained": residual._metrics_without_predictions(rare_trained),
        },
        "schema_version": METRICS_SCHEMA_VERSION,
    }
    predictions = {
        "crossfit": crossfit_predictions,
        "development": {
            "entry": entry_development["predictions"],
            "trained": trained_development["predictions"],
        },
        "rare_development": {
            "entry": rare_entry["predictions"],
            "trained": rare_trained["predictions"],
        },
        "schema_version": PREDICTIONS_SCHEMA_VERSION,
    }
    report = {
        "audit_accessed": False,
        "authority": copy.deepcopy(AUTHORITY),
        "development_accessed": True,
        "development_checks": development_checks,
        "development_comparison": development_comparison,
        "model": model_binding,
        "operations": copy.deepcopy(OPERATIONS),
        "rare_best_take_to_skip_errors": {
            "entry": entry_skip_errors,
            "trained": trained_skip_errors,
        },
        "rare_development_checks": rare_checks,
        "rare_development_comparison": rare_comparison,
        "schema_version": REPORT_SCHEMA_VERSION,
        "selected_epochs": selected_epochs,
        "train_only_stop": False,
        "verdict": verdict,
    }
    artifact_payloads = {
        "configuration.json": configuration_binding,
        "folds.json": folds_binding,
        "metrics.json": _write_artifact(
            staging, output, "metrics.json", _canonical_bytes(metrics)
        ),
        "predictions.json": _write_artifact(
            staging, output, "predictions.json", _canonical_bytes(predictions)
        ),
        "report.json": _write_artifact(
            staging, output, "report.json", _canonical_bytes(report)
        ),
        "report.md": _write_artifact(
            staging,
            output,
            "report.md",
            _render_report(report).encode("ascii"),
        ),
        "trained_model.json": model_binding,
    }
    manifest = {
        "artifacts": artifact_payloads,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": verdict,
    }
    _write_artifact(
        staging, output, "artifact_manifest.json", _canonical_bytes(manifest)
    )
    staging.rename(output)
    return report


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", required=True)
    parser.add_argument("--source-commit", required=True)
    parser.add_argument("--corpus-root", default=str(DEFAULT_CORPUS_ROOT))
    parser.add_argument("--rare-corpus-root", default=str(DEFAULT_RARE_CORPUS_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = execute(
            repo_root=args.repo_root,
            source_commit=args.source_commit,
            corpus_root=args.corpus_root,
            rare_corpus_root=args.rare_corpus_root,
            output_dir=args.output_dir,
        )
    except (
        OSError,
        StateConditionedRankingBlocked,
        ranking.CounterfactualRankingBlocked,
        residual.LargeCorpusResidualBlocked,
        runtime.SuccessorRuntimeError,
        subprocess.SubprocessError,
        uplift.UpliftCrossfitBlocked,
    ) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(_canonical_bytes(report).decode("ascii"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
