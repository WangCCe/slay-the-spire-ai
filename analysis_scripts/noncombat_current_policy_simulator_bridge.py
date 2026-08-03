"""Validate an offline bridge from sts_lightspeed snapshots to Current policy."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from contextlib import ExitStack, contextmanager
from pathlib import Path, PurePosixPath
from typing import Any
from unittest.mock import patch

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

import spirecomm.ai.agent as agent_module
from analysis_scripts.noncombat_event_option_semantics import (
    EventOptionSemanticsError,
    event_option_semantics_identity,
    reachable_event_option_semantics_identity,
    resolve_event_option_observation,
    resolve_reachable_event_option_observation,
)
from analysis_scripts.noncombat_simulator_adapter import (
    NativeSimulatorEnvironment,
    SimulatorAdapterError,
    TARGET_CATEGORIES,
    canonical_json_bytes,
    hash_compiled_simulator_sources,
    load_native_module,
    sha256_bytes,
    sha256_file,
    validate_candidates,
    validate_provenance,
    validate_snapshot,
)
from spirecomm.ai.agent import OptimizedAgent
from spirecomm.communication.action import (
    BuyCardAction,
    BuyPotionAction,
    BuyRelicAction,
    CancelAction,
    CardRewardAction,
    ChooseAction,
    ChooseMapBossAction,
    ChooseMapNodeAction,
    LeaveAction,
    ProceedAction,
)
from spirecomm.data.loader import game_data_loader
from spirecomm.spire.card import Card, CardRarity, CardType
from spirecomm.spire.character import PlayerClass
from spirecomm.spire.game import Game, RoomPhase
from spirecomm.spire.map import Map, Node
from spirecomm.spire.potion import Potion
from spirecomm.spire.relic import Relic
from spirecomm.spire.screen import (
    CardRewardScreen,
    EventOption,
    EventScreen,
    MapScreen,
    ScreenType,
    ShopScreen,
)


INPUT_SCHEMA_VERSION = "noncombat-current-policy-simulator-bridge-input-v1"
SUCCESSOR_INPUT_SCHEMA_VERSION = (
    "noncombat-current-policy-simulator-bridge-input-v2"
)
SUCCESSOR_COMPARISON_SCHEMA_VERSION = (
    "noncombat-current-policy-simulator-bridge-successor-comparison-v1"
)
ROW_RESULT_SCHEMA_VERSION = "noncombat-current-policy-simulator-bridge-row-v1"
METRICS_SCHEMA_VERSION = "noncombat-current-policy-simulator-bridge-metrics-v1"
SUCCESSOR_METRICS_SCHEMA_VERSION = (
    "noncombat-current-policy-simulator-bridge-metrics-v2"
)
MANIFEST_SCHEMA_VERSION = "noncombat-current-policy-simulator-bridge-manifest-v1"
SUCCESSOR_MANIFEST_SCHEMA_VERSION = (
    "noncombat-current-policy-simulator-bridge-manifest-v2"
)
STAGE2_RESULT_SCHEMA_VERSION = (
    "noncombat-current-policy-simulator-bridge-stage2-v1"
)
STAGE2_REPLAY_COUNT = 2
STAGE2_MAX_DECISIONS_PER_EPISODE = 500
POLICY_ID = "current_optimized_ironclad_a0_conservative_snapshot_v1"
DEMONSTRATION_SCHEMA_VERSION = "noncombat-simulator-native-demonstration-v1"
DEMONSTRATION_ARTIFACT_SCHEMA_VERSION = (
    "noncombat-simulator-baseline-demonstrations-artifact-v1"
)
CANONICAL_ARTIFACT_NAMES = (
    "configuration.json",
    "execution_journal.json",
    "metrics.json",
    "report.md",
    "row_results.json",
)
V1_REGISTERED_SOURCE_FILES = (
    "analysis_scripts/noncombat_current_policy_simulator_bridge.py",
    "analysis_scripts/noncombat_simulator_adapter.py",
    "spirecomm/ai/agent.py",
    "spirecomm/ai/decision/base.py",
    "spirecomm/ai/heuristics/card.py",
    "spirecomm/ai/heuristics/deck.py",
    "spirecomm/ai/heuristics/ironclad_deck.py",
    "spirecomm/ai/heuristics/ironclad_evaluator.py",
    "spirecomm/ai/heuristics/map_routing.py",
    "spirecomm/ai/priorities.py",
    "spirecomm/data/loader.py",
    "spirecomm/spire/card.py",
    "spirecomm/spire/game.py",
    "spirecomm/spire/map.py",
    "spirecomm/spire/potion.py",
    "spirecomm/spire/relic.py",
    "spirecomm/spire/screen.py",
)
REGISTERED_SOURCE_FILES = (
    V1_REGISTERED_SOURCE_FILES[0],
    "analysis_scripts/noncombat_event_option_semantics.py",
    *V1_REGISTERED_SOURCE_FILES[1:],
)
ALL_FALSE_AUTHORITY = {
    "baseline_floor_authorized": False,
    "formal_rl_readiness_authorized": False,
    "fresh_evidence_authorized": False,
    "gameplay_authorized": False,
    "promotion_authorized": False,
    "reward_authorized": False,
    "training_authorized": False,
}
_POTION_METADATA_NAME_ALIASES = {
    "ELIXIR_POTION": ("Elixir Potion", "Elixir"),
    "FAIRY_POTION": ("Fairy Potion", "Fairy in a Bottle"),
    "GAMBLERS_BREW": ("Gamblers Brew", "Gambler's Brew"),
}
_RELIC_METADATA_IDENTITIES = {
    "BIRD_FACED_URN": ("Bird Faced Urn", "Bird-Faced Urn"),
    "CAPTAINS_WHEEL": ("Captains Wheel", "Captain's Wheel"),
    "CHARONS_ASHES": ("Charons Ashes", "Charon's Ashes"),
    "NILRYS_CODEX": ("Nilrys Codex", "Nilry's Codex"),
    "PHILOSOPHERS_STONE": ("Philosophers Stone", "Philosopher's Stone"),
    "SELF_FORMING_CLAY": ("Self Forming Clay", "Self-Forming Clay"),
    "DU_VU_DOLL": ("Du Vu Doll", "Du-Vu Doll"),
    "GOLD_PLATED_CABLES": ("Goldplated Cables", "Gold-Plated Cables"),
    "NEOWS_LAMENT": ("Neows Lament", "Neow's Lament"),
    "SLAVERS_COLLAR": ("Slavers Collar", "Slaver's Collar"),
    "DOLLYS_MIRROR": ("Dollys Mirror", "Dolly's Mirror"),
    "LEES_WAFFLE": ("Lees Waffle", "Lee's Waffle"),
    "NLOTHS_GIFT": ("Nloths Gift", "N'loth's Gift"),
    "NLOTHS_HUNGRY_FACE": ("Nloths Hungry Face", "N'loth's Hungry Face"),
    "PANDORAS_BOX": ("Pandoras Box", "Pandora's Box"),
    "CIRCLET": ("Circlet", None),
    "RED_CIRCLET": ("Red Circlet", None),
}
SUCCESSOR_IMMUTABLE_PATHS = (
    ("authority",),
    ("current_policy",),
    ("identity", "adapter_provenance"),
    ("identity", "frozen_demonstrations"),
    ("identity", "metadata"),
    ("identity", "prior_seed_evidence"),
    ("identity", "runtime"),
    ("stage1",),
    ("stage2",),
)
SUCCESSOR_MUTABLE_PATHS = (
    "schema_version",
    "identity.implementation",
    "identity.event_option_semantics",
    "identity.predecessor_registration",
    "identity.predecessor_manifest",
    "output.directory",
)


class BridgeBlocked(RuntimeError):
    """Raised when exact bridge evidence cannot be established."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


def _reject_duplicate_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise BridgeBlocked("duplicate_json_key", key)
        result[key] = value
    return result


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BridgeBlocked("invalid_mapping", label)
    return dict(value)


def _validated_event_semantics_identity(
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    actual = (
        reachable_event_option_semantics_identity()
        if value is None
        else _mapping(value, "event semantics identity")
    )
    supported = (
        reachable_event_option_semantics_identity(),
        event_option_semantics_identity(),
    )
    if actual not in supported:
        raise BridgeBlocked(
            "event_option_semantics_identity_mismatch",
            {"actual": actual, "expected": list(supported)},
        )
    return copy.deepcopy(actual)


def _registration_event_semantics_identity(
    registration: Mapping[str, Any],
) -> dict[str, Any]:
    if registration.get("schema_version") == SUCCESSOR_INPUT_SCHEMA_VERSION:
        return _validated_event_semantics_identity(
            _mapping(registration.get("identity"), "registration.identity").get(
                "event_option_semantics"
            )
        )
    if registration.get("schema_version") == INPUT_SCHEMA_VERSION:
        return event_option_semantics_identity()
    raise BridgeBlocked("registration_schema_mismatch")


def _sequence(value: object, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise BridgeBlocked("invalid_sequence", label)
    return list(value)


def _require_keys(value: Mapping[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise BridgeBlocked(
            "keys_mismatch",
            {"label": label, "actual": sorted(value), "expected": sorted(expected)},
        )


def _positive_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise BridgeBlocked("invalid_positive_integer", label)
    return value


def _nonnegative_int(value: object, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise BridgeBlocked("invalid_nonnegative_integer", label)
    return value


def _shop_remove_cost(value: object, *, purge_available: bool) -> int:
    if value == -1:
        if purge_available:
            raise BridgeBlocked("shop_remove_cost_sentinel_candidate_mismatch")
        return 0
    return _nonnegative_int(value, "shop remove_cost")


def _is_hex(value: object, length: int) -> bool:
    return (
        isinstance(value, str)
        and len(value) == length
        and all(character in "0123456789abcdef" for character in value.lower())
    )


def _validated_binding(
    value: object, label: str, *, repository_relative: bool
) -> dict[str, Any]:
    binding = _mapping(value, label)
    _require_keys(binding, {"path", "sha256", "size_bytes"}, label)
    path = binding["path"]
    if not isinstance(path, str) or not path:
        raise BridgeBlocked("invalid_binding_path", label)
    if repository_relative:
        pure_path = PurePosixPath(path.replace("\\", "/"))
        if pure_path.is_absolute() or ".." in pure_path.parts:
            raise BridgeBlocked("binding_path_not_repository_relative", label)
    elif not Path(path).is_absolute():
        raise BridgeBlocked("binding_path_not_absolute", label)
    if not _is_hex(binding["sha256"], 64):
        raise BridgeBlocked("invalid_binding_sha256", label)
    _positive_int(binding["size_bytes"], f"{label}.size_bytes")
    return binding


def _validated_current_policy(value: object) -> dict[str, Any]:
    policy = _mapping(value, "current_policy")
    _require_keys(
        policy,
        {
            "ascension",
            "character",
            "elite_mode",
            "gameplay_io_enabled",
            "policy_id",
            "screen_entrypoint",
            "tracker_enabled",
            "use_optimized_card_selection",
            "use_optimized_combat",
        },
        "current_policy",
    )
    expected = {
        "ascension": 0,
        "character": "IRONCLAD",
        "elite_mode": "conservative",
        "gameplay_io_enabled": False,
        "policy_id": POLICY_ID,
        "screen_entrypoint": "handle_screen",
        "tracker_enabled": False,
        "use_optimized_card_selection": True,
        "use_optimized_combat": True,
    }
    if policy != expected:
        raise BridgeBlocked(
            "current_policy_configuration_mismatch",
            {"actual": policy, "expected": expected},
        )
    return policy


def validate_registration(value: object) -> dict[str, Any]:
    """Validate an original or successor bridge registration without defaults."""

    registration = _mapping(value, "registration")
    authority = _mapping(registration.get("authority"), "authority")
    if authority != ALL_FALSE_AUTHORITY:
        raise BridgeBlocked("authority_must_be_all_false", authority)

    _require_keys(
        registration,
        {
            "authority",
            "current_policy",
            "identity",
            "output",
            "schema_version",
            "stage1",
            "stage2",
        },
        "registration",
    )
    schema_version = registration["schema_version"]
    if schema_version not in {INPUT_SCHEMA_VERSION, SUCCESSOR_INPUT_SCHEMA_VERSION}:
        raise BridgeBlocked("registration_schema_mismatch")
    registration["current_policy"] = _validated_current_policy(
        registration["current_policy"]
    )

    identity = _mapping(registration["identity"], "identity")
    identity_keys = {
        "adapter_provenance",
        "frozen_demonstrations",
        "implementation",
        "metadata",
        "prior_seed_evidence",
        "runtime",
    }
    if schema_version == SUCCESSOR_INPUT_SCHEMA_VERSION:
        identity_keys.update(
            {
                "event_option_semantics",
                "predecessor_manifest",
                "predecessor_registration",
            }
        )
    _require_keys(identity, identity_keys, "identity")
    try:
        identity["adapter_provenance"] = validate_provenance(
            identity["adapter_provenance"]
        )
    except (TypeError, ValueError) as exc:
        raise BridgeBlocked("invalid_adapter_provenance", str(exc)) from exc
    identity["frozen_demonstrations"] = _validated_binding(
        identity["frozen_demonstrations"],
        "identity.frozen_demonstrations",
        repository_relative=True,
    )
    identity["metadata"] = _validated_binding(
        identity["metadata"], "identity.metadata", repository_relative=False
    )
    identity["prior_seed_evidence"] = _validated_binding(
        identity["prior_seed_evidence"],
        "identity.prior_seed_evidence",
        repository_relative=True,
    )
    if schema_version == SUCCESSOR_INPUT_SCHEMA_VERSION:
        semantic_identity = _mapping(
            identity["event_option_semantics"],
            "identity.event_option_semantics",
        )
        expected_semantic_identity = event_option_semantics_identity()
        if semantic_identity != expected_semantic_identity:
            raise BridgeBlocked(
                "event_option_semantics_identity_mismatch",
                {
                    "actual": semantic_identity,
                    "expected": expected_semantic_identity,
                },
            )
        identity["event_option_semantics"] = semantic_identity
        identity["predecessor_registration"] = _validated_binding(
            identity["predecessor_registration"],
            "identity.predecessor_registration",
            repository_relative=True,
        )
        identity["predecessor_manifest"] = _validated_binding(
            identity["predecessor_manifest"],
            "identity.predecessor_manifest",
            repository_relative=True,
        )

    implementation = _mapping(identity["implementation"], "identity.implementation")
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "identity.implementation",
    )
    if not _is_hex(implementation["commit"], 40):
        raise BridgeBlocked("invalid_implementation_commit")
    expected_source_files = (
        V1_REGISTERED_SOURCE_FILES
        if schema_version == INPUT_SCHEMA_VERSION
        else REGISTERED_SOURCE_FILES
    )
    if implementation["source_files"] != list(expected_source_files):
        raise BridgeBlocked("implementation_source_files_mismatch")
    if not _is_hex(implementation["source_sha256"], 64):
        raise BridgeBlocked("invalid_implementation_source_sha256")
    identity["implementation"] = implementation

    runtime = _mapping(identity["runtime"], "identity.runtime")
    _require_keys(runtime, {"python"}, "identity.runtime")
    if not isinstance(runtime["python"], str) or not runtime["python"]:
        raise BridgeBlocked("invalid_runtime_python")
    identity["runtime"] = runtime
    registration["identity"] = identity

    stage1 = _mapping(registration["stage1"], "stage1")
    _require_keys(
        stage1,
        {"category_minimums", "replay_count", "rows"},
        "stage1",
    )
    minimums = _mapping(stage1["category_minimums"], "stage1.category_minimums")
    if set(minimums) != set(TARGET_CATEGORIES):
        raise BridgeBlocked("stage1_category_minimums_mismatch")
    for category in TARGET_CATEGORIES:
        _positive_int(minimums[category], f"stage1.category_minimums.{category}")
    stage1["category_minimums"] = minimums
    stage1["replay_count"] = _positive_int(
        stage1["replay_count"], "stage1.replay_count"
    )
    if stage1["replay_count"] < 2:
        raise BridgeBlocked("stage1_replay_count_too_small")
    rows = _sequence(stage1["rows"], "stage1.rows")
    if not rows:
        raise BridgeBlocked("stage1_rows_empty")
    normalized_rows = []
    row_keys = set()
    for index, raw_row in enumerate(rows):
        row = _mapping(raw_row, f"stage1.rows[{index}]")
        _require_keys(
            row,
            {
                "category",
                "cohort",
                "decision_index",
                "row_sha256",
                "seed",
                "source_snapshot_sha256",
            },
            f"stage1.rows[{index}]",
        )
        if row["category"] not in TARGET_CATEGORIES:
            raise BridgeBlocked("unsupported_stage1_category", row["category"])
        if row["cohort"] not in {"train", "validation"}:
            raise BridgeBlocked("unsupported_stage1_cohort", row["cohort"])
        _nonnegative_int(row["seed"], f"stage1.rows[{index}].seed")
        _nonnegative_int(
            row["decision_index"], f"stage1.rows[{index}].decision_index"
        )
        for field in ("row_sha256", "source_snapshot_sha256"):
            if not _is_hex(row[field], 64):
                raise BridgeBlocked("invalid_stage1_row_hash", {"index": index, "field": field})
        key = (row["cohort"], row["seed"], row["decision_index"])
        if key in row_keys:
            raise BridgeBlocked("duplicate_stage1_row", key)
        row_keys.add(key)
        normalized_rows.append(row)
    stage1["rows"] = normalized_rows
    registration["stage1"] = stage1

    stage2 = _mapping(registration["stage2"], "stage2")
    _require_keys(
        stage2,
        {
            "enabled_only_if_stage1_passes",
            "max_episodes",
            "prior_seed_json_path",
            "reused_seeds",
        },
        "stage2",
    )
    if stage2["enabled_only_if_stage1_passes"] is not True:
        raise BridgeBlocked("stage2_gate_must_be_enabled")
    seeds = _sequence(stage2["reused_seeds"], "stage2.reused_seeds")
    if not seeds or seeds != sorted(set(seeds)):
        raise BridgeBlocked("invalid_stage2_reused_seeds")
    for seed in seeds:
        _nonnegative_int(seed, "stage2.reused_seeds")
    if stage2["max_episodes"] != len(seeds):
        raise BridgeBlocked("stage2_max_episodes_mismatch")
    if stage2["prior_seed_json_path"] != "study.cohorts.compatibility_seeds":
        raise BridgeBlocked("stage2_prior_seed_json_path_mismatch")
    stage2["reused_seeds"] = seeds
    registration["stage2"] = stage2

    output = _mapping(registration["output"], "output")
    _require_keys(output, {"artifact_names", "directory"}, "output")
    if output["artifact_names"] != list(CANONICAL_ARTIFACT_NAMES):
        raise BridgeBlocked("output_artifact_names_mismatch")
    output_path = PurePosixPath(str(output["directory"]).replace("\\", "/"))
    if output_path.is_absolute() or ".." in output_path.parts:
        raise BridgeBlocked("output_directory_not_repository_relative")
    registration["output"] = output
    registration["authority"] = authority
    return registration


def _registration_value_at_path(
    registration: Mapping[str, Any], path: Sequence[str]
) -> object:
    current: object = registration
    for part in path:
        if not isinstance(current, Mapping) or part not in current:
            raise BridgeBlocked(
                "successor_comparison_path_missing", ".".join(path)
            )
        current = current[part]
    return current


def validate_successor_registration(
    successor: object, predecessor: object
) -> dict[str, Any]:
    """Prove that a v2 registration preserves the v1 execution contract."""

    normalized_successor = validate_registration(copy.deepcopy(successor))
    normalized_predecessor = validate_registration(copy.deepcopy(predecessor))
    if normalized_successor["schema_version"] != SUCCESSOR_INPUT_SCHEMA_VERSION:
        raise BridgeBlocked("successor_registration_schema_required")
    if normalized_predecessor["schema_version"] != INPUT_SCHEMA_VERSION:
        raise BridgeBlocked("predecessor_registration_schema_mismatch")

    immutable_paths = []
    for path in SUCCESSOR_IMMUTABLE_PATHS:
        actual = _registration_value_at_path(normalized_successor, path)
        expected = _registration_value_at_path(normalized_predecessor, path)
        path_label = ".".join(path)
        if actual != expected:
            raise BridgeBlocked(
                "successor_immutable_field_mismatch",
                {"actual": actual, "expected": expected, "path": path_label},
            )
        immutable_paths.append(path_label)

    if (
        normalized_successor["output"]["directory"]
        == normalized_predecessor["output"]["directory"]
    ):
        raise BridgeBlocked("successor_output_directory_not_new")
    return {
        "immutable_paths": immutable_paths,
        "mutable_paths": list(SUCCESSOR_MUTABLE_PATHS),
        "predecessor_schema_version": normalized_predecessor["schema_version"],
        "schema_version": SUCCESSOR_COMPARISON_SCHEMA_VERSION,
        "status": "passed",
        "successor_schema_version": normalized_successor["schema_version"],
    }


def load_registration(path: Path | str) -> dict[str, Any]:
    try:
        value = json.loads(
            Path(path).read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
        )
    except BridgeBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BridgeBlocked("cannot_load_registration", str(exc)) from exc
    return validate_registration(value)


class MetadataCatalog:
    """Exact item metadata used to hydrate simulator card snapshots."""

    def __init__(self, path: Path | str):
        self.path = Path(path).resolve()
        if not self.path.is_file():
            raise BridgeBlocked("metadata_missing", str(self.path))
        try:
            data = json.loads(
                self.path.read_text(encoding="utf-8"),
                object_pairs_hook=_reject_duplicate_pairs,
            )
        except BridgeBlocked:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise BridgeBlocked("metadata_invalid", str(exc)) from exc
        payload = _mapping(data, "metadata")
        for field in ("cards", "relics", "potions"):
            if not isinstance(payload.get(field), list):
                raise BridgeBlocked("metadata_collection_missing", field)
        self.sha256 = sha256_file(self.path)
        self.size_bytes = self.path.stat().st_size
        self.cards = self._index(payload["cards"], "cards", allow_duplicates=True)
        self.relics = self._index(payload["relics"], "relics")
        self.potions = self._index(payload["potions"], "potions")

    @staticmethod
    def _index(
        values: Sequence[object], label: str, *, allow_duplicates: bool = False
    ) -> dict[str, Any]:
        result = {}
        for index, raw in enumerate(values):
            item = _mapping(raw, f"metadata.{label}[{index}]")
            name = item.get("name")
            if not isinstance(name, str) or not name:
                raise BridgeBlocked("metadata_name_missing", f"{label}[{index}]")
            key = name.casefold()
            if allow_duplicates:
                result.setdefault(key, []).append(item)
            elif key in result:
                raise BridgeBlocked("metadata_duplicate_name", name)
            else:
                result[key] = item
        return result

    @staticmethod
    def _card_color_from_id(card_id: str) -> str | None:
        suffix_to_color = {
            "_BLUE": "blue",
            "_GREEN": "green",
            "_PURPLE": "purple",
            "_RED": "red",
        }
        upper_id = card_id.upper()
        for suffix, color in suffix_to_color.items():
            if upper_id.endswith(suffix):
                return color
        return None

    @staticmethod
    def _source_slot(value: Mapping[str, Any], label: str) -> int:
        slot = value.get("slot")
        if isinstance(slot, bool) or not isinstance(slot, int) or slot < 0:
            raise BridgeBlocked("missing_source_slot", label)
        return slot

    def card(self, value: Mapping[str, Any], *, role: str) -> Card:
        source = _mapping(value, f"{role} card")
        card_id = source.get("id")
        name = source.get("name")
        if not isinstance(card_id, str) or not card_id:
            raise BridgeBlocked("card_id_missing", role)
        if not isinstance(name, str) or not name:
            raise BridgeBlocked("card_name_missing", role)
        metadata_candidates = self.cards.get(name.casefold())
        if metadata_candidates is None:
            raise BridgeBlocked("card_metadata_missing", name)
        if len(metadata_candidates) == 1:
            metadata = metadata_candidates[0]
        else:
            color = self._card_color_from_id(card_id)
            color_matches = [
                candidate
                for candidate in metadata_candidates
                if str(candidate.get("color", "")).casefold() == color
            ]
            if len(color_matches) != 1:
                raise BridgeBlocked(
                    "card_metadata_ambiguous",
                    {
                        "card_id": card_id,
                        "name": name,
                        "candidate_colors": [
                            candidate.get("color") for candidate in metadata_candidates
                        ],
                    },
                )
            metadata = color_matches[0]
        slot = self._source_slot(source, role)
        type_name = str(metadata.get("type", "")).upper()
        rarity_name = str(metadata.get("rarity", "")).upper()
        try:
            card_type = CardType[type_name]
            rarity = CardRarity[rarity_name]
        except KeyError as exc:
            raise BridgeBlocked(
                "card_metadata_enum_invalid",
                {"name": name, "type": type_name, "rarity": rarity_name},
            ) from exc
        raw_cost = str(metadata.get("cost", "")).strip().upper()
        if raw_cost == "X":
            cost = -1
        elif raw_cost in {"UNPLAYABLE", "-"}:
            cost = -2
        else:
            try:
                cost = int(raw_cost)
            except ValueError as exc:
                raise BridgeBlocked("card_metadata_cost_invalid", name) from exc
        upgrades = source.get("upgrade_count")
        if isinstance(upgrades, bool) or not isinstance(upgrades, int) or upgrades < 0:
            raise BridgeBlocked("card_upgrade_count_invalid", name)
        upgraded = source.get("upgraded")
        if not isinstance(upgraded, bool) or upgraded != (upgrades > 0):
            raise BridgeBlocked("card_upgrade_flag_mismatch", name)
        misc = source.get("misc", 0)
        if isinstance(misc, bool) or not isinstance(misc, int):
            raise BridgeBlocked("card_misc_invalid", name)
        price = source.get("price", 0)
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise BridgeBlocked("card_price_invalid", name)
        card = Card(
            card_id=card_id,
            name=name,
            card_type=card_type,
            rarity=rarity,
            upgrades=upgrades,
            has_target=False,
            cost=cost,
            uuid=f"bridge:{role}:{slot}:{card_id}:{upgrades}",
            misc=misc,
            price=price,
        )
        card._bridge_source_slot = slot
        card._bridge_source_role = role
        return card

    def relic(self, value: Mapping[str, Any], *, role: str) -> Relic:
        source = _mapping(value, f"{role} relic")
        relic_id = source.get("id")
        name = source.get("name")
        if not isinstance(relic_id, str) or not relic_id:
            raise BridgeBlocked("relic_id_missing", role)
        if not isinstance(name, str) or not name:
            raise BridgeBlocked("relic_name_missing", role)
        identity = _RELIC_METADATA_IDENTITIES.get(relic_id)
        hydrated_name = name
        if identity is not None:
            expected_native_name, metadata_name = identity
            if name.casefold() != expected_native_name.casefold():
                raise BridgeBlocked("relic_metadata_missing", name)
            if metadata_name is None:
                metadata = self.relics.get(name.casefold())
                if metadata is not None:
                    hydrated_name = metadata["name"]
            else:
                metadata = self.relics.get(metadata_name.casefold())
                if metadata is None:
                    raise BridgeBlocked("relic_metadata_missing", name)
                hydrated_name = metadata["name"]
        elif name.casefold() not in self.relics:
            raise BridgeBlocked("relic_metadata_missing", name)
        counter = source.get("data", 0)
        price = source.get("price", 0)
        if isinstance(counter, bool) or not isinstance(counter, int):
            raise BridgeBlocked("relic_counter_invalid", name)
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise BridgeBlocked("relic_price_invalid", name)
        relic = Relic(relic_id, hydrated_name, counter=counter, price=price)
        if "slot" in source:
            relic._bridge_source_slot = self._source_slot(source, role)
        return relic

    def potion(self, value: Mapping[str, Any], *, role: str) -> Potion:
        source = _mapping(value, f"{role} potion")
        potion_id = source.get("id")
        name = source.get("name")
        if not isinstance(potion_id, str) or not isinstance(name, str):
            raise BridgeBlocked("potion_identity_missing", role)
        slot = self._source_slot(source, role)
        if potion_id == "EMPTY_POTION_SLOT" and name == "EMPTY_POTION_SLOT":
            potion = Potion("Potion Slot", "Potion Slot", False, False, False)
        else:
            alias = _POTION_METADATA_NAME_ALIASES.get(potion_id)
            metadata_name = name
            if alias is not None:
                expected_native_name, metadata_name = alias
                if name.casefold() != expected_native_name.casefold():
                    raise BridgeBlocked("potion_metadata_missing", name)
            metadata = self.potions.get(metadata_name.casefold())
            if metadata is None:
                raise BridgeBlocked("potion_metadata_missing", name)
            price = source.get("price", 0)
            if isinstance(price, bool) or not isinstance(price, int) or price < 0:
                raise BridgeBlocked("potion_price_invalid", name)
            hydrated_name = metadata["name"] if alias is not None else name
            potion = Potion(
                potion_id, hydrated_name, False, False, False, price=price
            )
        potion._bridge_source_slot = slot
        return potion


def _hydrate_map(value: object) -> Map:
    payload = _mapping(value, "state.map")
    nodes = _sequence(payload.get("nodes"), "state.map.nodes")
    dungeon_map = Map()
    source_nodes = {}
    for index, raw in enumerate(nodes):
        source = _mapping(raw, f"state.map.nodes[{index}]")
        x = source.get("x")
        y = source.get("y")
        symbol = source.get("symbol")
        if (
            isinstance(x, bool)
            or not isinstance(x, int)
            or isinstance(y, bool)
            or not isinstance(y, int)
            or not isinstance(symbol, str)
            or not symbol
        ):
            raise BridgeBlocked("map_node_invalid", index)
        if (x, y) in source_nodes:
            raise BridgeBlocked("map_node_duplicate", (x, y))
        node = Node(x, y, symbol)
        node.room = source.get("room")
        dungeon_map.add_node(node)
        source_nodes[(x, y)] = source
    for coordinate, source in source_nodes.items():
        node = dungeon_map.get_node(*coordinate)
        for raw_edge in _sequence(source.get("edges"), f"map node {coordinate}.edges"):
            edge = _mapping(raw_edge, f"map node {coordinate}.edge")
            child = dungeon_map.get_node(edge.get("x"), edge.get("y"))
            if child is None:
                if edge.get("y") == 15 and isinstance(edge.get("x"), int):
                    child = Node(edge["x"], 15, "B")
                    child.room = "BOSS"
                    dungeon_map.add_node(child)
                else:
                    raise BridgeBlocked("map_edge_target_missing", edge)
            node.children.append(child)
    return dungeon_map


_EVENT_OPTION_LEGACY_KEYS = {"choice_index", "label", "text"}
_EVENT_OPTION_V2_KEYS = {
    "choice_index",
    "current_position",
    "label",
    "simulator_choice_index",
    "text",
}


def _event_candidate_indices(candidates: Sequence[Mapping[str, Any]]) -> list[int]:
    indices = []
    for position, raw_candidate in enumerate(candidates):
        candidate = _mapping(raw_candidate, f"event candidate[{position}]")
        if candidate.get("kind") != "event_option":
            raise BridgeBlocked(
                "event_option_semantics_candidate_kind_mismatch",
                candidate.get("action_id"),
            )
        raw = _mapping(candidate.get("raw"), f"event candidate[{position}].raw")
        simulator_index = raw.get("idx1")
        if (
            isinstance(simulator_index, bool)
            or not isinstance(simulator_index, int)
            or simulator_index < 0
        ):
            raise BridgeBlocked(
                "event_option_semantics_candidate_index_invalid",
                candidate.get("action_id"),
            )
        indices.append(simulator_index)
    if indices != sorted(set(indices)):
        raise BridgeBlocked("event_option_semantics_candidate_order_invalid", indices)
    return indices


def _normalize_event_option_semantics(
    semantics: object,
    candidates: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], str]:
    if not isinstance(semantics, list):
        raise BridgeBlocked("missing_event_option_semantics")
    candidate_indices = _event_candidate_indices(candidates)
    if len(semantics) != len(candidate_indices):
        raise BridgeBlocked(
            "event_option_semantics_candidate_mismatch",
            {"semantics_count": len(semantics), "candidates": candidate_indices},
        )

    normalized = []
    row_versions = set()
    for position, raw_option in enumerate(semantics):
        option = _mapping(raw_option, f"event option_semantics[{position}]")
        keys = set(option)
        if keys == _EVENT_OPTION_LEGACY_KEYS:
            row_versions.add("legacy")
            current_position = option.get("choice_index")
            simulator_choice_index = current_position
        elif keys == _EVENT_OPTION_V2_KEYS:
            row_versions.add("v2")
            current_position = option.get("current_position")
            simulator_choice_index = option.get("simulator_choice_index")
        else:
            raise BridgeBlocked(
                "event_option_semantics_invalid",
                {"position": position, "keys": sorted(keys)},
            )

        choice_index = option.get("choice_index")
        label = option.get("label")
        text = option.get("text")
        if (
            isinstance(choice_index, bool)
            or not isinstance(choice_index, int)
            or choice_index < 0
            or isinstance(current_position, bool)
            or not isinstance(current_position, int)
            or current_position < 0
            or isinstance(simulator_choice_index, bool)
            or not isinstance(simulator_choice_index, int)
            or simulator_choice_index < 0
            or choice_index != current_position
            or not isinstance(label, str)
            or not label
            or not isinstance(text, str)
            or not text
        ):
            raise BridgeBlocked("event_option_semantics_invalid", position)
        normalized.append(
            {
                "choice_index": current_position,
                "current_position": current_position,
                "label": label,
                "simulator_choice_index": simulator_choice_index,
                "text": text,
            }
        )

    if len(row_versions) != 1:
        raise BridgeBlocked("event_option_semantics_version_mixed")
    current_positions = [row["current_position"] for row in normalized]
    expected_positions = list(range(len(normalized)))
    if current_positions != expected_positions:
        raise BridgeBlocked(
            "event_option_semantics_position_mismatch",
            {"actual": current_positions, "expected": expected_positions},
        )
    simulator_indices = [row["simulator_choice_index"] for row in normalized]
    if "legacy" in row_versions and candidate_indices != expected_positions:
        raise BridgeBlocked(
            "event_option_semantics_legacy_ambiguous", candidate_indices
        )
    if simulator_indices != candidate_indices:
        raise BridgeBlocked(
            "event_option_semantics_candidate_mismatch",
            {"semantics": simulator_indices, "candidates": candidate_indices},
        )
    source = "inline_legacy_contiguous" if "legacy" in row_versions else "inline_v2"
    return normalized, source


def _hydrate_event_screen(
    state: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> tuple[EventScreen, list[EventOption]]:
    context = _mapping(state.get("decision_context"), "event decision_context")
    event_id = context.get("event_id")
    event_name = context.get("event_name")
    if not isinstance(event_id, str) or not isinstance(event_name, str):
        raise BridgeBlocked("event_identity_missing")
    semantics, _ = _normalize_event_option_semantics(
        context.get("option_semantics"), candidates
    )
    options = [
        EventOption(
            option["text"],
            option["label"],
            False,
            option["current_position"],
        )
        for option in semantics
    ]
    screen = EventScreen(event_name, event_id, "")
    screen.options = options
    return screen, options


def enrich_event_option_semantics(
    *,
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    simulator_provenance: Mapping[str, Any] | None,
    semantics_identity: Mapping[str, Any] | None = None,
) -> tuple[dict[str, Any], str]:
    """Return a hydration copy with exact event semantics when required."""

    before_snapshot = canonical_json_bytes(snapshot)
    before_candidates = canonical_json_bytes(candidates)
    enriched = copy.deepcopy(dict(snapshot))
    if enriched.get("category") != "event":
        return enriched, "not_applicable"

    state = _mapping(enriched.get("state"), "snapshot.state")
    context = _mapping(
        state.get("decision_context"), "snapshot.state.decision_context"
    )
    if "option_semantics" in context:
        semantics, source = _normalize_event_option_semantics(
            context["option_semantics"], candidates
        )
        context["option_semantics"] = semantics
    else:
        if simulator_provenance is None:
            raise BridgeBlocked("event_option_semantics_provenance_missing")
        resolved_identity = _validated_event_semantics_identity(
            semantics_identity
        )
        try:
            resolver = (
                resolve_reachable_event_option_observation
                if resolved_identity
                == reachable_event_option_semantics_identity()
                else resolve_event_option_observation
            )
            observation = resolver(
                snapshot=snapshot,
                candidates=candidates,
                simulator_provenance=simulator_provenance,
            )
        except EventOptionSemanticsError as exc:
            raise BridgeBlocked(exc.reason, exc.detail) from exc
        semantics, _ = _normalize_event_option_semantics(
            observation["options"], candidates
        )
        context["event_id"] = observation["current_event_id"]
        context["option_semantics"] = semantics
        source = observation.get(
            "semantic_source", resolved_identity["contract_id"]
        )
        if source != resolved_identity["contract_id"]:
            raise BridgeBlocked(
                "event_option_semantics_source_mismatch",
                {"actual": source, "expected": resolved_identity["contract_id"]},
            )
    state["decision_context"] = context
    enriched["state"] = state

    if canonical_json_bytes(snapshot) != before_snapshot:
        raise BridgeBlocked("source_snapshot_mutated_during_semantic_enrichment")
    if canonical_json_bytes(candidates) != before_candidates:
        raise BridgeBlocked("source_candidates_mutated_during_semantic_enrichment")
    return enriched, source


def hydrate_game(
    snapshot: Mapping[str, Any],
    candidates: Sequence[Mapping[str, Any]],
    metadata: MetadataCatalog,
) -> Game:
    """Hydrate one validated simulator snapshot without mutating its sources."""

    before_snapshot = canonical_json_bytes(snapshot)
    before_candidates = canonical_json_bytes(candidates)
    try:
        normalized_snapshot = validate_snapshot(copy.deepcopy(dict(snapshot)))
        category = normalized_snapshot.get("category")
        normalized_candidates = validate_candidates(
            copy.deepcopy(list(candidates)), category=category
        )
    except (TypeError, ValueError) as exc:
        raise BridgeBlocked("invalid_adapter_row", str(exc)) from exc
    if normalized_snapshot["terminal"] or category not in TARGET_CATEGORIES:
        raise BridgeBlocked("snapshot_not_target_decision")
    state = _mapping(normalized_snapshot["state"], "snapshot.state")

    game = Game()
    game.current_hp = _nonnegative_int(state.get("cur_hp"), "state.cur_hp")
    game.max_hp = _positive_int(state.get("max_hp"), "state.max_hp")
    game.floor = _nonnegative_int(state.get("floor"), "state.floor")
    game.act = _positive_int(state.get("act"), "state.act")
    game.gold = _nonnegative_int(state.get("gold"), "state.gold")
    game.ascension_level = _nonnegative_int(
        state.get("ascension"), "state.ascension"
    )
    game.seed = state.get("seed")
    game.character = PlayerClass.IRONCLAD
    game.act_boss = state.get("boss")
    game.has_emerald_key = bool(state.get("green_key"))
    game.has_sapphire_key = bool(state.get("blue_key"))
    game.has_ruby_key = bool(state.get("red_key"))
    game.deck = [
        metadata.card(_mapping(card, "deck card"), role="deck")
        for card in _sequence(state.get("deck"), "state.deck")
    ]
    game.relics = [
        metadata.relic(_mapping(relic, "run relic"), role="run")
        for relic in _sequence(state.get("relics"), "state.relics")
    ]
    game.potions = [
        metadata.potion(_mapping(potion, "run potion"), role="run")
        for potion in _sequence(state.get("potions"), "state.potions")
    ]
    game.map = _hydrate_map(state.get("map"))
    game.in_combat = False
    game.room_phase = RoomPhase.INCOMPLETE
    game.room_type = str(state.get("cur_room", ""))
    game.monsters = []
    game.hand = []
    game.available_commands = ["choose"]
    game.choice_available = False
    game.choice_list = []
    game.screen_up = True

    if category == "route":
        current = _mapping(state.get("cur_map_node"), "state.cur_map_node")
        current_x = current.get("x")
        current_y = current.get("y")
        if not isinstance(current_x, int) or not isinstance(current_y, int):
            raise BridgeBlocked("current_map_node_invalid")
        current_node = game.map.get_node(current_x, current_y)
        if current_node is None:
            current_node = Node(current_x, current_y, "O")
        next_nodes = []
        boss_candidates = []
        for candidate in normalized_candidates:
            raw = candidate["raw"]
            x = raw.get("x")
            y = raw.get("y")
            if not isinstance(x, int) or not isinstance(y, int):
                raise BridgeBlocked("route_candidate_coordinate_missing", candidate["action_id"])
            node = game.map.get_node(x, y)
            if node is None:
                if raw.get("room") != "BOSS":
                    raise BridgeBlocked("route_candidate_node_missing", candidate["action_id"])
                node = Node(x, y, "B")
            next_nodes.append(node)
            if raw.get("room") == "BOSS":
                boss_candidates.append(candidate)
        if boss_candidates and len(normalized_candidates) != 1:
            raise BridgeBlocked("boss_candidate_not_unique")
        game.screen_type = ScreenType.MAP
        game.screen = MapScreen(current_node, next_nodes, bool(boss_candidates))
    elif category == "card_reward":
        context = _mapping(state.get("decision_context"), "card reward decision_context")
        cards = [
            metadata.card(_mapping(card, "reward card"), role="reward")
            for card in _sequence(context.get("cards"), "card reward cards")
        ]
        kinds = {candidate["kind"] for candidate in normalized_candidates}
        can_bowl = context.get("has_singing_bowl")
        if not isinstance(can_bowl, bool):
            raise BridgeBlocked("card_reward_bowl_flag_missing")
        if can_bowl != ("bowl" in kinds):
            raise BridgeBlocked("card_reward_bowl_candidate_mismatch")
        game.screen_type = ScreenType.CARD_REWARD
        game.screen = CardRewardScreen(cards, can_bowl, "skip" in kinds or can_bowl)
        game.available_commands = ["choose", "skip"]
        game.cancel_available = True
    elif category == "shop":
        context = _mapping(state.get("decision_context"), "shop decision_context")
        cards = [
            metadata.card(_mapping(card, "shop card"), role="shop_card")
            for card in _sequence(context.get("cards"), "shop cards")
        ]
        relics = [
            metadata.relic(_mapping(relic, "shop relic"), role="shop_relic")
            for relic in _sequence(context.get("relics"), "shop relics")
        ]
        potions = [
            metadata.potion(_mapping(potion, "shop potion"), role="shop_potion")
            for potion in _sequence(context.get("potions"), "shop potions")
        ]
        purge_available = any(
            candidate["kind"] == "remove_card" for candidate in normalized_candidates
        )
        purge_cost = _shop_remove_cost(
            context.get("remove_cost"), purge_available=purge_available
        )
        game.screen_type = ScreenType.SHOP_SCREEN
        game.screen = ShopScreen(cards, relics, potions, purge_available, purge_cost)
        game.available_commands = ["choose", "leave"]
        game.cancel_available = True
    else:
        game.screen_type = ScreenType.EVENT
        game.screen, game.choice_list = _hydrate_event_screen(
            state, normalized_candidates
        )
        game.choice_available = True

    if canonical_json_bytes(snapshot) != before_snapshot:
        raise BridgeBlocked("source_snapshot_mutated_during_hydration")
    if canonical_json_bytes(candidates) != before_candidates:
        raise BridgeBlocked("source_candidates_mutated_during_hydration")
    return game


def _unique_match(
    candidates: Sequence[Mapping[str, Any]],
    predicate,
    *,
    category: str,
) -> str:
    matches = [candidate for candidate in candidates if predicate(candidate)]
    if len(matches) == 1:
        return str(matches[0]["action_id"])
    reason = "candidate_mapping_absent" if not matches else "candidate_mapping_ambiguous"
    raise BridgeBlocked(
        reason,
        {
            "category": category,
            "candidate_action_ids": [candidate["action_id"] for candidate in candidates],
            "matched_action_ids": [candidate["action_id"] for candidate in matches],
        },
    )


def map_current_action(
    *,
    category: str,
    action: object,
    candidates: Sequence[Mapping[str, Any]],
    event_semantics_validated: bool = False,
    event_option_semantics: Sequence[Mapping[str, Any]] | None = None,
) -> str:
    """Map one Current action object to exactly one stable simulator candidate."""

    try:
        normalized = validate_candidates(copy.deepcopy(list(candidates)), category=category)
    except (TypeError, ValueError) as exc:
        raise BridgeBlocked("invalid_candidate_set", str(exc)) from exc

    if category == "route":
        if isinstance(action, ChooseMapBossAction):
            return _unique_match(
                normalized,
                lambda candidate: candidate["kind"] == "map_node"
                and candidate["raw"].get("room") == "BOSS",
                category=category,
            )
        if not isinstance(action, ChooseMapNodeAction):
            raise BridgeBlocked("unsupported_current_action", type(action).__name__)
        x = getattr(action.node, "x", None)
        y = getattr(action.node, "y", None)
        return _unique_match(
            normalized,
            lambda candidate: candidate["kind"] == "map_node"
            and candidate["raw"].get("x") == x
            and candidate["raw"].get("y") == y,
            category=category,
        )

    if category == "card_reward":
        if isinstance(action, CardRewardAction) and action.name == "bowl":
            kind = "bowl"
            return _unique_match(
                normalized, lambda candidate: candidate["kind"] == kind, category=category
            )
        if isinstance(action, CancelAction):
            return _unique_match(
                normalized,
                lambda candidate: candidate["kind"] == "skip",
                category=category,
            )
        if not isinstance(action, CardRewardAction):
            raise BridgeBlocked("unsupported_current_action", type(action).__name__)
        slot = getattr(action, "_bridge_source_slot", None)
        if not isinstance(slot, int):
            raise BridgeBlocked("missing_source_slot", "card_reward")
        return _unique_match(
            normalized,
            lambda candidate: candidate["kind"] == "take"
            and candidate["raw"].get("slot") == slot,
            category=category,
        )

    if category == "shop":
        inventory_types = (
            (BuyCardAction, "buy_card"),
            (BuyRelicAction, "buy_relic"),
            (BuyPotionAction, "buy_potion"),
        )
        for action_type, kind in inventory_types:
            if isinstance(action, action_type):
                slot = getattr(action, "_bridge_source_slot", None)
                if not isinstance(slot, int):
                    raise BridgeBlocked("missing_source_slot", kind)
                return _unique_match(
                    normalized,
                    lambda candidate, expected_kind=kind: candidate["kind"]
                    == expected_kind
                    and candidate["raw"].get("slot") == slot,
                    category=category,
                )
        if isinstance(action, ChooseAction) and action.name == "purge":
            return _unique_match(
                normalized,
                lambda candidate: candidate["kind"] == "remove_card",
                category=category,
            )
        if isinstance(action, (LeaveAction, ProceedAction, CancelAction)):
            return _unique_match(
                normalized,
                lambda candidate: candidate["kind"] == "leave",
                category=category,
            )
        raise BridgeBlocked("unsupported_current_action", type(action).__name__)

    if category == "event":
        if not event_semantics_validated or event_option_semantics is None:
            raise BridgeBlocked("missing_event_option_semantics")
        if not isinstance(action, ChooseAction) or action.name is not None:
            raise BridgeBlocked("unsupported_current_action", type(action).__name__)
        current_position = action.choice_index
        if (
            isinstance(current_position, bool)
            or not isinstance(current_position, int)
            or current_position < 0
        ):
            raise BridgeBlocked("event_option_position_invalid", current_position)
        semantics, _ = _normalize_event_option_semantics(
            list(event_option_semantics), normalized
        )
        matching_rows = [
            row
            for row in semantics
            if row["current_position"] == current_position
        ]
        if len(matching_rows) != 1:
            raise BridgeBlocked("event_option_position_invalid", current_position)
        simulator_choice_index = matching_rows[0]["simulator_choice_index"]
        return _unique_match(
            normalized,
            lambda candidate: candidate["kind"] == "event_option"
            and candidate["raw"].get("idx1") == simulator_choice_index,
            category=category,
        )
    raise BridgeBlocked("unsupported_category", category)


def _capture_source(action: object, source: object, kind: str) -> object:
    slot = getattr(source, "_bridge_source_slot", None)
    if isinstance(slot, int):
        action._bridge_source_slot = slot
    action._bridge_action_kind = kind
    return action


@contextmanager
def _traced_current_actions():
    class TracedCardRewardAction(CardRewardAction):
        def __init__(self, card=None, bowl=False):
            super().__init__(card=card, bowl=bowl)
            if card is not None:
                _capture_source(self, card, "take")

    class TracedBuyCardAction(BuyCardAction):
        def __init__(self, card):
            super().__init__(card)
            _capture_source(self, card, "buy_card")

    class TracedBuyRelicAction(BuyRelicAction):
        def __init__(self, relic):
            super().__init__(relic)
            _capture_source(self, relic, "buy_relic")

    class TracedBuyPotionAction(BuyPotionAction):
        def __init__(self, potion):
            super().__init__(potion)
            _capture_source(self, potion, "buy_potion")

    def blocked_simple_card_reward(_self):
        raise BridgeBlocked("simpleagent_card_reward_fallback")

    with ExitStack() as stack:
        stack.enter_context(patch.object(agent_module, "CardRewardAction", TracedCardRewardAction))
        stack.enter_context(patch.object(agent_module, "BuyCardAction", TracedBuyCardAction))
        stack.enter_context(patch.object(agent_module, "BuyRelicAction", TracedBuyRelicAction))
        stack.enter_context(patch.object(agent_module, "BuyPotionAction", TracedBuyPotionAction))
        stack.enter_context(
            patch.object(agent_module.SimpleAgent, "choose_card_reward", blocked_simple_card_reward)
        )
        yield


class CurrentPolicyBridgeSession:
    """Episode-local Current agent with gameplay side effects disabled."""

    def __init__(
        self,
        *,
        metadata: MetadataCatalog,
        current_policy: Mapping[str, Any],
        event_semantics_identity: Mapping[str, Any] | None = None,
        require_global_metadata_match: bool = True,
        simulator_provenance: Mapping[str, Any] | None = None,
    ):
        self.metadata = metadata
        self.current_policy = _validated_current_policy(current_policy)
        self.event_semantics_identity = _validated_event_semantics_identity(
            event_semantics_identity
        )
        self.simulator_provenance = (
            copy.deepcopy(dict(simulator_provenance))
            if simulator_provenance is not None
            else None
        )
        if require_global_metadata_match:
            active_path = Path(game_data_loader.items_file).resolve()
            if active_path != metadata.path:
                raise BridgeBlocked(
                    "active_metadata_path_mismatch",
                    {"active": str(active_path), "registered": str(metadata.path)},
                )
            if sha256_file(active_path) != metadata.sha256:
                raise BridgeBlocked("active_metadata_hash_mismatch")
        if not agent_module.OPTIMIZED_AI_AVAILABLE:
            raise BridgeBlocked("optimized_components_unavailable")
        self.agent = OptimizedAgent(
            chosen_class=PlayerClass.IRONCLAD,
            use_optimized_combat=True,
            use_optimized_card_selection=True,
            elite_mode="conservative",
        )
        self.agent.game_tracker = None
        if (
            self.agent.card_evaluator is None
            or self.agent.deck_strategy is None
            or self.agent.map_router is None
        ):
            raise BridgeBlocked("optimized_components_downgraded")
        self._last_decision_index: int | None = None

    def evaluate(
        self,
        *,
        snapshot: Mapping[str, Any],
        candidates: Sequence[Mapping[str, Any]],
        decision_index: int,
    ) -> dict[str, Any]:
        if self._last_decision_index is not None and decision_index <= self._last_decision_index:
            raise BridgeBlocked(
                "episode_decision_order_invalid",
                {"previous": self._last_decision_index, "current": decision_index},
            )
        before_snapshot = canonical_json_bytes(snapshot)
        before_candidates = canonical_json_bytes(candidates)
        hydration_snapshot, event_semantics_source = enrich_event_option_semantics(
            snapshot=snapshot,
            candidates=candidates,
            simulator_provenance=self.simulator_provenance,
            semantics_identity=self.event_semantics_identity,
        )
        game = hydrate_game(hydration_snapshot, candidates, self.metadata)
        if game.ascension_level != self.current_policy["ascension"]:
            raise BridgeBlocked("snapshot_ascension_mismatch", game.ascension_level)
        self.agent.game = game
        try:
            with _traced_current_actions():
                action = self.agent.handle_screen()
        except BridgeBlocked:
            raise
        except Exception as exc:
            raise BridgeBlocked(
                "current_policy_exception",
                {"type": type(exc).__name__, "message": str(exc)},
            ) from exc
        if self.agent.game_tracker is not None:
            raise BridgeBlocked("tracker_reenabled")
        category = snapshot.get("category")
        event_option_semantics = None
        event_observation = None
        if category == "event":
            hydration_state = _mapping(
                hydration_snapshot.get("state"), "hydration snapshot.state"
            )
            hydration_context = _mapping(
                hydration_state.get("decision_context"),
                "hydration snapshot.state.decision_context",
            )
            event_option_semantics = hydration_context.get("option_semantics")
        action_id = map_current_action(
            category=category,
            action=action,
            candidates=candidates,
            event_semantics_validated=(category == "event"),
            event_option_semantics=event_option_semantics,
        )
        if canonical_json_bytes(snapshot) != before_snapshot:
            raise BridgeBlocked("source_snapshot_mutated_during_evaluation")
        if canonical_json_bytes(candidates) != before_candidates:
            raise BridgeBlocked("source_candidates_mutated_during_evaluation")
        if category == "event":
            source_state = _mapping(snapshot.get("state"), "snapshot.state")
            source_context = _mapping(
                source_state.get("decision_context"),
                "snapshot.state.decision_context",
            )
            current_position = getattr(action, "choice_index", None)
            matching_semantics = [
                row
                for row in _sequence(
                    event_option_semantics, "event option semantics"
                )
                if isinstance(row, Mapping)
                and row.get("current_position") == current_position
            ]
            if len(matching_semantics) != 1:
                raise BridgeBlocked(
                    "event_option_position_invalid", current_position
                )
            event_observation = {
                "current_event_id": hydration_context.get("event_id"),
                "current_position": current_position,
                "event_data": source_context.get("event_data"),
                "selected_action_id": action_id,
                "semantics_source": event_semantics_source,
                "simulator_choice_index": matching_semantics[0].get(
                    "simulator_choice_index"
                ),
                "upstream_event_id": source_context.get("event_id"),
            }
        self._last_decision_index = decision_index
        result = {
            "action_id": action_id,
            "action_type": type(action).__name__,
            "category": category,
            "fallback_used": False,
            "input_candidates_sha256": sha256_bytes(before_candidates),
            "input_snapshot_sha256": sha256_bytes(before_snapshot),
            "policy_id": POLICY_ID,
            "source_mutated": False,
            "tracker_enabled": False,
        }
        if category == "event":
            result["event_semantics_source"] = event_semantics_source
            result["event_observation"] = event_observation
        return result


def _registered_stage2_native_identity(
    registration: Mapping[str, Any]
) -> dict[str, Any]:
    provenance = registration["identity"]["adapter_provenance"]
    return {
        "build": copy.deepcopy(provenance["build"]),
        "module_sha256": provenance["module_sha256"],
        "module_size_bytes": provenance["module_size_bytes"],
        "simulator_commit": provenance["simulator_commit"],
        "simulator_dirty": provenance["simulator_dirty"],
        "simulator_source_file_count": provenance["simulator_source_file_count"],
        "simulator_source_sha256": provenance["simulator_source_sha256"],
        "submodules": copy.deepcopy(provenance["submodules"]),
    }


def validate_stage2_native_identity(
    registration: Mapping[str, Any], actual_identity: object
) -> dict[str, Any]:
    """Validate every executable native identity field before Stage 2."""

    actual = _mapping(actual_identity, "stage2 native identity")
    expected = _registered_stage2_native_identity(registration)
    mismatches = sorted(
        key for key in set(actual) | set(expected) if actual.get(key) != expected.get(key)
    )
    if mismatches:
        raise BridgeBlocked(
            "stage2_native_identity_mismatch",
            {
                "actual": actual,
                "expected": expected,
                "fields": mismatches,
            },
        )
    return copy.deepcopy(actual)


def _git_text(repo: Path, *args: str) -> str:
    try:
        completed = subprocess.run(
            ["git", *args],
            cwd=repo,
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise BridgeBlocked(
            "stage2_native_git_identity_failed",
            {"args": list(args), "repository": str(repo)},
        ) from exc
    return completed.stdout.strip()


def collect_stage2_native_identity(
    *,
    module_path: Path | str,
    simulator_repo: Path | str,
    native_module: object,
) -> dict[str, Any]:
    """Collect content identities from runtime discovery paths."""

    module_file = Path(module_path).resolve()
    simulator = Path(simulator_repo).resolve()
    if not module_file.is_file():
        raise BridgeBlocked("stage2_native_module_missing", str(module_file))
    if not simulator.is_dir():
        raise BridgeBlocked("stage2_simulator_repository_missing", str(simulator))
    try:
        build = json.loads(native_module.build_info_json())
    except (AttributeError, TypeError, json.JSONDecodeError) as exc:
        raise BridgeBlocked("stage2_native_build_identity_invalid", str(exc)) from exc
    build["python"] = sys.version.split()[0]
    source_sha256, source_file_count = hash_compiled_simulator_sources(simulator)
    return {
        "build": build,
        "module_sha256": sha256_file(module_file),
        "module_size_bytes": module_file.stat().st_size,
        "simulator_commit": _git_text(simulator, "rev-parse", "HEAD"),
        "simulator_dirty": bool(_git_text(simulator, "status", "--porcelain=v1")),
        "simulator_source_file_count": source_file_count,
        "simulator_source_sha256": source_sha256,
        "submodules": {
            "json": _git_text(simulator / "json", "rev-parse", "HEAD"),
            "pybind11": _git_text(simulator / "pybind11", "rev-parse", "HEAD"),
        },
    }


def _run_stage2_replay(
    *,
    environment: Any,
    session: Any,
    seed: int,
) -> dict[str, Any]:
    selected_action_ids = []
    policy_input_sha256s = []
    categories = []
    while True:
        try:
            snapshot = environment.snapshot()
        except SimulatorAdapterError as exc:
            raise BridgeBlocked("stage2_snapshot_failed", str(exc)) from exc
        if snapshot.get("terminal") is True:
            break
        if len(selected_action_ids) >= STAGE2_MAX_DECISIONS_PER_EPISODE:
            raise BridgeBlocked(
                "stage2_decision_limit_exceeded",
                {"limit": STAGE2_MAX_DECISIONS_PER_EPISODE, "seed": seed},
            )
        if snapshot.get("state", {}).get("seed") != str(seed):
            raise BridgeBlocked("stage2_environment_seed_mismatch", seed)
        decision_index = snapshot.get("decision_count")
        if isinstance(decision_index, bool) or not isinstance(decision_index, int):
            raise BridgeBlocked("stage2_decision_index_invalid", decision_index)
        try:
            candidates = environment.legal_actions()
            evaluation = session.evaluate(
                snapshot=snapshot,
                candidates=candidates,
                decision_index=decision_index,
            )
            transition = environment.step(evaluation["action_id"])
        except SimulatorAdapterError as exc:
            raise BridgeBlocked("stage2_simulator_step_failed", str(exc)) from exc
        if transition.get("selected_action_id") != evaluation["action_id"]:
            raise BridgeBlocked("stage2_transition_action_mismatch")
        categories.append(evaluation["category"])
        selected_action_ids.append(evaluation["action_id"])
        policy_input_sha256s.append(
            sha256_bytes(
                canonical_json_bytes(
                    {
                        "candidates": evaluation["input_candidates_sha256"],
                        "snapshot": evaluation["input_snapshot_sha256"],
                    }
                )
            )
        )

    terminal_state = _mapping(snapshot.get("state"), "stage2 terminal state")
    terminal_floor = terminal_state.get("floor")
    if isinstance(terminal_floor, bool) or not isinstance(terminal_floor, int):
        raise BridgeBlocked("stage2_terminal_floor_invalid", terminal_floor)
    outcome = terminal_state.get("outcome")
    if outcome not in {"player_loss", "player_victory"}:
        raise BridgeBlocked("stage2_terminal_outcome_invalid", outcome)
    row = {
        "action_sequence_sha256": sha256_bytes(
            canonical_json_bytes(selected_action_ids)
        ),
        "categories": categories,
        "decision_count": len(selected_action_ids),
        "outcome": outcome,
        "policy_input_sha256s": policy_input_sha256s,
        "seed": seed,
        "selected_action_ids": selected_action_ids,
        "terminal_floor": terminal_floor,
    }
    row["trajectory_sha256"] = sha256_bytes(canonical_json_bytes(row))
    return row


def run_stage2_compatibility(
    *,
    registration: Mapping[str, Any],
    environment_factory: Callable[[int], Any],
    session_factory: Callable[[], Any],
    native_identity: Mapping[str, Any],
) -> dict[str, Any]:
    """Run exactly the registered reused-seed Current compatibility gate."""

    normalized_registration = validate_registration(copy.deepcopy(registration))
    if normalized_registration["schema_version"] != SUCCESSOR_INPUT_SCHEMA_VERSION:
        raise BridgeBlocked("stage2_successor_registration_required")
    validated_native_identity = validate_stage2_native_identity(
        normalized_registration, native_identity
    )
    rows = []
    for seed in normalized_registration["stage2"]["reused_seeds"]:
        replays = []
        for _ in range(STAGE2_REPLAY_COUNT):
            replays.append(
                _run_stage2_replay(
                    environment=environment_factory(seed),
                    session=session_factory(),
                    seed=seed,
                )
            )
        if canonical_json_bytes(replays[0]) != canonical_json_bytes(replays[1]):
            raise BridgeBlocked(
                "stage2_trajectory_nondeterministic",
                {
                    "first": replays[0]["trajectory_sha256"],
                    "second": replays[1]["trajectory_sha256"],
                    "seed": seed,
                },
            )
        rows.append({**replays[0], "replay_count": STAGE2_REPLAY_COUNT})
    return {
        "max_decisions_per_episode": STAGE2_MAX_DECISIONS_PER_EPISODE,
        "native_identity": validated_native_identity,
        "replay_count": STAGE2_REPLAY_COUNT,
        "rows": rows,
        "schema_version": STAGE2_RESULT_SCHEMA_VERSION,
        "seeds": list(normalized_registration["stage2"]["reused_seeds"]),
        "status": "passed",
    }


def classify_stage1(
    *,
    row_results: Sequence[Mapping[str, Any]],
    category_minimums: Mapping[str, int],
) -> dict[str, Any]:
    passed_counts = Counter(
        str(row.get("category"))
        for row in row_results
        if row.get("status") == "passed"
    )
    coverage = {
        category: passed_counts[category] >= int(minimum)
        for category, minimum in category_minimums.items()
    }
    all_rows_passed = bool(row_results) and all(
        row.get("status") == "passed" for row in row_results
    )
    passed = all_rows_passed and all(coverage.values())
    return {
        "authority": dict(ALL_FALSE_AUTHORITY),
        "category_coverage": coverage,
        "passed": passed,
        "stage2_authorized": passed,
        "verdict": (
            "frozen_bridge_structurally_compatible"
            if passed
            else "frozen_bridge_not_compatible"
        ),
    }


def _binding_actual(path: Path, display_path: str) -> dict[str, Any]:
    if not path.is_file():
        raise BridgeBlocked("bound_file_missing", display_path)
    return {
        "path": display_path,
        "sha256": sha256_file(path),
        "size_bytes": path.stat().st_size,
    }


def _verify_binding(
    *, repo_root: Path, binding: Mapping[str, Any], repository_relative: bool
) -> Path:
    path = (
        (repo_root / str(binding["path"])).resolve()
        if repository_relative
        else Path(str(binding["path"])).resolve()
    )
    if repository_relative:
        try:
            path.relative_to(repo_root)
        except ValueError as exc:
            raise BridgeBlocked("bound_file_escapes_repository", binding["path"]) from exc
    actual = _binding_actual(path, str(binding["path"]))
    if actual != dict(binding):
        raise BridgeBlocked(
            "bound_file_identity_mismatch",
            {"registered": dict(binding), "actual": actual},
        )
    return path


def hash_bound_files(repo_root: Path, source_files: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for relative in source_files:
        path = (repo_root / relative).resolve()
        try:
            canonical_relative = path.relative_to(repo_root).as_posix()
        except ValueError as exc:
            raise BridgeBlocked("source_file_escapes_repository", relative) from exc
        if not path.is_file():
            raise BridgeBlocked("source_file_missing", relative)
        relative_bytes = canonical_relative.encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative_bytes).to_bytes(4, "big"))
        digest.update(relative_bytes)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    return digest.hexdigest()


def _verify_sources_at_commit(
    repo_root: Path, commit: str, source_files: Sequence[str]
) -> None:
    for relative in source_files:
        try:
            completed = subprocess.run(
                ["git", "show", f"{commit}:{relative}"],
                cwd=repo_root,
                check=True,
                capture_output=True,
            )
        except (OSError, subprocess.CalledProcessError) as exc:
            raise BridgeBlocked("source_not_available_at_commit", relative) from exc
        if completed.stdout != (repo_root / relative).read_bytes():
            raise BridgeBlocked("source_differs_from_implementation_commit", relative)


def _json_path(value: Mapping[str, Any], path: str) -> object:
    current: object = value
    for part in path.split("."):
        if not isinstance(current, Mapping) or part not in current:
            raise BridgeBlocked("prior_seed_json_path_missing", path)
        current = current[part]
    return current


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(
            path.read_text(encoding="utf-8"), object_pairs_hook=_reject_duplicate_pairs
        )
    except BridgeBlocked:
        raise
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise BridgeBlocked("cannot_load_json", {"label": label, "error": str(exc)}) from exc
    return _mapping(value, label)


def validate_successor_evidence(
    registration: Mapping[str, Any], repo_root: Path
) -> dict[str, Any] | None:
    """Verify predecessor files and immutable registration equality for v2."""

    if registration["schema_version"] != SUCCESSOR_INPUT_SCHEMA_VERSION:
        return None
    identity = registration["identity"]
    predecessor_path = _verify_binding(
        repo_root=repo_root,
        binding=identity["predecessor_registration"],
        repository_relative=True,
    )
    manifest_path = _verify_binding(
        repo_root=repo_root,
        binding=identity["predecessor_manifest"],
        repository_relative=True,
    )
    predecessor = load_registration(predecessor_path)
    comparison = validate_successor_registration(registration, predecessor)

    expected_manifest_path = (
        PurePosixPath(predecessor["output"]["directory"])
        / "artifact_manifest.json"
    ).as_posix()
    actual_manifest_path = str(identity["predecessor_manifest"]["path"]).replace(
        "\\", "/"
    )
    if actual_manifest_path != expected_manifest_path:
        raise BridgeBlocked(
            "predecessor_manifest_path_mismatch",
            {"actual": actual_manifest_path, "expected": expected_manifest_path},
        )

    manifest = _load_json(manifest_path, "predecessor manifest")
    _require_keys(
        manifest,
        {
            "artifact_hashes",
            "authority",
            "registration_sha256",
            "schema_version",
            "stage2_executed",
            "verdict",
        },
        "predecessor manifest",
    )
    if manifest["schema_version"] != MANIFEST_SCHEMA_VERSION:
        raise BridgeBlocked("predecessor_manifest_schema_mismatch")
    if manifest["registration_sha256"] != sha256_file(predecessor_path):
        raise BridgeBlocked("predecessor_manifest_registration_mismatch")
    if manifest["authority"] != ALL_FALSE_AUTHORITY:
        raise BridgeBlocked("predecessor_manifest_authority_mismatch")
    artifact_hashes = _mapping(
        manifest["artifact_hashes"], "predecessor manifest.artifact_hashes"
    )
    if set(artifact_hashes) != set(CANONICAL_ARTIFACT_NAMES):
        raise BridgeBlocked("predecessor_manifest_artifact_names_mismatch")
    for name, digest in artifact_hashes.items():
        if not _is_hex(digest, 64):
            raise BridgeBlocked(
                "predecessor_manifest_artifact_hash_invalid", name
            )

    comparison["predecessor_manifest"] = dict(
        identity["predecessor_manifest"]
    )
    comparison["predecessor_registration"] = dict(
        identity["predecessor_registration"]
    )
    comparison["predecessor_verdict"] = manifest["verdict"]
    return comparison


def _validate_identity(
    registration: Mapping[str, Any], repo_root: Path
) -> tuple[Path, MetadataCatalog, dict[str, Any] | None]:
    identity = registration["identity"]
    successor_comparison = validate_successor_evidence(registration, repo_root)
    demonstrations_path = _verify_binding(
        repo_root=repo_root,
        binding=identity["frozen_demonstrations"],
        repository_relative=True,
    )
    metadata_path = _verify_binding(
        repo_root=repo_root,
        binding=identity["metadata"],
        repository_relative=False,
    )
    prior_path = _verify_binding(
        repo_root=repo_root,
        binding=identity["prior_seed_evidence"],
        repository_relative=True,
    )
    implementation = identity["implementation"]
    actual_source_hash = hash_bound_files(repo_root, implementation["source_files"])
    if actual_source_hash != implementation["source_sha256"]:
        raise BridgeBlocked("implementation_source_hash_mismatch")
    _verify_sources_at_commit(
        repo_root, implementation["commit"], implementation["source_files"]
    )
    if identity["runtime"]["python"] != sys.version.split()[0]:
        raise BridgeBlocked(
            "runtime_python_mismatch",
            {"registered": identity["runtime"]["python"], "actual": sys.version.split()[0]},
        )
    prior = _load_json(prior_path, "prior seed evidence")
    registered_prior_seeds = _json_path(
        prior, registration["stage2"]["prior_seed_json_path"]
    )
    if registered_prior_seeds != registration["stage2"]["reused_seeds"]:
        raise BridgeBlocked(
            "stage2_reused_seed_evidence_mismatch",
            {"evidence": registered_prior_seeds, "registered": registration["stage2"]["reused_seeds"]},
        )
    metadata = MetadataCatalog(metadata_path)
    return demonstrations_path, metadata, successor_comparison


def _selected_rows(
    demonstrations: Mapping[str, Any], selections: Sequence[Mapping[str, Any]]
) -> list[dict[str, Any]]:
    if demonstrations.get("schema_version") != DEMONSTRATION_ARTIFACT_SCHEMA_VERSION:
        raise BridgeBlocked("demonstration_artifact_schema_mismatch")
    datasets = _mapping(demonstrations.get("datasets"), "demonstrations.datasets")
    result = []
    for selection in selections:
        dataset = _mapping(datasets.get(selection["cohort"]), "selected dataset")
        rows = _sequence(dataset.get("rows"), "selected dataset rows")
        matches = [
            _mapping(row, "demonstration row")
            for row in rows
            if row.get("seed") == selection["seed"]
            and row.get("decision_index") == selection["decision_index"]
            and row.get("category") == selection["category"]
        ]
        if len(matches) != 1:
            raise BridgeBlocked("selected_row_match_count", {"selection": selection, "count": len(matches)})
        row = matches[0]
        if row.get("schema_version") != DEMONSTRATION_SCHEMA_VERSION:
            raise BridgeBlocked("demonstration_row_schema_mismatch")
        if sha256_bytes(canonical_json_bytes(row)) != selection["row_sha256"]:
            raise BridgeBlocked("selected_row_hash_mismatch", selection)
        if row.get("source_snapshot_sha256") != selection["source_snapshot_sha256"]:
            raise BridgeBlocked("selected_snapshot_registration_mismatch", selection)
        if sha256_bytes(canonical_json_bytes(row.get("source_snapshot"))) != row.get(
            "source_snapshot_sha256"
        ):
            raise BridgeBlocked("selected_snapshot_hash_mismatch", selection)
        if sha256_bytes(canonical_json_bytes(row.get("candidate_actions"))) != row.get(
            "candidate_actions_sha256"
        ):
            raise BridgeBlocked("selected_candidates_hash_mismatch", selection)
        result.append(row)
    return result


def _evaluate_stage1(
    *,
    registration: Mapping[str, Any],
    demonstrations: Mapping[str, Any],
    metadata: MetadataCatalog,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    rows = _selected_rows(demonstrations, registration["stage1"]["rows"])
    registered_provenance = canonical_json_bytes(
        registration["identity"]["adapter_provenance"]
    )
    row_results = []
    for row in rows:
        selection = {
            "category": row["category"],
            "cohort": row["cohort"],
            "decision_index": row["decision_index"],
            "seed": row["seed"],
        }
        replay_results = []
        for replay_index in range(registration["stage1"]["replay_count"]):
            try:
                if canonical_json_bytes(row["provenance"]) != registered_provenance:
                    raise BridgeBlocked("row_adapter_provenance_mismatch")
                session = CurrentPolicyBridgeSession(
                    metadata=metadata,
                    current_policy=registration["current_policy"],
                    event_semantics_identity=(
                        _registration_event_semantics_identity(registration)
                    ),
                    simulator_provenance=registration["identity"][
                        "adapter_provenance"
                    ],
                )
                evaluation = session.evaluate(
                    snapshot=row["source_snapshot"],
                    candidates=row["candidate_actions"],
                    decision_index=row["decision_index"],
                )
                replay_results.append(
                    {"replay_index": replay_index, "status": "passed", **evaluation}
                )
            except BridgeBlocked as exc:
                replay_results.append(
                    {
                        "detail": exc.detail,
                        "reason": exc.reason,
                        "replay_index": replay_index,
                        "status": "failed",
                    }
                )
        replay_signatures = [
            (entry["status"], entry.get("action_id"), entry.get("reason"))
            for entry in replay_results
        ]
        deterministic = len(set(replay_signatures)) == 1
        all_passed = all(entry["status"] == "passed" for entry in replay_results)
        status = "passed" if all_passed and deterministic else "failed"
        reason = None
        if not deterministic:
            reason = "nondeterministic_replay"
        elif not all_passed:
            reason = replay_results[0].get("reason")
        row_results.append(
            {
                **selection,
                "deterministic": deterministic,
                "reason": reason,
                "replays": replay_results,
                "schema_version": ROW_RESULT_SCHEMA_VERSION,
                "status": status,
            }
        )
    classification = classify_stage1(
        row_results=row_results,
        category_minimums=registration["stage1"]["category_minimums"],
    )
    return row_results, classification


def _report_markdown(
    *,
    classification: Mapping[str, Any],
    row_results: Sequence[Mapping[str, Any]],
    successor_comparison: Mapping[str, Any] | None = None,
    stage2_result: Mapping[str, Any] | None = None,
) -> str:
    lines = [
        "# Current Policy Simulator Bridge POC",
        "",
        f"Verdict: `{classification['verdict']}`.",
        "",
        "This is structural bridge evidence only. It does not establish policy quality, a baseline floor, reward validity, outcome support, promotion, or formal RL readiness.",
        "",
    ]
    if successor_comparison is not None:
        lines.extend(
            [
                "## Successor Integrity",
                "",
                f"Status: `{successor_comparison['status']}`.",
                "",
                f"Predecessor verdict: `{successor_comparison['predecessor_verdict']}`.",
                "",
                "Immutable paths: "
                + ", ".join(
                    f"`{path}`" for path in successor_comparison["immutable_paths"]
                )
                + ".",
                "",
            ]
        )
    lines.extend(
        [
            "## Frozen Rows",
            "",
            "| Category | Seed | Decision | Status | Result |",
            "| --- | ---: | ---: | --- | --- |",
        ]
    )
    for row in row_results:
        result = row.get("reason")
        if result is None:
            result = row["replays"][0].get("action_id", "passed")
        lines.append(
            f"| `{row['category']}` | {row['seed']} | {row['decision_index']} | `{row['status']}` | `{result}` |"
        )
    lines.extend(["", "## Stage 2", ""])
    if stage2_result is not None and stage2_result["status"] == "passed":
        lines.extend(
            [
                "The registered reused-seed compatibility check passed with two deterministic replays per seed.",
                "",
                "| Seed | Decisions | Floor | Outcome | Trajectory |",
                "| ---: | ---: | ---: | --- | --- |",
            ]
        )
        for row in stage2_result["rows"]:
            lines.append(
                f"| {row['seed']} | {row['decision_count']} | {row['terminal_floor']} | `{row['outcome']}` | `{row['trajectory_sha256']}` |"
            )
    elif stage2_result is not None:
        lines.append(
            "The registered reused-seed compatibility check failed closed with "
            f"`{stage2_result['reason']}`."
        )
    else:
        lines.append(
            "Stage 2 is authorized by Stage 1 but requires the registered bounded compatibility executor."
            if classification["stage2_authorized"]
            else "Stage 2 was not run because at least one frozen structural gate failed."
        )
    lines.extend(["", "## Authority", ""])
    for name, enabled in sorted(ALL_FALSE_AUTHORITY.items()):
        lines.append(f"- `{name}`: `{str(enabled).lower()}`")
    lines.extend(
        [
            "",
            "A separate OpenSpec change and untouched preregistered seeds are required before any baseline-floor study.",
            "",
        ]
    )
    return "\n".join(lines)


def build_artifacts(
    *,
    registration: Mapping[str, Any],
    registration_sha256: str,
    row_results: Sequence[Mapping[str, Any]],
    classification: Mapping[str, Any],
    successor_comparison: Mapping[str, Any] | None = None,
    stage2_result: Mapping[str, Any] | None = None,
) -> dict[str, bytes]:
    reason_counts = Counter(
        str(row["reason"]) for row in row_results if row.get("reason") is not None
    )
    configuration = {
        "registration": registration,
        "registration_sha256": registration_sha256,
        "schema_version": registration["schema_version"],
    }
    if successor_comparison is not None:
        configuration["successor_comparison"] = successor_comparison
    journal = {
        "steps": [
            "validated_registration_and_bound_sources",
            *(
                ["validated_predecessor_and_immutable_successor_fields"]
                if successor_comparison is not None
                else []
            ),
            "loaded_registered_frozen_rows",
            "replayed_each_row_with_fresh_current_session",
            "classified_stage1",
            (
                "executed_registered_stage2_compatibility"
                if stage2_result is not None
                else "stage2_authorized_not_executed"
                if classification["stage2_authorized"]
                else "stage2_not_authorized"
            ),
        ]
    }
    metrics = {
        "authority": dict(ALL_FALSE_AUTHORITY),
        "category_coverage": classification["category_coverage"],
        "passed_row_count": sum(row["status"] == "passed" for row in row_results),
        "reason_counts": dict(sorted(reason_counts.items())),
        "registration_sha256": registration_sha256,
        "row_count": len(row_results),
        "schema_version": (
            SUCCESSOR_METRICS_SCHEMA_VERSION
            if successor_comparison is not None
            else METRICS_SCHEMA_VERSION
        ),
        "stage1_passed": classification["passed"],
        "stage2": {
            "authorized": classification["stage2_authorized"],
            "executed": stage2_result is not None,
            "reason": (
                (
                    "completed"
                    if stage2_result["status"] == "passed"
                    else stage2_result["reason"]
                )
                if stage2_result is not None
                else "executor_not_entered_by_frozen_only_poc"
                if classification["stage2_authorized"]
                else "stage1_not_compatible"
            ),
        },
        "verdict": classification["verdict"],
    }
    if successor_comparison is not None:
        metrics["successor_comparison"] = successor_comparison
    if stage2_result is not None:
        metrics["stage2"]["result"] = stage2_result
    artifacts = {
        "configuration.json": canonical_json_bytes(configuration),
        "execution_journal.json": canonical_json_bytes(journal),
        "metrics.json": canonical_json_bytes(metrics),
        "report.md": _report_markdown(
            classification=classification,
            row_results=row_results,
            successor_comparison=successor_comparison,
            stage2_result=stage2_result,
        ).encode("utf-8"),
        "row_results.json": canonical_json_bytes(
            {
                "rows": list(row_results),
                "schema_version": "noncombat-current-policy-simulator-bridge-rows-v1",
            }
        ),
    }
    manifest = {
        "artifact_hashes": {
            name: sha256_bytes(data) for name, data in sorted(artifacts.items())
        },
        "authority": dict(ALL_FALSE_AUTHORITY),
        "registration_sha256": registration_sha256,
        "schema_version": (
            SUCCESSOR_MANIFEST_SCHEMA_VERSION
            if successor_comparison is not None
            else MANIFEST_SCHEMA_VERSION
        ),
        "stage2_executed": stage2_result is not None,
        "verdict": classification["verdict"],
    }
    if successor_comparison is not None:
        manifest["successor_comparison"] = successor_comparison
    if stage2_result is not None:
        manifest["stage2_result_sha256"] = sha256_bytes(
            canonical_json_bytes(stage2_result)
        )
    artifacts["artifact_manifest.json"] = canonical_json_bytes(manifest)
    return artifacts


def _assert_artifacts_match(
    output_dir: Path, artifacts: Mapping[str, bytes], reason: str
) -> None:
    actual_names = {
        path.name for path in output_dir.iterdir() if path.is_file()
    } if output_dir.is_dir() else set()
    if actual_names != set(artifacts):
        raise BridgeBlocked(
            reason,
            {"actual": sorted(actual_names), "expected": sorted(artifacts)},
        )
    for name, expected in artifacts.items():
        path = output_dir / name
        if path.read_bytes() != expected:
            raise BridgeBlocked(reason, name)


def _write_artifacts(output_dir: Path, artifacts: Mapping[str, bytes]) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for name, data in artifacts.items():
        temporary = output_dir / f".{name}.tmp"
        temporary.write_bytes(data)
        temporary.replace(output_dir / name)


def run_poc(
    *,
    registration_path: Path | str,
    repo_root: Path | str,
    recompute: bool = False,
    execute_stage2: bool = False,
    module_path: Path | str | None = None,
    simulator_repo: Path | str | None = None,
    dll_directories: Sequence[Path | str] = (),
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    input_path = Path(registration_path).resolve()
    registration = load_registration(input_path)
    registration_sha256 = sha256_file(input_path)
    demonstrations_path, metadata, successor_comparison = _validate_identity(
        registration, root
    )
    demonstrations = _load_json(demonstrations_path, "frozen demonstrations")
    row_results, classification = _evaluate_stage1(
        registration=registration,
        demonstrations=demonstrations,
        metadata=metadata,
    )
    stage1_artifacts = build_artifacts(
        registration=registration,
        registration_sha256=registration_sha256,
        row_results=row_results,
        classification=classification,
        successor_comparison=successor_comparison,
    )
    stage2_result = None
    if execute_stage2:
        if not classification["stage2_authorized"]:
            raise BridgeBlocked("stage2_not_authorized")
        if module_path is None or simulator_repo is None:
            raise BridgeBlocked("stage2_runtime_paths_required")
        try:
            native_module = load_native_module(
                module_path, dll_directories=dll_directories
            )
        except SimulatorAdapterError as exc:
            raise BridgeBlocked("stage2_native_module_load_failed", str(exc)) from exc
        actual_native_identity = collect_stage2_native_identity(
            module_path=module_path,
            simulator_repo=simulator_repo,
            native_module=native_module,
        )
        validate_stage2_native_identity(registration, actual_native_identity)
        provenance = registration["identity"]["adapter_provenance"]

        def environment_factory(seed: int) -> NativeSimulatorEnvironment:
            return NativeSimulatorEnvironment(
                native_module.Environment(seed, registration["current_policy"]["ascension"]),
                provenance,
            )

        def session_factory() -> CurrentPolicyBridgeSession:
            return CurrentPolicyBridgeSession(
                metadata=metadata,
                current_policy=registration["current_policy"],
                event_semantics_identity=(
                    _registration_event_semantics_identity(registration)
                ),
                simulator_provenance=provenance,
            )

        try:
            stage2_result = run_stage2_compatibility(
                registration=registration,
                environment_factory=environment_factory,
                session_factory=session_factory,
                native_identity=actual_native_identity,
            )
        except BridgeBlocked as exc:
            stage2_result = {
                "detail": exc.detail,
                "max_decisions_per_episode": STAGE2_MAX_DECISIONS_PER_EPISODE,
                "native_identity": actual_native_identity,
                "reason": exc.reason,
                "replay_count": STAGE2_REPLAY_COUNT,
                "schema_version": STAGE2_RESULT_SCHEMA_VERSION,
                "seeds": list(registration["stage2"]["reused_seeds"]),
                "status": "failed",
            }
    artifacts = build_artifacts(
        registration=registration,
        registration_sha256=registration_sha256,
        row_results=row_results,
        classification=classification,
        successor_comparison=successor_comparison,
        stage2_result=stage2_result,
    )
    output_dir = (root / registration["output"]["directory"]).resolve()
    try:
        output_dir.relative_to(root)
    except ValueError as exc:
        raise BridgeBlocked("output_directory_escapes_repository") from exc
    if recompute:
        _assert_artifacts_match(
            output_dir, artifacts, "artifact_recompute_mismatch"
        )
    else:
        if execute_stage2 and output_dir.exists() and any(output_dir.iterdir()):
            _assert_artifacts_match(
                output_dir,
                stage1_artifacts,
                "stage2_prepublication_artifact_mismatch",
            )
        elif output_dir.exists() and any(output_dir.iterdir()):
            raise BridgeBlocked("output_directory_not_empty", str(output_dir))
        _write_artifacts(output_dir, artifacts)
    return {
        "output_directory": str(output_dir),
        "stage2_authorized": classification["stage2_authorized"],
        "stage2_executed": stage2_result is not None,
        "stage2_status": (
            stage2_result["status"] if stage2_result is not None else "not_executed"
        ),
        "verdict": classification["verdict"],
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--recompute", action="store_true")
    parser.add_argument("--execute-stage2", action="store_true")
    parser.add_argument("--module")
    parser.add_argument("--simulator-repo")
    parser.add_argument("--dll-directory", action="append", default=[])
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = run_poc(
            registration_path=args.registration,
            repo_root=args.repo_root,
            recompute=args.recompute,
            execute_stage2=args.execute_stage2,
            module_path=args.module,
            simulator_repo=args.simulator_repo,
            dll_directories=args.dll_directory,
        )
    except BridgeBlocked as exc:
        print(json.dumps({"detail": exc.detail, "reason": exc.reason}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
