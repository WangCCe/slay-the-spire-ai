"""Audit non-combat representation sufficiency and SimpleAgent suitability."""

from __future__ import annotations

import argparse
import copy
import json
import math
import os
import re
import subprocess
import sys
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Mapping, Sequence
from pathlib import Path
from typing import Any

from analysis_scripts.noncombat_simulator_adapter import (
    NATIVE_TARGET_POLICY_ID,
    canonical_json_bytes,
    sha256_bytes,
    sha256_file,
)
from analysis_scripts.noncombat_simulator_training_smoke import (
    LEAKAGE_FIELDS,
    _candidate_features,
    _verify_sources_at_commit,
    hash_bound_files,
    project_policy_view,
)
from analysis_scripts.noncombat_structured_baseline_ranker_poc import (
    REGISTERED_TRAIN_SEEDS,
    TRAIN_INPUT_MANIFEST_SCHEMA_VERSION,
    StructuredPocBlocked,
    _actual_binding,
    _binding_for_path,
    _is_commit,
    _is_sha256,
    _load_json,
    _mapping,
    _require_exact,
    _require_keys,
    load_train_input_archive,
    structured_feature_map,
    validate_train_input,
    vectorize_structured_features,
)


AuditBlocked = StructuredPocBlocked

REGISTRATION_SCHEMA_VERSION = (
    "noncombat-state-action-teacher-sufficiency-audit-input-v1"
)
SOURCE_FACTS_SCHEMA_VERSION = "noncombat-teacher-source-facts-v1"
DEPENDENCY_SCHEMA_VERSION = "noncombat-teacher-dependency-coverage-v1"
ROW_EVIDENCE_SCHEMA_VERSION = "noncombat-teacher-row-evidence-v1"
METRICS_SCHEMA_VERSION = "noncombat-representation-alias-metrics-v1"
SUITABILITY_SCHEMA_VERSION = "noncombat-teacher-suitability-v1"
REPORT_SCHEMA_VERSION = "noncombat-state-action-teacher-audit-report-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-state-action-teacher-audit-manifest-v1"
JOURNAL_SCHEMA_VERSION = "noncombat-state-action-teacher-audit-journal-v1"

AUDITED_CATEGORIES = ("card_reward", "route")
SIGNATURE_IDS = (
    "teacher-source-v1",
    "adapter-observable-v1",
    "legacy-hash-1024-v1",
    "structured-hash-2048-v1",
)
VERDICT_ORDER = (
    "blocked",
    "adapter_representation_repair_required",
    "simpleagent_unsuitable_as_policy_quality_gate",
    "audit_inconclusive",
)
EXTERNAL_SOURCE_FILES = (
    "include/constants/Rooms.h",
    "include/game/Card.h",
    "include/sim/search/SimpleAgent.h",
    "src/game/Card.cpp",
    "src/sim/search/SimpleAgent.cpp",
)
REGISTERED_SOURCE_FILES = (
    "analysis_scripts/noncombat_policy_model.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "analysis_scripts/noncombat_simulator_training_smoke.py",
    "analysis_scripts/noncombat_structured_baseline_ranker_poc.py",
    "analysis_scripts/noncombat_state_action_teacher_sufficiency_audit.py",
    "simulator_adapters/sts_lightspeed/noncombat_adapter.cpp",
)
CANONICAL_ARTIFACT_NAMES = (
    "artifact_manifest.json",
    "configuration.json",
    "dependency_coverage.json",
    "report.json",
    "report.md",
    "representation_metrics.json",
    "row_evidence.json",
    "source_facts.json",
    "teacher_suitability.json",
)

MAP_SCREEN_ANCHOR = "case ScreenState::MAP_SCREEN:"
ROUTE_FUNCTION_ANCHOR = (
    "fixed_list<int,16> search::SimpleAgent::getBestMapPathForWeights"
)
CARD_FUNCTION_ANCHOR = "void search::SimpleAgent::stepCardReward"
MAP_WEIGHTS_ANCHOR = "static constexpr int mapWeights[3][6]"
CARD_PRIORITIES_ANCHOR = "constexpr std::array<CardId,133> cardsPriorities"
MAX_COPIES_ANCHOR = "maxCopies = new std::map<CardId, int>"
ADAPTER_CARD_CANDIDATES_ANCHOR = (
    "std::vector<Candidate> cardRewardCandidates() const"
)
ADAPTER_NATIVE_ACTION_ANCHOR = (
    "std::string probeNativeBaselineAction(sts::search::SimpleAgent *agentAfter) const"
)
CARD_EQUALITY_ANCHOR = "bool Card::operator==(const Card &rhs) const"


def _authority() -> dict[str, bool]:
    return {
        "dagger": False,
        "formal_noncombat_rl": False,
        "live_gameplay": False,
        "live_policy_loading": False,
        "model_fitting": False,
        "native_build": False,
        "native_evidence_collection": False,
        "native_module_loading": False,
        "ope_reinterpretation": False,
        "policy_promotion": False,
        "policy_quality": False,
        "qualification": False,
        "simulator_rollout": False,
    }


def _audit_contract() -> dict[str, Any]:
    return {
        "categories": list(AUDITED_CATEGORIES),
        "limits": {
            "max_candidates_per_row": 32,
            "max_model_fits": 0,
            "max_native_calls": 0,
            "max_rows": 1500,
            "max_wall_seconds": 120.0,
        },
        "seeds": list(REGISTERED_TRAIN_SEEDS),
        "signatures": {
            "adapter-observable-v1": {
                "leakage_fields": sorted(LEAKAGE_FIELDS),
                "type": "canonical-policy-view-bytes",
            },
            "legacy-hash-1024-v1": {
                "dtype": "float32",
                "hash_dim": 1024,
                "type": "exact-candidate-vector-bytes",
            },
            "structured-hash-2048-v1": {
                "dtype": "float32",
                "hash_dim": 2048,
                "type": "exact-candidate-vector-bytes",
            },
            "teacher-source-v1": {
                "type": "source-faithful-dependency-signature"
            },
        },
        "suitability_checks": [
            "route_replans_with_current_state",
            "route_reads_survivability",
            "route_reads_run_resources",
            "card_copy_limit_uses_actual_deck",
            "card_reads_deck_and_run_context",
            "card_values_skip_vs_bowl",
        ],
        "verdict_order": list(VERDICT_ORDER),
    }


def _external_file_records(root: Path) -> list[dict[str, Any]]:
    records = []
    for relative in EXTERNAL_SOURCE_FILES:
        path = root / relative
        if not path.is_file():
            raise AuditBlocked(f"external source file is missing: {relative}")
        records.append(
            {
                "path": relative,
                "sha256": sha256_file(path),
                "size_bytes": path.stat().st_size,
            }
        )
    return records


def _git_output(root: Path, *args: str) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), *args],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise AuditBlocked(f"cannot inspect git checkout {root}: {exc}") from exc
    return result.stdout.strip()


def _external_identity(root: Path) -> dict[str, Any]:
    commit = _git_output(root, "rev-parse", "HEAD")
    relevant_status = _git_output(root, "status", "--short", "--", *EXTERNAL_SOURCE_FILES)
    overall_status = _git_output(root, "status", "--short")
    return {
        "commit": commit,
        "files": _external_file_records(root),
        "overall_dirty_at_registration": bool(overall_status),
        "overall_status_sha256": sha256_bytes(overall_status.encode("utf-8")),
        "relevant_status": relevant_status,
        "repo_path": str(root.resolve()),
    }


def _validate_external_contract(value: object) -> dict[str, Any]:
    identity = dict(_mapping(value, "external source identity"))
    _require_keys(
        identity,
        {
            "commit",
            "files",
            "overall_dirty_at_registration",
            "overall_status_sha256",
            "relevant_status",
            "repo_path",
        },
        "external source identity",
    )
    if not _is_commit(identity["commit"]):
        raise AuditBlocked("external source commit is invalid")
    if not isinstance(identity["repo_path"], str) or not identity["repo_path"]:
        raise AuditBlocked("external source repo path is invalid")
    if not isinstance(identity["relevant_status"], str):
        raise AuditBlocked("external relevant status is invalid")
    if not isinstance(identity["overall_dirty_at_registration"], bool):
        raise AuditBlocked("external dirty flag is invalid")
    if not _is_sha256(identity["overall_status_sha256"]):
        raise AuditBlocked("external status hash is invalid")
    files = identity["files"]
    if not isinstance(files, list) or len(files) != len(EXTERNAL_SOURCE_FILES):
        raise AuditBlocked("external source file inventory mismatch")
    normalized = []
    for record_value in files:
        record = dict(_mapping(record_value, "external source file"))
        _require_keys(record, {"path", "sha256", "size_bytes"}, "external source file")
        if record["path"] not in EXTERNAL_SOURCE_FILES or not _is_sha256(
            record["sha256"]
        ):
            raise AuditBlocked("external source file identity is invalid")
        if (
            isinstance(record["size_bytes"], bool)
            or not isinstance(record["size_bytes"], int)
            or record["size_bytes"] <= 0
        ):
            raise AuditBlocked("external source file size is invalid")
        normalized.append(record)
    if [item["path"] for item in normalized] != list(EXTERNAL_SOURCE_FILES):
        raise AuditBlocked("external source files are not in registered order")
    identity["files"] = normalized
    return identity


def validate_registration(value: object) -> dict[str, Any]:
    registration = dict(_mapping(value, "audit registration"))
    _require_keys(
        registration,
        {"audit", "authority", "identity", "schema_version"},
        "audit registration",
    )
    _require_exact(
        registration,
        "schema_version",
        REGISTRATION_SCHEMA_VERSION,
        "audit registration",
    )
    authority = dict(_mapping(registration["authority"], "authority"))
    if authority != _authority():
        raise AuditBlocked("registration authority must remain all false")
    audit = dict(_mapping(registration["audit"], "audit contract"))
    if audit != _audit_contract():
        raise AuditBlocked("audit contract differs from the registered contract")
    identity = dict(_mapping(registration["identity"], "identity"))
    _require_keys(
        identity,
        {
            "external_source",
            "implementation",
            "residual_failure_audit",
            "residual_manifest",
            "residual_verdict",
            "runtime",
            "teacher_policy_id",
            "train_dataset_sha256",
            "train_input",
            "train_input_manifest",
        },
        "identity",
    )
    if identity["teacher_policy_id"] != NATIVE_TARGET_POLICY_ID:
        raise AuditBlocked("teacher policy identity mismatch")
    if identity["residual_verdict"] != "poc_valid_without_route_card_residual":
        raise AuditBlocked("residual lineage verdict mismatch")
    if not _is_sha256(identity["train_dataset_sha256"]):
        raise AuditBlocked("train dataset identity is invalid")
    implementation = dict(_mapping(identity["implementation"], "implementation"))
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "implementation",
    )
    if (
        not _is_commit(implementation["commit"])
        or implementation["source_files"] != list(REGISTERED_SOURCE_FILES)
        or not _is_sha256(implementation["source_sha256"])
    ):
        raise AuditBlocked("implementation identity is invalid")
    runtime = dict(_mapping(identity["runtime"], "runtime"))
    _require_keys(runtime, {"python", "torch"}, "runtime")
    if any(not isinstance(runtime[name], str) or not runtime[name] for name in runtime):
        raise AuditBlocked("runtime identity is invalid")
    for name in (
        "residual_failure_audit",
        "residual_manifest",
        "train_input",
        "train_input_manifest",
    ):
        identity[name] = dict(_mapping(identity[name], name))
        if set(identity[name]) != {"path", "sha256", "size_bytes"}:
            raise AuditBlocked(f"{name} binding keys mismatch")
        if not _is_sha256(identity[name]["sha256"]):
            raise AuditBlocked(f"{name} binding hash is invalid")
    identity["external_source"] = _validate_external_contract(
        identity["external_source"]
    )
    identity["implementation"] = implementation
    identity["runtime"] = runtime
    registration["audit"] = audit
    registration["authority"] = authority
    registration["identity"] = identity
    return registration


def load_registration(path: Path | str) -> dict[str, Any]:
    return validate_registration(_load_json(path, "teacher sufficiency registration"))


def _torch_version() -> str:
    try:
        import torch
    except ImportError as exc:
        raise AuditBlocked("PyTorch is required to audit registered feature vectors") from exc
    return str(torch.__version__)


def build_registration(
    *,
    repo_root: Path,
    external_repo_root: Path,
    implementation_commit: str,
    train_input_path: Path | str,
    train_input_manifest_path: Path | str,
    residual_manifest_path: Path | str,
    residual_failure_audit_path: Path | str,
) -> dict[str, Any]:
    if not _is_commit(implementation_commit):
        raise AuditBlocked("implementation commit is invalid")
    try:
        source_sha256 = hash_bound_files(repo_root, REGISTERED_SOURCE_FILES)
        _verify_sources_at_commit(repo_root, implementation_commit, REGISTERED_SOURCE_FILES)
    except Exception as exc:
        raise AuditBlocked(f"cannot bind implementation sources: {exc}") from exc
    train_input = load_train_input_archive(
        train_input_path,
        manifest_path=train_input_manifest_path,
        expected_seeds=REGISTERED_TRAIN_SEEDS,
    )
    train_manifest = _load_json(train_input_manifest_path, "train input manifest")
    if train_manifest.get("schema_version") != TRAIN_INPUT_MANIFEST_SCHEMA_VERSION:
        raise AuditBlocked("train input manifest schema mismatch")
    if train_manifest.get("train_dataset_sha256") != train_input["source"][
        "train_dataset_sha256"
    ]:
        raise AuditBlocked("train input manifest dataset identity mismatch")
    residual_manifest = _load_json(residual_manifest_path, "residual manifest")
    if residual_manifest.get("verdict") != "poc_valid_without_route_card_residual":
        raise AuditBlocked("residual lineage is not the terminal negative")
    if any(bool(item) for item in residual_manifest.get("authority", {}).values()):
        raise AuditBlocked("residual lineage has downstream authority")
    registration = {
        "audit": _audit_contract(),
        "authority": _authority(),
        "identity": {
            "external_source": _external_identity(external_repo_root),
            "implementation": {
                "commit": implementation_commit,
                "source_files": list(REGISTERED_SOURCE_FILES),
                "source_sha256": source_sha256,
            },
            "residual_failure_audit": _binding_for_path(
                repo_root, residual_failure_audit_path
            ),
            "residual_manifest": _binding_for_path(repo_root, residual_manifest_path),
            "residual_verdict": "poc_valid_without_route_card_residual",
            "runtime": {
                "python": ".".join(map(str, sys.version_info[:3])),
                "torch": _torch_version(),
            },
            "teacher_policy_id": NATIVE_TARGET_POLICY_ID,
            "train_dataset_sha256": train_input["source"]["train_dataset_sha256"],
            "train_input": _binding_for_path(repo_root, train_input_path),
            "train_input_manifest": _binding_for_path(
                repo_root, train_input_manifest_path
            ),
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
        "residual_failure_audit",
        "residual_manifest",
        "train_input",
        "train_input_manifest",
    ):
        if _actual_binding(repo_root, identity[name]) != identity[name]:
            raise AuditBlocked(f"registered binding mismatch: {name}")
    implementation = identity["implementation"]
    try:
        actual_source_sha256 = hash_bound_files(
            repo_root, implementation["source_files"]
        )
        _verify_sources_at_commit(
            repo_root, implementation["commit"], implementation["source_files"]
        )
    except Exception as exc:
        raise AuditBlocked(f"implementation identity failed: {exc}") from exc
    if actual_source_sha256 != implementation["source_sha256"]:
        raise AuditBlocked("implementation source hash mismatch")
    runtime = {
        "python": ".".join(map(str, sys.version_info[:3])),
        "torch": _torch_version(),
    }
    if runtime != identity["runtime"]:
        raise AuditBlocked("registered runtime mismatch")
    external = validate_external_identity(identity["external_source"])
    external_root = Path(external["repo_path"])
    train_input = load_train_input_archive(
        repo_root / identity["train_input"]["path"],
        manifest_path=repo_root / identity["train_input_manifest"]["path"],
        expected_seeds=value["audit"]["seeds"],
    )
    if train_input["source"]["train_dataset_sha256"] != identity[
        "train_dataset_sha256"
    ]:
        raise AuditBlocked("registered train dataset identity mismatch")
    residual = _load_json(
        repo_root / identity["residual_manifest"]["path"], "residual manifest"
    )
    if residual.get("verdict") != identity["residual_verdict"] or any(
        bool(item) for item in residual.get("authority", {}).values()
    ):
        raise AuditBlocked("registered residual lineage mismatch")
    return {
        "external_commit": external["commit"],
        "implementation_commit": implementation["commit"],
        "implementation_source_sha256": actual_source_sha256,
        "runtime": runtime,
        "train_dataset_sha256": identity["train_dataset_sha256"],
    }


def validate_external_identity(value: object) -> dict[str, Any]:
    external = _validate_external_contract(value)
    external_root = Path(external["repo_path"])
    if _git_output(external_root, "rev-parse", "HEAD") != external["commit"]:
        raise AuditBlocked("external source commit mismatch")
    relevant_status = _git_output(
        external_root, "status", "--short", "--", *EXTERNAL_SOURCE_FILES
    )
    if relevant_status != external["relevant_status"]:
        raise AuditBlocked("external relevant-file status mismatch")
    if _external_file_records(external_root) != external["files"]:
        raise AuditBlocked("external physical source identity mismatch")
    return external


def _matching_brace(text: str, opening: int) -> int:
    if opening < 0 or opening >= len(text) or text[opening] != "{":
        raise AuditBlocked("source block opening brace is invalid")
    depth = 0
    state = "normal"
    quote = ""
    index = opening
    while index < len(text):
        char = text[index]
        next_char = text[index + 1] if index + 1 < len(text) else ""
        if state == "line_comment":
            if char == "\n":
                state = "normal"
        elif state == "block_comment":
            if char == "*" and next_char == "/":
                state = "normal"
                index += 1
        elif state == "string":
            if char == "\\":
                index += 1
            elif char == quote:
                state = "normal"
        elif char == "/" and next_char == "/":
            state = "line_comment"
            index += 1
        elif char == "/" and next_char == "*":
            state = "block_comment"
            index += 1
        elif char in {'"', "'"}:
            state = "string"
            quote = char
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return index
            if depth < 0:
                break
        index += 1
    raise AuditBlocked("source block has no matching closing brace")


def extract_braced_block(text: str, anchor: str) -> dict[str, Any]:
    start = text.find(anchor)
    if start < 0 or text.find(anchor, start + 1) >= 0:
        raise AuditBlocked(f"source anchor must occur exactly once: {anchor}")
    opening = text.find("{", start + len(anchor))
    if opening < 0:
        raise AuditBlocked(f"source anchor has no opening brace: {anchor}")
    closing = _matching_brace(text, opening)
    block = text[start : closing + 1]
    return {
        "anchor": anchor,
        "end_line": text.count("\n", 0, closing) + 1,
        "sha256": sha256_bytes(block.encode("utf-8")),
        "start_line": text.count("\n", 0, start) + 1,
        "text": block,
    }


def parse_source_facts(
    *,
    simple_agent_cpp: str,
    simple_agent_h: str,
    card_cpp: str,
    rooms_h: str,
    adapter_cpp: str,
) -> dict[str, Any]:
    route = extract_braced_block(simple_agent_cpp, ROUTE_FUNCTION_ANCHOR)
    map_screen_start = simple_agent_cpp.find(MAP_SCREEN_ANCHOR)
    if map_screen_start < 0 or simple_agent_cpp.find(
        MAP_SCREEN_ANCHOR, map_screen_start + 1
    ) >= 0:
        raise AuditBlocked("map screen anchor must occur exactly once")
    map_screen_end = simple_agent_cpp.find("case ScreenState::TREASURE_ROOM", map_screen_start)
    if map_screen_end < 0:
        raise AuditBlocked("map screen block terminator is missing")
    map_screen_text = simple_agent_cpp[map_screen_start:map_screen_end]
    map_screen = {
        "anchor": MAP_SCREEN_ANCHOR,
        "end_line": simple_agent_cpp.count("\n", 0, map_screen_end) + 1,
        "sha256": sha256_bytes(map_screen_text.encode("utf-8")),
        "start_line": simple_agent_cpp.count("\n", 0, map_screen_start) + 1,
        "text": map_screen_text,
    }
    card = extract_braced_block(simple_agent_cpp, CARD_FUNCTION_ANCHOR)
    weights_block = extract_braced_block(simple_agent_cpp, MAP_WEIGHTS_ANCHOR)
    weights_body = weights_block["text"][weights_block["text"].find("{") :]
    weights = [int(item) for item in re.findall(r"-?\d+", weights_body)]
    if len(weights) != 18:
        raise AuditBlocked("map weight table must contain exactly 18 values")
    map_weights = [weights[index : index + 6] for index in range(0, 18, 6)]
    priorities_block = extract_braced_block(simple_agent_cpp, CARD_PRIORITIES_ANCHOR)
    card_priorities = re.findall(r"CardId::([A-Z0-9_]+)", priorities_block["text"])
    if len(card_priorities) != 133:
        raise AuditBlocked("card priority table must contain exactly 133 entries")
    copies_block = extract_braced_block(simple_agent_cpp, MAX_COPIES_ANCHOR)
    max_copies = {
        name: int(limit)
        for name, limit in re.findall(
            r"\{\s*CardId::([A-Z0-9_]+)\s*,\s*(\d+)\s*\}",
            copies_block["text"],
        )
    }
    if not max_copies:
        raise AuditBlocked("maxCopies table is empty or unparseable")
    adapter_cards = extract_braced_block(adapter_cpp, ADAPTER_CARD_CANDIDATES_ANCHOR)
    adapter_native = extract_braced_block(adapter_cpp, ADAPTER_NATIVE_ACTION_ANCHOR)
    card_equality = extract_braced_block(card_cpp, CARD_EQUALITY_ANCHOR)
    required_route_tokens = (
        "mapPath = getBestMapPathForWeights(*gc.map, mapWeights[gc.act-1])",
        "mapPath[gc.curMapNodeY+1]",
        "gc.curMapNodeY < 0",
    )
    if any(token not in map_screen_text for token in required_route_tokens):
        raise AuditBlocked("map-screen source contract changed")
    if "for (auto c : lastCardReward)" not in card["text"]:
        raise AuditBlocked("card-reward offer-count loop is missing")
    if "gc.deck" in card["text"]:
        raise AuditBlocked("registered card-reward source unexpectedly reads gc.deck")
    if "lastRewardIdx, 5" not in card["text"]:
        raise AuditBlocked("registered card-reward skip action changed")
    if "fixed_list<int,16> mapPath" not in simple_agent_h:
        raise AuditBlocked("SimpleAgent mapPath member is missing")
    room_names = re.findall(r'"([A-Z_]+)"', rooms_h)
    expected_rooms = [
        "SHOP",
        "REST",
        "EVENT",
        "ELITE",
        "MONSTER",
        "TREASURE",
        "BOSS",
        "BOSS_TREASURE",
        "NONE",
        "INVALID",
    ]
    if room_names[: len(expected_rooms)] != expected_rooms:
        raise AuditBlocked("Room enum/string order changed")
    if "Candidate::Mode::CARD_BOWL" not in adapter_cards["text"] or (
        "Candidate::Mode::CARD_SKIP" not in adapter_cards["text"]
    ):
        raise AuditBlocked("adapter skip/bowl mapping changed")
    if "probe.baselineAgent_.stepCardReward" not in adapter_native["text"]:
        raise AuditBlocked("adapter native card target mapping changed")
    equality_fields = re.findall(r"(?:return|&&)\s*(id|misc|upgraded)\s*==", card_equality["text"])
    if equality_fields != ["id", "misc", "upgraded"]:
        raise AuditBlocked("Card equality source contract changed")
    blocks = {}
    for name, block in (
        ("adapter_card_candidates", adapter_cards),
        ("adapter_native_action", adapter_native),
        ("card_equality", card_equality),
        ("card_reward", card),
        ("card_priorities", priorities_block),
        ("map_screen", map_screen),
        ("map_weights", weights_block),
        ("max_copies", copies_block),
        ("route", route),
    ):
        blocks[name] = {key: block[key] for key in block if key != "text"}
    return {
        "blocks": blocks,
        "card": {
            "card_priority_count": len(card_priorities),
            "card_priority_duplicate_count": len(card_priorities)
            - len(set(card_priorities)),
            "card_priority_order": card_priorities,
            "equality_fields": equality_fields,
            "copy_limit_count": len(max_copies),
            "copy_limits": dict(sorted(max_copies.items())),
            "default_priority": 0,
            "offer_count_used_for_copy_limit": True,
            "reads_actual_deck": False,
            "reads_run_context": False,
            "skip_action_index": 5,
            "values_singing_bowl": False,
        },
        "route": {
            "cached_path_member": "mapPath",
            "map_weights": map_weights,
            "reads_current_gold": "gc.gold" in map_screen_text + route["text"],
            "reads_current_hp": "gc.curHp" in map_screen_text + route["text"],
            "replans_only_at_map_entry": "gc.curMapNodeY < 0" in map_screen_text,
            "strict_final_tie_keeps_first": "path.weight > bestPathWeight" in route["text"],
            "strict_path_tie_keeps_existing": "path.weight < curPath.weight + roomWeight"
            in route["text"],
        },
        "schema_version": SOURCE_FACTS_SCHEMA_VERSION,
    }


def load_source_facts(registration: Mapping[str, Any], *, repo_root: Path) -> dict[str, Any]:
    external_root = Path(registration["identity"]["external_source"]["repo_path"])
    return parse_source_facts(
        simple_agent_cpp=(external_root / "src/sim/search/SimpleAgent.cpp").read_text(
            encoding="utf-8"
        ),
        simple_agent_h=(external_root / "include/sim/search/SimpleAgent.h").read_text(
            encoding="utf-8"
        ),
        card_cpp=(external_root / "src/game/Card.cpp").read_text(encoding="utf-8"),
        rooms_h=(external_root / "include/constants/Rooms.h").read_text(
            encoding="utf-8"
        ),
        adapter_cpp=(
            repo_root / "simulator_adapters/sts_lightspeed/noncombat_adapter.cpp"
        ).read_text(encoding="utf-8"),
    )


def _map_nodes(state: Mapping[str, Any]) -> dict[tuple[int, int], dict[str, Any]]:
    map_value = _mapping(state.get("map"), "route state map")
    nodes = map_value.get("nodes")
    if not isinstance(nodes, list):
        raise AuditBlocked("route map nodes must be a list")
    result = {}
    for node_value in nodes:
        node = dict(_mapping(node_value, "route map node"))
        x = node.get("x")
        y = node.get("y")
        if (
            isinstance(x, bool)
            or not isinstance(x, int)
            or not 0 <= x <= 6
            or isinstance(y, bool)
            or not isinstance(y, int)
            or not 0 <= y <= 14
        ):
            raise AuditBlocked("route map node coordinates are invalid")
        key = (x, y)
        if key in result:
            raise AuditBlocked("route map node coordinates are duplicated")
        edges = node.get("edges")
        if not isinstance(edges, list):
            raise AuditBlocked("route map edges must be a list")
        normalized_edges = []
        for edge_value in edges:
            edge = _mapping(edge_value, "route map edge")
            edge_x = edge.get("x")
            edge_y = edge.get("y")
            if (
                isinstance(edge_x, bool)
                or not isinstance(edge_x, int)
                or not 0 <= edge_x <= 6
                or edge_y != y + 1
            ):
                raise AuditBlocked("route map edge is invalid")
            normalized_edges.append(edge_x)
        result[key] = {"edges": normalized_edges, "room": str(node.get("room"))}
    return result


def reconstruct_route_action(
    state: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    source_facts: Mapping[str, Any],
) -> str:
    act = state.get("act")
    if isinstance(act, bool) or not isinstance(act, int) or not 1 <= act <= 3:
        raise AuditBlocked("registered route rows require act 1 through 3")
    current = _mapping(state.get("cur_map_node"), "current map node")
    current_y = current.get("y")
    if isinstance(current_y, bool) or not isinstance(current_y, int):
        raise AuditBlocked("current map y is invalid")
    target_path_index = current_y + 1
    if not 0 <= target_path_index <= 15:
        raise AuditBlocked("current map y is outside the cached path")
    nodes = _map_nodes(state)
    weights = source_facts["route"]["map_weights"][act - 1]
    room_index = {
        "SHOP": 0,
        "REST": 1,
        "EVENT": 2,
        "ELITE": 3,
        "MONSTER": 4,
        "TREASURE": 5,
    }

    def empty_path() -> dict[str, Any]:
        return {"route": [], "weight": 0}

    paths1 = [empty_path() for _ in range(7)]
    paths2 = [empty_path() for _ in range(7)]
    for x in range(7):
        node = nodes.get((x, 0), {"edges": [], "room": "NONE"})
        if node["edges"]:
            room = node["room"]
            if room not in room_index:
                raise AuditBlocked(f"unsupported route room at map entry: {room}")
            paths1[x] = {"route": [x], "weight": weights[room_index[room]]}
    last_paths = paths1
    next_paths = paths2
    for y in range(14):
        for x in range(7):
            node = nodes.get((x, y), {"edges": [], "room": "NONE"})
            if not node["edges"]:
                continue
            current_path = last_paths[x]
            for edge_x in node["edges"]:
                target = nodes.get((edge_x, y + 1))
                if target is None or target["room"] not in room_index:
                    raise AuditBlocked("route edge target is missing or unsupported")
                room_weight = weights[room_index[target["room"]]]
                existing = next_paths[edge_x]
                proposed_weight = current_path["weight"] + room_weight
                proposed_size = len(current_path["route"]) + 1
                if (
                    len(existing["route"]) < proposed_size
                    or existing["weight"] < proposed_weight
                ):
                    next_paths[edge_x] = {
                        "route": [*current_path["route"], edge_x],
                        "weight": proposed_weight,
                    }
        last_paths, next_paths = next_paths, last_paths
    best_x = None
    best_weight = 0
    for x in range(7):
        path = paths1[x]
        if path["weight"] > best_weight:
            best_weight = path["weight"]
            best_x = x
    if best_x is None:
        raise AuditBlocked("route source evaluator found no weighted path")
    map_path = [*paths1[best_x]["route"], 0]
    if len(map_path) != 16:
        raise AuditBlocked("route source evaluator did not produce 16 coordinates")
    selected_x = map_path[target_path_index]
    expected_id = f"route:map_node:{selected_x}:{target_path_index}"
    matches = [item for item in candidates if item.get("action_id") == expected_id]
    if len(matches) != 1:
        raise AuditBlocked("reconstructed route action does not map exactly once")
    return expected_id


def _card_semantic_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    kind = str(candidate.get("kind"))
    raw = _mapping(candidate.get("raw"), "card candidate raw")
    if kind == "take":
        return (
            kind,
            str(raw.get("id")),
            bool(raw.get("upgraded")),
            int(raw.get("upgrade_count", 0)),
            int(raw.get("misc", 0)),
        )
    return (kind,)


def _card_equality_key(candidate: Mapping[str, Any]) -> tuple[Any, ...]:
    raw = _mapping(candidate.get("raw"), "card candidate raw")
    return (
        str(raw.get("id")),
        int(raw.get("misc", 0)),
        bool(raw.get("upgraded")),
    )


def semantic_action_key(
    category: str, candidate: Mapping[str, Any]
) -> tuple[Any, ...]:
    if category == "card_reward":
        return _card_semantic_key(candidate)
    if category == "route":
        raw = _mapping(candidate.get("raw"), "route candidate raw")
        return ("map_node", int(raw.get("x")), int(raw.get("y")))
    raise AuditBlocked(f"unsupported semantic action category: {category}")


def reconstruct_card_reward_action(
    candidates: Sequence[Mapping[str, Any]], source_facts: Mapping[str, Any]
) -> str:
    offered = [item for item in candidates if item.get("kind") == "take"]
    if not offered:
        raise AuditBlocked("card reward contains no take candidate")
    counts = Counter(str(_mapping(item.get("raw"), "card raw").get("id")) for item in offered)
    copy_limits = source_facts["card"]["copy_limits"]
    pickable = []
    for candidate in offered:
        card_id = str(_mapping(candidate.get("raw"), "card raw").get("id"))
        if card_id not in copy_limits or counts[card_id] < copy_limits[card_id]:
            pickable.append(candidate)
    if not pickable:
        skips = [item for item in candidates if item.get("kind") in {"skip", "bowl"}]
        if len(skips) != 1:
            raise AuditBlocked("card reward skip/bowl candidate must map exactly once")
        return str(skips[0]["action_id"])
    priorities = {
        card_id: index + 1
        for index, card_id in enumerate(source_facts["card"]["card_priority_order"])
    }
    best_score = 10000
    best_candidate = None
    for candidate in pickable:
        raw = _mapping(candidate.get("raw"), "card raw")
        score = 2 * priorities.get(str(raw.get("id")), 0) + (
            -1 if bool(raw.get("upgraded")) else 0
        )
        if score < best_score:
            best_score = score
            best_candidate = candidate
    if best_candidate is None:
        raise AuditBlocked("card source evaluator found no best candidate")
    best_equality = _card_equality_key(best_candidate)
    for candidate in offered:
        if _card_equality_key(candidate) == best_equality:
            return str(candidate["action_id"])
    raise AuditBlocked("card source evaluator could not remap selected card")


def build_dependency_coverage(source_facts: Mapping[str, Any]) -> dict[str, Any]:
    def entry(
        dependency_id: str,
        category: str,
        source_input: str,
        role: str,
        raw_adapter: str,
        legacy: str,
        structured: str,
        evidence: str,
    ) -> dict[str, str]:
        return {
            "category": category,
            "dependency_id": dependency_id,
            "evidence": evidence,
            "legacy_projection": legacy,
            "raw_adapter": raw_adapter,
            "role": role,
            "source_input": source_input,
            "structured_projection": structured,
        }

    dependencies = [
        entry(
            "route.act",
            "route",
            "gc.act",
            "selects one of three fixed room-weight tables",
            "directly_represented",
            "directly_represented",
            "directly_represented",
            "source_facts.route.map_weights",
        ),
        entry(
            "route.map_topology_and_rooms",
            "route",
            "gc.map nodes, ordered edges, and room enum",
            "determines the complete cached maximum-weight route",
            "directly_represented",
            "directly_represented",
            "missing_exact_dependency",
            "source_facts.blocks.route",
        ),
        entry(
            "route.current_map_y",
            "route",
            "gc.curMapNodeY",
            "indexes the next coordinate in the cached route",
            "directly_represented",
            "directly_represented",
            "directly_represented",
            "source_facts.blocks.map_screen",
        ),
        entry(
            "route.cached_map_path",
            "route",
            "SimpleAgent.mapPath",
            "persists the map-entry route across later choices",
            "deterministically_derivable",
            "deterministically_derivable",
            "missing_exact_dependency",
            "source_facts.route.cached_path_member",
        ),
        entry(
            "route.map_weights",
            "route",
            "mapWeights[act-1]",
            "fixed teacher-policy parameters",
            "policy_constant",
            "policy_constant",
            "policy_constant",
            "source_facts.route.map_weights",
        ),
        entry(
            "route.source_order_ties",
            "route",
            "ordered x/edge loops and strict comparisons",
            "keeps the first path on equal weight",
            "policy_constant",
            "policy_constant",
            "policy_constant",
            "source_facts.route.strict_path_tie_keeps_existing",
        ),
        entry(
            "card.identity_and_upgrade",
            "card_reward",
            "lastCardReward card id and upgraded flag",
            "computes static card priority",
            "directly_represented",
            "directly_represented",
            "directly_represented",
            "source_facts.blocks.card_reward",
        ),
        entry(
            "card.offer_order",
            "card_reward",
            "lastCardReward iteration order",
            "keeps the first card on equal priority and equality remap",
            "directly_represented",
            "directly_represented",
            "missing_exact_dependency",
            "source_facts.blocks.card_reward",
        ),
        entry(
            "card.offer_local_counts",
            "card_reward",
            "deckCounts populated from lastCardReward",
            "applies the copy-limit table to offer multiplicity",
            "directly_represented",
            "directly_represented",
            "directly_represented",
            "source_facts.card.offer_count_used_for_copy_limit",
        ),
        entry(
            "card.equality_remap_fields",
            "card_reward",
            "Card::operator== id, misc, and upgraded fields",
            "maps the selected Card value back to the first equal reward slot",
            "directly_represented",
            "directly_represented",
            "directly_represented",
            "source_facts.card.equality_fields",
        ),
        entry(
            "card.priority_and_copy_tables",
            "card_reward",
            "cardPriorityMap and maxCopies",
            "fixed teacher-policy parameters",
            "policy_constant",
            "policy_constant",
            "policy_constant",
            "source_facts.card",
        ),
        entry(
            "card.skip_or_bowl_mapping",
            "card_reward",
            "adapter candidate mapped from GameAction card index 5",
            "maps the teacher skip bits to one legal action id",
            "directly_represented",
            "directly_represented",
            "directly_represented",
            "source_facts.blocks.adapter_card_candidates",
        ),
        entry(
            "card.actual_deck",
            "card_reward",
            "gc.deck",
            "available run context not read by the teacher",
            "intentionally_irrelevant_to_teacher",
            "intentionally_irrelevant_to_teacher",
            "intentionally_irrelevant_to_teacher",
            "source_facts.card.reads_actual_deck",
        ),
        entry(
            "card.other_run_context",
            "card_reward",
            "act, floor, hp, gold, boss, relics, and potions",
            "available run context not read by the teacher",
            "intentionally_irrelevant_to_teacher",
            "intentionally_irrelevant_to_teacher",
            "intentionally_irrelevant_to_teacher",
            "source_facts.card.reads_run_context",
        ),
    ]
    allowed = {
        "deterministically_derivable",
        "directly_represented",
        "intentionally_irrelevant_to_teacher",
        "missing_exact_dependency",
        "policy_constant",
    }
    if any(
        item[layer] not in allowed
        for item in dependencies
        for layer in ("raw_adapter", "legacy_projection", "structured_projection")
    ):
        raise AuditBlocked("dependency coverage contains an unknown classification")
    summary = {}
    for layer in ("raw_adapter", "legacy_projection", "structured_projection"):
        counts = Counter(item[layer] for item in dependencies)
        summary[layer] = {
            "by_status": {name: counts[name] for name in sorted(allowed)},
            "missing_dependency_ids": [
                item["dependency_id"]
                for item in dependencies
                if item[layer] == "missing_exact_dependency"
            ],
        }
    return {
        "dependencies": dependencies,
        "raw_adapter_actionable_gap_count": len(
            summary["raw_adapter"]["missing_dependency_ids"]
        ),
        "schema_version": DEPENDENCY_SCHEMA_VERSION,
        "summary": summary,
    }


def _source_signature_payload(
    *,
    category: str,
    state: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    source_facts: Mapping[str, Any],
) -> dict[str, Any]:
    if category == "route":
        return {
            "act": state.get("act"),
            "candidates": [semantic_action_key(category, item) for item in candidates],
            "cur_map_node_y": _mapping(
                state.get("cur_map_node"), "current map node"
            ).get("y"),
            "map": copy.deepcopy(state.get("map")),
            "map_weights": source_facts["route"]["map_weights"],
            "tie_rule": "strict-first-existing-v1",
        }
    return {
        "candidates": [semantic_action_key(category, item) for item in candidates],
        "card_priority_order": source_facts["card"]["card_priority_order"],
        "copy_limits": source_facts["card"]["copy_limits"],
        "default_priority": source_facts["card"]["default_priority"],
        "tie_rule": "first-minimum-in-offer-order-v1",
    }


def _tensor_row_hashes(tensor: Any, *, expected_width: int) -> list[str]:
    torch = __import__("torch")
    value = tensor.detach().to(device="cpu", dtype=torch.float32).contiguous()
    if value.ndim != 2 or value.shape[1] != expected_width:
        raise AuditBlocked("feature matrix shape mismatch")
    if not torch.isfinite(value).all().item():
        raise AuditBlocked("feature matrix contains non-finite values")
    return [sha256_bytes(row.contiguous().numpy().tobytes()) for row in value]


def build_representation_row(
    row: Mapping[str, Any], source_facts: Mapping[str, Any]
) -> dict[str, Any]:
    category = str(row.get("category"))
    if category not in AUDITED_CATEGORIES:
        raise AuditBlocked("representation row category is not audited")
    snapshot = _mapping(row.get("source_snapshot"), "source snapshot")
    state = _mapping(snapshot.get("state"), "source state")
    candidates_value = row.get("candidate_actions")
    if not isinstance(candidates_value, list) or len(candidates_value) < 2:
        raise AuditBlocked("representation rows must have multiple candidates")
    candidates = [dict(_mapping(item, "candidate")) for item in candidates_value]
    target_id = str(_mapping(row.get("teacher"), "teacher").get("action_id"))
    candidate_ids = [str(item.get("action_id")) for item in candidates]
    if candidate_ids.count(target_id) != 1:
        raise AuditBlocked("representation target must map exactly once")
    target_index = candidate_ids.index(target_id)
    semantic_keys = [list(semantic_action_key(category, item)) for item in candidates]
    source_payload = _source_signature_payload(
        category=category,
        state=state,
        candidates=candidates,
        source_facts=source_facts,
    )
    source_shared = sha256_bytes(canonical_json_bytes(source_payload))
    source_candidates = [
        sha256_bytes(
            canonical_json_bytes(
                {"candidate": semantic_keys[index], "source": source_shared}
            )
        )
        for index in range(len(candidates))
    ]
    adapter_candidates = [
        sha256_bytes(canonical_json_bytes(project_policy_view(state, candidate)))
        for candidate in candidates
    ]
    legacy_candidates = _tensor_row_hashes(
        _candidate_features(state, candidates, hash_dim=1024), expected_width=1024
    )
    structured_vectors = __import__("torch").stack(
        [
            vectorize_structured_features(
                structured_feature_map(state, candidate, category=category),
                hash_dim=2048,
            )
            for candidate in candidates
        ]
    )
    structured_candidates = _tensor_row_hashes(
        structured_vectors, expected_width=2048
    )
    candidate_signatures = {
        "adapter-observable-v1": adapter_candidates,
        "legacy-hash-1024-v1": legacy_candidates,
        "structured-hash-2048-v1": structured_candidates,
        "teacher-source-v1": source_candidates,
    }
    representations = {}
    for signature_id in SIGNATURE_IDS:
        signatures = candidate_signatures[signature_id]
        representations[signature_id] = {
            "candidate_signatures": signatures,
            "decision_signature": sha256_bytes(
                canonical_json_bytes(
                    {"candidate_signatures": signatures, "category": category}
                )
            ),
        }
    return {
        "category": category,
        "candidate_action_ids": candidate_ids,
        "representations": representations,
        "row_id": f"{row.get('seed')}:{row.get('decision_index')}",
        "seed": row.get("seed"),
        "semantic_action_keys": semantic_keys,
        "target_action_id": target_id,
        "target_index": target_index,
    }


def _bounded_examples(values: Sequence[Any], limit: int = 20) -> list[Any]:
    return list(values[:limit])


def _representation_metrics(rows: Sequence[Mapping[str, Any]], signature_id: str) -> dict[str, Any]:
    decision_groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    pair_directions: dict[tuple[str, str], dict[str, set[str]]] = defaultdict(
        lambda: defaultdict(set)
    )
    candidate_signatures: set[str] = set()
    alias_class_count = 0
    alias_rows: set[str] = set()
    non_equivalent_alias_rows: set[str] = set()
    target_alias_rows: set[str] = set()
    impossible_target_tie_rows: set[str] = set()
    semantic_duplicate_rows: set[str] = set()
    for row in rows:
        representation = row["representations"][signature_id]
        signatures = representation["candidate_signatures"]
        target_index = row["target_index"]
        decision_groups[representation["decision_signature"]].append(row)
        candidate_signatures.update(signatures)
        signature_indices: dict[str, list[int]] = defaultdict(list)
        semantic_indices: dict[str, list[int]] = defaultdict(list)
        for index, signature in enumerate(signatures):
            signature_indices[signature].append(index)
            semantic_indices[json.dumps(row["semantic_action_keys"][index])].append(index)
        if any(len(indices) > 1 for indices in semantic_indices.values()):
            semantic_duplicate_rows.add(row["row_id"])
        for indices in signature_indices.values():
            if len(indices) <= 1:
                continue
            alias_class_count += 1
            alias_rows.add(row["row_id"])
            semantic_values = {
                json.dumps(row["semantic_action_keys"][index]) for index in indices
            }
            if len(semantic_values) > 1:
                non_equivalent_alias_rows.add(row["row_id"])
            if target_index in indices:
                target_alias_rows.add(row["row_id"])
                if target_index != min(indices):
                    impossible_target_tie_rows.add(row["row_id"])
        target_signature = signatures[target_index]
        for index, other_signature in enumerate(signatures):
            if index == target_index or other_signature == target_signature:
                continue
            low, high = sorted((target_signature, other_signature))
            direction = "low_over_high" if target_signature == low else "high_over_low"
            pair_directions[(low, high)][direction].add(row["row_id"])
    repeated = [group for group in decision_groups.values() if len(group) > 1]
    conflicting_position = []
    conflicting_semantic = []
    for group in repeated:
        if len({row["target_index"] for row in group}) > 1:
            conflicting_position.append(group)
        target_semantics = {
            json.dumps(row["semantic_action_keys"][row["target_index"]])
            for row in group
        }
        if len(target_semantics) > 1:
            conflicting_semantic.append(group)
    contradictions = []
    contradiction_rows: set[str] = set()
    for (low, high), directions in sorted(pair_directions.items()):
        if set(directions) != {"high_over_low", "low_over_high"}:
            continue
        row_ids = sorted(set().union(*directions.values()))
        contradiction_rows.update(row_ids)
        contradictions.append(
            {
                "candidate_pair": [low, high],
                "high_over_low_rows": sorted(directions["high_over_low"]),
                "low_over_high_rows": sorted(directions["low_over_high"]),
            }
        )
    return {
        "candidate_alias_class_count": alias_class_count,
        "candidate_alias_row_count": len(alias_rows),
        "candidate_alias_row_examples": _bounded_examples(sorted(alias_rows)),
        "conflicting_semantic_target_group_count": len(conflicting_semantic),
        "conflicting_semantic_target_row_count": len(
            {row["row_id"] for group in conflicting_semantic for row in group}
        ),
        "conflicting_target_position_group_count": len(conflicting_position),
        "conflicting_target_position_row_count": len(
            {row["row_id"] for group in conflicting_position for row in group}
        ),
        "decision_group_count": len(decision_groups),
        "impossible_target_tie_row_count": len(impossible_target_tie_rows),
        "impossible_target_tie_row_examples": _bounded_examples(
            sorted(impossible_target_tie_rows)
        ),
        "non_equivalent_candidate_alias_row_count": len(non_equivalent_alias_rows),
        "non_equivalent_candidate_alias_row_examples": _bounded_examples(
            sorted(non_equivalent_alias_rows)
        ),
        "pairwise_contradiction_count": len(contradictions),
        "pairwise_contradiction_examples": _bounded_examples(contradictions),
        "pairwise_contradiction_row_count": len(contradiction_rows),
        "repeated_decision_group_count": len(repeated),
        "repeated_decision_row_count": sum(len(group) for group in repeated),
        "row_count": len(rows),
        "semantic_duplicate_action_row_count": len(semantic_duplicate_rows),
        "semantic_duplicate_action_row_examples": _bounded_examples(
            sorted(semantic_duplicate_rows)
        ),
        "target_candidate_alias_row_count": len(target_alias_rows),
        "unique_candidate_signature_count": len(candidate_signatures),
    }


def build_representation_metrics(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    if not rows:
        raise AuditBlocked("representation metric rows must be nonempty")
    by_signature = {}
    for signature_id in SIGNATURE_IDS:
        by_category = {
            category: _representation_metrics(
                [row for row in rows if row["category"] == category], signature_id
            )
            for category in AUDITED_CATEGORIES
        }
        by_signature[signature_id] = {
            "all": _representation_metrics(rows, signature_id),
            "by_category": by_category,
        }
    return {
        "by_signature": by_signature,
        "multi_candidate_row_count": len(rows),
        "schema_version": METRICS_SCHEMA_VERSION,
    }


def build_teacher_suitability(source_facts: Mapping[str, Any]) -> dict[str, Any]:
    route = source_facts["route"]
    card = source_facts["card"]
    checks = [
        {
            "check_id": "route_replans_with_current_state",
            "critical": True,
            "evidence": "source_facts.route.replans_only_at_map_entry",
            "passed": not bool(route["replans_only_at_map_entry"]),
        },
        {
            "check_id": "route_reads_survivability",
            "critical": True,
            "evidence": "source_facts.route.reads_current_hp",
            "passed": bool(route["reads_current_hp"]),
        },
        {
            "check_id": "route_reads_run_resources",
            "critical": True,
            "evidence": "source_facts.route.reads_current_gold",
            "passed": bool(route["reads_current_gold"]),
        },
        {
            "check_id": "card_copy_limit_uses_actual_deck",
            "critical": True,
            "evidence": "source_facts.card.reads_actual_deck",
            "passed": bool(card["reads_actual_deck"])
            and not bool(card["offer_count_used_for_copy_limit"]),
        },
        {
            "check_id": "card_reads_deck_and_run_context",
            "critical": True,
            "evidence": "source_facts.card.reads_actual_deck/read_run_context",
            "passed": bool(card["reads_actual_deck"])
            and bool(card["reads_run_context"]),
        },
        {
            "check_id": "card_values_skip_vs_bowl",
            "critical": True,
            "evidence": "source_facts.card.values_singing_bowl",
            "passed": bool(card["values_singing_bowl"]),
        },
    ]
    if [item["check_id"] for item in checks] != _audit_contract()[
        "suitability_checks"
    ]:
        raise AuditBlocked("teacher suitability check inventory drifted")
    failed = [item["check_id"] for item in checks if item["critical"] and not item["passed"]]
    return {
        "checks": checks,
        "critical_failed_check_ids": failed,
        "policy_quality_gate_suitable": not failed,
        "schema_version": SUITABILITY_SCHEMA_VERSION,
    }


def classify_verdict(
    *, blockers: Sequence[str], adapter_gap_reasons: Sequence[str], suitability_failures: Sequence[str]
) -> str:
    if blockers:
        return "blocked"
    if adapter_gap_reasons:
        return "adapter_representation_repair_required"
    if suitability_failures:
        return "simpleagent_unsuitable_as_policy_quality_gate"
    return "audit_inconclusive"


def execute_audit(
    *,
    registration: Mapping[str, Any],
    train_input: Mapping[str, Any],
    source_facts: Mapping[str, Any],
) -> dict[str, Any]:
    value = validate_registration(registration)
    normalized_input = validate_train_input(
        copy.deepcopy(train_input), expected_seeds=value["audit"]["seeds"]
    )
    dataset = normalized_input["dataset"]
    rows = dataset["rows"]
    limits = value["audit"]["limits"]
    if len(rows) > limits["max_rows"]:
        raise AuditBlocked("train corpus exceeds the registered row bound")
    if normalized_input["source"]["train_dataset_sha256"] != value["identity"][
        "train_dataset_sha256"
    ]:
        raise AuditBlocked("train corpus identity differs from registration")

    evidence_rows = []
    representation_rows = []
    reconstruction_mismatches = []
    category_counts = Counter()
    singleton_counts = Counter()
    max_candidate_count = 0
    for row in rows:
        category = str(row.get("category"))
        if category not in AUDITED_CATEGORIES:
            continue
        candidates_value = row.get("candidate_actions")
        if not isinstance(candidates_value, list) or not candidates_value:
            raise AuditBlocked("audited row has no candidates")
        candidates = [dict(_mapping(item, "candidate")) for item in candidates_value]
        if len(candidates) > limits["max_candidates_per_row"]:
            raise AuditBlocked("audited row exceeds the registered candidate bound")
        max_candidate_count = max(max_candidate_count, len(candidates))
        category_counts[category] += 1
        if len(candidates) == 1:
            singleton_counts[category] += 1
        state = _mapping(
            _mapping(row.get("source_snapshot"), "source snapshot").get("state"),
            "source state",
        )
        observed = str(_mapping(row.get("teacher"), "teacher").get("action_id"))
        if category == "route":
            expected = reconstruct_route_action(state, candidates, source_facts)
        else:
            expected = reconstruct_card_reward_action(candidates, source_facts)
        row_id = f"{row.get('seed')}:{row.get('decision_index')}"
        matched = expected == observed
        if not matched:
            reconstruction_mismatches.append(
                {"expected_action_id": expected, "observed_action_id": observed, "row_id": row_id}
            )
        target_candidate = next(
            (item for item in candidates if item.get("action_id") == observed), None
        )
        if target_candidate is None:
            raise AuditBlocked("recorded teacher action is absent from candidates")
        row_evidence = {
            "candidate_count": len(candidates),
            "category": category,
            "expected_action_id": expected,
            "observed_action_id": observed,
            "reconstruction_match": matched,
            "row_id": row_id,
            "seed": row.get("seed"),
            "semantic_target": list(semantic_action_key(category, target_candidate)),
        }
        if len(candidates) > 1:
            representation = build_representation_row(row, source_facts)
            representation_rows.append(representation)
            row_evidence["representation_decision_signatures"] = {
                signature_id: representation["representations"][signature_id][
                    "decision_signature"
                ]
                for signature_id in SIGNATURE_IDS
            }
        evidence_rows.append(row_evidence)
    if set(category_counts) != set(AUDITED_CATEGORIES):
        raise AuditBlocked("audited corpus category coverage is incomplete")
    if not representation_rows:
        raise AuditBlocked("audited corpus has no multi-candidate rows")

    dependencies = build_dependency_coverage(source_facts)
    metrics = build_representation_metrics(representation_rows)
    suitability = build_teacher_suitability(source_facts)
    blockers = []
    if reconstruction_mismatches:
        blockers.append("teacher_action_reconstruction_mismatch")
    adapter_metrics = metrics["by_signature"]["adapter-observable-v1"]["all"]
    adapter_gap_reasons = list(
        dependencies["summary"]["raw_adapter"]["missing_dependency_ids"]
    )
    if adapter_metrics["conflicting_semantic_target_group_count"]:
        adapter_gap_reasons.append("adapter_observable_conflicting_semantic_targets")
    if adapter_metrics["non_equivalent_candidate_alias_row_count"]:
        adapter_gap_reasons.append("adapter_observable_non_equivalent_candidate_alias")
    if adapter_metrics["pairwise_contradiction_count"]:
        adapter_gap_reasons.append("adapter_observable_pairwise_preference_contradiction")
    adapter_gap_reasons = sorted(set(adapter_gap_reasons))
    verdict = classify_verdict(
        blockers=blockers,
        adapter_gap_reasons=adapter_gap_reasons,
        suitability_failures=suitability["critical_failed_check_ids"],
    )
    return {
        "dependency_coverage": dependencies,
        "metrics": metrics,
        "report": {
            "adapter_gap_reasons": adapter_gap_reasons,
            "audited_category_counts": {
                name: category_counts[name] for name in AUDITED_CATEGORIES
            },
            "audited_row_count": sum(category_counts.values()),
            "authority": _authority(),
            "blockers": blockers,
            "max_candidate_count": max_candidate_count,
            "multi_candidate_row_count": len(representation_rows),
            "next_proposal_class": {
                "adapter_representation_repair_required": "adapter-representation-repair",
                "audit_inconclusive": "none-stop-and-reassess",
                "blocked": "none-fix-audit-contract",
                "simpleagent_unsuitable_as_policy_quality_gate": (
                    "outcome-backed-noncombat-rl-readiness"
                ),
            }[verdict],
            "reconstruction_match_count": len(evidence_rows)
            - len(reconstruction_mismatches),
            "reconstruction_mismatch_count": len(reconstruction_mismatches),
            "reconstruction_mismatch_examples": _bounded_examples(
                reconstruction_mismatches
            ),
            "schema_version": REPORT_SCHEMA_VERSION,
            "singleton_counts": {
                name: singleton_counts[name] for name in AUDITED_CATEGORIES
            },
            "suitability_failed_check_ids": suitability[
                "critical_failed_check_ids"
            ],
            "verdict": verdict,
        },
        "row_evidence": {
            "rows": evidence_rows,
            "schema_version": ROW_EVIDENCE_SCHEMA_VERSION,
        },
        "source_facts": copy.deepcopy(source_facts),
        "suitability": suitability,
    }


def _report_markdown(
    *, registration: Mapping[str, Any], execution: Mapping[str, Any]
) -> str:
    report = execution["report"]
    metrics = execution["metrics"]
    dependency = execution["dependency_coverage"]
    lines = [
        "# Non-Combat State/Action and Teacher Sufficiency Audit",
        "",
        f"- Verdict: `{report['verdict']}`",
        f"- Next proposal class: `{report['next_proposal_class']}`",
        f"- Audited rows: {report['audited_row_count']}",
        f"- Multi-candidate rows: {report['multi_candidate_row_count']}",
        (
            "- Teacher reconstruction: "
            f"{report['reconstruction_match_count']}/{report['audited_row_count']} exact"
        ),
        (
            "- Raw adapter missing dependencies: "
            f"{dependency['raw_adapter_actionable_gap_count']}"
        ),
        "",
        "## Representation Evidence",
        "",
        "| Signature | Repeated decision groups | Semantic conflicts | "
        "Non-equivalent aliases | Pairwise contradictions |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]
    for signature_id in SIGNATURE_IDS:
        current = metrics["by_signature"][signature_id]["all"]
        lines.append(
            f"| `{signature_id}` | {current['repeated_decision_group_count']} | "
            f"{current['conflicting_semantic_target_group_count']} | "
            f"{current['non_equivalent_candidate_alias_row_count']} | "
            f"{current['pairwise_contradiction_count']} |"
        )
    lines.extend(
        [
            "",
            "## Teacher Suitability",
            "",
        ]
    )
    for check in execution["suitability"]["checks"]:
        status = "PASS" if check["passed"] else "FAIL"
        lines.append(f"- `{check['check_id']}`: {status} ({check['evidence']})")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This result measures deterministic source closure and representation "
            "aliases on the preserved train corpus. It does not authorize model "
            "fitting, native execution, gameplay, formal RL, qualification, or "
            "policy promotion.",
            "",
            (
                "Registered implementation: `"
                f"{registration['identity']['implementation']['commit']}`"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def _json_artifact(value: Mapping[str, Any]) -> bytes:
    return canonical_json_bytes(value)


def build_artifacts(
    *, registration: Mapping[str, Any], execution: Mapping[str, Any]
) -> dict[str, bytes]:
    value = validate_registration(registration)
    report = execution["report"]
    artifacts = {
        "configuration.json": _json_artifact(value),
        "dependency_coverage.json": _json_artifact(execution["dependency_coverage"]),
        "report.json": _json_artifact(report),
        "report.md": _report_markdown(
            registration=value, execution=execution
        ).encode("utf-8"),
        "representation_metrics.json": _json_artifact(execution["metrics"]),
        "row_evidence.json": _json_artifact(execution["row_evidence"]),
        "source_facts.json": _json_artifact(execution["source_facts"]),
        "teacher_suitability.json": _json_artifact(execution["suitability"]),
    }
    manifest = {
        "artifact_hashes": {
            name: sha256_bytes(payload) for name, payload in sorted(artifacts.items())
        },
        "authority": _authority(),
        "canonical_artifact_names": list(CANONICAL_ARTIFACT_NAMES),
        "configuration_sha256": sha256_bytes(artifacts["configuration.json"]),
        "managed_inventory": [*CANONICAL_ARTIFACT_NAMES, "execution_journal.json"],
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "verdict": report["verdict"],
    }
    artifacts["artifact_manifest.json"] = _json_artifact(manifest)
    validate_artifact_payloads(artifacts)
    return artifacts


def _load_artifact_json(payload: bytes, label: str) -> dict[str, Any]:
    def reject_duplicates(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        result = {}
        for key, value in pairs:
            if key in result:
                raise AuditBlocked(f"{label} contains duplicate key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(payload, object_pairs_hook=reject_duplicates)
    except AuditBlocked:
        raise
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise AuditBlocked(f"{label} is invalid JSON: {exc}") from exc
    return dict(_mapping(value, label))


def validate_artifact_payloads(artifacts: Mapping[str, bytes]) -> dict[str, Any]:
    if set(artifacts) != set(CANONICAL_ARTIFACT_NAMES):
        raise AuditBlocked("canonical artifact inventory mismatch")
    manifest = _load_artifact_json(
        artifacts["artifact_manifest.json"], "artifact manifest"
    )
    _require_keys(
        manifest,
        {
            "artifact_hashes",
            "authority",
            "canonical_artifact_names",
            "configuration_sha256",
            "managed_inventory",
            "schema_version",
            "verdict",
        },
        "artifact manifest",
    )
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise AuditBlocked("artifact manifest schema mismatch")
    if manifest["authority"] != _authority():
        raise AuditBlocked("artifact manifest authority mismatch")
    if manifest["canonical_artifact_names"] != list(CANONICAL_ARTIFACT_NAMES):
        raise AuditBlocked("canonical artifact name list mismatch")
    if manifest["managed_inventory"] != [
        *CANONICAL_ARTIFACT_NAMES,
        "execution_journal.json",
    ]:
        raise AuditBlocked("managed artifact inventory mismatch")
    expected_hashes = {
        name: sha256_bytes(artifacts[name])
        for name in sorted(artifacts)
        if name != "artifact_manifest.json"
    }
    if manifest["artifact_hashes"] != expected_hashes:
        raise AuditBlocked("artifact hash closure mismatch")
    configuration = _load_artifact_json(
        artifacts["configuration.json"], "configuration"
    )
    validate_registration(configuration)
    if manifest["configuration_sha256"] != sha256_bytes(
        artifacts["configuration.json"]
    ):
        raise AuditBlocked("configuration hash mismatch")
    report = _load_artifact_json(artifacts["report.json"], "report")
    if report.get("schema_version") != REPORT_SCHEMA_VERSION:
        raise AuditBlocked("report schema mismatch")
    if report.get("authority") != _authority():
        raise AuditBlocked("report authority mismatch")
    if report.get("verdict") not in VERDICT_ORDER or manifest["verdict"] != report[
        "verdict"
    ]:
        raise AuditBlocked("artifact verdict mismatch")
    expected_schemas = {
        "dependency_coverage.json": DEPENDENCY_SCHEMA_VERSION,
        "representation_metrics.json": METRICS_SCHEMA_VERSION,
        "row_evidence.json": ROW_EVIDENCE_SCHEMA_VERSION,
        "source_facts.json": SOURCE_FACTS_SCHEMA_VERSION,
        "teacher_suitability.json": SUITABILITY_SCHEMA_VERSION,
    }
    for name, schema in expected_schemas.items():
        payload = _load_artifact_json(artifacts[name], name)
        if payload.get("schema_version") != schema:
            raise AuditBlocked(f"{name} schema mismatch")
    try:
        markdown = artifacts["report.md"].decode("utf-8")
    except UnicodeError as exc:
        raise AuditBlocked(f"report Markdown is invalid UTF-8: {exc}") from exc
    if not markdown.startswith(
        "# Non-Combat State/Action and Teacher Sufficiency Audit\n"
    ):
        raise AuditBlocked("report Markdown header mismatch")
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
    if any(root.iterdir()):
        raise AuditBlocked("audit output directory must be empty before publication")
    order = sorted(name for name in artifacts if name != "artifact_manifest.json")
    order.append("artifact_manifest.json")
    installed = []
    temporary = {name: root / f".{name}.tmp" for name in order}
    try:
        for name in order:
            temporary[name].write_bytes(artifacts[name])
        for name in order:
            replace(temporary[name], root / name)
            installed.append(name)
    except Exception:
        for name in installed:
            (root / name).unlink(missing_ok=True)
        raise
    finally:
        for path in temporary.values():
            path.unlink(missing_ok=True)
    validate_artifact_directory(root)


def publish_execution_journal(
    output_dir: Path | str, *, elapsed_seconds: float, wall_time_budget_seconds: float
) -> None:
    if (
        not math.isfinite(elapsed_seconds)
        or elapsed_seconds < 0.0
        or not math.isfinite(wall_time_budget_seconds)
        or wall_time_budget_seconds <= 0.0
    ):
        raise AuditBlocked("execution timing values are invalid")
    root = Path(output_dir)
    validate_artifact_directory(root)
    destination = root / "execution_journal.json"
    if destination.exists():
        raise AuditBlocked("execution journal already exists")
    journal = {
        "canonical": False,
        "elapsed_seconds": elapsed_seconds,
        "schema_version": JOURNAL_SCHEMA_VERSION,
        "wall_time_budget_seconds": wall_time_budget_seconds,
    }
    temporary = root / ".execution_journal.json.tmp"
    temporary.write_bytes(canonical_json_bytes(journal))
    try:
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)
    validate_artifact_directory(root)


def validate_artifact_directory(output_dir: Path | str) -> dict[str, Any]:
    root = Path(output_dir)
    allowed = set(CANONICAL_ARTIFACT_NAMES) | {"execution_journal.json"}
    try:
        entries = {path.name for path in root.iterdir()}
    except OSError as exc:
        raise AuditBlocked(f"cannot inspect artifact directory: {exc}") from exc
    if not set(CANONICAL_ARTIFACT_NAMES).issubset(entries) or not entries.issubset(
        allowed
    ):
        raise AuditBlocked("published artifact inventory mismatch")
    artifacts = {name: (root / name).read_bytes() for name in CANONICAL_ARTIFACT_NAMES}
    manifest = validate_artifact_payloads(artifacts)
    if "execution_journal.json" in entries:
        journal = _load_json(root / "execution_journal.json", "execution journal")
        if (
            journal.get("schema_version") != JOURNAL_SCHEMA_VERSION
            or journal.get("canonical") is not False
        ):
            raise AuditBlocked("execution journal contract mismatch")
    return manifest


def recompute_artifact_directory(
    *,
    output_dir: Path | str,
    registration: Mapping[str, Any],
    train_input: Mapping[str, Any],
    source_facts: Mapping[str, Any],
) -> dict[str, Any]:
    root = Path(output_dir)
    manifest = validate_artifact_directory(root)
    execution = execute_audit(
        registration=registration, train_input=train_input, source_facts=source_facts
    )
    expected = build_artifacts(registration=registration, execution=execution)
    for name in CANONICAL_ARTIFACT_NAMES:
        if (root / name).read_bytes() != expected[name]:
            raise AuditBlocked(f"canonical recomputation mismatch: {name}")
    return manifest


def run_registered_audit(
    *,
    registration: Mapping[str, Any],
    train_input: Mapping[str, Any],
    source_facts: Mapping[str, Any],
    output_dir: Path | str,
) -> dict[str, Any]:
    value = validate_registration(registration)
    start = time.monotonic()
    execution = execute_audit(
        registration=value, train_input=train_input, source_facts=source_facts
    )
    elapsed = time.monotonic() - start
    budget = value["audit"]["limits"]["max_wall_seconds"]
    if elapsed > budget:
        raise AuditBlocked("audit exceeded the registered wall-time bound")
    artifacts = build_artifacts(registration=value, execution=execution)
    publish_artifacts(output_dir, artifacts)
    publish_execution_journal(
        output_dir, elapsed_seconds=elapsed, wall_time_budget_seconds=budget
    )
    return validate_artifact_directory(output_dir)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    register = commands.add_parser("register", description="Freeze the audit inputs.")
    register.add_argument("--implementation-commit", required=True)
    register.add_argument("--external-repo", type=Path, required=True)
    register.add_argument("--train-input", type=Path, required=True)
    register.add_argument("--train-input-manifest", type=Path, required=True)
    register.add_argument("--residual-manifest", type=Path, required=True)
    register.add_argument("--residual-failure-audit", type=Path, required=True)
    register.add_argument("--output", type=Path, required=True)
    run = commands.add_parser("run", description="Run the registered read-only audit.")
    run.add_argument("--input", type=Path, required=True)
    run.add_argument("--output-dir", type=Path, required=True)
    validate = commands.add_parser(
        "validate", description="Strictly recompute a published audit."
    )
    validate.add_argument("--input", type=Path, required=True)
    validate.add_argument("--output-dir", type=Path, required=True)
    return parser


def _registered_train_input(
    registration: Mapping[str, Any], *, repo_root: Path
) -> dict[str, Any]:
    identity = registration["identity"]
    return load_train_input_archive(
        repo_root / identity["train_input"]["path"],
        manifest_path=repo_root / identity["train_input_manifest"]["path"],
        expected_seeds=registration["audit"]["seeds"],
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    repo_root = Path(__file__).resolve().parents[1]
    try:
        if args.command == "register":
            registration = build_registration(
                repo_root=repo_root,
                external_repo_root=args.external_repo,
                implementation_commit=args.implementation_commit,
                train_input_path=args.train_input,
                train_input_manifest_path=args.train_input_manifest,
                residual_manifest_path=args.residual_manifest,
                residual_failure_audit_path=args.residual_failure_audit,
            )
            validate_registered_identity(registration, repo_root=repo_root)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_bytes(canonical_json_bytes(registration))
            print(sha256_file(args.output))
            return 0
        registration = load_registration(args.input)
        validate_registered_identity(registration, repo_root=repo_root)
        train_input = _registered_train_input(registration, repo_root=repo_root)
        source_facts = load_source_facts(registration, repo_root=repo_root)
        if args.command == "run":
            manifest = run_registered_audit(
                registration=registration,
                train_input=train_input,
                source_facts=source_facts,
                output_dir=args.output_dir,
            )
        else:
            manifest = recompute_artifact_directory(
                output_dir=args.output_dir,
                registration=registration,
                train_input=train_input,
                source_facts=source_facts,
            )
        print(json.dumps(manifest, indent=2, sort_keys=True))
        return 0
    except AuditBlocked as exc:
        print(f"blocked: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
