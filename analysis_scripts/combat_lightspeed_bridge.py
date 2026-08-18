"""Offline mapping from sts_lightspeed combat states to the RL v2 contract."""

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

import numpy as np

from analysis_scripts.noncombat_simulator_adapter import (
    hash_compiled_simulator_sources,
    sha256_file,
)
from spirecomm.ai.rl.v2.id_mapping import IdMapper
from spirecomm.ai.rl.v2.types import EncodedStateV2


ADAPTER_API_VERSION = "sts-lightspeed-combat-adapter-v3"
STATE_SCHEMA_VERSION = "sts-lightspeed-combat-state-v3"
SOURCE_TYPE = "sts_lightspeed_combat_simulation"
BASELINE_POLICY = "native_simple_agent_v1"
MODULE_NAME = "sts_lightspeed_combat_adapter"
ACTION_DIM = 133
TARGET_SLOTS = 6
POTION_OFFSET = 60
END_TURN_ACTION = 90
CONTINUOUS_DIM = 328
CARD_SLOTS = 10
POTION_SLOTS = 5
RELIC_SLOTS = 40
MONSTER_SLOTS = 5
MAX_CARD_SELECT_SETTLEMENTS = 8
MAX_BATTLE_INDEX = 63

POTION_ID_ALIASES = {
    "BlessingOfTheForge": "Blessing of the Forge",
    "ElixirPotion": "Elixir",
    "FairyPotion": "Fairy in a Bottle",
    "GamblersBrew": "Gambler's Brew",
}
RELIC_ID_ALIASES = {
    "Bird Faced Urn": "Bird-Faced Urn",
    "CaptainsWheel": "Captain's Wheel",
    "Self Forming Clay": "Self-Forming Clay",
    "Cables": "Gold-Plated Cables",
    "NeowsBlessing": "Neow's Lament",
    "SlaversCollar": "Slaver's Collar",
    "DollysMirror": "Dolly's Mirror",
    "Nloth's Gift": "N'loth's Gift",
    "NlothsMask": "N'loth's Hungry Face",
}

KEYWORDS = (
    "Strength",
    "Dexterity",
    "Vulnerable",
    "Weak",
    "Frail",
    "Thorns",
    "Artifact",
    "Intangible",
    "Poison",
    "Regen",
    "Ritual",
    "Vigor",
    "Mantra",
    "Confused",
    "PlatedArmor",
    "Metallicize",
)
CARD_TAGS = ("AOE", "Draw", "Energy", "Exhaust", "Ethereal", "Retain", "Innate")
INTENT_ORDER = (
    "ATTACK",
    "ATTACK_BUFF",
    "ATTACK_DEBUFF",
    "ATTACK_DEFEND",
    "BUFF",
    "DEBUFF",
    "DEFEND",
    "DEFEND_BUFF",
    "DEFEND_DEBUFF",
)
_DLL_DIRECTORY_HANDLES: list[Any] = []


class CombatBridgeError(RuntimeError):
    """A native combat state cannot satisfy the explicit bridge contract."""

    def __init__(self, reason: str, detail: object | None = None):
        self.reason = reason
        self.detail = detail
        message = reason if detail is None else f"{reason}: {detail}"
        super().__init__(message)


@dataclass(frozen=True)
class MappedCombatState:
    state: EncodedStateV2
    action_mask: np.ndarray


def canonical_json_bytes(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise CombatBridgeError("invalid_mapping", label)
    return dict(value)


def _sequence(value: object, label: str) -> list[Any]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise CombatBridgeError("invalid_sequence", label)
    return list(value)


def _integer(value: object, label: str) -> int:
    if isinstance(value, bool):
        raise CombatBridgeError("invalid_integer", label)
    try:
        result = int(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CombatBridgeError("invalid_integer", label) from exc
    if str(result) != str(value) and not isinstance(value, int):
        try:
            if float(value) != result:
                raise CombatBridgeError("invalid_integer", label)
        except (TypeError, ValueError, OverflowError) as exc:
            raise CombatBridgeError("invalid_integer", label) from exc
    return result


def _number(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise CombatBridgeError("invalid_number", label)
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise CombatBridgeError("invalid_number", label) from exc
    if not np.isfinite(result):
        raise CombatBridgeError("invalid_number", label)
    return result


def _boolean(value: object, label: str) -> bool:
    if not isinstance(value, bool):
        raise CombatBridgeError("invalid_boolean", label)
    return value


def _ratio(numerator: object, denominator: object, default: float = 1.0) -> float:
    value = _number(numerator, "ratio numerator")
    maximum = _number(denominator, "ratio denominator")
    if maximum <= 0:
        return default
    return min(max(value, 0.0), maximum) / maximum


def _power_features(value: object, label: str) -> list[float]:
    powers = _mapping(value, label)
    missing = [name for name in KEYWORDS if name not in powers]
    if missing:
        raise CombatBridgeError("missing_power_identity", {"label": label, "missing": missing})
    result = []
    for name in KEYWORDS:
        amount = _number(powers[name], f"{label}.{name}")
        if name in ("Strength", "Dexterity"):
            result.append(float(np.tanh(amount / 10.0)))
        else:
            result.append(min(max(amount, 0.0), 20.0) / 20.0)
    return result


def _strict_card_id(id_mapper: IdMapper, name: object) -> int:
    if not isinstance(name, str) or not name:
        raise CombatBridgeError("invalid_card_identity", name)
    result = id_mapper.card_id(name)
    if result <= 0:
        raise CombatBridgeError("unknown_card_identity", name)
    return result


def _strict_potion_id(id_mapper: IdMapper, *identities: object) -> int:
    candidates = [value for value in identities if isinstance(value, str) and value]
    if not candidates:
        raise CombatBridgeError("invalid_potion_identity", identities)
    for value in candidates:
        result = id_mapper.potion_id(POTION_ID_ALIASES.get(value, value))
        if result > 0:
            return result
    raise CombatBridgeError("unknown_potion_identity", candidates[0])


def _strict_relic_id(id_mapper: IdMapper, *identities: object) -> int:
    candidates = [value for value in identities if isinstance(value, str) and value]
    if not candidates:
        raise CombatBridgeError("invalid_relic_identity", identities)
    for value in candidates:
        result = id_mapper.relic_id(RELIC_ID_ALIASES.get(value, value))
        if result > 0:
            return result
    raise CombatBridgeError("unknown_relic_identity", candidates[0])


def validate_card_select_settlement(
    value: object,
    *,
    label: str = "card_select_settlement",
) -> dict[str, Any]:
    settlement = _mapping(value, label)
    count = _integer(settlement.get("count"), f"{label}.count")
    if not 0 <= count <= MAX_CARD_SELECT_SETTLEMENTS:
        raise CombatBridgeError("invalid_card_select_settlement_count", count)
    tasks = _sequence(settlement.get("tasks"), f"{label}.tasks")
    if len(tasks) != count:
        raise CombatBridgeError(
            "card_select_settlement_count_mismatch",
            {"count": count, "task_count": len(tasks)},
        )
    for index, task in enumerate(tasks):
        if not isinstance(task, str) or not task:
            raise CombatBridgeError(
                "invalid_card_select_settlement_task",
                {"index": index, "task": task},
            )
    return {"count": count, "tasks": list(tasks)}


def validate_progression(
    value: object,
    *,
    state: Mapping[str, Any] | None = None,
    label: str = "progression",
) -> dict[str, Any]:
    progression = _mapping(value, label)
    if progression.get("baseline_policy") != BASELINE_POLICY:
        raise CombatBridgeError(
            "progression_baseline_policy_mismatch",
            progression.get("baseline_policy"),
        )
    requested = _integer(
        progression.get("requested_battle_index"),
        f"{label}.requested_battle_index",
    )
    reached = _integer(
        progression.get("reached_battle_index"),
        f"{label}.reached_battle_index",
    )
    if requested != reached:
        raise CombatBridgeError(
            "progression_battle_index_mismatch",
            {"requested": requested, "reached": reached},
        )
    if not 0 <= requested <= MAX_BATTLE_INDEX:
        raise CombatBridgeError("invalid_progression_battle_index", requested)
    result = {
        "act": _integer(progression.get("act"), f"{label}.act"),
        "baseline_policy": BASELINE_POLICY,
        "deck_size": _integer(progression.get("deck_size"), f"{label}.deck_size"),
        "encounter": progression.get("encounter"),
        "floor": _integer(progression.get("floor"), f"{label}.floor"),
        "player_current_hp": _integer(
            progression.get("player_current_hp"), f"{label}.player_current_hp"
        ),
        "player_max_hp": _integer(
            progression.get("player_max_hp"), f"{label}.player_max_hp"
        ),
        "reached_battle_index": reached,
        "relic_count": _integer(
            progression.get("relic_count"), f"{label}.relic_count"
        ),
        "requested_battle_index": requested,
    }
    if (
        not 1 <= result["act"] <= 4
        or result["deck_size"] <= 0
        or not isinstance(result["encounter"], str)
        or not result["encounter"]
        or result["floor"] <= 0
        or result["player_max_hp"] <= 0
        or result["relic_count"] < 0
    ):
        raise CombatBridgeError("invalid_progression_metadata", result)
    if state is not None:
        player = _mapping(state.get("player"), "snapshot.state.player")
        expected = {
            "act": _integer(state.get("act"), "snapshot.state.act"),
            "deck_size": _integer(state.get("deck_size"), "snapshot.state.deck_size"),
            "encounter": state.get("encounter"),
            "floor": _integer(state.get("floor"), "snapshot.state.floor"),
            "player_current_hp": _integer(
                player.get("current_hp"), "snapshot.state.player.current_hp"
            ),
            "player_max_hp": _integer(
                player.get("max_hp"), "snapshot.state.player.max_hp"
            ),
            "reached_battle_index": _integer(
                state.get("battle_index"), "snapshot.state.battle_index"
            ),
            "relic_count": _integer(
                state.get("relic_count"), "snapshot.state.relic_count"
            ),
        }
        actual = {key: result[key] for key in expected}
        if actual != expected:
            raise CombatBridgeError(
                "progression_state_mismatch",
                {"progression": actual, "state": expected},
            )
    return result


def validate_snapshot(value: object) -> dict[str, Any]:
    snapshot = _mapping(value, "snapshot")
    expected = {
        "adapter_api_version": ADAPTER_API_VERSION,
        "schema_version": STATE_SCHEMA_VERSION,
        "source_type": SOURCE_TYPE,
        "rl_action_dim": ACTION_DIM,
    }
    for key, wanted in expected.items():
        if snapshot.get(key) != wanted:
            raise CombatBridgeError("snapshot_identity_mismatch", {"field": key, "actual": snapshot.get(key)})
    validate_card_select_settlement(snapshot.get("card_select_settlement"))
    if not _boolean(snapshot.get("supported"), "snapshot.supported"):
        raise CombatBridgeError("unsupported_native_state", snapshot.get("unsupported_reason"))
    if _boolean(snapshot.get("terminal"), "snapshot.terminal"):
        raise CombatBridgeError("terminal_native_state")
    state = _mapping(snapshot.get("state"), "snapshot.state")
    validate_progression(snapshot.get("progression"), state=state)
    if state.get("input_state") != "PLAYER_NORMAL":
        raise CombatBridgeError("unsupported_input_state", state.get("input_state"))
    return snapshot


def validate_actions(value: object, *, state: Mapping[str, Any]) -> list[dict[str, Any]]:
    actions = [_mapping(item, f"actions[{index}]") for index, item in enumerate(_sequence(value, "actions"))]
    seen_ids: set[str] = set()
    seen_indices: set[int] = set()
    hand_count = len(_sequence(state.get("hand"), "state.hand"))
    potion_count = len(_sequence(state.get("potions"), "state.potions"))
    monster_count = len(
        [
            monster
            for monster in _sequence(state.get("monsters"), "state.monsters")
            if _mapping(monster, "monster").get("targetable") is True
        ]
    )
    for index, action in enumerate(actions):
        action_id = action.get("action_id")
        if not isinstance(action_id, str) or not action_id or action_id in seen_ids:
            raise CombatBridgeError("invalid_or_duplicate_action_id", action_id)
        seen_ids.add(action_id)
        if action.get("available") is not True:
            raise CombatBridgeError("unavailable_native_action", action_id)
        kind = action.get("kind")
        source_slot = _integer(action.get("source_slot"), f"actions[{index}].source_slot")
        target_slot = _integer(action.get("target_slot"), f"actions[{index}].target_slot")
        actual = _integer(action.get("rl_action_index"), f"actions[{index}].rl_action_index")
        if kind == "play_card":
            if not 0 <= source_slot < min(hand_count, CARD_SLOTS):
                raise CombatBridgeError("invalid_card_action_slot", action_id)
            if not 0 <= target_slot <= min(monster_count, MONSTER_SLOTS):
                raise CombatBridgeError("invalid_card_target_slot", action_id)
            expected = source_slot * TARGET_SLOTS + target_slot
        elif kind == "use_potion":
            if not 0 <= source_slot < min(potion_count, POTION_SLOTS):
                raise CombatBridgeError("invalid_potion_action_slot", action_id)
            if not 0 <= target_slot <= min(monster_count, MONSTER_SLOTS):
                raise CombatBridgeError("invalid_potion_target_slot", action_id)
            expected = POTION_OFFSET + source_slot * TARGET_SLOTS + target_slot
        elif kind == "end_turn":
            if source_slot != -1 or target_slot != 0:
                raise CombatBridgeError("invalid_end_turn_shape", action_id)
            expected = END_TURN_ACTION
        else:
            raise CombatBridgeError("unsupported_action_kind", kind)
        if actual != expected:
            raise CombatBridgeError(
                "rl_action_correspondence_mismatch",
                {"action_id": action_id, "actual": actual, "expected": expected},
            )
        if actual in seen_indices:
            raise CombatBridgeError("duplicate_rl_action_index", actual)
        seen_indices.add(actual)
    if END_TURN_ACTION not in seen_indices:
        raise CombatBridgeError("end_turn_missing")
    return actions


def encode_rl_v2(
    snapshot_value: object,
    actions_value: object,
    *,
    id_mapper: IdMapper,
) -> MappedCombatState:
    snapshot = validate_snapshot(snapshot_value)
    state = _mapping(snapshot["state"], "snapshot.state")
    actions = validate_actions(actions_value, state=state)

    player = _mapping(state.get("player"), "state.player")
    if player.get("character") != "IRONCLAD":
        raise CombatBridgeError("unsupported_character", player.get("character"))
    hand = [_mapping(item, f"state.hand[{index}]") for index, item in enumerate(_sequence(state.get("hand"), "state.hand"))]
    if len(hand) > CARD_SLOTS:
        raise CombatBridgeError("hand_slot_overflow", len(hand))
    piles = _mapping(state.get("piles"), "state.piles")

    continuous: list[float] = [
        _ratio(player.get("current_hp"), player.get("max_hp")),
        min(max(_number(player.get("energy"), "player.energy"), 0.0), 5.0) / 5.0,
        min(max(_number(player.get("block"), "player.block"), 0.0), 100.0) / 100.0,
        min(max(_number(state.get("floor"), "state.floor"), 0.0), 50.0) / 50.0,
        *_power_features(player.get("powers"), "player.powers"),
        min(max(_number(piles.get("draw"), "piles.draw"), 0.0), 100.0) / 100.0,
        min(max(_number(piles.get("discard"), "piles.discard"), 0.0), 100.0) / 100.0,
        min(max(_number(piles.get("exhaust"), "piles.exhaust"), 0.0), 100.0) / 100.0,
        min(len(hand), 100) / 100.0,
        1.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
        0.0,
    ]

    monsters = [
        _mapping(item, f"state.monsters[{index}]")
        for index, item in enumerate(_sequence(state.get("monsters"), "state.monsters"))
        if _mapping(item, f"state.monsters[{index}]").get("targetable") is True
    ]
    if len(monsters) > MONSTER_SLOTS:
        raise CombatBridgeError("monster_slot_overflow", len(monsters))
    for slot in range(MONSTER_SLOTS):
        if slot >= len(monsters):
            continuous.extend([0.0] * 30)
            continue
        monster = monsters[slot]
        intent = monster.get("intent")
        if intent not in (*INTENT_ORDER, "UNKNOWN"):
            raise CombatBridgeError("unknown_intent_identity", intent)
        intent_features = [1.0 if intent == name else 0.0 for name in INTENT_ORDER]
        continuous.extend(
            [
                1.0,
                _ratio(monster.get("current_hp"), monster.get("max_hp")),
                min(max(_number(monster.get("block"), "monster.block"), 0.0), 100.0) / 100.0,
                *intent_features,
                float(np.tanh(_number(monster.get("move_adjusted_damage"), "monster.damage") / 50.0)),
                min(max(_number(monster.get("move_hits"), "monster.hits"), 0.0), 10.0) / 10.0,
                *_power_features(monster.get("powers"), "monster.powers"),
            ]
        )

    card_ids = np.zeros(CARD_SLOTS, dtype=np.int64)
    for slot in range(CARD_SLOTS):
        if slot >= len(hand):
            continuous.extend([0.0] * 14)
            continue
        card = hand[slot]
        if _integer(card.get("slot"), f"hand[{slot}].slot") != slot:
            raise CombatBridgeError("noncontiguous_card_slot", slot)
        card_name = card.get("name")
        card_ids[slot] = _strict_card_id(id_mapper, card_name)
        cost = _number(card.get("cost_for_turn"), f"hand[{slot}].cost_for_turn")
        card_type = card.get("card_type")
        if card_type not in ("ATTACK", "SKILL", "POWER", "STATUS", "CURSE"):
            raise CombatBridgeError("unknown_card_type", card_type)
        type_features = [
            1.0 if card_type == "ATTACK" else 0.0,
            1.0 if card_type == "SKILL" else 0.0,
            1.0 if card_type == "POWER" else 0.0,
            1.0 if card_type in ("STATUS", "CURSE") else 0.0,
        ]
        tags = set(id_mapper.card_tag_list(card_name))
        continuous.extend(
            [
                1.0 if _boolean(card.get("upgraded"), f"hand[{slot}].upgraded") else 0.0,
                1.0 if cost < 0 else min(cost, 5.0) / 5.0,
                1.0 if _boolean(card.get("playable"), f"hand[{slot}].playable") else 0.0,
                *type_features,
                *(1.0 if tag in tags else 0.0 for tag in CARD_TAGS),
            ]
        )

    continuous.extend([1.0, 0.0, 0.0, 0.0, 0.0])
    continuous_array = np.asarray(continuous, dtype=np.float32)
    if continuous_array.shape != (CONTINUOUS_DIM,):
        raise CombatBridgeError("continuous_shape_mismatch", continuous_array.shape)

    potion_ids = np.zeros(POTION_SLOTS, dtype=np.int64)
    for index, raw in enumerate(_sequence(state.get("potions"), "state.potions")):
        potion = _mapping(raw, f"state.potions[{index}]")
        slot = _integer(potion.get("slot"), f"potions[{index}].slot")
        if not 0 <= slot < POTION_SLOTS:
            raise CombatBridgeError("potion_slot_overflow", slot)
        if not _boolean(potion.get("empty"), f"potions[{index}].empty"):
            potion_ids[slot] = _strict_potion_id(
                id_mapper,
                potion.get("id"),
                potion.get("name"),
            )

    relic_ids = np.zeros(RELIC_SLOTS, dtype=np.int64)
    relics = _sequence(state.get("relics"), "state.relics")
    if len(relics) > RELIC_SLOTS:
        raise CombatBridgeError("relic_slot_overflow", len(relics))
    for index, raw in enumerate(relics):
        relic = _mapping(raw, f"state.relics[{index}]")
        slot = _integer(relic.get("slot"), f"relics[{index}].slot")
        if slot != index:
            raise CombatBridgeError("noncontiguous_relic_slot", slot)
        relic_ids[slot] = _strict_relic_id(
            id_mapper,
            relic.get("id"),
            relic.get("name"),
        )

    action_mask = np.zeros(ACTION_DIM, dtype=bool)
    for action in actions:
        action_mask[_integer(action["rl_action_index"], "action.rl_action_index")] = True
    return MappedCombatState(
        state=EncodedStateV2(
            continuous=continuous_array,
            card_ids=card_ids,
            potion_ids=potion_ids,
            relic_ids=relic_ids,
        ),
        action_mask=action_mask,
    )


def load_native_module(
    module_path: Path | str,
    *,
    dll_directories: Iterable[Path | str] = (),
) -> ModuleType:
    module_file = Path(module_path).resolve()
    if not module_file.is_file():
        raise CombatBridgeError("native_module_missing", module_file)
    if hasattr(os, "add_dll_directory"):
        for directory in dll_directories:
            _DLL_DIRECTORY_HANDLES.append(os.add_dll_directory(str(Path(directory).resolve())))
    existing = sys.modules.get(MODULE_NAME)
    if existing is not None:
        if Path(getattr(existing, "__file__", "")).resolve() != module_file:
            raise CombatBridgeError("native_module_path_conflict", existing.__file__)
        module = existing
    else:
        spec = importlib.util.spec_from_file_location(MODULE_NAME, module_file)
        if spec is None or spec.loader is None:
            raise CombatBridgeError("native_module_spec_failed", module_file)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sys.modules[MODULE_NAME] = module
    if module.adapter_api_version() != ADAPTER_API_VERSION:
        raise CombatBridgeError("native_module_api_mismatch", module.adapter_api_version())
    return module


class NativeCombatEnvironment:
    def __init__(self, native: object):
        self.native = native

    @classmethod
    def reset(
        cls,
        module: ModuleType,
        seed: int,
        ascension: int = 0,
        battle_index: int = 0,
    ) -> "NativeCombatEnvironment":
        return cls(module.Environment(seed, ascension, battle_index))

    def clone(self) -> "NativeCombatEnvironment":
        return type(self)(self.native.clone())

    def snapshot(self) -> dict[str, Any]:
        return _mapping(json.loads(self.native.snapshot_json()), "native snapshot")

    def legal_actions(self) -> list[dict[str, Any]]:
        return [
            _mapping(item, f"native actions[{index}]")
            for index, item in enumerate(json.loads(self.native.legal_actions_json()))
        ]

    def status(self) -> dict[str, Any]:
        status = _mapping(json.loads(self.native.status_json()), "native status")
        validate_card_select_settlement(
            status.get("card_select_settlement"),
            label="native status.card_select_settlement",
        )
        validate_progression(
            status.get("progression"),
            label="native status.progression",
        )
        return status

    def mapped_state(self, *, id_mapper: IdMapper) -> MappedCombatState:
        status = self.status()
        if not _boolean(status.get("supported"), "native status.supported"):
            reason = status.get("unsupported_reason") or status.get("input_state")
            raise CombatBridgeError("native_state_unsupported", reason)
        return encode_rl_v2(self.snapshot(), self.legal_actions(), id_mapper=id_mapper)

    def step(self, action_id: str) -> None:
        self.native.step(action_id)

    def terminal(self) -> bool:
        return bool(self.native.terminal())


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


def collect_provenance(
    *,
    repo_root: Path | str,
    simulator_repo: Path | str,
    module_path: Path | str,
    native_module: ModuleType,
) -> dict[str, Any]:
    repo = Path(repo_root).resolve()
    simulator = Path(simulator_repo).resolve()
    module_file = Path(module_path).resolve()
    source_paths = (
        repo / "analysis_scripts" / "combat_lightspeed_bridge.py",
        repo / "analysis_scripts" / "combat_lightspeed_calibration.py",
        repo / "simulator_adapters" / "sts_lightspeed" / "CMakeLists.txt",
        repo / "simulator_adapters" / "sts_lightspeed" / "combat_adapter.cpp",
    )
    digest = hashlib.sha256()
    for path in source_paths:
        if not path.is_file():
            raise CombatBridgeError("adapter_source_missing", path)
        relative = path.relative_to(repo).as_posix().encode("utf-8")
        data = path.read_bytes()
        digest.update(len(relative).to_bytes(4, "big"))
        digest.update(relative)
        digest.update(len(data).to_bytes(8, "big"))
        digest.update(data)
    simulator_source_sha256, source_count = hash_compiled_simulator_sources(simulator)
    build = _mapping(json.loads(native_module.build_info_json()), "native build info")
    if build.get("adapter_api_version") != ADAPTER_API_VERSION:
        raise CombatBridgeError("native_build_api_mismatch", build.get("adapter_api_version"))
    return {
        "adapter_commit": _git(repo, "rev-parse", "HEAD"),
        "adapter_dirty": bool(_git(repo, "status", "--porcelain=v1", "--", *(str(path.relative_to(repo)) for path in source_paths))),
        "adapter_source_sha256": digest.hexdigest(),
        "build": {**build, "python": sys.version.split()[0]},
        "module_path": module_file.as_posix(),
        "module_sha256": sha256_file(module_file),
        "module_size_bytes": module_file.stat().st_size,
        "simulator_commit": _git(simulator, "rev-parse", "HEAD"),
        "simulator_dirty": bool(_git(simulator, "status", "--porcelain=v1")),
        "simulator_source_file_count": source_count,
        "simulator_source_sha256": simulator_source_sha256,
        "submodules": {
            "json": _git(simulator / "json", "rev-parse", "HEAD"),
            "pybind11": _git(simulator / "pybind11", "rev-parse", "HEAD"),
        },
    }
