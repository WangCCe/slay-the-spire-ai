"""Offline-only wrapper and schema contract for the sts_lightspeed POC."""

from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable, Mapping, Sequence


ADAPTER_API_VERSION = "sts-lightspeed-noncombat-adapter-v2"
SUPPORTED_PROVENANCE_ADAPTER_API_VERSIONS = (
    "sts-lightspeed-noncombat-adapter-v1",
    ADAPTER_API_VERSION,
)
STATE_SCHEMA_VERSION = "sts-lightspeed-state-v1"
TRANSITION_SCHEMA_VERSION = "noncombat-simulator-transition-v1"
NATIVE_BASELINE_ACTION_SCHEMA_VERSION = "sts-lightspeed-native-baseline-action-v1"
NATIVE_TARGET_POLICY_ID = "sts_lightspeed_simple_agent_target_v1"
SOURCE_TYPE = "sts_lightspeed_simulation"
TARGET_CATEGORIES = ("card_reward", "event", "route", "shop")
MODULE_NAME = "sts_lightspeed_noncombat_adapter"

_DLL_DIRECTORY_HANDLES: list[Any] = []


class SimulatorAdapterError(ValueError):
    """Raised when the optional simulator violates the adapter contract."""


def canonical_json_bytes(value: Any) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path | str) -> str:
    return sha256_bytes(Path(path).read_bytes())


def normalize_label(value: object) -> str:
    return "".join(char for char in str(value).lower() if char.isalnum())


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise SimulatorAdapterError(f"{label} must be an object")
    return value


def validate_snapshot(value: object) -> dict[str, Any]:
    snapshot = dict(_mapping(value, "snapshot"))
    if snapshot.get("adapter_api_version") != ADAPTER_API_VERSION:
        raise SimulatorAdapterError("snapshot adapter_api_version mismatch")
    if snapshot.get("schema_version") != STATE_SCHEMA_VERSION:
        raise SimulatorAdapterError("snapshot schema_version mismatch")
    if snapshot.get("source_type") != SOURCE_TYPE:
        raise SimulatorAdapterError("snapshot source_type mismatch")
    if not isinstance(snapshot.get("terminal"), bool):
        raise SimulatorAdapterError("snapshot terminal must be boolean")
    category = snapshot.get("category")
    if category is not None and category not in TARGET_CATEGORIES:
        raise SimulatorAdapterError(f"unsupported snapshot category: {category!r}")
    _mapping(snapshot.get("state"), "snapshot.state")
    baseline = _mapping(snapshot.get("baseline_control"), "snapshot.baseline_control")
    if not isinstance(baseline.get("policy_id"), str) or not baseline["policy_id"]:
        raise SimulatorAdapterError("baseline policy_id is required")
    if not isinstance(baseline.get("history"), list):
        raise SimulatorAdapterError("baseline history must be a list")
    return snapshot


def validate_candidates(
    value: object,
    *,
    category: str | None,
) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        raise SimulatorAdapterError("candidate actions must be a list")
    if category is None:
        if value:
            raise SimulatorAdapterError("terminal or non-target state reported candidates")
        return []
    if category not in TARGET_CATEGORIES:
        raise SimulatorAdapterError(f"unsupported candidate category: {category!r}")

    result: list[dict[str, Any]] = []
    action_ids: set[str] = set()
    for index, raw_candidate in enumerate(value):
        candidate = dict(_mapping(raw_candidate, f"candidate[{index}]"))
        action_id = candidate.get("action_id")
        if not isinstance(action_id, str) or not action_id:
            raise SimulatorAdapterError(f"candidate[{index}] action_id is required")
        if action_id in action_ids:
            raise SimulatorAdapterError(f"duplicate candidate action_id: {action_id}")
        action_ids.add(action_id)
        if candidate.get("category") != category:
            raise SimulatorAdapterError(f"candidate category mismatch: {action_id}")
        if candidate.get("available") is not True:
            raise SimulatorAdapterError(f"candidate must be available: {action_id}")
        for field in ("kind", "label"):
            if not isinstance(candidate.get(field), str) or not candidate[field]:
                raise SimulatorAdapterError(f"candidate {field} is required: {action_id}")
        _mapping(candidate.get("raw"), f"candidate[{index}].raw")
        result.append(candidate)
    if not result:
        raise SimulatorAdapterError(f"target category {category} has no candidates")
    return result


def validate_native_baseline_action(
    value: object,
    *,
    category: str | None,
    candidates: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    action = dict(_mapping(value, "native baseline action"))
    if action.get("schema_version") != NATIVE_BASELINE_ACTION_SCHEMA_VERSION:
        raise SimulatorAdapterError("native baseline action schema mismatch")
    if action.get("policy_id") != NATIVE_TARGET_POLICY_ID:
        raise SimulatorAdapterError("native baseline policy id mismatch")
    if category not in TARGET_CATEGORIES or action.get("category") != category:
        raise SimulatorAdapterError("native baseline action category mismatch")
    action_id = action.get("action_id")
    if not isinstance(action_id, str) or not action_id:
        raise SimulatorAdapterError("native baseline action_id is required")
    candidate_ids = [candidate.get("action_id") for candidate in candidates]
    if candidate_ids.count(action_id) != 1:
        raise SimulatorAdapterError(
            "native baseline action must map to exactly one reported candidate"
        )
    return action


def validate_provenance(value: object) -> dict[str, Any]:
    provenance = dict(_mapping(value, "provenance"))
    required = (
        "adapter_commit",
        "adapter_source_sha256",
        "module_sha256",
        "simulator_commit",
        "simulator_source_sha256",
    )
    for field in required:
        if not isinstance(provenance.get(field), str) or not provenance[field]:
            raise SimulatorAdapterError(f"provenance.{field} is required")
    submodules = _mapping(provenance.get("submodules"), "provenance.submodules")
    for name in ("json", "pybind11"):
        if not isinstance(submodules.get(name), str) or not submodules[name]:
            raise SimulatorAdapterError(f"provenance.submodules.{name} is required")
    build = _mapping(provenance.get("build"), "provenance.build")
    for field in ("adapter_api_version", "compiler", "cpp_standard", "python"):
        if not build.get(field):
            raise SimulatorAdapterError(f"provenance.build.{field} is required")
    if build["adapter_api_version"] not in SUPPORTED_PROVENANCE_ADAPTER_API_VERSIONS:
        raise SimulatorAdapterError("provenance adapter API mismatch")
    return provenance


def build_transition(
    *,
    before: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    selected_action_id: str,
    after: Mapping[str, Any],
    provenance: Mapping[str, Any],
) -> dict[str, Any]:
    normalized_before = validate_snapshot(before)
    normalized_after = validate_snapshot(after)
    category = normalized_before["category"]
    if category not in TARGET_CATEGORIES:
        raise SimulatorAdapterError("transition source must be a target decision")
    normalized_candidates = validate_candidates(list(candidates), category=category)
    candidate_ids = {candidate["action_id"] for candidate in normalized_candidates}
    if selected_action_id not in candidate_ids:
        raise SimulatorAdapterError("selected action is not a reported candidate")
    normalized_provenance = validate_provenance(provenance)

    transition = {
        "baseline_control": normalized_after["baseline_control"],
        "candidate_actions": normalized_candidates,
        "category": category,
        "evidence_class": "simulator_transition",
        "live_evidence": {
            "known_propensity": False,
            "live_outcome_join": False,
            "ope_overlap": False,
            "target_supported_victory": False,
        },
        "provenance": normalized_provenance,
        "schema_version": TRANSITION_SCHEMA_VERSION,
        "selected_action_id": selected_action_id,
        "source_state": normalized_before["state"],
        "source_type": SOURCE_TYPE,
        "successor": {
            "category": normalized_after["category"],
            "state": normalized_after["state"],
            "terminal": normalized_after["terminal"],
        },
        "training_authority": {
            "formal_noncombat_rl": False,
            "live_policy_loading": False,
            "live_study_launch": False,
            "ope_reinterpretation": False,
            "policy_promotion": False,
        },
    }
    return transition


@dataclass
class NativeSimulatorEnvironment:
    """Validated Python facade over the optional native environment."""

    native: Any
    provenance: Mapping[str, Any]

    def snapshot(self) -> dict[str, Any]:
        return validate_snapshot(json.loads(self.native.snapshot_json()))

    def legal_actions(self) -> list[dict[str, Any]]:
        snapshot = self.snapshot()
        return validate_candidates(
            json.loads(self.native.legal_actions_json()),
            category=snapshot["category"],
        )

    def clone(self) -> "NativeSimulatorEnvironment":
        return NativeSimulatorEnvironment(self.native.clone(), self.provenance)

    def native_baseline_action(self) -> dict[str, Any]:
        before = self.snapshot()
        candidates = self.legal_actions()
        before_snapshot_bytes = canonical_json_bytes(before)
        before_candidate_bytes = canonical_json_bytes(candidates)
        try:
            raw_action = json.loads(self.native.native_baseline_action_json())
        except (AttributeError, TypeError, RuntimeError, json.JSONDecodeError) as exc:
            raise SimulatorAdapterError(f"invalid native baseline action: {exc}") from exc

        after = self.snapshot()
        if canonical_json_bytes(after) != before_snapshot_bytes:
            raise SimulatorAdapterError("native baseline query mutated source snapshot")
        after_candidates = self.legal_actions()
        if canonical_json_bytes(after_candidates) != before_candidate_bytes:
            raise SimulatorAdapterError("native baseline query mutated source candidates")
        return validate_native_baseline_action(
            raw_action,
            category=before["category"],
            candidates=candidates,
        )

    def step_native_baseline(self) -> dict[str, Any]:
        before = self.snapshot()
        candidates = self.legal_actions()
        expected = self.native_baseline_action()
        try:
            selected_action_id = self.native.step_native_baseline()
        except (AttributeError, TypeError, RuntimeError) as exc:
            raise SimulatorAdapterError(f"native baseline step failed: {exc}") from exc
        if selected_action_id != expected["action_id"]:
            raise SimulatorAdapterError("native baseline query and step action differ")
        after = self.snapshot()
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=selected_action_id,
            after=after,
            provenance=self.provenance,
        )

    def step(self, action_id: str) -> dict[str, Any]:
        before = self.snapshot()
        candidates = self.legal_actions()
        self.native.step(action_id)
        after = self.snapshot()
        return build_transition(
            before=before,
            candidates=candidates,
            selected_action_id=action_id,
            after=after,
            provenance=self.provenance,
        )


def load_native_module(
    module_path: Path | str,
    *,
    dll_directories: Iterable[Path | str] = (),
) -> ModuleType:
    module_file = Path(module_path).resolve()
    if not module_file.is_file():
        raise SimulatorAdapterError(f"native adapter module is missing: {module_file}")
    if hasattr(os, "add_dll_directory"):
        for directory in dll_directories:
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(Path(directory).resolve())))

    existing = sys.modules.get(MODULE_NAME)
    if existing is not None:
        existing_file = Path(getattr(existing, "__file__", "")).resolve()
        if existing_file != module_file:
            raise SimulatorAdapterError(
                f"{MODULE_NAME} already loaded from a different path: {existing_file}"
            )
        module = existing
    else:
        spec = importlib.util.spec_from_file_location(MODULE_NAME, module_file)
        if spec is None or spec.loader is None:
            raise SimulatorAdapterError(f"cannot load extension module: {module_file}")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[MODULE_NAME] = module

    if module.adapter_api_version() != ADAPTER_API_VERSION:
        raise SimulatorAdapterError("native module adapter API mismatch")
    return module


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def hash_compiled_simulator_sources(repo_path: Path | str) -> tuple[str, int]:
    repo = Path(repo_path).resolve()
    files = sorted(
        (
            path
            for root in (repo / "include", repo / "src")
            for path in root.rglob("*")
            if path.is_file()
        ),
        key=lambda path: path.relative_to(repo).as_posix(),
    )
    digest = hashlib.sha256()
    for path in files:
        relative = path.relative_to(repo).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest(), len(files)


def collect_provenance(
    *,
    simulator_repo: Path | str,
    module_path: Path | str,
    adapter_repo: Path | str,
    adapter_source_paths: Sequence[Path | str],
    native_module: ModuleType,
) -> dict[str, Any]:
    simulator = Path(simulator_repo).resolve()
    adapter = Path(adapter_repo).resolve()
    module_file = Path(module_path).resolve()
    simulator_source_sha256, source_file_count = hash_compiled_simulator_sources(simulator)

    adapter_digest = hashlib.sha256()
    for raw_path in sorted((Path(path).resolve() for path in adapter_source_paths), key=str):
        relative = raw_path.relative_to(adapter).as_posix().encode("utf-8")
        data = raw_path.read_bytes()
        adapter_digest.update(len(relative).to_bytes(4, "big"))
        adapter_digest.update(relative)
        adapter_digest.update(len(data).to_bytes(8, "big"))
        adapter_digest.update(data)

    build = json.loads(native_module.build_info_json())
    build["python"] = sys.version.split()[0]
    return validate_provenance(
        {
            "adapter_commit": _git(adapter, "rev-parse", "HEAD"),
            "adapter_source_sha256": adapter_digest.hexdigest(),
            "build": build,
            "module_sha256": sha256_file(module_file),
            "module_size_bytes": module_file.stat().st_size,
            "simulator_commit": _git(simulator, "rev-parse", "HEAD"),
            "simulator_dirty": bool(_git(simulator, "status", "--porcelain=v1")),
            "simulator_source_file_count": source_file_count,
            "simulator_source_sha256": simulator_source_sha256,
            "submodules": {
                "json": _git(simulator / "json", "rev-parse", "HEAD"),
                "pybind11": _git(simulator / "pybind11", "rev-parse", "HEAD"),
            },
        }
    )
