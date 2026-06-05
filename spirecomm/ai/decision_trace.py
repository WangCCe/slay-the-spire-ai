"""Small JSONL decision traces for live gameplay diagnosis."""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional


TRACE_ENV = "STS_DECISION_TRACE_FILE"
DISABLED_VALUES = {"", "0", "false", "off", "none", "disabled"}

logger = logging.getLogger(__name__)


def decision_trace_path(path: Optional[Path] = None) -> Optional[Path]:
    if path is not None:
        return Path(path)
    value = os.environ.get(TRACE_ENV)
    if value is None or value.strip().lower() in DISABLED_VALUES:
        return None
    return Path(value)


def build_decision_trace_event(
    action,
    game,
    source: str,
    decision_path: str = "",
) -> Dict[str, Any]:
    player = getattr(game, "player", None)
    return {
        "timestamp": datetime.utcnow().isoformat(timespec="milliseconds") + "Z",
        "unix_time": round(time.time(), 3),
        "source": str(source),
        "decision_path": str(decision_path or ""),
        "floor": _to_int(getattr(game, "floor", None)),
        "turn": _to_int(getattr(game, "turn", None)),
        "act": _to_int(getattr(game, "act", None)),
        "room_type": _safe_str(getattr(game, "room_type", "")),
        "screen_type": _safe_str(getattr(game, "screen_type", "")),
        "in_combat": bool(getattr(game, "in_combat", False)),
        "player": _player_summary(game, player),
        "hand": [_card_summary(card) for card in _safe_iterable(getattr(game, "hand", []))],
        "monsters": [
            _monster_summary(monster)
            for monster in _safe_iterable(getattr(game, "monsters", []))
        ],
        "potions": [
            _potion_summary(potion)
            for potion in _safe_iterable(getattr(game, "potions", []))
        ],
        "action": _action_summary(action, game),
    }


def write_decision_trace_event(
    action,
    game,
    source: str = "combat_rl",
    decision_path: str = "",
    path: Optional[Path] = None,
) -> bool:
    target = decision_trace_path(path)
    if target is None:
        return False
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        event = build_decision_trace_event(
            action,
            game,
            source=source,
            decision_path=decision_path,
        )
        with target.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, sort_keys=True) + "\n")
        return True
    except Exception as exc:
        logger.debug("decision trace write failed: %s", exc)
        return False


def _player_summary(game, player) -> Dict[str, Any]:
    return {
        "current_hp": _to_int(
            getattr(player, "current_hp", getattr(game, "current_hp", None))
        ),
        "max_hp": _to_int(getattr(player, "max_hp", getattr(game, "max_hp", None))),
        "block": _to_int(getattr(player, "block", getattr(game, "block", None))),
        "energy": _to_int(getattr(player, "energy", getattr(game, "energy", None))),
    }


def _card_summary(card) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(card, "name", "")),
        "id": _safe_str(getattr(card, "card_id", getattr(card, "id", ""))),
        "cost": _to_int(
            getattr(card, "cost_for_turn", getattr(card, "cost", None)),
            default=None,
        ),
        "playable": _safe_bool(getattr(card, "is_playable", None)),
        "type": _safe_str(getattr(card, "card_type", "")),
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
        "move_hits": _to_int(getattr(monster, "move_hits", None)),
        "gone": bool(getattr(monster, "is_gone", False)),
        "half_dead": bool(getattr(monster, "half_dead", False)),
    }


def _potion_summary(potion) -> Dict[str, Any]:
    return {
        "name": _safe_str(getattr(potion, "name", "")),
        "id": _safe_str(getattr(potion, "potion_id", getattr(potion, "id", ""))),
        "can_use": _safe_bool(getattr(potion, "can_use", None)),
    }


def _action_summary(action, game) -> Dict[str, Any]:
    summary = {
        "type": type(action).__name__ if action is not None else None,
        "command": _safe_str(getattr(action, "command", "")),
    }
    for attr in ("card_index", "target_index", "potion_index", "use"):
        if hasattr(action, attr):
            summary[attr] = _json_scalar(getattr(action, attr))

    card = getattr(action, "card", None)
    card_index = getattr(action, "card_index", None)
    if card is None and isinstance(card_index, int):
        hand = list(_safe_iterable(getattr(game, "hand", [])))
        if 0 <= card_index < len(hand):
            card = hand[card_index]
    if card is not None:
        summary["card"] = _card_summary(card)

    potion = getattr(action, "potion", None)
    potion_index = getattr(action, "potion_index", None)
    if potion is None and isinstance(potion_index, int):
        potions = list(_safe_iterable(getattr(game, "potions", [])))
        if 0 <= potion_index < len(potions):
            potion = potions[potion_index]
    if potion is not None:
        summary["potion"] = _potion_summary(potion)

    return summary


def _safe_iterable(value):
    return value if isinstance(value, (list, tuple)) else []


def _safe_str(value) -> str:
    if value is None:
        return ""
    return str(value)


def _safe_bool(value):
    return None if value is None else bool(value)


def _json_scalar(value):
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    return str(value)


def _to_int(value, default=0):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError, OverflowError):
        try:
            return int(float(value))
        except (TypeError, ValueError, OverflowError):
            return default
