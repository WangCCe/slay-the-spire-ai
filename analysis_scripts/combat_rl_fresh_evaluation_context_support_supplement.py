"""Add one fresh early/mid evaluation supplement to a bound guard corpus."""

from __future__ import annotations

import argparse
from collections import Counter
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Iterable, Mapping

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts import combat_rl_real_context_balanced_corpus as balanced  # noqa: E402
from analysis_scripts.combat_lightspeed_bridge import load_native_module  # noqa: E402
from analysis_scripts.combat_lightspeed_replay_distribution_calibration import (  # noqa: E402
    RealReplayBinding,
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
from spirecomm.ai.rl.v2.id_mapping import build_id_mapper  # noqa: E402


REGISTRATION_SCHEMA = "combat-rl-fresh-evaluation-context-support-registration-v1"
REPORT_SCHEMA = "combat-rl-fresh-evaluation-context-support-report-v1"
WEIGHTS_SCHEMA = "combat-rl-fresh-evaluation-context-weights-v1"
MANIFEST_SCHEMA = "combat-rl-fresh-evaluation-context-support-manifest-v1"
EXPERIMENT_ID = "combat-rl-fresh-evaluation-context-support-supplement-20260829-r1"
EXPECTED_INTERPRETER = Path(r"D:\anaconda\envs\stsai\python.exe")
OUTPUT_DIR = REPORTS_ROOT / EXPERIMENT_ID.replace("-", "_")
STAGING_DIR = REPORTS_ROOT / f".{OUTPUT_DIR.name}.staging"
SIMULATOR_REPO = Path(r"D:\CLionProjects\sts_lightspeed")

FIXED_RECIPE = {
    "evaluation_seed_first": 271000,
    "evaluation_seed_last": 272023,
    "battle_indices": [0, 3, 6, 9],
    "target_floor_first": 0,
    "target_floor_last": 22,
    "max_source_decisions": 100,
    "max_actions_per_turn": 8,
    "max_states_per_profile": 2,
    "max_canonical_actions": 8,
    "continuation_decisions": 8,
    "return_discount": 0.99,
    "positive_advantage_margin": 0.5,
    "collect_training_partition": False,
    "context_cell": [
        "floor_stratum",
        "potion_occupied_slots",
        "relic_occupied_slots",
        "player_hp_quartile",
    ],
}

# Aliases intentionally preserve the archived gate and weighting implementation.
FIXED_GATES = copy.deepcopy(balanced.FIXED_GATES)
derive_context_weights = balanced.derive_context_weights
apply_support_gates = balanced.apply_support_gates

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
    "analysis_scripts/combat_rl_fresh_evaluation_context_support_supplement.py",
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

PRIOR_OUTPUT = REPORTS_ROOT / "combat_rl_real_context_balanced_corpus_20260829_r1"
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
    "prior_train_corpus": {
        "path": PRIOR_OUTPUT / "train_corpus.pt",
        "sha256": "af2c1d40f307eacee951333462ad5688e276f6006c8a6b0b5f5189b92845bbe2",
    },
    "prior_evaluation_corpus": {
        "path": PRIOR_OUTPUT / "evaluation_corpus.pt",
        "sha256": "0b74fe10cd62d4bddc2beb6bd942d7fd5e5d1b82881a73cc7dcc3a6dba1b8b74",
    },
    "prior_context_weights": {
        "path": PRIOR_OUTPUT / "context_weights.pt",
        "sha256": "07b3d4ca49becf7c5fd19da9cb088908b354fceda8c5983e9cf455c8d923b148",
    },
    "prior_report": {
        "path": PRIOR_OUTPUT / "report.json",
        "sha256": "85b92efa27a4896d160184b2666331a8413b08b000ee2b71faed3a9aa162cd85",
    },
    "prior_manifest": {
        "path": PRIOR_OUTPUT / "manifest.json",
        "sha256": "01e32c38a8e7db394b2b7e2d76d360cb664631c4fe2f31c7b4277de95e2db31d",
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

TENSOR_NAMES = balanced.TENSOR_NAMES


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


def _binding(path: Path, sha256: str) -> dict[str, str]:
    return {"path": str(path.resolve()), "sha256": sha256.lower()}


def _seed_set(values: Iterable[int], *, label: str) -> set[int]:
    result = {int(value) for value in values}
    if not result:
        raise ValueError(f"{label} seed partition is empty")
    return result


def validate_fresh_seed_isolation(
    *,
    prior_train_seeds: Iterable[int],
    prior_evaluation_seeds: Iterable[int],
    fresh_evaluation_seeds: Iterable[int],
) -> None:
    partitions = {
        "prior_train": _seed_set(prior_train_seeds, label="prior train"),
        "prior_evaluation": _seed_set(
            prior_evaluation_seeds, label="prior evaluation"
        ),
        "fresh_evaluation": _seed_set(
            fresh_evaluation_seeds, label="fresh evaluation"
        ),
    }
    names = list(partitions)
    for left_index, left in enumerate(names):
        for right in names[left_index + 1 :]:
            overlap = partitions[left].intersection(partitions[right])
            if overlap:
                raise ValueError(
                    f"seed partitions overlap: {left} and {right}: "
                    f"{sorted(overlap)[:5]}"
                )


def _select_rows(corpus: Mapping[str, Any], indices: torch.Tensor) -> dict[str, Any]:
    values = balanced.validate_corpus(
        corpus,
        expected_partition=str(corpus.get("partition", "")),
        require_both_classes=False,
    )
    selected = indices.long().reshape(-1)
    return {
        "partition": values["partition"],
        "tensors": {
            name: tensor.index_select(0, selected)
            for name, tensor in values["tensors"].items()
        },
        "metadata": [copy.deepcopy(values["metadata"][int(index)]) for index in selected],
        "row_count": int(selected.numel()),
    }


def filter_evaluation_supplement(
    corpus: Mapping[str, Any],
) -> tuple[dict[str, Any], dict[str, int]]:
    values = balanced.validate_corpus(
        corpus, expected_partition="evaluation", require_both_classes=False
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
        raise ValueError("fresh evaluation supplement contains no target-floor rows")
    return _select_rows(values, torch.tensor(kept, dtype=torch.long)), dict(
        sorted(exclusions.items())
    )


def append_evaluation_corpus(
    prior: Mapping[str, Any], supplement: Mapping[str, Any]
) -> dict[str, Any]:
    left = balanced.validate_corpus(prior, expected_partition="evaluation")
    right = balanced.validate_corpus(
        supplement, expected_partition="evaluation", require_both_classes=False
    )
    for name in TENSOR_NAMES:
        if left["tensors"][name].shape[1:] != right["tensors"][name].shape[1:]:
            raise ValueError(f"corpus tensor shape differs: {name}")
    new_metadata = []
    for raw in right["metadata"]:
        row = copy.deepcopy(raw)
        if "source_component" in row:
            raise ValueError("fresh corpus metadata already contains source_component")
        row["source_component"] = "early_mid_fresh_evaluation_supplement"
        new_metadata.append(row)
    combined = {
        "partition": "evaluation",
        "tensors": {
            name: torch.cat((left["tensors"][name], right["tensors"][name]), dim=0)
            for name in TENSOR_NAMES
        },
        "metadata": copy.deepcopy(left["metadata"]) + new_metadata,
        "row_count": left["row_count"] + right["row_count"],
    }
    return balanced.validate_corpus(combined, expected_partition="evaluation")


def copy_verified_file(source: Path, target: Path, *, expected_sha256: str) -> dict[str, Any]:
    expected = _validate_sha256(expected_sha256, label="copied file")
    if sha256_file(source) != expected:
        raise ValueError("source file hash differs before copy")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(source, target)
    actual = sha256_file(target)
    if actual != expected:
        raise ValueError("copied file hash differs")
    return {"sha256": actual, "size_bytes": target.stat().st_size}


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
        "runner": _binding(Path(__file__), source_files[SOURCE_SNAPSHOT_PATHS[0]]),
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
    normalized_inputs = {}
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
    return subprocess.check_output(["git", "show", f"{commit}:{relative}"], cwd=REPO_ROOT)


def _validate_prior_publication(inputs: Mapping[str, Mapping[str, str]]) -> dict[str, Any]:
    manifest = json.loads(Path(inputs["prior_manifest"]["path"]).read_text(encoding="ascii"))
    report = json.loads(Path(inputs["prior_report"]["path"]).read_text(encoding="ascii"))
    if manifest.get("experiment_id") != "combat-rl-real-context-balanced-corpus-20260829-r1":
        raise ValueError("prior manifest experiment differs")
    expected_artifacts = {
        "train_corpus.pt": inputs["prior_train_corpus"]["sha256"],
        "evaluation_corpus.pt": inputs["prior_evaluation_corpus"]["sha256"],
        "context_weights.pt": inputs["prior_context_weights"]["sha256"],
        "report.json": inputs["prior_report"]["sha256"],
    }
    artifacts = manifest.get("artifacts")
    if not isinstance(artifacts, Mapping):
        raise ValueError("prior manifest artifact inventory differs")
    for name, expected in expected_artifacts.items():
        if artifacts.get(name, {}).get("sha256") != expected:
            raise ValueError(f"prior manifest artifact differs: {name}")
    if report.get("bindings", {}).get("gates") != FIXED_GATES:
        raise ValueError("prior report gates differ")
    if report.get("support_gate", {}).get("decision") != (
        "corpus_support_insufficient_close_without_fit"
    ):
        raise ValueError("prior report decision differs")
    return {
        "experiment_id": manifest["experiment_id"],
        "source_commit": manifest["source_commit"],
        "decision": report["support_gate"]["decision"],
        "artifact_hashes_match": True,
        "gates_match": True,
    }


def preflight_registration(registration: Mapping[str, Any]) -> dict[str, Any]:
    normalized = validate_registration(registration)
    if Path(sys.executable).resolve() != EXPECTED_INTERPRETER.resolve():
        raise ValueError("preflight interpreter differs")
    balanced.ensure_output_paths_absent(OUTPUT_DIR, STAGING_DIR)
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
        if sha256_file(REPO_ROOT / relative) != expected:
            raise ValueError(f"source file hash differs: {relative}")
        committed = hashlib.sha256(
            _git_bytes(normalized["source_commit"], relative)
        ).hexdigest()
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
        input_evidence[name] = {**binding, "size_bytes": path.stat().st_size}
    prior = _validate_prior_publication(normalized["inputs"])
    validate_fresh_seed_isolation(
        prior_train_seeds=range(264000, 265024),
        prior_evaluation_seeds=(
            *range(266000, 266256),
            *range(270000, 270512),
        ),
        fresh_evaluation_seeds=range(
            FIXED_RECIPE["evaluation_seed_first"],
            FIXED_RECIPE["evaluation_seed_last"] + 1,
        ),
    )
    return {
        "schema_version": "combat-rl-fresh-evaluation-context-support-preflight-v1",
        "verdict": "source_only_preflight_passed",
        "source_commit": normalized["source_commit"],
        "head_commit": current,
        "output_absent": True,
        "staging_absent": True,
        "native_loaded": False,
        "model_loaded": False,
        "model_fitted": False,
        "game_started": False,
        "prior_publication": prior,
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
    validated = balanced.validate_corpus(corpus, expected_partition=partition)
    return {
        "schema_version": 1,
        "corpus_kind": CORPUS_KIND,
        "partition": partition,
        "tensors": validated["tensors"],
        "metadata": validated["metadata"],
    }


def _missing_context_cells(real: Any, simulator: Mapping[str, Any]) -> dict[str, Any]:
    real_rows = balanced._context_rows(real)
    simulator_rows = balanced._context_rows(simulator)
    real_counts = Counter(real_rows["cell_ids"])
    simulator_counts = Counter(simulator_rows["cell_ids"])
    total = sum(real_counts.values())
    missing = [
        {
            "cell_id": cell,
            "real_row_count": count,
            "real_context_mass": count / total,
            "simulator_row_count": simulator_counts.get(cell, 0),
        }
        for cell, count in real_counts.items()
        if not simulator_counts.get(cell, 0)
    ]
    missing.sort(key=lambda row: (-row["real_context_mass"], row["cell_id"]))
    by_stratum: Counter[str] = Counter()
    for row in missing:
        by_stratum[row["cell_id"].split("|", 1)[0]] += row["real_row_count"]
    return {
        "missing_real_context_mass": sum(row["real_context_mass"] for row in missing),
        "missing_cell_count": len(missing),
        "missing_real_mass_by_floor_stratum": {
            key: value / total for key, value in sorted(by_stratum.items())
        },
        "top_missing_cells": missing[:50],
    }


def _partition_summary(corpus: Mapping[str, Any]) -> dict[str, Any]:
    values = balanced.validate_corpus(
        corpus, expected_partition=str(corpus["partition"])
    )
    floors = Counter(int(row["floor"]) for row in values["metadata"])
    sources = Counter(row.get("source_component", "unbound") for row in values["metadata"])
    return {
        "row_count": values["row_count"],
        "positive_count": int(values["tensors"]["positive"].sum()),
        "negative_count": int((~values["tensors"]["positive"]).sum()),
        "seed_count": len({int(row["seed"]) for row in values["metadata"]}),
        "floor_counts": {str(key): value for key, value in sorted(floors.items())},
        "source_component_counts": dict(sorted(sources.items())),
    }


def _validate_train_weight_reproduction(path: Path, current: Mapping[str, Any]) -> None:
    prior = torch.load(path, map_location="cpu", weights_only=False)
    prior_train = prior.get("train") if isinstance(prior, Mapping) else None
    if not isinstance(prior_train, Mapping):
        raise ValueError("prior train context weights are missing")
    if prior_train.get("cell_ids") != current["cell_ids"]:
        raise ValueError("recomputed train context cells differ")
    prior_weights = torch.as_tensor(prior_train.get("weights"), dtype=torch.float64)
    current_weights = torch.as_tensor(current["weights"], dtype=torch.float64)
    if not torch.equal(prior_weights, current_weights):
        raise ValueError("recomputed train context weights differ")


def _render_summary(report: Mapping[str, Any]) -> str:
    evaluation = report["combined"]["evaluation"]
    support = report["context_support"]["evaluation"]
    failed = [
        name for name, passed in report["support_gate"]["conditions"].items() if not passed
    ]
    return "\n".join(
        (
            "# Fresh evaluation context-support supplement",
            "",
            f"- Decision: `{report['support_gate']['decision']}`",
            f"- Fresh supplement rows retained: `{report['supplement']['retained_rows']}`",
            f"- Augmented evaluation rows: `{evaluation['row_count']}`",
            f"- Evaluation real context mass covered: `{support['real_context_mass_covered']:.6f}`",
            f"- Evaluation ESS: `{support['effective_sample_size']:.3f}`",
            f"- Failed conditions: `{', '.join(failed) if failed else 'none'}`",
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
    prior_train_path: Path,
) -> None:
    balanced.ensure_output_paths_absent(OUTPUT_DIR, STAGING_DIR)
    STAGING_DIR.mkdir(parents=False)
    try:
        copied_train = copy_verified_file(
            prior_train_path,
            STAGING_DIR / "train_corpus.pt",
            expected_sha256=registration["inputs"]["prior_train_corpus"]["sha256"],
        )
        if copied_train["size_bytes"] != prior_train_path.stat().st_size:
            raise ValueError("copied training corpus size differs")
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
        (STAGING_DIR / "registration.json").write_bytes(canonical_json_bytes(registration))
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
    train = _loaded_corpus(inputs["prior_train_corpus"], "train")
    prior_evaluation = _loaded_corpus(
        inputs["prior_evaluation_corpus"], "evaluation"
    )
    fixed_fresh_seeds = tuple(
        range(
            FIXED_RECIPE["evaluation_seed_first"],
            FIXED_RECIPE["evaluation_seed_last"] + 1,
        )
    )
    validate_fresh_seed_isolation(
        prior_train_seeds=(int(row["seed"]) for row in train["metadata"]),
        prior_evaluation_seeds=(
            int(row["seed"]) for row in prior_evaluation["metadata"]
        ),
        fresh_evaluation_seeds=fixed_fresh_seeds,
    )

    native_module = load_native_module(inputs["native_module"])
    id_mapper = build_id_mapper(inputs["items_json"])
    initial = load_initial_checkpoint(
        inputs["initial_checkpoint"],
        expected_sha256=normalized["inputs"]["initial_checkpoint"]["sha256"],
    )
    trainer = create_fresh_trainer(
        id_mapper,
        seed=2026082951,
        batch_size=128,
        learning_starts=128,
    )
    parent_state, initialization = initialize_trainer(trainer, initial)
    config = CorpusConfig(
        train_seeds=tuple(range(268000, 269024)),
        evaluation_seeds=fixed_fresh_seeds,
        battle_indices=tuple(FIXED_RECIPE["battle_indices"]),
        max_source_decisions=FIXED_RECIPE["max_source_decisions"],
        max_actions_per_turn=FIXED_RECIPE["max_actions_per_turn"],
        max_states_per_profile=FIXED_RECIPE["max_states_per_profile"],
        max_canonical_actions=FIXED_RECIPE["max_canonical_actions"],
        continuation_decisions=FIXED_RECIPE["continuation_decisions"],
        return_discount=FIXED_RECIPE["return_discount"],
        positive_advantage_margin=FIXED_RECIPE["positive_advantage_margin"],
    )
    supplement_raw, supplement_summary = collect_partition(
        native_module,
        id_mapper=id_mapper,
        trainer=trainer,
        seeds=fixed_fresh_seeds,
        config=config,
    )
    if parameter_sha256(trainer.online_network.state_dict()) != parameter_sha256(parent_state):
        raise ValueError("parent parameters changed during corpus collection")
    supplement = {
        "partition": "evaluation",
        **supplement_raw,
        "row_count": len(supplement_raw["metadata"]),
    }
    actual_fresh_seeds = {int(row["seed"]) for row in supplement["metadata"]}
    if not actual_fresh_seeds.issubset(set(fixed_fresh_seeds)):
        raise ValueError("fresh evaluation corpus contains an unregistered seed")
    filtered, exclusions = filter_evaluation_supplement(supplement)
    evaluation = append_evaluation_corpus(prior_evaluation, filtered)

    train_weights = derive_context_weights(real, train)
    _validate_train_weight_reproduction(inputs["prior_context_weights"], train_weights)
    evaluation_weights = derive_context_weights(real, evaluation)
    integrity = balanced._integrity_conditions(train, evaluation)
    evaluation_late_floor_rows = sum(
        23 <= int(row["floor"]) <= 34 for row in evaluation["metadata"]
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
            "evaluation": supplement_summary,
            "target_floor_exclusions": exclusions,
            "retained_rows": filtered["row_count"],
            "requested_seed_count": len(fixed_fresh_seeds),
            "observed_seed_count": len(actual_fresh_seeds),
            "training_partition_collected": False,
        },
        "combined": {
            "train": _partition_summary(train),
            "evaluation": _partition_summary(evaluation),
        },
        "context_support": {
            "train": train_weights["metrics"],
            "evaluation": evaluation_weights["metrics"],
        },
        "missing_context": {
            "train": _missing_context_cells(real, train),
            "evaluation": _missing_context_cells(real, evaluation),
        },
        "evaluation_late_floor_rows": evaluation_late_floor_rows,
        "train_corpus_preservation": {
            "byte_identical": True,
            "sha256": normalized["inputs"]["prior_train_corpus"]["sha256"],
            "recomputed_context_weights_identical": True,
        },
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
        train=train,
        evaluation=evaluation,
        train_weights=train_weights,
        evaluation_weights=evaluation_weights,
        registration=normalized,
        prior_train_path=inputs["prior_train_corpus"],
    )
    return report


def _load_registration(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise ValueError(f"registration is missing: {path}")
    return json.loads(path.read_text(encoding="ascii"))


def _emit_json(value: Mapping[str, Any], output: Path | None) -> None:
    payload = canonical_json_bytes(value)
    if output is None:
        sys.stdout.buffer.write(payload)
        return
    output.write_bytes(payload)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    build = subparsers.add_parser("build-registration")
    build.add_argument("--source-commit", required=True)
    build.add_argument("--output", type=Path)
    preflight = subparsers.add_parser("preflight")
    preflight.add_argument("--registration", type=Path, required=True)
    preflight.add_argument("--output", type=Path)
    run = subparsers.add_parser("run")
    run.add_argument("--registration", type=Path, required=True)
    args = parser.parse_args()
    if args.command == "build-registration":
        _emit_json(build_registration(args.source_commit), args.output)
        return 0
    registration = _load_registration(args.registration)
    if args.command == "preflight":
        _emit_json(preflight_registration(registration), args.output)
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
