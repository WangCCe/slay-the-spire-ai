"""Collect a targeted context-support supplement for the successor corpus."""

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
from typing import Any, Mapping, Sequence

import torch


REPO_ROOT = Path(__file__).resolve().parents[1]
REPORTS_ROOT = REPO_ROOT / "reports"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from analysis_scripts import (  # noqa: E402
    combat_rl_action_relative_successor_delta_ablation as predecessor,
)


REGISTRATION_SCHEMA = (
    "combat-rl-action-relative-successor-context-supplement-registration-v1"
)
REPORT_SCHEMA = "combat-rl-action-relative-successor-context-supplement-report-v1"
MANIFEST_SCHEMA = (
    "combat-rl-action-relative-successor-context-supplement-manifest-v1"
)
EXPERIMENT_ID = (
    "combat-rl-action-relative-successor-context-supplement-20260829-r1"
)
SMOKE_EXPERIMENT_ID = (
    "combat-rl-action-relative-successor-context-supplement-smoke-20260829-r1"
)
OUTPUT_DIR = REPORTS_ROOT / EXPERIMENT_ID.replace("-", "_")
SMOKE_OUTPUT_DIR = REPORTS_ROOT / SMOKE_EXPERIMENT_ID.replace("-", "_")
REGISTRATION_PATH = REPORTS_ROOT / f"{EXPERIMENT_ID.replace('-', '_')}_registration.json"
PREFLIGHT_PATH = REPORTS_ROOT / f"{EXPERIMENT_ID.replace('-', '_')}_preflight.json"
SMOKE_REGISTRATION_PATH = REPORTS_ROOT / (
    f"{SMOKE_EXPERIMENT_ID.replace('-', '_')}_registration.json"
)
SMOKE_PREFLIGHT_PATH = REPORTS_ROOT / (
    f"{SMOKE_EXPERIMENT_ID.replace('-', '_')}_preflight.json"
)

FIXED_SLICES = {
    "fit_battle_3": {
        "partition": "fit",
        "seed_bounds": [283000, 283383],
        "battle_indices": [3],
    },
    "fresh_battle_3": {
        "partition": "fresh",
        "seed_bounds": [284000, 285023],
        "battle_indices": [3],
    },
    "fresh_battle_10": {
        "partition": "fresh",
        "seed_bounds": [286000, 287535],
        "battle_indices": [10],
    },
}
SMOKE_SLICES = {
    "smoke_battle_3": {
        "partition": "smoke_battle_3",
        "seed_bounds": [282900, 282907],
        "battle_indices": [3],
    },
    "smoke_battle_10": {
        "partition": "smoke_battle_10",
        "seed_bounds": [282910, 282917],
        "battle_indices": [10],
    },
}


def _collection_recipe(*, smoke: bool) -> dict[str, Any]:
    recipe = copy.deepcopy(predecessor.FIXED_CORPUS_RECIPE)
    recipe.pop("partitions")
    recipe.pop("battle_indices")
    recipe["slices"] = copy.deepcopy(SMOKE_SLICES if smoke else FIXED_SLICES)
    if smoke:
        recipe.update(
            {
                "max_source_decisions": 60,
                "max_states_per_profile": 1,
                "continuation_decisions": 2,
                "max_wall_seconds": 1200,
                "max_stored_bytes": 134217728,
            }
        )
    else:
        recipe.update(
            {
                "max_wall_seconds": 7200,
                "max_stored_bytes": 536870912,
            }
        )
    return recipe


FIXED_RECIPE = _collection_recipe(smoke=False)
SMOKE_RECIPE = _collection_recipe(smoke=True)

R2_ROOT = REPORTS_ROOT / predecessor.CORPUS_EXPERIMENT_ID.replace("-", "_")
FIXED_INPUTS = {
    **copy.deepcopy(predecessor.FIXED_INPUTS),
    "r2_fit_corpus": {
        "path": R2_ROOT / "fit_corpus.pt",
        "sha256": "026972d0385d28e47ebf23ac4190c2ab47e6de870d95c67ea7a6d93eaeeeee70",
    },
    "r2_calibration_corpus": {
        "path": R2_ROOT / "calibration_corpus.pt",
        "sha256": "c2943ba2eaf4b8f95839d4733f4b5fcc0fe26fc63061dfd7e98f4e2a4e57275f",
    },
    "r2_fresh_corpus": {
        "path": R2_ROOT / "fresh_corpus.pt",
        "sha256": "bafc3e0acd68c26d8d5775026d96786558ecf17a2074132290629b4d323c6fc1",
    },
    "r2_report": {
        "path": R2_ROOT / "report.json",
        "sha256": "02803f978685d50d5024d353c8d19362737824a61ec976a1c1a1523d07d94de6",
    },
    "r2_manifest": {
        "path": R2_ROOT / "manifest.json",
        "sha256": "69d06c802e1951f78082c7d37a19386d4436d16230e11dc788260fc29ff1765e",
    },
    "r2_registration": {
        "path": R2_ROOT / "registration.json",
        "sha256": "1ede0b73582a0aba2507a6b9d9959ff1a328258543107260af2ea2e2b38af19f",
    },
}

AUTHORITY = {
    **copy.deepcopy(predecessor.CORPUS_AUTHORITY),
    "formal_evidence": True,
    "merged_support_decision": True,
}
SOURCE_SNAPSHOT_PATHS = (
    "analysis_scripts/combat_rl_action_relative_successor_context_supplement.py",
    *predecessor.SOURCE_SNAPSHOT_PATHS,
)


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")


def _source_file_hashes() -> dict[str, str]:
    return {
        relative: predecessor.sha256_file(REPO_ROOT / relative)
        for relative in SOURCE_SNAPSHOT_PATHS
    }


def _input_bindings() -> dict[str, dict[str, str]]:
    return {
        name: {
            "path": str(value["path"].resolve()),
            "sha256": str(value["sha256"]),
        }
        for name, value in sorted(FIXED_INPUTS.items())
    }


def _authority(*, smoke: bool) -> dict[str, bool]:
    result = copy.deepcopy(AUTHORITY)
    result["formal_evidence"] = not smoke
    result["merged_support_decision"] = not smoke
    return result


def build_registration(source_commit: str, *, smoke: bool) -> dict[str, Any]:
    source_commit = predecessor._validate_commit(source_commit)
    experiment_id = SMOKE_EXPERIMENT_ID if smoke else EXPERIMENT_ID
    output = SMOKE_OUTPUT_DIR if smoke else OUTPUT_DIR
    return {
        "schema_version": REGISTRATION_SCHEMA,
        "experiment_id": experiment_id,
        "source_commit": source_commit,
        "runner": {
            "path": str(Path(__file__).resolve()),
            "sha256": predecessor.sha256_file(Path(__file__)),
        },
        "source_files": _source_file_hashes(),
        "inputs": _input_bindings(),
        "predecessor_experiment_id": predecessor.CORPUS_EXPERIMENT_ID,
        "recipe": copy.deepcopy(SMOKE_RECIPE if smoke else FIXED_RECIPE),
        "output_dir": str(output.resolve()),
        "smoke": smoke,
        "authority": _authority(smoke=smoke),
    }


def validate_registration(
    registration: Mapping[str, Any], *, smoke: bool
) -> dict[str, Any]:
    expected = build_registration(str(registration.get("source_commit", "")), smoke=smoke)
    if dict(registration) != expected:
        raise ValueError("successor supplement registration payload differs")
    validate_slice_contract(expected["recipe"]["slices"], occupied_seeds=set())
    return copy.deepcopy(expected)


def _slice_seed_set(config: Mapping[str, Any]) -> set[int]:
    required = {"partition", "seed_bounds", "battle_indices"}
    if not isinstance(config, Mapping) or set(config) != required:
        raise ValueError("successor supplement slice shape differs")
    bounds = config["seed_bounds"]
    battles = config["battle_indices"]
    if (
        not isinstance(config["partition"], str)
        or not config["partition"]
        or not isinstance(bounds, list)
        or len(bounds) != 2
        or any(not isinstance(value, int) or isinstance(value, bool) for value in bounds)
        or bounds[0] > bounds[1]
        or not isinstance(battles, list)
        or len(battles) != 1
        or not isinstance(battles[0], int)
        or isinstance(battles[0], bool)
    ):
        raise ValueError("successor supplement slice value differs")
    return set(range(bounds[0], bounds[1] + 1))


def validate_slice_contract(
    slices: Mapping[str, Mapping[str, Any]], *, occupied_seeds: set[int]
) -> dict[str, Mapping[str, Any]]:
    if not isinstance(slices, Mapping) or not slices:
        raise ValueError("successor supplement slice inventory differs")
    seen: set[int] = set()
    for name, config in slices.items():
        if not isinstance(name, str) or not name:
            raise ValueError("successor supplement slice name differs")
        seeds = _slice_seed_set(config)
        if seen.intersection(seeds):
            raise ValueError("successor supplement seed slices overlap")
        seen.update(seeds)
    if seen.intersection(occupied_seeds):
        raise ValueError("successor supplement seed collides with lineage")
    return copy.deepcopy(dict(slices))


def validate_collected_slice(
    corpus: Mapping[str, Any],
    *,
    slice_name: str,
    slices: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if slice_name not in slices:
        raise ValueError("successor supplement slice name is unregistered")
    config = slices[slice_name]
    validated = predecessor.validate_successor_corpus(
        corpus, expected_partition=str(config["partition"])
    )
    seeds = _slice_seed_set(config)
    battles = set(config["battle_indices"])
    for row in validated["metadata"]:
        if int(row.get("seed", -1)) not in seeds or int(
            row.get("battle_index", -1)
        ) not in battles:
            raise ValueError("successor supplement row is outside registered slice")
    return validated


def merge_successor_corpora(
    partition: str, *corpora: Mapping[str, Any]
) -> dict[str, Any]:
    if not corpora:
        raise ValueError("successor supplement merge has no corpora")
    validated = [
        predecessor.validate_successor_corpus(value, expected_partition=partition)
        for value in corpora
    ]
    tensors = {
        name: torch.cat([value["tensors"][name] for value in validated], dim=0)
        for name in predecessor.SOURCE_TENSOR_NAMES
    }
    pairs: dict[str, torch.Tensor] = {}
    row_offset = 0
    source_rows: list[torch.Tensor] = []
    for value in validated:
        source_rows.append(value["pairs"]["source_rows"] + row_offset)
        row_offset += int(value["row_count"])
    pairs["source_rows"] = torch.cat(source_rows, dim=0)
    for name in predecessor.PAIR_TENSOR_NAMES:
        if name != "source_rows":
            pairs[name] = torch.cat(
                [value["pairs"][name] for value in validated], dim=0
            )
    merged = {
        "schema_version": predecessor.CORPUS_SCHEMA,
        "corpus_kind": predecessor.CORPUS_KIND,
        "partition": partition,
        "tensors": tensors,
        "metadata": [
            copy.deepcopy(row)
            for value in validated
            for row in value["metadata"]
        ],
        "pairs": pairs,
        "row_count": sum(int(value["row_count"]) for value in validated),
        "pair_count": sum(int(value["pair_count"]) for value in validated),
    }
    return predecessor.validate_successor_corpus(
        merged, expected_partition=partition
    )


def validate_merged_seed_isolation(corpora: Mapping[str, Mapping[str, Any]]) -> None:
    expected = {"fit", "calibration", "fresh"}
    if set(corpora) != expected:
        raise ValueError("successor supplement merged partition inventory differs")
    seen: set[int] = set()
    for partition in ("fit", "calibration", "fresh"):
        value = predecessor.validate_successor_corpus(
            corpora[partition], expected_partition=partition
        )
        seeds = {int(row["seed"]) for row in value["metadata"]}
        if seen.intersection(seeds):
            raise ValueError("successor supplement merged seeds overlap")
        seen.update(seeds)


def evaluate_merged_support(
    corpora: Mapping[str, Mapping[str, Any]], paths: Mapping[str, Any]
) -> dict[str, Any]:
    return predecessor._corpus_support_evidence(corpora, paths)


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


def build_report_payload(
    *,
    registration: Mapping[str, Any],
    started: Mapping[str, Any],
    support: Mapping[str, Any] | None,
    partition_summaries: Mapping[str, Any],
    merged_identities: Mapping[str, Any],
    provenance: Mapping[str, Any],
    elapsed_seconds: float,
    smoke_repeat_identity_exact: bool | None = None,
    initialization: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    smoke = registration.get("smoke") is True
    if smoke:
        decision = (
            "deterministic_smoke_passed"
            if smoke_repeat_identity_exact is True
            else "deterministic_smoke_failed"
        )
    elif support is not None and support["gate"]["passed"] is True:
        decision = "merged_support_ready_for_separate_fit"
    else:
        decision = "merged_support_insufficient_close_without_fit"
    return {
        "schema_version": REPORT_SCHEMA,
        "experiment_id": registration["experiment_id"],
        "source_commit": registration["source_commit"],
        "predecessor_experiment_id": registration["predecessor_experiment_id"],
        "smoke": smoke,
        "recipe": copy.deepcopy(registration["recipe"]),
        "inputs": copy.deepcopy(registration["inputs"]),
        "source_files": copy.deepcopy(registration["source_files"]),
        "partitions": copy.deepcopy(dict(partition_summaries)),
        "merged_identities": copy.deepcopy(dict(merged_identities)),
        "context_support": copy.deepcopy(support),
        "smoke_repeat_identity_exact": smoke_repeat_identity_exact,
        "provenance": copy.deepcopy(dict(provenance)),
        "initialization": copy.deepcopy(initialization),
        "started_receipt": copy.deepcopy(dict(started)),
        "elapsed_seconds_before_publication": float(elapsed_seconds),
        "decision": decision,
        "optimizer_constructed": False,
        "authority": copy.deepcopy(registration["authority"]),
    }


def _render_summary(report: Mapping[str, Any]) -> str:
    lines = [
        "# Action-relative successor context supplement",
        "",
        f"- Experiment: `{report['experiment_id']}`",
        f"- Decision: `{report.get('decision', 'unreported')}`",
    ]
    for name, summary in report.get("partitions", {}).items():
        lines.append(
            f"- {name}: `{summary['row_count']}` states, "
            f"`{summary['pair_count']}` candidate pairs"
        )
    lines.extend(
        (
            "",
            "This is development-only simulator evidence. It grants no gameplay,",
            "training, policy evaluation, qualification, promotion, or production authority.",
            "",
        )
    )
    return "\n".join(lines)


def publish_artifacts(
    *,
    output: Path,
    corpora: Mapping[str, Mapping[str, Any]],
    report: Mapping[str, Any],
    registration: Mapping[str, Any],
    preflight: Mapping[str, Any],
    started: Mapping[str, Any],
    max_stored_bytes: int,
) -> dict[str, Any]:
    output = Path(output).resolve()
    staging = output.with_name(f".{output.name}.staging")
    if output.exists() or staging.exists():
        raise ValueError("successor supplement output or staging already exists")
    staging.mkdir(parents=True, exist_ok=False)
    try:
        for name, corpus in corpora.items():
            partition = str(corpus["partition"])
            validated = predecessor.validate_successor_corpus(
                corpus, expected_partition=partition
            )
            path = staging / f"{name}_corpus.pt"
            torch.save(validated, path)
            loaded = torch.load(path, map_location="cpu", weights_only=False)
            if predecessor.successor_corpus_identity(
                loaded
            ) != predecessor.successor_corpus_identity(validated):
                raise RuntimeError("successor supplement corpus roundtrip differs")
        (staging / "report.json").write_bytes(_canonical_json_bytes(report))
        (staging / "summary.md").write_text(
            _render_summary(report), encoding="ascii", newline="\n"
        )
        (staging / "registration.json").write_bytes(
            _canonical_json_bytes(registration)
        )
        (staging / "preflight.json").write_bytes(_canonical_json_bytes(preflight))
        (staging / "started_receipt.json").write_bytes(
            _canonical_json_bytes(started)
        )
        stored = sum(path.stat().st_size for path in staging.rglob("*") if path.is_file())
        if stored > int(max_stored_bytes):
            raise RuntimeError("successor supplement stored-byte limit exceeded")
        artifacts = {
            path.relative_to(staging).as_posix(): {
                "sha256": predecessor.sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
            for path in sorted(staging.rglob("*"))
            if path.is_file() and path.name != "manifest.json"
        }
        manifest = {
            "schema_version": MANIFEST_SCHEMA,
            "experiment_id": report["experiment_id"],
            "source_commit": report["source_commit"],
            "decision": report.get("decision"),
            "artifacts": artifacts,
        }
        (staging / "manifest.json").write_bytes(_canonical_json_bytes(manifest))
        os.replace(staging, output)
        return manifest
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise


def _validated_source_commit(source_commit: str) -> str:
    commit = predecessor._validate_commit(source_commit)
    current = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="ascii",
    ).stdout.strip()
    if subprocess.run(
        ["git", "merge-base", "--is-ancestor", commit, current],
        cwd=REPO_ROOT,
        check=False,
    ).returncode:
        raise ValueError("successor supplement source commit is not an ancestor")
    for relative in SOURCE_SNAPSHOT_PATHS:
        if subprocess.run(
            ["git", "diff", "--quiet", commit, "--", relative],
            cwd=REPO_ROOT,
            check=False,
        ).returncode:
            raise ValueError(f"successor supplement source changed: {relative}")
    return commit


def _validated_inputs(registration: Mapping[str, Any]) -> dict[str, Path]:
    paths: dict[str, Path] = {}
    for name, binding in registration["inputs"].items():
        path = Path(binding["path"]).resolve()
        if not path.is_file() or predecessor.sha256_file(path) != binding["sha256"]:
            raise ValueError(f"successor supplement input binding differs: {name}")
        paths[name] = path
    return paths


def _registered_slice_seeds(*, exclude_experiment_id: str) -> set[int]:
    seeds: set[int] = set()
    for bounds in predecessor.FIXED_COHORT.values():
        seeds.update(range(int(bounds[0]), int(bounds[1]) + 1))
    for bounds in predecessor.SMOKE_CORPUS_RECIPE["partitions"].values():
        seeds.update(range(int(bounds[0]), int(bounds[1]) + 1))
    candidates = {
        *REPORTS_ROOT.glob(
            "combat_rl_action_relative_successor_context_supplement*_registration.json"
        ),
        *REPORTS_ROOT.glob(
            "combat_rl_action_relative_successor_context_supplement*/registration.json"
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
                seeds.update(_slice_seed_set(config))
    return seeds


def _r2_seed_inventory(paths: Mapping[str, Path]) -> set[int]:
    seeds: set[int] = set()
    for partition in ("fit", "calibration", "fresh"):
        corpus = predecessor._load_successor_corpus(
            paths[f"r2_{partition}_corpus"], partition=partition
        )
        seeds.update(int(row["seed"]) for row in corpus["metadata"])
    return seeds


def write_registration(*, source_commit: str, smoke: bool) -> dict[str, Any]:
    registration_path = SMOKE_REGISTRATION_PATH if smoke else REGISTRATION_PATH
    preflight_path = SMOKE_PREFLIGHT_PATH if smoke else PREFLIGHT_PATH
    output = SMOKE_OUTPUT_DIR if smoke else OUTPUT_DIR
    if registration_path.exists() or preflight_path.exists() or output.exists():
        raise ValueError("successor supplement registration or output already exists")
    registration = validate_registration(
        build_registration(source_commit, smoke=smoke), smoke=smoke
    )
    _validated_source_commit(source_commit)
    paths = _validated_inputs(registration)
    occupied = _registered_slice_seeds(
        exclude_experiment_id=registration["experiment_id"]
    ) | _r2_seed_inventory(paths)
    validate_slice_contract(
        registration["recipe"]["slices"], occupied_seeds=occupied
    )
    preflight = {
        "schema_version": (
            "combat-rl-action-relative-successor-context-supplement-preflight-v1"
        ),
        "experiment_id": registration["experiment_id"],
        "source_commit": source_commit,
        "registration_sha256": hashlib.sha256(
            _canonical_json_bytes(registration)
        ).hexdigest(),
        "lineage_seed_count": len(occupied),
        "slice_profile_count": sum(
            len(_slice_seed_set(config))
            for config in registration["recipe"]["slices"].values()
        ),
        "output_absent": True,
        "native_loaded": False,
        "optimizer_constructed": False,
        "authority": copy.deepcopy(registration["authority"]),
    }
    registration_path.write_bytes(_canonical_json_bytes(registration))
    preflight_path.write_bytes(_canonical_json_bytes(preflight))
    return {"registration": registration, "preflight": preflight}


def _load_registration(path: Path) -> tuple[dict[str, Any], bool]:
    value = json.loads(path.read_text(encoding="ascii"))
    smoke = value.get("smoke") is True
    expected = SMOKE_REGISTRATION_PATH if smoke else REGISTRATION_PATH
    if path.resolve() != expected.resolve():
        raise ValueError("successor supplement registration path differs")
    return validate_registration(value, smoke=smoke), smoke


def record_started_failure(registration_path: Path, error: BaseException) -> Path | None:
    try:
        registration = json.loads(Path(registration_path).read_text(encoding="ascii"))
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
    try:
        started = json.loads(started_path.read_text(encoding="ascii"))
    except (OSError, ValueError):
        return None
    failure = {
        "schema_version": (
            "combat-rl-action-relative-successor-context-supplement-failure-v1"
        ),
        "experiment_id": experiment_id,
        "source_commit": source_commit,
        "started_receipt": started,
        "error_type": type(error).__name__,
        "error_message": str(error),
        "output_exists": output.exists(),
        "optimizer_constructed": False,
        "authority": copy.deepcopy(registration.get("authority", {})),
    }
    failure_path.write_bytes(_canonical_json_bytes(failure))
    return failure_path


def _slice_recipe(recipe: Mapping[str, Any], config: Mapping[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(dict(recipe))
    result.pop("slices")
    result["battle_indices"] = copy.deepcopy(config["battle_indices"])
    return result


def _collect_slices(
    registration: Mapping[str, Any],
    *,
    native_module: Any,
    mapper: Any,
    trainer: Any,
) -> tuple[dict[str, dict[str, Any]], dict[str, dict[str, Any]]]:
    corpora: dict[str, dict[str, Any]] = {}
    summaries: dict[str, dict[str, Any]] = {}
    for name, config in registration["recipe"]["slices"].items():
        bounds = config["seed_bounds"]
        corpus, summary = predecessor.collect_successor_partition(
            native_module,
            id_mapper=mapper,
            trainer=trainer,
            partition=str(config["partition"]),
            seeds=tuple(range(int(bounds[0]), int(bounds[1]) + 1)),
            recipe=_slice_recipe(registration["recipe"], config),
        )
        corpora[name] = validate_collected_slice(
            corpus, slice_name=name, slices=registration["recipe"]["slices"]
        )
        summaries[name] = summary
    return corpora, summaries


def run_registered(registration_path: Path) -> dict[str, Any]:
    if Path(sys.executable).resolve() != predecessor.EXPECTED_INTERPRETER.resolve():
        raise ValueError("successor supplement must use the registered interpreter")
    if not bool(sys.flags.isolated):
        raise ValueError("successor supplement must run in isolated mode")
    registration, smoke = _load_registration(Path(registration_path).resolve())
    _validated_source_commit(registration["source_commit"])
    paths = _validated_inputs(registration)
    occupied = _registered_slice_seeds(
        exclude_experiment_id=registration["experiment_id"]
    ) | _r2_seed_inventory(paths)
    validate_slice_contract(
        registration["recipe"]["slices"], occupied_seeds=occupied
    )

    output = Path(registration["output_dir"]).resolve()
    staging = output.with_name(f".{output.name}.staging")
    started_path = REPORTS_ROOT / f".{registration['experiment_id']}.started.json"
    if output.exists() or staging.exists() or started_path.exists():
        raise ValueError("successor supplement output, staging, or receipt already exists")
    started_at = time.time()
    started = {
        "schema_version": (
            "combat-rl-action-relative-successor-context-supplement-started-v1"
        ),
        "experiment_id": registration["experiment_id"],
        "source_commit": registration["source_commit"],
        "started_unix": started_at,
    }
    started_path.write_bytes(_canonical_json_bytes(started))

    native_module = predecessor.load_native_module(paths["native_module"])
    mapper = predecessor.build_id_mapper(paths["items_json"])
    initial = predecessor.load_initial_checkpoint(
        paths["parent_checkpoint"],
        expected_sha256=registration["inputs"]["parent_checkpoint"]["sha256"],
    )
    trainer = predecessor.create_fresh_trainer(
        mapper, seed=2026082902, batch_size=128, learning_starts=128
    )
    parent_state, initialization = predecessor.initialize_trainer(trainer, initial)
    supplements, collected_summaries = _collect_slices(
        registration,
        native_module=native_module,
        mapper=mapper,
        trainer=trainer,
    )

    if smoke:
        repeated, _ = _collect_slices(
            registration,
            native_module=native_module,
            mapper=mapper,
            trainer=trainer,
        )
        deterministic = all(
            predecessor.successor_corpus_identity(supplements[name])
            == predecessor.successor_corpus_identity(repeated[name])
            for name in supplements
        )
        if not deterministic:
            raise RuntimeError("successor supplement smoke identity differs")
        published_corpora = supplements
        support = None
        merged_identities: dict[str, Any] = {}
    else:
        r2 = {
            partition: predecessor._load_successor_corpus(
                paths[f"r2_{partition}_corpus"], partition=partition
            )
            for partition in ("fit", "calibration", "fresh")
        }
        merged = {
            "fit": merge_successor_corpora(
                "fit", r2["fit"], supplements["fit_battle_3"]
            ),
            "calibration": predecessor.validate_successor_corpus(
                r2["calibration"], expected_partition="calibration"
            ),
            "fresh": merge_successor_corpora(
                "fresh",
                r2["fresh"],
                supplements["fresh_battle_3"],
                supplements["fresh_battle_10"],
            ),
        }
        validate_merged_seed_isolation(merged)
        support = evaluate_merged_support(merged, paths)
        published_corpora = merged
        merged_identities = {
            name: predecessor.successor_corpus_identity(value)
            for name, value in merged.items()
        }
        deterministic = None

    provenance = predecessor.collect_provenance(
        repo_root=REPO_ROOT,
        simulator_repo=predecessor.SIMULATOR_REPO,
        module_path=paths["native_module"],
        native_module=native_module,
    )
    partition_summaries = {
        f"supplement_{name}": {
            **_partition_summary(corpus),
            "collection": copy.deepcopy(collected_summaries[name]),
        }
        for name, corpus in supplements.items()
    }
    if not smoke:
        partition_summaries.update(
            {
                f"merged_{name}": _partition_summary(corpus)
                for name, corpus in published_corpora.items()
            }
        )
    report = build_report_payload(
        registration=registration,
        started=started,
        support=support,
        partition_summaries=partition_summaries,
        merged_identities=merged_identities,
        provenance=provenance,
        elapsed_seconds=time.time() - started_at,
        smoke_repeat_identity_exact=deterministic,
        initialization=initialization,
    )
    if report["elapsed_seconds_before_publication"] > float(
        registration["recipe"]["max_wall_seconds"]
    ):
        raise RuntimeError("successor supplement wall-time limit exceeded")
    preflight_path = SMOKE_PREFLIGHT_PATH if smoke else PREFLIGHT_PATH
    preflight = json.loads(preflight_path.read_text(encoding="ascii"))
    publish_artifacts(
        output=output,
        corpora=published_corpora,
        report=report,
        registration=registration,
        preflight=preflight,
        started=started,
        max_stored_bytes=int(registration["recipe"]["max_stored_bytes"]),
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write-registration", action="store_true")
    parser.add_argument("--run-registration", type=Path)
    parser.add_argument("--source-commit")
    parser.add_argument("--smoke", action="store_true")
    args = parser.parse_args()
    if args.write_registration == (args.run_registration is not None):
        parser.error("choose exactly one of --write-registration or --run-registration")
    if args.write_registration:
        if args.source_commit is None:
            parser.error("--source-commit is required")
        result = write_registration(
            source_commit=args.source_commit, smoke=bool(args.smoke)
        )
    else:
        if args.source_commit is not None or args.smoke:
            parser.error("run mode reads identity from the registration")
        try:
            result = run_registered(args.run_registration)
        except BaseException as error:
            record_started_failure(args.run_registration, error)
            raise
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


__all__ = [
    "EXPERIMENT_ID",
    "SMOKE_EXPERIMENT_ID",
    "FIXED_SLICES",
    "SMOKE_SLICES",
    "FIXED_RECIPE",
    "SMOKE_RECIPE",
    "AUTHORITY",
    "build_registration",
    "validate_registration",
    "validate_slice_contract",
    "validate_collected_slice",
    "merge_successor_corpora",
    "validate_merged_seed_isolation",
    "evaluate_merged_support",
    "build_report_payload",
    "publish_artifacts",
    "record_started_failure",
    "write_registration",
    "run_registered",
]
