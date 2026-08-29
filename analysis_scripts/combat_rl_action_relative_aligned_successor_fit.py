"""Fit the fixed successor ablation after live-opportunity support passes."""

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
import time
from typing import Any, Callable, Mapping

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts import (  # noqa: E402
    combat_rl_action_relative_live_context_target as live_target,
)
from analysis_scripts import (  # noqa: E402
    combat_rl_action_relative_successor_context_supplement as supplement,
)
from analysis_scripts import (  # noqa: E402
    combat_rl_action_relative_successor_delta_ablation as predecessor,
)
from analysis_scripts import combat_rl_real_context_balanced_corpus as balanced  # noqa: E402


EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
REPORTS_ROOT = REPO_ROOT / "reports"
EXPERIMENT_ID = "combat-rl-action-relative-aligned-successor-fit-20260829-r1"
OUTPUT_DIR = REPORTS_ROOT / EXPERIMENT_ID.replace("-", "_")
REGISTRATION_PATH = REPORTS_ROOT / f"{EXPERIMENT_ID.replace('-', '_')}_registration.json"
PREFLIGHT_PATH = REPORTS_ROOT / f"{EXPERIMENT_ID.replace('-', '_')}_preflight.json"
REGISTRATION_SCHEMA = "combat-rl-action-relative-aligned-successor-fit-registration-v1"
REPORT_SCHEMA = "combat-rl-action-relative-aligned-successor-fit-report-v1"
MANIFEST_SCHEMA = "combat-rl-action-relative-aligned-successor-fit-manifest-v1"
INPUT_NAMES = (
    "items_json",
    "parent_checkpoint",
    "live_target",
    "live_target_report",
    "live_target_manifest",
    "live_target_registration",
    "fit_corpus",
    "calibration_corpus",
    "fresh_corpus",
    "corpus_report",
    "corpus_manifest",
    "corpus_registration",
)
SOURCE_BOUND_PATHS = tuple(
    sorted(
        set(predecessor.SOURCE_SNAPSHOT_PATHS)
        | {
            "analysis_scripts/combat_rl_action_relative_aligned_successor_fit.py",
            "analysis_scripts/combat_rl_action_relative_live_context_target.py",
            "analysis_scripts/combat_rl_action_relative_successor_context_supplement.py",
        }
    )
)
FIT_AUTHORITY = {
    "candidate_action_takeover": False,
    "fresh_lightspeed_policy_gate": False,
    "gameplay": False,
    "model_fitting": True,
    "online_training": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "promotion": False,
    "qualification": False,
    "training": True,
}
RESOURCE_LIMITS = {
    "maximum_wall_seconds": 7200.0,
    "maximum_output_bytes": 67_108_864,
}


def _canonical_json_bytes(value: Any) -> bytes:
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("ascii")


def file_binding(path: Path) -> dict[str, str]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ValueError(f"aligned successor fit input is missing: {resolved}")
    return {"path": str(resolved), "sha256": predecessor.sha256_file(resolved)}


def _validate_sha256(value: Any, *, label: str) -> str:
    return predecessor._validate_sha256(value, label=label)


def _validate_source_commit(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("aligned successor fit source commit is missing")
    normalized = value.lower()
    if len(normalized) != 40 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("aligned successor fit source commit is invalid")
    return normalized


def _source_file_hashes() -> dict[str, str]:
    return {
        relative: predecessor.sha256_file(REPO_ROOT / relative)
        for relative in SOURCE_BOUND_PATHS
    }


def _normalize_inputs(
    inputs: Mapping[str, Mapping[str, str]]
) -> dict[str, dict[str, str]]:
    if not isinstance(inputs, Mapping) or set(inputs) != set(INPUT_NAMES):
        raise ValueError("aligned successor fit input inventory differs")
    normalized: dict[str, dict[str, str]] = {}
    for name in INPUT_NAMES:
        binding = inputs[name]
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise ValueError("aligned successor fit input binding differs")
        raw_path = Path(str(binding["path"]))
        if not raw_path.is_absolute():
            raise ValueError("aligned successor fit input path must be absolute")
        path = raw_path.resolve()
        normalized[name] = {
            "path": str(path.resolve()),
            "sha256": _validate_sha256(binding["sha256"], label=name),
        }
    return normalized


def build_fit_registration(
    source_commit: str, *, inputs: Mapping[str, Mapping[str, str]]
) -> dict[str, Any]:
    commit = _validate_source_commit(source_commit)
    return {
        "schema_version": REGISTRATION_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": commit,
        "interpreter": str(EXPECTED_INTERPRETER.resolve()),
        "runner": file_binding(Path(__file__)),
        "source_files": _source_file_hashes(),
        "inputs": _normalize_inputs(inputs),
        "recipe": copy.deepcopy(predecessor.FIXED_ABLATION_RECIPE),
        "offline_gates": copy.deepcopy(predecessor.FIXED_OFFLINE_GATES),
        "resource_limits": copy.deepcopy(RESOURCE_LIMITS),
        "output_dir": str(OUTPUT_DIR.resolve()),
        "authority": copy.deepcopy(FIT_AUTHORITY),
    }


def validate_fit_registration(registration: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_fit_registration(
        str(registration.get("source_commit", "")),
        inputs=registration.get("inputs", {}),
    )
    if dict(registration) != expected:
        raise ValueError("aligned successor fit registration payload differs")
    return copy.deepcopy(expected)


def _validate_source_binding(source_commit: str) -> None:
    common = {
        "cwd": str(REPO_ROOT),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "check": False,
    }
    ancestor = subprocess.run(
        ["git", "merge-base", "--is-ancestor", source_commit, "HEAD"], **common
    )
    if ancestor.returncode != 0:
        raise ValueError("aligned successor fit source commit is not an ancestor")
    for relative in SOURCE_BOUND_PATHS:
        present = subprocess.run(
            ["git", "cat-file", "-e", f"{source_commit}:{relative}"], **common
        )
        if present.returncode != 0:
            raise ValueError(f"aligned successor fit source is absent: {relative}")
    unchanged = subprocess.run(
        ["git", "diff", "--quiet", source_commit, "--", *SOURCE_BOUND_PATHS],
        **common,
    )
    if unchanged.returncode != 0:
        raise ValueError("aligned successor fit sources differ from registration")


def _validated_input_paths(registration: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"]).resolve()
        if not path.is_file() or predecessor.sha256_file(path) != binding["sha256"]:
            raise ValueError(f"aligned successor fit input differs: {name}")
        paths[name] = path
    return paths


def _load_live_target(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="ascii"))
    if not isinstance(payload, Mapping) or payload.get("schema_version") != live_target.TARGET_SCHEMA:
        raise ValueError("aligned successor live target schema differs")
    rows = payload.get("rows")
    if not isinstance(rows, list) or not rows:
        raise ValueError("aligned successor live target rows are missing")
    if payload.get("target_identity_sha256") != live_target.context_target_identity(rows):
        raise ValueError("aligned successor live target identity differs")
    sufficiency = payload.get("sufficiency")
    if not isinstance(sufficiency, Mapping) or sufficiency.get(
        "all_conditions_passed"
    ) is not True:
        raise ValueError("aligned successor live target is insufficient")
    if payload.get("authority") != live_target.TARGET_AUTHORITY:
        raise ValueError("aligned successor live target authority differs")
    return copy.deepcopy(dict(payload))


def _validate_manifest_artifacts(
    manifest_path: Path, *, root: Path, required: set[str]
) -> Mapping[str, Any]:
    manifest = json.loads(manifest_path.read_text(encoding="ascii"))
    artifacts = manifest.get("artifacts") if isinstance(manifest, Mapping) else None
    if not isinstance(artifacts, Mapping) or not required.issubset(artifacts):
        raise ValueError("aligned successor input manifest inventory differs")
    for name, binding in artifacts.items():
        if not isinstance(binding, Mapping) or set(binding) != {"sha256", "size_bytes"}:
            raise ValueError("aligned successor input manifest binding differs")
        path = root / str(name)
        if (
            not path.is_file()
            or path.stat().st_size != int(binding["size_bytes"])
            or predecessor.sha256_file(path)
            != _validate_sha256(binding["sha256"], label=str(name))
        ):
            raise ValueError("aligned successor input manifest artifact differs")
    return manifest


def _validate_input_packages(paths: Mapping[str, Path]) -> None:
    target_manifest = _validate_manifest_artifacts(
        paths["live_target_manifest"],
        root=paths["live_target_manifest"].parent,
        required={"target.json", "report.json", "registration.json"},
    )
    target_report = json.loads(paths["live_target_report"].read_text(encoding="ascii"))
    if (
        target_report.get("decision")
        != "target_ready_for_one_aligned_support_evaluation"
        or target_manifest.get("decision") != target_report.get("decision")
    ):
        raise ValueError("aligned successor target package is not ready")
    target_registration = json.loads(
        paths["live_target_registration"].read_text(encoding="ascii")
    )
    live_target.validate_target_registration(
        target_registration, require_batch_outputs=True
    )
    corpus_manifest = _validate_manifest_artifacts(
        paths["corpus_manifest"],
        root=paths["corpus_manifest"].parent,
        required={
            "fit_corpus.pt",
            "calibration_corpus.pt",
            "fresh_corpus.pt",
            "report.json",
            "registration.json",
        },
    )
    corpus_report = json.loads(paths["corpus_report"].read_text(encoding="ascii"))
    if corpus_manifest.get("decision") != corpus_report.get("decision"):
        raise ValueError("aligned successor corpus package decision differs")


def evaluate_aligned_support(
    target_rows: list[Mapping[str, Any]],
    corpora: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    supplement.validate_merged_seed_isolation(corpora)
    train = predecessor._combined_training_source_view(
        corpora["fit"], corpora["calibration"]
    )
    fresh = predecessor._balanced_source_view(
        corpora["fresh"], partition="evaluation"
    )
    train_context = live_target.derive_context_weights_from_target(
        target_rows, train
    )
    fresh_context = live_target.derive_context_weights_from_target(
        target_rows, fresh
    )
    integrity = balanced._integrity_conditions(train, fresh)
    late_rows = sum(23 <= int(row["floor"]) <= 34 for row in fresh["metadata"])
    gate = balanced.apply_support_gates(
        train_metrics=train_context["metrics"],
        evaluation_metrics=fresh_context["metrics"],
        evaluation_late_floor_rows=late_rows,
        integrity_conditions=integrity,
    )
    return {
        "target_row_count": len(target_rows),
        "train": train_context["metrics"],
        "fresh": fresh_context["metrics"],
        "evaluation_late_floor_rows": late_rows,
        "integrity": integrity,
        "gate": gate,
    }


def run_if_supported(
    support: Mapping[str, Any], fit: Callable[[], Mapping[str, Any]]
) -> dict[str, Any]:
    gate = support.get("gate")
    if not isinstance(gate, Mapping) or gate.get("passed") is not True:
        return {
            "fit_executed": False,
            "fit_result": None,
            "decision": "aligned_support_insufficient_close_without_fit",
        }
    result = fit()
    return {
        "fit_executed": True,
        "fit_result": result,
        "decision": str(result.get("decision", "paired_fit_complete")),
    }


def _fit_once(
    *,
    registration: Mapping[str, Any],
    paths: Mapping[str, Path],
    target_rows: list[Mapping[str, Any]],
    fit_corpus: Mapping[str, Any],
    calibration_corpus: Mapping[str, Any],
) -> dict[str, Any]:
    fit_context = live_target.derive_context_weights_from_target(
        target_rows, fit_corpus
    )
    calibration_context = live_target.derive_context_weights_from_target(
        target_rows, calibration_corpus
    )
    fit_plan = predecessor._weighted_sampling_plan(
        fit_corpus, fit_context["weights"]
    )
    mapper = predecessor.build_id_mapper(paths["items_json"])
    initial = predecessor.load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = predecessor.create_fresh_trainer(
        mapper,
        seed=int(predecessor.FIXED_ABLATION_RECIPE["model_initialization_seed"]),
        batch_size=int(
            predecessor.FIXED_ABLATION_RECIPE["samples_per_class_per_update"]
        )
        * 3,
        learning_starts=64,
    )
    parent_state, initialization = predecessor.initialize_trainer(trainer, initial)
    parent = trainer.online_network
    parent.eval()
    metadata = predecessor._trainer_metadata(trainer)
    extractor = predecessor.ActionRelativeSelectiveClassifier(
        parent,
        metadata,
        predecessor.ActionRelativeSelectiveConfig(
            hidden_dim=int(predecessor.FIXED_ABLATION_RECIPE["hidden_dim"]),
            include_item_semantics=True,
        ),
        selection_threshold=0.0,
    )
    extractor.eval()
    parent_before = predecessor.state_dict_sha256(parent.state_dict())
    fit_features = predecessor.build_ablation_feature_matrices(
        extractor, fit_corpus
    )
    heads: dict[str, torch.nn.Module] = {}
    fit_reports: dict[str, dict[str, Any]] = {}
    for arm in ("control", "successor"):
        head, fit_report = predecessor._fit_head(
            fit_features[arm],
            fit_plan["labels"],
            class_plan=fit_plan["class_plan"],
            ranking_pairs=fit_plan["ranking_pairs"],
            ranking_plan=fit_plan["ranking_plan"],
        )
        heads[arm] = head
        fit_reports[arm] = {
            **fit_report,
            "feature_sha256": predecessor._sha256_tensors(
                {"features": fit_features[arm]}
            ),
            "sampling_plan_sha256": fit_plan["sha256"],
        }
    calibration_features = predecessor.build_ablation_feature_matrices(
        extractor, calibration_corpus
    )
    calibration_pair_weights = predecessor.derive_pair_sampling_weights(
        calibration_corpus["pairs"]["source_rows"],
        calibration_context["weights"],
        labels=calibration_features["labels"],
    )["raw"]
    calibrations = {
        arm: predecessor._calibrate_head(
            heads[arm],
            calibration_features[arm],
            calibration_features["labels"],
            calibration_pair_weights,
        )
        for arm in ("control", "successor")
    }
    parent_after = predecessor.state_dict_sha256(parent.state_dict())
    if parent_before != parent_after:
        raise RuntimeError("aligned successor fit changed the frozen parent")
    boundary = predecessor.FreshAccessBoundary()
    for arm in ("control", "successor"):
        boundary.freeze_arm(
            arm,
            fit_reports[arm]["state_dict_sha256"],
            calibrations[arm]["selection_threshold"],
        )
    fresh_access = boundary.authorize_fresh_access()
    fresh_corpus = predecessor._load_successor_corpus(
        paths["fresh_corpus"], partition="fresh"
    )
    fresh_context = live_target.derive_context_weights_from_target(
        target_rows, fresh_corpus
    )
    fresh_features = predecessor.build_ablation_feature_matrices(
        extractor, fresh_corpus
    )
    fresh_evaluation = {
        arm: predecessor.evaluate_ablation_head(
            heads[arm],
            fresh_features[arm],
            fresh_corpus,
            fresh_context["weights"],
            selection_threshold=calibrations[arm]["selection_threshold"],
        )
        for arm in ("control", "successor")
    }
    hard_gate = predecessor.apply_weighted_offline_gates(
        fresh_evaluation["successor"]["raw"],
        fresh_evaluation["successor"]["weighted"],
    )
    signal = predecessor.compare_representation_signal(
        fresh_evaluation["control"], fresh_evaluation["successor"]
    )
    decision = (
        "offline_passed_propose_fresh_lightspeed_gate"
        if hard_gate["all_conditions_passed"]
        else signal["decision"]
    )
    artifacts = {
        arm: predecessor._head_artifact(
            heads[arm],
            arm=arm,
            threshold=calibrations[arm]["selection_threshold"],
            input_dim=int(fresh_features[arm].shape[1]),
        )
        for arm in ("control", "successor")
    }
    for arm in ("control", "successor"):
        restored = predecessor._restore_head(artifacts[arm])
        with torch.no_grad():
            if not torch.equal(
                heads[arm](fresh_features[arm]), restored(fresh_features[arm])
            ):
                raise RuntimeError("aligned successor artifact roundtrip changed logits")
    return {
        "decision": decision,
        "initialization": initialization,
        "parent_parameter_sha256": predecessor.parameter_sha256(parent_state),
        "parent_state_dict_sha256_before": parent_before,
        "parent_state_dict_sha256_after": parent_after,
        "fit_context": fit_context["metrics"],
        "calibration_context": calibration_context["metrics"],
        "fresh_context": fresh_context["metrics"],
        "sampling_plan_sha256": fit_plan["sha256"],
        "fit": fit_reports,
        "calibration": calibrations,
        "fresh_access": fresh_access,
        "fresh_evaluation": {
            arm: {"raw": result["raw"], "weighted": result["weighted"]}
            for arm, result in fresh_evaluation.items()
        },
        "hard_gate": hard_gate,
        "representation_signal": signal,
        "artifact_roundtrip_exact": True,
        "artifacts": artifacts,
    }


def _publish(
    *,
    registration_path: Path,
    registration: Mapping[str, Any],
    started_path: Path,
    support: Mapping[str, Any],
    target_payload: Mapping[str, Any],
    fit_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    decision = (
        "aligned_support_insufficient_close_without_fit"
        if fit_result is None
        else str(fit_result["decision"])
    )
    report = {
        "schema_version": REPORT_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "inputs": registration["inputs"],
        "recipe": copy.deepcopy(predecessor.FIXED_ABLATION_RECIPE),
        "offline_gates": copy.deepcopy(predecessor.FIXED_OFFLINE_GATES),
        "resource_limits": copy.deepcopy(RESOURCE_LIMITS),
        "live_target_identity_sha256": target_payload["target_identity_sha256"],
        "aligned_support": copy.deepcopy(dict(support)),
        "optimizer_constructed": fit_result is not None,
        "fit_executed": fit_result is not None,
        "fit_result": None
        if fit_result is None
        else {key: value for key, value in fit_result.items() if key != "artifacts"},
        "decision": decision,
        "authority": {
            **copy.deepcopy(FIT_AUTHORITY),
            "fresh_lightspeed_policy_gate": bool(
                fit_result is not None
                and fit_result["hard_gate"]["all_conditions_passed"]
            ),
        },
    }
    staging = OUTPUT_DIR.with_name(f".{OUTPUT_DIR.name}.staging")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        if fit_result is not None:
            artifact_path = staging / "paired_successor_delta_ablation.pth"
            torch.save(
                {
                    "schema_version": "combat-rl-action-relative-aligned-successor-artifact-v1",
                    "recipe": copy.deepcopy(predecessor.FIXED_ABLATION_RECIPE),
                    "parent_checkpoint_sha256": registration["inputs"][
                        "parent_checkpoint"
                    ]["sha256"],
                    "sampling_plan_sha256": fit_result["sampling_plan_sha256"],
                    "arms": fit_result["artifacts"],
                    "production_compatible": False,
                },
                artifact_path,
            )
            report["artifact"] = {
                "path": artifact_path.name,
                "sha256": predecessor.sha256_file(artifact_path),
                "size_bytes": artifact_path.stat().st_size,
                "production_compatible": False,
            }
        (staging / "report.json").write_bytes(_canonical_json_bytes(report))
        shutil.copyfile(registration_path, staging / "registration.json")
        shutil.copyfile(PREFLIGHT_PATH, staging / "preflight.json")
        shutil.copyfile(started_path, staging / "started_receipt.json")
        summary = "\n".join(
            (
                "# Aligned action-relative successor fit",
                "",
                f"- Decision: `{decision}`",
                f"- Aligned support passed: `{str(support['gate']['passed']).lower()}`",
                f"- Fit executed: `{str(fit_result is not None).lower()}`",
                "",
                "This is development-only offline evidence and grants no live",
                "candidate takeover, qualification, promotion, or production authority.",
                "",
            )
        )
        (staging / "summary.md").write_text(
            summary, encoding="ascii", newline="\n"
        )
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "experiment_id": EXPERIMENT_ID,
            "source_commit": registration["source_commit"],
            "decision": decision,
            "artifacts": {
                path.name: {
                    "sha256": predecessor.sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
                for path in sorted(staging.iterdir())
                if path.is_file() and path.name != "manifest.json"
            },
        }
        (staging / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
        stored = sum(
            path.stat().st_size for path in staging.iterdir() if path.is_file()
        )
        if stored > int(RESOURCE_LIMITS["maximum_output_bytes"]):
            raise RuntimeError("aligned successor fit output exceeds storage limit")
        os.replace(staging, OUTPUT_DIR)
        return report
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def run_registered_fit(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("aligned successor fit must use the Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("aligned successor fit must run in isolated mode")
    if registration_path.resolve() != REGISTRATION_PATH.resolve():
        raise ValueError("aligned successor fit registration path differs")
    live_target.require_committed_file(
        registration_path, label="aligned successor fit registration"
    )
    registration = validate_fit_registration(
        json.loads(registration_path.read_text(encoding="ascii"))
    )
    _validate_source_binding(registration["source_commit"])
    paths = _validated_input_paths(registration)
    _validate_input_packages(paths)
    staging = OUTPUT_DIR.with_name(f".{OUTPUT_DIR.name}.staging")
    started_path = REPORTS_ROOT / f".{EXPERIMENT_ID}.started.json"
    failure_path = REPORTS_ROOT / f"{OUTPUT_DIR.name}_failure.json"
    if OUTPUT_DIR.exists() or staging.exists() or started_path.exists() or failure_path.exists():
        raise ValueError("aligned successor output, staging, receipt, or failure exists")
    target_payload = _load_live_target(paths["live_target"])
    corpora = {
        partition: predecessor._load_successor_corpus(
            paths[f"{partition}_corpus"], partition=partition
        )
        for partition in ("fit", "calibration", "fresh")
    }
    started_at = time.time()
    started = {
        "schema_version": "combat-rl-action-relative-aligned-successor-fit-started-v1",
        "experiment_id": EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "started_unix": time.time(),
        "optimizer_constructed": False,
        "fresh_policy_metric_access": False,
    }
    started_path.write_bytes(_canonical_json_bytes(started))
    try:
        support = evaluate_aligned_support(target_payload["rows"], corpora)
        fit_result = None
        if support["gate"]["passed"] is True:
            # Fresh policy labels are reloaded only after both fitted arms are frozen.
            del corpora["fresh"]
            fit_result = _fit_once(
                registration=registration,
                paths=paths,
                target_rows=target_payload["rows"],
                fit_corpus=corpora["fit"],
                calibration_corpus=corpora["calibration"],
            )
        if time.time() - started_at > float(RESOURCE_LIMITS["maximum_wall_seconds"]):
            raise RuntimeError("aligned successor fit exceeds wall-time limit")
        return _publish(
            registration_path=registration_path,
            registration=registration,
            started_path=started_path,
            support=support,
            target_payload=target_payload,
            fit_result=fit_result,
        )
    except BaseException as exc:
        failure = {
            "schema_version": "combat-rl-action-relative-aligned-successor-fit-failure-v1",
            "experiment_id": EXPERIMENT_ID,
            "source_commit": registration["source_commit"],
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        failure_path.write_bytes(_canonical_json_bytes(failure))
        raise


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    report = run_registered_fit(args.registration)
    print(json.dumps({"decision": report["decision"]}, sort_keys=True))


if __name__ == "__main__":
    main()
