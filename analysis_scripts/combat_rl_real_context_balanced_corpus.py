"""Build one real-context-balanced late-progression guard corpus."""

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
from typing import Any, Iterable, Mapping, Sequence

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts.combat_lightspeed_replay_distribution_calibration import (  # noqa: E402
    RealReplayBinding,
    SEMANTIC_CONTINUOUS_INDICES,
    TransitionBatch,
    floor_stratum,
    load_real_replay_bindings,
)
from analysis_scripts.combat_lightspeed_training_smoke import (  # noqa: E402
    create_fresh_trainer,
    initialize_trainer,
    load_initial_checkpoint,
    parameter_sha256,
)
from analysis_scripts.combat_rl_guard_advantage_corpus import (  # noqa: E402
    CORPUS_KIND,
    CorpusConfig,
    collect_partition,
    collect_provenance,
)
from analysis_scripts.combat_rl_guard_advantage_residual_fit import (  # noqa: E402
    load_corpus,
    sha256_file,
)
from analysis_scripts.combat_lightspeed_bridge import load_native_module  # noqa: E402
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


SCHEMA_VERSION = 1
REGISTRATION_SCHEMA = "combat-rl-real-context-balanced-corpus-registration-v1"
REPORT_SCHEMA = "combat-rl-real-context-balanced-corpus-report-v1"
WEIGHTS_SCHEMA = "combat-rl-real-context-weights-v1"
MANIFEST_SCHEMA = "combat-rl-real-context-balanced-corpus-manifest-v1"
EXPERIMENT_ID = "combat-rl-real-context-balanced-corpus-20260829-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
OUTPUT_DIR = REPORTS_ROOT / EXPERIMENT_ID.replace("-", "_")
STAGING_DIR = REPORTS_ROOT / f".{OUTPUT_DIR.name}.staging"
SIMULATOR_REPO = Path(r"D:\CLionProjects\sts_lightspeed")

FIXED_RECIPE = {
    "train_seed_first": 268000,
    "train_seed_last": 269023,
    "evaluation_seed_first": 270000,
    "evaluation_seed_last": 270511,
    "battle_indices": [10, 11, 12, 13, 14],
    "target_floor_first": 23,
    "target_floor_last": 34,
    "max_source_decisions": 100,
    "max_actions_per_turn": 8,
    "max_states_per_profile": 2,
    "max_canonical_actions": 8,
    "continuation_decisions": 8,
    "return_discount": 0.99,
    "positive_advantage_margin": 0.5,
    "context_cell": [
        "floor_stratum",
        "potion_occupied_slots",
        "relic_occupied_slots",
        "player_hp_quartile",
    ],
}

FIXED_GATES = {
    "evaluation_late_floor_rows_minimum": 256,
    "real_context_mass_covered_minimum": 0.90,
    "floor_23_27_context_mass_covered_minimum": 0.80,
    "floor_28_34_context_mass_covered_minimum": 0.60,
    "train_effective_sample_size_minimum": 750.0,
    "evaluation_effective_sample_size_minimum": 400.0,
    "maximum_normalized_weight_maximum": 0.015,
    "player_hp_ratio_weighted_smd_maximum": 0.20,
    "potion_occupied_slots_weighted_smd_maximum": 0.20,
    "relic_occupied_slots_weighted_smd_maximum": 0.20,
    "floor_ratio_weighted_smd_maximum": 0.30,
}

AUTHORITY = {
    "native_corpus_generation": True,
    "descriptive_context_support": True,
    "model_fitting": False,
    "training": False,
    "evaluation": False,
    "ope": False,
    "gameplay": False,
    "communication_mod": False,
    "production_checkpoint_loading": False,
    "production_checkpoint_writing": False,
    "qualification": False,
    "promotion": False,
}

SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_real_context_balanced_corpus.py",
    "analysis_scripts/combat_rl_guard_advantage_corpus.py",
    "analysis_scripts/combat_rl_guard_advantage_residual_fit.py",
    "analysis_scripts/combat_lightspeed_replay_distribution_calibration.py",
    "analysis_scripts/combat_lightspeed_training_smoke.py",
    "analysis_scripts/combat_lightspeed_bridge.py",
    "spirecomm/ai/rl/v2/action_space.py",
    "spirecomm/ai/rl/v2/id_mapping.py",
    "spirecomm/ai/rl/v2/network.py",
    "spirecomm/ai/rl/v2/state_encoder.py",
)

FIXED_INPUTS = {
    "native_module": {
        "path": REPO_ROOT
        / ".sts_lightspeed_combat_guard_advantage_20260828_r1_build"
        / "sts_lightspeed_combat_adapter.cp310-win_amd64.pyd",
        "sha256": "195678b7fc6bf69815f3d2971404afb8ce72fb666700edf4203383429caf1009",
    },
    "items_json": {
        "path": Path(r"D:\SteamLibrary\steamapps\common\SlayTheSpire\export\items.json"),
        "sha256": "e23784ea8ed3092e3bfa9918240e162a9cbcb837badfb53c612eb0d83cc811dc",
    },
    "initial_checkpoint": {
        "path": REPORTS_ROOT
        / "combat_lightspeed_production_r16_shadow_20260819_r1"
        / "simulator_only_production_shadow.pth",
        "sha256": "ce2ae34f82b3f457fb35e87d429c397204c42d0f742d3ac8952d91b69119b83b",
    },
    "base_train_corpus": {
        "path": REPORTS_ROOT
        / "combat_rl_guard_advantage_expanded_corpus_20260829_r1"
        / "train_corpus.pt",
        "sha256": "90f3e83763f2591065380e89b24ebbedc7bbc3ef529a749b0cbb54a2dab2fa1f",
    },
    "base_evaluation_corpus": {
        "path": REPORTS_ROOT
        / "combat_rl_guard_advantage_expanded_corpus_20260829_r1"
        / "evaluation_corpus.pt",
        "sha256": "028d51871b12fd509b87b6d45adb161b399a29c34782b30b28f66c0a97e48e58",
    },
    "base_corpus_report": {
        "path": REPORTS_ROOT
        / "combat_rl_guard_advantage_expanded_corpus_20260829_r1"
        / "report.json",
        "sha256": "5993832214c60dbfd275f7dc10109fb127454f8a989aedec20252693c4077325",
    },
    "real_r14_replay": {
        "path": REPORTS_ROOT
        / "combat_rl_parent_on_policy_replay_collection_20260818_r14"
        / "rl_combat_model_ep20_steps3765.pth",
        "sha256": "eed11099d1b8d35baa8ce0ccbf87efb6fb4a864e6fe6246837b0cac91c505014",
    },
    "real_r15_replay": {
        "path": REPORTS_ROOT
        / "combat_rl_parent_on_policy_replay_collection_20260818_r15"
        / "rl_combat_model_ep20_steps3920.pth",
        "sha256": "67c3a49fbb2094d20793214c0a4a294684054eb6f4a24ac59573fab29c39a2dd",
    },
}

TENSOR_NAMES = (
    "continuous",
    "card_ids",
    "potion_ids",
    "relic_ids",
    "action_masks",
    "guard_actions",
    "target_actions",
    "advantages",
    "positive",
)


def canonical_json_bytes(value: Mapping[str, Any]) -> bytes:
    return (
        json.dumps(value, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True)
        + "\n"
    ).encode("ascii")


def _validate_sha256(value: Any, *, label: str) -> str:
    if not isinstance(value, str):
        raise ValueError(f"{label} SHA-256 is missing")
    normalized = value.lower()
    if len(normalized) != 64 or any(
        character not in "0123456789abcdef" for character in normalized
    ):
        raise ValueError(f"{label} SHA-256 is invalid")
    return normalized


def _validate_commit(value: Any) -> str:
    if not isinstance(value, str) or len(value) != 40 or any(
        character not in "0123456789abcdef" for character in value.lower()
    ):
        raise ValueError("source commit is invalid")
    return value.lower()


def _seed_set(values: Iterable[int], *, label: str) -> set[int]:
    result = {int(value) for value in values}
    if not result:
        raise ValueError(f"{label} seed partition is empty")
    return result


def validate_seed_isolation(
    *,
    base_train: Iterable[int],
    base_evaluation: Iterable[int],
    supplement_train: Iterable[int],
    supplement_evaluation: Iterable[int],
) -> None:
    partitions = {
        "base_train": _seed_set(base_train, label="base train"),
        "base_evaluation": _seed_set(base_evaluation, label="base evaluation"),
        "supplement_train": _seed_set(supplement_train, label="supplement train"),
        "supplement_evaluation": _seed_set(
            supplement_evaluation, label="supplement evaluation"
        ),
    }
    names = list(partitions)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            overlap = partitions[left].intersection(partitions[right])
            if overlap:
                raise ValueError(
                    f"seed partitions overlap: {left} and {right}: {sorted(overlap)[:5]}"
                )


def _normalized_corpus(corpus: Mapping[str, Any]) -> dict[str, Any]:
    tensors = corpus.get("tensors")
    metadata = corpus.get("metadata")
    if not isinstance(tensors, Mapping) or set(tensors) != set(TENSOR_NAMES):
        raise ValueError("corpus tensor inventory differs")
    if not isinstance(metadata, list):
        raise ValueError("corpus metadata is invalid")
    normalized_tensors = {
        name: torch.as_tensor(tensors[name]).detach().cpu() for name in TENSOR_NAMES
    }
    row_count = int(corpus.get("row_count", normalized_tensors["positive"].numel()))
    return {
        "partition": str(corpus.get("partition", "")),
        "tensors": normalized_tensors,
        "metadata": [copy.deepcopy(dict(row)) for row in metadata],
        "row_count": row_count,
    }


def validate_corpus(
    corpus: Mapping[str, Any],
    *,
    expected_partition: str,
    require_both_classes: bool = True,
) -> dict[str, Any]:
    normalized = _normalized_corpus(corpus)
    if normalized["partition"] != expected_partition:
        raise ValueError("corpus partition differs")
    tensors = normalized["tensors"]
    count = normalized["row_count"]
    if count <= 0 or len(normalized["metadata"]) != count:
        raise ValueError("corpus row counts differ")
    if any(value.shape[0] != count for value in tensors.values()):
        raise ValueError("corpus tensor row counts differ")
    if tensors["continuous"].ndim != 2 or tensors["action_masks"].ndim != 2:
        raise ValueError("corpus tensor dimensions differ")
    for name in ("continuous", "advantages"):
        if not bool(torch.isfinite(tensors[name]).all()):
            raise ValueError(f"corpus {name} values are not finite")
    action_masks = tensors["action_masks"].bool()
    guard_actions = tensors["guard_actions"].long().reshape(-1)
    target_actions = tensors["target_actions"].long().reshape(-1)
    action_dim = int(action_masks.shape[1])
    if bool((guard_actions < 0).any()) or bool((guard_actions >= action_dim).any()):
        raise ValueError("corpus guard action is illegal")
    if bool((target_actions < 0).any()) or bool((target_actions >= action_dim).any()):
        raise ValueError("corpus target action is illegal")
    rows = torch.arange(count)
    if not bool(action_masks[rows, guard_actions].all()):
        raise ValueError("corpus guard action is illegal")
    if not bool(action_masks[rows, target_actions].all()):
        raise ValueError("corpus target action is illegal")
    positive = tensors["positive"].bool().reshape(-1)
    if require_both_classes and (
        not bool(positive.any()) or not bool((~positive).any())
    ):
        raise ValueError("corpus requires both label classes")
    for index, row in enumerate(normalized["metadata"]):
        if not isinstance(row.get("seed"), int) or not isinstance(row.get("floor"), int):
            raise ValueError("corpus metadata seed or floor is invalid")
        for key, tensor in (
            ("guard_action_index", guard_actions),
            ("target_action_index", target_actions),
        ):
            if key in row and int(row[key]) != int(tensor[index]):
                raise ValueError(f"corpus metadata {key} is misaligned")
    normalized["tensors"]["action_masks"] = action_masks
    normalized["tensors"]["guard_actions"] = guard_actions
    normalized["tensors"]["target_actions"] = target_actions
    normalized["tensors"]["positive"] = positive
    normalized["tensors"]["advantages"] = tensors["advantages"].float().reshape(-1)
    return normalized


def _select_rows(corpus: Mapping[str, Any], indices: torch.Tensor) -> dict[str, Any]:
    values = validate_corpus(
        corpus,
        expected_partition=str(corpus.get("partition", "")),
        require_both_classes=False,
    )
    selected = indices.long().reshape(-1)
    return {
        "partition": values["partition"],
        "tensors": {
            name: tensor.index_select(0, selected) for name, tensor in values["tensors"].items()
        },
        "metadata": [copy.deepcopy(values["metadata"][int(index)]) for index in selected],
        "row_count": int(selected.numel()),
    }


def filter_supplement_corpus(
    corpus: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    values = validate_corpus(
        corpus,
        expected_partition=str(corpus.get("partition", "")),
        require_both_classes=False,
    )
    first = int(FIXED_RECIPE["target_floor_first"])
    last = int(FIXED_RECIPE["target_floor_last"])
    kept: list[int] = []
    exclusions: Counter[str] = Counter()
    for index, row in enumerate(values["metadata"]):
        floor = int(row["floor"])
        if floor < first:
            exclusions["below_target_floor"] += 1
        elif floor > last:
            exclusions["above_target_floor"] += 1
        else:
            kept.append(index)
    if not kept:
        raise ValueError("supplement contains no target-floor rows")
    selected = _select_rows(values, torch.tensor(kept, dtype=torch.long))
    return selected, dict(sorted(exclusions.items()))


def combine_corpora(
    base: Mapping[str, Any],
    supplement: Mapping[str, Any],
    *,
    partition: str,
) -> dict[str, Any]:
    left = validate_corpus(base, expected_partition=partition)
    right = validate_corpus(
        supplement, expected_partition=partition, require_both_classes=False
    )
    for name in TENSOR_NAMES:
        if left["tensors"][name].shape[1:] != right["tensors"][name].shape[1:]:
            raise ValueError(f"corpus tensor shape differs: {name}")
    metadata = []
    for source, rows in (
        ("expanded_base", left["metadata"]),
        ("late_supplement", right["metadata"]),
    ):
        for raw in rows:
            row = copy.deepcopy(raw)
            if "source_component" in row:
                raise ValueError("corpus metadata already contains source_component")
            row["source_component"] = source
            metadata.append(row)
    combined = {
        "partition": partition,
        "tensors": {
            name: torch.cat((left["tensors"][name], right["tensors"][name]), dim=0)
            for name in TENSOR_NAMES
        },
        "metadata": metadata,
        "row_count": left["row_count"] + right["row_count"],
    }
    return validate_corpus(combined, expected_partition=partition)


def _context_tensors(batch: Mapping[str, Any] | TransitionBatch) -> dict[str, torch.Tensor]:
    if isinstance(batch, TransitionBatch):
        return {
            "continuous": torch.as_tensor(batch.continuous),
            "potion_ids": torch.as_tensor(batch.potion_ids),
            "relic_ids": torch.as_tensor(batch.relic_ids),
        }
    tensors = batch.get("tensors") if isinstance(batch, Mapping) else None
    if not isinstance(tensors, Mapping):
        raise ValueError("context batch tensors are missing")
    required = ("continuous", "potion_ids", "relic_ids")
    result = {name: torch.as_tensor(tensors[name]).detach().cpu() for name in required}
    count = int(result["continuous"].shape[0])
    if count <= 0 or any(value.shape[0] != count for value in result.values()):
        raise ValueError("context batch row counts differ")
    if not bool(torch.isfinite(result["continuous"]).all()):
        raise ValueError("context batch continuous values are not finite")
    return result


def _context_rows(batch: Mapping[str, Any] | TransitionBatch) -> dict[str, Any]:
    tensors = _context_tensors(batch)
    continuous = tensors["continuous"].double()
    floor_ratio = continuous[:, 3]
    hp_ratio = continuous[:, SEMANTIC_CONTINUOUS_INDICES["player_hp_ratio"]]
    if bool((hp_ratio < 0.0).any()) or bool((hp_ratio > 1.0).any()):
        raise ValueError("context player HP ratio is outside [0, 1]")
    strata = [floor_stratum(float(value)) for value in floor_ratio]
    potion = (tensors["potion_ids"] != 0).sum(dim=1).long()
    relic = (tensors["relic_ids"] != 0).sum(dim=1).long()
    hp_quartile = torch.clamp((hp_ratio * 4.0).long(), min=0, max=3)
    cells = [
        (strata[index], int(potion[index]), int(relic[index]), int(hp_quartile[index]))
        for index in range(len(strata))
    ]
    return {
        "cells": cells,
        "cell_ids": [_cell_id(cell) for cell in cells],
        "floor_ratio": floor_ratio,
        "player_hp_ratio": hp_ratio,
        "potion_occupied_slots": potion.double(),
        "relic_occupied_slots": relic.double(),
    }


def _cell_id(cell: tuple[str, int, int, int]) -> str:
    return f"{cell[0]}|p{cell[1]}|r{cell[2]}|h{cell[3]}"


def _smd(
    real: torch.Tensor,
    simulator: torch.Tensor,
    *,
    weights: torch.Tensor | None,
) -> float | None:
    real_values = real.double()
    simulator_values = simulator.double()
    real_mean = float(real_values.mean())
    real_std = float(real_values.std(unbiased=False))
    if weights is None:
        simulator_mean = float(simulator_values.mean())
        simulator_std = float(simulator_values.std(unbiased=False))
    else:
        simulator_mean = float((simulator_values * weights).sum())
        simulator_std = math.sqrt(
            float((weights * (simulator_values - simulator_mean).square()).sum())
        )
    pooled = math.sqrt((real_std * real_std + simulator_std * simulator_std) / 2.0)
    delta = abs(simulator_mean - real_mean)
    if pooled <= 1e-12:
        return 0.0 if delta <= 1e-12 else None
    return delta / pooled


def derive_context_weights(
    real: Mapping[str, Any] | TransitionBatch,
    simulator: Mapping[str, Any] | TransitionBatch,
) -> dict[str, Any]:
    real_rows = _context_rows(real)
    simulator_rows = _context_rows(simulator)
    real_counts = Counter(real_rows["cells"])
    simulator_counts = Counter(simulator_rows["cells"])
    common = set(real_counts).intersection(simulator_counts)
    if not common:
        raise ValueError("real and simulator context support do not overlap")
    real_total = len(real_rows["cells"])
    simulator_total = len(simulator_rows["cells"])
    raw_weights = torch.tensor(
        [
            (real_counts[cell] / real_total) / (simulator_counts[cell] / simulator_total)
            if cell in common
            else 0.0
            for cell in simulator_rows["cells"]
        ],
        dtype=torch.float64,
    )
    weight_sum = float(raw_weights.sum())
    if not math.isfinite(weight_sum) or weight_sum <= 0.0:
        raise ValueError("context weights cannot be normalized")
    weights = raw_weights / weight_sum
    if not bool(torch.isfinite(weights).all()) or bool((weights < 0.0).any()):
        raise ValueError("context weights are invalid")

    floor_coverage: dict[str, float | None] = {}
    for stratum in ("floor_23_27", "floor_28_34"):
        denominator = sum(count for cell, count in real_counts.items() if cell[0] == stratum)
        numerator = sum(
            count for cell, count in real_counts.items() if cell[0] == stratum and cell in common
        )
        floor_coverage[stratum] = (
            numerator / denominator if denominator else None
        )
    smds = {
        name: {
            "raw": _smd(real_rows[name], simulator_rows[name], weights=None),
            "weighted": _smd(real_rows[name], simulator_rows[name], weights=weights),
        }
        for name in (
            "floor_ratio",
            "player_hp_ratio",
            "potion_occupied_slots",
            "relic_occupied_slots",
        )
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
        "simulator_mass_retained": sum(simulator_counts[cell] for cell in common)
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
        "cell_ids": simulator_rows["cell_ids"],
        "matched_cell_ids": sorted(_cell_id(cell) for cell in common),
        "metrics": metrics,
    }


def _at_least(value: Any, threshold: float) -> bool:
    return value is not None and math.isfinite(float(value)) and float(value) >= threshold


def _at_most(value: Any, threshold: float) -> bool:
    return value is not None and math.isfinite(float(value)) and float(value) <= threshold


def apply_support_gates(
    *,
    train_metrics: Mapping[str, Any],
    evaluation_metrics: Mapping[str, Any],
    evaluation_late_floor_rows: int,
    integrity_conditions: Mapping[str, bool],
) -> dict[str, Any]:
    train_smd = train_metrics["standardized_mean_differences"]
    evaluation_smd = evaluation_metrics["standardized_mean_differences"]
    conditions = {
        "evaluation_late_floor_rows": int(evaluation_late_floor_rows)
        >= FIXED_GATES["evaluation_late_floor_rows_minimum"],
        "train_real_context_mass_covered": _at_least(
            train_metrics["real_context_mass_covered"],
            FIXED_GATES["real_context_mass_covered_minimum"],
        ),
        "evaluation_real_context_mass_covered": _at_least(
            evaluation_metrics["real_context_mass_covered"],
            FIXED_GATES["real_context_mass_covered_minimum"],
        ),
        "train_floor_23_27_context_mass_covered": _at_least(
            train_metrics["floor_context_mass_covered"]["floor_23_27"],
            FIXED_GATES["floor_23_27_context_mass_covered_minimum"],
        ),
        "evaluation_floor_23_27_context_mass_covered": _at_least(
            evaluation_metrics["floor_context_mass_covered"]["floor_23_27"],
            FIXED_GATES["floor_23_27_context_mass_covered_minimum"],
        ),
        "train_floor_28_34_context_mass_covered": _at_least(
            train_metrics["floor_context_mass_covered"]["floor_28_34"],
            FIXED_GATES["floor_28_34_context_mass_covered_minimum"],
        ),
        "evaluation_floor_28_34_context_mass_covered": _at_least(
            evaluation_metrics["floor_context_mass_covered"]["floor_28_34"],
            FIXED_GATES["floor_28_34_context_mass_covered_minimum"],
        ),
        "train_effective_sample_size": _at_least(
            train_metrics["effective_sample_size"],
            FIXED_GATES["train_effective_sample_size_minimum"],
        ),
        "evaluation_effective_sample_size": _at_least(
            evaluation_metrics["effective_sample_size"],
            FIXED_GATES["evaluation_effective_sample_size_minimum"],
        ),
        "train_maximum_normalized_weight": _at_most(
            train_metrics["maximum_normalized_weight"],
            FIXED_GATES["maximum_normalized_weight_maximum"],
        ),
        "evaluation_maximum_normalized_weight": _at_most(
            evaluation_metrics["maximum_normalized_weight"],
            FIXED_GATES["maximum_normalized_weight_maximum"],
        ),
    }
    for prefix, smds in (("train", train_smd), ("evaluation", evaluation_smd)):
        for metric in (
            "player_hp_ratio",
            "potion_occupied_slots",
            "relic_occupied_slots",
            "floor_ratio",
        ):
            conditions[f"{prefix}_{metric}_weighted_smd"] = _at_most(
                smds[metric]["weighted"],
                FIXED_GATES[f"{metric}_weighted_smd_maximum"],
            )
    for name, value in sorted(integrity_conditions.items()):
        conditions[f"integrity_{name}"] = value is True
    passed = all(conditions.values())
    return {
        "conditions": conditions,
        "passed": passed,
        "decision": (
            "corpus_support_ready_for_separate_weighted_fit"
            if passed
            else "corpus_support_insufficient_close_without_fit"
        ),
    }


def ensure_output_paths_absent(output: Path, staging: Path) -> None:
    if output.exists():
        raise ValueError(f"output already exists: {output}")
    if staging.exists():
        raise ValueError(f"staging output already exists: {staging}")


def _binding(path: Path, sha256: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha256.lower()}


def build_registration(source_commit: str) -> dict[str, Any]:
    commit = _validate_commit(source_commit)
    source_files = {
        relative: sha256_file(REPO_ROOT / relative) for relative in SOURCE_SNAPSHOT_PATHS
    }
    return {
        "schema_version": REGISTRATION_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": commit,
        "interpreter": str(EXPECTED_INTERPRETER.resolve()),
        "runner": _binding(
            Path(__file__), source_files[SOURCE_SNAPSHOT_PATHS[0]]
        ),
        "source_files": source_files,
        "inputs": {
            name: _binding(value["path"], value["sha256"])
            for name, value in sorted(FIXED_INPUTS.items())
        },
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "gates": copy.deepcopy(FIXED_GATES),
        "output_dir": str(OUTPUT_DIR.resolve()),
        "authority": copy.deepcopy(AUTHORITY),
    }


def validate_registration(value: Mapping[str, Any]) -> dict[str, Any]:
    required = {
        "schema_version",
        "experiment_id",
        "source_commit",
        "interpreter",
        "runner",
        "source_files",
        "inputs",
        "recipe",
        "gates",
        "output_dir",
        "authority",
    }
    if not isinstance(value, Mapping) or set(value) != required:
        raise ValueError("registration root keys differ")
    if value["schema_version"] != REGISTRATION_SCHEMA:
        raise ValueError("registration schema differs")
    if value["experiment_id"] != EXPERIMENT_ID:
        raise ValueError("registration experiment differs")
    source_commit = _validate_commit(value["source_commit"])
    if Path(str(value["interpreter"])).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("registration interpreter differs")
    source_files = value["source_files"]
    if not isinstance(source_files, Mapping) or set(source_files) != set(
        SOURCE_SNAPSHOT_PATHS
    ):
        raise ValueError("registration source inventory differs")
    normalized_sources = {
        path: _validate_sha256(sha, label=f"source {path}")
        for path, sha in source_files.items()
    }
    runner = value["runner"]
    if not isinstance(runner, Mapping) or set(runner) != {"path", "sha256"}:
        raise ValueError("registration runner binding differs")
    if Path(str(runner["path"])).resolve() != Path(__file__).resolve():
        raise ValueError("registration runner path differs")
    runner_sha = _validate_sha256(runner["sha256"], label="runner")
    if runner_sha != normalized_sources[SOURCE_SNAPSHOT_PATHS[0]]:
        raise ValueError("registration runner hash differs from source inventory")
    inputs = value["inputs"]
    if not isinstance(inputs, Mapping) or set(inputs) != set(FIXED_INPUTS):
        raise ValueError("registration input inventory differs")
    normalized_inputs: dict[str, dict[str, str]] = {}
    for name, expected in FIXED_INPUTS.items():
        binding = inputs[name]
        if not isinstance(binding, Mapping) or set(binding) != {"path", "sha256"}:
            raise ValueError(f"registration input binding differs: {name}")
        if Path(str(binding["path"])).resolve() != expected["path"].resolve():
            raise ValueError(f"registration input path differs: {name}")
        digest = _validate_sha256(binding["sha256"], label=name)
        if digest != expected["sha256"]:
            raise ValueError(f"registration input hash differs: {name}")
        normalized_inputs[name] = _binding(expected["path"], digest)
    if value["recipe"] != FIXED_RECIPE:
        raise ValueError("registration recipe differs")
    if value["gates"] != FIXED_GATES:
        raise ValueError("registration gates differ")
    if Path(str(value["output_dir"])).resolve() != OUTPUT_DIR.resolve():
        raise ValueError("registration output path differs")
    if value["authority"] != AUTHORITY:
        raise ValueError("registration authority differs")
    return {
        "schema_version": REGISTRATION_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": source_commit,
        "interpreter": str(EXPECTED_INTERPRETER.resolve()),
        "runner": _binding(Path(__file__), runner_sha),
        "source_files": normalized_sources,
        "inputs": normalized_inputs,
        "recipe": copy.deepcopy(FIXED_RECIPE),
        "gates": copy.deepcopy(FIXED_GATES),
        "output_dir": str(OUTPUT_DIR.resolve()),
        "authority": copy.deepcopy(AUTHORITY),
    }


def _git_bytes(commit: str, relative: str) -> bytes:
    return subprocess.check_output(
        ["git", "show", f"{commit}:{relative}"], cwd=REPO_ROOT
    )


def preflight_registration(registration: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_registration(registration)
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("preflight interpreter differs")
    ensure_output_paths_absent(OUTPUT_DIR, STAGING_DIR)
    current = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True
    ).strip()
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", normalized["source_commit"], current],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("registered source commit is not an ancestor of HEAD")
    for relative, expected in normalized["source_files"].items():
        current_path = REPO_ROOT / relative
        if sha256_file(current_path) != expected:
            raise ValueError(f"source file hash differs: {relative}")
        committed = hashlib.sha256(_git_bytes(normalized["source_commit"], relative)).hexdigest()
        if committed != expected:
            raise ValueError(f"committed source file hash differs: {relative}")
    input_evidence = {}
    for name, binding in normalized["inputs"].items():
        path = Path(binding["path"])
        if not path.is_file():
            raise ValueError(f"registered input is missing: {name}")
        actual = sha256_file(path)
        if actual != binding["sha256"]:
            raise ValueError(f"registered input hash differs: {name}")
        input_evidence[name] = {
            **binding,
            "size_bytes": path.stat().st_size,
        }
    validate_seed_isolation(
        base_train=range(264000, 265024),
        base_evaluation=range(266000, 266256),
        supplement_train=range(
            FIXED_RECIPE["train_seed_first"], FIXED_RECIPE["train_seed_last"] + 1
        ),
        supplement_evaluation=range(
            FIXED_RECIPE["evaluation_seed_first"],
            FIXED_RECIPE["evaluation_seed_last"] + 1,
        ),
    )
    return {
        "schema_version": "combat-rl-real-context-balanced-corpus-preflight-v1",
        "verdict": "source_only_preflight_passed",
        "source_commit": normalized["source_commit"],
        "head_commit": current,
        "output_absent": True,
        "staging_absent": True,
        "native_loaded": False,
        "model_fitted": False,
        "game_started": False,
        "inputs": input_evidence,
    }


def _loaded_corpus(path: Path, partition: str) -> dict[str, Any]:
    value = load_corpus(path, expected_partition=partition)
    return {
        "partition": partition,
        "tensors": {name: value["tensors"][name] for name in TENSOR_NAMES},
        "metadata": value["metadata"],
        "row_count": value["row_count"],
    }


def _corpus_payload(corpus: Mapping[str, Any], *, partition: str) -> dict[str, Any]:
    validated = validate_corpus(corpus, expected_partition=partition)
    return {
        "schema_version": 1,
        "corpus_kind": CORPUS_KIND,
        "partition": partition,
        "tensors": validated["tensors"],
        "metadata": validated["metadata"],
    }


def _partition_summary(corpus: Mapping[str, Any]) -> dict[str, Any]:
    values = validate_corpus(
        corpus, expected_partition=str(corpus["partition"])
    )
    floors = Counter(int(row["floor"]) for row in values["metadata"])
    strata = Counter(
        floor_stratum(float(value)) for value in values["tensors"]["continuous"][:, 3]
    )
    sources = Counter(row.get("source_component", "unbound") for row in values["metadata"])
    encounters = Counter(str(row.get("encounter", "unknown")) for row in values["metadata"])
    seeds = {int(row["seed"]) for row in values["metadata"]}
    return {
        "row_count": values["row_count"],
        "positive_count": int(values["tensors"]["positive"].sum()),
        "negative_count": int((~values["tensors"]["positive"]).sum()),
        "seed_count": len(seeds),
        "floor_counts": {str(key): value for key, value in sorted(floors.items())},
        "floor_stratum_counts": dict(sorted(strata.items())),
        "source_component_counts": dict(sorted(sources.items())),
        "encounter_counts": dict(sorted(encounters.items())),
    }


def _integrity_conditions(
    train: Mapping[str, Any], evaluation: Mapping[str, Any]
) -> dict[str, bool]:
    train_value = validate_corpus(train, expected_partition="train")
    evaluation_value = validate_corpus(evaluation, expected_partition="evaluation")
    train_seeds = {int(row["seed"]) for row in train_value["metadata"]}
    evaluation_seeds = {int(row["seed"]) for row in evaluation_value["metadata"]}
    finite = all(
        bool(torch.isfinite(value["tensors"]["continuous"]).all())
        and bool(torch.isfinite(value["tensors"]["advantages"]).all())
        for value in (train_value, evaluation_value)
    )
    return {
        "class_complete": all(
            bool(value["tensors"]["positive"].any())
            and bool((~value["tensors"]["positive"]).any())
            for value in (train_value, evaluation_value)
        ),
        "finite": finite,
        "legal": True,
        "provenance": True,
        "seed_isolation": not bool(train_seeds.intersection(evaluation_seeds)),
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    train = report["combined"]["train"]
    evaluation = report["combined"]["evaluation"]
    return "\n".join(
        (
            "# Real-context-balanced guard corpus",
            "",
            f"- Decision: `{report['support_gate']['decision']}`",
            f"- Train rows: `{train['row_count']}`",
            f"- Fresh evaluation rows: `{evaluation['row_count']}`",
            f"- Fresh evaluation floor 23..34 rows: `{report['evaluation_late_floor_rows']}`",
            f"- Train ESS: `{report['context_support']['train']['effective_sample_size']:.3f}`",
            f"- Fresh evaluation ESS: `{report['context_support']['evaluation']['effective_sample_size']:.3f}`",
            "",
            "This artifact grants corpus-support evidence only. It does not grant",
            "training, gameplay, qualification, promotion, or production authority.",
            "",
        )
    )


def _publish(
    *,
    report: Mapping[str, Any],
    train: Mapping[str, Any],
    evaluation: Mapping[str, Any],
    train_weights: Mapping[str, Any],
    evaluation_weights: Mapping[str, Any],
    registration: Mapping[str, Any],
) -> None:
    ensure_output_paths_absent(OUTPUT_DIR, STAGING_DIR)
    STAGING_DIR.mkdir(parents=False)
    try:
        torch.save(_corpus_payload(train, partition="train"), STAGING_DIR / "train_corpus.pt")
        torch.save(
            _corpus_payload(evaluation, partition="evaluation"),
            STAGING_DIR / "evaluation_corpus.pt",
        )
        torch.save(
            {
                "schema_version": WEIGHTS_SCHEMA,
                "train": {
                    "weights": train_weights["weights"],
                    "cell_ids": train_weights["cell_ids"],
                    "matched_cell_ids": train_weights["matched_cell_ids"],
                    "metrics": train_weights["metrics"],
                },
                "evaluation": {
                    "weights": evaluation_weights["weights"],
                    "cell_ids": evaluation_weights["cell_ids"],
                    "matched_cell_ids": evaluation_weights["matched_cell_ids"],
                    "metrics": evaluation_weights["metrics"],
                },
            },
            STAGING_DIR / "context_weights.pt",
        )
        (STAGING_DIR / "report.json").write_bytes(canonical_json_bytes(report))
        (STAGING_DIR / "summary.md").write_text(
            _render_summary(report), encoding="ascii", newline="\n"
        )
        (STAGING_DIR / "registration.json").write_bytes(
            canonical_json_bytes(registration)
        )
        snapshot_root = STAGING_DIR / "source_snapshot"
        for relative in SOURCE_SNAPSHOT_PATHS:
            destination = snapshot_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO_ROOT / relative, destination)
        artifacts = {}
        for path in sorted(STAGING_DIR.rglob("*")):
            if path.is_file() and path.name != "manifest.json":
                relative = path.relative_to(STAGING_DIR).as_posix()
                artifacts[relative] = {
                    "sha256": sha256_file(path),
                    "size_bytes": path.stat().st_size,
                }
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "experiment_id": EXPERIMENT_ID,
            "source_commit": registration["source_commit"],
            "decision": report["support_gate"]["decision"],
            "artifacts": artifacts,
        }
        (STAGING_DIR / "manifest.json").write_bytes(canonical_json_bytes(manifest))
        os.replace(STAGING_DIR, OUTPUT_DIR)
    except BaseException:
        if STAGING_DIR.exists():
            shutil.rmtree(STAGING_DIR)
        raise


def run_registered(registration: Mapping[str, Any]) -> dict[str, Any]:
    started = time.monotonic()
    normalized = validate_registration(registration)
    preflight = preflight_registration(normalized)
    inputs = {name: Path(binding["path"]) for name, binding in normalized["inputs"].items()}

    real, real_evidence = load_real_replay_bindings(
        (
            RealReplayBinding(
                label="r14",
                path=inputs["real_r14_replay"],
                sha256=normalized["inputs"]["real_r14_replay"]["sha256"],
            ),
            RealReplayBinding(
                label="r15",
                path=inputs["real_r15_replay"],
                sha256=normalized["inputs"]["real_r15_replay"]["sha256"],
            ),
        )
    )
    base_train = _loaded_corpus(inputs["base_train_corpus"], "train")
    base_evaluation = _loaded_corpus(inputs["base_evaluation_corpus"], "evaluation")

    native_module = load_native_module(inputs["native_module"])
    id_mapper = build_id_mapper(inputs["items_json"])
    initial = load_initial_checkpoint(
        inputs["initial_checkpoint"],
        expected_sha256=normalized["inputs"]["initial_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        id_mapper,
        seed=2026082941,
        batch_size=128,
        learning_starts=128,
    )
    parent_state, initialization = initialize_trainer(trainer, initial)
    config = CorpusConfig(
        train_seeds=tuple(
            range(FIXED_RECIPE["train_seed_first"], FIXED_RECIPE["train_seed_last"] + 1)
        ),
        evaluation_seeds=tuple(
            range(
                FIXED_RECIPE["evaluation_seed_first"],
                FIXED_RECIPE["evaluation_seed_last"] + 1,
            )
        ),
        battle_indices=tuple(FIXED_RECIPE["battle_indices"]),
        max_source_decisions=FIXED_RECIPE["max_source_decisions"],
        max_actions_per_turn=FIXED_RECIPE["max_actions_per_turn"],
        max_states_per_profile=FIXED_RECIPE["max_states_per_profile"],
        max_canonical_actions=FIXED_RECIPE["max_canonical_actions"],
        continuation_decisions=FIXED_RECIPE["continuation_decisions"],
        return_discount=FIXED_RECIPE["return_discount"],
        positive_advantage_margin=FIXED_RECIPE["positive_advantage_margin"],
    )
    supplement_train_raw, supplement_train_summary = collect_partition(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        seeds=config.train_seeds,
        config=config,
    )
    supplement_evaluation_raw, supplement_evaluation_summary = collect_partition(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        seeds=config.evaluation_seeds,
        config=config,
    )
    if parameter_sha256(trainer.online_network.state_dict()) != parameter_sha256(parent_state):
        raise ValueError("parent parameters changed during corpus collection")
    supplement_train = {
        "partition": "train",
        **supplement_train_raw,
        "row_count": len(supplement_train_raw["metadata"]),
    }
    supplement_evaluation = {
        "partition": "evaluation",
        **supplement_evaluation_raw,
        "row_count": len(supplement_evaluation_raw["metadata"]),
    }
    filtered_train, train_exclusions = filter_supplement_corpus(supplement_train)
    filtered_evaluation, evaluation_exclusions = filter_supplement_corpus(
        supplement_evaluation
    )
    combined_train = combine_corpora(base_train, filtered_train, partition="train")
    combined_evaluation = combine_corpora(
        base_evaluation, filtered_evaluation, partition="evaluation"
    )
    train_weights = derive_context_weights(real, combined_train)
    evaluation_weights = derive_context_weights(real, combined_evaluation)
    integrity = _integrity_conditions(combined_train, combined_evaluation)
    evaluation_late_floor_rows = sum(
        23 <= int(row["floor"]) <= 34 for row in combined_evaluation["metadata"]
    )
    support_gate = apply_support_gates(
        train_metrics=train_weights["metrics"],
        evaluation_metrics=evaluation_weights["metrics"],
        evaluation_late_floor_rows=evaluation_late_floor_rows,
        integrity_conditions=integrity,
    )
    provenance = collect_provenance(
        repo_root=REPO_ROOT,
        simulator_repo=SIMULATOR_REPO,
        module_path=inputs["native_module"],
        native_module=native_module,
    )
    report = {
        "schema_version": REPORT_SCHEMA,
        "experiment_id": EXPERIMENT_ID,
        "source_commit": normalized["source_commit"],
        "duration_seconds": time.monotonic() - started,
        "preflight": preflight,
        "bindings": normalized,
        "real_replay": {
            "transition_count": real.transition_count,
            "bindings": real_evidence,
        },
        "initialization": initialization,
        "supplement": {
            "train": supplement_train_summary,
            "evaluation": supplement_evaluation_summary,
            "target_floor_exclusions": {
                "train": train_exclusions,
                "evaluation": evaluation_exclusions,
            },
            "retained_target_floor_rows": {
                "train": filtered_train["row_count"],
                "evaluation": filtered_evaluation["row_count"],
            },
        },
        "combined": {
            "train": _partition_summary(combined_train),
            "evaluation": _partition_summary(combined_evaluation),
        },
        "context_support": {
            "train": train_weights["metrics"],
            "evaluation": evaluation_weights["metrics"],
        },
        "evaluation_late_floor_rows": evaluation_late_floor_rows,
        "integrity": integrity,
        "support_gate": support_gate,
        "provenance": provenance,
        "operations": {
            "native_loaded": True,
            "environment_constructed": True,
            "optimizer_steps": 0,
            "model_fitted": False,
            "training": False,
            "gameplay": False,
            "communication_mod": False,
        },
        "authority": copy.deepcopy(AUTHORITY),
    }
    _publish(
        report=report,
        train=combined_train,
        evaluation=combined_evaluation,
        train_weights=train_weights,
        evaluation_weights=evaluation_weights,
        registration=normalized,
    )
    return report


def _load_registration(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"registration is missing: {path}")
    return json.loads(path.read_text(encoding="ascii"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build-registration")
    build.add_argument("--source-commit", required=True)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--registration", type=Path, required=True)
    run = subparsers.add_parser("run")
    run.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build-registration":
        sys.stdout.buffer.write(canonical_json_bytes(build_registration(args.source_commit)))
        return 0
    registration = _load_registration(args.registration)
    if args.command == "preflight":
        sys.stdout.buffer.write(canonical_json_bytes(preflight_registration(registration)))
        return 0
    report = run_registered(registration)
    print(
        json.dumps(
            {
                "output_dir": str(OUTPUT_DIR.resolve()),
                "decision": report["support_gate"]["decision"],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
