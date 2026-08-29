"""Collect and fit one development-only late-floor successor experiment."""

from __future__ import annotations

import argparse
import copy
from collections import Counter
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Callable, Mapping, Sequence

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts import (  # noqa: E402
    combat_rl_action_relative_aligned_successor_fit as aligned,
)
from analysis_scripts import (  # noqa: E402
    combat_rl_action_relative_live_context_target as live_target,
)
from analysis_scripts import (  # noqa: E402
    combat_rl_action_relative_successor_context_supplement as supplement,
)
from analysis_scripts import (  # noqa: E402
    combat_rl_action_relative_successor_delta_ablation as predecessor,
)
from analysis_scripts import (  # noqa: E402
    combat_rl_real_context_balanced_corpus as balanced,
)


REPORTS_ROOT = REPO_ROOT / "reports"
COLLECTION_EXPERIMENT_ID = (
    "combat-rl-late-floor-successor-development-collection-20260829-r1"
)
FIT_EXPERIMENT_ID = "combat-rl-late-floor-successor-development-fit-20260829-r1"
COLLECTION_OUTPUT_DIR = REPORTS_ROOT / COLLECTION_EXPERIMENT_ID.replace("-", "_")
FIT_OUTPUT_DIR = REPORTS_ROOT / FIT_EXPERIMENT_ID.replace("-", "_")
COLLECTION_REGISTRATION_PATH = REPORTS_ROOT / (
    f"{COLLECTION_EXPERIMENT_ID.replace('-', '_')}_registration.json"
)
COLLECTION_PREFLIGHT_PATH = REPORTS_ROOT / (
    f"{COLLECTION_EXPERIMENT_ID.replace('-', '_')}_preflight.json"
)
FIT_REGISTRATION_PATH = REPORTS_ROOT / (
    f"{FIT_EXPERIMENT_ID.replace('-', '_')}_registration.json"
)
FIT_PREFLIGHT_PATH = REPORTS_ROOT / (
    f"{FIT_EXPERIMENT_ID.replace('-', '_')}_preflight.json"
)

COLLECTION_REGISTRATION_SCHEMA = (
    "combat-rl-late-floor-successor-development-collection-registration-v1"
)
COLLECTION_REPORT_SCHEMA = (
    "combat-rl-late-floor-successor-development-collection-report-v1"
)
COLLECTION_MANIFEST_SCHEMA = (
    "combat-rl-late-floor-successor-development-collection-manifest-v1"
)
FIT_REGISTRATION_SCHEMA = (
    "combat-rl-late-floor-successor-development-fit-registration-v1"
)
FIT_REPORT_SCHEMA = "combat-rl-late-floor-successor-development-fit-report-v1"
FIT_MANIFEST_SCHEMA = "combat-rl-late-floor-successor-development-fit-manifest-v1"
PROJECTION_SCHEMA = "combat-rl-successor-fresh-context-projection-v1"

FIXED_SLICES = {
    "fit_battle_10": {
        "partition": "fit",
        "seed_bounds": [288000, 290047],
        "battle_indices": [10],
    },
    "calibration_battle_10": {
        "partition": "calibration",
        "seed_bounds": [290048, 290559],
        "battle_indices": [10],
    },
    "fresh_battle_10": {
        "partition": "fresh",
        "seed_bounds": [291000, 292023],
        "battle_indices": [10],
    },
}


def _collection_recipe() -> dict[str, Any]:
    recipe = copy.deepcopy(predecessor.FIXED_CORPUS_RECIPE)
    recipe.pop("partitions")
    recipe.pop("battle_indices")
    recipe.update(
        {
            "slices": copy.deepcopy(FIXED_SLICES),
            "max_wall_seconds": 7200,
            "max_stored_bytes": 805_306_368,
        }
    )
    return recipe


COLLECTION_RECIPE = _collection_recipe()
COLLECTION_RESOURCE_LIMITS = {
    "maximum_wall_seconds": 7200.0,
    "maximum_stored_bytes": 805_306_368,
}
FIT_RESOURCE_LIMITS = {
    "maximum_wall_seconds": 7200.0,
    "maximum_output_bytes": 67_108_864,
}
CONTAMINATION = {
    "development_target_only": True,
    "prior_fresh_metadata_inspected": True,
    "prior_fresh_label_fields_exposed": True,
    "prior_fresh_policy_confirmation": False,
    "independent_confirmation": False,
}
COLLECTION_AUTHORITY = {
    **copy.deepcopy(predecessor.CORPUS_AUTHORITY),
    "development_only": True,
    "formal_evidence": False,
    "model_fitting": False,
    "training": False,
}
FIT_AUTHORITY = {
    **copy.deepcopy(predecessor.FIT_AUTHORITY),
    "development_only": True,
    "model_fitting": True,
    "training": True,
    "independent_confirmation": False,
}

COLLECTION_INPUT_NAMES = (
    "items_json",
    "native_module",
    "parent_checkpoint",
    "predecessor_fit_corpus",
    "predecessor_calibration_corpus",
    "predecessor_fresh_corpus_contaminated",
    "predecessor_report",
    "predecessor_manifest",
    "predecessor_registration",
    "development_target",
    "development_target_report",
    "development_target_manifest",
    "development_target_registration",
)
FIT_INPUT_NAMES = (
    "items_json",
    "parent_checkpoint",
    "development_target",
    "development_target_report",
    "development_target_manifest",
    "development_target_registration",
    "fit_corpus",
    "calibration_corpus",
    "fresh_corpus",
    "fresh_context_projection",
    "collection_report",
    "collection_manifest",
    "collection_registration",
)
PROJECTION_ROW_FIELDS = (
    "row_index",
    "seed",
    "battle_index",
    "floor",
    "floor_ratio",
    "player_hp_ratio",
    "potion_occupied_slots",
    "relic_occupied_slots",
    "player_hp_quartile",
    "context_cell_id",
)
SOURCE_BOUND_PATHS = tuple(
    sorted(
        set(predecessor.SOURCE_SNAPSHOT_PATHS)
        | {
            "analysis_scripts/combat_rl_late_floor_successor_development_fit.py",
            "analysis_scripts/combat_rl_action_relative_successor_context_supplement.py",
            "analysis_scripts/combat_rl_action_relative_aligned_successor_fit.py",
            "analysis_scripts/combat_rl_action_relative_live_context_target.py",
        }
    )
)


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
    resolved = Path(path).resolve()
    if not resolved.is_file():
        raise ValueError(f"late-floor successor input is missing: {resolved}")
    return {
        "path": str(resolved),
        "sha256": predecessor.sha256_file(resolved),
    }


def _validate_source_commit(value: Any) -> str:
    if not isinstance(value, str):
        raise ValueError("late-floor successor source commit is missing")
    normalized = value.lower()
    if len(normalized) != 40 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError("late-floor successor source commit is invalid")
    return normalized


def _source_file_hashes() -> dict[str, str]:
    return {
        relative: predecessor.sha256_file(REPO_ROOT / relative)
        for relative in SOURCE_BOUND_PATHS
    }


def _normalize_inputs(
    inputs: Mapping[str, Mapping[str, str]], *, names: Sequence[str]
) -> dict[str, dict[str, str]]:
    if not isinstance(inputs, Mapping) or set(inputs) != set(names):
        raise ValueError("late-floor successor input inventory differs")
    normalized: dict[str, dict[str, str]] = {}
    for name in names:
        binding = inputs[name]
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise ValueError("late-floor successor input binding differs")
        path = Path(str(binding["path"]))
        if not path.is_absolute():
            raise ValueError("late-floor successor input path must be absolute")
        normalized[name] = {
            "path": str(path.resolve()),
            "sha256": predecessor._validate_sha256(
                binding["sha256"], label=name
            ),
        }
    return normalized


def build_collection_registration(
    source_commit: str, *, inputs: Mapping[str, Mapping[str, str]]
) -> dict[str, Any]:
    return {
        "schema_version": COLLECTION_REGISTRATION_SCHEMA,
        "experiment_id": COLLECTION_EXPERIMENT_ID,
        "source_commit": _validate_source_commit(source_commit),
        "interpreter": str(predecessor.EXPECTED_INTERPRETER.resolve()),
        "runner": file_binding(Path(__file__)),
        "source_files": _source_file_hashes(),
        "inputs": _normalize_inputs(inputs, names=COLLECTION_INPUT_NAMES),
        "recipe": copy.deepcopy(COLLECTION_RECIPE),
        "resource_limits": copy.deepcopy(COLLECTION_RESOURCE_LIMITS),
        "output_dir": str(COLLECTION_OUTPUT_DIR.resolve()),
        "contamination": copy.deepcopy(CONTAMINATION),
        "authority": copy.deepcopy(COLLECTION_AUTHORITY),
    }


def validate_collection_registration(
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    expected = build_collection_registration(
        str(registration.get("source_commit", "")),
        inputs=registration.get("inputs", {}),
    )
    if dict(registration) != expected:
        raise ValueError("late-floor collection registration payload differs")
    validate_slice_contract(expected["recipe"]["slices"], occupied_seeds=set())
    return copy.deepcopy(expected)


def build_fit_registration(
    source_commit: str, *, inputs: Mapping[str, Mapping[str, str]]
) -> dict[str, Any]:
    return {
        "schema_version": FIT_REGISTRATION_SCHEMA,
        "experiment_id": FIT_EXPERIMENT_ID,
        "source_commit": _validate_source_commit(source_commit),
        "interpreter": str(predecessor.EXPECTED_INTERPRETER.resolve()),
        "runner": file_binding(Path(__file__)),
        "source_files": _source_file_hashes(),
        "inputs": _normalize_inputs(inputs, names=FIT_INPUT_NAMES),
        "recipe": copy.deepcopy(predecessor.FIXED_ABLATION_RECIPE),
        "offline_gates": copy.deepcopy(predecessor.FIXED_OFFLINE_GATES),
        "resource_limits": copy.deepcopy(FIT_RESOURCE_LIMITS),
        "output_dir": str(FIT_OUTPUT_DIR.resolve()),
        "contamination": copy.deepcopy(CONTAMINATION),
        "authority": copy.deepcopy(FIT_AUTHORITY),
    }


def validate_fit_registration(registration: Mapping[str, Any]) -> dict[str, Any]:
    expected = build_fit_registration(
        str(registration.get("source_commit", "")),
        inputs=registration.get("inputs", {}),
    )
    if dict(registration) != expected:
        raise ValueError("late-floor fit registration payload differs")
    return copy.deepcopy(expected)


def validate_slice_contract(
    slices: Mapping[str, Mapping[str, Any]], *, occupied_seeds: set[int]
) -> dict[str, Mapping[str, Any]]:
    return supplement.validate_slice_contract(
        slices, occupied_seeds=occupied_seeds
    )


def merge_successor_corpora(
    partition: str, *corpora: Mapping[str, Any]
) -> dict[str, Any]:
    return supplement.merge_successor_corpora(partition, *corpora)


def _projection_identity(
    *, fresh_corpus_identity: Mapping[str, Any], rows: Sequence[Mapping[str, Any]]
) -> str:
    return hashlib.sha256(
        _canonical_json_bytes(
            {
                "fresh_corpus_identity": dict(fresh_corpus_identity),
                "rows": [dict(row) for row in rows],
            }
        )
    ).hexdigest()


def build_fresh_context_projection(fresh_corpus: Mapping[str, Any]) -> dict[str, Any]:
    corpus = predecessor.validate_successor_corpus(
        fresh_corpus, expected_partition="fresh"
    )
    context = balanced._context_rows(corpus)
    rows: list[dict[str, Any]] = []
    for index, (cell, metadata) in enumerate(
        zip(context["cell_ids"], corpus["metadata"])
    ):
        floor = int(metadata["floor"])
        hp_ratio = float(context["player_hp_ratio"][index])
        potion = int(context["potion_occupied_slots"][index])
        relic = int(context["relic_occupied_slots"][index])
        quartile = min(3, max(0, int(hp_ratio * 4.0)))
        expected_cell = live_target.context_cell_id(
            floor=floor,
            potion_occupied_slots=potion,
            relic_occupied_slots=relic,
            player_hp_quartile=quartile,
        )
        if cell != expected_cell:
            raise ValueError("fresh context projection cell identity differs")
        rows.append(
            {
                "row_index": index,
                "seed": int(metadata["seed"]),
                "battle_index": int(metadata["battle_index"]),
                "floor": floor,
                "floor_ratio": float(context["floor_ratio"][index]),
                "player_hp_ratio": hp_ratio,
                "potion_occupied_slots": potion,
                "relic_occupied_slots": relic,
                "player_hp_quartile": quartile,
                "context_cell_id": cell,
            }
        )
    corpus_identity = predecessor.successor_corpus_identity(corpus)
    return {
        "schema_version": PROJECTION_SCHEMA,
        "partition": "fresh",
        "row_count": len(rows),
        "fresh_corpus_identity": corpus_identity,
        "rows": rows,
        "projection_identity_sha256": _projection_identity(
            fresh_corpus_identity=corpus_identity, rows=rows
        ),
        "policy_label_access": False,
    }


def validate_fresh_context_projection(
    projection: Mapping[str, Any],
    *,
    expected_corpus_identity: Mapping[str, Any],
) -> dict[str, Any]:
    required = {
        "schema_version",
        "partition",
        "row_count",
        "fresh_corpus_identity",
        "rows",
        "projection_identity_sha256",
        "policy_label_access",
    }
    if not isinstance(projection, Mapping) or set(projection) != required:
        raise ValueError("fresh context projection shape differs")
    rows = projection["rows"]
    if (
        projection["schema_version"] != PROJECTION_SCHEMA
        or projection["partition"] != "fresh"
        or projection["policy_label_access"] is not False
        or not isinstance(rows, list)
        or int(projection["row_count"]) != len(rows)
        or not rows
        or dict(projection["fresh_corpus_identity"])
        != dict(expected_corpus_identity)
    ):
        raise ValueError("fresh context projection identity differs")
    normalized_rows: list[dict[str, Any]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, Mapping) or set(row) != set(PROJECTION_ROW_FIELDS):
            raise ValueError("fresh context projection row fields differ")
        normalized = dict(row)
        if int(normalized["row_index"]) != index:
            raise ValueError("fresh context projection row index differs")
        floor = int(normalized["floor"])
        hp_ratio = float(normalized["player_hp_ratio"])
        potion = int(normalized["potion_occupied_slots"])
        relic = int(normalized["relic_occupied_slots"])
        quartile = int(normalized["player_hp_quartile"])
        if (
            not math.isfinite(hp_ratio)
            or not 0.0 <= hp_ratio <= 1.0
            or abs(float(normalized["floor_ratio"]) - floor / 50.0) > 1e-6
            or normalized["context_cell_id"]
            != live_target.context_cell_id(
                floor=floor,
                potion_occupied_slots=potion,
                relic_occupied_slots=relic,
                player_hp_quartile=quartile,
            )
        ):
            raise ValueError("fresh context projection row value differs")
        normalized_rows.append(normalized)
    identity = _projection_identity(
        fresh_corpus_identity=expected_corpus_identity, rows=normalized_rows
    )
    if projection["projection_identity_sha256"] != identity:
        raise ValueError("fresh context projection hash differs")
    return copy.deepcopy(dict(projection))


def derive_context_weights_from_projection(
    target_rows: Sequence[Mapping[str, Any]], projection: Mapping[str, Any]
) -> dict[str, Any]:
    value = validate_fresh_context_projection(
        projection,
        expected_corpus_identity=projection.get("fresh_corpus_identity", {}),
    )
    real_rows = live_target._target_feature_rows(target_rows)
    rows = value["rows"]
    cell_ids = [str(row["context_cell_id"]) for row in rows]
    real_counts = Counter(real_rows["cells"])
    simulator_counts = Counter(cell_ids)
    common = set(real_counts).intersection(simulator_counts)
    if not common:
        raise ValueError("development target and fresh projection do not overlap")
    real_total = len(real_rows["cells"])
    simulator_total = len(cell_ids)
    raw_weights = torch.tensor(
        [
            (real_counts[cell] / real_total)
            / (simulator_counts[cell] / simulator_total)
            if cell in common
            else 0.0
            for cell in cell_ids
        ],
        dtype=torch.float64,
    )
    weights = raw_weights / float(raw_weights.sum())
    projection_features = {
        "floor_ratio": torch.tensor(
            [float(row["floor_ratio"]) for row in rows], dtype=torch.float64
        ),
        "player_hp_ratio": torch.tensor(
            [float(row["player_hp_ratio"]) for row in rows], dtype=torch.float64
        ),
        "potion_occupied_slots": torch.tensor(
            [float(row["potion_occupied_slots"]) for row in rows],
            dtype=torch.float64,
        ),
        "relic_occupied_slots": torch.tensor(
            [float(row["relic_occupied_slots"]) for row in rows],
            dtype=torch.float64,
        ),
    }
    floor_coverage: dict[str, float | None] = {}
    for stratum in ("floor_23_27", "floor_28_34"):
        denominator = sum(
            count
            for cell, count in real_counts.items()
            if cell.startswith(f"{stratum}|")
        )
        numerator = sum(
            count
            for cell, count in real_counts.items()
            if cell.startswith(f"{stratum}|") and cell in common
        )
        floor_coverage[stratum] = (
            numerator / denominator if denominator else None
        )
    smds = {
        name: {
            "raw": balanced._smd(
                real_rows[name], projection_features[name], weights=None
            ),
            "weighted": balanced._smd(
                real_rows[name], projection_features[name], weights=weights
            ),
        }
        for name in projection_features
    }
    effective_sample_size = 1.0 / float(weights.square().sum())
    metrics = {
        "real_row_count": real_total,
        "simulator_row_count": simulator_total,
        "real_context_cell_count": len(real_counts),
        "simulator_context_cell_count": len(simulator_counts),
        "matched_context_cell_count": len(common),
        "real_context_mass_covered": sum(real_counts[cell] for cell in common)
        / real_total,
        "simulator_mass_retained": sum(
            simulator_counts[cell] for cell in common
        )
        / simulator_total,
        "floor_context_mass_covered": floor_coverage,
        "effective_sample_size": effective_sample_size,
        "effective_sample_size_fraction": effective_sample_size / simulator_total,
        "maximum_normalized_weight": float(weights.max()),
        "zero_weight_row_count": int((weights == 0.0).sum()),
        "standardized_mean_differences": smds,
    }
    return {
        "weights": weights,
        "cell_ids": cell_ids,
        "matched_cell_ids": sorted(common),
        "metrics": metrics,
    }


def run_if_supported(
    support: Mapping[str, Any], fit: Callable[[], Mapping[str, Any]]
) -> dict[str, Any]:
    gate = support.get("gate")
    if not isinstance(gate, Mapping) or gate.get("passed") is not True:
        return {
            "fit_executed": False,
            "fit_result": None,
            "decision": "development_support_insufficient_close_without_fit",
        }
    result = fit()
    return {
        "fit_executed": True,
        "fit_result": result,
        "decision": str(result.get("decision", "development_paired_fit_complete")),
    }


def _validate_source_binding(source_commit: str) -> None:
    commit = _validate_source_commit(source_commit)
    common = {
        "cwd": str(REPO_ROOT),
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
        "encoding": "ascii",
        "check": False,
    }
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, "HEAD"], **common
    ).returncode:
        raise ValueError("late-floor successor source commit is not an ancestor")
    for relative in SOURCE_BOUND_PATHS:
        if subprocess.run(
            ["git", "cat-file", "-e", f"{commit}:{relative}"], **common
        ).returncode:
            raise ValueError(f"late-floor successor source is absent: {relative}")
    if subprocess.run(
        ["git", "diff", "--quiet", commit, "--", *SOURCE_BOUND_PATHS], **common
    ).returncode:
        raise ValueError("late-floor successor sources differ from registration")


def _validated_inputs(registration: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"]).resolve()
        if not path.is_file() or predecessor.sha256_file(path) != binding["sha256"]:
            raise ValueError(f"late-floor successor input differs: {name}")
        paths[name] = path
    return paths


def _collection_input_paths() -> dict[str, Path]:
    predecessor_root = (
        REPORTS_ROOT
        / "combat_rl_action_relative_successor_context_supplement_20260829_r1"
    )
    target_root = (
        REPORTS_ROOT
        / "combat_rl_action_relative_live_context_target_20260829_r2"
    )
    return {
        "items_json": Path(predecessor.FIXED_INPUTS["items_json"]["path"]),
        "native_module": Path(predecessor.FIXED_INPUTS["native_module"]["path"]),
        "parent_checkpoint": Path(
            predecessor.FIXED_INPUTS["parent_checkpoint"]["path"]
        ),
        "predecessor_fit_corpus": predecessor_root / "fit_corpus.pt",
        "predecessor_calibration_corpus": predecessor_root
        / "calibration_corpus.pt",
        "predecessor_fresh_corpus_contaminated": predecessor_root
        / "fresh_corpus.pt",
        "predecessor_report": predecessor_root / "report.json",
        "predecessor_manifest": predecessor_root / "manifest.json",
        "predecessor_registration": predecessor_root / "registration.json",
        "development_target": target_root / "target.json",
        "development_target_report": target_root / "report.json",
        "development_target_manifest": target_root / "manifest.json",
        "development_target_registration": target_root / "registration.json",
    }


def _collection_input_bindings() -> dict[str, dict[str, str]]:
    return {
        name: file_binding(path)
        for name, path in _collection_input_paths().items()
    }


def _fit_input_paths() -> dict[str, Path]:
    target_root = (
        REPORTS_ROOT
        / "combat_rl_action_relative_live_context_target_20260829_r2"
    )
    return {
        "items_json": Path(predecessor.FIXED_INPUTS["items_json"]["path"]),
        "parent_checkpoint": Path(
            predecessor.FIXED_INPUTS["parent_checkpoint"]["path"]
        ),
        "development_target": target_root / "target.json",
        "development_target_report": target_root / "report.json",
        "development_target_manifest": target_root / "manifest.json",
        "development_target_registration": target_root / "registration.json",
        "fit_corpus": COLLECTION_OUTPUT_DIR / "fit_corpus.pt",
        "calibration_corpus": COLLECTION_OUTPUT_DIR / "calibration_corpus.pt",
        "fresh_corpus": COLLECTION_OUTPUT_DIR / "fresh_corpus.pt",
        "fresh_context_projection": COLLECTION_OUTPUT_DIR / "fresh_context.json",
        "collection_report": COLLECTION_OUTPUT_DIR / "report.json",
        "collection_manifest": COLLECTION_OUTPUT_DIR / "manifest.json",
        "collection_registration": COLLECTION_OUTPUT_DIR / "registration.json",
    }


def _validate_bound_packages(paths: Mapping[str, Path]) -> None:
    if "predecessor_manifest" in paths:
        aligned._validate_manifest_artifacts(
            paths["predecessor_manifest"],
            root=paths["predecessor_manifest"].parent,
            required={
                "fit_corpus.pt",
                "calibration_corpus.pt",
                "fresh_corpus.pt",
                "report.json",
                "registration.json",
            },
        )
    target_manifest_name = (
        "development_target_manifest"
        if "development_target_manifest" in paths
        else None
    )
    if target_manifest_name is not None:
        aligned._validate_manifest_artifacts(
            paths[target_manifest_name],
            root=paths[target_manifest_name].parent,
            required={"target.json", "report.json", "registration.json"},
        )
        report = json.loads(
            paths["development_target_report"].read_text(encoding="ascii")
        )
        if report.get("decision") != (
            "target_ready_for_one_aligned_support_evaluation"
        ):
            raise ValueError("late-floor development target is not sealed")
        registration = json.loads(
            paths["development_target_registration"].read_text(encoding="ascii")
        )
        live_target.validate_target_registration(
            registration, require_batch_outputs=True
        )


def _registered_lineage_seeds(*, exclude_experiment_id: str) -> set[int]:
    seeds = supplement._registered_slice_seeds(
        exclude_experiment_id=exclude_experiment_id
    )
    candidates = {
        *REPORTS_ROOT.glob(
            "combat_rl_late_floor_successor_development*_registration.json"
        ),
        *REPORTS_ROOT.glob(
            "combat_rl_late_floor_successor_development*/registration.json"
        ),
    }
    for path in sorted(candidates):
        try:
            value = json.loads(path.read_text(encoding="ascii"))
        except (OSError, ValueError):
            continue
        if value.get("experiment_id") == exclude_experiment_id:
            continue
        slices = value.get("recipe", {}).get("slices", {})
        if isinstance(slices, Mapping):
            for config in slices.values():
                seeds.update(supplement._slice_seed_set(config))
    return seeds


def _predecessor_seed_inventory(paths: Mapping[str, Path]) -> set[int]:
    seeds: set[int] = set()
    for name, partition in (
        ("predecessor_fit_corpus", "fit"),
        ("predecessor_calibration_corpus", "calibration"),
        ("predecessor_fresh_corpus_contaminated", "fresh"),
    ):
        corpus = predecessor._load_successor_corpus(paths[name], partition=partition)
        seeds.update(int(row["seed"]) for row in corpus["metadata"])
    return seeds


def _context_diagnostics(
    target_rows: Sequence[Mapping[str, Any]],
    train_context: Mapping[str, Any],
) -> dict[str, Any]:
    train_cells = set(train_context["matched_cell_ids"])
    late_rows = [
        row for row in target_rows if 28 <= int(row["floor"]) <= 34
    ]
    counts = Counter(str(row["context_cell_id"]) for row in late_rows)
    missing = sorted(set(counts) - train_cells, key=lambda cell: (-counts[cell], cell))
    matched_mass = sum(counts[cell] for cell in counts if cell in train_cells)
    per_run: list[dict[str, Any]] = []
    for seed in sorted({int(row["run_seed"]) for row in late_rows}):
        rows = [row for row in late_rows if int(row["run_seed"]) == seed]
        matched = sum(row["context_cell_id"] in train_cells for row in rows)
        per_run.append(
            {
                "run_seed": seed,
                "row_count": len(rows),
                "matched_row_count": matched,
                "coverage": matched / len(rows),
            }
        )
    leave_one_out = []
    for item in per_run:
        denominator = len(late_rows) - item["row_count"]
        if denominator:
            leave_one_out.append(
                {
                    "removed_run_seed": item["run_seed"],
                    "remaining_row_count": denominator,
                    "coverage": (
                        matched_mass - item["matched_row_count"]
                    )
                    / denominator,
                }
            )
    return {
        "floor_28_34_target_row_count": len(late_rows),
        "floor_28_34_target_cell_count": len(counts),
        "matched_target_row_count": matched_mass,
        "coverage": matched_mass / len(late_rows) if late_rows else None,
        "missing_cells": [
            {"context_cell_id": cell, "target_row_count": counts[cell]}
            for cell in missing
        ],
        "late_run_count": len(per_run),
        "per_run": per_run,
        "leave_one_late_run_out": leave_one_out,
    }


def evaluate_development_support(
    *,
    target_rows: Sequence[Mapping[str, Any]],
    fit_corpus: Mapping[str, Any],
    calibration_corpus: Mapping[str, Any],
    fresh_projection: Mapping[str, Any],
    integrity: Mapping[str, bool],
) -> dict[str, Any]:
    train = predecessor._combined_training_source_view(
        fit_corpus, calibration_corpus
    )
    train_context = live_target.derive_context_weights_from_target(
        target_rows, train
    )
    fresh_context = derive_context_weights_from_projection(
        target_rows, fresh_projection
    )
    late_rows = sum(
        23 <= int(row["floor"]) <= 34 for row in fresh_projection["rows"]
    )
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
        "integrity": dict(integrity),
        "gate": gate,
        "late_floor_attribution": _context_diagnostics(
            target_rows, train_context
        ),
        "development_only": True,
        "fresh_policy_evaluation": False,
    }


def _partition_summary(corpus: Mapping[str, Any]) -> dict[str, Any]:
    partition = str(corpus["partition"])
    value = predecessor.validate_successor_corpus(
        corpus, expected_partition=partition
    )
    return {
        "partition": partition,
        "row_count": int(value["row_count"]),
        "pair_count": int(value["pair_count"]),
        "seed_count": len({int(row["seed"]) for row in value["metadata"]}),
        "battle_indices": sorted(
            {int(row["battle_index"]) for row in value["metadata"]}
        ),
        "identity": predecessor.successor_corpus_identity(value),
    }


def _publish_collection(
    *,
    corpora: Mapping[str, Mapping[str, Any]],
    projection: Mapping[str, Any],
    report: Mapping[str, Any],
    registration: Mapping[str, Any],
    preflight: Mapping[str, Any],
    started: Mapping[str, Any],
) -> dict[str, Any]:
    staging = COLLECTION_OUTPUT_DIR.with_name(
        f".{COLLECTION_OUTPUT_DIR.name}.staging"
    )
    if COLLECTION_OUTPUT_DIR.exists() or staging.exists():
        raise ValueError("late-floor collection output or staging exists")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        for name, corpus in corpora.items():
            validated = predecessor.validate_successor_corpus(
                corpus, expected_partition=str(corpus["partition"])
            )
            torch.save(validated, staging / f"{name}_corpus.pt")
        (staging / "fresh_context.json").write_bytes(
            _canonical_json_bytes(projection)
        )
        (staging / "report.json").write_bytes(_canonical_json_bytes(report))
        (staging / "registration.json").write_bytes(
            _canonical_json_bytes(registration)
        )
        (staging / "preflight.json").write_bytes(
            _canonical_json_bytes(preflight)
        )
        (staging / "started_receipt.json").write_bytes(
            _canonical_json_bytes(started)
        )
        summary = "\n".join(
            (
                "# Late-floor successor development collection",
                "",
                f"- Decision: `{report['decision']}`",
                f"- Development support passed: `{str(report['development_support']['gate']['passed']).lower()}`",
                f"- Fresh policy evaluation: `false`",
                "",
                "This is development-only evidence and grants no gameplay,",
                "qualification, promotion, or production authority.",
                "",
            )
        )
        (staging / "summary.md").write_text(
            summary, encoding="ascii", newline="\n"
        )
        stored = sum(path.stat().st_size for path in staging.iterdir() if path.is_file())
        if stored > int(COLLECTION_RESOURCE_LIMITS["maximum_stored_bytes"]):
            raise RuntimeError("late-floor collection exceeds storage limit")
        artifacts = {
            path.name: {
                "sha256": predecessor.sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(staging.iterdir())
            if path.is_file() and path.name != "manifest.json"
        }
        manifest = {
            "schema_version": COLLECTION_MANIFEST_SCHEMA,
            "experiment_id": COLLECTION_EXPERIMENT_ID,
            "source_commit": registration["source_commit"],
            "decision": report["decision"],
            "artifacts": artifacts,
        }
        (staging / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
        os.replace(staging, COLLECTION_OUTPUT_DIR)
        return manifest
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _registration_sha256(registration: Mapping[str, Any]) -> str:
    return hashlib.sha256(_canonical_json_bytes(registration)).hexdigest()


def _validate_preflight(
    preflight: Mapping[str, Any],
    *,
    registration: Mapping[str, Any],
    schema_version: str,
) -> dict[str, Any]:
    if (
        not isinstance(preflight, Mapping)
        or preflight.get("schema_version") != schema_version
        or preflight.get("experiment_id") != registration["experiment_id"]
        or preflight.get("source_commit") != registration["source_commit"]
        or preflight.get("registration_sha256")
        != _registration_sha256(registration)
        or preflight.get("authority") != registration["authority"]
        or preflight.get("output_absent") is not True
        or preflight.get("native_loaded") is not False
        or preflight.get("optimizer_constructed") is not False
        or preflight.get("fresh_policy_metric_access") is not False
    ):
        raise ValueError("late-floor successor preflight differs")
    return copy.deepcopy(dict(preflight))


def write_collection_registration(*, source_commit: str) -> dict[str, Any]:
    started = REPORTS_ROOT / f".{COLLECTION_EXPERIMENT_ID}.started.json"
    failure = REPORTS_ROOT / (
        f"{COLLECTION_EXPERIMENT_ID.replace('-', '_')}_failure.json"
    )
    staging = COLLECTION_OUTPUT_DIR.with_name(
        f".{COLLECTION_OUTPUT_DIR.name}.staging"
    )
    collisions = (
        COLLECTION_REGISTRATION_PATH,
        COLLECTION_PREFLIGHT_PATH,
        COLLECTION_OUTPUT_DIR,
        staging,
        started,
        failure,
    )
    if any(path.exists() for path in collisions):
        raise ValueError("late-floor collection registration or output exists")
    registration = validate_collection_registration(
        build_collection_registration(
            source_commit, inputs=_collection_input_bindings()
        )
    )
    _validate_source_binding(registration["source_commit"])
    paths = _validated_inputs(registration)
    _validate_bound_packages(paths)
    occupied = _registered_lineage_seeds(
        exclude_experiment_id=COLLECTION_EXPERIMENT_ID
    ) | _predecessor_seed_inventory(paths)
    validate_slice_contract(
        registration["recipe"]["slices"], occupied_seeds=occupied
    )
    preflight = {
        "schema_version": (
            "combat-rl-late-floor-successor-development-collection-preflight-v1"
        ),
        "experiment_id": COLLECTION_EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "registration_sha256": _registration_sha256(registration),
        "lineage_seed_count": len(occupied),
        "registered_profile_count": sum(
            len(supplement._slice_seed_set(config))
            for config in registration["recipe"]["slices"].values()
        ),
        "output_absent": True,
        "native_loaded": False,
        "optimizer_constructed": False,
        "fresh_policy_metric_access": False,
        "authority": copy.deepcopy(registration["authority"]),
    }
    COLLECTION_REGISTRATION_PATH.write_bytes(
        _canonical_json_bytes(registration)
    )
    COLLECTION_PREFLIGHT_PATH.write_bytes(_canonical_json_bytes(preflight))
    return {"registration": registration, "preflight": preflight}


def _load_collection_registration(path: Path) -> dict[str, Any]:
    if path.resolve() != COLLECTION_REGISTRATION_PATH.resolve():
        raise ValueError("late-floor collection registration path differs")
    live_target.require_committed_file(
        path, label="late-floor collection registration"
    )
    registration = validate_collection_registration(
        json.loads(path.read_text(encoding="ascii"))
    )
    preflight = json.loads(COLLECTION_PREFLIGHT_PATH.read_text(encoding="ascii"))
    _validate_preflight(
        preflight,
        registration=registration,
        schema_version=(
            "combat-rl-late-floor-successor-development-collection-preflight-v1"
        ),
    )
    return registration


def _collection_report(
    *,
    registration: Mapping[str, Any],
    started: Mapping[str, Any],
    supplements: Mapping[str, Mapping[str, Any]],
    collection_summaries: Mapping[str, Mapping[str, Any]],
    merged: Mapping[str, Mapping[str, Any]],
    projection: Mapping[str, Any],
    support: Mapping[str, Any],
    initialization: Mapping[str, Any],
    parent_before: str,
    parent_after: str,
    provenance: Mapping[str, Any],
    elapsed_seconds: float,
) -> dict[str, Any]:
    decision = (
        "development_support_ready_for_registered_fit"
        if support["gate"]["passed"] is True
        else "development_support_insufficient_close_without_fit"
    )
    return {
        "schema_version": COLLECTION_REPORT_SCHEMA,
        "experiment_id": COLLECTION_EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "inputs": copy.deepcopy(registration["inputs"]),
        "recipe": copy.deepcopy(registration["recipe"]),
        "resource_limits": copy.deepcopy(registration["resource_limits"]),
        "partitions": {
            "fit_supplement": _partition_summary(
                supplements["fit_battle_10"]
            ),
            "calibration_supplement": _partition_summary(
                supplements["calibration_battle_10"]
            ),
            "fresh": _partition_summary(supplements["fresh_battle_10"]),
            "fit": _partition_summary(merged["fit"]),
            "calibration": _partition_summary(merged["calibration"]),
        },
        "collection_summaries": copy.deepcopy(dict(collection_summaries)),
        "fresh_context_projection": {
            "schema_version": projection["schema_version"],
            "row_count": projection["row_count"],
            "projection_identity_sha256": projection[
                "projection_identity_sha256"
            ],
            "fresh_corpus_identity": copy.deepcopy(
                projection["fresh_corpus_identity"]
            ),
            "policy_label_access": False,
        },
        "development_support": copy.deepcopy(dict(support)),
        "initialization": copy.deepcopy(dict(initialization)),
        "parent_state_dict_sha256_before": parent_before,
        "parent_state_dict_sha256_after": parent_after,
        "parent_immutable": parent_before == parent_after,
        "provenance": copy.deepcopy(dict(provenance)),
        "started_receipt": copy.deepcopy(dict(started)),
        "elapsed_seconds_before_publication": float(elapsed_seconds),
        "optimizer_constructed": False,
        "fit_executed": False,
        "fresh_policy_evaluation": False,
        "decision": decision,
        "contamination": copy.deepcopy(CONTAMINATION),
        "authority": copy.deepcopy(registration["authority"]),
    }


def run_registered_collection(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != predecessor.EXPECTED_INTERPRETER.resolve():
        raise ValueError("late-floor collection must use the Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("late-floor collection must run in isolated mode")
    registration = _load_collection_registration(
        Path(registration_path).resolve()
    )
    _validate_source_binding(registration["source_commit"])
    paths = _validated_inputs(registration)
    _validate_bound_packages(paths)
    occupied = _registered_lineage_seeds(
        exclude_experiment_id=COLLECTION_EXPERIMENT_ID
    ) | _predecessor_seed_inventory(paths)
    validate_slice_contract(
        registration["recipe"]["slices"], occupied_seeds=occupied
    )
    staging = COLLECTION_OUTPUT_DIR.with_name(
        f".{COLLECTION_OUTPUT_DIR.name}.staging"
    )
    started_path = REPORTS_ROOT / f".{COLLECTION_EXPERIMENT_ID}.started.json"
    failure_path = REPORTS_ROOT / (
        f"{COLLECTION_EXPERIMENT_ID.replace('-', '_')}_failure.json"
    )
    if (
        COLLECTION_OUTPUT_DIR.exists()
        or staging.exists()
        or started_path.exists()
        or failure_path.exists()
    ):
        raise ValueError("late-floor collection output, receipt, or failure exists")
    started_at = time.time()
    started = {
        "schema_version": (
            "combat-rl-late-floor-successor-development-collection-started-v1"
        ),
        "experiment_id": COLLECTION_EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "started_unix": started_at,
        "native_loaded": False,
        "optimizer_constructed": False,
        "fresh_policy_metric_access": False,
    }
    started_path.write_bytes(_canonical_json_bytes(started))
    native_module = predecessor.load_native_module(paths["native_module"])
    mapper = predecessor.build_id_mapper(paths["items_json"])
    initial = predecessor.load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = predecessor.create_fresh_trainer(
        mapper, seed=2026082903, batch_size=128, learning_starts=128
    )
    _parent_state, initialization = predecessor.initialize_trainer(
        trainer, initial
    )
    parent_before = predecessor.state_dict_sha256(
        trainer.online_network.state_dict()
    )
    supplements, collection_summaries = supplement._collect_slices(
        registration,
        native_module=native_module,
        mapper=mapper,
        trainer=trainer,
    )
    parent_after = predecessor.state_dict_sha256(
        trainer.online_network.state_dict()
    )
    if parent_before != parent_after:
        raise RuntimeError("late-floor collection changed the frozen parent")
    predecessor_fit = predecessor._load_successor_corpus(
        paths["predecessor_fit_corpus"], partition="fit"
    )
    predecessor_calibration = predecessor._load_successor_corpus(
        paths["predecessor_calibration_corpus"], partition="calibration"
    )
    merged = {
        "fit": merge_successor_corpora(
            "fit", predecessor_fit, supplements["fit_battle_10"]
        ),
        "calibration": merge_successor_corpora(
            "calibration",
            predecessor_calibration,
            supplements["calibration_battle_10"],
        ),
        "fresh": predecessor.validate_successor_corpus(
            supplements["fresh_battle_10"], expected_partition="fresh"
        ),
    }
    supplement.validate_merged_seed_isolation(merged)
    projection = build_fresh_context_projection(merged["fresh"])
    target = aligned._load_live_target(paths["development_target"])
    train = predecessor._combined_training_source_view(
        merged["fit"], merged["calibration"]
    )
    fresh_view = predecessor._balanced_source_view(
        merged["fresh"], partition="evaluation"
    )
    integrity = balanced._integrity_conditions(train, fresh_view)
    support = evaluate_development_support(
        target_rows=target["rows"],
        fit_corpus=merged["fit"],
        calibration_corpus=merged["calibration"],
        fresh_projection=projection,
        integrity=integrity,
    )
    provenance = predecessor.collect_provenance(
        repo_root=REPO_ROOT,
        simulator_repo=predecessor.SIMULATOR_REPO,
        module_path=paths["native_module"],
        native_module=native_module,
    )
    elapsed = time.time() - started_at
    if elapsed > float(COLLECTION_RESOURCE_LIMITS["maximum_wall_seconds"]):
        raise RuntimeError("late-floor collection exceeds wall-time limit")
    report = _collection_report(
        registration=registration,
        started=started,
        supplements=supplements,
        collection_summaries=collection_summaries,
        merged=merged,
        projection=projection,
        support=support,
        initialization=initialization,
        parent_before=parent_before,
        parent_after=parent_after,
        provenance=provenance,
        elapsed_seconds=elapsed,
    )
    preflight = _validate_preflight(
        json.loads(COLLECTION_PREFLIGHT_PATH.read_text(encoding="ascii")),
        registration=registration,
        schema_version=(
            "combat-rl-late-floor-successor-development-collection-preflight-v1"
        ),
    )
    _publish_collection(
        corpora={
            "fit_supplement": supplements["fit_battle_10"],
            "calibration_supplement": supplements[
                "calibration_battle_10"
            ],
            "fit": merged["fit"],
            "calibration": merged["calibration"],
            "fresh": merged["fresh"],
        },
        projection=projection,
        report=report,
        registration=registration,
        preflight=preflight,
        started=started,
    )
    return report


def _validate_collection_package(paths: Mapping[str, Path]) -> dict[str, Any]:
    manifest = aligned._validate_manifest_artifacts(
        paths["collection_manifest"],
        root=paths["collection_manifest"].parent,
        required={
            "fit_corpus.pt",
            "calibration_corpus.pt",
            "fresh_corpus.pt",
            "fresh_context.json",
            "report.json",
            "registration.json",
        },
    )
    report = json.loads(paths["collection_report"].read_text(encoding="ascii"))
    if (
        report.get("schema_version") != COLLECTION_REPORT_SCHEMA
        or manifest.get("decision") != report.get("decision")
        or report.get("contamination") != CONTAMINATION
        or report.get("authority") != COLLECTION_AUTHORITY
        or report.get("fresh_policy_evaluation") is not False
    ):
        raise ValueError("late-floor collection package differs")
    support = report.get("development_support")
    if not isinstance(support, Mapping):
        raise ValueError("late-floor development support is missing")
    projection = json.loads(
        paths["fresh_context_projection"].read_text(encoding="ascii")
    )
    expected_identity = report.get("partitions", {}).get("fresh", {}).get(
        "identity"
    )
    if not isinstance(expected_identity, Mapping):
        raise ValueError("late-floor fresh corpus identity is missing")
    validate_fresh_context_projection(
        projection, expected_corpus_identity=expected_identity
    )
    if (
        report.get("fresh_context_projection", {}).get(
            "projection_identity_sha256"
        )
        != projection["projection_identity_sha256"]
    ):
        raise ValueError("late-floor fresh projection report differs")
    return report


def write_fit_registration(*, source_commit: str) -> dict[str, Any]:
    started = REPORTS_ROOT / f".{FIT_EXPERIMENT_ID}.started.json"
    failure = REPORTS_ROOT / f"{FIT_EXPERIMENT_ID.replace('-', '_')}_failure.json"
    staging = FIT_OUTPUT_DIR.with_name(f".{FIT_OUTPUT_DIR.name}.staging")
    collisions = (
        FIT_REGISTRATION_PATH,
        FIT_PREFLIGHT_PATH,
        FIT_OUTPUT_DIR,
        staging,
        started,
        failure,
    )
    if any(path.exists() for path in collisions):
        raise ValueError("late-floor fit registration or output exists")
    inputs = {name: file_binding(path) for name, path in _fit_input_paths().items()}
    registration = validate_fit_registration(
        build_fit_registration(source_commit, inputs=inputs)
    )
    _validate_source_binding(registration["source_commit"])
    paths = _validated_inputs(registration)
    _validate_bound_packages(paths)
    report = _validate_collection_package(paths)
    support = report["development_support"]
    if support.get("gate", {}).get("passed") is not True:
        raise ValueError("late-floor development support did not pass")
    preflight = {
        "schema_version": (
            "combat-rl-late-floor-successor-development-fit-preflight-v1"
        ),
        "experiment_id": FIT_EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "registration_sha256": _registration_sha256(registration),
        "collection_decision": report["decision"],
        "development_support_decision": support["gate"]["decision"],
        "output_absent": True,
        "native_loaded": False,
        "optimizer_constructed": False,
        "fresh_policy_metric_access": False,
        "authority": copy.deepcopy(registration["authority"]),
    }
    FIT_REGISTRATION_PATH.write_bytes(_canonical_json_bytes(registration))
    FIT_PREFLIGHT_PATH.write_bytes(_canonical_json_bytes(preflight))
    return {"registration": registration, "preflight": preflight}


def _load_fit_registration(path: Path) -> dict[str, Any]:
    if path.resolve() != FIT_REGISTRATION_PATH.resolve():
        raise ValueError("late-floor fit registration path differs")
    live_target.require_committed_file(path, label="late-floor fit registration")
    registration = validate_fit_registration(
        json.loads(path.read_text(encoding="ascii"))
    )
    preflight = json.loads(FIT_PREFLIGHT_PATH.read_text(encoding="ascii"))
    _validate_preflight(
        preflight,
        registration=registration,
        schema_version="combat-rl-late-floor-successor-development-fit-preflight-v1",
    )
    return registration


def _development_fit_decision(fit_result: Mapping[str, Any] | None) -> str:
    if fit_result is None:
        return "development_support_insufficient_close_without_fit"
    if fit_result["hard_gate"]["all_conditions_passed"] is True:
        return "development_hard_pass_propose_independent_live_confirmation"
    if fit_result["representation_signal"]["all_conditions_passed"] is True:
        return (
            "development_descriptive_pass_propose_independent_live_confirmation"
        )
    return "development_successor_recipe_closed"


def _publish_fit(
    *,
    registration: Mapping[str, Any],
    preflight: Mapping[str, Any],
    started: Mapping[str, Any],
    support: Mapping[str, Any],
    fit_result: Mapping[str, Any] | None,
) -> dict[str, Any]:
    decision = _development_fit_decision(fit_result)
    report = {
        "schema_version": FIT_REPORT_SCHEMA,
        "experiment_id": FIT_EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "inputs": copy.deepcopy(registration["inputs"]),
        "recipe": copy.deepcopy(registration["recipe"]),
        "offline_gates": copy.deepcopy(registration["offline_gates"]),
        "resource_limits": copy.deepcopy(registration["resource_limits"]),
        "development_support": copy.deepcopy(dict(support)),
        "optimizer_constructed": fit_result is not None,
        "fit_executed": fit_result is not None,
        "fit_result": (
            None
            if fit_result is None
            else {
                key: value
                for key, value in fit_result.items()
                if key != "artifacts"
            }
        ),
        "decision": decision,
        "contamination": copy.deepcopy(CONTAMINATION),
        "authority": {
            **copy.deepcopy(FIT_AUTHORITY),
            "lightspeed_policy_gate": False,
            "candidate_action_takeover": False,
            "qualification": False,
            "promotion": False,
        },
    }
    staging = FIT_OUTPUT_DIR.with_name(f".{FIT_OUTPUT_DIR.name}.staging")
    if FIT_OUTPUT_DIR.exists() or staging.exists():
        raise ValueError("late-floor fit output or staging exists")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        if fit_result is not None:
            artifact_path = staging / "paired_successor_delta_ablation.pth"
            torch.save(
                {
                    "schema_version": (
                        "combat-rl-late-floor-successor-development-artifact-v1"
                    ),
                    "recipe": copy.deepcopy(predecessor.FIXED_ABLATION_RECIPE),
                    "parent_checkpoint_sha256": registration["inputs"][
                        "parent_checkpoint"
                    ]["sha256"],
                    "sampling_plan_sha256": fit_result[
                        "sampling_plan_sha256"
                    ],
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
        (staging / "registration.json").write_bytes(
            _canonical_json_bytes(registration)
        )
        (staging / "preflight.json").write_bytes(
            _canonical_json_bytes(preflight)
        )
        (staging / "started_receipt.json").write_bytes(
            _canonical_json_bytes(started)
        )
        summary = "\n".join(
            (
                "# Late-floor successor development fit",
                "",
                f"- Decision: `{decision}`",
                f"- Fit executed: `{str(fit_result is not None).lower()}`",
                "",
                "This is development-only evidence and grants no gameplay,",
                "qualification, promotion, or production authority.",
                "",
            )
        )
        (staging / "summary.md").write_text(
            summary, encoding="ascii", newline="\n"
        )
        stored = sum(path.stat().st_size for path in staging.iterdir() if path.is_file())
        if stored > int(FIT_RESOURCE_LIMITS["maximum_output_bytes"]):
            raise RuntimeError("late-floor fit exceeds storage limit")
        artifacts = {
            path.name: {
                "sha256": predecessor.sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(staging.iterdir())
            if path.is_file() and path.name != "manifest.json"
        }
        manifest = {
            "schema_version": FIT_MANIFEST_SCHEMA,
            "experiment_id": FIT_EXPERIMENT_ID,
            "source_commit": registration["source_commit"],
            "decision": decision,
            "artifacts": artifacts,
        }
        (staging / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
        os.replace(staging, FIT_OUTPUT_DIR)
        return report
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def run_registered_fit(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != predecessor.EXPECTED_INTERPRETER.resolve():
        raise ValueError("late-floor fit must use the Windows interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("late-floor fit must run in isolated mode")
    registration = _load_fit_registration(Path(registration_path).resolve())
    _validate_source_binding(registration["source_commit"])
    paths = _validated_inputs(registration)
    _validate_bound_packages(paths)
    collection_report = _validate_collection_package(paths)
    support = collection_report["development_support"]
    staging = FIT_OUTPUT_DIR.with_name(f".{FIT_OUTPUT_DIR.name}.staging")
    started_path = REPORTS_ROOT / f".{FIT_EXPERIMENT_ID}.started.json"
    failure_path = REPORTS_ROOT / f"{FIT_EXPERIMENT_ID.replace('-', '_')}_failure.json"
    if (
        FIT_OUTPUT_DIR.exists()
        or staging.exists()
        or started_path.exists()
        or failure_path.exists()
    ):
        raise ValueError("late-floor fit output, receipt, or failure exists")
    started_at = time.time()
    started = {
        "schema_version": (
            "combat-rl-late-floor-successor-development-fit-started-v1"
        ),
        "experiment_id": FIT_EXPERIMENT_ID,
        "source_commit": registration["source_commit"],
        "started_unix": started_at,
        "optimizer_constructed": False,
        "fresh_corpus_deserialized": False,
        "fresh_policy_metric_access": False,
    }
    started_path.write_bytes(_canonical_json_bytes(started))

    def execute_fit() -> Mapping[str, Any]:
        target = aligned._load_live_target(paths["development_target"])
        fit_corpus = predecessor._load_successor_corpus(
            paths["fit_corpus"], partition="fit"
        )
        calibration_corpus = predecessor._load_successor_corpus(
            paths["calibration_corpus"], partition="calibration"
        )
        return aligned._fit_once(
            registration=registration,
            paths={
                "items_json": paths["items_json"],
                "parent_checkpoint": paths["parent_checkpoint"],
                "fresh_corpus": paths["fresh_corpus"],
            },
            target_rows=target["rows"],
            fit_corpus=fit_corpus,
            calibration_corpus=calibration_corpus,
        )

    outcome = run_if_supported(support, execute_fit)
    fit_result = outcome["fit_result"]
    if time.time() - started_at > float(FIT_RESOURCE_LIMITS["maximum_wall_seconds"]):
        raise RuntimeError("late-floor fit exceeds wall-time limit")
    preflight = _validate_preflight(
        json.loads(FIT_PREFLIGHT_PATH.read_text(encoding="ascii")),
        registration=registration,
        schema_version="combat-rl-late-floor-successor-development-fit-preflight-v1",
    )
    return _publish_fit(
        registration=registration,
        preflight=preflight,
        started=started,
        support=support,
        fit_result=fit_result,
    )


def record_started_failure(
    registration_path: Path, error: BaseException
) -> Path | None:
    try:
        registration = json.loads(
            Path(registration_path).read_text(encoding="ascii")
        )
        experiment_id = str(registration["experiment_id"])
        source_commit = str(registration["source_commit"])
        output = Path(registration["output_dir"]).resolve()
    except (OSError, KeyError, TypeError, ValueError):
        return None
    started_path = REPORTS_ROOT / f".{experiment_id}.started.json"
    if not started_path.is_file():
        return None
    failure_path = REPORTS_ROOT / f"{experiment_id.replace('-', '_')}_failure.json"
    if failure_path.exists():
        return failure_path
    started = json.loads(started_path.read_text(encoding="ascii"))
    failure = {
        "schema_version": "combat-rl-late-floor-successor-development-failure-v1",
        "experiment_id": experiment_id,
        "source_commit": source_commit,
        "started_receipt": started,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "output_exists": output.exists(),
        "authority": copy.deepcopy(registration.get("authority", {})),
    }
    failure_path.write_bytes(_canonical_json_bytes(failure))
    return failure_path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument("--write-collection-registration", action="store_true")
    modes.add_argument("--run-collection-registration", type=Path)
    modes.add_argument("--write-fit-registration", action="store_true")
    modes.add_argument("--run-fit-registration", type=Path)
    parser.add_argument("--source-commit")
    args = parser.parse_args()
    if args.write_collection_registration or args.write_fit_registration:
        if args.source_commit is None:
            parser.error("--source-commit is required in write mode")
        result = (
            write_collection_registration(source_commit=args.source_commit)
            if args.write_collection_registration
            else write_fit_registration(source_commit=args.source_commit)
        )
    else:
        if args.source_commit is not None:
            parser.error("run mode reads source identity from registration")
        registration_path = (
            args.run_collection_registration or args.run_fit_registration
        )
        try:
            result = (
                run_registered_collection(registration_path)
                if args.run_collection_registration is not None
                else run_registered_fit(registration_path)
            )
        except BaseException as error:
            record_started_failure(registration_path, error)
            raise
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


__all__ = [
    "COLLECTION_INPUT_NAMES",
    "FIT_INPUT_NAMES",
    "FIXED_SLICES",
    "PROJECTION_ROW_FIELDS",
    "build_collection_registration",
    "validate_collection_registration",
    "build_fit_registration",
    "validate_fit_registration",
    "file_binding",
    "validate_slice_contract",
    "merge_successor_corpora",
    "build_fresh_context_projection",
    "validate_fresh_context_projection",
    "derive_context_weights_from_projection",
    "run_if_supported",
    "evaluate_development_support",
    "write_collection_registration",
    "run_registered_collection",
    "write_fit_registration",
    "run_registered_fit",
]
