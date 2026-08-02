"""Run a train-only structured non-combat baseline-ranker implementation POC."""

from __future__ import annotations

import argparse
import copy
import gzip
import hashlib
import json
import math
import os
import random
import re
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from numbers import Real
from pathlib import Path, PurePosixPath
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    NATIVE_TARGET_POLICY_ID,
    SOURCE_TYPE,
    TARGET_CATEGORIES,
    SimulatorAdapterError,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
    validate_candidates,
    validate_native_baseline_action,
    validate_snapshot,
)
from analysis_scripts.noncombat_simulator_baseline_warm_start import (
    DATASET_SCHEMA_VERSION,
    DEMONSTRATION_ARTIFACT_SCHEMA_VERSION,
    DEMONSTRATION_SCHEMA_VERSION,
    build_warm_start_model,
    canonical_warm_start_model_payload,
    load_warm_start_model,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    _candidate_features as legacy_candidate_features,
    _git,
    _verify_sources_at_commit,
    hash_bound_files,
    project_policy_view,
)


REGISTRATION_SCHEMA_VERSION = "noncombat-structured-baseline-ranker-poc-input-v1"
TRAIN_INPUT_SCHEMA_VERSION = "noncombat-structured-baseline-ranker-train-input-v1"
TRAIN_INPUT_MANIFEST_SCHEMA_VERSION = (
    "noncombat-structured-baseline-ranker-train-input-manifest-v1"
)
ARCHIVE_MANIFEST_SCHEMA_VERSION = "noncombat-simulator-baseline-corpus-archive-v1"
STRUCTURED_FEATURE_VERSION = "noncombat-structured-policy-features-v1"
LEGACY_CANDIDATE_ID = "legacy-hash-mlp-multichoice-v1"
STRUCTURED_CANDIDATE_ID = "structured-category-ranker-v1"
FOLD_RULE = "sorted-round-robin-seed-folds-v1"
TIE_RULE = "first-max-in-adapter-order"
MODEL_SCHEMA_VERSION = "noncombat-structured-baseline-ranker-model-v1"
EXECUTION_SCHEMA_VERSION = "noncombat-structured-baseline-ranker-execution-v1"
METRICS_SCHEMA_VERSION = "noncombat-structured-baseline-ranker-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-structured-baseline-ranker-manifest-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-structured-baseline-ranker-journal-v1"
REGISTERED_TRAIN_SEEDS = tuple(range(4000, 4032))
REGISTERED_SOURCE_FILES = (
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_baseline_warm_start.py",
    "analysis_scripts/noncombat_simulator_training_smoke.py",
    "analysis_scripts/noncombat_structured_baseline_ranker_poc.py",
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


class StructuredPocBlocked(RuntimeError):
    """Raised when a POC evidence or execution contract fails closed."""


def _authority() -> dict[str, bool]:
    return {
        "dagger": False,
        "formal_noncombat_rl": False,
        "live_gameplay": False,
        "live_policy_loading": False,
        "native_evidence_collection": False,
        "ope_reinterpretation": False,
        "policy_promotion": False,
        "qualification": False,
        "simulator_rollout": False,
    }


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise StructuredPocBlocked(f"{label} must be an object")
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise StructuredPocBlocked(f"{label} must be an array")
    return list(value)


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise StructuredPocBlocked(f"{label} keys mismatch")


def _require_exact(
    value: Mapping[str, Any], field: str, expected: object, label: str
) -> None:
    actual = value.get(field)
    if type(actual) is not type(expected) or actual != expected:
        raise StructuredPocBlocked(f"{label}.{field} must equal {expected!r}")


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _is_commit(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise StructuredPocBlocked(f"{label} must be a positive integer")
    return value


def _finite_number(value: object, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, Real):
        raise StructuredPocBlocked(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise StructuredPocBlocked(f"{label} must be a finite number")
    return result


def _seed_array(value: object, label: str) -> list[int]:
    seeds = _sequence(value, label)
    if not seeds:
        raise StructuredPocBlocked(f"{label} must be nonempty")
    if any(isinstance(seed, bool) or not isinstance(seed, int) for seed in seeds):
        raise StructuredPocBlocked(f"{label} must contain only integers")
    if seeds != sorted(set(seeds)):
        raise StructuredPocBlocked(f"{label} must be sorted and unique")
    return seeds


def _validate_binding(value: object, label: str) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    path = binding["path"]
    if not isinstance(path, str) or not path:
        raise StructuredPocBlocked(f"{label}.path is required")
    pure_path = PurePosixPath(path.replace("\\", "/"))
    if pure_path.is_absolute() or ".." in pure_path.parts:
        raise StructuredPocBlocked(f"{label}.path must be repository-relative")
    if not _is_sha256(binding["sha256"]):
        raise StructuredPocBlocked(f"{label}.sha256 is invalid")
    binding["size_bytes"] = _positive_int(binding["size_bytes"], f"{label}.size_bytes")
    return binding


def _actual_binding(repo_root: Path, binding: Mapping[str, Any]) -> dict[str, Any]:
    path = (repo_root / str(binding["path"])).resolve()
    try:
        path.relative_to(repo_root)
    except ValueError as exc:
        raise StructuredPocBlocked(
            f"bound artifact escapes repository: {binding['path']}"
        ) from exc
    if not path.is_file():
        raise StructuredPocBlocked(f"bound artifact is missing: {binding['path']}")
    return {
        "path": str(binding["path"]),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise StructuredPocBlocked(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _load_json(path: Path | str, label: str) -> dict[str, Any]:
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=_reject_duplicate_pairs)
    except StructuredPocBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StructuredPocBlocked(f"cannot load {label}: {exc}") from exc
    return _mapping(value, label)


def _load_gzip_json(path: Path | str, label: str) -> dict[str, Any]:
    try:
        with gzip.open(path, "rt", encoding="utf-8") as handle:
            value = json.load(handle, object_pairs_hook=_reject_duplicate_pairs)
    except StructuredPocBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise StructuredPocBlocked(f"cannot load {label}: {exc}") from exc
    return _mapping(value, label)


def _validate_candidate_config(value: object, *, structured: bool) -> dict[str, Any]:
    label = "poc.candidates.structured" if structured else "poc.candidates.control"
    candidate = _mapping(value, label)
    _require_keys(
        candidate,
        {"architecture", "feature_version", "hash_dim", "hidden_dim", "id"},
        label,
    )
    expected = (
        {
            "architecture": "category-specific-mlp-v1",
            "feature_version": STRUCTURED_FEATURE_VERSION,
            "hash_dim": 2048,
            "hidden_dim": 64,
            "id": STRUCTURED_CANDIDATE_ID,
        }
        if structured
        else {
            "architecture": "shared-mlp-v1",
            "feature_version": "noncombat-simulator-policy-features-v1",
            "hash_dim": 1024,
            "hidden_dim": 128,
            "id": LEGACY_CANDIDATE_ID,
        }
    )
    for field, expected_value in expected.items():
        _require_exact(candidate, field, expected_value, label)
    return candidate


def validate_registration(value: object) -> dict[str, Any]:
    """Validate the exact train-only POC contract without supplying defaults."""
    registration = _mapping(value, "registration")
    _require_keys(registration, {"authority", "identity", "poc", "schema_version"}, "registration")
    _require_exact(
        registration, "schema_version", REGISTRATION_SCHEMA_VERSION, "registration"
    )

    identity = _mapping(registration["identity"], "identity")
    _require_keys(
        identity,
        {
            "implementation",
            "runtime",
            "source_archive",
            "source_archive_manifest",
            "source_warm_start_manifest",
            "teacher_policy_id",
            "train_dataset_sha256",
            "train_input",
            "train_input_manifest",
        },
        "identity",
    )
    for name in (
        "source_archive",
        "source_archive_manifest",
        "source_warm_start_manifest",
        "train_input",
        "train_input_manifest",
    ):
        identity[name] = _validate_binding(identity[name], f"identity.{name}")
    _require_exact(identity, "teacher_policy_id", NATIVE_TARGET_POLICY_ID, "identity")
    if not _is_sha256(identity["train_dataset_sha256"]):
        raise StructuredPocBlocked("identity.train_dataset_sha256 is invalid")

    implementation = _mapping(identity["implementation"], "identity.implementation")
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "identity.implementation",
    )
    if not _is_commit(implementation["commit"]):
        raise StructuredPocBlocked("identity.implementation.commit is invalid")
    if implementation["source_files"] != list(REGISTERED_SOURCE_FILES):
        raise StructuredPocBlocked(
            "identity.implementation.source_files must equal the registered source list"
        )
    if not _is_sha256(implementation["source_sha256"]):
        raise StructuredPocBlocked("identity.implementation.source_sha256 is invalid")
    identity["implementation"] = implementation

    runtime = _mapping(identity["runtime"], "identity.runtime")
    _require_keys(runtime, {"python", "torch"}, "identity.runtime")
    if any(not isinstance(runtime[name], str) or not runtime[name] for name in runtime):
        raise StructuredPocBlocked("identity.runtime values are required")
    identity["runtime"] = runtime

    poc = _mapping(registration["poc"], "poc")
    _require_keys(
        poc,
        {
            "candidates",
            "evaluation",
            "folds",
            "limits",
            "optimizer",
            "seeds",
            "tie_rule",
        },
        "poc",
    )
    seeds = _seed_array(poc["seeds"], "poc.seeds")
    if seeds != list(REGISTERED_TRAIN_SEEDS):
        raise StructuredPocBlocked("poc.seeds must equal 4000..4031")
    poc["seeds"] = seeds
    _require_exact(poc, "tie_rule", TIE_RULE, "poc")

    folds = _mapping(poc["folds"], "poc.folds")
    _require_keys(folds, {"count", "rule"}, "poc.folds")
    _require_exact(folds, "count", 4, "poc.folds")
    _require_exact(folds, "rule", FOLD_RULE, "poc.folds")
    poc["folds"] = folds

    candidates = _mapping(poc["candidates"], "poc.candidates")
    _require_keys(candidates, {"control", "structured"}, "poc.candidates")
    candidates["control"] = _validate_candidate_config(
        candidates["control"], structured=False
    )
    candidates["structured"] = _validate_candidate_config(
        candidates["structured"], structured=True
    )
    poc["candidates"] = candidates

    optimizer = _mapping(poc["optimizer"], "poc.optimizer")
    expected_optimizer = {
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
    _require_keys(optimizer, set(expected_optimizer), "poc.optimizer")
    for field, expected in expected_optimizer.items():
        _require_exact(optimizer, field, expected, "poc.optimizer")
    poc["optimizer"] = optimizer

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
    exact_thresholds = {
        "maximum_mean_cross_entropy_delta": 0.0,
        "minimum_card_reward_agreement_delta": 0.0,
        "minimum_macro_agreement_delta": 0.03,
        "minimum_overall_agreement_delta": 0.03,
        "minimum_route_agreement_delta": 0.0,
    }
    _require_keys(thresholds, set(exact_thresholds), "poc.evaluation.thresholds")
    for field, expected in exact_thresholds.items():
        _require_exact(thresholds, field, expected, "poc.evaluation.thresholds")
    evaluation["thresholds"] = thresholds
    poc["evaluation"] = evaluation

    limits = _mapping(poc["limits"], "poc.limits")
    exact_limits = {
        "max_candidates_per_row": 32,
        "max_model_fits_per_execution": 9,
        "max_rows": 1500,
        "max_wall_seconds_per_execution": 900.0,
    }
    _require_keys(limits, set(exact_limits), "poc.limits")
    for field, expected in exact_limits.items():
        _require_exact(limits, field, expected, "poc.limits")
    poc["limits"] = limits

    authority = _mapping(registration["authority"], "authority")
    if authority != _authority():
        raise StructuredPocBlocked("registration authority must remain all false")
    registration["identity"] = identity
    registration["poc"] = poc
    registration["authority"] = authority
    return registration


def load_registration(path: Path | str) -> dict[str, Any]:
    return validate_registration(_load_json(path, "registration"))


def validate_train_dataset(
    value: object, *, expected_seeds: Sequence[int]
) -> dict[str, Any]:
    """Validate retained teacher rows without constructing model features."""
    dataset = _mapping(value, "train dataset")
    expected_seed_list = _seed_array(expected_seeds, "expected train seeds")
    if dataset.get("schema_version") != DATASET_SCHEMA_VERSION:
        raise StructuredPocBlocked("train dataset schema mismatch")
    if dataset.get("cohort") != "train":
        raise StructuredPocBlocked("train dataset cohort must equal train")
    if dataset.get("source_type") != SOURCE_TYPE:
        raise StructuredPocBlocked("train dataset source_type mismatch")
    if dataset.get("teacher_policy_id") != NATIVE_TARGET_POLICY_ID:
        raise StructuredPocBlocked("train dataset teacher policy mismatch")
    if dataset.get("seeds") != expected_seed_list:
        raise StructuredPocBlocked("train dataset seeds mismatch")
    if dataset.get("all_categories") != list(TARGET_CATEGORIES):
        raise StructuredPocBlocked("train dataset category coverage mismatch")
    rows = dataset.get("rows")
    episodes = dataset.get("episodes")
    if not isinstance(rows, list) or not rows:
        raise StructuredPocBlocked("train dataset rows must be nonempty")
    if not isinstance(episodes, list) or len(episodes) != len(expected_seed_list):
        raise StructuredPocBlocked("train dataset episodes mismatch")

    rows_by_seed: dict[int, list[dict[str, Any]]] = {
        seed: [] for seed in expected_seed_list
    }
    ordering: list[tuple[int, int]] = []
    categories: set[str] = set()
    for row_value in rows:
        row = _mapping(row_value, "train demonstration row")
        if row.get("schema_version") != DEMONSTRATION_SCHEMA_VERSION:
            raise StructuredPocBlocked("train demonstration row schema mismatch")
        if row.get("cohort") != "train" or row.get("source_type") != SOURCE_TYPE:
            raise StructuredPocBlocked("train demonstration row cohort mismatch")
        seed = row.get("seed")
        decision_index = row.get("decision_index")
        if seed not in rows_by_seed:
            raise StructuredPocBlocked("train demonstration row seed mismatch")
        if (
            isinstance(decision_index, bool)
            or not isinstance(decision_index, int)
            or decision_index < 0
        ):
            raise StructuredPocBlocked("train demonstration decision index is invalid")
        ordering.append((seed, decision_index))
        try:
            snapshot = validate_snapshot(row.get("source_snapshot"))
            candidates = validate_candidates(
                row.get("candidate_actions"), category=snapshot["category"]
            )
            teacher = validate_native_baseline_action(
                row.get("teacher"), category=snapshot["category"], candidates=candidates
            )
        except SimulatorAdapterError as exc:
            raise StructuredPocBlocked(f"invalid train demonstration row: {exc}") from exc
        if snapshot["terminal"] or snapshot["category"] != row.get("category"):
            raise StructuredPocBlocked("train demonstration snapshot mismatch")
        if row.get("source_snapshot_sha256") != sha256_bytes(
            canonical_json_bytes(snapshot)
        ):
            raise StructuredPocBlocked("train demonstration snapshot hash mismatch")
        if row.get("candidate_actions_sha256") != sha256_bytes(
            canonical_json_bytes(candidates)
        ):
            raise StructuredPocBlocked("train demonstration candidate hash mismatch")
        policy_views = row.get("policy_views")
        if not isinstance(policy_views, list) or len(policy_views) != len(candidates):
            raise StructuredPocBlocked("train demonstration policy views mismatch")
        for candidate, entry_value in zip(candidates, policy_views, strict=True):
            entry = _mapping(entry_value, "train policy view")
            expected_view = project_policy_view(snapshot["state"], candidate)
            if entry.get("action_id") != candidate["action_id"]:
                raise StructuredPocBlocked("train policy-view action mismatch")
            if entry.get("policy_view") != expected_view:
                raise StructuredPocBlocked("train policy-view payload mismatch")
            if entry.get("sha256") != sha256_bytes(canonical_json_bytes(expected_view)):
                raise StructuredPocBlocked("train policy-view hash mismatch")
        if [candidate["action_id"] for candidate in candidates].count(
            teacher["action_id"]
        ) != 1:
            raise StructuredPocBlocked("train target does not map exactly once")
        categories.add(str(row["category"]))
        rows_by_seed[seed].append(row)

    if ordering != sorted(ordering):
        raise StructuredPocBlocked("train demonstration rows are not ordered")
    if categories != set(TARGET_CATEGORIES):
        raise StructuredPocBlocked("train demonstration categories are incomplete")
    for seed, seed_rows in rows_by_seed.items():
        if [row["decision_index"] for row in seed_rows] != list(range(len(seed_rows))):
            raise StructuredPocBlocked(
                f"train demonstration indices are not contiguous for seed {seed}"
            )

    for expected_seed, episode_value in zip(expected_seed_list, episodes, strict=True):
        episode = _mapping(episode_value, "train demonstration episode")
        seed_rows = rows_by_seed[expected_seed]
        if episode.get("seed") != expected_seed:
            raise StructuredPocBlocked("train demonstration episode seed mismatch")
        if episode.get("decisions") != len(seed_rows):
            raise StructuredPocBlocked("train demonstration episode row count mismatch")
        expected_row_hashes = [
            sha256_bytes(canonical_json_bytes(row)) for row in seed_rows
        ]
        if episode.get("row_sha256s") != expected_row_hashes:
            raise StructuredPocBlocked("train demonstration episode row hashes mismatch")
        if episode.get("selected_action_ids") != [
            row["teacher"]["action_id"] for row in seed_rows
        ]:
            raise StructuredPocBlocked("train demonstration action sequence mismatch")
    return dataset


def build_train_input(
    *,
    demonstrations_artifact: Mapping[str, Any],
    archive_manifest: Mapping[str, Any],
    expected_seeds: Sequence[int],
) -> dict[str, Any]:
    """Select only the registered train cohort from a preserved artifact."""
    demonstrations = _mapping(demonstrations_artifact, "demonstrations artifact")
    if demonstrations.get("schema_version") != DEMONSTRATION_ARTIFACT_SCHEMA_VERSION:
        raise StructuredPocBlocked("demonstrations artifact schema mismatch")
    archive = _mapping(archive_manifest, "archive manifest")
    if archive.get("schema_version") != ARCHIVE_MANIFEST_SCHEMA_VERSION:
        raise StructuredPocBlocked("archive manifest schema mismatch")
    if demonstrations.get("registration_sha256") != archive.get("registration_sha256"):
        raise StructuredPocBlocked("source registration identity mismatch")
    if not _is_sha256(archive.get("raw_sha256")):
        raise StructuredPocBlocked("archive raw SHA-256 is invalid")
    datasets = _mapping(demonstrations.get("datasets"), "demonstrations datasets")
    if set(datasets) != {"final_test", "train", "validation"}:
        raise StructuredPocBlocked("demonstrations dataset inventory mismatch")
    train = validate_train_dataset(datasets["train"], expected_seeds=expected_seeds)
    train_sha256 = sha256_bytes(canonical_json_bytes(train))
    return {
        "dataset": copy.deepcopy(train),
        "schema_version": TRAIN_INPUT_SCHEMA_VERSION,
        "source": {
            "archive_raw_sha256": archive["raw_sha256"],
            "registration_sha256": archive["registration_sha256"],
            "train_dataset_sha256": train_sha256,
        },
    }


def validate_train_input(
    value: object, *, expected_seeds: Sequence[int]
) -> dict[str, Any]:
    train_input = _mapping(value, "train input")
    _require_keys(train_input, {"dataset", "schema_version", "source"}, "train input")
    _require_exact(train_input, "schema_version", TRAIN_INPUT_SCHEMA_VERSION, "train input")
    source = _mapping(train_input["source"], "train input source")
    _require_keys(
        source,
        {"archive_raw_sha256", "registration_sha256", "train_dataset_sha256"},
        "train input source",
    )
    if any(not _is_sha256(source[name]) for name in source):
        raise StructuredPocBlocked("train input source SHA-256 is invalid")
    dataset = validate_train_dataset(
        train_input["dataset"], expected_seeds=expected_seeds
    )
    if source["train_dataset_sha256"] != sha256_bytes(canonical_json_bytes(dataset)):
        raise StructuredPocBlocked("train input dataset hash mismatch")
    train_input["source"] = source
    train_input["dataset"] = dataset
    return train_input


def write_train_input_archive(
    train_input: Mapping[str, Any],
    *,
    output_path: Path | str,
    manifest_path: Path | str,
    expected_seeds: Sequence[int],
) -> dict[str, Any]:
    value = validate_train_input(train_input, expected_seeds=expected_seeds)
    raw = canonical_json_bytes(value)
    destination = Path(output_path)
    manifest_destination = Path(manifest_path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    manifest_destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(f".{destination.name}.tmp")
    try:
        with temporary.open("wb") as raw_handle:
            with gzip.GzipFile(
                filename="",
                mode="wb",
                compresslevel=9,
                fileobj=raw_handle,
                mtime=0,
            ) as compressed:
                compressed.write(raw)
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    manifest = {
        "gzip_sha256": sha256_file(destination),
        "gzip_size_bytes": destination.stat().st_size,
        "raw_sha256": sha256_bytes(raw),
        "raw_size_bytes": len(raw),
        "schema_version": TRAIN_INPUT_MANIFEST_SCHEMA_VERSION,
        "train_dataset_sha256": value["source"]["train_dataset_sha256"],
    }
    manifest_destination.write_bytes(canonical_json_bytes(manifest))
    loaded = load_train_input_archive(
        destination,
        manifest_path=manifest_destination,
        expected_seeds=expected_seeds,
    )
    if canonical_json_bytes(loaded) != raw:
        raise StructuredPocBlocked("published train input did not round trip")
    return manifest


def load_train_input_archive(
    path: Path | str,
    *,
    manifest_path: Path | str,
    expected_seeds: Sequence[int],
) -> dict[str, Any]:
    archive_path = Path(path)
    manifest = _load_json(manifest_path, "train input manifest")
    _require_keys(
        manifest,
        {
            "gzip_sha256",
            "gzip_size_bytes",
            "raw_sha256",
            "raw_size_bytes",
            "schema_version",
            "train_dataset_sha256",
        },
        "train input manifest",
    )
    _require_exact(
        manifest,
        "schema_version",
        TRAIN_INPUT_MANIFEST_SCHEMA_VERSION,
        "train input manifest",
    )
    if manifest["gzip_sha256"] != sha256_file(archive_path):
        raise StructuredPocBlocked("train input gzip hash mismatch")
    if manifest["gzip_size_bytes"] != archive_path.stat().st_size:
        raise StructuredPocBlocked("train input gzip size mismatch")
    try:
        with gzip.open(archive_path, "rb") as handle:
            raw = handle.read()
    except OSError as exc:
        raise StructuredPocBlocked(f"cannot decompress train input: {exc}") from exc
    if len(raw) != manifest["raw_size_bytes"] or sha256_bytes(raw) != manifest["raw_sha256"]:
        raise StructuredPocBlocked("train input raw identity mismatch")
    try:
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_pairs)
    except StructuredPocBlocked:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise StructuredPocBlocked(f"train input JSON is invalid: {exc}") from exc
    result = validate_train_input(value, expected_seeds=expected_seeds)
    if result["source"]["train_dataset_sha256"] != manifest["train_dataset_sha256"]:
        raise StructuredPocBlocked("train input manifest dataset hash mismatch")
    return result


def _slug(value: object) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")
    return text or "empty"


def _add_feature(features: dict[str, float], name: str, value: Real = 1.0) -> None:
    numeric = _finite_number(value, f"feature {name}")
    features[name] = features.get(name, 0.0) + numeric


def _add_token(features: dict[str, float], namespace: str, value: object) -> None:
    _add_feature(features, f"{namespace}={_slug(value)}")


def _numeric(value: object, default: float = 0.0) -> float:
    if value is None:
        return default
    return _finite_number(value, "numeric state value")


def _collection(value: object, label: str) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise StructuredPocBlocked(f"{label} must be an array")
    return [_mapping(item, f"{label} item") for item in value]


def _identity_counts(
    values: Sequence[Mapping[str, Any]], *, identity_fields: Sequence[str]
) -> Counter[str]:
    counts: Counter[str] = Counter()
    for item in values:
        identity = next(
            (item.get(field) for field in identity_fields if item.get(field)), "unknown"
        )
        counts[_slug(identity)] += 1
    return counts


def _add_counter(
    features: dict[str, float], namespace: str, values: Counter[str]
) -> None:
    for identity in sorted(values):
        _add_feature(features, f"{namespace}.{identity}.count", values[identity])


def _add_nested_summary(
    features: dict[str, float], namespace: str, value: object
) -> None:
    if isinstance(value, Mapping):
        for key in sorted(value, key=str):
            _add_nested_summary(features, f"{namespace}.{_slug(key)}", value[key])
        return
    if isinstance(value, list):
        canonical_items = sorted(
            (canonical_json_bytes(item).decode("utf-8") for item in value)
        )
        counts = Counter(canonical_items)
        _add_feature(features, f"{namespace}.length", len(value))
        for item, count in sorted(counts.items()):
            digest = hashlib.sha256(item.encode("utf-8")).hexdigest()[:16]
            _add_feature(features, f"{namespace}.item.{digest}.count", count)
        return
    if isinstance(value, bool) or value is None or isinstance(value, str):
        _add_token(features, namespace, value)
        return
    if isinstance(value, Real):
        _add_feature(features, namespace, value)
        return
    raise StructuredPocBlocked(
        f"unsupported structured context type: {type(value).__name__}"
    )


def _global_features(state: Mapping[str, Any], category: str) -> dict[str, float]:
    features: dict[str, float] = {}
    _add_token(features, "category", category)
    for field in ("act", "ascension", "cur_hp", "floor", "gold", "max_hp"):
        _add_feature(features, f"state.{field}", _numeric(state.get(field)))
    max_hp = max(_numeric(state.get("max_hp"), 1.0), 1.0)
    hp_ratio = _numeric(state.get("cur_hp")) / max_hp
    _add_feature(features, "state.hp_ratio", hp_ratio)
    _add_feature(features, "state.missing_hp_ratio", 1.0 - hp_ratio)
    _add_feature(features, "state.gold_log", math.log1p(max(_numeric(state.get("gold")), 0.0)))
    for field in ("blue_key", "green_key", "red_key"):
        _add_token(features, f"state.{field}", bool(state.get(field)))
    for field in ("boss", "cur_room", "encounter", "screen_state"):
        _add_token(features, f"state.{field}", state.get(field))

    current_node = _mapping(state.get("cur_map_node"), "state.cur_map_node")
    _add_feature(features, "state.cur_map_node.x", _numeric(current_node.get("x")))
    _add_feature(features, "state.cur_map_node.y", _numeric(current_node.get("y")))

    deck = _collection(state.get("deck"), "state.deck")
    deck_counts = _identity_counts(deck, identity_fields=("id", "name"))
    _add_feature(features, "deck.size", len(deck))
    _add_counter(features, "deck.card", deck_counts)
    _add_feature(
        features,
        "deck.upgraded_count",
        sum(bool(card.get("upgraded")) for card in deck),
    )
    _add_feature(
        features,
        "deck.total_upgrade_count",
        sum(_numeric(card.get("upgrade_count")) for card in deck),
    )

    relics = _collection(state.get("relics"), "state.relics")
    relic_counts = _identity_counts(relics, identity_fields=("id", "name"))
    _add_feature(features, "relics.count", len(relics))
    _add_counter(features, "relic", relic_counts)
    for relic in relics:
        identity = _slug(relic.get("id") or relic.get("name") or "unknown")
        _add_feature(features, f"relic.{identity}.data", _numeric(relic.get("data")))

    potions = _collection(state.get("potions"), "state.potions")
    potion_counts = _identity_counts(potions, identity_fields=("id", "name"))
    nonempty_potions = sum(
        count for identity, count in potion_counts.items() if identity not in {"empty", "invalid"}
    )
    _add_feature(features, "potions.capacity", len(potions))
    _add_feature(features, "potions.nonempty_count", nonempty_potions)
    _add_counter(features, "potion", potion_counts)

    map_value = state.get("map")
    if map_value is None:
        _add_token(features, "map.present", False)
    else:
        map_data = _mapping(map_value, "state.map")
        nodes = _collection(map_data.get("nodes"), "state.map.nodes")
        room_counts = Counter(_slug(node.get("room")) for node in nodes)
        _add_token(features, "map.present", True)
        _add_feature(features, "map.node_count", len(nodes))
        _add_counter(features, "map.room", room_counts)
        burning = _mapping(map_data.get("burning_elite"), "state.map.burning_elite")
        _add_feature(features, "map.burning_elite.x", _numeric(burning.get("x")))
        _add_feature(features, "map.burning_elite.y", _numeric(burning.get("y")))
        _add_feature(features, "map.burning_elite.buff", _numeric(burning.get("buff")))
    return features


def _map_graph(
    state: Mapping[str, Any],
) -> tuple[dict[tuple[int, int], dict[str, Any]], dict[str, Any]]:
    map_data = _mapping(state.get("map"), "state.map")
    nodes: dict[tuple[int, int], dict[str, Any]] = {}
    for node in _collection(map_data.get("nodes"), "state.map.nodes"):
        x = node.get("x")
        y = node.get("y")
        if (
            isinstance(x, bool)
            or not isinstance(x, int)
            or isinstance(y, bool)
            or not isinstance(y, int)
        ):
            raise StructuredPocBlocked("map node coordinates must be integers")
        key = (x, y)
        if key in nodes:
            raise StructuredPocBlocked("map node coordinates must be unique")
        edges = []
        for edge in _collection(node.get("edges"), "map node edges"):
            edge_x = edge.get("x")
            edge_y = edge.get("y")
            if (
                isinstance(edge_x, bool)
                or not isinstance(edge_x, int)
                or isinstance(edge_y, bool)
                or not isinstance(edge_y, int)
                or edge_y <= y
            ):
                raise StructuredPocBlocked("map edge must advance to integer coordinates")
            edges.append((edge_x, edge_y))
        normalized = copy.deepcopy(node)
        normalized["_edges"] = tuple(sorted(set(edges)))
        nodes[key] = normalized
    return nodes, map_data


def _reachable_layers(
    nodes: Mapping[tuple[int, int], Mapping[str, Any]], start: tuple[int, int]
) -> list[set[tuple[int, int]]]:
    layers = [{start}]
    for _ in range(3):
        next_layer: set[tuple[int, int]] = set()
        for key in layers[-1]:
            if key[1] >= 15:
                continue
            node = nodes.get(key)
            if node is None:
                raise StructuredPocBlocked(f"route node is missing from map: {key}")
            next_layer.update(node["_edges"])
        layers.append(next_layer)
    return layers


def _suffix_path_summary(
    nodes: Mapping[tuple[int, int], Mapping[str, Any]], start: tuple[int, int]
) -> dict[str, Any]:
    room_names = sorted({_slug(node.get("room")) for node in nodes.values()} | {"boss"})
    memo: dict[tuple[int, int], dict[str, Any]] = {}

    def visit(key: tuple[int, int]) -> dict[str, Any]:
        if key in memo:
            return memo[key]
        if key[1] >= 15:
            result = {
                "max": {room: (1 if room == "boss" else 0) for room in room_names},
                "min": {room: (1 if room == "boss" else 0) for room in room_names},
                "path_count": 1,
                "sum": {room: (1 if room == "boss" else 0) for room in room_names},
            }
            memo[key] = result
            return result
        node = nodes.get(key)
        if node is None:
            raise StructuredPocBlocked(f"route node is missing from map: {key}")
        room = _slug(node.get("room"))
        children = [visit(child) for child in node["_edges"]]
        if not children:
            path_count = 1
            result = {
                "max": {name: (1 if name == room else 0) for name in room_names},
                "min": {name: (1 if name == room else 0) for name in room_names},
                "path_count": path_count,
                "sum": {name: (1 if name == room else 0) for name in room_names},
            }
        else:
            path_count = sum(child["path_count"] for child in children)
            result = {
                "max": {
                    name: (1 if name == room else 0)
                    + max(child["max"][name] for child in children)
                    for name in room_names
                },
                "min": {
                    name: (1 if name == room else 0)
                    + min(child["min"][name] for child in children)
                    for name in room_names
                },
                "path_count": path_count,
                "sum": {
                    name: (1 if name == room else 0) * path_count
                    + sum(child["sum"][name] for child in children)
                    for name in room_names
                },
            }
        memo[key] = result
        return result

    return visit(start)


def _add_route_features(
    features: dict[str, float], state: Mapping[str, Any], candidate: Mapping[str, Any]
) -> None:
    raw = _mapping(candidate.get("raw"), "route candidate.raw")
    x = raw.get("x")
    y = raw.get("y")
    if (
        isinstance(x, bool)
        or not isinstance(x, int)
        or isinstance(y, bool)
        or not isinstance(y, int)
    ):
        raise StructuredPocBlocked("route candidate coordinates must be integers")
    current = _mapping(state.get("cur_map_node"), "state.cur_map_node")
    _add_token(features, "route.room", raw.get("room"))
    _add_feature(features, "route.x", x)
    _add_feature(features, "route.y", y)
    _add_feature(features, "route.delta_x", x - _numeric(current.get("x")))
    _add_feature(features, "route.delta_y", y - _numeric(current.get("y")))
    nodes, map_data = _map_graph(state)
    start = (x, y)
    layers = _reachable_layers(nodes, start)
    for depth, layer in enumerate(layers):
        _add_feature(features, f"route.depth.{depth}.node_count", len(layer))
        counts = Counter(
            "boss" if key[1] >= 15 else _slug(nodes[key].get("room"))
            for key in layer
        )
        _add_counter(features, f"route.depth.{depth}.room", counts)
    suffix = _suffix_path_summary(nodes, start)
    _add_feature(features, "route.suffix.path_count", suffix["path_count"])
    for room in sorted(suffix["sum"]):
        expected = suffix["sum"][room] / suffix["path_count"]
        _add_feature(features, f"route.suffix.{room}.expected", expected)
        _add_feature(features, f"route.suffix.{room}.min", suffix["min"][room])
        _add_feature(features, f"route.suffix.{room}.max", suffix["max"][room])
    hp_ratio = _numeric(state.get("cur_hp")) / max(_numeric(state.get("max_hp"), 1.0), 1.0)
    expected_risk = sum(
        suffix["sum"].get(room, 0) / suffix["path_count"]
        for room in ("elite", "monster")
    )
    expected_shop = suffix["sum"].get("shop", 0) / suffix["path_count"]
    _add_feature(features, "route.interaction.risk_missing_hp", expected_risk * (1.0 - hp_ratio))
    _add_feature(
        features,
        "route.interaction.shop_gold",
        expected_shop * math.log1p(max(_numeric(state.get("gold")), 0.0)),
    )
    burning = _mapping(map_data.get("burning_elite"), "state.map.burning_elite")
    _add_token(
        features,
        "route.selected_burning_elite",
        burning.get("x") == x and burning.get("y") == y,
    )


def _add_card_reward_features(
    features: dict[str, float], state: Mapping[str, Any], candidate: Mapping[str, Any]
) -> None:
    kind = str(candidate.get("kind"))
    raw = _mapping(candidate.get("raw"), "card-reward candidate.raw")
    _add_token(features, "card_reward.kind", kind)
    deck = _collection(state.get("deck"), "state.deck")
    deck_counts = _identity_counts(deck, identity_fields=("id", "name"))
    if kind == "take":
        identity = _slug(raw.get("id") or raw.get("name") or candidate.get("label"))
        _add_token(features, "card_reward.card", identity)
        _add_token(features, "card_reward.upgraded", bool(raw.get("upgraded")))
        _add_feature(features, "card_reward.upgrade_count", _numeric(raw.get("upgrade_count")))
        _add_feature(features, "card_reward.misc", _numeric(raw.get("misc")))
        _add_feature(features, "card_reward.deck_duplicate_count", deck_counts[identity])
        _add_token(features, "card_reward.deck_contains", deck_counts[identity] > 0)
    context = _mapping(state.get("decision_context"), "state.decision_context")
    offered = _collection(context.get("cards", []), "card reward offered cards")
    offer_counts = _identity_counts(offered, identity_fields=("id", "name"))
    _add_feature(features, "card_reward.offer_count", len(offered))
    _add_counter(features, "card_reward.offered", offer_counts)
    _add_token(
        features,
        "card_reward.has_singing_bowl",
        bool(context.get("has_singing_bowl")),
    )


def _add_shop_features(
    features: dict[str, float], state: Mapping[str, Any], candidate: Mapping[str, Any]
) -> None:
    kind = str(candidate.get("kind"))
    raw = _mapping(candidate.get("raw"), "shop candidate.raw")
    _add_token(features, "shop.kind", kind)
    identity = _slug(raw.get("id") or raw.get("name") or candidate.get("label"))
    _add_token(features, f"shop.{_slug(kind)}.item", identity)
    price = _numeric(raw.get("price"))
    gold = _numeric(state.get("gold"))
    _add_feature(features, "shop.price", price)
    _add_feature(features, "shop.price_to_gold", price / max(gold, 1.0))
    _add_feature(features, "shop.post_purchase_gold", gold - price)
    _add_token(features, "shop.affordable", gold >= price)
    deck = _collection(state.get("deck"), "state.deck")
    deck_counts = _identity_counts(deck, identity_fields=("id", "name"))
    relic_counts = _identity_counts(
        _collection(state.get("relics"), "state.relics"),
        identity_fields=("id", "name"),
    )
    potion_counts = _identity_counts(
        _collection(state.get("potions"), "state.potions"),
        identity_fields=("id", "name"),
    )
    _add_feature(features, "shop.deck_item_count", deck_counts[identity])
    _add_feature(features, "shop.owned_relic_count", relic_counts[identity])
    _add_feature(features, "shop.owned_potion_count", potion_counts[identity])
    _add_token(features, "shop.item_upgraded", bool(raw.get("upgraded")))
    _add_feature(features, "shop.item_upgrade_count", _numeric(raw.get("upgrade_count")))
    context = _mapping(state.get("decision_context"), "state.decision_context")
    _add_feature(features, "shop.remove_cost", _numeric(context.get("remove_cost")))
    _add_feature(features, "shop.deck_size", len(deck))


def _add_event_features(
    features: dict[str, float], state: Mapping[str, Any], candidate: Mapping[str, Any]
) -> None:
    raw = _mapping(candidate.get("raw"), "event candidate.raw")
    context = _mapping(state.get("decision_context"), "state.decision_context")
    event_id = raw.get("event_id") or context.get("event_id") or context.get("event_name")
    _add_token(features, "event.id", event_id)
    _add_feature(features, "event.option_index", _numeric(raw.get("idx1")))
    _add_nested_summary(features, "event.data", context.get("event_data"))


def structured_feature_map(
    state: Mapping[str, Any], candidate: Mapping[str, Any], *, category: str
) -> dict[str, float]:
    """Build one semantic, collection-order-invariant state/candidate feature map."""
    if category not in TARGET_CATEGORIES:
        raise StructuredPocBlocked(f"unsupported structured category: {category}")
    state_value = _mapping(state, "state")
    candidate_value = _mapping(candidate, "candidate")
    if candidate_value.get("category") != category or candidate_value.get("available") is not True:
        raise StructuredPocBlocked("structured candidate category or availability mismatch")
    features = _global_features(state_value, category)
    _add_token(features, "candidate.kind", candidate_value.get("kind"))
    if category == "route":
        _add_route_features(features, state_value, candidate_value)
    elif category == "card_reward":
        _add_card_reward_features(features, state_value, candidate_value)
    elif category == "shop":
        _add_shop_features(features, state_value, candidate_value)
    else:
        _add_event_features(features, state_value, candidate_value)
    if not features or any(not math.isfinite(value) for value in features.values()):
        raise StructuredPocBlocked("structured feature map must be finite and nonempty")
    return dict(sorted(features.items()))


def _signed_hash(name: str, hash_dim: int) -> tuple[int, float]:
    digest = hashlib.sha256(name.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") % hash_dim, (-1.0 if digest[8] & 1 else 1.0)


def _normalize_feature_value(value: float) -> float:
    return math.copysign(min(math.log1p(abs(value)), 10.0) / 10.0, value)


def vectorize_structured_features(
    features: Mapping[str, Real], *, hash_dim: int
) -> Any:
    torch = _torch_module()
    dimension = _positive_int(hash_dim, "structured hash_dim")
    vector = torch.zeros(dimension, dtype=torch.float32, device="cpu")
    for name in sorted(features):
        value = _finite_number(features[name], f"feature {name}")
        index, sign = _signed_hash(name, dimension)
        vector[index] += sign * _normalize_feature_value(value)
    if not torch.isfinite(vector).all().item():
        raise StructuredPocBlocked("structured feature vector is not finite")
    return vector


def structured_candidate_features(
    state: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    *,
    category: str,
    hash_dim: int,
) -> tuple[Any, tuple[tuple[str, ...], ...]]:
    torch = _torch_module()
    try:
        normalized_candidates = validate_candidates(list(candidates), category=category)
    except SimulatorAdapterError as exc:
        raise StructuredPocBlocked(f"invalid structured candidate set: {exc}") from exc
    maps = [
        structured_feature_map(state, candidate, category=category)
        for candidate in normalized_candidates
    ]
    vectors = [vectorize_structured_features(value, hash_dim=hash_dim) for value in maps]
    return torch.stack(vectors), tuple(tuple(value) for value in maps)


def feature_collision_diagnostics(
    feature_key_sets: Sequence[Sequence[str]], *, hash_dim: int
) -> dict[str, Any]:
    unique_keys = sorted({key for keys in feature_key_sets for key in keys})
    bins: dict[int, list[str]] = defaultdict(list)
    for key in unique_keys:
        index, _ = _signed_hash(key, hash_dim)
        bins[index].append(key)
    occupied = len(bins)
    collided_bins = sum(len(keys) > 1 for keys in bins.values())
    collisions = len(unique_keys) - occupied
    return {
        "collided_bin_count": collided_bins,
        "collision_count": collisions,
        "collision_fraction": collisions / len(unique_keys) if unique_keys else 0.0,
        "hash_dim": hash_dim,
        "occupied_bin_count": occupied,
        "unique_feature_count": len(unique_keys),
    }


def _torch_module():
    try:
        import torch
    except ImportError as exc:
        raise StructuredPocBlocked("PyTorch is required for the structured POC") from exc
    return torch


def build_structured_model(*, hash_dim: int, hidden_dim: int, model_seed: int) -> Any:
    torch = _torch_module()
    hash_dim = _positive_int(hash_dim, "structured model hash_dim")
    hidden_dim = _positive_int(hidden_dim, "structured model hidden_dim")
    if isinstance(model_seed, bool) or not isinstance(model_seed, int):
        raise StructuredPocBlocked("structured model seed must be an integer")
    torch.manual_seed(model_seed)

    class CategoryRanker(torch.nn.Module):
        def __init__(self) -> None:
            super().__init__()
            self.heads = torch.nn.ModuleDict(
                {
                    category: torch.nn.Sequential(
                        torch.nn.Linear(hash_dim, hidden_dim),
                        torch.nn.ReLU(),
                        torch.nn.Linear(hidden_dim, 1),
                    )
                    for category in TARGET_CATEGORIES
                }
            )

        def forward(self, candidate_features: Any, category: str) -> Any:
            if category not in self.heads:
                raise StructuredPocBlocked(f"unsupported model category: {category}")
            return self.heads[category](candidate_features).squeeze(-1)

    return CategoryRanker().cpu()


def _build_candidate_model(candidate: Mapping[str, Any], *, model_seed: int) -> Any:
    if candidate["id"] == LEGACY_CANDIDATE_ID:
        return build_warm_start_model(
            hash_dim=candidate["hash_dim"],
            hidden_dim=candidate["hidden_dim"],
            model_seed=model_seed,
        )
    if candidate["id"] == STRUCTURED_CANDIDATE_ID:
        return build_structured_model(
            hash_dim=candidate["hash_dim"],
            hidden_dim=candidate["hidden_dim"],
            model_seed=model_seed,
        )
    raise StructuredPocBlocked(f"unsupported model candidate: {candidate.get('id')}")


def _score_model(model: Any, features: Any, *, candidate_id: str, category: str) -> Any:
    if candidate_id == STRUCTURED_CANDIDATE_ID:
        return model(features, category)
    if candidate_id == LEGACY_CANDIDATE_ID:
        return model(features)
    raise StructuredPocBlocked(f"unsupported model candidate: {candidate_id}")


def _ensure_finite_tensor(value: Any, label: str) -> None:
    torch = _torch_module()
    if not torch.isfinite(value).all().item():
        raise StructuredPocBlocked(f"non-finite {label}")


def _ensure_finite_model(model: Any) -> None:
    for name, parameter in model.named_parameters():
        _ensure_finite_tensor(parameter, f"model parameter {name}")


def canonical_model_payload(
    model: Any, *, candidate: Mapping[str, Any]
) -> dict[str, Any]:
    tensors = {}
    for name, tensor in sorted(model.state_dict().items()):
        value = tensor.detach().cpu().contiguous().reshape(-1)
        tensors[name] = {
            "dtype": "float32",
            "shape": list(tensor.shape),
            "values": [float(item).hex() for item in value.tolist()],
        }
    return {
        "architecture": candidate["architecture"],
        "candidate_id": candidate["id"],
        "feature_version": candidate["feature_version"],
        "hash_dim": candidate["hash_dim"],
        "hidden_dim": candidate["hidden_dim"],
        "schema_version": MODEL_SCHEMA_VERSION,
        "tensors": tensors,
    }


def load_model_payload(
    value: object, *, candidate: Mapping[str, Any], model_seed: int
) -> Any:
    payload = _mapping(value, "model payload")
    _require_keys(
        payload,
        {
            "architecture",
            "candidate_id",
            "feature_version",
            "hash_dim",
            "hidden_dim",
            "schema_version",
            "tensors",
        },
        "model payload",
    )
    expected = {
        "architecture": candidate["architecture"],
        "candidate_id": candidate["id"],
        "feature_version": candidate["feature_version"],
        "hash_dim": candidate["hash_dim"],
        "hidden_dim": candidate["hidden_dim"],
        "schema_version": MODEL_SCHEMA_VERSION,
    }
    for field, expected_value in expected.items():
        _require_exact(payload, field, expected_value, "model payload")
    torch = _torch_module()
    model = _build_candidate_model(candidate, model_seed=model_seed)
    expected_state = model.state_dict()
    tensor_payloads = _mapping(payload["tensors"], "model tensors")
    if set(tensor_payloads) != set(expected_state):
        raise StructuredPocBlocked("model tensor inventory mismatch")
    tensors = {}
    for name, expected_tensor in expected_state.items():
        tensor_payload = _mapping(tensor_payloads[name], f"model tensor {name}")
        _require_keys(tensor_payload, {"dtype", "shape", "values"}, f"model tensor {name}")
        _require_exact(tensor_payload, "dtype", "float32", f"model tensor {name}")
        shape = tensor_payload["shape"]
        if shape != list(expected_tensor.shape):
            raise StructuredPocBlocked(f"model tensor shape mismatch: {name}")
        raw_values = tensor_payload["values"]
        expected_count = math.prod(shape)
        if not isinstance(raw_values, list) or len(raw_values) != expected_count:
            raise StructuredPocBlocked(f"model tensor value count mismatch: {name}")
        parsed = []
        for raw_value in raw_values:
            if not isinstance(raw_value, str):
                raise StructuredPocBlocked(f"model tensor value is invalid: {name}")
            try:
                parsed_value = float.fromhex(raw_value)
            except ValueError as exc:
                raise StructuredPocBlocked(
                    f"model tensor value is invalid: {name}"
                ) from exc
            if not math.isfinite(parsed_value):
                raise StructuredPocBlocked(f"model tensor value is non-finite: {name}")
            parsed.append(parsed_value)
        tensors[name] = torch.tensor(parsed, dtype=torch.float32).reshape(shape)
    model.load_state_dict(tensors, strict=True)
    model.requires_grad_(False)
    model.eval()
    _ensure_finite_model(model)
    if canonical_model_payload(model, candidate=candidate) != payload:
        raise StructuredPocBlocked("model payload canonical round trip mismatch")
    return model


@dataclass(frozen=True)
class PreparedRow:
    seed: int
    decision_index: int
    category: str
    candidate_action_ids: tuple[str, ...]
    target_action_id: str
    target_index: int
    features: Any
    feature_keys: tuple[tuple[str, ...], ...]


def prepare_rows(
    dataset: Mapping[str, Any], *, candidate: Mapping[str, Any]
) -> tuple[PreparedRow, ...]:
    rows: list[PreparedRow] = []
    for row_value in dataset["rows"]:
        row = _mapping(row_value, "demonstration row")
        candidates = row["candidate_actions"]
        if len(candidates) < 2:
            continue
        snapshot = row["source_snapshot"]
        category = row["category"]
        if candidate["id"] == LEGACY_CANDIDATE_ID:
            try:
                features = legacy_candidate_features(
                    snapshot["state"], candidates, hash_dim=candidate["hash_dim"]
                )
            except (TypeError, ValueError) as exc:
                raise StructuredPocBlocked(f"legacy feature projection failed: {exc}") from exc
            feature_keys: tuple[tuple[str, ...], ...] = tuple(() for _ in candidates)
        elif candidate["id"] == STRUCTURED_CANDIDATE_ID:
            features, feature_keys = structured_candidate_features(
                snapshot["state"],
                candidates,
                category=category,
                hash_dim=candidate["hash_dim"],
            )
        else:
            raise StructuredPocBlocked("unregistered candidate reached feature preparation")
        _ensure_finite_tensor(features, "prepared candidate features")
        action_ids = tuple(str(item["action_id"]) for item in candidates)
        target_action_id = str(row["teacher"]["action_id"])
        rows.append(
            PreparedRow(
                seed=int(row["seed"]),
                decision_index=int(row["decision_index"]),
                category=str(category),
                candidate_action_ids=action_ids,
                target_action_id=target_action_id,
                target_index=action_ids.index(target_action_id),
                features=features,
                feature_keys=feature_keys,
            )
        )
    if not rows:
        raise StructuredPocBlocked("POC has no multi-candidate rows")
    ordering = [(row.seed, row.decision_index) for row in rows]
    if ordering != sorted(ordering):
        raise StructuredPocBlocked("prepared rows are not deterministically ordered")
    if {row.category for row in rows} != set(TARGET_CATEGORIES):
        raise StructuredPocBlocked("prepared rows do not cover all target categories")
    return tuple(rows)


def build_seed_folds(
    seeds: Sequence[int], *, fold_count: int
) -> tuple[dict[str, Any], ...]:
    normalized = _seed_array(seeds, "fold seeds")
    count = _positive_int(fold_count, "fold count")
    if count > len(normalized):
        raise StructuredPocBlocked("fold count exceeds seed count")
    folds = []
    all_seeds = set(normalized)
    for index in range(count):
        heldout = normalized[index::count]
        fit = sorted(all_seeds - set(heldout))
        folds.append({"fit_seeds": fit, "fold": index, "heldout_seeds": heldout})
    heldout_flat = [seed for fold in folds for seed in fold["heldout_seeds"]]
    if sorted(heldout_flat) != normalized or len(heldout_flat) != len(set(heldout_flat)):
        raise StructuredPocBlocked("fold assignment is not exhaustive and exclusive")
    return tuple(folds)


def _group_rows_for_batches(
    rows: Sequence[PreparedRow],
) -> dict[str, dict[int, list[PreparedRow]]]:
    grouped: dict[str, dict[int, list[PreparedRow]]] = {
        category: defaultdict(list) for category in TARGET_CATEGORIES
    }
    for row in rows:
        grouped[row.category][len(row.candidate_action_ids)].append(row)
    if any(not grouped[category] for category in TARGET_CATEGORIES):
        raise StructuredPocBlocked("training rows must cover every category")
    return grouped


def train_candidate_model(
    rows: Sequence[PreparedRow],
    *,
    candidate: Mapping[str, Any],
    optimizer_config: Mapping[str, Any],
) -> tuple[Any, dict[str, Any]]:
    if not rows:
        raise StructuredPocBlocked("candidate training rows must be nonempty")
    torch = _torch_module()
    random.seed(optimizer_config["model_seed"])
    torch.manual_seed(optimizer_config["model_seed"])
    model = _build_candidate_model(
        candidate, model_seed=optimizer_config["model_seed"]
    )
    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=optimizer_config["learning_rate"],
        betas=(optimizer_config["beta1"], optimizer_config["beta2"]),
        eps=optimizer_config["epsilon"],
        weight_decay=optimizer_config["weight_decay"],
    )
    grouped = _group_rows_for_batches(rows)
    category_count = float(len(TARGET_CATEGORIES))
    history = []
    for epoch in range(1, optimizer_config["epochs"] + 1):
        model.train()
        optimizer.zero_grad(set_to_none=True)
        category_losses = {}
        for category in TARGET_CATEGORIES:
            category_rows = [
                row
                for candidate_count in sorted(grouped[category])
                for row in grouped[category][candidate_count]
            ]
            loss_sum = 0.0
            for candidate_count in sorted(grouped[category]):
                batch = grouped[category][candidate_count]
                features = torch.stack([row.features for row in batch])
                targets = torch.tensor(
                    [row.target_index for row in batch], dtype=torch.long, device="cpu"
                )
                logits = _score_model(
                    model,
                    features,
                    candidate_id=candidate["id"],
                    category=category,
                )
                _ensure_finite_tensor(logits, "training logits")
                losses = torch.nn.functional.cross_entropy(
                    logits, targets, reduction="none"
                )
                _ensure_finite_tensor(losses, "training loss")
                (
                    losses.sum()
                    / (category_count * float(len(category_rows)))
                ).backward()
                loss_sum += float(losses.detach().sum().item())
            category_losses[category] = loss_sum / len(category_rows)
        for name, parameter in model.named_parameters():
            if parameter.grad is None:
                raise StructuredPocBlocked(f"missing model gradient: {name}")
            _ensure_finite_tensor(parameter.grad, f"model gradient {name}")
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
    payload = canonical_model_payload(model, candidate=candidate)
    load_model_payload(
        payload, candidate=candidate, model_seed=optimizer_config["model_seed"]
    )
    return model, {
        "final_model_sha256": sha256_bytes(canonical_json_bytes(payload)),
        "history": history,
        "row_count": len(rows),
    }


def evaluate_candidate_model(
    model: Any,
    rows: Sequence[PreparedRow],
    *,
    candidate_id: str,
    fold: int,
) -> list[dict[str, Any]]:
    torch = _torch_module()
    predictions = []
    model.eval()
    with torch.no_grad():
        for row in rows:
            logits = _score_model(
                model,
                row.features,
                candidate_id=candidate_id,
                category=row.category,
            )
            probabilities = torch.softmax(logits, dim=0)
            _ensure_finite_tensor(logits, "evaluation logits")
            _ensure_finite_tensor(probabilities, "evaluation probabilities")
            selected_index = int(torch.argmax(probabilities).item())
            target_probability = float(probabilities[row.target_index].item())
            if not 0.0 < target_probability <= 1.0:
                raise StructuredPocBlocked("teacher probability must be in (0, 1]")
            predictions.append(
                {
                    "candidate_action_ids": list(row.candidate_action_ids),
                    "candidate_count": len(row.candidate_action_ids),
                    "category": row.category,
                    "correct": selected_index == row.target_index,
                    "cross_entropy": -math.log(target_probability),
                    "decision_index": row.decision_index,
                    "fold": fold,
                    "predicted_action_id": row.candidate_action_ids[selected_index],
                    "seed": row.seed,
                    "target_action_id": row.target_action_id,
                    "target_probability": target_probability,
                }
            )
    return predictions


def metrics_from_predictions(predictions: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not predictions:
        raise StructuredPocBlocked("prediction metrics require rows")
    by_category = {}
    for category in TARGET_CATEGORIES:
        rows = [row for row in predictions if row["category"] == category]
        if not rows:
            raise StructuredPocBlocked(f"prediction metrics missing category {category}")
        by_category[category] = {
            "action_agreement": sum(bool(row["correct"]) for row in rows) / len(rows),
            "mean_cross_entropy": sum(float(row["cross_entropy"]) for row in rows)
            / len(rows),
            "row_count": len(rows),
        }
    overall_agreement = sum(bool(row["correct"]) for row in predictions) / len(predictions)
    overall_cross_entropy = sum(float(row["cross_entropy"]) for row in predictions) / len(
        predictions
    )
    result = {
        "by_category": by_category,
        "macro_category_action_agreement": sum(
            entry["action_agreement"] for entry in by_category.values()
        )
        / len(by_category),
        "macro_category_mean_cross_entropy": sum(
            entry["mean_cross_entropy"] for entry in by_category.values()
        )
        / len(by_category),
        "overall_action_agreement": overall_agreement,
        "overall_mean_cross_entropy": overall_cross_entropy,
        "row_count": len(predictions),
    }
    numeric_values = [
        overall_agreement,
        overall_cross_entropy,
        result["macro_category_action_agreement"],
        result["macro_category_mean_cross_entropy"],
        *(entry["action_agreement"] for entry in by_category.values()),
        *(entry["mean_cross_entropy"] for entry in by_category.values()),
    ]
    if any(not math.isfinite(value) for value in numeric_values):
        raise StructuredPocBlocked("prediction metrics are non-finite")
    return result


def singleton_summary(dataset: Mapping[str, Any]) -> dict[str, Any]:
    by_category = {category: 0 for category in TARGET_CATEGORIES}
    total_by_category = {category: 0 for category in TARGET_CATEGORIES}
    for row in dataset["rows"]:
        category = row["category"]
        total_by_category[category] += 1
        if len(row["candidate_actions"]) == 1:
            by_category[category] += 1
    return {
        "by_category": by_category,
        "excluded_from_competence_metrics": True,
        "row_count": sum(by_category.values()),
        "total_by_category": total_by_category,
        "total_row_count": len(dataset["rows"]),
    }


def run_candidate_cross_validation(
    rows: Sequence[PreparedRow],
    *,
    candidate: Mapping[str, Any],
    folds: Sequence[Mapping[str, Any]],
    optimizer_config: Mapping[str, Any],
    deadline: float,
    clock: Callable[[], float],
) -> dict[str, Any]:
    predictions = []
    fold_results = []
    for fold_value in folds:
        if clock() > deadline:
            raise StructuredPocBlocked("POC execution exceeded wall-time bound")
        fold = _mapping(fold_value, "fold")
        fit_seed_set = set(fold["fit_seeds"])
        heldout_seed_set = set(fold["heldout_seeds"])
        if fit_seed_set & heldout_seed_set:
            raise StructuredPocBlocked("fold fit and held-out seeds overlap")
        fit_rows = [row for row in rows if row.seed in fit_seed_set]
        heldout_rows = [row for row in rows if row.seed in heldout_seed_set]
        if len(fit_rows) + len(heldout_rows) != len(rows):
            raise StructuredPocBlocked("fold rows do not cover the train corpus")
        model, training = train_candidate_model(
            fit_rows,
            candidate=candidate,
            optimizer_config=optimizer_config,
        )
        fold_predictions = evaluate_candidate_model(
            model,
            heldout_rows,
            candidate_id=candidate["id"],
            fold=fold["fold"],
        )
        predictions.extend(fold_predictions)
        fold_results.append(
            {
                "fit_row_count": len(fit_rows),
                "fold": fold["fold"],
                "heldout_metrics": metrics_from_predictions(fold_predictions),
                "heldout_row_count": len(heldout_rows),
                "model_sha256": training["final_model_sha256"],
                "training_history": training["history"],
            }
        )
    predictions.sort(key=lambda row: (row["seed"], row["decision_index"]))
    expected_keys = [(row.seed, row.decision_index) for row in rows]
    actual_keys = [(row["seed"], row["decision_index"]) for row in predictions]
    if actual_keys != expected_keys or len(actual_keys) != len(set(actual_keys)):
        raise StructuredPocBlocked("held-out predictions are not one-to-one with rows")
    return {
        "candidate_id": candidate["id"],
        "folds": fold_results,
        "metrics": metrics_from_predictions(predictions),
        "predictions": predictions,
    }


def compare_candidates(
    *,
    control: Mapping[str, Any],
    structured: Mapping[str, Any],
    thresholds: Mapping[str, Any],
) -> dict[str, Any]:
    control_metrics = control["metrics"]
    structured_metrics = structured["metrics"]
    deltas = {
        "card_reward_agreement": structured_metrics["by_category"]["card_reward"][
            "action_agreement"
        ]
        - control_metrics["by_category"]["card_reward"]["action_agreement"],
        "macro_agreement": structured_metrics["macro_category_action_agreement"]
        - control_metrics["macro_category_action_agreement"],
        "mean_cross_entropy": structured_metrics["overall_mean_cross_entropy"]
        - control_metrics["overall_mean_cross_entropy"],
        "overall_agreement": structured_metrics["overall_action_agreement"]
        - control_metrics["overall_action_agreement"],
        "route_agreement": structured_metrics["by_category"]["route"]["action_agreement"]
        - control_metrics["by_category"]["route"]["action_agreement"],
    }
    checks = {
        "card_reward_nonregression": deltas["card_reward_agreement"]
        >= thresholds["minimum_card_reward_agreement_delta"],
        "cross_entropy_nonworse": deltas["mean_cross_entropy"]
        <= thresholds["maximum_mean_cross_entropy_delta"],
        "macro_agreement_improvement": deltas["macro_agreement"]
        >= thresholds["minimum_macro_agreement_delta"],
        "overall_agreement_improvement": deltas["overall_agreement"]
        >= thresholds["minimum_overall_agreement_delta"],
        "route_nonregression": deltas["route_agreement"]
        >= thresholds["minimum_route_agreement_delta"],
    }
    return {
        "checks": checks,
        "deltas": deltas,
        "selected_candidate_id": (
            STRUCTURED_CANDIDATE_ID if all(checks.values()) else None
        ),
        "verdict": (
            "structured_candidate_selected"
            if all(checks.values())
            else "poc_valid_without_structured_candidate"
        ),
    }


def execute_poc(
    *,
    registration: Mapping[str, Any],
    train_input: Mapping[str, Any],
    clock: Callable[[], float] = time.monotonic,
) -> dict[str, Any]:
    value = validate_registration(registration)
    train = validate_train_input(
        train_input, expected_seeds=value["poc"]["seeds"]
    )
    dataset = train["dataset"]
    limits = value["poc"]["limits"]
    if len(dataset["rows"]) > limits["max_rows"]:
        raise StructuredPocBlocked("train corpus exceeds registered row bound")
    if any(
        len(row["candidate_actions"]) > limits["max_candidates_per_row"]
        for row in dataset["rows"]
    ):
        raise StructuredPocBlocked("train row exceeds candidate bound")
    start = _finite_number(clock(), "clock")
    deadline = start + limits["max_wall_seconds_per_execution"]
    torch = _torch_module()
    previous_threads = torch.get_num_threads()
    torch.set_num_threads(value["poc"]["optimizer"]["torch_num_threads"])
    try:
        folds = build_seed_folds(
            value["poc"]["seeds"], fold_count=value["poc"]["folds"]["count"]
        )
        control_rows = prepare_rows(
            dataset, candidate=value["poc"]["candidates"]["control"]
        )
        structured_rows = prepare_rows(
            dataset, candidate=value["poc"]["candidates"]["structured"]
        )
        control_keys = [(row.seed, row.decision_index) for row in control_rows]
        structured_keys = [(row.seed, row.decision_index) for row in structured_rows]
        if control_keys != structured_keys:
            raise StructuredPocBlocked("registered candidates received different rows")
        control = run_candidate_cross_validation(
            control_rows,
            candidate=value["poc"]["candidates"]["control"],
            folds=folds,
            optimizer_config=value["poc"]["optimizer"],
            deadline=deadline,
            clock=clock,
        )
        structured = run_candidate_cross_validation(
            structured_rows,
            candidate=value["poc"]["candidates"]["structured"],
            folds=folds,
            optimizer_config=value["poc"]["optimizer"],
            deadline=deadline,
            clock=clock,
        )
        comparison = compare_candidates(
            control=control,
            structured=structured,
            thresholds=value["poc"]["evaluation"]["thresholds"],
        )
        selected_model = None
        selected_model_sha256 = None
        selected_training = None
        fit_count = 8
        if comparison["selected_candidate_id"] == STRUCTURED_CANDIDATE_ID:
            model, selected_training = train_candidate_model(
                structured_rows,
                candidate=value["poc"]["candidates"]["structured"],
                optimizer_config=value["poc"]["optimizer"],
            )
            selected_model = canonical_model_payload(
                model, candidate=value["poc"]["candidates"]["structured"]
            )
            selected_model_sha256 = sha256_bytes(canonical_json_bytes(selected_model))
            fit_count += 1
        if fit_count > limits["max_model_fits_per_execution"]:
            raise StructuredPocBlocked("POC exceeded registered model-fit bound")
        if clock() > deadline:
            raise StructuredPocBlocked("POC execution exceeded wall-time bound")
        feature_keys = [keys for row in structured_rows for keys in row.feature_keys]
        execution = {
            "candidate_results": {
                "control": control,
                "structured": structured,
            },
            "comparison": comparison,
            "feature_collision_diagnostics": feature_collision_diagnostics(
                feature_keys,
                hash_dim=value["poc"]["candidates"]["structured"]["hash_dim"],
            ),
            "fit_count": fit_count,
            "folds": list(folds),
            "schema_version": EXECUTION_SCHEMA_VERSION,
            "selected_model": selected_model,
            "selected_model_sha256": selected_model_sha256,
            "selected_training": selected_training,
            "singleton_summary": singleton_summary(dataset),
            "train_dataset_sha256": train["source"]["train_dataset_sha256"],
        }
        return execution
    finally:
        torch.set_num_threads(previous_threads)


def _validate_source_archive_manifest(value: object) -> dict[str, Any]:
    manifest = _mapping(value, "source archive manifest")
    _require_keys(
        manifest,
        {
            "compression",
            "gzip_path",
            "gzip_sha256",
            "gzip_size_bytes",
            "raw_path",
            "raw_sha256",
            "raw_size_bytes",
            "registration_sha256",
            "schema_version",
        },
        "source archive manifest",
    )
    _require_exact(
        manifest,
        "schema_version",
        ARCHIVE_MANIFEST_SCHEMA_VERSION,
        "source archive manifest",
    )
    compression = _mapping(manifest["compression"], "source compression")
    _require_keys(
        compression, {"format", "level", "mtime", "original_name"}, "source compression"
    )
    for field, expected in {
        "format": "gzip",
        "level": 9,
        "mtime": 0,
        "original_name": "demonstrations.json",
    }.items():
        _require_exact(compression, field, expected, "source compression")
    for field in ("gzip_sha256", "raw_sha256", "registration_sha256"):
        if not _is_sha256(manifest[field]):
            raise StructuredPocBlocked(f"source archive {field} is invalid")
    for field in ("gzip_size_bytes", "raw_size_bytes"):
        manifest[field] = _positive_int(manifest[field], f"source archive {field}")
    for field in ("gzip_path", "raw_path"):
        path = manifest[field]
        if not isinstance(path, str) or not path:
            raise StructuredPocBlocked(f"source archive {field} is required")
    manifest["compression"] = compression
    return manifest


def load_preserved_demonstrations(
    demonstrations_path: Path | str, *, archive_manifest_path: Path | str
) -> tuple[dict[str, Any], dict[str, Any]]:
    path = Path(demonstrations_path)
    archive = _validate_source_archive_manifest(
        _load_json(archive_manifest_path, "source archive manifest")
    )
    if path.suffix.lower() == ".gz":
        if sha256_file(path) != archive["gzip_sha256"]:
            raise StructuredPocBlocked("source gzip hash mismatch")
        if path.stat().st_size != archive["gzip_size_bytes"]:
            raise StructuredPocBlocked("source gzip size mismatch")
        try:
            with gzip.open(path, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            raise StructuredPocBlocked(f"cannot decompress source demonstrations: {exc}") from exc
        if len(raw) != archive["raw_size_bytes"] or sha256_bytes(raw) != archive["raw_sha256"]:
            raise StructuredPocBlocked("source raw identity mismatch after decompression")
        try:
            demonstrations = json.loads(raw, object_pairs_hook=_reject_duplicate_pairs)
        except StructuredPocBlocked:
            raise
        except (UnicodeError, json.JSONDecodeError) as exc:
            raise StructuredPocBlocked(
                f"source demonstrations JSON is invalid: {exc}"
            ) from exc
    else:
        if sha256_file(path) != archive["raw_sha256"]:
            raise StructuredPocBlocked("source raw hash mismatch")
        if path.stat().st_size != archive["raw_size_bytes"]:
            raise StructuredPocBlocked("source raw size mismatch")
        demonstrations = _load_json(path, "source demonstrations")
    return _mapping(demonstrations, "source demonstrations"), archive


def _binding_for_path(repo_root: Path, path: Path | str) -> dict[str, Any]:
    resolved = Path(path).resolve()
    try:
        relative = resolved.relative_to(repo_root.resolve()).as_posix()
    except ValueError as exc:
        raise StructuredPocBlocked(f"bound path escapes repository: {path}") from exc
    if not resolved.is_file():
        raise StructuredPocBlocked(f"bound path is missing: {path}")
    return {
        "path": relative,
        "sha256": sha256_file(resolved),
        "size_bytes": resolved.stat().st_size,
    }


def prepare_train_input_from_sources(
    *,
    demonstrations_path: Path | str,
    archive_manifest_path: Path | str,
    warm_start_manifest_path: Path | str,
    output_path: Path | str,
    output_manifest_path: Path | str,
    expected_seeds: Sequence[int] = REGISTERED_TRAIN_SEEDS,
) -> dict[str, Any]:
    demonstrations, archive = load_preserved_demonstrations(
        demonstrations_path, archive_manifest_path=archive_manifest_path
    )
    warm_start_manifest = _load_json(
        warm_start_manifest_path, "warm-start artifact manifest"
    )
    artifact_hashes = _mapping(
        warm_start_manifest.get("artifact_hashes"),
        "warm-start artifact hashes",
    )
    if artifact_hashes.get("demonstrations.json") != archive["raw_sha256"]:
        raise StructuredPocBlocked("warm-start and archive demonstration hashes differ")
    if warm_start_manifest.get("registration_sha256") != archive["registration_sha256"]:
        raise StructuredPocBlocked("warm-start and archive registration hashes differ")
    train_input = build_train_input(
        demonstrations_artifact=demonstrations,
        archive_manifest=archive,
        expected_seeds=expected_seeds,
    )
    return write_train_input_archive(
        train_input,
        output_path=output_path,
        manifest_path=output_manifest_path,
        expected_seeds=expected_seeds,
    )


def build_registration(
    *,
    repo_root: Path,
    implementation_commit: str,
    source_archive_path: Path | str,
    source_archive_manifest_path: Path | str,
    source_warm_start_manifest_path: Path | str,
    train_input_path: Path | str,
    train_input_manifest_path: Path | str,
) -> dict[str, Any]:
    if not _is_commit(implementation_commit):
        raise StructuredPocBlocked("implementation commit is invalid")
    train_manifest = _load_json(train_input_manifest_path, "train input manifest")
    if train_manifest.get("schema_version") != TRAIN_INPUT_MANIFEST_SCHEMA_VERSION:
        raise StructuredPocBlocked("train input manifest schema mismatch")
    train_input = load_train_input_archive(
        train_input_path,
        manifest_path=train_input_manifest_path,
        expected_seeds=REGISTERED_TRAIN_SEEDS,
    )
    if (
        train_input["source"]["train_dataset_sha256"]
        != train_manifest.get("train_dataset_sha256")
    ):
        raise StructuredPocBlocked("train input registration identity mismatch")
    try:
        source_sha256 = hash_bound_files(repo_root, REGISTERED_SOURCE_FILES)
        _verify_sources_at_commit(repo_root, implementation_commit, REGISTERED_SOURCE_FILES)
    except Exception as exc:
        raise StructuredPocBlocked(f"cannot bind implementation sources: {exc}") from exc
    torch = _torch_module()
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
            "source_archive": _binding_for_path(repo_root, source_archive_path),
            "source_archive_manifest": _binding_for_path(
                repo_root, source_archive_manifest_path
            ),
            "source_warm_start_manifest": _binding_for_path(
                repo_root, source_warm_start_manifest_path
            ),
            "teacher_policy_id": NATIVE_TARGET_POLICY_ID,
            "train_dataset_sha256": train_manifest["train_dataset_sha256"],
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
                    "id": LEGACY_CANDIDATE_ID,
                },
                "structured": {
                    "architecture": "category-specific-mlp-v1",
                    "feature_version": STRUCTURED_FEATURE_VERSION,
                    "hash_dim": 2048,
                    "hidden_dim": 64,
                    "id": STRUCTURED_CANDIDATE_ID,
                },
            },
            "evaluation": {
                "primary_metric": "seed_grouped_heldout_multicandidate_action_agreement",
                "singleton_treatment": "report_only_excluded_from_fit_and_gate",
                "thresholds": {
                    "maximum_mean_cross_entropy_delta": 0.0,
                    "minimum_card_reward_agreement_delta": 0.0,
                    "minimum_macro_agreement_delta": 0.03,
                    "minimum_overall_agreement_delta": 0.03,
                    "minimum_route_agreement_delta": 0.0,
                },
            },
            "folds": {"count": 4, "rule": FOLD_RULE},
            "limits": {
                "max_candidates_per_row": 32,
                "max_model_fits_per_execution": 9,
                "max_rows": 1500,
                "max_wall_seconds_per_execution": 900.0,
            },
            "optimizer": {
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
            },
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
        "source_archive",
        "source_archive_manifest",
        "source_warm_start_manifest",
        "train_input",
        "train_input_manifest",
    ):
        if _actual_binding(repo_root, identity[name]) != identity[name]:
            raise StructuredPocBlocked(f"registered binding mismatch: {name}")
    implementation = identity["implementation"]
    try:
        actual_source_sha256 = hash_bound_files(
            repo_root, implementation["source_files"]
        )
        _verify_sources_at_commit(
            repo_root, implementation["commit"], implementation["source_files"]
        )
    except Exception as exc:
        raise StructuredPocBlocked(f"implementation identity failed: {exc}") from exc
    if actual_source_sha256 != implementation["source_sha256"]:
        raise StructuredPocBlocked("implementation source hash mismatch")
    torch = _torch_module()
    runtime = {
        "python": ".".join(map(str, __import__("sys").version_info[:3])),
        "torch": str(torch.__version__),
    }
    if runtime != identity["runtime"]:
        raise StructuredPocBlocked("registered runtime mismatch")
    source_archive = _validate_source_archive_manifest(
        _load_json(
            repo_root / identity["source_archive_manifest"]["path"],
            "source archive manifest",
        )
    )
    if (
        source_archive["gzip_sha256"] != identity["source_archive"]["sha256"]
        or source_archive["gzip_size_bytes"] != identity["source_archive"]["size_bytes"]
    ):
        raise StructuredPocBlocked("registered source archive identity mismatch")
    warm_manifest = _load_json(
        repo_root / identity["source_warm_start_manifest"]["path"],
        "warm-start manifest",
    )
    if (
        _mapping(warm_manifest.get("artifact_hashes"), "warm-start hashes").get(
            "demonstrations.json"
        )
        != source_archive["raw_sha256"]
    ):
        raise StructuredPocBlocked("registered warm-start source hash mismatch")
    return {
        "implementation_commit": implementation["commit"],
        "implementation_source_sha256": actual_source_sha256,
        "runtime": runtime,
        "source_archive_raw_sha256": source_archive["raw_sha256"],
    }


def finalize_classification(
    primary: Mapping[str, Any], replay: Mapping[str, Any]
) -> dict[str, Any]:
    primary_sha256 = sha256_bytes(canonical_json_bytes(primary))
    replay_sha256 = sha256_bytes(canonical_json_bytes(replay))
    replay_identity = primary_sha256 == replay_sha256
    comparison = _mapping(primary.get("comparison"), "primary comparison")
    checks = dict(_mapping(comparison.get("checks"), "comparison checks"))
    checks["replay_identity"] = replay_identity
    selected = comparison.get("selected_candidate_id")
    if not replay_identity:
        verdict = "blocked"
        selected = None
    elif all(checks.values()) and selected == STRUCTURED_CANDIDATE_ID:
        verdict = "structured_candidate_selected"
    else:
        verdict = "poc_valid_without_structured_candidate"
        selected = None
    return {
        "authority": _authority(),
        "checks": checks,
        "primary_execution_sha256": primary_sha256,
        "replay_execution_sha256": replay_sha256,
        "selected_candidate_id": selected,
        "verdict": verdict,
    }


def build_metrics_artifact(
    *,
    registration_sha256: str,
    primary: Mapping[str, Any],
    replay: Mapping[str, Any],
    classification: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "authority": _authority(),
        "candidate_metrics": {
            name: copy.deepcopy(primary["candidate_results"][name]["metrics"])
            for name in ("control", "structured")
        },
        "classification": copy.deepcopy(dict(classification)),
        "comparison": copy.deepcopy(primary["comparison"]),
        "feature_collision_diagnostics": copy.deepcopy(
            primary["feature_collision_diagnostics"]
        ),
        "fit_count_per_execution": primary["fit_count"],
        "registration_sha256": registration_sha256,
        "schema_version": METRICS_SCHEMA_VERSION,
        "singleton_summary": copy.deepcopy(primary["singleton_summary"]),
        "train_dataset_sha256": primary["train_dataset_sha256"],
    }


def render_report(
    *, registration_sha256: str, metrics: Mapping[str, Any]
) -> str:
    classification = metrics["classification"]
    control = metrics["candidate_metrics"]["control"]
    structured = metrics["candidate_metrics"]["structured"]
    deltas = metrics["comparison"]["deltas"]
    collision = metrics["feature_collision_diagnostics"]
    singleton = metrics["singleton_summary"]
    lines = [
        "# Non-Combat Structured Baseline-Ranker POC",
        "",
        f"- Verdict: `{classification['verdict']}`",
        f"- Selected candidate: `{classification['selected_candidate_id']}`",
        "- Evidence class: `observed-train-only implementation fit`",
        "- Policy-quality claim: `false`",
        f"- Registration SHA-256: `{registration_sha256}`",
        f"- Train dataset SHA-256: `{metrics['train_dataset_sha256']}`",
        "",
        "## Multi-Candidate Held-Out Metrics",
        "",
        "| Metric | Legacy control | Structured | Delta |",
        "| --- | ---: | ---: | ---: |",
        f"| Overall agreement | {control['overall_action_agreement']:.6f} | {structured['overall_action_agreement']:.6f} | {deltas['overall_agreement']:+.6f} |",
        f"| Macro category agreement | {control['macro_category_action_agreement']:.6f} | {structured['macro_category_action_agreement']:.6f} | {deltas['macro_agreement']:+.6f} |",
        f"| Mean cross entropy | {control['overall_mean_cross_entropy']:.6f} | {structured['overall_mean_cross_entropy']:.6f} | {deltas['mean_cross_entropy']:+.6f} |",
        "",
        "## Category Agreement",
        "",
        "| Category | Rows | Legacy | Structured | Delta |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for category in TARGET_CATEGORIES:
        control_value = control["by_category"][category]
        structured_value = structured["by_category"][category]
        delta = structured_value["action_agreement"] - control_value["action_agreement"]
        lines.append(
            f"| {category} | {control_value['row_count']} | {control_value['action_agreement']:.6f} | {structured_value['action_agreement']:.6f} | {delta:+.6f} |"
        )
    lines.extend(
        [
            "",
            "## Selection Checks",
            "",
            *(
                f"- {name}: `{'pass' if passed else 'fail'}`"
                for name, passed in sorted(classification["checks"].items())
            ),
            "",
            "## Data Strata",
            "",
            f"- Multi-candidate rows: {control['row_count']}",
            f"- Singleton rows excluded from fit/gate: {singleton['row_count']}",
            f"- Total train rows: {singleton['total_row_count']}",
            "",
            "## Structured Hash Diagnostics",
            "",
            f"- Hash width: {collision['hash_dim']}",
            f"- Unique feature keys: {collision['unique_feature_count']}",
            f"- Occupied bins: {collision['occupied_bin_count']}",
            f"- Collision fraction: {collision['collision_fraction']:.6f}",
            "",
            "## Boundaries",
            "",
            "- No validation or final-test row contributed to features, fitting, selection, or metrics.",
            "- No native simulator, new seed, rollout, floor, victory, live game, checkpoint, or reward was used.",
            "- SimpleAgent remains auxiliary supervision; all legal candidates remain available.",
            "- A positive verdict authorizes only a separate fresh-study preregistration.",
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
        replay=replay,
        classification=classification,
    )
    selected_model = (
        copy.deepcopy(primary["selected_model"])
        if classification["selected_candidate_id"] == STRUCTURED_CANDIDATE_ID
        else None
    )
    models = {
        "fold_model_sha256s": {
            name: [entry["model_sha256"] for entry in primary["candidate_results"][name]["folds"]]
            for name in ("control", "structured")
        },
        "registration_sha256": registration_sha256,
        "replay_selected_model_sha256": replay["selected_model_sha256"],
        "schema_version": MODEL_SCHEMA_VERSION,
        "selected_model": selected_model,
        "selected_model_sha256": (
            primary["selected_model_sha256"] if selected_model is not None else None
        ),
    }
    predictions = {
        "candidate_predictions": {
            name: copy.deepcopy(primary["candidate_results"][name]["predictions"])
            for name in ("control", "structured")
        },
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
        "registration_sha256": registration_sha256,
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": classification["verdict"],
    }
    payloads["artifact_manifest.json"] = canonical_json_bytes(manifest)
    validate_artifact_payloads(payloads)
    return payloads


def _artifact_json(artifacts: Mapping[str, bytes], name: str) -> dict[str, Any]:
    try:
        value = json.loads(
            artifacts[name], object_pairs_hook=_reject_duplicate_pairs
        )
    except StructuredPocBlocked:
        raise
    except (KeyError, UnicodeError, json.JSONDecodeError) as exc:
        raise StructuredPocBlocked(f"canonical artifact {name} is invalid: {exc}") from exc
    return _mapping(value, f"canonical artifact {name}")


def validate_artifact_payloads(artifacts: Mapping[str, bytes]) -> dict[str, Any]:
    if set(artifacts) != set(CANONICAL_ARTIFACT_NAMES):
        raise StructuredPocBlocked("canonical artifact set is incomplete")
    if any(not isinstance(payload, bytes) for payload in artifacts.values()):
        raise StructuredPocBlocked("canonical artifact payloads must be bytes")
    manifest = _artifact_json(artifacts, "artifact_manifest.json")
    if manifest.get("schema_version") != MANIFEST_SCHEMA_VERSION:
        raise StructuredPocBlocked("artifact manifest schema mismatch")
    expected_hashes = {
        name: sha256_bytes(artifacts[name])
        for name in sorted(artifacts)
        if name != "artifact_manifest.json"
    }
    if manifest.get("artifact_hashes") != expected_hashes:
        raise StructuredPocBlocked("artifact manifest hash closure mismatch")
    if manifest.get("authority") != _authority():
        raise StructuredPocBlocked("artifact authority mismatch")
    registration = validate_registration(_artifact_json(artifacts, "configuration.json"))
    registration_sha256 = sha256_bytes(canonical_json_bytes(registration))
    if manifest.get("registration_sha256") != registration_sha256:
        raise StructuredPocBlocked("artifact registration identity mismatch")
    metrics = _artifact_json(artifacts, "metrics.json")
    if (
        metrics.get("schema_version") != METRICS_SCHEMA_VERSION
        or metrics.get("registration_sha256") != registration_sha256
        or metrics.get("authority") != _authority()
    ):
        raise StructuredPocBlocked("metrics artifact contract mismatch")
    classification = _mapping(metrics.get("classification"), "metrics classification")
    if (
        classification.get("authority") != _authority()
        or classification.get("verdict") != manifest.get("verdict")
        or classification.get("verdict")
        not in {
            "blocked",
            "poc_valid_without_structured_candidate",
            "structured_candidate_selected",
        }
    ):
        raise StructuredPocBlocked("artifact verdict contract mismatch")
    predictions = _artifact_json(artifacts, "predictions.json")
    if (
        predictions.get("registration_sha256") != registration_sha256
        or predictions.get("primary_execution_sha256")
        != classification.get("primary_execution_sha256")
        or predictions.get("replay_execution_sha256")
        != classification.get("replay_execution_sha256")
    ):
        raise StructuredPocBlocked("prediction execution identity mismatch")
    models = _artifact_json(artifacts, "models.json")
    selected_model = models.get("selected_model")
    if classification.get("selected_candidate_id") == STRUCTURED_CANDIDATE_ID:
        if not isinstance(selected_model, Mapping):
            raise StructuredPocBlocked("selected model artifact is missing")
        candidate = registration["poc"]["candidates"]["structured"]
        loaded = load_model_payload(
            selected_model,
            candidate=candidate,
            model_seed=registration["poc"]["optimizer"]["model_seed"],
        )
        canonical = canonical_model_payload(loaded, candidate=candidate)
        if models.get("selected_model_sha256") != sha256_bytes(
            canonical_json_bytes(canonical)
        ):
            raise StructuredPocBlocked("selected model hash mismatch")
        if models.get("replay_selected_model_sha256") != models.get(
            "selected_model_sha256"
        ):
            raise StructuredPocBlocked("selected model replay mismatch")
    elif selected_model is not None or models.get("selected_model_sha256") is not None:
        raise StructuredPocBlocked("negative or blocked POC published a selected model")
    try:
        report = artifacts["report.md"].decode("utf-8")
    except UnicodeError as exc:
        raise StructuredPocBlocked(f"report is invalid UTF-8: {exc}") from exc
    if not report.startswith("# Non-Combat Structured Baseline-Ranker POC\n"):
        raise StructuredPocBlocked("report header mismatch")
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
        raise StructuredPocBlocked("output artifact inventory mismatch")
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
        raise StructuredPocBlocked(f"cannot inspect artifact directory: {exc}") from exc
    if not set(CANONICAL_ARTIFACT_NAMES).issubset(entries) or not entries.issubset(allowed):
        raise StructuredPocBlocked("published artifact inventory mismatch")
    artifacts = {name: (root / name).read_bytes() for name in CANONICAL_ARTIFACT_NAMES}
    manifest = validate_artifact_payloads(artifacts)
    if manifest["artifact_hashes"] != {
        name: sha256_file(root / name) for name in sorted(manifest["artifact_hashes"])
    }:
        raise StructuredPocBlocked("published artifact hash closure mismatch")
    journal_path = root / "execution_journal.json"
    if journal_path.exists():
        journal = _load_json(journal_path, "execution journal")
        if journal.get("schema_version") != JOURNAL_SCHEMA_VERSION or journal.get(
            "canonical"
        ) is not False:
            raise StructuredPocBlocked("execution journal contract mismatch")
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
        raise StructuredPocBlocked("execution journal values must be non-negative")
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
    artifacts = build_artifacts(
        registration=value,
        primary=primary,
        replay=replay,
    )
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
    prepare = commands.add_parser(
        "prepare-input", description="Derive one canonical train-only corpus."
    )
    prepare.add_argument("--demonstrations", type=Path, required=True)
    prepare.add_argument("--archive-manifest", type=Path, required=True)
    prepare.add_argument("--warm-start-manifest", type=Path, required=True)
    prepare.add_argument("--output", type=Path, required=True)
    prepare.add_argument("--manifest-output", type=Path, required=True)

    register = commands.add_parser(
        "register", description="Freeze the exact implementation-fit POC registration."
    )
    register.add_argument("--implementation-commit", required=True)
    register.add_argument("--source-archive", type=Path, required=True)
    register.add_argument("--source-archive-manifest", type=Path, required=True)
    register.add_argument("--source-warm-start-manifest", type=Path, required=True)
    register.add_argument("--train-input", type=Path, required=True)
    register.add_argument("--train-input-manifest", type=Path, required=True)
    register.add_argument("--output", type=Path, required=True)

    run = commands.add_parser(
        "run", description="Run one registered primary comparison and replay."
    )
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)

    validate = commands.add_parser(
        "validate", description="Rehash and semantically validate a POC artifact set."
    )
    validate.add_argument("--output-dir", type=Path, required=True)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        if args.command == "prepare-input":
            manifest = prepare_train_input_from_sources(
                demonstrations_path=args.demonstrations,
                archive_manifest_path=args.archive_manifest,
                warm_start_manifest_path=args.warm_start_manifest,
                output_path=args.output,
                output_manifest_path=args.manifest_output,
            )
            print(json.dumps(manifest, indent=2, sort_keys=True))
            return 0
        if args.command == "register":
            registration = build_registration(
                repo_root=repo_root,
                implementation_commit=args.implementation_commit,
                source_archive_path=args.source_archive,
                source_archive_manifest_path=args.source_archive_manifest,
                source_warm_start_manifest_path=args.source_warm_start_manifest,
                train_input_path=args.train_input,
                train_input_manifest_path=args.train_input_manifest,
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
            if train_input["source"]["train_dataset_sha256"] != registration["identity"][
                "train_dataset_sha256"
            ]:
                raise StructuredPocBlocked("registered train dataset identity mismatch")
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
