"""Build a source-bound Current event-option observation contract."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any


INPUT_SCHEMA_VERSION = "noncombat-event-option-observation-contract-input-v1"
CONTRACT_SCHEMA_VERSION = "noncombat-event-option-observation-contract-v1"
METRICS_SCHEMA_VERSION = "noncombat-event-option-observation-contract-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-event-option-observation-contract-manifest-v1"
IMPLEMENTATION_SOURCE_FILES = (
    "analysis_scripts/noncombat_event_option_observation_contract.py",
)
CANONICAL_ARTIFACT_NAMES = (
    "configuration.json",
    "contract.json",
    "metrics.json",
    "report.md",
    "artifact_manifest.json",
)
R2_INVENTORY_SCHEMA_VERSION = "noncombat-event-semantics-coverage-inventory-v1"
R2_MANIFEST_SCHEMA_VERSION = "noncombat-event-semantics-coverage-manifest-v1"
R2_INPUT_SCHEMA_VERSION = "noncombat-event-semantics-coverage-audit-input-v1"
EXPECTED_EVENT_COUNT = 25
EXPECTED_ALIAS_COUNT = 47
EXPECTED_RULE_KIND_COUNTS = {
    "cursed_tome_phase": 1,
    "nloth_relic": 1,
    "static": 23,
}
UPSTREAM_SOURCE_KEYS = (
    "display_labels",
    "event_identities",
    "event_save_ids",
    "execution",
    "legal_actions",
)
ALL_FALSE_AUTHORITY = {
    "adapter_implementation_authorized": False,
    "baseline_floor_authorized": False,
    "compatibility_evaluation_authorized": False,
    "formal_rl_readiness_authorized": False,
    "gameplay_authorized": False,
    "model_fitting_authorized": False,
    "promotion_authorized": False,
    "resolver_implementation_authorized": False,
    "reward_authorized": False,
    "seed_use_authorized": False,
    "simulator_execution_authorized": False,
    "training_authorized": False,
}
R2_ALL_FALSE_AUTHORITY = {
    "formal_rl_readiness_authorized": False,
    "gameplay_authorized": False,
    "model_fitting_authorized": False,
    "promotion_authorized": False,
    "resolver_extension_authorized": False,
    "reward_authorized": False,
    "seed_use_authorized": False,
    "simulator_execution_authorized": False,
    "training_authorized": False,
}
NLOTH_REQUIRED_CONTEXT = {
    "offered_relics_path": "state.decision_context.offered_relics",
    "record_fields": [
        "relic_id",
        "relic_name",
        "relic_slot",
        "simulator_choice_index",
    ],
    "snapshot_relics_path": "state.relics",
    "source_fields": [
        "GameContext.info.relicIdx0",
        "GameContext.info.relicIdx1",
    ],
}


class ContractBlocked(ValueError):
    """Raised when the observation contract cannot remain exact."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, indent=2, sort_keys=True) + "\n").encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path | str) -> str:
    return sha256_bytes(Path(path).read_bytes())


def _static_rule(
    canonical_id: str,
    aliases: Sequence[str],
    upstream_enum: str,
    upstream_event_id: str,
    event_game_name: str,
    options: Sequence[tuple[int, str]],
    *,
    current_event_id: str | None = None,
) -> dict[str, Any]:
    return {
        "aliases": list(aliases),
        "canonical_id": canonical_id,
        "current_event_id": current_event_id or canonical_id,
        "event_game_name": event_game_name,
        "kind": "static",
        "options": [
            {"label": label, "simulator_choice_index": index}
            for index, label in options
        ],
        "upstream_enum": upstream_enum,
        "upstream_event_id": upstream_event_id,
    }


EVENT_RULES: list[dict[str, Any]] = [
    _static_rule(
        "Back to Basics",
        ["Back to Basics", "BackToBasics"],
        "ANCIENT_WRITING",
        "Back to Basics",
        "Ancient Writing",
        [(0, "Elegance"), (1, "Simplicity")],
    ),
    _static_rule(
        "Big Fish",
        ["Big Fish", "BigFish"],
        "BIG_FISH",
        "Big Fish",
        "Big Fish",
        [(0, "Banana"), (1, "Donut"), (2, "Box")],
    ),
    {
        "aliases": ["Cursed Tome", "CursedTome"],
        "canonical_id": "Cursed Tome",
        "current_event_id": "Cursed Tome",
        "event_game_name": "Cursed Tome",
        "kind": "cursed_tome_phase",
        "options": [
            {"label": "Read", "simulator_choice_index": 0},
            {"label": "Leave", "simulator_choice_index": 1},
            {"label": "Continue", "simulator_choice_index": 2},
            {"label": "Continue", "simulator_choice_index": 3},
            {"label": "Continue", "simulator_choice_index": 4},
            {"label": "Take", "simulator_choice_index": 5},
            {"label": "Stop", "simulator_choice_index": 6},
        ],
        "phases": [
            {"event_data": 0, "simulator_choice_indices": [0, 1]},
            {"event_data": 1, "simulator_choice_indices": [2]},
            {"event_data": 2, "simulator_choice_indices": [3]},
            {"event_data": 3, "simulator_choice_indices": [4]},
            {"event_data": 4, "simulator_choice_indices": [5, 6]},
        ],
        "upstream_enum": "CURSED_TOME",
        "upstream_event_id": "Cursed Tome",
    },
    _static_rule(
        "Dead Adventurer",
        ["Dead Adventurer", "DeadAdventurer"],
        "DEAD_ADVENTURER",
        "Dead Adventurer",
        "Dead Adventurer",
        [(0, "Search"), (1, "Escape")],
    ),
    _static_rule(
        "Drug Dealer",
        ["Drug Dealer"],
        "AUGMENTER",
        "Drug Dealer",
        "Augmenter",
        [
            (0, "Test J.A.X"),
            (1, "Become Test Subject"),
            (2, "Ingest Mutagens"),
        ],
    ),
    _static_rule(
        "Face Trader",
        ["Face Trader", "FaceTrader"],
        "FACE_TRADER",
        "Face Trader",
        "Face Trader",
        [(0, "Touch"), (1, "Trade"), (2, "Leave")],
    ),
    _static_rule(
        "Forgotten Altar",
        ["Forgotten Altar", "ForgottenAltar"],
        "FORGOTTEN_ALTAR",
        "Forgotten Altar",
        "Forgotten Altar",
        [(0, "Offer: Golden Idol"), (1, "Sacrifice"), (2, "Desecrate")],
    ),
    _static_rule(
        "Ghosts",
        ["Council of Ghosts", "CouncilOfGhosts", "Ghosts"],
        "GHOSTS",
        "Ghosts",
        "Council of Ghosts",
        [(0, "Accept"), (1, "Refuse")],
    ),
    _static_rule(
        "Golden Idol",
        ["Golden Idol", "GoldenIdol"],
        "GOLDEN_IDOL",
        "Golden Idol",
        "Golden Idol",
        [
            (0, "Take"),
            (1, "Leave"),
            (2, "Outrun"),
            (3, "Smash"),
            (4, "Hide"),
        ],
    ),
    _static_rule(
        "Golden Shrine",
        ["Golden Shrine", "GoldenShrine"],
        "GOLDEN_SHRINE",
        "Golden Shrine",
        "Golden Shrine",
        [(0, "Pray"), (1, "Desecrate"), (2, "Leave")],
    ),
    _static_rule(
        "Knowing Skull",
        ["Knowing Skull"],
        "KNOWING_SKULL",
        "Knowing Skull",
        "Knowing Skull",
        [
            (0, "Riches?"),
            (1, "Success?"),
            (2, "A Pick Me Up?"),
            (3, "How do I leave?"),
        ],
    ),
    _static_rule(
        "Liars Game",
        ["Liars Game"],
        "THE_SSSSSERPENT",
        "Liars Game",
        "The Ssssserpent",
        [(0, "Agree"), (1, "Disagree")],
    ),
    _static_rule(
        "Living Wall",
        ["Living Wall", "LivingWall"],
        "LIVING_WALL",
        "Living Wall",
        "Living Wall",
        [(0, "Forget"), (1, "Change"), (2, "Grow")],
    ),
    _static_rule(
        "Masked Bandits",
        ["Masked Bandits", "MaskedBandits"],
        "MASKED_BANDITS",
        "Masked Bandits",
        "Masked Bandits",
        [(0, "Pay"), (1, "Fight!")],
    ),
    _static_rule(
        "MindBloom",
        ["Mind Bloom", "MindBloom"],
        "MINDBLOOM",
        "Mindbloom",
        "Mindbloom",
        [
            (0, "I am War"),
            (1, "I am Awake"),
            (2, "I am Rich"),
            (3, "I am Healthy"),
        ],
        current_event_id="MindBloom",
    ),
    _static_rule(
        "Mushrooms",
        ["Mushrooms", "The Mushroom Lair"],
        "HYPNOTIZING_COLORED_MUSHROOMS",
        "Mushrooms",
        "Hypnotizing Colored Mushrooms",
        [(0, "Stomp"), (1, "Eat")],
    ),
    _static_rule(
        "Mysterious Sphere",
        ["Mysterious Sphere", "MysteriousSphere"],
        "MYSTERIOUS_SPHERE",
        "Mysterious Sphere",
        "Mysterious Sphere",
        [(0, "Open Sphere"), (1, "Leave")],
    ),
    {
        "aliases": ["N'loth", "Nloth", "N’loth"],
        "canonical_id": "N'loth",
        "current_event_id": "N'loth",
        "event_game_name": "N'loth",
        "kind": "nloth_relic",
        "options": [
            {
                "label_template": "Offer {relic_name}",
                "simulator_choice_index": 0,
            },
            {
                "label_template": "Offer {relic_name}",
                "simulator_choice_index": 1,
            },
            {"label": "Leave", "simulator_choice_index": 2},
        ],
        "required_context": copy.deepcopy(NLOTH_REQUIRED_CONTEXT),
        "upstream_enum": "NLOTH",
        "upstream_event_id": "Nloth",
    },
    _static_rule(
        "Note For Yourself",
        ["Note For Yourself", "NoteForYourself"],
        "NOTE_FOR_YOURSELF",
        "Note For Yourself",
        "Note For Yourself",
        [(0, "Take and Give"), (1, "Ignore")],
    ),
    _static_rule(
        "Shining Light",
        ["Shining Light", "ShiningLight"],
        "SHINING_LIGHT",
        "Shining Light",
        "Shining Light",
        [(0, "Enter"), (1, "Leave")],
    ),
    _static_rule(
        "The Cleric",
        ["Cleric", "The Cleric"],
        "THE_CLERIC",
        "The Cleric",
        "The Cleric",
        [(0, "Heal"), (1, "Purify"), (2, "Leave")],
    ),
    _static_rule(
        "The Library",
        ["The Library"],
        "THE_LIBRARY",
        "The Library",
        "The Library",
        [(0, "Read"), (1, "Sleep")],
    ),
    _static_rule(
        "The Mausoleum",
        ["Mausoleum", "The Mausoleum"],
        "THE_MAUSOLEUM",
        "The Mausoleum",
        "The Mausoleum",
        [(0, "Open Coffin"), (1, "Leave")],
    ),
    _static_rule(
        "Vampires",
        ["Vampires"],
        "VAMPIRES",
        "Vampires",
        "Vampires(?)",
        [(0, "Offer"), (1, "Accept"), (2, "Refuse")],
    ),
    _static_rule(
        "World of Goop",
        ["World of Goop", "WorldOfGoop"],
        "WORLD_OF_GOOP",
        "World of Goop",
        "World of Goop",
        [(0, "Gather Gold"), (1, "Leave It")],
    ),
]


def registry_sha256(rules: Sequence[Mapping[str, Any]] = EVENT_RULES) -> str:
    return sha256_bytes(canonical_json_bytes(rules))


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ContractBlocked("mapping_required", label)
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ContractBlocked("sequence_required", label)
    return list(value)


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    actual = set(value)
    if actual != expected:
        raise ContractBlocked(
            "object_keys_mismatch",
            {"actual": sorted(actual), "expected": sorted(expected), "label": label},
        )


def _is_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value)
    )


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ContractBlocked("duplicate_json_key", key)
        result[key] = value
    return result


def _validated_relative_path(value: object, label: str) -> str:
    if not isinstance(value, str) or not value:
        raise ContractBlocked("relative_path_required", label)
    normalized = value.replace("\\", "/")
    pure = PurePosixPath(normalized)
    if pure.is_absolute() or ".." in pure.parts or normalized != pure.as_posix():
        raise ContractBlocked("invalid_relative_path", {"label": label, "path": value})
    return normalized


def _validated_binding(value: object, label: str) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    binding["path"] = _validated_relative_path(binding["path"], f"{label}.path")
    if not _is_hex(binding["sha256"], 64):
        raise ContractBlocked("invalid_binding_sha256", label)
    if (
        isinstance(binding["size_bytes"], bool)
        or not isinstance(binding["size_bytes"], int)
        or binding["size_bytes"] <= 0
    ):
        raise ContractBlocked("invalid_binding_size", label)
    return binding


def validate_registration(value: object) -> dict[str, Any]:
    registration = _mapping(copy.deepcopy(value), "registration")
    _require_keys(
        registration,
        {
            "audit",
            "authority",
            "expected",
            "implementation",
            "output",
            "schema_version",
            "source_identity",
        },
        "registration",
    )
    if registration["schema_version"] != INPUT_SCHEMA_VERSION:
        raise ContractBlocked("registration_schema_mismatch")
    if registration["authority"] != ALL_FALSE_AUTHORITY:
        raise ContractBlocked("contract_authority_mismatch")
    registration["authority"] = dict(ALL_FALSE_AUTHORITY)

    audit = _mapping(registration["audit"], "audit")
    _require_keys(audit, {"directory", "inventory", "manifest", "registration"}, "audit")
    audit["directory"] = _validated_relative_path(audit["directory"], "audit.directory")
    for field in ("inventory", "manifest", "registration"):
        audit[field] = _validated_binding(audit[field], f"audit.{field}")
    expected_audit_paths = {
        "inventory": (PurePosixPath(audit["directory"]) / "event_inventory.json").as_posix(),
        "manifest": (PurePosixPath(audit["directory"]) / "artifact_manifest.json").as_posix(),
    }
    for field, path in expected_audit_paths.items():
        if audit[field]["path"] != path:
            raise ContractBlocked("audit_artifact_path_mismatch", field)
    registration["audit"] = audit

    implementation = _mapping(registration["implementation"], "implementation")
    _require_keys(
        implementation, {"commit", "source_files", "source_sha256"}, "implementation"
    )
    if not _is_hex(implementation["commit"], 40):
        raise ContractBlocked("implementation_commit_invalid")
    source_files = [
        _validated_relative_path(path, "implementation.source_files")
        for path in _sequence(implementation["source_files"], "implementation.source_files")
    ]
    if source_files != list(IMPLEMENTATION_SOURCE_FILES):
        raise ContractBlocked("implementation_source_files_mismatch")
    implementation["source_files"] = source_files
    if not _is_hex(implementation["source_sha256"], 64):
        raise ContractBlocked("implementation_source_sha256_invalid")
    registration["implementation"] = implementation

    source_identity = _mapping(registration["source_identity"], "source_identity")
    _require_keys(
        source_identity,
        {
            "current_repository_commit",
            "current_source",
            "simulator_parent_commit",
            "simulator_source_sha256",
            "upstream_source_files",
        },
        "source_identity",
    )
    for field in ("current_repository_commit", "simulator_parent_commit"):
        if not _is_hex(source_identity[field], 40):
            raise ContractBlocked("source_commit_invalid", field)
    if not _is_hex(source_identity["simulator_source_sha256"], 64):
        raise ContractBlocked("simulator_source_sha256_invalid")
    source_identity["current_source"] = _validated_binding(
        source_identity["current_source"], "source_identity.current_source"
    )
    upstream = _mapping(
        source_identity["upstream_source_files"], "source_identity.upstream_source_files"
    )
    _require_keys(upstream, set(UPSTREAM_SOURCE_KEYS), "source_identity.upstream_source_files")
    source_identity["upstream_source_files"] = {
        key: _validated_binding(upstream[key], f"source_identity.upstream_source_files.{key}")
        for key in UPSTREAM_SOURCE_KEYS
    }
    registration["source_identity"] = source_identity

    expected = _mapping(registration["expected"], "expected")
    _require_keys(
        expected,
        {
            "alias_count",
            "event_count",
            "registry_sha256",
            "rule_kind_counts",
            "unaccounted_surface_count",
        },
        "expected",
    )
    if expected["event_count"] != EXPECTED_EVENT_COUNT:
        raise ContractBlocked("expected_event_count_mismatch")
    if expected["alias_count"] != EXPECTED_ALIAS_COUNT:
        raise ContractBlocked("expected_alias_count_mismatch")
    if expected["unaccounted_surface_count"] != 0:
        raise ContractBlocked("expected_unaccounted_surface_count_mismatch")
    if expected["registry_sha256"] != registry_sha256():
        raise ContractBlocked("expected_registry_sha256_mismatch")
    if expected["rule_kind_counts"] != EXPECTED_RULE_KIND_COUNTS:
        raise ContractBlocked("expected_rule_kind_counts_mismatch")
    expected["rule_kind_counts"] = dict(EXPECTED_RULE_KIND_COUNTS)
    registration["expected"] = expected

    output = _mapping(registration["output"], "output")
    _require_keys(output, {"artifact_names", "directory"}, "output")
    output["directory"] = _validated_relative_path(output["directory"], "output.directory")
    if output["artifact_names"] != list(CANONICAL_ARTIFACT_NAMES):
        raise ContractBlocked("output_artifact_names_mismatch")
    if output["directory"] == audit["directory"]:
        raise ContractBlocked("output_directory_reuses_audit")
    registration["output"] = output
    return registration


def load_registration(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except ContractBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractBlocked("registration_load_failed", str(exc)) from exc
    return validate_registration(value)


def verify_bound_file(root: Path | str, binding: Mapping[str, Any]) -> Path:
    base = Path(root).resolve()
    path = (base / str(binding["path"])).resolve()
    try:
        path.relative_to(base)
    except ValueError as exc:
        raise ContractBlocked("bound_file_escapes_root", binding["path"]) from exc
    if not path.is_file():
        raise ContractBlocked("bound_file_missing", binding["path"])
    actual = {
        "path": str(binding["path"]),
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }
    if actual != dict(binding):
        raise ContractBlocked(
            "bound_file_identity_mismatch",
            {"actual": actual, "registered": dict(binding)},
        )
    return path


def load_canonical_json(path: Path | str, label: str) -> dict[str, Any]:
    try:
        raw = Path(path).read_bytes()
        value = json.loads(raw, object_pairs_hook=_reject_duplicate_pairs)
    except ContractBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractBlocked("contract_artifact_load_failed", label) from exc
    if canonical_json_bytes(value) != raw:
        raise ContractBlocked("contract_artifact_not_canonical", label)
    return _mapping(value, label)


def _validated_options(rule: Mapping[str, Any], label: str) -> list[dict[str, Any]]:
    kind = rule["kind"]
    options = []
    for position, raw in enumerate(_sequence(rule["options"], f"{label}.options")):
        option = _mapping(raw, f"{label}.options[{position}]")
        expected_keys = (
            {"label_template", "simulator_choice_index"}
            if kind == "nloth_relic" and position < 2
            else {"label", "simulator_choice_index"}
        )
        _require_keys(option, expected_keys, f"{label}.options[{position}]")
        choice_index = option["simulator_choice_index"]
        if isinstance(choice_index, bool) or not isinstance(choice_index, int) or choice_index < 0:
            raise ContractBlocked("contract_registry_option_index_invalid", label)
        field = "label_template" if "label_template" in option else "label"
        if not isinstance(option[field], str) or not option[field]:
            raise ContractBlocked("contract_registry_option_label_invalid", label)
        options.append(option)
    indices = [option["simulator_choice_index"] for option in options]
    if indices != sorted(set(indices)):
        raise ContractBlocked("contract_registry_option_order_or_duplicate", label)
    return options


def _inventory_rows(value: object) -> list[dict[str, Any]]:
    inventory = _mapping(value, "inventory")
    _require_keys(inventory, {"rows", "schema_version"}, "inventory")
    if inventory["schema_version"] != R2_INVENTORY_SCHEMA_VERSION:
        raise ContractBlocked("contract_inventory_schema_mismatch")
    rows = [
        _mapping(row, f"inventory.rows[{index}]")
        for index, row in enumerate(_sequence(inventory["rows"], "inventory.rows"))
    ]
    canonical_ids = [row.get("canonical_id") for row in rows]
    if canonical_ids != sorted(set(canonical_ids)):
        raise ContractBlocked("contract_inventory_event_order_or_duplicate")
    return rows


def _inventory_display_entries(row: Mapping[str, Any], label: str) -> list[dict[str, Any]]:
    display = _mapping(row.get("display_labels"), f"{label}.display_labels")
    entries = []
    for index, raw in enumerate(_sequence(display.get("display_entries"), label)):
        entry = _mapping(raw, f"{label}.display_entries[{index}]")
        _require_keys(entry, {"index", "label"}, f"{label}.display_entries[{index}]")
        entries.append(
            {
                "label": entry["label"],
                "simulator_choice_index": entry["index"],
            }
        )
    return entries


def validate_contract_registry(
    rules: Sequence[Mapping[str, Any]], inventory: Mapping[str, Any]
) -> dict[str, Any]:
    rows = _inventory_rows(inventory)
    normalized_rules = [
        _mapping(copy.deepcopy(rule), f"rules[{index}]")
        for index, rule in enumerate(_sequence(rules, "rules"))
    ]
    inventory_ids = [row["canonical_id"] for row in rows]
    rule_ids = [rule.get("canonical_id") for rule in normalized_rules]
    if rule_ids != inventory_ids:
        raise ContractBlocked(
            "contract_registry_event_identity_mismatch",
            {"inventory": inventory_ids, "registry": rule_ids},
        )
    if len(rule_ids) != EXPECTED_EVENT_COUNT:
        raise ContractBlocked("contract_registry_event_count_mismatch")

    aliases: set[str] = set()
    kind_counts: Counter[str] = Counter()
    normalized_events = []
    for row, rule in zip(rows, normalized_rules):
        canonical_id = row["canonical_id"]
        kind = rule.get("kind")
        expected_keys = {
            "aliases",
            "canonical_id",
            "current_event_id",
            "event_game_name",
            "kind",
            "options",
            "upstream_enum",
            "upstream_event_id",
        }
        if kind == "cursed_tome_phase":
            expected_keys.add("phases")
        elif kind == "nloth_relic":
            expected_keys.add("required_context")
        elif kind != "static":
            raise ContractBlocked("contract_registry_rule_kind_invalid", canonical_id)
        _require_keys(rule, expected_keys, f"rules.{canonical_id}")
        kind_counts[kind] += 1

        if rule["aliases"] != row.get("aliases"):
            raise ContractBlocked("contract_registry_alias_mismatch", canonical_id)
        for alias in rule["aliases"]:
            if alias in aliases:
                raise ContractBlocked("contract_registry_alias_duplicate", alias)
            aliases.add(alias)
        identity = _mapping(row.get("event_identity"), f"inventory.{canonical_id}.identity")
        expected_identity = {
            "event_game_name": identity.get("event_game_name"),
            "upstream_enum": row.get("upstream_enum"),
            "upstream_event_id": identity.get("event_id"),
        }
        actual_identity = {
            "event_game_name": rule["event_game_name"],
            "upstream_enum": rule["upstream_enum"],
            "upstream_event_id": rule["upstream_event_id"],
        }
        if actual_identity != expected_identity:
            raise ContractBlocked("contract_registry_upstream_identity_mismatch", canonical_id)
        if rule["current_event_id"] not in rule["aliases"]:
            raise ContractBlocked("contract_registry_current_event_id_invalid", canonical_id)

        options = _validated_options(rule, f"rules.{canonical_id}")
        if kind == "static":
            if options != _inventory_display_entries(row, canonical_id):
                raise ContractBlocked("contract_registry_static_label_mismatch", canonical_id)
        elif kind == "cursed_tome_phase":
            expected_phases = [
                {"event_data": 0, "simulator_choice_indices": [0, 1]},
                {"event_data": 1, "simulator_choice_indices": [2]},
                {"event_data": 2, "simulator_choice_indices": [3]},
                {"event_data": 3, "simulator_choice_indices": [4]},
                {"event_data": 4, "simulator_choice_indices": [5, 6]},
            ]
            if rule["phases"] != expected_phases:
                raise ContractBlocked("contract_registry_cursed_tome_phase_mismatch")
            visible = [
                option for option in options if option["simulator_choice_index"] in {0, 1, 5, 6}
            ]
            if visible != _inventory_display_entries(row, canonical_id):
                raise ContractBlocked("contract_registry_cursed_tome_label_mismatch")
            legal = _mapping(row.get("legal_actions"), f"inventory.{canonical_id}.legal")
            if legal.get("dynamic_return_expressions") != [
                "0x1 << (gc.info.eventData+1)",
                "0x3 << (gc.info.eventData+1)",
            ]:
                raise ContractBlocked("contract_registry_cursed_tome_source_mismatch")
        else:
            if rule["required_context"] != NLOTH_REQUIRED_CONTEXT:
                raise ContractBlocked("contract_registry_nloth_context_mismatch")
            inventory_entries = _inventory_display_entries(row, canonical_id)
            if inventory_entries != [
                {"label": "[Offer", "simulator_choice_index": 0},
                {"label": "[Offer", "simulator_choice_index": 1},
                {"label": "Leave", "simulator_choice_index": 2},
            ]:
                raise ContractBlocked("contract_registry_nloth_source_mismatch")

        normalized_events.append(rule)

    if len(aliases) != EXPECTED_ALIAS_COUNT:
        raise ContractBlocked("contract_registry_alias_count_mismatch", len(aliases))
    if dict(sorted(kind_counts.items())) != EXPECTED_RULE_KIND_COUNTS:
        raise ContractBlocked("contract_registry_rule_kind_counts_mismatch")
    return {
        "adapter_ready": False,
        "alias_count": len(aliases),
        "authority": dict(ALL_FALSE_AUTHORITY),
        "event_count": len(normalized_events),
        "events": normalized_events,
        "registry_sha256": registry_sha256(normalized_rules),
        "required_snapshot_extensions": [
            {
                "canonical_id": "N'loth",
                "required_context": copy.deepcopy(NLOTH_REQUIRED_CONTEXT),
            }
        ],
        "resolver_ready": False,
        "rule_kind_counts": dict(sorted(kind_counts.items())),
        "schema_version": CONTRACT_SCHEMA_VERSION,
        "unaccounted_surface_count": 0,
    }


def _candidate_indices(
    rule: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> list[int]:
    values = _sequence(candidates, "candidates")
    indices = []
    for position, raw in enumerate(values):
        candidate = _mapping(raw, f"candidates[{position}]")
        _require_keys(
            candidate,
            {"event_id", "simulator_choice_index"},
            f"candidates[{position}]",
        )
        if candidate["event_id"] != rule["upstream_event_id"]:
            raise ContractBlocked(
                "contract_candidate_event_mismatch",
                {"actual": candidate["event_id"], "expected": rule["upstream_event_id"]},
            )
        choice_index = candidate["simulator_choice_index"]
        if isinstance(choice_index, bool) or not isinstance(choice_index, int) or choice_index < 0:
            raise ContractBlocked("contract_candidate_index_invalid", position)
        indices.append(choice_index)
    if len(indices) != len(set(indices)):
        raise ContractBlocked("contract_candidate_index_duplicate")
    if indices != sorted(indices):
        raise ContractBlocked("contract_candidate_order_invalid")
    return indices


def _nloth_labels(
    *,
    snapshot_relics: Sequence[Mapping[str, Any]] | None,
    offered_relics: Sequence[Mapping[str, Any]] | None,
) -> dict[int, str]:
    if snapshot_relics is None or offered_relics is None:
        raise ContractBlocked("contract_nloth_context_missing")
    relics = _sequence(snapshot_relics, "snapshot_relics")
    offered = _sequence(offered_relics, "offered_relics")
    if len(offered) != 2:
        raise ContractBlocked("contract_nloth_offered_relic_count_mismatch")
    normalized_offered = []
    for index, raw in enumerate(offered):
        record = _mapping(raw, f"offered_relics[{index}]")
        _require_keys(record, set(NLOTH_REQUIRED_CONTEXT["record_fields"]), f"offered[{index}]")
        if record["simulator_choice_index"] != index:
            raise ContractBlocked("contract_nloth_choice_index_mismatch", index)
        slot = record["relic_slot"]
        if isinstance(slot, bool) or not isinstance(slot, int) or not 0 <= slot < len(relics):
            raise ContractBlocked("contract_nloth_relic_slot_invalid", slot)
        relic = _mapping(relics[slot], f"snapshot_relics[{slot}]")
        if (
            record["relic_id"] != relic.get("id")
            or record["relic_name"] != relic.get("name")
            or not isinstance(record["relic_id"], str)
            or not record["relic_id"]
            or not isinstance(record["relic_name"], str)
            or not record["relic_name"]
        ):
            raise ContractBlocked("contract_nloth_relic_mismatch", index)
        normalized_offered.append(record)
    if normalized_offered[0]["relic_slot"] == normalized_offered[1]["relic_slot"]:
        raise ContractBlocked("contract_nloth_relic_slot_duplicate")
    return {
        0: f"Offer {normalized_offered[0]['relic_name']}",
        1: f"Offer {normalized_offered[1]['relic_name']}",
        2: "Leave",
    }


def build_event_observation(
    rule: Mapping[str, Any],
    *,
    candidates: Sequence[Mapping[str, Any]],
    event_data: object,
    snapshot_relics: Sequence[Mapping[str, Any]] | None = None,
    offered_relics: Sequence[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    normalized_rule = _mapping(copy.deepcopy(rule), "rule")
    kind = normalized_rule.get("kind")
    if kind == "cursed_tome_phase":
        if isinstance(event_data, bool) or not isinstance(event_data, int):
            raise ContractBlocked("contract_event_phase_invalid", event_data)
        phase = next(
            (
                phase
                for phase in normalized_rule["phases"]
                if phase["event_data"] == event_data
            ),
            None,
        )
        if phase is None:
            raise ContractBlocked("contract_event_phase_unsupported", event_data)
    else:
        phase = None

    indices = _candidate_indices(normalized_rule, candidates)
    if not indices:
        raise ContractBlocked("contract_candidate_set_empty")
    if phase is not None and indices != phase["simulator_choice_indices"]:
        raise ContractBlocked(
            "contract_event_phase_candidates_mismatch",
            {"actual": indices, "expected": phase["simulator_choice_indices"]},
        )

    if kind == "nloth_relic":
        if indices != [0, 1, 2]:
            raise ContractBlocked("contract_nloth_candidate_indices_mismatch", indices)
        labels = _nloth_labels(
            snapshot_relics=snapshot_relics, offered_relics=offered_relics
        )
    else:
        labels = {
            option["simulator_choice_index"]: option["label"]
            for option in normalized_rule["options"]
        }
    unknown = [index for index in indices if index not in labels]
    if unknown:
        raise ContractBlocked("contract_candidate_index_unsupported", unknown)

    return {
        "canonical_id": normalized_rule["canonical_id"],
        "current_event_id": normalized_rule["current_event_id"],
        "event_data": event_data,
        "options": [
            {
                "current_position": current_position,
                "label": labels[choice_index],
                "simulator_choice_index": choice_index,
            }
            for current_position, choice_index in enumerate(indices)
        ],
        "rule_kind": kind,
        "upstream_event_id": normalized_rule["upstream_event_id"],
    }


def _report_markdown(contract: Mapping[str, Any]) -> str:
    lines = [
        "# Non-Combat Event Option Observation Contract",
        "",
        "This is a static Current-observation contract. It does not authorize a resolver, adapter change, simulator execution, gameplay, evaluation, model, or training.",
        "",
        "| Canonical event | Upstream event id | Current event id | Rule | Options |",
        "| --- | --- | --- | --- | --- |",
    ]
    for rule in contract["events"]:
        if rule["kind"] == "nloth_relic":
            summary = "0:Offer <relic>; 1:Offer <relic>; 2:Leave"
        else:
            summary = "; ".join(
                f"{option['simulator_choice_index']}:{option['label']}"
                for option in rule["options"]
            )
        lines.append(
            f"| `{rule['canonical_id']}` | `{rule['upstream_event_id']}` | "
            f"`{rule['current_event_id']}` | `{rule['kind']}` | {summary} |"
        )
    lines.extend(
        [
            "",
            "## Required Snapshot Extension",
            "",
            "`N'loth` requires `state.decision_context.offered_relics` records for simulator choices 0 and 1, bound by relic slot, id, and name to `state.relics`.",
            "",
            "Resolver and adapter readiness remain false.",
            "",
        ]
    )
    return "\n".join(lines)


def build_artifacts(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    contract: Mapping[str, Any],
) -> dict[str, bytes]:
    normalized_registration = validate_registration(registration)
    if contract.get("authority") != ALL_FALSE_AUTHORITY:
        raise ContractBlocked("contract_payload_authority_mismatch")
    metrics = {
        "adapter_ready": False,
        "alias_count": contract["alias_count"],
        "authority": dict(ALL_FALSE_AUTHORITY),
        "event_count": contract["event_count"],
        "registration_sha256": registration_sha256,
        "resolver_ready": False,
        "rule_kind_counts": contract["rule_kind_counts"],
        "schema_version": METRICS_SCHEMA_VERSION,
        "unaccounted_surface_count": contract["unaccounted_surface_count"],
    }
    payloads = {
        "configuration.json": canonical_json_bytes(
            {
                "registration": normalized_registration,
                "registration_sha256": registration_sha256,
                "schema_version": INPUT_SCHEMA_VERSION,
            }
        ),
        "contract.json": canonical_json_bytes(contract),
        "metrics.json": canonical_json_bytes(metrics),
        "report.md": _report_markdown(contract).encode("utf-8"),
    }
    manifest = {
        "adapter_ready": False,
        "artifact_hashes": {
            name: sha256_bytes(data) for name, data in sorted(payloads.items())
        },
        "authority": dict(ALL_FALSE_AUTHORITY),
        "event_count": contract["event_count"],
        "registration_sha256": registration_sha256,
        "resolver_ready": False,
        "schema_version": MANIFEST_SCHEMA_VERSION,
    }
    payloads["artifact_manifest.json"] = canonical_json_bytes(manifest)
    return {name: payloads[name] for name in CANONICAL_ARTIFACT_NAMES}


def write_or_verify_artifacts(
    output_dir: Path | str,
    artifacts: Mapping[str, bytes],
    *,
    recompute: bool,
) -> None:
    directory = Path(output_dir)
    expected_names = set(CANONICAL_ARTIFACT_NAMES)
    if set(artifacts) != expected_names:
        raise ContractBlocked("artifact_name_set_invalid")
    actual_names = {path.name for path in directory.iterdir()} if directory.is_dir() else set()
    if recompute:
        if actual_names != expected_names:
            raise ContractBlocked(
                "artifact_recompute_mismatch",
                {"actual": sorted(actual_names), "expected": sorted(expected_names)},
            )
        for name, expected in artifacts.items():
            if (directory / name).read_bytes() != expected:
                raise ContractBlocked("artifact_recompute_mismatch", name)
        return
    if directory.exists() and actual_names:
        raise ContractBlocked("output_directory_not_empty", str(directory))
    directory.mkdir(parents=True, exist_ok=True)
    for name, data in artifacts.items():
        temporary = directory / f".{name}.tmp"
        if temporary.exists():
            raise ContractBlocked("artifact_temporary_output_exists", str(temporary))
        temporary.write_bytes(data)
        temporary.replace(directory / name)


def hash_bound_files(repo_root: Path | str, source_files: Sequence[str]) -> str:
    root = Path(repo_root).resolve()
    digest = hashlib.sha256()
    for relative in source_files:
        path = (root / relative).resolve()
        try:
            canonical_relative = path.relative_to(root).as_posix()
        except ValueError as exc:
            raise ContractBlocked("implementation_source_escapes_repository", relative) from exc
        if not path.is_file():
            raise ContractBlocked("implementation_source_missing", relative)
        relative_bytes = canonical_relative.encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative_bytes).to_bytes(4, "big"))
        digest.update(relative_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _verify_implementation_at_commit(
    root: Path, implementation: Mapping[str, Any]
) -> None:
    if hash_bound_files(root, implementation["source_files"]) != implementation[
        "source_sha256"
    ]:
        raise ContractBlocked("implementation_source_sha256_mismatch")
    for relative in implementation["source_files"]:
        try:
            result = subprocess.run(
                ["git", "show", f"{implementation['commit']}:{relative}"],
                cwd=root,
                check=False,
                capture_output=True,
                timeout=30,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ContractBlocked("implementation_commit_read_failed", relative) from exc
        if result.returncode != 0:
            raise ContractBlocked(
                "implementation_commit_read_failed",
                result.stderr.decode("utf-8", errors="replace"),
            )
        if result.stdout != (root / relative).read_bytes():
            raise ContractBlocked("implementation_commit_source_mismatch", relative)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        return _mapping(
            json.loads(
                path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            ),
            label,
        )
    except ContractBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ContractBlocked("bound_json_load_failed", label) from exc


def _verify_r2_inputs(
    root: Path, registration: Mapping[str, Any]
) -> dict[str, Any]:
    audit = registration["audit"]
    r2_registration_path = verify_bound_file(root, audit["registration"])
    inventory_path = verify_bound_file(root, audit["inventory"])
    manifest_path = verify_bound_file(root, audit["manifest"])
    r2_registration = _load_json(r2_registration_path, "r2_registration")
    inventory = load_canonical_json(inventory_path, "r2_inventory")
    manifest = load_canonical_json(manifest_path, "r2_manifest")
    _require_keys(
        r2_registration,
        {
            "authority",
            "current",
            "events",
            "implementation",
            "output",
            "schema_version",
            "simulator",
        },
        "r2_registration",
    )
    if r2_registration["schema_version"] != R2_INPUT_SCHEMA_VERSION:
        raise ContractBlocked("r2_registration_schema_mismatch")
    if r2_registration["authority"] != R2_ALL_FALSE_AUTHORITY:
        raise ContractBlocked("r2_registration_authority_mismatch")
    _require_keys(
        manifest,
        {
            "artifact_hashes",
            "authority",
            "event_count",
            "registration_sha256",
            "resolver_ready",
            "schema_version",
            "status_counts",
        },
        "r2_manifest",
    )
    if manifest.get("schema_version") != R2_MANIFEST_SCHEMA_VERSION:
        raise ContractBlocked("r2_manifest_schema_mismatch")
    if manifest["authority"] != R2_ALL_FALSE_AUTHORITY:
        raise ContractBlocked("r2_manifest_authority_mismatch")
    if manifest["resolver_ready"] is not False:
        raise ContractBlocked("r2_manifest_resolver_readiness_mismatch")
    if manifest["event_count"] != EXPECTED_EVENT_COUNT or manifest[
        "status_counts"
    ] != {"source_complete": 24, "source_partial": 1}:
        raise ContractBlocked("r2_manifest_metric_mismatch")
    artifact_hashes = _mapping(manifest.get("artifact_hashes"), "r2_manifest.artifact_hashes")
    if artifact_hashes.get("event_inventory.json") != audit["inventory"]["sha256"]:
        raise ContractBlocked("r2_manifest_inventory_hash_mismatch")
    if r2_registration.get("output", {}).get("directory") != audit["directory"]:
        raise ContractBlocked("r2_registration_directory_mismatch")

    source_identity = registration["source_identity"]
    current = _mapping(r2_registration.get("current"), "r2_registration.current")
    simulator = _mapping(r2_registration.get("simulator"), "r2_registration.simulator")
    if current.get("repository_commit") != source_identity["current_repository_commit"]:
        raise ContractBlocked("current_repository_commit_mismatch")
    if current.get("source") != source_identity["current_source"]:
        raise ContractBlocked("current_source_binding_mismatch")
    if simulator.get("parent_commit") != source_identity["simulator_parent_commit"]:
        raise ContractBlocked("simulator_parent_commit_mismatch")
    if simulator.get("source_sha256") != source_identity["simulator_source_sha256"]:
        raise ContractBlocked("simulator_source_identity_mismatch")
    upstream = _mapping(simulator.get("source_files"), "r2_registration.simulator.source_files")
    if upstream != source_identity["upstream_source_files"]:
        raise ContractBlocked("upstream_source_bindings_mismatch")

    verify_bound_file(root, source_identity["current_source"])
    simulator_root = Path(str(simulator.get("root"))).resolve()
    if not simulator_root.is_dir():
        raise ContractBlocked("simulator_root_missing", str(simulator_root))
    for key in UPSTREAM_SOURCE_KEYS:
        verify_bound_file(simulator_root, source_identity["upstream_source_files"][key])
    return {"inventory": inventory, "r2_registration": r2_registration}


def run_contract(
    *,
    registration_path: Path | str,
    repo_root: Path | str,
    recompute: bool = False,
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    raw_input = Path(registration_path)
    input_path = (root / raw_input).resolve() if not raw_input.is_absolute() else raw_input.resolve()
    try:
        input_path.relative_to(root)
    except ValueError as exc:
        raise ContractBlocked("registration_escapes_repository") from exc
    registration = load_registration(input_path)
    _verify_implementation_at_commit(root, registration["implementation"])
    sources = _verify_r2_inputs(root, registration)
    contract = validate_contract_registry(EVENT_RULES, sources["inventory"])
    expected = registration["expected"]
    for field in (
        "alias_count",
        "event_count",
        "registry_sha256",
        "rule_kind_counts",
        "unaccounted_surface_count",
    ):
        if contract[field] != expected[field]:
            raise ContractBlocked("contract_expected_metric_mismatch", field)
    artifacts = build_artifacts(
        registration=registration,
        registration_sha256=sha256_file(input_path),
        contract=contract,
    )
    output_dir = (root / registration["output"]["directory"]).resolve()
    try:
        output_dir.relative_to(root)
    except ValueError as exc:
        raise ContractBlocked("output_directory_escapes_repository") from exc
    write_or_verify_artifacts(output_dir, artifacts, recompute=recompute)
    return {
        "adapter_ready": False,
        "alias_count": contract["alias_count"],
        "event_count": contract["event_count"],
        "output_directory": str(output_dir),
        "resolver_ready": False,
        "rule_kind_counts": contract["rule_kind_counts"],
        "unaccounted_surface_count": contract["unaccounted_surface_count"],
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", required=True)
    parser.add_argument(
        "--repo-root", default=str(Path(__file__).resolve().parents[1])
    )
    parser.add_argument("--recompute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = run_contract(
            registration_path=args.registration,
            repo_root=args.repo_root,
            recompute=args.recompute,
        )
    except ContractBlocked as exc:
        print(
            json.dumps(
                {"detail": exc.detail, "reason": exc.reason, "status": "blocked"},
                indent=2,
                sort_keys=True,
            )
        )
        return 2
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
