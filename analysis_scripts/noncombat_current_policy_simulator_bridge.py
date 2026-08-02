"""Validate an offline bridge from sts_lightspeed snapshots to Current policy."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import subprocess
import sys
from collections import Counter
from collections.abc import Mapping, Sequence
from contextlib import ExitStack, contextmanager
from pathlib import Path, PurePosixPath
from typing import Any
from unittest.mock import patch

import spirecomm.ai.agent as agent_module
from analysis_scripts.noncombat_simulator_adapter import (
    TARGET_CATEGORIES,
    canonical_json_bytes,
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
ROW_RESULT_SCHEMA_VERSION = "noncombat-current-policy-simulator-bridge-row-v1"
METRICS_SCHEMA_VERSION = "noncombat-current-policy-simulator-bridge-metrics-v1"
MANIFEST_SCHEMA_VERSION = "noncombat-current-policy-simulator-bridge-manifest-v1"
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
REGISTERED_SOURCE_FILES = (
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
ALL_FALSE_AUTHORITY = {
    "baseline_floor_authorized": False,
    "formal_rl_readiness_authorized": False,
    "fresh_evidence_authorized": False,
    "gameplay_authorized": False,
    "promotion_authorized": False,
    "reward_authorized": False,
    "training_authorized": False,
}


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
    """Validate the one accepted bridge POC registration without defaults."""

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
    if registration["schema_version"] != INPUT_SCHEMA_VERSION:
        raise BridgeBlocked("registration_schema_mismatch")
    registration["current_policy"] = _validated_current_policy(
        registration["current_policy"]
    )

    identity = _mapping(registration["identity"], "identity")
    _require_keys(
        identity,
        {
            "adapter_provenance",
            "frozen_demonstrations",
            "implementation",
            "metadata",
            "prior_seed_evidence",
            "runtime",
        },
        "identity",
    )
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

    implementation = _mapping(identity["implementation"], "identity.implementation")
    _require_keys(
        implementation,
        {"commit", "source_files", "source_sha256"},
        "identity.implementation",
    )
    if not _is_hex(implementation["commit"], 40):
        raise BridgeBlocked("invalid_implementation_commit")
    if implementation["source_files"] != list(REGISTERED_SOURCE_FILES):
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
        if name.casefold() not in self.relics:
            raise BridgeBlocked("relic_metadata_missing", name)
        counter = source.get("data", 0)
        price = source.get("price", 0)
        if isinstance(counter, bool) or not isinstance(counter, int):
            raise BridgeBlocked("relic_counter_invalid", name)
        if isinstance(price, bool) or not isinstance(price, int) or price < 0:
            raise BridgeBlocked("relic_price_invalid", name)
        relic = Relic(relic_id, name, counter=counter, price=price)
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
            if name.casefold() not in self.potions:
                raise BridgeBlocked("potion_metadata_missing", name)
            price = source.get("price", 0)
            if isinstance(price, bool) or not isinstance(price, int) or price < 0:
                raise BridgeBlocked("potion_price_invalid", name)
            potion = Potion(potion_id, name, False, False, False, price=price)
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


def _hydrate_event_screen(
    state: Mapping[str, Any], candidates: Sequence[Mapping[str, Any]]
) -> tuple[EventScreen, list[EventOption]]:
    context = _mapping(state.get("decision_context"), "event decision_context")
    event_id = context.get("event_id")
    event_name = context.get("event_name")
    if not isinstance(event_id, str) or not isinstance(event_name, str):
        raise BridgeBlocked("event_identity_missing")
    semantics = context.get("option_semantics")
    if not isinstance(semantics, list):
        raise BridgeBlocked("missing_event_option_semantics", event_id)
    candidate_indices = sorted(
        candidate["raw"].get("idx1") for candidate in candidates
    )
    options = []
    semantic_indices = []
    for index, raw in enumerate(semantics):
        option = _mapping(raw, f"event option_semantics[{index}]")
        _require_keys(option, {"choice_index", "label", "text"}, f"event option {index}")
        choice_index = option["choice_index"]
        label = option["label"]
        text = option["text"]
        if (
            isinstance(choice_index, bool)
            or not isinstance(choice_index, int)
            or not isinstance(label, str)
            or not label
            or not isinstance(text, str)
            or not text
        ):
            raise BridgeBlocked("event_option_semantics_invalid", index)
        semantic_indices.append(choice_index)
        options.append(EventOption(text, label, False, choice_index))
    if semantic_indices != candidate_indices:
        raise BridgeBlocked(
            "event_option_semantics_candidate_mismatch",
            {"semantics": semantic_indices, "candidates": candidate_indices},
        )
    screen = EventScreen(event_name, event_id, "")
    screen.options = options
    return screen, options


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
        purge_cost = _nonnegative_int(context.get("remove_cost"), "shop remove_cost")
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
        if not event_semantics_validated:
            raise BridgeBlocked("missing_event_option_semantics")
        if not isinstance(action, ChooseAction) or action.name is not None:
            raise BridgeBlocked("unsupported_current_action", type(action).__name__)
        return _unique_match(
            normalized,
            lambda candidate: candidate["kind"] == "event_option"
            and candidate["raw"].get("idx1") == action.choice_index,
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
        require_global_metadata_match: bool = True,
    ):
        self.metadata = metadata
        self.current_policy = _validated_current_policy(current_policy)
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
        game = hydrate_game(snapshot, candidates, self.metadata)
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
        action_id = map_current_action(
            category=category,
            action=action,
            candidates=candidates,
            event_semantics_validated=(category == "event"),
        )
        if canonical_json_bytes(snapshot) != before_snapshot:
            raise BridgeBlocked("source_snapshot_mutated_during_evaluation")
        if canonical_json_bytes(candidates) != before_candidates:
            raise BridgeBlocked("source_candidates_mutated_during_evaluation")
        self._last_decision_index = decision_index
        return {
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


def _validate_identity(
    registration: Mapping[str, Any], repo_root: Path
) -> tuple[Path, MetadataCatalog]:
    identity = registration["identity"]
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
    return demonstrations_path, metadata


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
    *, classification: Mapping[str, Any], row_results: Sequence[Mapping[str, Any]]
) -> str:
    lines = [
        "# Current Policy Simulator Bridge POC",
        "",
        f"Verdict: `{classification['verdict']}`.",
        "",
        "This is structural bridge evidence only. It does not establish policy quality, a baseline floor, reward validity, outcome support, promotion, or formal RL readiness.",
        "",
        "## Frozen Rows",
        "",
        "| Category | Seed | Decision | Status | Result |",
        "| --- | ---: | ---: | --- | --- |",
    ]
    for row in row_results:
        result = row.get("reason")
        if result is None:
            result = row["replays"][0].get("action_id", "passed")
        lines.append(
            f"| `{row['category']}` | {row['seed']} | {row['decision_index']} | `{row['status']}` | `{result}` |"
        )
    lines.extend(
        [
            "",
            "## Stage 2",
            "",
            (
                "Stage 2 is authorized by Stage 1 but requires the registered bounded compatibility executor."
                if classification["stage2_authorized"]
                else "Stage 2 was not run because at least one frozen structural gate failed."
            ),
            "",
            "## Authority",
            "",
        ]
    )
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
) -> dict[str, bytes]:
    reason_counts = Counter(
        str(row["reason"]) for row in row_results if row.get("reason") is not None
    )
    configuration = {
        "registration": registration,
        "registration_sha256": registration_sha256,
        "schema_version": INPUT_SCHEMA_VERSION,
    }
    journal = {
        "steps": [
            "validated_registration_and_bound_sources",
            "loaded_registered_frozen_rows",
            "replayed_each_row_with_fresh_current_session",
            "classified_stage1",
            (
                "stage2_authorized_not_executed"
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
        "schema_version": METRICS_SCHEMA_VERSION,
        "stage1_passed": classification["passed"],
        "stage2": {
            "authorized": classification["stage2_authorized"],
            "executed": False,
            "reason": (
                "executor_not_entered_by_frozen_only_poc"
                if classification["stage2_authorized"]
                else "stage1_not_compatible"
            ),
        },
        "verdict": classification["verdict"],
    }
    artifacts = {
        "configuration.json": canonical_json_bytes(configuration),
        "execution_journal.json": canonical_json_bytes(journal),
        "metrics.json": canonical_json_bytes(metrics),
        "report.md": _report_markdown(
            classification=classification, row_results=row_results
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
        "schema_version": MANIFEST_SCHEMA_VERSION,
        "stage2_executed": False,
        "verdict": classification["verdict"],
    }
    artifacts["artifact_manifest.json"] = canonical_json_bytes(manifest)
    return artifacts


def run_poc(
    *, registration_path: Path | str, repo_root: Path | str, recompute: bool = False
) -> dict[str, Any]:
    root = Path(repo_root).resolve()
    input_path = Path(registration_path).resolve()
    registration = load_registration(input_path)
    registration_sha256 = sha256_file(input_path)
    demonstrations_path, metadata = _validate_identity(registration, root)
    demonstrations = _load_json(demonstrations_path, "frozen demonstrations")
    row_results, classification = _evaluate_stage1(
        registration=registration,
        demonstrations=demonstrations,
        metadata=metadata,
    )
    artifacts = build_artifacts(
        registration=registration,
        registration_sha256=registration_sha256,
        row_results=row_results,
        classification=classification,
    )
    output_dir = (root / registration["output"]["directory"]).resolve()
    try:
        output_dir.relative_to(root)
    except ValueError as exc:
        raise BridgeBlocked("output_directory_escapes_repository") from exc
    if recompute:
        for name, expected in artifacts.items():
            path = output_dir / name
            if not path.is_file() or path.read_bytes() != expected:
                raise BridgeBlocked("artifact_recompute_mismatch", name)
    else:
        if output_dir.exists() and any(output_dir.iterdir()):
            raise BridgeBlocked("output_directory_not_empty", str(output_dir))
        output_dir.mkdir(parents=True, exist_ok=True)
        for name, data in artifacts.items():
            (output_dir / name).write_bytes(data)
    return {
        "output_directory": str(output_dir),
        "stage2_authorized": classification["stage2_authorized"],
        "stage2_executed": False,
        "verdict": classification["verdict"],
    }


def _parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registration", required=True)
    parser.add_argument("--repo-root", default=str(Path(__file__).resolve().parents[1]))
    parser.add_argument("--recompute", action="store_true")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        result = run_poc(
            registration_path=args.registration,
            repo_root=args.repo_root,
            recompute=args.recompute,
        )
    except BridgeBlocked as exc:
        print(json.dumps({"detail": exc.detail, "reason": exc.reason}, sort_keys=True))
        return 2
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
