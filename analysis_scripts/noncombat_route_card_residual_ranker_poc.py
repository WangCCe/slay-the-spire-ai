"""Run the terminal train-only non-combat route/card residual-ranker POC."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import random
import time
from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    NATIVE_TARGET_POLICY_ID,
    TARGET_CATEGORIES,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.noncombat_simulator_baseline_warm_start import (
    canonical_warm_start_model_payload,
    load_warm_start_model,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    _verify_sources_at_commit,
    hash_bound_files,
)
from analysis_scripts.noncombat_structured_baseline_ranker_poc import (
    FOLD_RULE,
    LEGACY_CANDIDATE_ID,
    REGISTERED_TRAIN_SEEDS,
    STRUCTURED_FEATURE_VERSION,
    TIE_RULE,
    TRAIN_INPUT_MANIFEST_SCHEMA_VERSION,
    PreparedRow,
    StructuredPocBlocked,
    _actual_binding,
    _binding_for_path,
    _ensure_finite_model,
    _ensure_finite_tensor,
    _finite_number,
    _is_commit,
    _is_sha256,
    _load_json,
    _mapping,
    _require_exact,
    _require_keys,
    _seed_array,
    _validate_binding,
    build_seed_folds,
    feature_collision_diagnostics,
    load_train_input_archive,
    metrics_from_predictions,
    prepare_rows,
    singleton_summary,
    train_candidate_model,
    validate_artifact_directory as validate_structured_artifact_directory,
    validate_train_input,
)


REGISTRATION_SCHEMA_VERSION = "noncombat-route-card-residual-ranker-poc-input-v1"
RESIDUAL_FEATURE_VERSION = STRUCTURED_FEATURE_VERSION
CONTROL_CANDIDATE_ID = LEGACY_CANDIDATE_ID
RESIDUAL_CANDIDATE_ID = "legacy-plus-structured-route-card-residual-v1"
RESIDUAL_CATEGORIES = ("card_reward", "route")
DELEGATED_CATEGORIES = ("event", "shop")
RESIDUAL_MODEL_SCHEMA_VERSION = "noncombat-route-card-residual-model-v1"
COMPOSITE_MODEL_SCHEMA_VERSION = "noncombat-route-card-composite-model-v1"
EXECUTION_SCHEMA_VERSION = "noncombat-route-card-residual-execution-v1"
METRICS_SCHEMA_VERSION = "noncombat-route-card-residual-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-route-card-residual-manifest-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-route-card-residual-journal-v1"
REGISTERED_SOURCE_FILES = (
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_baseline_warm_start.py",
    "analysis_scripts/noncombat_simulator_training_smoke.py",
    "analysis_scripts/noncombat_structured_baseline_ranker_poc.py",
    "analysis_scripts/noncombat_route_card_residual_ranker_poc.py",
)
CANONICAL_ARTIFACT_NAMES = (
    "artifact_manifest.json",
    "configuration.json",
    "folds.json",
    "metrics.json",
    "models.json",
    "predictions.json",
    "report.md",
)


# Reuse the upstream contract error so delegated validators have one catchable type.
ResidualPocBlocked = StructuredPocBlocked


def _authority() -> dict[str, bool]:
    return {
        "dagger": False,
        "formal_noncombat_rl": False,
        "live_gameplay": False,
        "live_policy_loading": False,
        "native_evidence_collection": False,
        "ope_reinterpretation": False,
        "policy_promotion": False,
        "policy_quality": False,
        "qualification": False,
        "simulator_rollout": False,
    }


def _load_artifact_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ResidualPocBlocked(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(payload, object_pairs_hook=reject_duplicates)
    except ResidualPocBlocked:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ResidualPocBlocked(f"{label} is invalid JSON: {exc}") from exc
    return _mapping(value, label)


def _validate_control_candidate(value: object) -> dict[str, Any]:
    candidate = _mapping(value, "poc.candidates.control")
    expected = {
        "architecture": "shared-mlp-v1",
        "feature_version": "noncombat-simulator-policy-features-v1",
        "hash_dim": 1024,
        "hidden_dim": 128,
        "id": CONTROL_CANDIDATE_ID,
    }
    _require_keys(candidate, set(expected), "poc.candidates.control")
    for field, expected_value in expected.items():
        _require_exact(candidate, field, expected_value, "poc.candidates.control")
    return candidate


def _validate_residual_candidate(value: object) -> dict[str, Any]:
    candidate = _mapping(value, "poc.candidates.residual")
    expected = {
        "architecture": "legacy-plus-two-head-bounded-residual-v1",
        "base_candidate_id": CONTROL_CANDIDATE_ID,
        "composition": "base-logit-plus-tanh-residual-v1",
        "feature_version": RESIDUAL_FEATURE_VERSION,
        "hash_dim": 2048,
        "hidden_dim": 32,
        "id": RESIDUAL_CANDIDATE_ID,
        "initialization": "zero-output-layer-v1",
        "residual_categories": list(RESIDUAL_CATEGORIES),
        "residual_scale": 1.0,
    }
    _require_keys(candidate, set(expected), "poc.candidates.residual")
    for field, expected_value in expected.items():
        _require_exact(candidate, field, expected_value, "poc.candidates.residual")
    return candidate


def _validate_optimizer(value: object, label: str) -> dict[str, Any]:
    optimizer = _mapping(value, label)
    expected = {
        "algorithm": "adam",
        "beta1": 0.9,
        "beta2": 0.999,
        "category_balanced": True,
        "deterministic_order": True,
        "epochs": 20,
        "epsilon": 1e-8,
        "learning_rate": 0.001,
        "model_seed": 0,
        "multi_candidate_only": True,
        "torch_num_threads": 1,
        "weight_decay": 0.0,
    }
    _require_keys(optimizer, set(expected), label)
    for field, expected_value in expected.items():
        _require_exact(optimizer, field, expected_value, label)
    return optimizer


def _registered_thresholds() -> dict[str, float]:
    return {
        "maximum_aggregate_card_reward_cross_entropy_delta": -0.01,
        "maximum_aggregate_route_cross_entropy_delta": -0.01,
        "maximum_fold_category_cross_entropy_delta": 0.0,
        "maximum_fold_overall_cross_entropy_delta": 0.0,
        "minimum_aggregate_card_reward_agreement_delta": 0.01,
        "minimum_aggregate_route_agreement_delta": 0.05,
        "minimum_fold_category_agreement_delta": 0.0,
        "minimum_fold_macro_agreement_delta": 0.0,
        "minimum_macro_agreement_delta": 0.02,
        "minimum_overall_agreement_delta": 0.03,
    }


def validate_registration(value: object) -> dict[str, Any]:
    """Validate the exact terminal POC contract without supplying defaults."""
    registration = _mapping(value, "registration")
    _require_keys(
        registration,
        {"authority", "identity", "poc", "schema_version"},
        "registration",
    )
    _require_exact(
        registration, "schema_version", REGISTRATION_SCHEMA_VERSION, "registration"
    )

    authority = _mapping(registration["authority"], "authority")
    if authority != _authority():
        raise ResidualPocBlocked("registration authority must remain all false")

    identity = _mapping(registration["identity"], "identity")
    _require_keys(
        identity,
        {
            "implementation",
            "runtime",
            "structured_poc_failure_audit",
            "structured_poc_manifest",
            "structured_poc_verdict",
            "teacher_policy_id",
            "train_dataset_sha256",
            "train_input",
            "train_input_manifest",
        },
        "identity",
    )
    for name in (
        "structured_poc_failure_audit",
        "structured_poc_manifest",
        "train_input",
        "train_input_manifest",
    ):
        identity[name] = _validate_binding(identity[name], f"identity.{name}")
    _require_exact(identity, "teacher_policy_id", NATIVE_TARGET_POLICY_ID, "identity")
    _require_exact(
        identity,
        "structured_poc_verdict",
        "poc_valid_without_structured_candidate",
        "identity",
    )
    if not _is_sha256(identity["train_dataset_sha256"]):
        raise ResidualPocBlocked("identity.train_dataset_sha256 is invalid")

    implementation = _mapping(identity["implementation"], "identity.implementation")
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "identity.implementation",
    )
    if not _is_commit(implementation["commit"]):
        raise ResidualPocBlocked("identity.implementation.commit is invalid")
    if implementation["source_files"] != list(REGISTERED_SOURCE_FILES):
        raise ResidualPocBlocked("implementation source file inventory mismatch")
    if not _is_sha256(implementation["source_sha256"]):
        raise ResidualPocBlocked("identity.implementation.source_sha256 is invalid")
    identity["implementation"] = implementation

    runtime = _mapping(identity["runtime"], "identity.runtime")
    _require_keys(runtime, {"python", "torch"}, "identity.runtime")
    if any(not isinstance(runtime[name], str) or not runtime[name] for name in runtime):
        raise ResidualPocBlocked("identity.runtime values are required")
    identity["runtime"] = runtime

    poc = _mapping(registration["poc"], "poc")
    _require_keys(
        poc,
        {
            "candidates",
            "evaluation",
            "folds",
            "limits",
            "optimizers",
            "seeds",
            "tie_rule",
        },
        "poc",
    )
    seeds = _seed_array(poc["seeds"], "poc.seeds")
    if seeds != list(REGISTERED_TRAIN_SEEDS):
        raise ResidualPocBlocked("poc.seeds must equal 4000..4031")
    poc["seeds"] = seeds
    _require_exact(poc, "tie_rule", TIE_RULE, "poc")

    folds = _mapping(poc["folds"], "poc.folds")
    _require_keys(folds, {"count", "rule"}, "poc.folds")
    _require_exact(folds, "count", 4, "poc.folds")
    _require_exact(folds, "rule", FOLD_RULE, "poc.folds")
    poc["folds"] = folds

    candidates = _mapping(poc["candidates"], "poc.candidates")
    _require_keys(candidates, {"control", "residual"}, "poc.candidates")
    candidates["control"] = _validate_control_candidate(candidates["control"])
    candidates["residual"] = _validate_residual_candidate(candidates["residual"])
    poc["candidates"] = candidates

    optimizers = _mapping(poc["optimizers"], "poc.optimizers")
    _require_keys(optimizers, {"base", "residual"}, "poc.optimizers")
    optimizers["base"] = _validate_optimizer(optimizers["base"], "poc.optimizers.base")
    optimizers["residual"] = _validate_optimizer(
        optimizers["residual"], "poc.optimizers.residual"
    )
    poc["optimizers"] = optimizers

    evaluation = _mapping(poc["evaluation"], "poc.evaluation")
    _require_keys(
        evaluation,
        {"primary_metric", "singleton_treatment", "thresholds"},
        "poc.evaluation",
    )
    _require_exact(
        evaluation,
        "primary_metric",
        "seed_grouped_heldout_multicandidate_action_agreement",
        "poc.evaluation",
    )
    _require_exact(
        evaluation,
        "singleton_treatment",
        "report_only_excluded_from_fit_and_gate",
        "poc.evaluation",
    )
    thresholds = _mapping(evaluation["thresholds"], "poc.evaluation.thresholds")
    expected_thresholds = _registered_thresholds()
    _require_keys(thresholds, set(expected_thresholds), "poc.evaluation.thresholds")
    for field, expected_value in expected_thresholds.items():
        _require_exact(thresholds, field, expected_value, "poc.evaluation.thresholds")
    evaluation["thresholds"] = thresholds
    poc["evaluation"] = evaluation

    limits = _mapping(poc["limits"], "poc.limits")
    expected_limits = {
        "max_candidates_per_row": 32,
        "max_model_fits_per_execution": 10,
        "max_rows": 1500,
        "max_wall_seconds_per_execution": 900.0,
    }
    _require_keys(limits, set(expected_limits), "poc.limits")
    for field, expected_value in expected_limits.items():
        _require_exact(limits, field, expected_value, "poc.limits")
    poc["limits"] = limits

    registration["authority"] = authority
    registration["identity"] = identity
    registration["poc"] = poc
    return registration


def load_registration(path: Path | str) -> dict[str, Any]:
    return validate_registration(_load_json(path, "residual POC registration"))


def build_registration(
    *,
    repo_root: Path,
    implementation_commit: str,
    train_input_path: Path | str,
    train_input_manifest_path: Path | str,
    structured_poc_manifest_path: Path | str,
    structured_poc_failure_audit_path: Path | str,
) -> dict[str, Any]:
    if not _is_commit(implementation_commit):
        raise ResidualPocBlocked("implementation commit is invalid")
    train_manifest = _load_json(train_input_manifest_path, "train input manifest")
    if train_manifest.get("schema_version") != TRAIN_INPUT_MANIFEST_SCHEMA_VERSION:
        raise ResidualPocBlocked("train input manifest schema mismatch")
    train_input = load_train_input_archive(
        train_input_path,
        manifest_path=train_input_manifest_path,
        expected_seeds=REGISTERED_TRAIN_SEEDS,
    )
    train_dataset_sha256 = train_input["source"]["train_dataset_sha256"]
    if train_manifest.get("train_dataset_sha256") != train_dataset_sha256:
        raise ResidualPocBlocked("train input identity mismatch")
    structured_manifest_path = Path(structured_poc_manifest_path)
    structured_manifest = validate_structured_artifact_directory(
        structured_manifest_path.parent
    )
    if structured_manifest.get("verdict") != "poc_valid_without_structured_candidate":
        raise ResidualPocBlocked("structured POC lineage is not the registered negative")
    if any(bool(value) for value in structured_manifest.get("authority", {}).values()):
        raise ResidualPocBlocked("structured POC lineage has downstream authority")
    audit_path = Path(structured_poc_failure_audit_path)
    if not audit_path.is_file():
        raise ResidualPocBlocked("structured POC failure audit is missing")
    try:
        source_sha256 = hash_bound_files(repo_root, REGISTERED_SOURCE_FILES)
        _verify_sources_at_commit(repo_root, implementation_commit, REGISTERED_SOURCE_FILES)
    except Exception as exc:
        raise ResidualPocBlocked(f"cannot bind implementation sources: {exc}") from exc
    torch = _torch_module()
    optimizer = {
        "algorithm": "adam",
        "beta1": 0.9,
        "beta2": 0.999,
        "category_balanced": True,
        "deterministic_order": True,
        "epochs": 20,
        "epsilon": 1e-8,
        "learning_rate": 0.001,
        "model_seed": 0,
        "multi_candidate_only": True,
        "torch_num_threads": 1,
        "weight_decay": 0.0,
    }
    registration = {
        "authority": _authority(),
        "identity": {
            "implementation": {
                "commit": implementation_commit,
                "source_files": list(REGISTERED_SOURCE_FILES),
                "source_sha256": source_sha256,
            },
            "runtime": {
                "python": ".".join(map(str, __import__("sys").version_info[:3])),
                "torch": str(torch.__version__),
            },
            "structured_poc_failure_audit": _binding_for_path(repo_root, audit_path),
            "structured_poc_manifest": _binding_for_path(
                repo_root, structured_manifest_path
            ),
            "structured_poc_verdict": "poc_valid_without_structured_candidate",
            "teacher_policy_id": NATIVE_TARGET_POLICY_ID,
            "train_dataset_sha256": train_dataset_sha256,
            "train_input": _binding_for_path(repo_root, train_input_path),
            "train_input_manifest": _binding_for_path(
                repo_root, train_input_manifest_path
            ),
        },
        "poc": {
            "candidates": {
                "control": {
                    "architecture": "shared-mlp-v1",
                    "feature_version": "noncombat-simulator-policy-features-v1",
                    "hash_dim": 1024,
                    "hidden_dim": 128,
                    "id": CONTROL_CANDIDATE_ID,
                },
                "residual": {
                    "architecture": "legacy-plus-two-head-bounded-residual-v1",
                    "base_candidate_id": CONTROL_CANDIDATE_ID,
                    "composition": "base-logit-plus-tanh-residual-v1",
                    "feature_version": RESIDUAL_FEATURE_VERSION,
                    "hash_dim": 2048,
                    "hidden_dim": 32,
                    "id": RESIDUAL_CANDIDATE_ID,
                    "initialization": "zero-output-layer-v1",
                    "residual_categories": list(RESIDUAL_CATEGORIES),
                    "residual_scale": 1.0,
                },
            },
            "evaluation": {
                "primary_metric": "seed_grouped_heldout_multicandidate_action_agreement",
                "singleton_treatment": "report_only_excluded_from_fit_and_gate",
                "thresholds": _registered_thresholds(),
            },
            "folds": {"count": 4, "rule": FOLD_RULE},
            "limits": {
                "max_candidates_per_row": 32,
                "max_model_fits_per_execution": 10,
                "max_rows": 1500,
                "max_wall_seconds_per_execution": 900.0,
            },
            "optimizers": {"base": copy.deepcopy(optimizer), "residual": optimizer},
            "seeds": list(REGISTERED_TRAIN_SEEDS),
            "tie_rule": TIE_RULE,
        },
        "schema_version": REGISTRATION_SCHEMA_VERSION,
    }
    return validate_registration(registration)


def validate_registered_identity(
    registration: Mapping[str, Any], *, repo_root: Path
) -> dict[str, Any]:
    value = validate_registration(registration)
    identity = value["identity"]
    for name in (
        "structured_poc_failure_audit",
        "structured_poc_manifest",
        "train_input",
        "train_input_manifest",
    ):
        if _actual_binding(repo_root, identity[name]) != identity[name]:
            raise ResidualPocBlocked(f"registered binding mismatch: {name}")
    implementation = identity["implementation"]
    try:
        actual_source_sha256 = hash_bound_files(
            repo_root, implementation["source_files"]
        )
        _verify_sources_at_commit(
            repo_root, implementation["commit"], implementation["source_files"]
        )
    except Exception as exc:
        raise ResidualPocBlocked(f"implementation identity failed: {exc}") from exc
    if actual_source_sha256 != implementation["source_sha256"]:
        raise ResidualPocBlocked("implementation source hash mismatch")
    torch = _torch_module()
    runtime = {
        "python": ".".join(map(str, __import__("sys").version_info[:3])),
        "torch": str(torch.__version__),
    }
    if runtime != identity["runtime"]:
        raise ResidualPocBlocked("registered runtime mismatch")
    train_input = load_train_input_archive(
        repo_root / identity["train_input"]["path"],
        manifest_path=repo_root / identity["train_input_manifest"]["path"],
        expected_seeds=value["poc"]["seeds"],
    )
    if train_input["source"]["train_dataset_sha256"] != identity[
        "train_dataset_sha256"
    ]:
        raise ResidualPocBlocked("registered train dataset identity mismatch")
    structured_manifest_path = repo_root / identity["structured_poc_manifest"]["path"]
    structured_manifest = validate_structured_artifact_directory(
        structured_manifest_path.parent
    )
    if structured_manifest.get("verdict") != identity["structured_poc_verdict"]:
        raise ResidualPocBlocked("registered structured POC verdict mismatch")
    if any(bool(item) for item in structured_manifest.get("authority", {}).values()):
        raise ResidualPocBlocked("registered structured POC authority mismatch")
    return {
        "implementation_commit": implementation["commit"],
        "implementation_source_sha256": actual_source_sha256,
        "runtime": runtime,
        "structured_poc_verdict": structured_manifest["verdict"],
        "train_dataset_sha256": identity["train_dataset_sha256"],
    }


def _torch_module():
    try:
        import torch
    except ImportError as exc:
        raise ResidualPocBlocked("PyTorch is required for the residual POC") from exc
    return torch


def build_residual_model(
    *, hash_dim: int, hidden_dim: int, model_seed: int, residual_scale: float
) -> Any:
    torch = _torch_module()
    if hash_dim <= 0 or hidden_dim <= 0:
        raise ResidualPocBlocked("residual model dimensions must be positive")
    if model_seed != 0:
        raise ResidualPocBlocked("residual model seed must equal 0")
    if residual_scale != 1.0:
        raise ResidualPocBlocked("residual scale must equal 1.0")
    torch.set_num_threads(1)
    torch.use_deterministic_algorithms(True)
    random.seed(model_seed)
    torch.manual_seed(model_seed)

    class RouteCardResidual(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.heads = torch.nn.ModuleDict(
                {
                    category: torch.nn.Sequential(
                        torch.nn.Linear(hash_dim, hidden_dim),
                        torch.nn.ReLU(),
                        torch.nn.Linear(hidden_dim, 1),
                    )
                    for category in RESIDUAL_CATEGORIES
                }
            )
            for head in self.heads.values():
                torch.nn.init.zeros_(head[-1].weight)
                torch.nn.init.zeros_(head[-1].bias)

        def forward(self, candidate_features: Any, category: str) -> Any:
            if category not in self.heads:
                raise ResidualPocBlocked(
                    f"residual head cannot score delegated category {category}"
                )
            raw = self.heads[category](candidate_features).squeeze(-1)
            return torch.tanh(raw) * residual_scale

    model = RouteCardResidual().cpu()
    _ensure_finite_model(model)
    return model


def canonical_residual_model_payload(
    model: Any, *, candidate: Mapping[str, Any]
) -> dict[str, Any]:
    tensors = {}
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous()
        _ensure_finite_tensor(value, f"residual model tensor {name}")
        tensors[name] = {
            "dtype": "float32",
            "shape": list(value.shape),
            "values": [float(item).hex() for item in value.reshape(-1).tolist()],
        }
    return {
        "architecture": candidate["architecture"],
        "candidate_id": candidate["id"],
        "feature_version": candidate["feature_version"],
        "hash_dim": candidate["hash_dim"],
        "hidden_dim": candidate["hidden_dim"],
        "residual_categories": list(candidate["residual_categories"]),
        "residual_scale": candidate["residual_scale"],
        "schema_version": RESIDUAL_MODEL_SCHEMA_VERSION,
        "tensors": tensors,
    }


def load_residual_model_payload(
    value: object, *, candidate: Mapping[str, Any], model_seed: int
) -> Any:
    payload = _mapping(value, "residual model payload")
    _require_keys(
        payload,
        {
            "architecture",
            "candidate_id",
            "feature_version",
            "hash_dim",
            "hidden_dim",
            "residual_categories",
            "residual_scale",
            "schema_version",
            "tensors",
        },
        "residual model payload",
    )
    expected = {
        "architecture": candidate["architecture"],
        "candidate_id": candidate["id"],
        "feature_version": candidate["feature_version"],
        "hash_dim": candidate["hash_dim"],
        "hidden_dim": candidate["hidden_dim"],
        "residual_categories": list(candidate["residual_categories"]),
        "residual_scale": candidate["residual_scale"],
        "schema_version": RESIDUAL_MODEL_SCHEMA_VERSION,
    }
    for field, expected_value in expected.items():
        _require_exact(payload, field, expected_value, "residual model payload")
    model = build_residual_model(
        hash_dim=candidate["hash_dim"],
        hidden_dim=candidate["hidden_dim"],
        model_seed=model_seed,
        residual_scale=candidate["residual_scale"],
    )
    expected_state = model.state_dict()
    tensor_payloads = _mapping(payload["tensors"], "residual model tensors")
    if set(tensor_payloads) != set(expected_state):
        raise ResidualPocBlocked("residual model tensor inventory mismatch")
    torch = _torch_module()
    tensors = {}
    for name, expected_tensor in expected_state.items():
        entry = _mapping(tensor_payloads[name], f"residual model tensor {name}")
        _require_keys(entry, {"dtype", "shape", "values"}, f"residual tensor {name}")
        if entry["dtype"] != "float32" or entry["shape"] != list(expected_tensor.shape):
            raise ResidualPocBlocked(f"residual model tensor metadata mismatch: {name}")
        raw_values = entry["values"]
        if not isinstance(raw_values, list) or len(raw_values) != math.prod(
            expected_tensor.shape
        ):
            raise ResidualPocBlocked(f"residual model tensor value count mismatch: {name}")
        parsed = []
        for raw in raw_values:
            if not isinstance(raw, str):
                raise ResidualPocBlocked(f"residual model tensor value is invalid: {name}")
            try:
                numeric = float.fromhex(raw)
            except ValueError as exc:
                raise ResidualPocBlocked(
                    f"residual model tensor value is invalid: {name}"
                ) from exc
            if not math.isfinite(numeric):
                raise ResidualPocBlocked(
                    f"residual model tensor value is non-finite: {name}"
                )
            parsed.append(numeric)
        tensors[name] = torch.tensor(parsed, dtype=torch.float32).reshape(
            expected_tensor.shape
        )
    model.load_state_dict(tensors, strict=True)
    model.requires_grad_(False)
    model.eval()
    _ensure_finite_model(model)
    if canonical_residual_model_payload(model, candidate=candidate) != payload:
        raise ResidualPocBlocked("residual model canonical round trip mismatch")
    return model


def canonical_composite_model_payload(
    *, base_model: Any, residual_model: Any, registration: Mapping[str, Any]
) -> dict[str, Any]:
    value = validate_registration(registration)
    return {
        "base_candidate_id": CONTROL_CANDIDATE_ID,
        "base_model": canonical_warm_start_model_payload(base_model),
        "candidate_id": RESIDUAL_CANDIDATE_ID,
        "residual_model": canonical_residual_model_payload(
            residual_model, candidate=value["poc"]["candidates"]["residual"]
        ),
        "schema_version": COMPOSITE_MODEL_SCHEMA_VERSION,
    }


def load_composite_model_payload(
    value: object, *, registration: Mapping[str, Any]
) -> tuple[Any, Any]:
    registration_value = validate_registration(registration)
    payload = _mapping(value, "composite model")
    _require_keys(
        payload,
        {
            "base_candidate_id",
            "base_model",
            "candidate_id",
            "residual_model",
            "schema_version",
        },
        "composite model",
    )
    _require_exact(payload, "base_candidate_id", CONTROL_CANDIDATE_ID, "composite model")
    _require_exact(payload, "candidate_id", RESIDUAL_CANDIDATE_ID, "composite model")
    _require_exact(
        payload, "schema_version", COMPOSITE_MODEL_SCHEMA_VERSION, "composite model"
    )
    control = registration_value["poc"]["candidates"]["control"]
    base_model = load_warm_start_model(
        payload["base_model"],
        expected_hash_dim=control["hash_dim"],
        expected_hidden_dim=control["hidden_dim"],
    )
    residual_model = load_residual_model_payload(
        payload["residual_model"],
        candidate=registration_value["poc"]["candidates"]["residual"],
        model_seed=registration_value["poc"]["optimizers"]["residual"]["model_seed"],
    )
    if canonical_composite_model_payload(
        base_model=base_model,
        residual_model=residual_model,
        registration=registration_value,
    ) != payload:
        raise ResidualPocBlocked("composite model canonical round trip mismatch")
    return base_model, residual_model


@dataclass(frozen=True)
class PairedPreparedRow:
    legacy: PreparedRow
    structured: PreparedRow

    @property
    def seed(self) -> int:
        return self.legacy.seed

    @property
    def decision_index(self) -> int:
        return self.legacy.decision_index

    @property
    def category(self) -> str:
        return self.legacy.category


def pair_prepared_rows(
    legacy_rows: Sequence[PreparedRow], structured_rows: Sequence[PreparedRow]
) -> tuple[PairedPreparedRow, ...]:
    if len(legacy_rows) != len(structured_rows) or not legacy_rows:
        raise ResidualPocBlocked("paired prepared row counts differ or are empty")
    pairs = []
    for legacy, structured in zip(legacy_rows, structured_rows, strict=True):
        legacy_identity = (
            legacy.seed,
            legacy.decision_index,
            legacy.category,
            legacy.candidate_action_ids,
            legacy.target_action_id,
            legacy.target_index,
        )
        structured_identity = (
            structured.seed,
            structured.decision_index,
            structured.category,
            structured.candidate_action_ids,
            structured.target_action_id,
            structured.target_index,
        )
        if legacy_identity != structured_identity:
            raise ResidualPocBlocked("legacy and structured prepared rows differ")
        pairs.append(PairedPreparedRow(legacy=legacy, structured=structured))
    ordering = [(row.seed, row.decision_index) for row in pairs]
    if ordering != sorted(ordering) or len(ordering) != len(set(ordering)):
        raise ResidualPocBlocked("paired prepared rows are not unique and ordered")
    return tuple(pairs)


def prepare_paired_rows(
    dataset: Mapping[str, Any],
    *,
    control_candidate: Mapping[str, Any],
    residual_candidate: Mapping[str, Any],
) -> tuple[PairedPreparedRow, ...]:
    legacy_rows = prepare_rows(dataset, candidate=control_candidate)
    structured_projection = {
        "architecture": "category-specific-mlp-v1",
        "feature_version": residual_candidate["feature_version"],
        "hash_dim": residual_candidate["hash_dim"],
        "hidden_dim": residual_candidate["hidden_dim"],
        "id": "structured-category-ranker-v1",
    }
    structured_rows = prepare_rows(dataset, candidate=structured_projection)
    return pair_prepared_rows(legacy_rows, structured_rows)


def train_residual_model(
    rows: Sequence[PairedPreparedRow],
    *,
    base_model: Any,
    candidate: Mapping[str, Any],
    optimizer_config: Mapping[str, Any],
) -> tuple[Any, dict[str, Any]]:
    """Fit only the route/card residual while proving the base is immutable."""
    residual_rows = [row for row in rows if row.category in RESIDUAL_CATEGORIES]
    if not residual_rows or {row.category for row in residual_rows} != set(
        RESIDUAL_CATEGORIES
    ):
        raise ResidualPocBlocked("residual fit rows must cover route and card_reward")
    torch = _torch_module()
    random.seed(optimizer_config["model_seed"])
    torch.manual_seed(optimizer_config["model_seed"])
    base_model.requires_grad_(False)
    base_model.eval()
    base_before = canonical_warm_start_model_payload(base_model)
    model = build_residual_model(
        hash_dim=candidate["hash_dim"],
        hidden_dim=candidate["hidden_dim"],
        model_seed=optimizer_config["model_seed"],
        residual_scale=candidate["residual_scale"],
    )
    initial_payload = canonical_residual_model_payload(model, candidate=candidate)
    for name, entry in initial_payload["tensors"].items():
        if name.endswith(".2.weight") or name.endswith(".2.bias"):
            if any(float.fromhex(item) != 0.0 for item in entry["values"]):
                raise ResidualPocBlocked("residual output layer is not zero initialized")
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=optimizer_config["learning_rate"],
        betas=(optimizer_config["beta1"], optimizer_config["beta2"]),
        eps=optimizer_config["epsilon"],
        weight_decay=optimizer_config["weight_decay"],
    )
    grouped: dict[str, dict[int, list[PairedPreparedRow]]] = {
        category: defaultdict(list) for category in RESIDUAL_CATEGORIES
    }
    for row in residual_rows:
        grouped[row.category][len(row.legacy.candidate_action_ids)].append(row)
    category_count = float(len(RESIDUAL_CATEGORIES))
    history = []
    for epoch in range(1, int(optimizer_config["epochs"]) + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        category_losses = {}
        for category in RESIDUAL_CATEGORIES:
            category_rows = [
                row
                for candidate_count in sorted(grouped[category])
                for row in grouped[category][candidate_count]
            ]
            if not category_rows:
                raise ResidualPocBlocked(f"residual fit missing category {category}")
            loss_sum = 0.0
            for candidate_count in sorted(grouped[category]):
                batch = grouped[category][candidate_count]
                legacy_features = torch.stack([row.legacy.features for row in batch])
                structured_features = torch.stack(
                    [row.structured.features for row in batch]
                )
                targets = torch.tensor(
                    [row.legacy.target_index for row in batch], dtype=torch.long
                )
                with torch.no_grad():
                    base_logits = base_model(legacy_features)
                corrections = model(structured_features, category)
                logits = base_logits + corrections
                _ensure_finite_tensor(logits, "residual training logits")
                _ensure_finite_tensor(corrections, "residual training corrections")
                losses = torch.nn.functional.cross_entropy(
                    logits, targets, reduction="none"
                )
                _ensure_finite_tensor(losses, "residual training loss")
                (
                    losses.sum()
                    / (category_count * float(len(category_rows)))
                ).backward()
                loss_sum += float(losses.detach().sum().item())
            category_losses[category] = loss_sum / len(category_rows)
        for name, parameter in model.named_parameters():
            if parameter.grad is None:
                raise ResidualPocBlocked(f"missing residual model gradient: {name}")
            _ensure_finite_tensor(parameter.grad, f"residual model gradient {name}")
        if any(parameter.grad is not None for parameter in base_model.parameters()):
            raise ResidualPocBlocked("frozen base received a gradient")
        optimizer.step()
        _ensure_finite_model(model)
        history.append(
            {
                "category_losses": category_losses,
                "epoch": epoch,
                "loss": sum(category_losses.values()) / len(category_losses),
            }
        )
    optimizer.zero_grad(set_to_none=True)
    model.requires_grad_(False)
    model.eval()
    base_after = canonical_warm_start_model_payload(base_model)
    base_immutable = base_before == base_after
    if not base_immutable:
        raise ResidualPocBlocked("frozen legacy base changed during residual fitting")
    payload = canonical_residual_model_payload(model, candidate=candidate)
    load_residual_model_payload(
        payload, candidate=candidate, model_seed=optimizer_config["model_seed"]
    )
    return model, {
        "base_immutable": True,
        "final_model_sha256": sha256_bytes(canonical_json_bytes(payload)),
        "history": history,
        "row_count": len(residual_rows),
    }


def _tensor_hexes(value: Any) -> list[str]:
    return [float(item).hex() for item in value.detach().cpu().reshape(-1).tolist()]


def _prediction(
    *,
    row: PreparedRow,
    logits: Any,
    probabilities: Any,
    residuals: Any | None,
    fold: int,
    policy_id: str,
) -> dict[str, Any]:
    torch = _torch_module()
    _ensure_finite_tensor(logits, "evaluation logits")
    _ensure_finite_tensor(probabilities, "evaluation probabilities")
    selected_index = int(torch.argmax(probabilities).item())
    target_probability = float(probabilities[row.target_index].item())
    if not 0.0 < target_probability <= 1.0:
        raise ResidualPocBlocked("teacher probability must be in (0, 1]")
    residual_hexes = [] if residuals is None else _tensor_hexes(residuals)
    return {
        "candidate_action_ids": list(row.candidate_action_ids),
        "candidate_count": len(row.candidate_action_ids),
        "category": row.category,
        "correct": selected_index == row.target_index,
        "cross_entropy": -math.log(target_probability),
        "decision_index": row.decision_index,
        "fold": fold,
        "policy_id": policy_id,
        "predicted_action_id": row.candidate_action_ids[selected_index],
        "probability_hexes": _tensor_hexes(probabilities),
        "residual_hexes": residual_hexes,
        "score_hexes": _tensor_hexes(logits),
        "seed": row.seed,
        "target_action_id": row.target_action_id,
        "target_probability": target_probability,
        "target_probability_hex": target_probability.hex(),
    }


def delegation_summary(
    control_predictions: Sequence[Mapping[str, Any]],
    residual_predictions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if len(control_predictions) != len(residual_predictions):
        raise ResidualPocBlocked("delegation prediction counts differ")
    compared_fields = (
        "candidate_action_ids",
        "correct",
        "predicted_action_id",
        "probability_hexes",
        "score_hexes",
        "target_probability_hex",
    )
    by_category = {}
    for category in DELEGATED_CATEGORIES:
        row_count = 0
        mismatch_count = 0
        for control, residual in zip(
            control_predictions, residual_predictions, strict=True
        ):
            control_key = (control["seed"], control["decision_index"])
            residual_key = (residual["seed"], residual["decision_index"])
            if control_key != residual_key or control["category"] != residual["category"]:
                raise ResidualPocBlocked("paired prediction identities differ")
            if control["category"] != category:
                continue
            row_count += 1
            if any(control[field] != residual[field] for field in compared_fields):
                mismatch_count += 1
            if residual.get("residual_hexes") != []:
                mismatch_count += 1
        if row_count == 0:
            raise ResidualPocBlocked(f"delegation evidence missing {category}")
        by_category[category] = {
            "exact": mismatch_count == 0,
            "mismatch_count": mismatch_count,
            "row_count": row_count,
        }
    return {
        "by_category": by_category,
        "compared_fields": list(compared_fields),
        "exact": all(entry["exact"] for entry in by_category.values()),
        "row_count": sum(entry["row_count"] for entry in by_category.values()),
    }


def _diagnostic_summary(values: Sequence[float]) -> dict[str, Any]:
    if not values:
        raise ResidualPocBlocked("residual diagnostics require values")
    if any(not math.isfinite(value) for value in values):
        raise ResidualPocBlocked("residual diagnostics contain non-finite values")
    absolute = [abs(value) for value in values]
    return {
        "candidate_logit_count": len(values),
        "max_abs": max(absolute),
        "mean_abs": sum(absolute) / len(absolute),
        "rms": math.sqrt(sum(value * value for value in values) / len(values)),
    }


def residual_diagnostics(
    residual_predictions: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_category: dict[str, dict[str, Any]] = {}
    all_values = []
    for category in RESIDUAL_CATEGORIES:
        category_values = []
        for row in residual_predictions:
            if row["category"] != category:
                continue
            raw_values = row.get("residual_hexes")
            if not isinstance(raw_values, list) or len(raw_values) != row[
                "candidate_count"
            ]:
                raise ResidualPocBlocked("route/card prediction residuals are incomplete")
            for raw in raw_values:
                if not isinstance(raw, str):
                    raise ResidualPocBlocked("residual diagnostic value is invalid")
                try:
                    category_values.append(float.fromhex(raw))
                except ValueError as exc:
                    raise ResidualPocBlocked("residual diagnostic value is invalid") from exc
        by_category[category] = _diagnostic_summary(category_values)
        all_values.extend(category_values)
    for row in residual_predictions:
        if row["category"] in DELEGATED_CATEGORIES and row.get("residual_hexes") != []:
            raise ResidualPocBlocked("delegated prediction contains a residual")
    return {"by_category": by_category, "overall": _diagnostic_summary(all_values)}


def evaluate_paired_models(
    *,
    base_model: Any,
    residual_model: Any,
    rows: Sequence[PairedPreparedRow],
    fold: int,
) -> dict[str, Any]:
    torch = _torch_module()
    base_before = canonical_warm_start_model_payload(base_model)
    base_model.eval()
    residual_model.eval()
    control_predictions = []
    candidate_predictions = []
    with torch.no_grad():
        for pair in rows:
            base_logits = base_model(pair.legacy.features)
            control_probabilities = torch.softmax(base_logits, dim=0)
            control_predictions.append(
                _prediction(
                    row=pair.legacy,
                    logits=base_logits,
                    probabilities=control_probabilities,
                    residuals=None,
                    fold=fold,
                    policy_id=CONTROL_CANDIDATE_ID,
                )
            )
            if pair.category in RESIDUAL_CATEGORIES:
                corrections = residual_model(pair.structured.features, pair.category)
                candidate_logits = base_logits + corrections
                candidate_probabilities = torch.softmax(candidate_logits, dim=0)
            else:
                corrections = None
                candidate_logits = base_logits
                candidate_probabilities = control_probabilities
            candidate_predictions.append(
                _prediction(
                    row=pair.legacy,
                    logits=candidate_logits,
                    probabilities=candidate_probabilities,
                    residuals=corrections,
                    fold=fold,
                    policy_id=RESIDUAL_CANDIDATE_ID,
                )
            )
    if canonical_warm_start_model_payload(base_model) != base_before:
        raise ResidualPocBlocked("frozen legacy base changed during evaluation")
    return {
        "candidate_predictions": candidate_predictions,
        "control_predictions": control_predictions,
        "delegation": delegation_summary(control_predictions, candidate_predictions),
        "residual_diagnostics": residual_diagnostics(candidate_predictions),
    }


def metric_deltas(
    control_metrics: Mapping[str, Any], candidate_metrics: Mapping[str, Any]
) -> dict[str, Any]:
    by_category = {}
    for category in TARGET_CATEGORIES:
        control = control_metrics["by_category"][category]
        candidate = candidate_metrics["by_category"][category]
        if control["row_count"] != candidate["row_count"]:
            raise ResidualPocBlocked("paired category metric row counts differ")
        by_category[category] = {
            "action_agreement": candidate["action_agreement"]
            - control["action_agreement"],
            "mean_cross_entropy": candidate["mean_cross_entropy"]
            - control["mean_cross_entropy"],
            "row_count": control["row_count"],
        }
    return {
        "by_category": by_category,
        "macro_category_action_agreement": candidate_metrics[
            "macro_category_action_agreement"
        ]
        - control_metrics["macro_category_action_agreement"],
        "macro_category_mean_cross_entropy": candidate_metrics[
            "macro_category_mean_cross_entropy"
        ]
        - control_metrics["macro_category_mean_cross_entropy"],
        "overall_action_agreement": candidate_metrics["overall_action_agreement"]
        - control_metrics["overall_action_agreement"],
        "overall_mean_cross_entropy": candidate_metrics[
            "overall_mean_cross_entropy"
        ]
        - control_metrics["overall_mean_cross_entropy"],
        "row_count": control_metrics["row_count"],
    }


def _merge_delegation(
    summaries: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    by_category = {}
    for category in DELEGATED_CATEGORIES:
        row_count = sum(item["by_category"][category]["row_count"] for item in summaries)
        mismatch_count = sum(
            item["by_category"][category]["mismatch_count"] for item in summaries
        )
        by_category[category] = {
            "exact": mismatch_count == 0,
            "mismatch_count": mismatch_count,
            "row_count": row_count,
        }
    return {
        "by_category": by_category,
        "compared_fields": list(summaries[0]["compared_fields"]),
        "exact": all(entry["exact"] for entry in by_category.values()),
        "row_count": sum(entry["row_count"] for entry in by_category.values()),
    }


def run_paired_cross_validation(
    rows: Sequence[PairedPreparedRow],
    *,
    control_candidate: Mapping[str, Any],
    residual_candidate: Mapping[str, Any],
    folds: Sequence[Mapping[str, Any]],
    base_optimizer: Mapping[str, Any],
    residual_optimizer: Mapping[str, Any],
    deadline: float,
    clock: Callable[[], float],
) -> dict[str, Any]:
    control_predictions = []
    candidate_predictions = []
    fold_results = []
    for fold_value in folds:
        if clock() > deadline:
            raise ResidualPocBlocked("POC execution exceeded wall-time bound")
        fold = _mapping(fold_value, "fold")
        fit_seed_set = set(fold["fit_seeds"])
        heldout_seed_set = set(fold["heldout_seeds"])
        if fit_seed_set & heldout_seed_set:
            raise ResidualPocBlocked("fold fit and held-out seeds overlap")
        fit_rows = [row for row in rows if row.seed in fit_seed_set]
        heldout_rows = [row for row in rows if row.seed in heldout_seed_set]
        if len(fit_rows) + len(heldout_rows) != len(rows):
            raise ResidualPocBlocked("fold rows do not cover the train corpus")
        base_model, base_training = train_candidate_model(
            [row.legacy for row in fit_rows],
            candidate=control_candidate,
            optimizer_config=base_optimizer,
        )
        residual_model, residual_training = train_residual_model(
            fit_rows,
            base_model=base_model,
            candidate=residual_candidate,
            optimizer_config=residual_optimizer,
        )
        evaluation = evaluate_paired_models(
            base_model=base_model,
            residual_model=residual_model,
            rows=heldout_rows,
            fold=fold["fold"],
        )
        fold_control_metrics = metrics_from_predictions(
            evaluation["control_predictions"]
        )
        fold_candidate_metrics = metrics_from_predictions(
            evaluation["candidate_predictions"]
        )
        fold_results.append(
            {
                "base_immutable": residual_training["base_immutable"],
                "base_model_sha256": base_training["final_model_sha256"],
                "base_training_history": base_training["history"],
                "candidate_metrics": fold_candidate_metrics,
                "control_metrics": fold_control_metrics,
                "delegation": evaluation["delegation"],
                "deltas": metric_deltas(
                    fold_control_metrics, fold_candidate_metrics
                ),
                "fit_row_count": len(fit_rows),
                "fold": fold["fold"],
                "heldout_row_count": len(heldout_rows),
                "residual_diagnostics": evaluation["residual_diagnostics"],
                "residual_model_sha256": residual_training["final_model_sha256"],
                "residual_training_history": residual_training["history"],
            }
        )
        control_predictions.extend(evaluation["control_predictions"])
        candidate_predictions.extend(evaluation["candidate_predictions"])
    control_predictions.sort(key=lambda row: (row["seed"], row["decision_index"]))
    candidate_predictions.sort(key=lambda row: (row["seed"], row["decision_index"]))
    expected_keys = [(row.seed, row.decision_index) for row in rows]
    for predictions in (control_predictions, candidate_predictions):
        actual_keys = [(row["seed"], row["decision_index"]) for row in predictions]
        if actual_keys != expected_keys or len(actual_keys) != len(set(actual_keys)):
            raise ResidualPocBlocked("held-out predictions are not one-to-one with rows")
    control_metrics = metrics_from_predictions(control_predictions)
    candidate_metrics = metrics_from_predictions(candidate_predictions)
    return {
        "aggregate_metrics": {
            "candidate": candidate_metrics,
            "control": control_metrics,
            "deltas": metric_deltas(control_metrics, candidate_metrics),
        },
        "base_immutable": all(item["base_immutable"] for item in fold_results),
        "candidate_predictions": candidate_predictions,
        "control_predictions": control_predictions,
        "delegation": _merge_delegation(
            [item["delegation"] for item in fold_results]
        ),
        "fold_metrics": fold_results,
        "residual_diagnostics": residual_diagnostics(candidate_predictions),
    }


def compare_paired_result(
    result: Mapping[str, Any],
    *,
    thresholds: Mapping[str, Any],
    residual_scale: float,
) -> dict[str, Any]:
    aggregate = result["aggregate_metrics"]
    deltas = aggregate["deltas"]
    route = deltas["by_category"]["route"]
    card = deltas["by_category"]["card_reward"]
    fold_checks = []
    for fold in result["fold_metrics"]:
        fold_deltas = fold["deltas"]
        checks = {
            "card_reward_agreement_nonregression": fold_deltas["by_category"][
                "card_reward"
            ]["action_agreement"]
            >= thresholds["minimum_fold_category_agreement_delta"],
            "card_reward_cross_entropy_nonregression": fold_deltas["by_category"][
                "card_reward"
            ]["mean_cross_entropy"]
            <= thresholds["maximum_fold_category_cross_entropy_delta"],
            "macro_agreement_nonregression": fold_deltas[
                "macro_category_action_agreement"
            ]
            >= thresholds["minimum_fold_macro_agreement_delta"],
            "overall_cross_entropy_nonregression": fold_deltas[
                "overall_mean_cross_entropy"
            ]
            <= thresholds["maximum_fold_overall_cross_entropy_delta"],
            "route_agreement_nonregression": fold_deltas["by_category"]["route"][
                "action_agreement"
            ]
            >= thresholds["minimum_fold_category_agreement_delta"],
            "route_cross_entropy_nonregression": fold_deltas["by_category"][
                "route"
            ]["mean_cross_entropy"]
            <= thresholds["maximum_fold_category_cross_entropy_delta"],
        }
        fold_checks.append(
            {"checks": checks, "fold": fold["fold"], "pass": all(checks.values())}
        )
    structural_checks = {
        "base_immutable": bool(result["base_immutable"]),
        "event_shop_delegation_exact": bool(result["delegation"]["exact"]),
        "residual_bound": result["residual_diagnostics"]["overall"]["max_abs"]
        <= residual_scale,
    }
    competence_checks = {
        "aggregate_card_reward_agreement_improvement": card["action_agreement"]
        >= thresholds["minimum_aggregate_card_reward_agreement_delta"],
        "aggregate_card_reward_cross_entropy_improvement": card[
            "mean_cross_entropy"
        ]
        <= thresholds["maximum_aggregate_card_reward_cross_entropy_delta"],
        "aggregate_route_agreement_improvement": route["action_agreement"]
        >= thresholds["minimum_aggregate_route_agreement_delta"],
        "aggregate_route_cross_entropy_improvement": route["mean_cross_entropy"]
        <= thresholds["maximum_aggregate_route_cross_entropy_delta"],
        "all_fold_nonregression": all(item["pass"] for item in fold_checks),
        "macro_agreement_improvement": deltas["macro_category_action_agreement"]
        >= thresholds["minimum_macro_agreement_delta"],
        "overall_agreement_improvement": deltas["overall_action_agreement"]
        >= thresholds["minimum_overall_agreement_delta"],
    }
    checks = {**structural_checks, **competence_checks}
    structural_pass = all(structural_checks.values())
    selected = structural_pass and all(competence_checks.values())
    verdict = (
        "blocked"
        if not structural_pass
        else (
            "route_card_residual_selected"
            if selected
            else "poc_valid_without_route_card_residual"
        )
    )
    return {
        "checks": checks,
        "fold_checks": fold_checks,
        "selected_candidate_id": RESIDUAL_CANDIDATE_ID if selected else None,
        "verdict": verdict,
    }


def execute_poc(
    *,
    registration: Mapping[str, Any],
    train_input: Mapping[str, Any],
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    value = validate_registration(registration)
    train = validate_train_input(train_input, expected_seeds=value["poc"]["seeds"])
    if train["source"]["train_dataset_sha256"] != value["identity"][
        "train_dataset_sha256"
    ]:
        raise ResidualPocBlocked("registered train dataset identity mismatch")
    dataset = train["dataset"]
    limits = value["poc"]["limits"]
    if len(dataset["rows"]) > limits["max_rows"]:
        raise ResidualPocBlocked("train corpus exceeds registered row bound")
    if any(
        len(row["candidate_actions"]) > limits["max_candidates_per_row"]
        for row in dataset["rows"]
    ):
        raise ResidualPocBlocked("train row exceeds candidate bound")
    start = _finite_number(clock(), "clock")
    deadline = start + limits["max_wall_seconds_per_execution"]
    torch = _torch_module()
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(value["poc"]["optimizers"]["base"]["torch_num_threads"])
    try:
        folds = build_seed_folds(
            value["poc"]["seeds"], fold_count=value["poc"]["folds"]["count"]
        )
        pairs = prepare_paired_rows(
            dataset,
            control_candidate=value["poc"]["candidates"]["control"],
            residual_candidate=value["poc"]["candidates"]["residual"],
        )
        paired_result = run_paired_cross_validation(
            pairs,
            control_candidate=value["poc"]["candidates"]["control"],
            residual_candidate=value["poc"]["candidates"]["residual"],
            folds=folds,
            base_optimizer=value["poc"]["optimizers"]["base"],
            residual_optimizer=value["poc"]["optimizers"]["residual"],
            deadline=deadline,
            clock=clock,
        )
        comparison = compare_paired_result(
            paired_result,
            thresholds=value["poc"]["evaluation"]["thresholds"],
            residual_scale=value["poc"]["candidates"]["residual"][
                "residual_scale"
            ],
        )
        selected_model = None
        selected_model_sha256 = None
        selected_training = None
        fit_count = 8
        if comparison["selected_candidate_id"] == RESIDUAL_CANDIDATE_ID:
            base_model, base_training = train_candidate_model(
                [row.legacy for row in pairs],
                candidate=value["poc"]["candidates"]["control"],
                optimizer_config=value["poc"]["optimizers"]["base"],
            )
            residual_model, residual_training = train_residual_model(
                pairs,
                base_model=base_model,
                candidate=value["poc"]["candidates"]["residual"],
                optimizer_config=value["poc"]["optimizers"]["residual"],
            )
            selected_model = canonical_composite_model_payload(
                base_model=base_model,
                residual_model=residual_model,
                registration=value,
            )
            selected_model_sha256 = sha256_bytes(canonical_json_bytes(selected_model))
            selected_training = {
                "base": base_training,
                "residual": residual_training,
            }
            fit_count += 2
        if fit_count > limits["max_model_fits_per_execution"]:
            raise ResidualPocBlocked("POC exceeded registered model-fit bound")
        if clock() > deadline:
            raise ResidualPocBlocked("POC execution exceeded wall-time bound")
        feature_keys = [
            keys
            for row in pairs
            if row.category in RESIDUAL_CATEGORIES
            for keys in row.structured.feature_keys
        ]
        return {
            "comparison": comparison,
            "feature_collision_diagnostics": feature_collision_diagnostics(
                feature_keys,
                hash_dim=value["poc"]["candidates"]["residual"]["hash_dim"],
            ),
            "fit_count": fit_count,
            "folds": list(folds),
            "paired_result": paired_result,
            "schema_version": EXECUTION_SCHEMA_VERSION,
            "selected_model": selected_model,
            "selected_model_sha256": selected_model_sha256,
            "selected_training": selected_training,
            "singleton_summary": singleton_summary(dataset),
            "train_dataset_sha256": train["source"]["train_dataset_sha256"],
        }
    finally:
        torch.set_num_threads(previous_threads)


def finalize_classification(
    primary: Mapping[str, Any], replay: Mapping[str, Any]
) -> dict[str, Any]:
    primary_sha256 = sha256_bytes(canonical_json_bytes(primary))
    replay_sha256 = sha256_bytes(canonical_json_bytes(replay))
    replay_identity = primary_sha256 == replay_sha256
    comparison = _mapping(primary.get("comparison"), "primary comparison")
    checks = dict(_mapping(comparison.get("checks"), "comparison checks"))
    checks["replay_identity"] = replay_identity
    if not replay_identity or comparison.get("verdict") == "blocked":
        verdict = "blocked"
        selected = None
    elif (
        comparison.get("verdict") == "route_card_residual_selected"
        and comparison.get("selected_candidate_id") == RESIDUAL_CANDIDATE_ID
        and all(checks.values())
    ):
        verdict = "route_card_residual_selected"
        selected = RESIDUAL_CANDIDATE_ID
    else:
        verdict = "poc_valid_without_route_card_residual"
        selected = None
    return {
        "authority": _authority(),
        "checks": checks,
        "primary_execution_sha256": primary_sha256,
        "replay_execution_sha256": replay_sha256,
        "selected_candidate_id": selected,
        "verdict": verdict,
    }


def _canonical_fold_metrics(primary: Mapping[str, Any]) -> list[dict[str, Any]]:
    fields = (
        "base_immutable",
        "base_model_sha256",
        "candidate_metrics",
        "control_metrics",
        "delegation",
        "deltas",
        "fit_row_count",
        "fold",
        "heldout_row_count",
        "residual_diagnostics",
        "residual_model_sha256",
    )
    return [
        {field: copy.deepcopy(fold[field]) for field in fields}
        for fold in primary["paired_result"]["fold_metrics"]
    ]


def build_metrics_artifact(
    *,
    registration_sha256: str,
    primary: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    paired = primary["paired_result"]
    return {
        "aggregate_metrics": copy.deepcopy(paired["aggregate_metrics"]),
        "authority": _authority(),
        "base_immutable": paired["base_immutable"],
        "classification": copy.deepcopy(dict(classification)),
        "comparison": copy.deepcopy(primary["comparison"]),
        "delegation": copy.deepcopy(paired["delegation"]),
        "feature_collision_diagnostics": copy.deepcopy(
            primary["feature_collision_diagnostics"]
        ),
        "fit_count_per_execution": primary["fit_count"],
        "fold_metrics": _canonical_fold_metrics(primary),
        "registration_sha256": registration_sha256,
        "residual_diagnostics": copy.deepcopy(paired["residual_diagnostics"]),
        "schema_version": METRICS_SCHEMA_VERSION,
        "singleton_summary": copy.deepcopy(primary["singleton_summary"]),
        "train_dataset_sha256": primary["train_dataset_sha256"],
    }


def render_report(
    *, registration_sha256: str, metrics: Mapping[str, Any]
) -> str:
    classification = metrics["classification"]
    aggregate = metrics["aggregate_metrics"]
    control = aggregate["control"]
    candidate = aggregate["candidate"]
    deltas = aggregate["deltas"]
    lines = [
        "# Non-Combat Route/Card Residual-Ranker POC",
        "",
        f"- Verdict: `{classification['verdict']}`",
        f"- Selected candidate: `{classification['selected_candidate_id']}`",
        "- Evidence class: `observed-train-only terminal implementation fit`",
        "- Policy-quality claim: `false`",
        f"- Registration SHA-256: `{registration_sha256}`",
        f"- Train dataset SHA-256: `{metrics['train_dataset_sha256']}`",
        "",
        "## Multi-Candidate Held-Out Metrics",
        "",
        "| Metric | Legacy control | Residual candidate | Delta |",
        "| --- | ---: | ---: | ---: |",
        f"| Overall agreement | {control['overall_action_agreement']:.6f} | {candidate['overall_action_agreement']:.6f} | {deltas['overall_action_agreement']:+.6f} |",
        f"| Macro category agreement | {control['macro_category_action_agreement']:.6f} | {candidate['macro_category_action_agreement']:.6f} | {deltas['macro_category_action_agreement']:+.6f} |",
        f"| Overall cross entropy | {control['overall_mean_cross_entropy']:.6f} | {candidate['overall_mean_cross_entropy']:.6f} | {deltas['overall_mean_cross_entropy']:+.6f} |",
        "",
        "## Category Metrics",
        "",
        "| Category | Rows | Control agree | Candidate agree | Agree delta | CE delta |",
        "| --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for category in TARGET_CATEGORIES:
        control_value = control["by_category"][category]
        candidate_value = candidate["by_category"][category]
        delta_value = deltas["by_category"][category]
        lines.append(
            f"| {category} | {control_value['row_count']} | {control_value['action_agreement']:.6f} | {candidate_value['action_agreement']:.6f} | {delta_value['action_agreement']:+.6f} | {delta_value['mean_cross_entropy']:+.6f} |"
        )
    lines.extend(
        [
            "",
            "## Per-Fold Gate Evidence",
            "",
            "| Fold | Rows | Overall agree delta | Macro agree delta | Overall CE delta | Card agree delta | Card CE delta | Route agree delta | Route CE delta | Pass |",
            "| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    fold_checks = {
        item["fold"]: item for item in metrics["comparison"]["fold_checks"]
    }
    for fold in metrics["fold_metrics"]:
        delta_value = fold["deltas"]
        card = delta_value["by_category"]["card_reward"]
        route = delta_value["by_category"]["route"]
        lines.append(
            f"| {fold['fold']} | {fold['heldout_row_count']} | {delta_value['overall_action_agreement']:+.6f} | {delta_value['macro_category_action_agreement']:+.6f} | {delta_value['overall_mean_cross_entropy']:+.6f} | {card['action_agreement']:+.6f} | {card['mean_cross_entropy']:+.6f} | {route['action_agreement']:+.6f} | {route['mean_cross_entropy']:+.6f} | {'pass' if fold_checks[fold['fold']]['pass'] else 'fail'} |"
        )
    residual = metrics["residual_diagnostics"]["overall"]
    delegation = metrics["delegation"]
    singleton = metrics["singleton_summary"]
    lines.extend(
        [
            "",
            "## Terminal Checks",
            "",
            *(
                f"- {name}: `{'pass' if passed else 'fail'}`"
                for name, passed in sorted(classification["checks"].items())
            ),
            "",
            "## Delegation And Residual",
            "",
            f"- Event/shop delegation exact: `{str(delegation['exact']).lower()}` across {delegation['row_count']} rows",
            f"- Residual candidate logits: {residual['candidate_logit_count']}",
            f"- Residual max absolute correction: {residual['max_abs']:.6f}",
            f"- Residual mean absolute correction: {residual['mean_abs']:.6f}",
            f"- Residual RMS correction: {residual['rms']:.6f}",
            "",
            "## Data Strata",
            "",
            f"- Multi-candidate rows: {control['row_count']}",
            f"- Singleton rows excluded from fit/gate: {singleton['row_count']}",
            f"- Total train rows: {singleton['total_row_count']}",
            "",
            "## Boundaries",
            "",
            "- No validation or final-test row contributed to features, fitting, thresholds, selection, or metrics.",
            "- No native simulator, new seed, rollout, floor, victory, live game, checkpoint, outcome, or reward was used.",
            "- Event and shop use exact shared-base outputs; all legal candidates remain available.",
            "- A positive verdict authorizes only a separate fresh-study proposal.",
            "- A valid negative ends model trials on this corpus.",
            "",
            "## Authority",
            "",
            *(
                f"- {name}: `{str(enabled).lower()}`"
                for name, enabled in sorted(_authority().items())
            ),
        ]
    )
    return "\n".join(lines) + "\n"


def build_artifacts(
    *,
    registration: Mapping[str, Any],
    primary: Mapping[str, Any],
    replay: Mapping[str, Any],
) -> dict[str, bytes]:
    registration_value = validate_registration(registration)
    registration_sha256 = sha256_bytes(canonical_json_bytes(registration_value))
    classification = finalize_classification(primary, replay)
    metrics = build_metrics_artifact(
        registration_sha256=registration_sha256,
        primary=primary,
        classification=classification,
    )
    selected_model = (
        copy.deepcopy(primary["selected_model"])
        if classification["selected_candidate_id"] == RESIDUAL_CANDIDATE_ID
        else None
    )
    models = {
        "fold_models": [
            {
                "base_model_sha256": fold["base_model_sha256"],
                "base_training_history": copy.deepcopy(
                    fold["base_training_history"]
                ),
                "fold": fold["fold"],
                "residual_model_sha256": fold["residual_model_sha256"],
                "residual_training_history": copy.deepcopy(
                    fold["residual_training_history"]
                ),
            }
            for fold in primary["paired_result"]["fold_metrics"]
        ],
        "registration_sha256": registration_sha256,
        "replay_selected_model_sha256": (
            replay["selected_model_sha256"] if selected_model is not None else None
        ),
        "schema_version": COMPOSITE_MODEL_SCHEMA_VERSION,
        "selected_model": selected_model,
        "selected_model_sha256": (
            primary["selected_model_sha256"] if selected_model is not None else None
        ),
        "selected_training": (
            copy.deepcopy(primary["selected_training"])
            if selected_model is not None
            else None
        ),
    }
    predictions = {
        "candidate_predictions": copy.deepcopy(
            primary["paired_result"]["candidate_predictions"]
        ),
        "control_predictions": copy.deepcopy(
            primary["paired_result"]["control_predictions"]
        ),
        "primary_execution_sha256": classification["primary_execution_sha256"],
        "registration_sha256": registration_sha256,
        "replay_execution_sha256": classification["replay_execution_sha256"],
        "schema_version": EXECUTION_SCHEMA_VERSION,
    }
    folds = {
        "assignment": copy.deepcopy(primary["folds"]),
        "registration_sha256": registration_sha256,
        "rule": FOLD_RULE,
    }
    payloads = {
        "configuration.json": canonical_json_bytes(registration_value),
        "folds.json": canonical_json_bytes(folds),
        "metrics.json": canonical_json_bytes(metrics),
        "models.json": canonical_json_bytes(models),
        "predictions.json": canonical_json_bytes(predictions),
        "report.md": render_report(
            registration_sha256=registration_sha256, metrics=metrics
        ).encode("utf-8"),
    }
    manifest = {
        "artifact_hashes": {
            name: sha256_bytes(payload) for name, payload in sorted(payloads.items())
        },
        "authority": _authority(),
        "evidence_class": "observed-train-only-terminal-implementation-fit",
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": classification["verdict"],
    }
    payloads["artifact_manifest.json"] = canonical_json_bytes(manifest)
    validate_artifact_payloads(payloads)
    return payloads


def _artifact_json(artifacts: Mapping[str, bytes], name: str) -> dict[str, Any]:
    try:
        payload = artifacts[name]
    except KeyError as exc:
        raise ResidualPocBlocked(f"canonical artifact {name} is missing") from exc
    return _load_artifact_json(payload, f"canonical artifact {name}")


def _parse_finite_hex(value: object, label: str) -> float:
    if not isinstance(value, str):
        raise ResidualPocBlocked(f"{label} must be a hexadecimal float")
    try:
        numeric = float.fromhex(value)
    except ValueError as exc:
        raise ResidualPocBlocked(f"{label} is not a hexadecimal float") from exc
    if not math.isfinite(numeric):
        raise ResidualPocBlocked(f"{label} must be finite")
    return numeric


def _validate_prediction_rows(
    rows: object, *, policy_id: str
) -> list[dict[str, Any]]:
    if not isinstance(rows, list) or not rows:
        raise ResidualPocBlocked(f"{policy_id} predictions must be a nonempty array")
    expected_keys = {
        "candidate_action_ids",
        "candidate_count",
        "category",
        "correct",
        "cross_entropy",
        "decision_index",
        "fold",
        "policy_id",
        "predicted_action_id",
        "probability_hexes",
        "residual_hexes",
        "score_hexes",
        "seed",
        "target_action_id",
        "target_probability",
        "target_probability_hex",
    }
    normalized = []
    for index, raw_row in enumerate(rows):
        row = _mapping(raw_row, f"{policy_id} prediction {index}")
        _require_keys(row, expected_keys, f"{policy_id} prediction {index}")
        _require_exact(row, "policy_id", policy_id, f"{policy_id} prediction {index}")
        if row["category"] not in TARGET_CATEGORIES:
            raise ResidualPocBlocked("prediction category is invalid")
        if (
            isinstance(row["seed"], bool)
            or not isinstance(row["seed"], int)
            or isinstance(row["decision_index"], bool)
            or not isinstance(row["decision_index"], int)
            or row["decision_index"] < 0
            or isinstance(row["fold"], bool)
            or not isinstance(row["fold"], int)
            or row["fold"] not in range(4)
            or not isinstance(row["correct"], bool)
        ):
            raise ResidualPocBlocked("prediction identity fields are invalid")
        if (
            isinstance(row["candidate_count"], bool)
            or not isinstance(row["candidate_count"], int)
            or row["candidate_count"] < 2
        ):
            raise ResidualPocBlocked("prediction candidate count is invalid")
        action_ids = row["candidate_action_ids"]
        if (
            not isinstance(action_ids, list)
            or len(action_ids) != row["candidate_count"]
            or len(action_ids) != len(set(action_ids))
            or any(not isinstance(item, str) or not item for item in action_ids)
        ):
            raise ResidualPocBlocked("prediction candidate ids are invalid")
        if row["target_action_id"] not in action_ids or row[
            "predicted_action_id"
        ] not in action_ids:
            raise ResidualPocBlocked("prediction action is outside the candidate set")
        score_hexes = row["score_hexes"]
        probability_hexes = row["probability_hexes"]
        if not isinstance(score_hexes, list) or len(score_hexes) != len(action_ids):
            raise ResidualPocBlocked("prediction scores are incomplete")
        if not isinstance(probability_hexes, list) or len(probability_hexes) != len(
            action_ids
        ):
            raise ResidualPocBlocked("prediction probabilities are incomplete")
        scores = [
            _parse_finite_hex(item, f"prediction score {position}")
            for position, item in enumerate(score_hexes)
        ]
        probabilities = [
            _parse_finite_hex(item, f"prediction probability {position}")
            for position, item in enumerate(probability_hexes)
        ]
        if any(value < 0.0 or value > 1.0 for value in probabilities) or not math.isclose(
            sum(probabilities), 1.0, rel_tol=1e-6, abs_tol=1e-6
        ):
            raise ResidualPocBlocked("prediction probabilities are invalid")
        torch = _torch_module()
        recomputed_probabilities = torch.softmax(
            torch.tensor(scores, dtype=torch.float32), dim=0
        )
        if _tensor_hexes(recomputed_probabilities) != probability_hexes:
            raise ResidualPocBlocked("prediction probabilities do not match scores")
        selected_index = max(range(len(scores)), key=lambda position: scores[position])
        target_index = action_ids.index(row["target_action_id"])
        target_probability = _parse_finite_hex(
            row["target_probability_hex"], "prediction target probability"
        )
        if (
            isinstance(row["target_probability"], bool)
            or not isinstance(row["target_probability"], (int, float))
            or isinstance(row["cross_entropy"], bool)
            or not isinstance(row["cross_entropy"], (int, float))
            or not math.isfinite(float(row["cross_entropy"]))
            or row["cross_entropy"] < 0.0
            or target_probability != probabilities[target_index]
            or row["target_probability"] != target_probability
            or row["predicted_action_id"] != action_ids[selected_index]
            or row["correct"] != (selected_index == target_index)
            or row["cross_entropy"] != -math.log(target_probability)
        ):
            raise ResidualPocBlocked("prediction derived fields are inconsistent")
        residual_hexes = row["residual_hexes"]
        if not isinstance(residual_hexes, list):
            raise ResidualPocBlocked("prediction residuals are invalid")
        if policy_id == CONTROL_CANDIDATE_ID:
            if residual_hexes:
                raise ResidualPocBlocked("control prediction contains residuals")
        elif row["category"] in RESIDUAL_CATEGORIES:
            if len(residual_hexes) != len(action_ids):
                raise ResidualPocBlocked("candidate residuals are incomplete")
            residuals = [
                _parse_finite_hex(item, f"prediction residual {position}")
                for position, item in enumerate(residual_hexes)
            ]
            if any(abs(residual) > 1.0 for residual in residuals):
                raise ResidualPocBlocked("candidate residual exceeds bound")
        elif residual_hexes:
            raise ResidualPocBlocked("delegated prediction contains residuals")
        normalized.append(row)
    ordering = [(row["seed"], row["decision_index"]) for row in normalized]
    if ordering != sorted(ordering) or len(ordering) != len(set(ordering)):
        raise ResidualPocBlocked("prediction rows are not unique and ordered")
    return normalized


def _validate_training_history(
    value: object, *, epochs: int, label: str, categories: Sequence[str]
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or len(value) != epochs:
        raise ResidualPocBlocked(f"{label} epoch count mismatch")
    for expected_epoch, raw_entry in enumerate(value, start=1):
        entry = _mapping(raw_entry, f"{label} epoch {expected_epoch}")
        _require_keys(
            entry, {"category_losses", "epoch", "loss"}, f"{label} epoch"
        )
        if entry["epoch"] != expected_epoch:
            raise ResidualPocBlocked(f"{label} epoch ordering mismatch")
        losses = _mapping(entry["category_losses"], f"{label} category losses")
        if set(losses) != set(categories):
            raise ResidualPocBlocked(f"{label} category coverage mismatch")
        numeric = [entry["loss"], *losses.values()]
        if any(
            isinstance(item, bool)
            or not isinstance(item, (int, float))
            or not math.isfinite(float(item))
            for item in numeric
        ):
            raise ResidualPocBlocked(f"{label} contains non-finite loss")
    return value


def validate_artifact_payloads(artifacts: Mapping[str, bytes]) -> dict[str, Any]:
    if set(artifacts) != set(CANONICAL_ARTIFACT_NAMES):
        raise ResidualPocBlocked("canonical artifact set is incomplete")
    if any(not isinstance(payload, bytes) for payload in artifacts.values()):
        raise ResidualPocBlocked("canonical artifact payloads must be bytes")
    manifest = _artifact_json(artifacts, "artifact_manifest.json")
    _require_keys(
        manifest,
        {
            "artifact_hashes",
            "authority",
            "evidence_class",
            "registration_sha256",
            "schema_version",
            "verdict",
        },
        "artifact manifest",
    )
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise ResidualPocBlocked("artifact manifest schema mismatch")
    expected_hashes = {
        name: sha256_bytes(artifacts[name])
        for name in sorted(artifacts)
        if name != "artifact_manifest.json"
    }
    if manifest.get("artifact_hashes") != expected_hashes:
        raise ResidualPocBlocked("artifact manifest hash closure mismatch")
    if manifest.get("authority") != _authority():
        raise ResidualPocBlocked("artifact authority mismatch")
    if manifest.get("evidence_class") != (
        "observed-train-only-terminal-implementation-fit"
    ):
        raise ResidualPocBlocked("artifact evidence class mismatch")

    registration = validate_registration(_artifact_json(artifacts, "configuration.json"))
    registration_sha256 = sha256_bytes(canonical_json_bytes(registration))
    if manifest.get("registration_sha256") != registration_sha256:
        raise ResidualPocBlocked("artifact registration identity mismatch")

    metrics = _artifact_json(artifacts, "metrics.json")
    _require_keys(
        metrics,
        {
            "aggregate_metrics",
            "authority",
            "base_immutable",
            "classification",
            "comparison",
            "delegation",
            "feature_collision_diagnostics",
            "fit_count_per_execution",
            "fold_metrics",
            "registration_sha256",
            "residual_diagnostics",
            "schema_version",
            "singleton_summary",
            "train_dataset_sha256",
        },
        "metrics artifact",
    )
    if (
        metrics.get("schema_version") != METRICS_SCHEMA_VERSION
        or metrics.get("registration_sha256") != registration_sha256
        or metrics.get("authority") != _authority()
        or metrics.get("train_dataset_sha256")
        != registration["identity"]["train_dataset_sha256"]
    ):
        raise ResidualPocBlocked("metrics artifact contract mismatch")
    classification = _mapping(metrics.get("classification"), "metrics classification")
    _require_keys(
        classification,
        {
            "authority",
            "checks",
            "primary_execution_sha256",
            "replay_execution_sha256",
            "selected_candidate_id",
            "verdict",
        },
        "metrics classification",
    )
    if classification.get("authority") != _authority():
        raise ResidualPocBlocked("classification authority mismatch")
    if classification.get("verdict") not in {
        "blocked",
        "poc_valid_without_route_card_residual",
        "route_card_residual_selected",
    }:
        raise ResidualPocBlocked("classification verdict is invalid")
    if classification.get("verdict") != manifest.get("verdict"):
        raise ResidualPocBlocked("manifest verdict mismatch")

    predictions = _artifact_json(artifacts, "predictions.json")
    _require_keys(
        predictions,
        {
            "candidate_predictions",
            "control_predictions",
            "primary_execution_sha256",
            "registration_sha256",
            "replay_execution_sha256",
            "schema_version",
        },
        "predictions artifact",
    )
    if (
        predictions.get("schema_version") != EXECUTION_SCHEMA_VERSION
        or predictions.get("registration_sha256") != registration_sha256
        or predictions.get("primary_execution_sha256")
        != classification.get("primary_execution_sha256")
        or predictions.get("replay_execution_sha256")
        != classification.get("replay_execution_sha256")
    ):
        raise ResidualPocBlocked("prediction execution identity mismatch")
    control_predictions = _validate_prediction_rows(
        predictions.get("control_predictions"), policy_id=CONTROL_CANDIDATE_ID
    )
    candidate_predictions = _validate_prediction_rows(
        predictions.get("candidate_predictions"), policy_id=RESIDUAL_CANDIDATE_ID
    )
    control_keys = [
        (row["seed"], row["decision_index"]) for row in control_predictions
    ]
    candidate_keys = [
        (row["seed"], row["decision_index"]) for row in candidate_predictions
    ]
    if control_keys != candidate_keys:
        raise ResidualPocBlocked("control and candidate prediction identities differ")
    torch = _torch_module()
    for control_row, candidate_row in zip(
        control_predictions, candidate_predictions, strict=True
    ):
        paired_fields = (
            "candidate_action_ids",
            "candidate_count",
            "category",
            "decision_index",
            "fold",
            "seed",
            "target_action_id",
        )
        if any(control_row[field] != candidate_row[field] for field in paired_fields):
            raise ResidualPocBlocked("paired candidate decision evidence differs")
        if candidate_row["category"] in RESIDUAL_CATEGORIES:
            base_scores = torch.tensor(
                [float.fromhex(item) for item in control_row["score_hexes"]],
                dtype=torch.float32,
            )
            residuals = torch.tensor(
                [float.fromhex(item) for item in candidate_row["residual_hexes"]],
                dtype=torch.float32,
            )
            if _tensor_hexes(base_scores + residuals) != candidate_row["score_hexes"]:
                raise ResidualPocBlocked(
                    "candidate score does not equal base score plus residual"
                )

    aggregate_control = metrics_from_predictions(control_predictions)
    aggregate_candidate = metrics_from_predictions(candidate_predictions)
    aggregate = {
        "candidate": aggregate_candidate,
        "control": aggregate_control,
        "deltas": metric_deltas(aggregate_control, aggregate_candidate),
    }
    if canonical_json_bytes(aggregate) != canonical_json_bytes(
        metrics.get("aggregate_metrics")
    ):
        raise ResidualPocBlocked("aggregate metric materialization mismatch")

    fold_metrics = metrics.get("fold_metrics")
    if not isinstance(fold_metrics, list) or len(fold_metrics) != 4:
        raise ResidualPocBlocked("canonical per-fold metrics are incomplete")
    fold_evidence = []
    for expected_fold, raw_fold in enumerate(fold_metrics):
        fold = _mapping(raw_fold, f"fold metrics {expected_fold}")
        _require_keys(
            fold,
            {
                "base_immutable",
                "base_model_sha256",
                "candidate_metrics",
                "control_metrics",
                "delegation",
                "deltas",
                "fit_row_count",
                "fold",
                "heldout_row_count",
                "residual_diagnostics",
                "residual_model_sha256",
            },
            f"fold metrics {expected_fold}",
        )
        if (
            fold["fold"] != expected_fold
            or fold["base_immutable"] is not True
            or not _is_sha256(fold["base_model_sha256"])
            or not _is_sha256(fold["residual_model_sha256"])
        ):
            raise ResidualPocBlocked("fold identity or base immutability mismatch")
        fold_control = [
            row for row in control_predictions if row["fold"] == expected_fold
        ]
        fold_candidate = [
            row for row in candidate_predictions if row["fold"] == expected_fold
        ]
        if (
            len(fold_control) != fold["heldout_row_count"]
            or len(fold_control) != len(fold_candidate)
            or fold["fit_row_count"] != len(control_predictions) - len(fold_control)
        ):
            raise ResidualPocBlocked("fold held-out row count mismatch")
        recomputed_control = metrics_from_predictions(fold_control)
        recomputed_candidate = metrics_from_predictions(fold_candidate)
        recomputed_delta = metric_deltas(recomputed_control, recomputed_candidate)
        recomputed_delegation = delegation_summary(fold_control, fold_candidate)
        recomputed_residual = residual_diagnostics(fold_candidate)
        expected_materialized = (
            recomputed_control,
            recomputed_candidate,
            recomputed_delta,
            recomputed_delegation,
            recomputed_residual,
        )
        actual_materialized = (
            fold["control_metrics"],
            fold["candidate_metrics"],
            fold["deltas"],
            fold["delegation"],
            fold["residual_diagnostics"],
        )
        if canonical_json_bytes(actual_materialized) != canonical_json_bytes(
            expected_materialized
        ):
            raise ResidualPocBlocked("per-fold metric materialization mismatch")
        fold_evidence.append(fold)
    aggregate_delegation = delegation_summary(
        control_predictions, candidate_predictions
    )
    aggregate_residual = residual_diagnostics(candidate_predictions)
    if canonical_json_bytes(aggregate_delegation) != canonical_json_bytes(
        metrics.get("delegation")
    ):
        raise ResidualPocBlocked("aggregate delegation materialization mismatch")
    if canonical_json_bytes(aggregate_residual) != canonical_json_bytes(
        metrics.get("residual_diagnostics")
    ):
        raise ResidualPocBlocked("aggregate residual materialization mismatch")
    gate_input = {
        "aggregate_metrics": aggregate,
        "base_immutable": metrics.get("base_immutable"),
        "delegation": aggregate_delegation,
        "fold_metrics": fold_evidence,
        "residual_diagnostics": aggregate_residual,
    }
    recomputed_comparison = compare_paired_result(
        gate_input,
        thresholds=registration["poc"]["evaluation"]["thresholds"],
        residual_scale=registration["poc"]["candidates"]["residual"][
            "residual_scale"
        ],
    )
    if canonical_json_bytes(recomputed_comparison) != canonical_json_bytes(
        metrics.get("comparison")
    ):
        raise ResidualPocBlocked("terminal gate materialization mismatch")
    replay_identity = classification.get("primary_execution_sha256") == classification.get(
        "replay_execution_sha256"
    )
    expected_checks = {**recomputed_comparison["checks"], "replay_identity": replay_identity}
    if classification.get("checks") != expected_checks:
        raise ResidualPocBlocked("classification checks mismatch")
    expected_verdict = (
        "blocked"
        if not replay_identity or recomputed_comparison["verdict"] == "blocked"
        else recomputed_comparison["verdict"]
    )
    expected_selected = (
        RESIDUAL_CANDIDATE_ID
        if expected_verdict == "route_card_residual_selected"
        else None
    )
    if (
        classification.get("verdict") != expected_verdict
        or classification.get("selected_candidate_id") != expected_selected
    ):
        raise ResidualPocBlocked("classification verdict application mismatch")

    folds = _artifact_json(artifacts, "folds.json")
    _require_keys(
        folds, {"assignment", "registration_sha256", "rule"}, "folds artifact"
    )
    expected_folds = list(
        build_seed_folds(
            registration["poc"]["seeds"],
            fold_count=registration["poc"]["folds"]["count"],
        )
    )
    if (
        folds.get("registration_sha256") != registration_sha256
        or folds.get("rule") != FOLD_RULE
        or folds.get("assignment") != expected_folds
    ):
        raise ResidualPocBlocked("fold artifact contract mismatch")
    heldout_fold_by_seed = {
        seed: fold["fold"]
        for fold in expected_folds
        for seed in fold["heldout_seeds"]
    }
    if any(
        row["seed"] not in heldout_fold_by_seed
        or row["fold"] != heldout_fold_by_seed[row["seed"]]
        for row in control_predictions
    ):
        raise ResidualPocBlocked("prediction seed is assigned to the wrong fold")

    models = _artifact_json(artifacts, "models.json")
    _require_keys(
        models,
        {
            "fold_models",
            "registration_sha256",
            "replay_selected_model_sha256",
            "schema_version",
            "selected_model",
            "selected_model_sha256",
            "selected_training",
        },
        "models artifact",
    )
    if (
        models.get("schema_version") != COMPOSITE_MODEL_SCHEMA_VERSION
        or models.get("registration_sha256") != registration_sha256
    ):
        raise ResidualPocBlocked("models artifact contract mismatch")
    fold_models = models.get("fold_models")
    if not isinstance(fold_models, list) or len(fold_models) != 4:
        raise ResidualPocBlocked("fold model inventory mismatch")
    for expected_fold, raw_fold in enumerate(fold_models):
        fold = _mapping(raw_fold, f"fold model {expected_fold}")
        _require_keys(
            fold,
            {
                "base_model_sha256",
                "base_training_history",
                "fold",
                "residual_model_sha256",
                "residual_training_history",
            },
            f"fold model {expected_fold}",
        )
        if fold["fold"] != expected_fold or not _is_sha256(
            fold["base_model_sha256"]
        ) or not _is_sha256(fold["residual_model_sha256"]):
            raise ResidualPocBlocked("fold model identity mismatch")
        if (
            fold["base_model_sha256"]
            != fold_metrics[expected_fold]["base_model_sha256"]
            or fold["residual_model_sha256"]
            != fold_metrics[expected_fold]["residual_model_sha256"]
        ):
            raise ResidualPocBlocked("fold model and metric identities differ")
        _validate_training_history(
            fold["base_training_history"],
            epochs=registration["poc"]["optimizers"]["base"]["epochs"],
            label=f"fold {expected_fold} base history",
            categories=TARGET_CATEGORIES,
        )
        _validate_training_history(
            fold["residual_training_history"],
            epochs=registration["poc"]["optimizers"]["residual"]["epochs"],
            label=f"fold {expected_fold} residual history",
            categories=RESIDUAL_CATEGORIES,
        )
    selected_model = models.get("selected_model")
    if expected_selected == RESIDUAL_CANDIDATE_ID:
        if not isinstance(selected_model, Mapping):
            raise ResidualPocBlocked("selected composite model is missing")
        base_model, residual_model = load_composite_model_payload(
            selected_model, registration=registration
        )
        canonical = canonical_composite_model_payload(
            base_model=base_model,
            residual_model=residual_model,
            registration=registration,
        )
        selected_sha256 = sha256_bytes(canonical_json_bytes(canonical))
        if (
            models.get("selected_model_sha256") != selected_sha256
            or models.get("replay_selected_model_sha256") != selected_sha256
            or not isinstance(models.get("selected_training"), Mapping)
            or metrics.get("fit_count_per_execution") != 10
        ):
            raise ResidualPocBlocked("selected composite model identity mismatch")
        selected_training = _mapping(
            models["selected_training"], "selected model training"
        )
        _require_keys(
            selected_training, {"base", "residual"}, "selected model training"
        )
        base_training = _mapping(
            selected_training["base"], "selected base training"
        )
        residual_training = _mapping(
            selected_training["residual"], "selected residual training"
        )
        _require_keys(
            base_training,
            {"final_model_sha256", "history", "row_count"},
            "selected base training",
        )
        _require_keys(
            residual_training,
            {"base_immutable", "final_model_sha256", "history", "row_count"},
            "selected residual training",
        )
        expected_base_sha256 = sha256_bytes(
            canonical_json_bytes(canonical["base_model"])
        )
        expected_residual_sha256 = sha256_bytes(
            canonical_json_bytes(canonical["residual_model"])
        )
        residual_row_count = sum(
            aggregate["control"]["by_category"][category]["row_count"]
            for category in RESIDUAL_CATEGORIES
        )
        if (
            base_training["final_model_sha256"] != expected_base_sha256
            or residual_training["final_model_sha256"]
            != expected_residual_sha256
            or base_training["row_count"] != aggregate["control"]["row_count"]
            or residual_training["row_count"] != residual_row_count
            or residual_training["base_immutable"] is not True
        ):
            raise ResidualPocBlocked("selected training identity mismatch")
        _validate_training_history(
            base_training["history"],
            epochs=registration["poc"]["optimizers"]["base"]["epochs"],
            label="selected base history",
            categories=TARGET_CATEGORIES,
        )
        _validate_training_history(
            residual_training["history"],
            epochs=registration["poc"]["optimizers"]["residual"]["epochs"],
            label="selected residual history",
            categories=RESIDUAL_CATEGORIES,
        )
    elif any(
        models.get(field) is not None
        for field in ("selected_model", "selected_model_sha256", "selected_training")
    ) or models.get("replay_selected_model_sha256") is not None:
        raise ResidualPocBlocked("negative or blocked POC published a selected model")
    elif metrics.get("fit_count_per_execution") != 8:
        raise ResidualPocBlocked("negative POC model-fit count mismatch")

    singleton = _mapping(metrics.get("singleton_summary"), "singleton summary")
    _require_keys(
        singleton,
        {
            "by_category",
            "excluded_from_competence_metrics",
            "row_count",
            "total_by_category",
            "total_row_count",
        },
        "singleton summary",
    )
    singleton_by_category = _mapping(
        singleton["by_category"], "singleton summary by category"
    )
    total_by_category = _mapping(
        singleton["total_by_category"], "singleton total by category"
    )
    if (
        singleton.get("excluded_from_competence_metrics") is not True
        or set(singleton_by_category) != set(TARGET_CATEGORIES)
        or set(total_by_category) != set(TARGET_CATEGORIES)
        or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in [
                singleton["row_count"],
                singleton["total_row_count"],
                *singleton_by_category.values(),
                *total_by_category.values(),
            ]
        )
        or singleton["row_count"] != sum(singleton_by_category.values())
        or singleton["total_row_count"]
        != singleton["row_count"] + aggregate["control"]["row_count"]
        or any(
            total_by_category[category]
            != singleton_by_category[category]
            + aggregate["control"]["by_category"][category]["row_count"]
            for category in TARGET_CATEGORIES
        )
    ):
        raise ResidualPocBlocked("singleton competence boundary mismatch")
    try:
        report = artifacts["report.md"].decode("utf-8")
    except UnicodeError as exc:
        raise ResidualPocBlocked(f"report is invalid UTF-8: {exc}") from exc
    if not report.startswith("# Non-Combat Route/Card Residual-Ranker POC\n"):
        raise ResidualPocBlocked("report header mismatch")
    return manifest


def publish_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    replace: Callable[[str | os.PathLike[str], str | os.PathLike[str]], None] = os.replace,
) -> None:
    validate_artifact_payloads(artifacts)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    allowed = set(CANONICAL_ARTIFACT_NAMES) | {"execution_journal.json"}
    existing = {path.name for path in root.iterdir()}
    if not existing.issubset(allowed):
        raise ResidualPocBlocked("output artifact inventory mismatch")
    order = sorted(name for name in artifacts if name != "artifact_manifest.json")
    order.append("artifact_manifest.json")
    destinations = {name: root / name for name in order}
    previous = {
        name: path.read_bytes() if path.is_file() else None
        for name, path in destinations.items()
    }
    temporary = {
        name: path.with_name(f".{path.name}.tmp") for name, path in destinations.items()
    }
    installed = []
    try:
        for name in order:
            temporary[name].write_bytes(artifacts[name])
        for name in order:
            replace(temporary[name], destinations[name])
            installed.append(name)
    except Exception:
        for name in installed:
            destination = destinations[name]
            prior = previous[name]
            if prior is None:
                destination.unlink(missing_ok=True)
            else:
                restore = destination.with_name(f".{destination.name}.restore")
                restore.write_bytes(prior)
                os.replace(restore, destination)
        raise
    finally:
        for path in temporary.values():
            path.unlink(missing_ok=True)
        for path in destinations.values():
            path.with_name(f".{path.name}.restore").unlink(missing_ok=True)
    validate_artifact_directory(root)


def validate_artifact_directory(output_dir: Path | str) -> dict[str, Any]:
    root = Path(output_dir)
    allowed = set(CANONICAL_ARTIFACT_NAMES) | {"execution_journal.json"}
    try:
        entries = {path.name for path in root.iterdir()}
    except OSError as exc:
        raise ResidualPocBlocked(f"cannot inspect artifact directory: {exc}") from exc
    if not set(CANONICAL_ARTIFACT_NAMES).issubset(entries) or not entries.issubset(
        allowed
    ):
        raise ResidualPocBlocked("published artifact inventory mismatch")
    artifacts = {name: (root / name).read_bytes() for name in CANONICAL_ARTIFACT_NAMES}
    manifest = validate_artifact_payloads(artifacts)
    if manifest["artifact_hashes"] != {
        name: sha256_file(root / name) for name in sorted(manifest["artifact_hashes"])
    }:
        raise ResidualPocBlocked("published artifact hash closure mismatch")
    journal_path = root / "execution_journal.json"
    if journal_path.exists():
        journal = _load_json(journal_path, "execution journal")
        if journal.get("schema_version") != JOURNAL_SCHEMA_VERSION or journal.get(
            "canonical"
        ) is not False:
            raise ResidualPocBlocked("execution journal contract mismatch")
    return manifest


def publish_execution_journal(
    output_dir: Path | str,
    *,
    primary_elapsed_seconds: float,
    replay_elapsed_seconds: float,
    wall_time_budget_seconds: float,
) -> None:
    root = Path(output_dir)
    validate_artifact_directory(root)
    values = {
        "primary_elapsed_seconds": _finite_number(
            primary_elapsed_seconds, "primary elapsed seconds"
        ),
        "replay_elapsed_seconds": _finite_number(
            replay_elapsed_seconds, "replay elapsed seconds"
        ),
        "wall_time_budget_seconds": _finite_number(
            wall_time_budget_seconds, "wall-time budget seconds"
        ),
    }
    if any(value < 0.0 for value in values.values()):
        raise ResidualPocBlocked("execution journal values must be non-negative")
    journal = {
        "canonical": False,
        **values,
        "schema_version": JOURNAL_SCHEMA_VERSION,
    }
    destination = root / "execution_journal.json"
    temporary = destination.with_name(f".{destination.name}.tmp")
    temporary.write_bytes(canonical_json_bytes(journal))
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    validate_artifact_directory(root)


def run_registered_poc(
    *,
    registration: Mapping[str, Any],
    train_input: Mapping[str, Any],
    output_dir: Path | str,
) -> dict[str, Any]:
    value = validate_registration(registration)
    start = time.monotonic()
    primary = execute_poc(registration=value, train_input=train_input)
    primary_elapsed = time.monotonic() - start
    replay_start = time.monotonic()
    replay = execute_poc(registration=value, train_input=train_input)
    replay_elapsed = time.monotonic() - replay_start
    artifacts = build_artifacts(registration=value, primary=primary, replay=replay)
    publish_artifacts(output_dir, artifacts)
    publish_execution_journal(
        output_dir,
        primary_elapsed_seconds=primary_elapsed,
        replay_elapsed_seconds=replay_elapsed,
        wall_time_budget_seconds=value["poc"]["limits"][
            "max_wall_seconds_per_execution"
        ],
    )
    return validate_artifact_directory(output_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser(
        "register", description="Freeze the exact terminal residual POC registration."
    )
    register.add_argument("--implementation-commit", required=True)
    register.add_argument("--train-input", type=Path, required=True)
    register.add_argument("--train-input-manifest", type=Path, required=True)
    register.add_argument("--structured-poc-manifest", type=Path, required=True)
    register.add_argument("--structured-poc-failure-audit", type=Path, required=True)
    register.add_argument("--output", type=Path, required=True)

    run = commands.add_parser(
        "run", description="Run one registered paired comparison and replay."
    )
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)

    validate = commands.add_parser(
        "validate", description="Rehash and validate a residual POC artifact set."
    )
    validate.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        if args.command == "register":
            registration = build_registration(
                repo_root=repo_root,
                implementation_commit=args.implementation_commit,
                train_input_path=args.train_input,
                train_input_manifest_path=args.train_input_manifest,
                structured_poc_manifest_path=args.structured_poc_manifest,
                structured_poc_failure_audit_path=args.structured_poc_failure_audit,
            )
            validate_registered_identity(registration, repo_root=repo_root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical_json_bytes(registration))
            print(sha256_file(args.output))
            return 0
        if args.command == "run":
            registration = load_registration(args.input)
            validate_registered_identity(registration, repo_root=repo_root)
            identity = registration["identity"]
            train_input = load_train_input_archive(
                repo_root / identity["train_input"]["path"],
                manifest_path=repo_root / identity["train_input_manifest"]["path"],
                expected_seeds=registration["poc"]["seeds"],
            )
            if train_input["source"]["train_dataset_sha256"] != identity[
                "train_dataset_sha256"
            ]:
                raise ResidualPocBlocked("registered train dataset identity mismatch")
            manifest = run_registered_poc(
                registration=registration,
                train_input=train_input,
                output_dir=args.output_dir,
            )
            print(json.dumps(manifest, indent=2, sort_keys=True))
            return 0
        manifest = validate_artifact_directory(args.output_dir)
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    except StructuredPocBlocked as exc:
        print(f"blocked: {exc}", file=__import__("sys").stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
