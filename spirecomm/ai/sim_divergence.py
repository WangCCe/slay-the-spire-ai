"""Single-step simulation divergence traces for live combat diagnosis."""

import copy
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

from spirecomm.ai.heuristics.card_upgrades import (
    known_block_upgrade_bonus,
    known_damage_upgrade_bonus,
)


TRACE_ENV = "STS_SIM_DIVERGENCE_TRACE_FILE"
DISABLED_VALUES = {"", "0", "false", "off", "none", "disabled"}

BASE_ATTACK_DAMAGE = {
    "Anger": 6,
    "Bash": 8,
    "Carnage": 20,
    "Cleave": 8,
    "Clothesline": 12,
    "Headbutt": 9,
    "Hemokinesis": 15,
    "Iron Wave": 5,
    "Pommel Strike": 9,
    "Strike": 6,
    "Twin Strike": 10,
}

BASE_SKILL_BLOCK = {
    "Armaments": 5,
    "Defend": 5,
    "Flame Barrier": 12,
    "Ghostly Armor": 10,
    "Impervious": 30,
    "Iron Wave": 5,
    "Power Through": 15,
    "Shrug It Off": 8,
    "True Grit": 7,
}

CARD_SELF_DAMAGE = {
    "Hemokinesis": 2,
}

CARD_ID_ALIASES = {
    "Defend_R": "Defend",
    "Strike_R": "Strike",
}

logger = logging.getLogger(__name__)
_pending_expected: Optional[Dict[str, Any]] = None


def divergence_trace_path(path: Optional[Path] = None) -> Optional[Path]:
    if path is not None:
        return Path(path)
    value = os.environ.get(TRACE_ENV)
    if value is None or value.strip().lower() in DISABLED_VALUES:
        return None
    return Path(value)


def reset_pending_divergence() -> None:
    global _pending_expected
    _pending_expected = None


def record_expected_action(action, game, path: Optional[Path] = None) -> bool:
    """Record a read-only one-action expectation for the next live state."""
    global _pending_expected

    if divergence_trace_path(path) is None:
        return False
    if action is None or not getattr(game, "in_combat", False):
        _pending_expected = None
        return False

    try:
        before = snapshot_combat_state(game)
        _pending_expected = {
            "timestamp": _timestamp(),
            "unix_time": round(time.time(), 3),
            "floor": before["floor"],
            "turn": before["turn"],
            "before": before,
            "expected": _expected_after_action(action, game, before),
            "action": _action_summary(action, game),
        }
        return True
    except Exception as exc:
        _pending_expected = None
        logger.debug("sim divergence expected-state record failed: %s", exc)
        return False


def observe_next_state(game, path: Optional[Path] = None) -> bool:
    """Compare the pending expectation with the newest live state and log diffs."""
    global _pending_expected

    target = divergence_trace_path(path)
    if target is None or _pending_expected is None:
        return False

    pending = _pending_expected
    _pending_expected = None

    try:
        actual = snapshot_combat_state(game)
        if actual["floor"] != pending["floor"]:
            return False

        ignored_diffs = _ignored_diff_keys(pending)
        diffs = _diff_snapshots(pending["expected"], actual, ignored_diffs)
        if not diffs:
            return False

        event = {
            "event_type": "sim_divergence",
            "timestamp": _timestamp(),
            "unix_time": round(time.time(), 3),
            "reason": _classify_reason(pending, actual, diffs),
            "floor": actual["floor"],
            "turn": actual["turn"],
            "expected_turn": pending["turn"],
            "action": pending["action"],
            "diffs": diffs,
            "before": pending["before"],
            "expected": pending["expected"],
            "actual": actual,
        }
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        logger.info(
            "[SIM_DIVERGENCE] reason=%s floor=%s turn=%s action=%s diffs=%s",
            event["reason"],
            event["floor"],
            event["turn"],
            event["action"].get("type"),
            sorted(diffs),
        )
        return True
    except Exception as exc:
        logger.debug("sim divergence observe failed: %s", exc)
        return False


def snapshot_combat_state(game) -> Dict[str, Any]:
    player = getattr(game, "player", None)
    return {
        "floor": _to_int(getattr(game, "floor", None)),
        "turn": _to_int(getattr(game, "turn", None)),
        "act": _to_int(getattr(game, "act", None)),
        "room_type": _safe_str(getattr(game, "room_type", "")),
        "in_combat": bool(getattr(game, "in_combat", False)),
        "player": {
            "current_hp": _to_int(
                getattr(player, "current_hp", getattr(game, "current_hp", None))
            ),
            "max_hp": _to_int(getattr(player, "max_hp", getattr(game, "max_hp", None))),
            "block": _to_int(getattr(player, "block", getattr(game, "block", None))),
            "energy": _to_int(getattr(player, "energy", getattr(game, "energy", None))),
        },
        "hand": [_card_summary(card) for card in _safe_iterable(getattr(game, "hand", []))],
        "monsters": [
            _monster_summary(monster)
            for monster in _safe_iterable(getattr(game, "monsters", []))
        ],
    }


def _expected_after_action(action, game, before: Dict[str, Any]) -> Dict[str, Any]:
    expected = copy.deepcopy(before)
    action_type = type(action).__name__ if action is not None else ""

    if action_type == "PlayCardAction":
        card = _card_for_action(action, game)
        card_index = _to_int(getattr(action, "card_index", -1), default=-1)
        if card is not None:
            expected["player"]["energy"] = max(
                0,
                expected["player"]["energy"] - max(0, _card_cost(card)),
            )
            if _is_attack_card(card):
                target_index = _target_index_for_action(action, game)
                damage = _card_damage(card)
                _apply_expected_attack(expected, target_index, damage)
                self_damage = _card_self_damage(card)
                if self_damage > 0:
                    expected["player"]["current_hp"] = max(
                        0,
                        expected["player"]["current_hp"] - self_damage,
                    )
            block = _card_block(card)
            if block > 0:
                expected["player"]["block"] += block
        if 0 <= card_index < len(expected["hand"]):
            expected["hand"].pop(card_index)

    elif action_type == "EndTurnAction":
        incoming = _incoming_damage_from_snapshot(before)
        current_block = expected["player"]["block"]
        expected["player"]["current_hp"] = max(
            0,
            expected["player"]["current_hp"] - max(0, incoming - current_block),
        )
        expected["player"]["block"] = 0
        expected["player"]["energy"] = 0

    return expected


def _apply_expected_attack(expected: Dict[str, Any], target_index: Optional[int], damage: int) -> None:
    if target_index is None or target_index < 0:
        return
    monsters = expected.get("monsters", [])
    if target_index >= len(monsters):
        return
    target = monsters[target_index]
    remaining_damage = max(0, damage)
    if target["block"] > 0:
        blocked = min(target["block"], remaining_damage)
        target["block"] -= blocked
        remaining_damage -= blocked
    target["hp"] = max(0, target["hp"] - remaining_damage)
    if target["hp"] <= 0:
        target["gone"] = True


def _diff_snapshots(
    expected: Dict[str, Any],
    actual: Dict[str, Any],
    ignored_keys: Optional[set] = None,
) -> Dict[str, Dict[str, Any]]:
    diffs: Dict[str, Dict[str, Any]] = {}
    ignored_keys = ignored_keys or set()
    for field in ("current_hp", "block", "energy"):
        _add_diff(
            diffs,
            f"player.{field}",
            expected.get("player", {}).get(field),
            actual.get("player", {}).get(field),
            ignored_keys,
        )

    expected_monsters = expected.get("monsters", [])
    actual_monsters = actual.get("monsters", [])
    count = max(len(expected_monsters), len(actual_monsters))
    for index in range(count):
        expected_monster = expected_monsters[index] if index < len(expected_monsters) else {}
        actual_monster = actual_monsters[index] if index < len(actual_monsters) else {}
        for field in ("hp", "block", "gone", "half_dead", "intent"):
            _add_diff(
                diffs,
                f"monsters[{index}].{field}",
                expected_monster.get(field),
                actual_monster.get(field),
                ignored_keys,
            )
    return diffs


def _ignored_diff_keys(pending: Dict[str, Any]) -> set:
    action = pending.get("action", {})
    if action.get("type") == "EndTurnAction":
        return {"player.energy"}
    return set()


def _add_diff(
    diffs: Dict[str, Dict[str, Any]],
    key: str,
    expected: Any,
    actual: Any,
    ignored_keys: set,
) -> None:
    if key in ignored_keys:
        return
    if expected != actual:
        diffs[key] = {"expected": expected, "actual": actual}


def _classify_reason(
    pending: Dict[str, Any],
    actual: Dict[str, Any],
    diffs: Dict[str, Dict[str, Any]],
) -> str:
    before = pending.get("before", {})
    action = pending.get("action", {})
    player_diff = any(key.startswith("player.") for key in diffs)
    monster_diff = any(key.startswith("monsters[") for key in diffs)

    if (
        action.get("type") == "PlayCardAction"
        and player_diff
        and _action_targets_guardian(action, before)
        and _guardian_sharp_hide_visible(before)
    ):
        return "guardian_sharp_hide_reflection"

    if (
        action.get("type") == "EndTurnAction"
        and "player.current_hp" in diffs
        and _hand_contains_burn(before)
    ):
        return "end_turn_burn_damage"

    if monster_diff and _slime_split_visible(before):
        return "slime_split_state_mismatch"

    if monster_diff:
        return "monster_state_mismatch"
    if player_diff:
        return "player_state_mismatch"
    return "state_mismatch"


def _action_targets_guardian(action: Dict[str, Any], snapshot: Dict[str, Any]) -> bool:
    target_index = action.get("target_index")
    monsters = snapshot.get("monsters", [])
    if isinstance(target_index, int) and 0 <= target_index < len(monsters):
        monster = monsters[target_index]
        return _normalize(monster.get("id")) == "theguardian" or _normalize(monster.get("name")) == "theguardian"
    return any(
        _normalize(monster.get("id")) == "theguardian" or _normalize(monster.get("name")) == "theguardian"
        for monster in monsters
    )


def _guardian_sharp_hide_visible(snapshot: Dict[str, Any]) -> bool:
    for monster in snapshot.get("monsters", []):
        if not (
            _normalize(monster.get("id")) == "theguardian"
            or _normalize(monster.get("name")) == "theguardian"
        ):
            continue
        intent = _normalize(monster.get("intent"))
        if intent in {"attackbuff", "intentattackbuff"}:
            return True
    return False


def _hand_contains_burn(snapshot: Dict[str, Any]) -> bool:
    return any(_normalize(card.get("name")) == "burn" for card in snapshot.get("hand", []))


def _slime_split_visible(snapshot: Dict[str, Any]) -> bool:
    has_dead_boss = False
    live_slimes = 0
    for monster in snapshot.get("monsters", []):
        identifiers = {_normalize(monster.get("id")), _normalize(monster.get("name"))}
        if any("slimeboss" in value for value in identifiers):
            has_dead_boss = bool(monster.get("gone")) or _to_int(monster.get("hp")) <= 0
        elif any("slime" in value for value in identifiers) and not monster.get("gone"):
            live_slimes += 1
    return has_dead_boss and live_slimes >= 2


def _incoming_damage_from_snapshot(snapshot: Dict[str, Any]) -> int:
    total = 0
    for monster in snapshot.get("monsters", []):
        if monster.get("gone") or monster.get("half_dead"):
            continue
        if "attack" not in _normalize(monster.get("intent")):
            continue
        total += max(0, _to_int(monster.get("move_damage"))) * max(
            1,
            _to_int(monster.get("move_hits"), default=1),
        )
    return total


def _card_for_action(action, game):
    card = getattr(action, "card", None)
    if card is not None:
        return card
    card_index = _to_int(getattr(action, "card_index", -1), default=-1)
    hand = list(_safe_iterable(getattr(game, "hand", [])))
    if 0 <= card_index < len(hand):
        return hand[card_index]
    return None


def _target_index_for_action(action, game) -> Optional[int]:
    target_index = getattr(action, "target_index", None)
    if isinstance(target_index, int) and target_index >= 0:
        return target_index
    target = getattr(action, "target_monster", None)
    if target is None:
        return None
    monsters = list(_safe_iterable(getattr(game, "monsters", [])))
    for index, monster in enumerate(monsters):
        if monster is target:
            return index
    monster_index = getattr(target, "monster_index", None)
    return monster_index if isinstance(monster_index, int) else None


def _action_summary(action, game) -> Dict[str, Any]:
    summary = {"type": type(action).__name__ if action is not None else None}
    for attr in ("card_index", "target_index", "potion_index", "use"):
        if hasattr(action, attr):
            summary[attr] = _json_scalar(getattr(action, attr))
    card = _card_for_action(action, game)
    if card is not None:
        summary["card"] = _card_summary(card)
    return summary


def _card_summary(card) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(card, "name", "")),
        "id": _safe_str(getattr(card, "card_id", getattr(card, "id", ""))),
        "type": _safe_str(
            getattr(card, "type", getattr(card, "card_type", ""))
        ),
        "cost": _card_cost(card),
        "damage": _card_damage(card),
        "block": _card_block(card),
    }


def _monster_summary(monster) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(monster, "name", "")),
        "id": _safe_str(getattr(monster, "monster_id", getattr(monster, "id", ""))),
        "hp": _to_int(getattr(monster, "current_hp", None)),
        "max_hp": _to_int(getattr(monster, "max_hp", None)),
        "block": _to_int(getattr(monster, "block", None)),
        "intent": _safe_str(getattr(monster, "intent", "")),
        "move_damage": _to_int(getattr(monster, "move_adjusted_damage", None)),
        "move_hits": _to_int(getattr(monster, "move_hits", None), default=1),
        "gone": bool(getattr(monster, "is_gone", False)),
        "half_dead": bool(getattr(monster, "half_dead", False)),
    }


def _is_attack_card(card) -> bool:
    card_type = _normalize(getattr(card, "type", getattr(card, "card_type", "")))
    return card_type in {"attack", "cardtypeattack"}


def _card_cost(card) -> int:
    return max(
        0,
        _to_int(getattr(card, "cost_for_turn", getattr(card, "cost", 0))),
    )


def _card_damage(card) -> int:
    explicit = _to_int(getattr(card, "damage", 0))
    card_name = _known_card_name(card, BASE_ATTACK_DAMAGE)
    base_damage = BASE_ATTACK_DAMAGE.get(card_name) if card_name else None
    upgrade_bonus = known_damage_upgrade_bonus(card, card_name) if card_name else 0
    if explicit > 0:
        if base_damage is not None and upgrade_bonus > 0 and explicit <= base_damage:
            return explicit + upgrade_bonus
        return explicit
    if base_damage is not None:
        return base_damage + upgrade_bonus
    return 0


def _card_block(card) -> int:
    explicit = _to_int(getattr(card, "block", 0))
    card_name = _known_card_name(card, BASE_SKILL_BLOCK)
    base_block = BASE_SKILL_BLOCK.get(card_name) if card_name else None
    upgrade_bonus = known_block_upgrade_bonus(card, card_name) if card_name else 0
    if explicit > 0:
        if base_block is not None and upgrade_bonus > 0 and explicit <= base_block:
            return explicit + upgrade_bonus
        return explicit
    if base_block is not None:
        return base_block + upgrade_bonus
    return 0


def _card_self_damage(card) -> int:
    card_name = _known_card_name(card, CARD_SELF_DAMAGE)
    if card_name is None:
        return 0
    return CARD_SELF_DAMAGE.get(card_name, 0)


def _known_card_name(card, known_values: Dict[str, int]) -> Optional[str]:
    known_by_normalized = {_normalize(name): name for name in known_values}
    for attr in ("name", "card_id", "id"):
        value = getattr(card, attr, None)
        if value in CARD_ID_ALIASES:
            return CARD_ID_ALIASES[value]
        normalized = _normalize(_strip_upgrade_suffix(value))
        if normalized in known_by_normalized:
            return known_by_normalized[normalized]
    return None


def _strip_upgrade_suffix(value) -> str:
    text = str(value or "")
    if "+" not in text:
        return text
    base, suffix = text.rsplit("+", 1)
    if suffix == "" or suffix.isdigit():
        return base
    return text


def _normalize(value) -> str:
    return "".join(ch for ch in str(value or "").lower() if ch.isalnum())


def _safe_iterable(value):
    return value if isinstance(value, (list, tuple)) else []


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def _json_scalar(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _to_int(value, default=0) -> int:
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return default


def _timestamp() -> str:
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"
